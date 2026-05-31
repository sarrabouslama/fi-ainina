export default function AlertPanel({ alerts }) {
  const getStyle = (status) => {
    if (status === 'needs_help') return { border: 'var(--danger)', bg: 'rgba(239,68,68,0.08)' }
    if (status === 'okay') return { border: 'var(--ok)', bg: 'rgba(16,185,129,0.08)' }
    if (status === 'no_response') return { border: '#dc2626', bg: 'rgba(220,38,38,0.12)' }
    return { border: 'var(--warn)', bg: 'rgba(245,158,11,0.08)' }
  }

  const getIcon = (status) => {
    if (status === 'needs_help') return '🚨'
    if (status === 'okay') return '✅'
    if (status === 'no_response') return '⛔'
    return '⚠️'
  }

  const getActionBadge = (action) => {
    if (action === 'emergency') return { label: 'URGENCE', color: 'var(--danger)' }
    if (action === 'notify_only') return { label: 'INFO', color: 'var(--ok)' }
    if (action === 'verify') return { label: 'VÉRIFIER', color: 'var(--warn)' }
    return { label: action, color: 'var(--muted)' }
  }

  return (
    <div className="rounded-2xl p-5 flex flex-col gap-3"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between">
        <h2 className="font-display font-bold text-base text-white">🔔 Alertes</h2>
        {alerts.length > 0 && (
          <span className="text-xs px-2 py-1 rounded-full font-bold"
            style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--danger)' }}>
            {alerts.length}
          </span>
        )}
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-10 rounded-xl" style={{ background: 'var(--surface2)' }}>
          <p className="text-2xl mb-2">🌿</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>Aucune alerte</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1">
          {alerts.map((alert, i) => {
            const style = getStyle(alert.person_status || alert.event_type)
            const badge = getActionBadge(alert.action_required)
            return (
              <div key={i} className="rounded-xl p-4 animate-slide-in"
                style={{ background: style.bg, border: `1px solid ${style.border}` }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span>{getIcon(alert.person_status || alert.event_type)}</span>
                    <span className="font-display font-bold text-sm text-white">
                      {alert.event_type === 'fall_detected' ? 'Chute détectée' :
                       alert.event_type === 'emotion_distress' ? 'Détresse émotionnelle' :
                       alert.event_type === 'inactivity_detected' ? 'Inactivité détectée' :
                       alert.event_type}
                    </span>
                  </div>
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full"
                    style={{ background: `${badge.color}22`, color: badge.color }}>
                    {badge.label}
                  </span>
                </div>
                {alert.response_text && (
                  <p className="text-xs mb-1" style={{ color: 'var(--muted)' }}>
                    💬 "{alert.response_text}"
                  </p>
                )}
                {alert.message_for_family && (
                  <p className="text-xs italic" style={{ color: 'var(--muted)' }}>
                    {alert.message_for_family}
                  </p>
                )}
                <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
                  {alert.receivedAt ? new Date(alert.receivedAt).toLocaleTimeString('fr-FR') : ''}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
