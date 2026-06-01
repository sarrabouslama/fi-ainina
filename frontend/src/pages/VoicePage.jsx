import { useState } from 'react'
import axios from 'axios'
import { Send, Volume2, Mic, Loader2, RefreshCw, Bot, AlertTriangle } from 'lucide-react'

export default function VoicePage() {
  const [text, setText] = useState('')
  const [speed, setSpeed] = useState(1.0)
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('chat') // 'chat' | 'speak'
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])

  const handleSubmit = async () => {
    if (!text.trim()) return
    const userMsg = text
    setText('')
    setLoading(true)
    setError(null)
    setHistory(h => [...h, { role: 'user', text: userMsg }])

    try {
      if (mode === 'speak') {
        const res = await axios.post('http://localhost:8002/speak',
          { text: userMsg, speed },
          { responseType: 'blob', timeout: 15000 })
        const url = URL.createObjectURL(res.data)
        new Audio(url).play()
        setHistory(h => [...h, { role: 'lea', text: `Audio généré pour: "${userMsg}"` }])
      } else {
        const res = await axios.post('http://localhost:8001/chat', {
          user_id: '00000000-0000-0000-0000-000000000001',
          message: userMsg,
          emotion: 'auto',
          synthesize_voice: true,
        }, { timeout: 20000 })

        const reply = res.data?.response || ''
        setHistory(h => [...h, { role: 'lea', text: reply, emotion: res.data?.emotion }])

        if (res.data?.audio_base64) {
          const bytes = atob(res.data.audio_base64)
          const arr = new Uint8Array(bytes.length)
          for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i)
          const blob = new Blob([arr], { type: res.data.audio_content_type || 'audio/wav' })
          new Audio(URL.createObjectURL(blob)).play()
        }
      }
    } catch (e) {
      const msg = mode === 'speak' ? 'Service vocal non disponible (port 8002)' : 'Service LLM non disponible (port 8001)'
      setError(msg)
      setHistory(h => [...h, { role: 'error', text: msg }])
    } finally {
      setLoading(false)
    }
  }

  const PHRASES = [
    "Comment puis-je vous aider aujourd'hui ?",
    "J'ai besoin d'aide",
    "Je me sens bien merci",
    "Appelez ma famille s'il vous plaît",
    "Rappelle-moi mes médicaments",
    "Je veux parler à quelqu'un",
  ]

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Léa — Assistante Vocale</h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          Interaction naturelle en français · Whisper STT · Coqui TTS
        </p>
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Chat panel */}
        <div className="col-span-2 glass rounded-2xl p-5 flex flex-col" style={{ height: '600px' }}>
          {/* Mode selector */}
          <div className="flex gap-2 mb-4">
            {[
              { key: 'chat', icon: <Send size={13}/>, label: 'Chat + Voix (LLM)' },
              { key: 'speak', icon: <Volume2 size={13}/>, label: 'TTS seulement' },
            ].map(m => (
              <button key={m.key} onClick={() => setMode(m.key)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all"
                style={{
                  background: mode === m.key ? 'rgba(45,138,67,0.2)' : 'rgba(7,43,14,0.4)',
                  border: `1px solid ${mode === m.key ? 'var(--green)' : 'var(--border)'}`,
                  color: mode === m.key ? 'var(--green-light)' : 'var(--muted)',
                }}>
                {m.icon} {m.label}
              </button>
            ))}
            <button onClick={() => setHistory([])}
              className="ml-auto p-2 rounded-xl transition-all"
              style={{ background: 'rgba(7,43,14,0.4)', border: '1px solid var(--border)', color: 'var(--muted)' }}>
              <RefreshCw size={13} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto flex flex-col gap-3 mb-4 pr-1">
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full">
                <div className="w-16 h-16 rounded-full flex items-center justify-center mb-3"
                  style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
                  <Bot size={32} style={{ color: 'var(--green)' }} />
                </div>
                <p className="font-display font-semibold text-white mb-1">Bonjour ! Je suis Léa</p>
                <p className="text-sm text-center" style={{ color: 'var(--muted)' }}>
                  Écrivez un message ou utilisez les phrases rapides
                </p>
              </div>
            ) : (
              history.map((msg, i) => (
                <div key={i}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-up`}>
                  {msg.role !== 'user' && (
                    <div className="w-7 h-7 rounded-full flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-0.5"
                      style={{ background: msg.role === 'error' ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.15)' }}>
                      {msg.role === 'error'
                        ? <AlertTriangle size={14} style={{ color: '#f87171' }} />
                        : <Bot size={14} style={{ color: 'var(--green)' }} />}
                    </div>
                  )}
                  <div className="max-w-xs px-4 py-3 rounded-2xl text-sm"
                    style={{
                      background: msg.role === 'user' ? 'rgba(45,138,67,0.25)' :
                                  msg.role === 'error' ? 'rgba(239,68,68,0.1)' : 'rgba(14,61,24,0.6)',
                      border: `1px solid ${msg.role === 'user' ? 'rgba(45,138,67,0.3)' :
                               msg.role === 'error' ? 'rgba(239,68,68,0.2)' : 'var(--border)'}`,
                      color: msg.role === 'error' ? '#f87171' : 'var(--text)',
                      borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    }}>
                    {msg.text}
                    {msg.emotion && (
                      <p className="text-xs mt-1 opacity-60">Émotion détectée: {msg.emotion}</p>
                    )}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex justify-start animate-fade-up">
                <div className="w-7 h-7 rounded-full flex items-center justify-center text-sm mr-2"
                  style={{ background: 'rgba(16,185,129,0.15)' }}>
                  <Bot size={14} style={{ color: 'var(--green)' }} />
                </div>
                <div className="px-4 py-3 rounded-2xl flex items-center gap-2"
                  style={{ background: 'rgba(14,61,24,0.6)', border: '1px solid var(--border)' }}>
                  <Loader2 size={14} className="animate-spin" style={{ color: 'var(--green-light)' }} />
                  <span className="text-sm" style={{ color: 'var(--muted)' }}>Léa répond...</span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex gap-2">
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
              placeholder="Écrivez un message... (Entrée pour envoyer)"
              rows={2}
              className="input-field flex-1 resize-none"
            />
            <button onClick={handleSubmit} disabled={loading || !text.trim()}
              className="btn-primary flex-shrink-0 w-12 flex items-center justify-center">
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>

        {/* Right panel */}
        <div className="flex flex-col gap-4">
          {/* Wake word tip */}
          <div className="glass rounded-2xl p-5 animate-fade-up">
            <div className="flex items-center gap-2 mb-3">
              <Mic size={15} style={{ color: 'var(--green-light)' }} />
              <h3 className="font-display font-semibold text-sm text-white">Mains-libres</h3>
            </div>
            <div className="p-3 rounded-xl mb-3"
              style={{ background: 'rgba(45,138,67,0.1)', border: '1px solid rgba(45,138,67,0.2)' }}>
              <p className="text-xs text-center font-bold mb-1" style={{ color: 'var(--green-light)' }}>
                Mot-clé d'activation
              </p>
              <p className="text-center font-display text-lg text-white">"Bonjour Léa"</p>
            </div>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              Dites ce mot-clé pour activer Léa sans toucher l'écran. Idéal pour mobilité réduite.
            </p>
          </div>

          {/* Speed control */}
          <div className="glass rounded-2xl p-5 animate-fade-up delay-100">
            <h3 className="font-display font-semibold text-sm text-white mb-3">
              Vitesse de voix
            </h3>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs" style={{ color: 'var(--muted)' }}>Lent</span>
              <span className="font-bold text-sm" style={{ color: 'var(--green-light)' }}>{speed}x</span>
              <span className="text-xs" style={{ color: 'var(--muted)' }}>Rapide</span>
            </div>
            <input type="range" min="0.5" max="2.0" step="0.1" value={speed}
              onChange={e => setSpeed(parseFloat(e.target.value))}
              className="w-full h-1 rounded-full appearance-none cursor-pointer"
              style={{ accentColor: 'var(--green)' }} />
          </div>

          {/* Quick phrases */}
          <div className="glass rounded-2xl p-5 animate-fade-up delay-200">
            <h3 className="font-display font-semibold text-sm text-white mb-3">Phrases rapides</h3>
            <div className="flex flex-col gap-2">
              {PHRASES.map((p, i) => (
                <button key={i} onClick={() => setText(p)}
                  className="text-left text-xs px-3 py-2.5 rounded-xl transition-all"
                  style={{ background: 'rgba(7,43,14,0.5)', border: '1px solid var(--border)', color: 'var(--text2)' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border2)'; e.currentTarget.style.color = 'var(--text)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text2)' }}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
