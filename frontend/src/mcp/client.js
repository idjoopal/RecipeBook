/**
 * MCP Streamable HTTP 클라이언트
 * SDK 없이 fetch + SSE 스트림 파싱으로 구현
 */

let _msgId = 1
const nextId = () => _msgId++

async function parseResponse(response) {
  const ct = response.headers.get('content-type') || ''

  if (ct.includes('text/event-stream')) {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let result = null

    const processPart = (part) => {
      const lines = part.split('\n')
      for (const line of lines) {
        if (line.startsWith('data:')) {
          const json = line.slice(5).trim()
          if (!json) continue
          try {
            const parsed = JSON.parse(json)
            if (parsed.result !== undefined || parsed.error !== undefined) {
              result = parsed
            }
          } catch (_) {}
        }
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop()
      for (const part of parts) processPart(part)
    }
    // Flush any trailing message that wasn't terminated by \n\n before stream end.
    if (buffer.trim()) processPart(buffer)

    return result
  }

  return await response.json()
}

export class McpClient {
  constructor() {
    this.baseUrl = '/mcp/'
    this.sessionId = null
    this.serverInfo = null
    this.protocolVersion = null
  }

  async _send(body, _isRetry = false) {
    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
    }
    if (this.sessionId) {
      headers['Mcp-Session-Id'] = this.sessionId
    }

    const response = await fetch(this.baseUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })

    const newSession = response.headers.get('Mcp-Session-Id')
    if (newSession) this.sessionId = newSession

    if (!response.ok) {
      // 세션 만료/무효(서버 재기동 등, 4xx) → 1회에 한해 세션 리셋 후 재초기화+재시도.
      // initialize 자체는 재귀를 피하기 위해 복구 대상에서 제외한다.
      if (!_isRetry && this.sessionId && response.status >= 400 && response.status < 500
          && body.method !== 'initialize') {
        this.sessionId = null
        await this.initialize()
        return this._send(body, true)
      }
      const text = await response.text()
      throw new Error(`MCP HTTP ${response.status}: ${text}`)
    }

    // 204 No Content (notifications)
    if (response.status === 204) return null

    return parseResponse(response)
  }

  async initialize() {
    const body = {
      jsonrpc: '2.0',
      id: nextId(),
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: { roots: { listChanged: false } },
        clientInfo: { name: 'prebuilt-mcp-ui', version: '0.1.0' },
      },
    }

    const res = await this._send(body)

    if (res?.result) {
      this.serverInfo = res.result.serverInfo
      this.protocolVersion = res.result.protocolVersion
    }

    // notifications/initialized
    await this._send({
      jsonrpc: '2.0',
      method: 'notifications/initialized',
    }).catch(() => {})

    return res?.result
  }

  async listTools() {
    const res = await this._send({
      jsonrpc: '2.0',
      id: nextId(),
      method: 'tools/list',
      params: {},
    })
    return res?.result?.tools ?? []
  }

  async callTool(name, args) {
    const start = Date.now()
    const res = await this._send({
      jsonrpc: '2.0',
      id: nextId(),
      method: 'tools/call',
      params: { name, arguments: args },
    })
    const elapsed = Date.now() - start

    if (res?.error) throw new Error(res.error.message || JSON.stringify(res.error))

    const content = res?.result?.content ?? []
    const text = content
      .filter(c => c.type === 'text')
      .map(c => c.text)
      .join('\n')

    return { text: text || JSON.stringify(res?.result), elapsed }
  }
}

export const mcpClient = new McpClient()
