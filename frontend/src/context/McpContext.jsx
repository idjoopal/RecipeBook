import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { mcpClient } from '../mcp/client.js'

const INITIAL_CONN = { status: 'connecting', sessionId: null, serverInfo: null, protocolVersion: null }

const DISABLED_STORAGE_KEY = 'agentikit.disabledTools'

function loadDisabled() {
  try {
    const raw = localStorage.getItem(DISABLED_STORAGE_KEY)
    if (!raw) return new Set()
    const arr = JSON.parse(raw)
    return new Set(Array.isArray(arr) ? arr : [])
  } catch (_) {
    return new Set()
  }
}

function saveDisabled(set) {
  try {
    localStorage.setItem(DISABLED_STORAGE_KEY, JSON.stringify(Array.from(set)))
  } catch (_) {}
}

const McpContext = createContext(null)

export function McpProvider({ children }) {
  const [connection, setConnection] = useState(INITIAL_CONN)
  const [tools, setTools] = useState([])
  const [disabledTools, setDisabledTools] = useState(() => loadDisabled())
  const pollRef = useRef(null)

  const toggleTool = useCallback((name) => {
    setDisabledTools(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      saveDisabled(next)
      return next
    })
  }, [])

  const connectMcp = useCallback(async () => {
    setConnection(c => ({ ...c, status: 'connecting' }))
    try {
      await mcpClient.initialize()
      const toolList = await mcpClient.listTools()
      setConnection({
        status: 'ready',
        sessionId: mcpClient.sessionId,
        serverInfo: mcpClient.serverInfo,
        protocolVersion: mcpClient.protocolVersion,
      })
      setTools(toolList)
    } catch (e) {
      setConnection(c => ({ ...c, status: 'error' }))
    }
  }, [])

  const handleRestart = useCallback(() => {
    setConnection(c => ({ ...c, status: 'restarting' }))
  }, [])

  useEffect(() => {
    connectMcp()
  }, [connectMcp])

  // 자동 재연결 폴링: 서버 재기동(restarting) 또는 연결 오류(error) 시
  // /health/live가 올라오면 세션을 리셋하고 재연결한다.
  // (CLI 재기동·일시 네트워크 장애로 끊긴 MCP 세션을 새로고침 없이 자가복구)
  useEffect(() => {
    const shouldPoll = connection.status === 'restarting' || connection.status === 'error'
    if (!shouldPoll) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      return
    }
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch('/health/live')
        if (r.ok) {
          clearInterval(pollRef.current)
          pollRef.current = null
          mcpClient.sessionId = null
          await connectMcp()
        }
      } catch (_) {}
    }, 1500)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [connection.status, connectMcp])

  const enabledTools = tools.filter(t => !disabledTools.has(t.name))

  const value = {
    connection,
    tools,
    enabledTools,
    disabledTools,
    toggleTool,
    connectMcp,
    handleRestart,
  }

  return <McpContext.Provider value={value}>{children}</McpContext.Provider>
}

export function useMcp() {
  const ctx = useContext(McpContext)
  if (!ctx) throw new Error('useMcp must be used within <McpProvider>')
  return ctx
}
