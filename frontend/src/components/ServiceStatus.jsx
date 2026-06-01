import { useEffect, useState } from 'react'
import axios from 'axios'
import { RefreshCw, Server, Brain, Mic, Video, Smile, Bell } from 'lucide-react'

const SERVICES = [
  { key: 'companion',      name: 'Backend Principal', Icon: Server },
  { key: 'llm',            name: 'LLM / IA',          Icon: Brain  },
  { key: 'voice_assistant',name: 'Service Vocal',      Icon: Mic    },
  { key: 'fall_detection', name: 'Détection Chute',    Icon: Video  },
  { key: 'emotion',        name: 'Émotions',           Icon: Smile  },
  { key: 'alerts',         name: 'Alertes',            Icon: Bell   },
]

export default function ServiceStatus() {
  const [statuses, setStatuses] = useState({})
  const [checking, setChecking] = useState(false)
  const [lastCheck, setLastCheck] = useState(null)

  const check = async () => {
    setChecking(true)
    try {
      const res = await axios.get('http://127.0.0.1:8000/health', { timeout: 3000 })
      const s = res.data?.services || {}
      const mapped = {}
      Object.entries(s).forEach(([k, v]) => { mapped[k] = v === 'healthy' })
      mapped['companion'] = true
      setStatuses(mapped)
    } catch {
      setStatuses({ companion: false })
    }
    setLastCheck(new Date().toLocaleTimeString('fr-FR'))
    setChecking(false)
  }

  useEffect(() => { check(); const t = setInterval(check, 15000); return () => clearInterval(t) }, [])

  const online = Object.values(statuses).filter(Boolean).length

  return (
    <div className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-semibold text-white text-sm">Infrastructure</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: 'var(--muted)' }}>{online}/{SERVICES.length} actifs</span>
          <button onClick={check} className="p-1.5 rounded-lg transition-all"
            style={{ color: 'var(--muted)', background: 'var(--surface2)' }}>
            <RefreshCw size={12} className={checking ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        {SERVICES.map(({ key, name, Icon }) => {
          const up = statuses[key]
          const unknown = statuses[key] === undefined
          return (
            <div key={key} className="flex items-center justify-between py-2 px-3 rounded-xl"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div className="flex items-center gap-2.5">
                <Icon size={13} style={{ color: unknown ? 'var(--muted)' : up ? 'var(--ok)' : 'var(--danger)', flexShrink: 0 }} />
                <span className="text-xs font-medium" style={{ color: 'var(--text2)' }}>{name}</span>
              </div>
              {unknown ? (
                <span className="text-xs" style={{ color: 'var(--muted)' }}>—</span>
              ) : (
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: up ? 'var(--ok)' : 'var(--danger)' }} />
                  <span className="text-xs font-medium" style={{ color: up ? 'var(--ok)' : 'var(--danger)' }}>
                    {up ? 'actif' : 'inactif'}
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {lastCheck && (
        <p className="text-xs mt-3" style={{ color: 'var(--muted)' }}>Vérification: {lastCheck}</p>
      )}
    </div>
  )
}
