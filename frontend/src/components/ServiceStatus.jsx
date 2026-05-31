import { useEffect, useState } from 'react'
import axios from 'axios'
import { Wifi, WifiOff, RefreshCw } from 'lucide-react'

const SERVICES = [
  { key: 'companion', name: 'Backend Principal', url: 'http://localhost:8000/health', icon: '🏠' },
  { key: 'llm', name: 'LLM / IA', url: 'http://localhost:8001/health', icon: '🧠' },
  { key: 'voice', name: 'Service Vocal', url: 'http://localhost:8002/health', icon: '🎙️' },
  { key: 'fall', name: 'Détection Chute', url: 'http://localhost:8003/health', icon: '📹' },
  { key: 'emotion', name: 'Émotions', url: 'http://localhost:8004/health', icon: '😶' },
  { key: 'alerts', name: 'Alertes', url: 'http://localhost:8005/health', icon: '🔔' },
]

export default function ServiceStatus() {
  const [statuses, setStatuses] = useState({})
  const [checking, setChecking] = useState(false)
  const [lastCheck, setLastCheck] = useState(null)

  const check = async () => {
    setChecking(true)
    const res = {}
    await Promise.all(SERVICES.map(async s => {
      try { await axios.get(s.url, { timeout: 2000 }); res[s.key] = true }
      catch { res[s.key] = false }
    }))
    setStatuses(res)
    setLastCheck(new Date().toLocaleTimeString('fr-FR'))
    setChecking(false)
  }

  useEffect(() => { check(); const t = setInterval(check, 15000); return () => clearInterval(t) }, [])

  const online = Object.values(statuses).filter(Boolean).length

  return (
    <div className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-semibold text-white text-sm">Infrastructure</h3>
        <div className="flex items-center gap-3">
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            {online}/{SERVICES.length} actifs
          </span>
          <button onClick={check} className="p-1.5 rounded-lg transition-all"
            style={{ color: 'var(--muted)', background: 'var(--surface2)' }}>
            <RefreshCw size={12} className={checking ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {SERVICES.map(s => {
          const up = statuses[s.key]
          const unknown = statuses[s.key] === undefined
          return (
            <div key={s.key} className="flex items-center justify-between py-1.5 px-3 rounded-xl transition-all"
              style={{ background: 'rgba(7,43,14,0.4)' }}>
              <div className="flex items-center gap-2">
                <span className="text-sm">{s.icon}</span>
                <span className="text-xs font-medium" style={{ color: 'var(--text2)' }}>{s.name}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {unknown ? (
                  <span className="text-xs" style={{ color: 'var(--muted)' }}>—</span>
                ) : up ? (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'var(--ok)' }} />
                    <span className="text-xs font-medium" style={{ color: 'var(--ok)' }}>actif</span>
                  </>
                ) : (
                  <>
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--danger)' }} />
                    <span className="text-xs font-medium" style={{ color: 'var(--danger)' }}>inactif</span>
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {lastCheck && (
        <p className="text-xs mt-3" style={{ color: 'var(--muted)' }}>
          Dernière vérification: {lastCheck}
        </p>
      )}
    </div>
  )
}
