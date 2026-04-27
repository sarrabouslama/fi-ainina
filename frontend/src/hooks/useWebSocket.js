/**
 * useWebSocket.js — WebSocket hook for real-time fall detection stream.
 * TODO P3 frontend: implement
 * Usage: const { frame, analysis, isConnected } = useWebSocket(url)
 */
import { useState, useEffect, useRef } from 'react'

export function useWebSocket(url) {
  const [frame, setFrame] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    // TODO: open WebSocket, parse { frame, analysis } messages
    return () => { wsRef.current?.close() }
  }, [url])

  return { frame, analysis, isConnected }
}
