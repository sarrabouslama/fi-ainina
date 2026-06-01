import { useEffect, useRef, useState } from 'react'

export function useWebSocket(url) {
  const [messages, setMessages] = useState([])
  const [connected, setConnected] = useState(false)
  const ws = useRef(null)
  const timer = useRef(null)

  const connect = () => {
    if (!url) return
    try {
      ws.current = new WebSocket(url)
      ws.current.onopen = () => { setConnected(true); clearTimeout(timer.current) }
      ws.current.onclose = () => { setConnected(false); timer.current = setTimeout(connect, 4000) }
      ws.current.onerror = () => setConnected(false)
      ws.current.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data)
          setMessages(p => [{ ...d, _ts: new Date().toISOString() }, ...p].slice(0, 100))
        } catch {}
      }
    } catch { setConnected(false) }
  }

  useEffect(() => { connect(); return () => { clearTimeout(timer.current); ws.current?.close() } }, [url])
  return { messages, connected }
}
