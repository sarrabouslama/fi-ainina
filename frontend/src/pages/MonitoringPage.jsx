import { useEffect, useState } from 'react'
import axios from 'axios'
import { Video, Smile, Camera, WifiOff, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const FEED_URLS = {
  fall:    'http://127.0.0.1:8003/video_feed',
  emotion: 'http://127.0.0.1:8004/video_feed',
}

// ─── Elderly view: they control their own camera ───────────────────────────
function ElderlyMonitoring() {
  const [activeCamera, setActiveCamera] = useState(null)
  const [cameraLoading, setCameraLoading] = useState(false)
  const [cameraError, setCameraError] = useState(null)
  const [feedError, setFeedError] = useState(false)

  const toggleCamera = async (on) => {
    setCameraLoading(true)
    setCameraError(null)
    try {
      if (on) {
        await Promise.all([
          axios.post('http://127.0.0.1:8003/camera/start', {}, { timeout: 5000 }),
          axios.post('http://127.0.0.1:8004/camera/start', {}, { timeout: 5000 }),
        ])
        setActiveCamera('both')
      } else {
        await Promise.allSettled([
          axios.post('http://127.0.0.1:8003/camera/stop', {}, { timeout: 3000 }),
          axios.post('http://127.0.0.1:8004/camera/stop', {}, { timeout: 3000 }),
        ])
        setActiveCamera(null)
        setFeedError(false)
      }
    } catch {
      setCameraError('Impossible d\'accéder à la caméra. Vérifiez la connexion.')
    } finally {
      setCameraLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl font-bold mb-1" style={{ color: 'var(--text)' }}>
          Ma Surveillance
        </h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          Contrôlez votre caméra de surveillance à tout moment
        </p>
      </div>

      <div className="glass rounded-2xl p-6 mb-5 animate-fade-up">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: activeCamera ? 'rgba(239,68,68,0.1)' : 'rgba(30,107,46,0.1)' }}>
            {activeCamera ? <Eye size={20} style={{ color: 'var(--danger)' }} /> : <EyeOff size={20} style={{ color: 'var(--ok)' }} />}
          </div>
          <div>
            <p className="font-semibold" style={{ color: 'var(--text)' }}>
              Surveillance {activeCamera ? 'activée' : 'désactivée'}
            </p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              {activeCamera
                ? 'Détection de chute + reconnaissance d\'émotion actives'
                : 'Aucune surveillance active — vous êtes seul(e)'}
            </p>
          </div>
        </div>

        {cameraError && (
          <div className="mb-4 px-3 py-2 rounded-xl text-xs"
            style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--danger)' }}>
            {cameraError}
          </div>
        )}

        <div className="flex gap-3">
          <button
            disabled={cameraLoading || !!activeCamera}
            onClick={() => toggleCamera(true)}
            className="flex-1 py-3 rounded-xl font-semibold text-sm transition-all"
            style={{
              background: activeCamera ? 'rgba(30,107,46,0.08)' : 'var(--green)',
              color: activeCamera ? 'var(--muted)' : '#fff',
              opacity: cameraLoading ? 0.6 : 1,
              cursor: activeCamera ? 'default' : 'pointer',
            }}>
            Activer la surveillance
          </button>
          <button
            disabled={cameraLoading || !activeCamera}
            onClick={() => toggleCamera(false)}
            className="flex-1 py-3 rounded-xl font-semibold text-sm transition-all"
            style={{
              background: !activeCamera ? 'rgba(239,68,68,0.05)' : 'rgba(239,68,68,0.1)',
              color: !activeCamera ? 'var(--muted)' : 'var(--danger)',
              border: `1px solid ${!activeCamera ? 'rgba(239,68,68,0.1)' : 'rgba(239,68,68,0.3)'}`,
              opacity: cameraLoading ? 0.6 : 1,
              cursor: !activeCamera ? 'default' : 'pointer',
            }}>
            Désactiver
          </button>
        </div>
      </div>

      {/* Live camera feeds */}
      {activeCamera && (
        <div className="glass rounded-2xl overflow-hidden mb-5 animate-fade-up">
          <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: 'rgba(45,120,45,0.12)' }}>
            <span className="w-2 h-2 rounded-full animate-pulse flex-shrink-0" style={{ background: 'var(--danger)' }} />
            <p className="text-xs font-semibold" style={{ color: 'var(--text)' }}>Flux caméra en direct</p>
          </div>
          <div className="grid grid-cols-2" style={{ background: '#000' }}>
            {/* Fall detection feed */}
            <div style={{ position: 'relative', borderRight: '1px solid #222' }}>
              <p className="text-xs font-semibold px-2 py-1 absolute top-0 left-0 z-10"
                style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>
                Détection chute
              </p>
              <img src={FEED_URLS.fall} alt="Chute"
                onError={e => e.currentTarget.style.display = 'none'}
                style={{ width: '100%', display: 'block', minHeight: 180 }} />
            </div>
            {/* Emotion detection feed */}
            <div style={{ position: 'relative' }}>
              <p className="text-xs font-semibold px-2 py-1 absolute top-0 left-0 z-10"
                style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>
                Émotion
              </p>
              <img src={FEED_URLS.emotion} alt="Émotion"
                onError={e => e.currentTarget.style.display = 'none'}
                style={{ width: '100%', display: 'block', minHeight: 180 }} />
            </div>
          </div>
        </div>
      )}

      <div className="glass rounded-2xl p-5 animate-fade-up delay-100">
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          <span className="font-semibold" style={{ color: 'var(--text2)' }}>Confidentialité</span> —
          Vous pouvez désactiver la caméra à tout moment. Vos données de surveillance restent locales
          et ne sont jamais transmises à l'extérieur, conformément au RGPD.
        </p>
      </div>
    </div>
  )
}

