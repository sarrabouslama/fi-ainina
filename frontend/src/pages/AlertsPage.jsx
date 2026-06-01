import AlertFeed from '../components/AlertFeed'

export default function AlertsPage({ alerts, onResolveAlert }) {
  const emergency = alerts.filter(a => a.status !== 'resolved' && (a.action_required === 'emergency' || a.person_status === 'needs_help'))
  const verify = alerts.filter(a => a.action_required === 'verify' || a.person_status === 'unclear')
  const info = alerts.filter(a => a.action_required === 'notify_only' || a.person_status === 'okay')

  const TABS = [
    { key: 'all', label: 'Toutes', count: alerts.length, data: alerts, color: 'var(--green)' },
    { key: 'emergency', label: 'Urgences', count: emergency.length, data: emergency, color: 'var(--danger)' },
    { key: 'verify', label: 'À vérifier', count: verify.length, data: verify, color: 'var(--warn)' },
    { key: 'info', label: 'Info', count: info.length, data: info, color: 'var(--ok)' },
  ]

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Alertes & Événements</h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          Historique en temps réel via WebSocket · Alert Service (port 8005)
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {TABS.map((t, i) => (
          <div key={t.key} className="glass rounded-2xl p-4 text-center animate-fade-up"
            style={{ animationDelay: `${i * 0.08}s` }}>
            <p className="font-display font-bold text-2xl text-white mb-0.5">{t.count}</p>
            <p className="text-xs font-medium" style={{ color: t.color }}>{t.label}</p>
          </div>
        ))}
      </div>

      {/* Alert sections */}
      {emergency.length > 0 && (
        <div className="glass rounded-2xl p-5 mb-4 animate-fade-up">
          <h3 className="font-display font-semibold text-sm mb-3 flex items-center gap-2"
            style={{ color: 'var(--danger)' }}>
            🚨 Urgences ({emergency.length})
          </h3>
          <AlertFeed alerts={emergency} maxHeight="none" onResolve={onResolveAlert} />
        </div>
      )}

      <div className="glass rounded-2xl p-5 animate-fade-up delay-200">
        <h3 className="font-display font-semibold text-sm text-white mb-3">
          Toutes les alertes ({alerts.length})
        </h3>
        <AlertFeed alerts={alerts} maxHeight="500px" onResolve={onResolveAlert} />
      </div>
    </div>
  )
}
