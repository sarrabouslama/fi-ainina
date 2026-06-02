import { useEffect, useRef, useState, useCallback } from 'react'
import axios from 'axios'
import { Activity, Smile, WifiOff, Zap, StopCircle, Video } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

// ─── Service config ───────────────────────────────────────────────────────────
const SVC = {
  fall: {
    key: 'fall',
    label: 'Détection de chute',
    icon: Activity,
    color: '#dc2626',
    bg: 'rgba(220,38,38,0.08)',
    border: 'rgba(220,38,38,0.22)',
    port: 8003,
    feedUrl:   'http://127.0.0.1:8003/video_feed',
    startUrl:  'http://127.0.0.1:8003/camera/start',
    stopUrl:   'http://127.0.0.1:8003/camera/stop',
    statusUrl: 'http://127.0.0.1:8003/status',
    resetUrl:  'http://127.0.0.1:8003/reset',
    badge: 'MediaPipe Pose',
  },
  emotion: {
    key: 'emotion',
    label: 'Émotion & Rougeur',
    icon: Smile,
    color: '#16a34a',
    bg: 'rgba(22,163,74,0.08)',
    border: 'rgba(22,163,74,0.22)',
    port: 8004,
    feedUrl:   'http://127.0.0.1:8004/video_feed',
    startUrl:  'http://127.0.0.1:8004/camera/start',
    stopUrl:   'http://127.0.0.1:8004/camera/stop',
    statusUrl: 'http://127.0.0.1:8004/status',
    resetUrl:  null,
    badge: 'DeepFace',
  },
}

const EMOTION_COLORS = {
  happy: '#16a34a', neutral: '#6b7280', sad: '#2563eb',
  angry: '#dc2626', fear: '#9333ea', disgust: '#92400e', surprise: '#d97706',
}

// ─── Live emotion data panel ──────────────────────────────────────────────────
function EmotionData({ status }) {
  if (!status) return null
  const redness = status.redness_level || 'none'
  return (
    <div className="grid grid-cols-3 gap-2 mt-3">
      <div className="rounded-xl p-3" style={{ background: 'rgba(255,255,255,0.55)', border: '1px solid rgba(45,120,45,0.1)' }}>
        <p className="text-xs font-semibold mb-1" style={{ color: 'var(--muted)' }}>Émotion</p>
        <p className="font-bold text-base capitalize" style={{ color: EMOTION_COLORS[status.emotion] || 'var(--text)' }}>
          {status.emotion || '—'}
        </p>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          {status.confidence != null ? `${Math.round(status.confidence * 100)}%` : ''}
        </p>
      </div>
      <div className="rounded-xl p-3" style={{ background: 'rgba(255,255,255,0.55)', border: '1px solid rgba(45,120,45,0.1)' }}>
        <p className="text-xs font-semibold mb-1" style={{ color: 'var(--muted)' }}>Rougeur</p>
        <p className="font-bold text-base" style={{ color: redness === 'high' ? '#dc2626' : redness === 'mild' ? '#f59e0b' : 'var(--ok)' }}>
          {redness === 'none' ? 'Normale' : redness === 'mild' ? 'Légère' : 'Élevée'}
        </p>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          {status.redness_score != null ? `score ${status.redness_score.toFixed(2)}` : ''}
        </p>
      </div>
      <div className="rounded-xl p-3" style={{ background: 'rgba(255,255,255,0.55)', border: '1px solid rgba(45,120,45,0.1)' }}>
        <p className="text-xs font-semibold mb-1" style={{ color: 'var(--muted)' }}>Inactivité</p>
        <p className="font-bold text-base" style={{ color: (status.inactivity_seconds || 0) > 240 ? '#f59e0b' : 'var(--text)' }}>
          {Math.floor((status.inactivity_seconds || 0) / 60)}m {(status.inactivity_seconds || 0) % 60}s
        </p>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>sans mouvement</p>
      </div>
    </div>
  )
}

