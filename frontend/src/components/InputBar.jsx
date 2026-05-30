import { useRef, useEffect } from 'react'

export default function InputBar({ onSend, disabled, prefill }) {
  const ref = useRef(null)

  // 샘플 칩 등 외부에서 입력란을 채울 때: prefill 값이 바뀌면 textarea에 반영하고 포커스.
  useEffect(() => {
    if (prefill == null || !ref.current) return
    ref.current.value = prefill
    ref.current.style.height = 'auto'
    ref.current.style.height = Math.min(ref.current.scrollHeight, 140) + 'px'
    ref.current.focus()
  }, [prefill])

  function handleSend() {
    const text = ref.current?.value.trim()
    if (!text) return
    onSend(text)
    ref.current.value = ''
    ref.current.style.height = 'auto'
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleInput(e) {
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
  }

  return (
    <div className="input-bar">
      <textarea
        ref={ref}
        rows={1}
        placeholder="입력 후 Enter (Shift+Enter로 줄바꿈)"
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
      />
      <button className="send-btn" onClick={handleSend} disabled={disabled}>
        Send
      </button>
    </div>
  )
}
