import { formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'

const getConfig = (event_type, person_status) => {
  if (person_status === 'needs_help' || event_type === 'fall_detected')
    return { color: 'var(--danger)', bg: 'rgba(239,68,68,0.08)', icon: '🚨', label: 'Urgence' }
  if (event_type === 'emotion_distress')
    return { color: 'var(--warn)', bg: 'rgba(245,158,11,0.08)', icon: '😔', label: 'Détresse' }
  if (event_type === 'inactivity_detected')
    return { color: '#a78bfa', bg: 'rgba(167,139,250,0.08)', icon: '😴', label: 'Inactivité' }
  if (person_status === 'okay')
    return { color: 'var(--ok)', bg: 'rgba(34,197,94,0.08)', icon: '✅', label: 'OK' }
  return { color: 'var(--muted)', bg: 'rgba(107,147,115,0.08)', icon: '📋', label: 'Info' }
}

export default function AlertFeed({ alerts, maxHeight = '320px' }) {
  if (!alerts.length) {
    return (
      <div className="text-center py-12 rounded-2xl" style={{ background: 'rgba(7,43,14,0.3)' }}>
        <p className="text-3xl mb-2">🌿</p>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>Tout est calme</p>
        <p className="text-xs mt-1" style={{ color: 'var(--border2)' }}>Aucune alerte pour le moment</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight }}>
      {alerts.map((a, i) => {
        const cfg = getConfig(a.event_type, a.person_status)
        const time = a._ts ? new Date(a._ts) : null
        return (
          <div key={i}
            className="rounded-xl p-4 animate-fade-up transition-all"
            style={{ background: cfg.bg, border: `1px solid ${cfg.color}30`, animationDelay: `${i * 0.05}s` }}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <span className="text-xl flex-shrink-0 mt-0.5">{cfg.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-semibold text-sm text-white">
                      {a.event_type === 'fall_detected' ? 'Chute détectée' :
                       a.event_type === 'emotion_distress' ? 'Détresse émotionnelle' :
                       a.event_type === 'inactivity_detected' ? 'Inactivité détectée' :
                       a.event_type || 'Alerte'}
                    </span>
                    <span className="tag" style={{
                      background: `${cfg.color}15`,
                      color: cfg.color,
                      border: `1px solid ${cfg.color}30`,
                      padding: '2px 8px',
                      borderRadius: '20px',
                      fontSize: '10px',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em'
                    }}>
                      {cfg.label}
                    </span>
                  </div>
                  {a.response_text && (
                    <p className="text-xs mb-1 italic" style={{ color: 'var(--text2)' }}>
                      💬 "{a.response_text}"
                    </p>
                  )}
                  {a.message_for_family && (
                    <p className="text-xs" style={{ color: 'var(--muted)' }}>{a.message_for_family}</p>
                  )}
                </div>
              </div>
              {time && (
                <span className="text-xs flex-shrink-0 mt-0.5" style={{ color: 'var(--muted)' }}>
                  {time.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