// ─── Admin / Caregiver view: read-only status of the elderly's monitoring ──
function StaffMonitoring() {
  const { user } = useAuth()
  const [fallEvents, setFallEvents] = useState([])
  const [fallStatus, setFallStatus] = useState(null)
  const [feedError, setFeedError] = useState(false)
  const [showFeed, setShowFeed] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const [s, e] = await Promise.all([
          axios.get('http://localhost:8003/status', { timeout: 2000 }),
          axios.get('http://localhost:8003/events?limit=20', { timeout: 2000 }),
        ])
        setFallStatus(s.data)
        setFallEvents(e.data?.events || [])
      } catch {}
    }
    load()
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [])

  const fallState = fallStatus?.state || 'INCONNU'
  const isFallen = fallStatus?.is_fallen
  const stateColors = { STABLE: 'var(--ok)', FALLING: 'var(--warn)', FALLEN: 'var(--danger)', ALERT: '#dc2626' }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl font-bold mb-1" style={{ color: 'var(--text)' }}>
          Surveillance en temps réel
        </h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          État de la détection de chute du résident · Lecture seule
        </p>
      </div>

      {/* Current state banner */}
      <div className="glass rounded-2xl p-5 mb-5 animate-fade-up">
        {fallStatus ? (
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: `${stateColors[fallState] || 'var(--muted)'}15`, border: `2px solid ${stateColors[fallState] || 'var(--muted)'}40` }}>
              <span className="text-xl">{fallState === 'STABLE' ? '✓' : fallState === 'ALERT' ? '!' : '▲'}</span>
            </div>
            <div className="flex-1">
              <p className="font-display font-bold text-xl" style={{ color: stateColors[fallState] || 'var(--text)' }}>
                {fallState}
              </p>
              <p className="text-sm" style={{ color: 'var(--muted)' }}>
                {isFallen
                  ? `Le résident est au sol depuis ${Math.round(fallStatus.fall_duration_seconds || 0)}s`
                  : fallState === 'STABLE' ? 'Le résident va bien — aucune chute détectée' : 'Mouvement rapide détecté'}
              </p>
            </div>
            {isFallen && user?.role === 'admin' && (
              <button onClick={async () => { try { await axios.post('http://localhost:8003/reset') } catch {} }}
                className="btn-secondary text-sm px-4 py-2">
                Réinitialiser
              </button>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <WifiOff size={20} style={{ color: 'var(--muted)' }} />
            <div>
              <p className="font-semibold" style={{ color: 'var(--text2)' }}>Service non disponible</p>
              <p className="text-xs" style={{ color: 'var(--muted)' }}>Le service de détection (port 8003) ne répond pas</p>
            </div>
          </div>
        )}
      </div>

      {/* Live feed toggle for admin */}
      {user?.role === 'admin' && fallStatus && (
        <div className="glass rounded-2xl p-5 mb-5 animate-fade-up">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm" style={{ color: 'var(--text)' }}>Flux vidéo en direct</h3>
            <button onClick={() => { setShowFeed(f => !f); setFeedError(false) }}
              className="text-xs font-medium px-3 py-1.5 rounded-lg transition-all"
              style={{ background: showFeed ? 'rgba(239,68,68,0.1)' : 'rgba(30,107,46,0.1)', color: showFeed ? 'var(--danger)' : 'var(--green)' }}>
              {showFeed ? 'Masquer le flux' : 'Afficher le flux'}
            </button>
          </div>
          {showFeed && (
            <div className="rounded-xl overflow-hidden" style={{ background: '#000', minHeight: 240 }}>
              {feedError ? (
                <div className="flex flex-col items-center justify-center py-10">
                  <WifiOff size={24} className="mb-2" style={{ color: 'var(--muted)', opacity: 0.5 }} />
                  <p className="text-xs" style={{ color: 'var(--muted)' }}>Flux vidéo non disponible</p>
                </div>
              ) : (
                <img src={FEED_URLS.fall} alt="Camera"
                  onError={() => setFeedError(true)} onLoad={() => setFeedError(false)}
                  style={{ maxWidth: '100%', display: 'block', margin: '0 auto' }} />
              )}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-5">
        {/* Fall state machine */}
        <div className="glass rounded-2xl p-5 animate-fade-up">
          <h3 className="font-display font-semibold text-sm mb-4" style={{ color: 'var(--text)' }}>Machine à états</h3>
          {fallStatus ? (
            <div className="flex flex-col gap-3">
              {['STABLE', 'FALLING', 'FALLEN', 'ALERT'].map(state => {
                const active = fallStatus.state === state
                const colors = { STABLE: 'var(--ok)', FALLING: 'var(--warn)', FALLEN: 'var(--danger)', ALERT: '#dc2626' }
                return (
                  <div key={state} className="flex items-center gap-3 p-3 rounded-xl"
                    style={{
                      background: active ? `${colors[state]}12` : 'rgba(255,255,255,0.5)',
                      border: `1px solid ${active ? colors[state] + '40' : 'rgba(45,120,45,0.1)'}`,
                    }}>
                    <div className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ background: active ? colors[state] : 'var(--border2)' }} />
                    <p className="font-bold text-sm flex-1" style={{ color: active ? colors[state] : 'var(--muted)' }}>
                      {state}
                    </p>
                    {active && (
                      <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                        style={{ background: `${colors[state]}20`, color: colors[state] }}>
                        ACTIF
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <WifiOff size={24} className="mx-auto mb-2" style={{ color: 'var(--muted)', opacity: 0.4 }} />
              <p className="text-sm" style={{ color: 'var(--muted)' }}>Service hors ligne</p>
            </div>
          )}
        </div>

        {/* Events */}
        <div className="glass rounded-2xl p-5 animate-fade-up delay-100">
          <h3 className="font-display font-semibold text-sm mb-4" style={{ color: 'var(--text)' }}>
            Événements récents ({fallEvents.length})
          </h3>
          {fallEvents.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm" style={{ color: 'var(--muted)' }}>Aucun événement détecté</p>
              <p className="text-xs mt-1" style={{ color: 'var(--muted)', opacity: 0.7 }}>Le résident va bien</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2 max-h-80 overflow-y-auto">
              {fallEvents.map((e, i) => (
                <div key={i} className="px-3 py-2.5 rounded-xl text-xs"
                  style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(45,120,45,0.12)' }}>
                  <div className="flex justify-between">
                    <span className="font-bold" style={{ color: 'var(--text)' }}>{e.event || e.event_type}</span>
                    <span style={{ color: 'var(--muted)' }}>
                      {e.timestamp ? new Date(e.timestamp * 1000).toLocaleTimeString('fr-FR') : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function MonitoringPage() {
  const { user } = useAuth()
  if (user?.role === 'elderly') return <ElderlyMonitoring />
  return <StaffMonitoring />
}
