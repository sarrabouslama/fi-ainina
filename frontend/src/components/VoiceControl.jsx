import { useState } from 'react'
import axios from 'axios'

export default function VoiceControl() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [speed, setSpeed] = useState(1.0)

  const handleSpeak = async () => {
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    setResponse(null)
    try {
      const res = await axios.post('http://localhost:8002/speak',
        { text, speed },
        { responseType: 'blob', timeout: 15000 }
      )
      const url = URL.createObjectURL(res.data)
      const audio = new Audio(url)
      audio.play()
      setResponse('Audio joué avec succès ✅')
    } catch (e) {
      setError('Service vocal non disponible')
    } finally {
      setLoading(false)
    }
  }

  const handleChat = async () => {
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    setResponse(null)
    try {
      const res = await axios.post('http://localhost:8001/chat', {
        user_id: '00000000-0000-0000-0000-000000000001',
        message: text,
        emotion: 'auto',
        synthesize_voice: true,
      }, { timeout: 15000 })

      const reply = res.data?.response
      setResponse(reply)

      if (res.data?.audio_base64) {
        const bytes = atob(res.data.audio_base64)
        const arr = new Uint8Array(bytes.length)
        for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i)
        const blob = new Blob([arr], { type: res.data.audio_content_type || 'audio/wav' })
        const url = URL.createObjectURL(blob)
        new Audio(url).play()
      }
    } catch (e) {
      setError('Service LLM non disponible')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-2xl p-5"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <h2 className="font-display font-bold text-base text-white mb-4">🎙️ Contrôle Vocal</h2>

      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="Écrivez un message pour Léa..."
        rows={3}
        className="w-full rounded-xl px-4 py-3 text-sm resize-none outline-none transition"
        style={{
          background: 'var(--surface2)',
          border: '1px solid var(--border)',
          color: 'var(--text)',
        }}
      />

      <div className="mt-3 mb-4">
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs" style={{ color: 'var(--muted)' }}>
            Vitesse de la voix
          </label>
          <span className="text-xs font-bold" style={{ color: 'var(--accent)' }}>{speed}x</span>
        </div>
        <input
          type="range" min="0.5" max="2.0" step="0.1"
          value={speed}
          onChange={e => setSpeed(parseFloat(e.target.value))}
          className="w-full h-1 rounded-full appearance-none cursor-pointer"
          style={{ background: 'var(--surface2)', accentColor: 'var(--accent)' }}
        />
        <div className="flex justify-between text-xs mt-1" style={{ color: 'var(--muted)' }}>
          <span>0.5x</span><span>1.0x</span><span>2.0x</span>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleSpeak}
          disabled={loading || !text.trim()}
          className="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-40"
          style={{ background: 'var(--accent)', color: 'white' }}>
          {loading ? '...' : '🔊 Parler'}
        </button>
        <button
          onClick={handleChat}
          disabled={loading || !text.trim()}
          className="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-40"
          style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}>
          {loading ? '...' : '🧠 LLM + Voix'}
        </button>
      </div>

      {response && (
        <div className="mt-3 p-3 rounded-xl text-sm animate-fade-in"
          style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid var(--ok)', color: 'var(--ok)' }}>
          {response}
        </div>
      )}
      {error && (
        <div className="mt-3 p-3 rounded-xl text-sm animate-fade-in"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid var(--danger)', color: 'var(--danger)' }}>
          ⚠️ {error}
        </div>
      )}
    </div>
  )
}
