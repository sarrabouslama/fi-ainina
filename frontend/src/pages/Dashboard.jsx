import { useEffect, useState } from 'react'
import axios from 'axios'
import { Activity, Heart, AlertTriangle, Users, TrendingUp, Camera } from 'lucide-react'
import StatCard from '../components/StatCard'
import ServiceStatus from '../components/ServiceStatus'
import AlertFeed from '../components/AlertFeed'
import { useAuth } from '../context/AuthContext'

export default function Dashboard({ alerts }) {
  const { user } = useAuth()
  const [fallStatus, setFallStatus] = useState(null)
  const [emotion, setEmotion] = useState(null)
  const [dashData, setDashData] = useState(null)

  useEffect(() => {
    const fetchFall = async () => {
      try { const r = await axios.get('http://localhost:8003/status', { timeout: 2000 }); setFallStatus(r.data) } catch {}
    }
    const fetchEmotion = async () => {
      try { const r = await axios.get('http://localhost:8004/status/emotion', { timeout: 2000 }); setEmotion(r.data) } catch {}
    }
    const fetchDash = async () => {
      try { const r = await axios.get('http://localhost:8000/dashboard/summary', { timeout: 3000 }); setDashData(r.data) } catch {}
    }
    fetchFall(); fetchEmotion(); fetchDash()
    const t = setInterval(() => { fetchFall(); fetchEmotion() }, 3000)
    return () => clearInterval(t)
  }, [])

  const urgentCount = alerts.filter(a => a.action_required === 'emergency' || a.person_status === 'needs_help').length
  const fallState = fallStatus?.state || 'STABLE'
  const isFallen = fallStatus?.is_fallen

  const EMOTION_MAP = {
    happy: { icon: '😊', label: 'Heureux', color: '#fbbf24' },
    sad: { icon: '😢', label: 'Triste', color: '#60a5fa' },
    angry: { icon: '😠', label: 'En colère', color: '#f87171' },
    fear: { icon: '😨', label: 'Peur', color: '#a78bfa' },
    surprise: { icon: '😲', label: 'Surpris', color: '#fb923c' },
    neutral: { icon: '😐', label: 'Neutre', color: 'var(--sage)' },
  }
  const emo = EMOTION_MAP[emotion?.emotion || emotion?.current_emotion]

  return (
    <div className="p-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8 animate-fade-up">
        <p className="text-sm font-medium mb-1" style={{ color: 'var(--muted)' }}>
          {new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
        <h1 className="font-display text-3xl font-bold text-white">
          Bonjour{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''} 👋
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Vue d'ensemble de la surveillance en temps réel
        </p>
      </div>

      {/* Urgent banner */}
      {urgentCount > 0 && (
        <div className="mb-6 p-4 rounded-2xl flex items-center gap-4 animate-slide-down"
          style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
            style={{ background: 'rgba(239,68,68,0.15)' }}>🚨</div>
          <div className="flex-1">
            <p className="font-display font-bold text-white">
              {urgentCount} alerte{urgentCount > 1 ? 's' : ''} urgente{urgentCount > 1 ? 's' : ''} en attente
            </p>
            <p className="text-sm" style={{ color: '#f87171' }}>Intervention immédiate requise</p>
          </div>
          <a href="/alerts" className="btn-secondary text-sm py-2 px-4" style={{ fontSize: 13 }}>
            Voir les alertes
          </a>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard icon="🔔" label="Alertes aujourd'hui" value={alerts.length} sub="Cette session" delay={0} />
        <StatCard icon="🚨" label="Urgences" value={urgentCount} color="var(--danger)" sub="Intervention requise" delay={0.1} />
        <StatCard icon="✅" label="Personnes OK" value={alerts.filter(a => a.person_status === 'okay').length} color="var(--ok)" delay={0.2} />
        <StatCard icon="📹" label="État détection" value={fallState} color={isFallen ? 'var(--danger)' : 'var(--ok)'} sub={isFallen ? `${Math.round(fallStatus?.fall_duration_seconds || 0)}s au sol` : 'Surveillance active'} delay={0.3} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-12 gap-5">
        {/* Left: services + emotion */}
        <div className="col-span-3 flex flex-col gap-4">
          <ServiceStatus />

          {/* Emotion card */}
          <div className="glass rounded-2xl p-5 animate-fade-up delay-400">
            <h3 className="font-display font-semibold text-sm text-white mb-4">Émotion Détectée</h3>
            {emo ? (
              <div className="text-center">
                <div className="text-5xl mb-2 animate-float">{emo.icon}</div>
                <p className="font-display font-bold text-lg" style={{ color: emo.color }}>{emo.label}</p>
                {emotion?.confidence && (
                  <div className="mt-3">
                    <div className="h-1 rounded-full" style={{ background: 'var(--surface2)' }}>
                      <div className="h-1 rounded-full transition-all duration-500"
                        style={{ width: `${Math.round(emotion.confidence * 100)}%`, background: emo.color }} />
                    </div>
                    <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
                      {Math.round(emotion.confidence * 100)}% confiance
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-2xl mb-1">👁️</p>
                <p className="text-xs" style={{ color: 'var(--muted)' }}>Caméra inactive</p>
              </div>
            )}
          </div>
        </div>

        {/* Center: fall status + live feed */}
        <div className="col-span-5 flex flex-col gap-4">
          {/* Fall status */}
          <div className="glass rounded-2xl p-5 animate-fade-up delay-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-semibold text-sm text-white">Détection de Chute</h3>
              <Camera size={15} style={{ color: 'var(--muted)' }} />
            </div>
            {fallStatus ? (
              <div>
                <div className="flex items-center gap-3 p-4 rounded-xl mb-3"
                  style={{
                    background: isFallen ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.08)',
                    border: `1px solid ${isFallen ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.2)'}`
                  }}>
                  <span className="text-2xl">{isFallen ? '🚨' : '🟢'}</span>
                  <div>
                    <p className="font-bold text-white">{fallStatus.state}</p>
                    <p className="text-xs" style={{ color: 'var(--muted)' }}>
                      {isFallen ? `Au sol depuis ${Math.round(fallStatus.fall_duration_seconds || 0)}s` : 'Personne debout — normal'}
                    </p>
                  </div>
                </div>
                {isFallen && (
                  <button onClick={async () => { try { await axios.post('http://localhost:8003/reset') } catch {} }}
                    className="btn-secondary w-full text-sm py-2">
                    ↺ Réinitialiser (fausse alerte)
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-2xl mb-1">📷</p>
                <p className="text-xs" style={{ color: 'var(--muted)' }}>Service non disponible</p>
              </div>
            )}
          </div>

          {/* Recent alerts */}
          <div className="glass rounded-2xl p-5 flex-1 animate-fade-up delay-300">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-semibold text-sm text-white">Alertes récentes</h3>
              <a href="/alerts" className="text-xs font-medium transition-colors"
                style={{ color: 'var(--green-light)' }}>Voir tout →</a>
            </div>
            <AlertFeed alerts={alerts.slice(0, 5)} maxHeight="260px" />
          </div>
        </div>

        {/* Right: quick actions */}
        <div className="col-span-4 flex flex-col gap-4">
          <div className="glass rounded-2xl p-5 animate-fade-up delay-200">
            <h3 className="font-display font-semibold text-sm text-white mb-4">Actions rapides</h3>
            <div className="flex flex-col gap-2">
              {[
                { label: '🎙️ Parler à Léa', path: '/voice', color: 'var(--green)' },
                { label: '🔔 Historique alertes', path: '/alerts', color: 'var(--warn)' },
                { label: '📊 Surveillance', path: '/monitoring', color: '#a78bfa' },
                { label: '💬 Conversations', path: '/conversations', color: 'var(--sage)' },
              ].map(a => (
                <a key={a.path} href={a.path}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-medium"
                  style={{ background: 'rgba(7,43,14,0.5)', border: '1px solid var(--border)', color: 'var(--text2)' }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = a.color + '50'
                    e.currentTarget.style.color = 'var(--text)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'var(--border)'
                    e.currentTarget.style.color = 'var(--text2)'
                  }}>
                  {a.label}
                </a>
              ))}
            </div>
          </div>

          {/* System info */}
          <div className="glass rounded-2xl p-5 animate-fade-up delay-400">
            <h3 className="font-display font-semibold text-sm text-white mb-4">Système</h3>
            <div className="flex flex-col gap-2">
              {[
                { label: 'Architecture', value: 'Microservices' },
                { label: 'Surveillance', value: '24/7 Active' },
                { label: 'Chiffrement', value: 'Local — RGPD' },
                { label: 'Version', value: 'v2.0.0' },
              ].map(item => (
                <div key={item.label} className="flex justify-between items-center py-1.5">
                  <span className="text-xs" style={{ color: 'var(--muted)' }}>{item.label}</span>
                  <span className="text-xs font-medium" style={{ color: 'var(--text2)' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
