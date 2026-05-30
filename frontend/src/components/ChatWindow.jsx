import { useEffect, useRef } from 'react'
import Message from './Message.jsx'

export default function ChatWindow({ messages, isLoading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="messages">
        <div className="empty-state">
          <div className="empty-state-icon">🔌</div>
          <div className="empty-state-title">MCP Tool Tester</div>
          <div className="empty-state-hint">입력한 텍스트를 선택된 MCP Tool로 전달합니다</div>
        </div>
      </div>
    )
  }

  return (
    <div className="messages">
      {messages.map(msg => (
        <Message key={msg.id} message={msg} />
      ))}
      {isLoading && (
        <div className="message assistant">
          <div className="message-meta">🤖 처리 중…</div>
          <div className="message-bubble">
            <span className="spinner" />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
