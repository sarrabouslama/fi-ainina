import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import { Send, Volume2, Loader2, RefreshCw, Bot, AlertTriangle, Info, Mic, MicOff } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const MODES = [
  {
    key: 'chat',
    icon: <Send size={13}/>,
    label: 'Chat + Voix (LLM)',
    desc: 'Léa lit votre message, génère une réponse intelligente avec l\'IA et vous la lit à voix haute.',
  },
  {
    key: 'speak',
    icon: <Volume2 size={13}/>,
    label: 'TTS seulement',
    desc: 'Votre texte est simplement lu à voix haute sans réponse IA. Utile pour tester la synthèse vocale.',
  },
]

const PHRASES = [
  "J'ai besoin d'aide",
  "Je me sens bien merci",
  "Appelez ma famille s'il vous plaît",
  "Rappelle-moi mes médicaments",
  "Je veux parler à quelqu'un",
]

const WAKE_WORDS = ['bonjour léa', 'bonjour lea', 'bonjour la', 'bonjour']

export default function VoicePage() {
  const { user } = useAuth()
  const [text, setText] = useState('')
  const [speed, setSpeed] = useState(1.0)
  const [loading, setLoading] = useState(false)
  const [ttsLoading, setTtsLoading] = useState(false)
  const [streamingReply, setStreamingReply] = useState('')
  const [mode, setMode] = useState('chat')
  const [history, setHistory] = useState([])
  const [continuousVoice, setContinuousVoice] = useState(false)
  const [interimTranscript, setInterimTranscript] = useState('')
  const [sending, setSending] = useState(false)

  // Microphone state
  const [micListening, setMicListening] = useState(false)
  const [wakeActive, setWakeActive] = useState(false) // wake word mode on/off
  const [wakeDetected, setWakeDetected] = useState(false) // animation trigger

  const recognitionRef = useRef(null)
  const wakeRecognitionRef = useRef(null)
  const wakeIntendedRef = useRef(false)
  const wakeRestartTimer = useRef(null)
  const bottomRef = useRef(null)
  const continuousVoiceRef = useRef(false)
  const startMicAutoSubmitRef = useRef(null)

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  const hasSpeech = !!SpeechRecognition

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  // ── One-shot mic: fill text input ────────────────────────────────────────
  const startMic = useCallback(() => {
    if (!hasSpeech || micListening) return
    const rec = new SpeechRecognition()
    rec.lang = 'fr-FR'
    rec.interimResults = true
    rec.maxAlternatives = 1
    recognitionRef.current = rec

    rec.onstart = () => setMicListening(true)
    rec.onend = () => { setMicListening(false); setInterimTranscript('') }
    rec.onerror = () => { setMicListening(false); setInterimTranscript('') }
    rec.onresult = (e) => {
      const results = Array.from(e.results)
      const interim = results.map(r => r[0].transcript).join('')
      setInterimTranscript(interim)
      const last = results[results.length - 1]
      if (last.isFinal) {
        setInterimTranscript('')
        setText(last[0].transcript)
      }
    }
    rec.start()
  }, [hasSpeech, micListening, SpeechRecognition])

  const stopMic = useCallback(() => {
    recognitionRef.current?.stop()
    setMicListening(false)
  }, [])

  const stopConversation = useCallback(() => {
    continuousVoiceRef.current = false
    setContinuousVoice(false)
    recognitionRef.current?.stop()
    setMicListening(false)
    // Restart wake-word listening if mains-libres was active
    if (wakeIntendedRef.current === false && wakeRecognitionRef.current === null) {
      // wake was stopped for command mode — re-arm it
      setTimeout(() => {
        if (!continuousVoiceRef.current) {
          wakeIntendedRef.current = true
        }
      }, 400)
    }
  }, [])

  // ── Core LLM + TTS logic (called by handleSubmit and auto-submit) ─────────
  const processMessage = useCallback(async (userMsg) => {
    setSending(true)
    setTimeout(() => setSending(false), 800) // flash "Envoi..." then LLM takes over
    setLoading(true)
    setHistory(h => [...h, { role: 'user', text: userMsg }])
    try {
      const response = await fetch('http://127.0.0.1:8001/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user?.id || '00000000-0000-0000-0000-000000000001',
          message: userMsg,
          emotion: 'auto',
        }),
      })
      if (!response.ok) throw new Error(`Service LLM: HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let reply = ''
      let detectedEmotion = 'neutral'
      let firstToken = true

      let llmError = null
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.error) { llmError = data.error; continue } // capture, don't throw
            if (data.token) {
              if (firstToken) { setLoading(false); firstToken = false }
              reply += data.token
              setStreamingReply(reply)
            }
            if (data.emotion) detectedEmotion = data.emotion
          } catch {}
        }
      }

      setStreamingReply('')

      if (!reply) {
        // LLM returned no text — show the actual error if we have one
        const errMsg = llmError
          ? `Léa n'a pas pu répondre : ${llmError}`
          : 'Léa n\'a pas répondu (vérifiez que Ollama est démarré : ollama serve)'
        setHistory(h => [...h, { role: 'error', text: errMsg }])
        if (continuousVoiceRef.current) setTimeout(() => startMicAutoSubmitRef.current?.(), 1500)
        return
      }

      setHistory(h => [...h, { role: 'lea', text: reply, emotion: detectedEmotion }])

      // Save conversation directly from frontend
      if (reply && user?.id) {
        axios.post('http://127.0.0.1:8000/conversations/save', {
          user_id: user.id,
          user_message: userMsg,
          assistant_reply: reply,
        }).catch(err => console.error('Conversation save failed:', err.response?.status, err.message))
      }

      if (reply) {
        setTtsLoading(true)
        axios.post('http://127.0.0.1:8002/speak',
          { text: reply, speed },
          { responseType: 'blob', timeout: 60000 }
        ).then(r => {
          const audio = new Audio(URL.createObjectURL(r.data))
          audio.onended = () => {
            if (continuousVoiceRef.current) setTimeout(() => startMicAutoSubmitRef.current?.(), 300)
          }
          audio.play()
        }).catch(err => {
          setHistory(h => [...h, { role: 'error', text: `Synthèse vocale échouée : ${err.message}` }])
          if (continuousVoiceRef.current) setTimeout(() => startMicAutoSubmitRef.current?.(), 500)
        }).finally(() => setTtsLoading(false))
      } else if (continuousVoiceRef.current) {
        setTimeout(() => startMicAutoSubmitRef.current?.(), 300)
      }
    } catch (e) {
      const msg = e.message || ''
      setHistory(h => [...h, { role: 'error', text: `Erreur : ${msg || 'Service LLM non disponible'}` }])
      // Keep conversation alive even after an error
      if (continuousVoiceRef.current) setTimeout(() => startMicAutoSubmitRef.current?.(), 1500)
    } finally {
      setLoading(false)
    }
  }, [speed, user])

  // ── Auto-submit mic: captures and immediately sends to LLM ───────────────
  const STOP_WORDS = ['arrête', 'arrete', 'stop', 'au revoir', 'fin', 'bonne nuit']

  const startMicAutoSubmit = useCallback(() => {
    if (!hasSpeech) return
    const rec = new SpeechRecognition()
    rec.lang = 'fr-FR'
    rec.continuous = true      // keep listening across pauses
    rec.interimResults = true
    rec.maxAlternatives = 1
    recognitionRef.current = rec

    let accumulatedFinal = ''  // full text built from all final results
    let sendTimer = null       // debounce: send 1.8s after last word

    rec.onstart = () => setMicListening(true)
    rec.onend = () => {
      setMicListening(false)
      setInterimTranscript('')
      clearTimeout(sendTimer)
    }
    rec.onerror = () => {
      setMicListening(false)
      setInterimTranscript('')
      clearTimeout(sendTimer)
      if (continuousVoiceRef.current) setTimeout(() => startMicAutoSubmitRef.current?.(), 1000)
    }
    rec.onresult = (e) => {
      // Separate interim (in-progress) from final (committed) results
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          accumulatedFinal += e.results[i][0].transcript + ' '
        } else {
          interim += e.results[i][0].transcript
        }
      }
      setInterimTranscript((accumulatedFinal + interim).trim())

      if (accumulatedFinal.trim()) {
        // Reset 1.8s silence timer on every new word
        clearTimeout(sendTimer)
        sendTimer = setTimeout(() => {
          const transcript = accumulatedFinal.trim()
          if (!transcript) return
          rec.stop()
          setInterimTranscript('')
          // Stop-word check — end conversation by voice
          if (STOP_WORDS.some(w => transcript.toLowerCase().includes(w))) {
            stopConversation()
            return
          }
          processMessage(transcript)
        }, 1800)
      }
    }
    try { rec.start() } catch {}
  }, [hasSpeech, SpeechRecognition, processMessage, stopConversation])

  // Keep ref in sync so processMessage's onended closure always has the latest
  useEffect(() => { startMicAutoSubmitRef.current = startMicAutoSubmit }, [startMicAutoSubmit])

  // ── Continuous wake word detection ───────────────────────────────────────
  // wakeIntendedRef = whether the USER wants it ON (refs declared above).
  // The recognition instance may auto-stop/restart without changing UI state.

  const createWakeRecognition = useCallback(() => {
    if (!hasSpeech) return
    const rec = new SpeechRecognition()
    rec.lang = 'fr-FR'
    rec.continuous = true
    rec.interimResults = false
    wakeRecognitionRef.current = rec

    rec.onresult = (e) => {
      const last = e.results[e.results.length - 1]
      const said = last[0].transcript.toLowerCase().trim()
      if (WAKE_WORDS.some(w => said.includes(w))) {
        setWakeDetected(true)
        setTimeout(() => setWakeDetected(false), 2000)
        continuousVoiceRef.current = true
        setContinuousVoice(true)
        const ack = 'Oui, je vous écoute. Que souhaitez-vous ?'
        setHistory(h => [...h, { role: 'lea', text: ack }])

        // MUST stop wake recognition before starting command mic —
        // Chrome only allows one SpeechRecognition instance at a time.
        wakeIntendedRef.current = false
        clearTimeout(wakeRestartTimer.current)
        rec.stop()

        const startListeningAfterAck = () => setTimeout(() => startMicAutoSubmitRef.current?.(), 300)

        axios.post('http://127.0.0.1:8002/speak', { text: ack, speed: 1.0 }, { responseType: 'blob', timeout: 10000 })
          .then(r => {
            const audio = new Audio(URL.createObjectURL(r.data))
            audio.onended = startListeningAfterAck
            audio.play().catch(() => {
              const utt = new SpeechSynthesisUtterance(ack)
              utt.lang = 'fr-FR'
              utt.onend = startListeningAfterAck
              window.speechSynthesis.speak(utt)
            })
          })
          .catch(() => {
            const utt = new SpeechSynthesisUtterance(ack)
            utt.lang = 'fr-FR'
            utt.onend = startListeningAfterAck
            window.speechSynthesis.speak(utt)
          })
      }
    }

    rec.onerror = (e) => {
      // 'no-speech' and 'aborted' are normal — don't treat as errors
      if (e.error === 'no-speech' || e.error === 'aborted') return
      // Real error: stop intentional listening
      wakeIntendedRef.current = false
      setWakeActive(false)
    }

    rec.onend = () => {
      // Chrome stops continuous recognition after silence — auto-restart
      // if the user still intends it to be on.
      clearTimeout(wakeRestartTimer.current)
      if (wakeIntendedRef.current) {
        wakeRestartTimer.current = setTimeout(() => {
          if (wakeIntendedRef.current && wakeRecognitionRef.current === rec) {
            try { rec.start() } catch {}
          }
        }, 250) // short delay avoids rapid stop/start churn visible in UI
      }
    }

    try { rec.start() } catch {}
  }, [hasSpeech, SpeechRecognition, startMic])

  const stopWakeWord = useCallback(() => {
    wakeIntendedRef.current = false
    clearTimeout(wakeRestartTimer.current)
    wakeRecognitionRef.current?.stop()
    wakeRecognitionRef.current = null
  }, [])

  const toggleWakeWord = () => {
    if (wakeActive) {
      stopWakeWord()
      setWakeActive(false)
    } else {
      wakeIntendedRef.current = true
      setWakeActive(true)
      createWakeRecognition()
    }
  }

  // Cleanup on unmount
  useEffect(() => () => {
    recognitionRef.current?.stop()
    wakeIntendedRef.current = false
    clearTimeout(wakeRestartTimer.current)
    wakeRecognitionRef.current?.stop()
  }, [])

  // ── Chat submit ──────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!text.trim() || loading) return
    const userMsg = text.trim()
    setText('')

    // Wake word — acknowledge, enable continuous conversation, then listen
    if (WAKE_WORDS.some(w => userMsg.toLowerCase().includes(w))) {
      continuousVoiceRef.current = true
      setContinuousVoice(true)
      setWakeDetected(true)
      setTimeout(() => setWakeDetected(false), 2000)
      const ack = 'Oui, je vous écoute. Que souhaitez-vous ?'
      setHistory(h => [...h, { role: 'user', text: userMsg }, { role: 'lea', text: ack }])
      try {
        const r = await axios.post('http://127.0.0.1:8002/speak',
          { text: ack, speed }, { responseType: 'blob', timeout: 15000 })
        const audio = new Audio(URL.createObjectURL(r.data))
        audio.onended = () => setTimeout(startMicAutoSubmit, 300)
        audio.play()
      } catch {
        setTimeout(startMicAutoSubmit, 1000)
      }
      return
    }

    if (mode === 'speak') {
      setLoading(true)
      setHistory(h => [...h, { role: 'user', text: userMsg }])
      try {
        const res = await axios.post('http://127.0.0.1:8002/speak',
          { text: userMsg, speed }, { responseType: 'blob', timeout: 15000 })
        new Audio(URL.createObjectURL(res.data)).play()
        setHistory(h => [...h, { role: 'lea', text: `🔊 Lecture : "${userMsg}"` }])
      } catch {
        setHistory(h => [...h, { role: 'error', text: 'Service vocal non disponible (port 8002).' }])
      } finally {
        setLoading(false)
      }
      return
    }

    await processMessage(userMsg)
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl font-bold mb-1" style={{ color: 'var(--text)' }}>Léa — Assistante Vocale</h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          Interaction naturelle en français · STT · TTS
        </p>
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Chat panel */}
        <div className="col-span-2 glass rounded-2xl p-5 flex flex-col" style={{ height: '620px' }}>
          {/* Mode selector */}
          <div className="flex gap-2 mb-3">
            {MODES.map(m => {
              const active = mode === m.key
              return (
                <button key={m.key} onClick={() => setMode(m.key)}
                  title={m.desc}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all"
                  style={{
                    background: active ? 'var(--green)' : 'rgba(255,255,255,0.6)',
                    border: `1px solid ${active ? 'var(--green)' : 'rgba(45,120,45,0.15)'}`,
                    color: active ? '#fff' : 'var(--muted)',
                    boxShadow: active ? '0 2px 8px rgba(30,107,46,0.25)' : 'none',
                  }}>
                  {m.icon} {m.label}
                  {active && <span style={{ opacity: 0.8, fontSize: 9, marginLeft: 2 }}>●</span>}
                </button>
              )
            })}
            <button onClick={() => setHistory([])}
              title="Effacer la conversation"
              className="ml-auto p-2 rounded-xl transition-all"
              style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(45,120,45,0.15)', color: 'var(--muted)' }}>
              <RefreshCw size={13} />
            </button>
          </div>

          {/* Continuous conversation banner */}
          {continuousVoice && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl mb-3 text-xs animate-fade-up"
              style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)' }}>
              <span className="w-2 h-2 rounded-full animate-pulse flex-shrink-0" style={{ background: 'var(--green)' }} />
              <span className="flex-1 font-semibold" style={{ color: 'var(--green)' }}>
                Conversation active — Léa vous écoute après chaque réponse
              </span>
              <button onClick={stopConversation} className="flex-shrink-0 font-semibold px-2 py-0.5 rounded-lg transition-all"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', color: 'var(--danger)' }}>
                Arrêter
              </button>
            </div>
          )}

          {/* Mode description */}
          {!continuousVoice && (
            <div className="flex items-start gap-2 px-3 py-2 rounded-xl mb-3 text-xs"
              style={{ background: 'rgba(30,107,46,0.06)', border: '1px solid rgba(30,107,46,0.12)' }}>
              <Info size={12} style={{ color: 'var(--green)', flexShrink: 0, marginTop: 1 }} />
              <span style={{ color: 'var(--text2)' }}>{MODES.find(m => m.key === mode)?.desc}</span>
            </div>
          )}

          {/* Prominent listening indicator — shows during continuous voice when mic is active */}
          {continuousVoice && micListening && (
            <div className="flex items-center justify-center gap-3 py-3 mb-2 rounded-xl animate-fade-up"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}>
              <div className="flex gap-1 items-end">
                {[1,2,3,4,3,2,1].map((h, i) => (
                  <div key={i} className="rounded-full animate-pulse"
                    style={{
                      width: 4, height: h * 5,
                      background: '#f87171',
                      animationDelay: `${i * 0.1}s`,
                    }} />
                ))}
              </div>
              <span className="text-sm font-semibold" style={{ color: '#f87171' }}>
                Je vous écoute...
              </span>
              <div className="flex gap-1 items-end">
                {[1,2,3,4,3,2,1].reverse().map((h, i) => (
                  <div key={i} className="rounded-full animate-pulse"
                    style={{
                      width: 4, height: h * 5,
                      background: '#f87171',
                      animationDelay: `${i * 0.1}s`,
                    }} />
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto flex flex-col gap-3 mb-4 pr-1">
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full">
                <div className="w-16 h-16 rounded-full flex items-center justify-center mb-3"
                  style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
                  <Bot size={32} style={{ color: 'var(--green)' }} />
                </div>
                <p className="font-display font-semibold mb-1" style={{ color: 'var(--text)' }}>Bonjour ! Je suis Léa</p>
                <p className="text-sm text-center" style={{ color: 'var(--muted)' }}>
                  Écrivez un message, utilisez le micro 🎤, ou activez le mot-clé
                </p>
              </div>
            ) : (
              history.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-up`}>
                  {msg.role !== 'user' && (
                    <div className="w-7 h-7 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-0.5"
                      style={{ background: msg.role === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)' }}>
                      {msg.role === 'error'
                        ? <AlertTriangle size={14} style={{ color: '#f87171' }} />
                        : <Bot size={14} style={{ color: 'var(--green)' }} />}
                    </div>
                  )}
                  <div className="max-w-xs px-4 py-3 rounded-2xl text-sm"
                    style={{
                      background: msg.role === 'user' ? 'rgba(30,107,46,0.12)' :
                                  msg.role === 'error' ? 'rgba(185,28,28,0.06)' : 'rgba(255,255,255,0.85)',
                      border: `1px solid ${msg.role === 'user' ? 'rgba(30,107,46,0.2)' :
                               msg.role === 'error' ? 'rgba(185,28,28,0.15)' : 'rgba(45,120,45,0.12)'}`,
                      color: msg.role === 'error' ? 'var(--danger)' : 'var(--text)',
                      borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    }}>
                    {msg.text}
                    {msg.emotion && (
                      <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Émotion : {msg.emotion}</p>
                    )}
                  </div>
                </div>
              ))
            )}
            {sending && (
              <div className="flex justify-end animate-fade-up">
                <div className="px-4 py-2 rounded-2xl flex items-center gap-2 text-xs font-semibold"
                  style={{ background: 'rgba(30,107,46,0.12)', border: '1px solid rgba(30,107,46,0.25)', borderRadius: '18px 18px 4px 18px', color: 'var(--green)' }}>
                  <Loader2 size={12} className="animate-spin" />
                  Envoi à Léa...
                </div>
              </div>
            )}
            {loading && (
              <div className="flex justify-start animate-fade-up">
                <div className="w-7 h-7 rounded-full flex items-center justify-center mr-2"
                  style={{ background: 'rgba(16,185,129,0.15)' }}>
                  <Bot size={14} style={{ color: 'var(--green)' }} />
                </div>
                <div className="px-4 py-3 rounded-2xl flex items-center gap-2"
                  style={{ background: 'rgba(255,255,255,0.85)', border: '1px solid rgba(45,120,45,0.12)' }}>
                  <Loader2 size={14} className="animate-spin" style={{ color: 'var(--green)' }} />
                  <span className="text-sm" style={{ color: 'var(--text2)' }}>
                    {mode === 'speak' ? 'Synthèse...' : 'Léa répond...'}
                  </span>
                </div>
              </div>
            )}
            {/* Live transcript preview while mic is listening */}
            {interimTranscript && (
              <div className="flex justify-end animate-fade-up">
                <div className="max-w-xs px-4 py-3 rounded-2xl text-sm italic"
                  style={{
                    background: 'rgba(30,107,46,0.06)',
                    border: '1px dashed rgba(30,107,46,0.3)',
                    color: 'var(--muted)',
                    borderRadius: '18px 18px 4px 18px',
                  }}>
                  {interimTranscript}
                  <span className="animate-pulse" style={{ color: 'var(--green)' }}>|</span>
                </div>
              </div>
            )}

            {streamingReply && (
              <div className="flex justify-start animate-fade-up">
                <div className="w-7 h-7 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-0.5"
                  style={{ background: 'rgba(16,185,129,0.15)' }}>
                  <Bot size={14} style={{ color: 'var(--green)' }} />
                </div>
                <div className="max-w-xs px-4 py-3 rounded-2xl text-sm"
                  style={{ background: 'rgba(255,255,255,0.85)', border: '1px solid rgba(45,120,45,0.12)', color: 'var(--text)', borderRadius: '18px 18px 18px 4px' }}>
                  {streamingReply}
                  <span className="animate-pulse" style={{ color: 'var(--green)' }}>▌</span>
                </div>
              </div>
            )}
            {ttsLoading && (
              <div className="flex justify-start animate-fade-up">
                <div className="w-7 h-7 rounded-full flex items-center justify-center mr-2"
                  style={{ background: 'rgba(16,185,129,0.15)' }}>
                  <Volume2 size={14} style={{ color: 'var(--green)' }} />
                </div>
                <div className="px-4 py-3 rounded-2xl flex items-center gap-2"
                  style={{ background: 'rgba(255,255,255,0.85)', border: '1px solid rgba(45,120,45,0.12)' }}>
                  <Loader2 size={14} className="animate-spin" style={{ color: 'var(--green)' }} />
                  <span className="text-sm" style={{ color: 'var(--text2)' }}>Synthèse vocale...</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input row */}
          <div className="flex gap-2">
            {/* Mic button */}
            {hasSpeech && (
              <button
                onClick={micListening ? stopMic : startMic}
                title={micListening ? 'Arrêter le micro' : 'Dicter un message'}
                className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-xl transition-all"
                style={{
                  background: micListening ? 'rgba(239,68,68,0.12)' : 'rgba(255,255,255,0.7)',
                  border: `1.5px solid ${micListening ? 'rgba(239,68,68,0.4)' : 'rgba(45,120,45,0.2)'}`,
                  color: micListening ? '#f87171' : 'var(--muted)',
                }}>
                {micListening ? <MicOff size={16} /> : <Mic size={16} />}
              </button>
            )}
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
              placeholder={micListening ? '🎤 Je vous écoute...' : 'Écrivez un message... (Entrée pour envoyer)'}
              rows={2}
              className="input-field flex-1 resize-none"
              disabled={loading}
              style={{ fontStyle: micListening ? 'italic' : 'normal' }}
            />
            <button onClick={handleSubmit} disabled={loading || !text.trim()}
              className="btn-primary flex-shrink-0 px-4 flex items-center justify-center">
              {loading
                ? <Loader2 size={16} className="animate-spin" style={{ color: '#fff' }} />
                : <Send size={16} style={{ color: '#fff' }} />}
            </button>
          </div>
        </div>

        {/* Right panel */}
        <div className="flex flex-col gap-4">
          {/* Wake word card */}
          <div className="glass rounded-2xl p-5 animate-fade-up"
            style={{
              border: wakeDetected ? '1.5px solid var(--green)' : '1px solid rgba(45,120,45,0.12)',
              transition: 'border 0.3s',
            }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Mic size={15} style={{ color: wakeActive ? 'var(--green)' : 'var(--muted)' }} />
                <h3 className="font-display font-semibold text-sm" style={{ color: 'var(--text)' }}>Mains-libres</h3>
              </div>
              {wakeActive && (
                <span className="flex items-center gap-1 text-xs font-semibold"
                  style={{ color: 'var(--ok)' }}>
                  <span className="w-1.5 h-1.5 rounded-full inline-block animate-pulse"
                    style={{ background: 'var(--ok)' }} />
                  En écoute
                </span>
              )}
            </div>

            <div className="p-3 rounded-xl mb-3 text-center"
              style={{
                background: wakeDetected ? 'rgba(30,107,46,0.15)' : 'rgba(30,107,46,0.06)',
                border: `1px solid ${wakeDetected ? 'rgba(30,107,46,0.4)' : 'rgba(30,107,46,0.15)'}`,
                transition: 'all 0.3s',
              }}>
              <p className="text-xs font-semibold mb-0.5" style={{ color: 'var(--green)' }}>
                {wakeDetected ? '✓ Mot-clé détecté !' : 'Mot-clé d\'activation'}
              </p>
              <p className="font-display text-lg" style={{ color: 'var(--text)' }}>"Bonjour Léa"</p>
            </div>

            <p className="text-xs mb-3" style={{ color: 'var(--muted)' }}>
              {hasSpeech
                ? 'Dites "Bonjour Léa" pour activer sans toucher l\'écran.'
                : 'Votre navigateur ne supporte pas la reconnaissance vocale (Chrome recommandé).'}
            </p>

            {hasSpeech && (
              <button
                onClick={toggleWakeWord}
                className="w-full py-2 rounded-xl text-xs font-semibold transition-all"
                style={{
                  background: wakeActive ? 'rgba(185,28,28,0.08)' : 'rgba(30,107,46,0.1)',
                  border: `1px solid ${wakeActive ? 'rgba(185,28,28,0.2)' : 'rgba(30,107,46,0.2)'}`,
                  color: wakeActive ? 'var(--danger)' : 'var(--green)',
                }}>
                {wakeActive ? 'Désactiver l\'écoute' : 'Activer l\'écoute continue'}
              </button>
            )}
          </div>

          {/* Speed control */}
          <div className="glass rounded-2xl p-5 animate-fade-up delay-100">
            <h3 className="font-display font-semibold text-sm mb-3" style={{ color: 'var(--text)' }}>Vitesse de voix</h3>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs" style={{ color: 'var(--muted)' }}>Lent</span>
              <span className="font-bold text-sm" style={{ color: 'var(--green)' }}>{speed}x</span>
              <span className="text-xs" style={{ color: 'var(--muted)' }}>Rapide</span>
            </div>
            <input type="range" min="0.5" max="2.0" step="0.1" value={speed}
              onChange={e => setSpeed(parseFloat(e.target.value))}
              className="w-full h-1 rounded-full appearance-none cursor-pointer"
              style={{ accentColor: 'var(--green)' }} />
          </div>

          {/* Quick phrases */}
          <div className="glass rounded-2xl p-5 animate-fade-up delay-200">
            <h3 className="font-display font-semibold text-sm mb-3" style={{ color: 'var(--text)' }}>Phrases rapides</h3>
            <div className="flex flex-col gap-2">
              {PHRASES.map((p, i) => (
                <button key={i} onClick={() => setText(p)}
                  className="text-left text-xs px-3 py-2.5 rounded-xl transition-all"
                  style={{ background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(45,120,45,0.12)', color: 'var(--text2)' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--green)'; e.currentTarget.style.color = 'var(--green)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(45,120,45,0.12)'; e.currentTarget.style.color = 'var(--text2)' }}>
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
