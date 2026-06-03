import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { Mic, MessageSquare, Star, LogOut, Phone, Heart, Activity, CheckCircle, Loader2, ShieldCheck } from 'lucide-react'

const WAKE_WORDS = ['bonjour léa', 'bonjour lea', 'bonjour la', 'bonjour']

export default function ElderlyHome() {
  const { user, logout, refreshUser } = useAuth()
  const navigate = useNavigate()

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Bonjour' : hour < 18 ? 'Bon après-midi' : 'Bonsoir'
  const firstName = user?.full_name?.split(' ')[0] || ''

  const [emergencyState, setEmergencyState] = useState('idle') // idle | sending | sent
  const [consentLoading, setConsentLoading] = useState(false)

  const handleLogout = async () => { await logout(); navigate('/login') }

  const handleEmergency = async () => {
    if (emergencyState !== 'idle') return
    setEmergencyState('sending')
    try {
      await axios.post('http://127.0.0.1:8000/alerts/emergency', {}, { timeout: 5000 })
      setEmergencyState('sent')
      setTimeout(() => setEmergencyState('idle'), 8000)
    } catch (e) {
      console.error('Emergency alert failed:', e)
      setEmergencyState('idle')
    }
  }

  const handleConsent = async () => {
    setConsentLoading(true)
    try {
      await axios.post(`http://127.0.0.1:8000/users/${user.id}/consent`, { consent_given: true })
      await refreshUser()
    } catch (e) {
      console.error('Consent update failed:', e)
    } finally {
      setConsentLoading(false)
    }
  }

  // ── Background wake word detection (starts automatically when consent given) ──
  const wakeRecRef = useRef(null)
  const wakeIntendedRef = useRef(false)
  const wakeTimerRef = useRef(null)

  const startWakeWord = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const rec = new SR()
    rec.lang = 'fr-FR'
    rec.continuous = true
    rec.interimResults = false
    wakeRecRef.current = rec

    rec.onresult = (e) => {
      const last = e.results[e.results.length - 1]
      const said = last[0].transcript.toLowerCase().trim()
      if (WAKE_WORDS.some(w => said.includes(w))) {
        wakeIntendedRef.current = false
        clearTimeout(wakeTimerRef.current)
        rec.stop()
        navigate('/voice', { state: { autoStart: true } })
      }
    }

    rec.onerror = (e) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return
      wakeIntendedRef.current = false
    }

    rec.onend = () => {
      clearTimeout(wakeTimerRef.current)
      if (wakeIntendedRef.current) {
        wakeTimerRef.current = setTimeout(() => {
          if (wakeIntendedRef.current && wakeRecRef.current === rec) {
            try { rec.start() } catch {}
          }
        }, 250)
      }
    }

    try { rec.start() } catch {}
  }, [navigate])

  useEffect(() => {
    if (!user?.consent_given) return
    wakeIntendedRef.current = true
    startWakeWord()
    return () => {
      wakeIntendedRef.current = false
      clearTimeout(wakeTimerRef.current)
      wakeRecRef.current?.stop()
      wakeRecRef.current = null
    }
  }, [user?.consent_given, startWakeWord])

  const actions = [
    { label: 'Parler à Léa', desc: 'Votre assistante vocale', path: '/voice', Icon: Mic, color: 'var(--green)', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.25)' },
    { label: 'Mes conversations', desc: 'Historique avec Léa', path: '/conversations', Icon: MessageSquare, color: 'var(--teal)', bg: 'rgba(6,182,212,0.08)', border: 'rgba(6,182,212,0.15)' },
    { label: 'Ma surveillance', desc: 'Chute et émotion', path: '/monitoring', Icon: Activity, color: 'var(--teal)', bg: 'rgba(13,125,107,0.08)', border: 'rgba(13,125,107,0.15)' },
    { label: 'Laisser un avis', desc: 'Feedback et questions', path: '/reviews', Icon: Star, color: 'var(--gold)', bg: 'rgba(160,106,16,0.08)', border: 'rgba(160,106,16,0.15)' },
  ]

  // ── Consent screen ────────────────────────────────────────────────────────
  if (!user?.consent_given) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full blur-3xl opacity-20"
            style={{ background: 'radial-gradient(circle, rgba(5,150,105,0.15), transparent)' }} />
        </div>

        <div className="relative z-10 w-full max-w-md glass rounded-2xl p-8 text-center">
          <ShieldCheck size={52} className="mx-auto mb-5" style={{ color: 'var(--green)' }} />
          <h1 className="text-2xl font-bold mb-3" style={{ color: 'var(--text)' }}>
            Votre accord est nécessaire
          </h1>
          <p className="text-base mb-6 leading-relaxed" style={{ color: 'var(--text2)' }}>
            Pour que Léa puisse vous accompagner en toute sécurité, nous avons besoin de votre accord
            pour utiliser la caméra et l'assistant vocal.
          </p>

          <div className="flex flex-col gap-3 mb-7 text-left">
            {[
              'Votre voix, pour répondre à vos questions',
              'La caméra, pour détecter les chutes',
              'Vos données, pour alerter vos proches en cas d\'urgence',
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-xl"
                style={{ background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.15)' }}>
                <CheckCircle size={16} style={{ color: 'var(--green)', flexShrink: 0, marginTop: 1 }} />
                <span className="text-sm" style={{ color: 'var(--text2)' }}>{item}</span>
              </div>
            ))}
          </div>

          <button onClick={handleConsent} disabled={consentLoading}
            className="btn-primary w-full py-4 text-lg font-bold flex items-center justify-center gap-3 mb-4">
            {consentLoading
              ? <><Loader2 size={20} className="animate-spin" /> Enregistrement...</>
              : <><CheckCircle size={20} /> J'accepte</>}
          </button>

          <button onClick={handleLogout}
            className="flex items-center justify-center gap-2 mx-auto text-sm transition-colors"
            style={{ color: 'var(--muted)' }}>
            <LogOut size={14} />
            Se déconnecter
          </button>
        </div>
      </div>
    )
  }

  // ── Normal home ───────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="fixed inset-0 pointer-events-none overflow-hidden" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <img src="/logo.png" alt="logo" style={{ width: 400, height: 400 }} className="object-contain mx-auto mb-4" />
          <h1 className="text-3xl font-bold" style={{ color: 'var(--text)' }}>
            {greeting}{firstName ? `, ${firstName}` : ''}
          </h1>
          <p className="text-base mt-2" style={{ color: 'var(--text2)' }}>
            {new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
          {/* Léa is listening indicator */}
          <p className="text-xs mt-2 flex items-center justify-center gap-1.5"
            style={{ color: 'var(--green)' }}>
            <span className="w-1.5 h-1.5 rounded-full inline-block animate-pulse" style={{ background: 'var(--green)' }} />
            Léa vous écoute — dites "Bonjour Léa"
          </p>
        </div>

        {/* Wellness check */}
        <div className="glass rounded-2xl p-5 mb-6 text-center"
          style={{ border: '1px solid rgba(16,185,129,0.15)' }}>
          <Heart size={20} className="mx-auto mb-2" style={{ color: 'var(--green)' }} />
          <p className="text-sm font-medium mb-1" style={{ color: 'var(--text)' }}>Comment vous sentez-vous ?</p>
          <div className="flex justify-center gap-3 mt-3">
            {['Bien', 'Moyen', 'Pas bien'].map((s, i) => (
              <button key={s} onClick={() => navigate('/voice')}
                className="px-4 py-2 rounded-xl text-sm font-medium transition-all"
                style={{
                  background: i === 0 ? 'rgba(16,185,129,0.15)' : i === 1 ? 'rgba(245,158,11,0.1)' : 'rgba(239,68,68,0.1)',
                  border: `1px solid ${i === 0 ? 'rgba(16,185,129,0.3)' : i === 1 ? 'rgba(245,158,11,0.2)' : 'rgba(239,68,68,0.2)'}`,
                  color: i === 0 ? 'var(--green)' : i === 1 ? 'var(--warn)' : 'var(--danger)',
                }}>
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Main actions */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {actions.map(({ label, desc, path, Icon, color, bg, border }) => (
            <button key={path} onClick={() => navigate(path)}
              className="flex flex-col items-start p-5 rounded-2xl transition-all text-left"
              style={{ background: bg, border: `1px solid ${border}` }}
              onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
              onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
              <Icon size={22} style={{ color, marginBottom: 12 }} />
              <p className="text-sm font-bold leading-snug" style={{ color: 'var(--text)' }}>{label}</p>
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{desc}</p>
            </button>
          ))}
        </div>

        {/* Emergency */}
        <button onClick={handleEmergency}
          disabled={emergencyState !== 'idle'}
          className="w-full py-4 rounded-2xl text-base font-bold mb-6 transition-all flex items-center justify-center gap-3"
          style={{
            background: emergencyState === 'sent' ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.1)',
            border: `1px solid ${emergencyState === 'sent' ? 'rgba(34,197,94,0.35)' : 'rgba(239,68,68,0.3)'}`,
            color: emergencyState === 'sent' ? 'var(--ok)' : '#f87171',
            cursor: emergencyState !== 'idle' ? 'default' : 'pointer',
          }}>
          {emergencyState === 'sending' && <Loader2 size={18} className="animate-spin" />}
          {emergencyState === 'sent' && <CheckCircle size={18} />}
          {emergencyState === 'idle' && <Phone size={18} />}
          {emergencyState === 'sent' ? 'Alerte envoyée — aide en route' : emergencyState === 'sending' ? 'Envoi en cours...' : 'Urgence — Appeler à l\'aide'}
        </button>

        <button onClick={handleLogout}
          className="flex items-center justify-center gap-2 mx-auto text-sm transition-colors"
          style={{ color: 'var(--muted)' }}>
          <LogOut size={15} />
          Déconnexion
        </button>
      </div>
    </div>
  )
}
