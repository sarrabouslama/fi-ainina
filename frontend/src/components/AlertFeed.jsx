import { useState } from 'react'
import axios from 'axios'
import { AlertTriangle, Frown, Clock, CheckCircle, Info, Check, Loader2 } from 'lucide-react'

const getConfig = (event_type, person_status) => {
  if (person_status === 'needs_help' || event_type === 'fall_detected')
    return { color: 'var(--danger)', bg: 'rgba(185,28,28,0.07)', Icon: AlertTriangle, label: 'Urgence' }
  if (event_type === 'emotion_distress')
    return { color: 'var(--warn)', bg: 'rgba(180,83,9,0.07)', Icon: Frown, label: 'Détresse' }
  if (event_type === 'inactivity_detected')
    return { color: 'var(--violet)', bg: 'rgba(90,62,138,0.07)', Icon: Clock, label: 'Inactivité' }
  if (person_status === 'okay')
    return { color: 'var(--ok)', bg: 'rgba(30,107,46,0.07)', Icon: CheckCircle, label: 'OK' }
  return { color: 'var(--muted)', bg: 'rgba(94,138,94,0.07)', Icon: Info, label: 'Info' }
}

function AlertItem({ a, index, onResolve }) {
  const [resolving, setResolving] = useState(false)
  const [resolved, setResolved] = useState(a.status === 'resolved')

  const cfg = getConfig(a.event_type, a.person_status)
  const time = a._ts ? new Date(a._ts) : null
  const canResolve = onResolve && a.alert_id && !resolved

  const handleResolve = async () => {
    setResolving(true)
    try {
      await axios.patch(`http://127.0.0.1:8000/alerts/${a.alert_id}/resolve`)
      setResolved(true)
      onResolve()
    } catch {
      setResolving(false)
    }
  }

  return (
    <div
      className="rounded-xl p-4 animate-fade-up transition-all"
      style={{
        background: resolved ? 'rgba(30,107,46,0.05)' : cfg.bg,
        border: `1px solid ${resolved ? 'rgba(30,107,46,0.2)' : cfg.color + '25'}`,
        animationDelay: `${index * 0.05}s`,
        opacity: resolved ? 0.7 : 1,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <cfg.Icon size={16} style={{ color: resolved ? 'var(--ok)' : cfg.color, flexShrink: 0, marginTop: 2 }} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="font-semibold text-sm" style={{ color: 'var(--text)' }}>
                {a.event_type === 'fall_detected' ? 'Chute détectée' :
                 a.event_type === 'emotion_distress' ? 'Détresse émotionnelle' :
                 a.event_type === 'inactivity_detected' ? 'Inactivité détectée' :
                 a.event_type || 'Alerte'}
              </span>
              <span style={{
                background: resolved ? 'rgba(30,107,46,0.12)' : `${cfg.color}12`,
                color: resolved ? 'var(--ok)' : cfg.color,
                border: `1px solid ${resolved ? 'rgba(30,107,46,0.25)' : cfg.color + '25'}`,
                padding: '2px 8px', borderRadius: '20px',
                fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em'
              }}>
                {resolved ? 'Résolu' : cfg.label}
              </span>
            </div>
            {a.response_text && (
              <p className="text-xs mb-1 italic" style={{ color: 'var(--text2)' }}>
                "{a.response_text}"
              </p>
            )}
            {a.message_for_family && (
              <p className="text-xs" style={{ color: 'var(--muted)' }}>{a.message_for_family}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0 mt-0.5">
          {time && (
            <span className="text-xs" style={{ color: 'var(--muted)' }}>
              {time.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          {canResolve && (
            <button
              onClick={handleResolve}
              disabled={resolving}
              title="Marquer comme résolu"
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: 'rgba(30,107,46,0.1)',
                border: '1px solid rgba(30,107,46,0.25)',
                color: 'var(--ok)',
                cursor: resolving ? 'default' : 'pointer',
                opacity: resolving ? 0.6 : 1,
              }}
            >
              {resolving
                ? <Loader2 size={11} className="animate-spin" />
                : <Check size={11} />}
              {resolving ? '' : 'Résolu'}
            </button>
          )}
          {resolved && !canResolve && (
            <span className="flex items-center gap-1 text-xs font-semibold" style={{ color: 'var(--ok)' }}>
              <CheckCircle size={11} /> Résolu
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AlertFeed({ alerts, maxHeight = '320px', onResolve }) {
  if (!alerts.length) {
    return (
      <div className="text-center py-10 rounded-2xl" style={{ background: 'rgba(255,255,255,0.5)', border: '1px solid rgba(45,120,45,0.1)' }}>
        <CheckCircle size={28} className="mx-auto mb-2" style={{ color: 'var(--ok)', opacity: 0.5 }} />
        <p className="text-sm font-medium" style={{ color: 'var(--text2)' }}>Tout est calme</p>
        <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Aucune alerte pour le moment</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight }}>
      {alerts.map((a, i) => (
        <AlertItem key={a.alert_id ?? i} a={a} index={i} onResolve={onResolve} />
      ))}
    </div>
  )
}