// ─── Live fall state data ─────────────────────────────────────────────────────
const FALL_COLORS = { STABLE: '#16a34a', FALLING: '#f59e0b', FALLEN: '#dc2626', ALERT: '#dc2626' }
function FallData({ status, onReset, isAdmin }) {
  if (!status) return null
  const state = status.state || 'INCONNU'
  const color = FALL_COLORS[state] || 'var(--muted)'
  return (
    <div className="mt-3 flex items-center gap-3 p-3 rounded-xl"
      style={{ background: `${color}10`, border: `1px solid ${color}30` }}>
      <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}18`, border: `2px solid ${color}40` }}>
        <span style={{ color, fontSize: 14 }}>{state === 'STABLE' ? '✓' : '!'}</span>
      </div>
      <div className="flex-1">
        <p className="font-bold text-sm" style={{ color }}>{state}</p>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          {status.is_fallen ? `Au sol depuis ${Math.round(status.fall_duration_seconds || 0)}s` : 'Aucune chute détectée'}
        </p>
      </div>
      {status.is_fallen && isAdmin && (
        <button onClick={onReset}
          className="text-xs px-3 py-1.5 rounded-lg font-semibold"
          style={{ background: 'rgba(220,38,38,0.1)', color: '#dc2626' }}>
          Reset
        </button>
      )}
    </div>
  )
}

// ─── Single camera card ───────────────────────────────────────────────────────
function CameraCard({ svcKey, active, onActivate, onStop, loading, serviceOnline, statusData, isAdmin }) {
  const svc = SVC[svcKey]
  const Icon = svc.icon
  const [feedOk, setFeedOk] = useState(false)

  // Reset feed state when activation changes
  useEffect(() => { if (!active) setFeedOk(false) }, [active])

  const resetFall = async () => {
    try { await axios.post(svc.resetUrl, {}, { timeout: 3000 }) } catch {}
  }

  return (
    <div className="glass rounded-2xl overflow-hidden animate-fade-up flex flex-col"
      style={{ border: active ? `1.5px solid ${svc.border}` : undefined }}>

      {/* Card header */}
      <div className="flex items-center gap-3 px-5 py-4"
        style={{ borderBottom: `1px solid ${active ? svc.border : 'rgba(45,120,45,0.08)'}`, background: active ? svc.bg : 'transparent' }}>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: active ? svc.bg : 'rgba(0,0,0,0.04)', border: `1px solid ${active ? svc.border : 'rgba(0,0,0,0.06)'}` }}>
          <Icon size={18} style={{ color: active ? svc.color : 'var(--muted)' }} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <p className="font-display font-bold text-sm" style={{ color: active ? svc.color : 'var(--text)' }}>
              {svc.label}
            </p>
            {active && feedOk && (
              <span className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(220,38,38,0.1)', color: '#dc2626' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                EN DIRECT
              </span>
            )}
          </div>
          <p className="text-xs" style={{ color: 'var(--muted)' }}>
            {serviceOnline ? `Service actif · port ${svc.port} · ${svc.badge}` : `Service hors ligne · port ${svc.port}`}
          </p>
        </div>

        {/* Action button */}
        {!active ? (
          <button
            disabled={loading || !serviceOnline}
            onClick={onActivate}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all"
            style={{
              background: serviceOnline ? svc.color : 'rgba(0,0,0,0.06)',
              color: serviceOnline ? '#fff' : 'var(--muted)',
              opacity: loading ? 0.6 : 1,
              cursor: serviceOnline ? 'pointer' : 'not-allowed',
            }}>
            <Video size={14} />
            {loading ? 'Démarrage...' : 'Activer'}
          </button>
        ) : (
          <button
            disabled={loading}
            onClick={onStop}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all"
            style={{ background: 'rgba(220,38,38,0.1)', color: '#dc2626', border: '1px solid rgba(220,38,38,0.2)' }}>
            <StopCircle size={14} />
            Arrêter
          </button>
        )}
      </div>

      {/* Camera feed */}
      <div style={{ background: '#0a0a0a', minHeight: active ? 280 : 80, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'min-height 0.3s ease' }}>
        {active ? (
          <>
            <img
              src={svc.feedUrl}
              alt={svc.label}
              onLoad={() => setFeedOk(true)}
              onError={() => setFeedOk(false)}
              style={{ maxWidth: '100%', maxHeight: 420, display: feedOk ? 'block' : 'none', margin: '0 auto' }}
            />
            {!feedOk && (
              <div className="flex flex-col items-center gap-2 py-8">
                <WifiOff size={22} style={{ color: '#444' }} />
                <p className="text-xs" style={{ color: '#555' }}>Connexion au flux vidéo...</p>
                <p className="text-xs" style={{ color: '#444' }}>port {svc.port}/video_feed</p>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center gap-2 py-5">
            <Icon size={22} style={{ color: '#333' }} />
            <p className="text-xs font-medium" style={{ color: '#444' }}>
              {serviceOnline ? 'Appuyez sur Activer pour démarrer' : `Service non disponible sur le port ${svc.port}`}
            </p>
          </div>
        )}
      </div>

      {/* Live data (shown only when active) */}
      {active && (
        <div className="px-4 pb-4">
          {svcKey === 'emotion'
            ? <EmotionData status={statusData} />
            : <FallData status={statusData} onReset={resetFall} isAdmin={isAdmin} />}
        </div>
      )}
    </div>
  )
}

// ─── Alert test panel ─────────────────────────────────────────────────────────
function AlertTestPanel({ lastAlert }) {
  const [sending, setSending] = useState(null)
  const [result, setResult] = useState(null)

  const fire = async (eventType, label, meta) => {
    setSending(eventType); setResult(null)
    try {
      await axios.post('http://127.0.0.1:8005/alerts/test', {
        event_type: eventType,
        user_id: '00000000-0000-0000-0000-000000000001',
        severity: 'high',
        metadata: meta,
      }, { timeout: 5000 })
      setResult({ ok: true, label })
    } catch (e) {
      setResult({ ok: false, label, error: e?.response?.data?.detail || e.message })
    } finally { setSending(null) }
  }

  return (
    <div className="glass rounded-2xl p-5 animate-fade-up">
      <div className="flex items-center gap-2 mb-4">
        <Zap size={15} style={{ color: '#f59e0b' }} />
        <p className="font-display font-semibold text-sm" style={{ color: 'var(--text)' }}>
          Test pipeline d'alertes
        </p>
        <span className="text-xs px-2 py-0.5 rounded-full ml-auto font-medium"
          style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>
          WebSocket + Email + WhatsApp
        </span>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {[
          { key: 'emotion_distress',         label: 'Émotion détresse', color: '#9333ea', meta: { emotion: 'angry', score: 0.92 } },
          { key: 'extreme_redness_detected', label: 'Rougeur extrême',  color: '#dc2626', meta: { redness_score: 0.48, redness_level: 'high' } },
          { key: 'inactivity_detected',      label: 'Inactivité',       color: '#f59e0b', meta: { duration_seconds: 320 } },
        ].map(({ key, label, color, meta }) => (
          <button key={key} disabled={!!sending} onClick={() => fire(key, label, meta)}
            className="px-4 py-2 rounded-xl text-xs font-semibold transition-all"
            style={{ background: `${color}10`, color, border: `1px solid ${color}25`, opacity: sending && sending !== key ? 0.5 : 1 }}>
            {sending === key ? 'Envoi...' : `▶ ${label}`}
          </button>
        ))}
      </div>

      {result && (
        <div className="px-3 py-2 rounded-xl text-xs font-medium mb-2"
          style={{ background: result.ok ? 'rgba(22,163,74,0.08)' : 'rgba(220,38,38,0.08)', color: result.ok ? '#16a34a' : '#dc2626' }}>
          {result.ok ? `✓ "${result.label}" envoyée — vérifiez la notification + WhatsApp` : `✗ ${result.error}`}
        </div>
      )}

      {lastAlert && (
        <div className="px-3 py-2 rounded-xl text-xs"
          style={{ background: 'rgba(255,255,255,0.5)', border: '1px solid rgba(45,120,45,0.1)' }}>
          <span className="font-semibold" style={{ color: 'var(--text)' }}>Dernière alerte : </span>
          <span style={{ color: 'var(--muted)' }}>
            {lastAlert.event_type} · {lastAlert.severity} · {lastAlert._ts ? new Date(lastAlert._ts).toLocaleTimeString('fr-FR') : ''}
          </span>
        </div>
      )}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function MonitoringPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  // Which camera is active: null | 'fall' | 'emotion'
  const [activeCamera, setActiveCamera] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Service online status
  const [online, setOnline] = useState({ fall: false, emotion: false })

  // Live status data
  const [fallStatus, setFallStatus] = useState(null)
  const [emotionStatus, setEmotionStatus] = useState(null)

  // Alert WebSocket
  const [alertWsConnected, setAlertWsConnected] = useState(false)
  const [lastAlert, setLastAlert] = useState(null)
  const wsRef = useRef(null)

  // Poll both service statuses
  useEffect(() => {
    const poll = async () => {
      // Fall service
      try {
        const r = await axios.get('http://127.0.0.1:8003/status', { timeout: 2000 })
        setFallStatus(r.data)
        setOnline(o => ({ ...o, fall: true }))
      } catch {
        setFallStatus(null)
        setOnline(o => ({ ...o, fall: false }))
      }
      // Emotion service
      try {
        const r = await axios.get('http://127.0.0.1:8004/status', { timeout: 2000 })
        setEmotionStatus(r.data)
        setOnline(o => ({ ...o, emotion: true }))
      } catch {
        setEmotionStatus(null)
        setOnline(o => ({ ...o, emotion: false }))
      }
    }
    poll()
    const t = setInterval(poll, 3000)
    return () => clearInterval(t)
  }, [])

  // Alert WebSocket (port 8005)
  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket('ws://127.0.0.1:8005/ws')
        wsRef.current = ws
        ws.onopen  = () => setAlertWsConnected(true)
        ws.onclose = () => { setAlertWsConnected(false); setTimeout(connect, 4000) }
        ws.onerror = () => setAlertWsConnected(false)
        ws.onmessage = (e) => {
          try { setLastAlert({ ...JSON.parse(e.data), _ts: new Date().toISOString() }) } catch {}
        }
      } catch { setAlertWsConnected(false) }
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  // Activate a camera (stops the other one first)
  const activate = useCallback(async (key) => {
    setLoading(true)
    setError(null)
    try {
      // Stop the other service camera first (they share the physical camera)
      const otherKey = key === 'fall' ? 'emotion' : 'fall'
      if (activeCamera === otherKey) {
        try { await axios.post(SVC[otherKey].stopUrl, {}, { timeout: 3000 }) } catch {}
      }
      // Start the selected service camera
      await axios.post(SVC[key].startUrl, {}, { timeout: 6000 })
      setActiveCamera(key)
    } catch {
      setError(`Impossible de démarrer la caméra — service port ${SVC[key].port} non disponible.`)
    } finally {
      setLoading(false)
    }
  }, [activeCamera])

  // Stop current camera
  const stop = useCallback(async (key) => {
    setLoading(true)
    try { await axios.post(SVC[key].stopUrl, {}, { timeout: 3000 }) } catch {}
    setActiveCamera(null)
    setLoading(false)
  }, [])

  return (
    <div className="p-6 max-w-5xl mx-auto flex flex-col gap-5">

      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="font-display text-2xl font-bold mb-0.5" style={{ color: 'var(--text)' }}>
          Surveillance en temps réel
        </h1>
        <div className="flex items-center gap-3">
          <p className="text-sm" style={{ color: 'var(--text2)' }}>
            Activez un mode de détection pour démarrer la caméra
          </p>
          <span className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${alertWsConnected ? '' : 'opacity-60'}`}
            style={{ background: alertWsConnected ? 'rgba(22,163,74,0.08)' : 'rgba(0,0,0,0.05)', color: alertWsConnected ? '#16a34a' : 'var(--muted)' }}>
            <span className={`w-1.5 h-1.5 rounded-full ${alertWsConnected ? 'animate-pulse bg-green-500' : 'bg-gray-400'}`} />
            Alertes {alertWsConnected ? 'connectées' : 'déconnectées'}
          </span>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 py-3 rounded-2xl text-sm"
          style={{ background: 'rgba(220,38,38,0.08)', color: '#dc2626', border: '1px solid rgba(220,38,38,0.15)' }}>
          {error}
        </div>
      )}

      {/* Two camera cards */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <CameraCard
          svcKey="fall"
          active={activeCamera === 'fall'}
          onActivate={() => activate('fall')}
          onStop={() => stop('fall')}
          loading={loading}
          serviceOnline={online.fall}
          statusData={fallStatus}
          isAdmin={isAdmin}
        />
        <CameraCard
          svcKey="emotion"
          active={activeCamera === 'emotion'}
          onActivate={() => activate('emotion')}
          onStop={() => stop('emotion')}
          loading={loading}
          serviceOnline={online.emotion}
          statusData={emotionStatus}
          isAdmin={isAdmin}
        />
      </div>

      {/* Alert test panel */}
      <AlertTestPanel lastAlert={lastAlert} />

    </div>
  )
}
