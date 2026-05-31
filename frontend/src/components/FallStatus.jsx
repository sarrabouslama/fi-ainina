import { useEffect, useState } from 'react'
import axios from 'axios'

const STATE_CONFIG = {
  STABLE: { label: 'Stable', icon: '🟢', color: 'var(--ok)', bg: 'rgba(16,185,129,0.08)' },
  FALLING: { label: 'Chute en cours...', icon: '⚠️', color: 'var(--warn)', bg: 'rgba(245,158,11,0.08)' },
  FALLEN: { label: 'Chute détectée', icon: '🚨', color: 'var(--danger)', bg: 'rgba(239,68,68,0.1)' },
  ALERT: { label: 'ALERTE URGENTE', icon: '🆘', color: '#dc2626', bg: 'rgba(220,38,38,0.15)' },
}

export default function FallStatus() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await axios.get('http://localhost:8003/status', { timeout: 2000 })
        setStatus(res.data)
      } catch {
        setStatus(null)
      } finally {
        setLoading(false)
      }
    }
    fetch()
    const interval = setInterval(fetch, 2000)
    return () => clearInterval(interval)
  }, [])

  const handleReset = async () => {
    try {
      await axios.post('http://localhost:8003/reset')
      setStatus(prev => prev ? { ...prev, state: 'STABLE', is_fallen: false } : prev)
    } catch {}
  }

  const cfg = STATUS_CONFIG[status?.state] || STATE_CONFIG['STABLE']

  return (
    <div className="rounded-2xl p-5"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <h2 className="font-display font-bold text-base text-white mb-4">📹 Détection de Chute</h2>

      {loading ? (
        <p className="text-sm text-center py-6" style={{ color: 'var(--muted)' }}>Connexion...</p>
      ) : !status ? (
        <div className="text-center py-6 rounded-xl" style={{ background: 'var(--surface2)' }}>
          <p className="text-2xl mb-1">📷</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>Service non disponible</p>
        </div>
      ) : (
        <>
          <div className="rounded-xl p-4 mb-3 text-center"
            style={{ background: cfg.bg, border: `1px solid ${cfg.color}` }}>
            <p className="text-3xl mb-1">{cfg.icon}</p>
            <p className="font-display font-bold text-lg" style={{ color: cfg.color }}>
              {cfg.label}
            </p>
            {status.fall_duration_seconds && (
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
                Durée: {Math.round(status.fall_duration_seconds)}s
              </p>
            )}
          </div>

          {status.is_fallen && (
            <button
              onClick={handleReset}
              className="w-full py-2.5 rounded-xl text-sm font-bold transition-all"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}>
              ↺ Réinitialiser (Fausse alerte)
            </button>
          )}
        </>
      )}
    </div>
  )
}

const STATUS_CONFIG = STATE_CONFIG
