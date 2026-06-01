import { useEffect, useState } from 'react'
import axios from 'axios'

export default function MonitoringPage() {
  const [fallEvents, setFallEvents] = useState([])
  const [fallStatus, setFallStatus] = useState(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const [s, e] = await Promise.all([
          axios.get('http://localhost:8003/status', { timeout: 2000 }),
          axios.get('http://localhost:8003/events?limit=20', { timeout: 2000 }),
        ])
        setFallStatus(s.data)
        setFallEvents(e.data?.events || [])
      } catch {}
    }
    fetch()
    const t = setInterval(fetch, 3000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Surveillance Temps Réel</h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          Fall Detection Service · Emotion Service · Computer Vision
        </p>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Fall state machine */}
        <div className="glass rounded-2xl p-5 animate-fade-up">
          <h3 className="font-display font-semibold text-sm text-white mb-4">État machine à chute</h3>
          {fallStatus ? (
            <div className="flex flex-col gap-3">
              {['STABLE', 'FALLING', 'FALLEN', 'ALERT'].map(state => {
                const active = fallStatus.state === state
                const colors = {
                  STABLE: 'var(--ok)',
                  FALLING: 'var(--warn)',
                  FALLEN: 'var(--danger)',
                  ALERT: '#dc2626',
                }
                const icons = { STABLE: '●', FALLING: '▲', FALLEN: '■', ALERT: '!' }
                return (
                  <div key={state} className="flex items-center gap-3 p-3 rounded-xl transition-all"
                    style={{
                      background: active ? `${colors[state]}15` : 'rgba(7,43,14,0.3)',
                      border: `1px solid ${active ? colors[state] + '40' : 'var(--border)'}`,
                    }}>
                    <span className="text-lg">{icons[state]}</span>
                    <div className="flex-1">
                      <p className="font-bold text-sm" style={{ color: active ? colors[state] : 'var(--muted)' }}>
                        {state}
                      </p>
                    </div>
                    {active && (
                      <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                        style={{ background: `${colors[state]}20`, color: colors[state] }}>
                        ACTUEL
                      </span>
                    )}
                  </div>
                )
              })}
              {fallStatus.is_fallen && (
                <button onClick={async () => { try { await axios.post('http://localhost:8003/reset') } catch {} }}
                  className="btn-secondary text-sm py-2 mt-1">
                  ↺ Réinitialiser
                </button>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-sm" style={{ color: 'var(--muted)' }}>Service non disponible</p>
            </div>
          )}
        </div>

        {/* Recent fall events */}
        <div className="glass rounded-2xl p-5 animate-fade-up delay-100">
          <h3 className="font-display font-semibold text-sm text-white mb-4">
            Événements récents ({fallEvents.length})
          </h3>
          {fallEvents.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm" style={{ color: 'var(--muted)' }}>Aucun événement</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2 max-h-80 overflow-y-auto">
              {fallEvents.map((e, i) => (
                <div key={i} className="px-3 py-2.5 rounded-xl text-xs"
                  style={{ background: 'rgba(7,43,14,0.5)', border: '1px solid var(--border)' }}>
                  <div className="flex justify-between mb-1">
                    <span className="font-bold text-white">{e.event || e.event_type || 'event'}</span>
                    <span style={{ color: 'var(--muted)' }}>
                      {e.timestamp ? new Date(e.timestamp * 1000).toLocaleTimeString('fr-FR') : ''}
                    </span>
                  </div>
                  {e.details && (
                    <p style={{ color: 'var(--muted)' }}>
                      {JSON.stringify(e.details).slice(0, 60)}...
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
