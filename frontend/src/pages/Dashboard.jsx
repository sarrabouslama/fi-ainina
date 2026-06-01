import { useEffect, useState } from 'react'
import axios from 'axios'
import { Link } from 'react-router-dom'
import {
  Activity, AlertTriangle, Bell, Camera, Eye, Heart,
  Mic, Monitor, Smile, Users, Video, ShieldAlert,
  UserCheck, Clock, CheckCircle,
} from 'lucide-react'
import StatCard from '../components/StatCard'
import ServiceStatus from '../components/ServiceStatus'
import AlertFeed from '../components/AlertFeed'
import { useAuth } from '../context/AuthContext'

/* ─── Admin dashboard ──────────────────────────────────────────────── */
function AdminDashboard({ alerts, fallStatus, emotion, overview, onResolveAlert }) {
  const { user } = useAuth()
  const urgentCount = alerts.filter(a => a.status !== 'resolved' && (a.action_required === 'emergency' || a.person_status === 'needs_help')).length
  const fallState = fallStatus?.state || 'STABLE'
  const isFallen = fallStatus?.is_fallen

  const EMOTION_MAP = {
    happy:    { label: 'Heureux',   color: '#fbbf24' },
    sad:      { label: 'Triste',    color: '#60a5fa' },
    angry:    { label: 'En colère', color: '#f87171' },
    fear:     { label: 'Peur',      color: '#a78bfa' },
    surprise: { label: 'Surpris',   color: '#fb923c' },
    neutral:  { label: 'Neutre',    color: 'var(--sage)' },
  }
  const emo = EMOTION_MAP[emotion?.emotion || emotion?.current_emotion]
  const userStats = overview?.user_stats
  const monitoredCount = userStats?.monitored_users ?? '—'

  return (
    <div className="p-8 max-w-7xl">
      <div className="mb-8 animate-fade-up">
        <p className="text-sm font-medium mb-1" style={{ color: 'var(--muted)' }}>
          {new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
        <h1 className="font-display text-3xl font-bold" style={{ color: 'var(--text)' }}>
          Bonjour{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Administration · Vue système complète
        </p>
      </div>

      {urgentCount > 0 && (
        <div className="mb-6 p-4 rounded-2xl flex items-center gap-4 animate-slide-down"
          style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(239,68,68,0.15)' }}>
            <AlertTriangle size={18} style={{ color: '#f87171' }} />
          </div>
          <div className="flex-1">
            <p className="font-display font-bold" style={{ color: 'var(--text)' }}>
              {urgentCount} alerte{urgentCount > 1 ? 's' : ''} urgente{urgentCount > 1 ? 's' : ''} en attente
            </p>
            <p className="text-sm" style={{ color: '#f87171' }}>Intervention immédiate requise</p>
          </div>
          <a href="/alerts" className="btn-secondary text-sm py-2 px-4" style={{ fontSize: 13 }}>
            Voir les alertes
          </a>
        </div>
      )}

      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard icon={Bell} label="Alertes aujourd'hui" value={alerts.length} sub="Cette session" delay={0} />
        <StatCard icon={AlertTriangle} label="Urgences" value={urgentCount} color="var(--danger)" sub="Intervention requise" delay={0.1} />
        <StatCard icon={Users} label="Personnes suivies" value={monitoredCount} color="var(--teal)" sub="Elderly + soignants" delay={0.2} />
        <StatCard icon={Video} label="État détection" value={fallState} color={isFallen ? 'var(--danger)' : 'var(--ok)'} sub={isFallen ? `${Math.round(fallStatus?.fall_duration_seconds || 0)}s au sol` : 'Surveillance active'} delay={0.3} />
      </div>

      <div className="grid grid-cols-12 gap-5">
        {/* Left col */}
        <div className="col-span-3 flex flex-col gap-4">
          <ServiceStatus />

          <div className="glass rounded-2xl p-5 animate-fade-up delay-400">
            <h3 className="font-display font-semibold text-sm mb-4" style={{ color: 'var(--text)' }}>Émotion Détectée</h3>
            {emo ? (
              <div className="text-center">
                <div className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                  style={{ background: `${emo.color}18`, border: `1px solid ${emo.color}30` }}>
                  <Smile size={22} style={{ color: emo.color }} />
                </div>
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
                <Eye size={24} className="mx-auto mb-2" style={{ color: 'var(--muted)' }} />
                <p className="text-xs" style={{ color: 'var(--muted)' }}>Caméra inactive</p>
              </div>
            )}
          </div>
        </div>

        {/* Center col */}
        <div className="col-span-5 flex flex-col gap-4">
          <div className="glass rounded-2xl p-5 animate-fade-up delay-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-semibold text-sm" style={{ color: 'var(--text)' }}>Détection de Chute</h3>
              <Camera size={15} style={{ color: 'var(--muted)' }} />
            </div>
            {fallStatus ? (
              <div>
                <div className="flex items-center gap-3 p-4 rounded-xl mb-3"
                  style={{
                    background: isFallen ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.08)',
                    border: `1px solid ${isFallen ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.2)'}`
                  }}>
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ background: isFallen ? 'var(--danger)' : 'var(--ok)' }} />
                  <div>
                    <p className="font-bold" style={{ color: 'var(--text)' }}>{fallStatus.state}</p>
                    <p className="text-xs" style={{ color: 'var(--muted)' }}>
                      {isFallen ? `Au sol depuis ${Math.round(fallStatus.fall_duration_seconds || 0)}s` : 'Personne debout — normal'}
                    </p>
                  </div>
                </div>
                {isFallen && (
                  <button onClick={async () => { try { await axios.post('http://localhost:8003/reset') } catch {} }}
                    className="btn-secondary w-full text-sm py-2">
                    Réinitialiser (fausse alerte)
                  </button>
                )}
              </div>
            ) : (
              <div className="text-center py-6">
                <Camera size={24} className="mx-auto mb-2" style={{ color: 'var(--muted)' }} />
                <p className="text-xs" style={{ color: 'var(--muted)' }}>Service non disponible</p>
              </div>
            )}
          </div>

          <div className="glass rounded-2xl p-5 flex-1 animate-fade-up delay-300">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-semibold text-sm" style={{ color: 'var(--text)' }}>Alertes récentes</h3>
              <Link to="/alerts" className="text-xs font-medium transition-colors" style={{ color: 'var(--green)' }}>Voir tout</Link>
            </div>
            <AlertFeed alerts={alerts.slice(0, 5)} maxHeight="260px" onResolve={onResolveAlert} />
          </div>
        </div>

        {/* Right col */}
        <div className="col-span-4 flex flex-col gap-4">
          <div className="glass rounded-2xl p-5 animate-fade-up delay-200">
            <h3 className="font-display font-semibold text-sm mb-4" style={{ color: 'var(--text)' }}>Actions rapides</h3>
            <div className="flex flex-col gap-2">
              {[
                { label: 'Gestion des utilisateurs', path: '/users' },
                { label: 'Historique alertes', path: '/alerts' },
                { label: 'Surveillance', path: '/monitoring' },
                { label: 'Conversations', path: '/conversations' },
                { label: 'Revues', path: '/reviews' },
              ].map(a => (
                <Link key={a.path} to={a.path}
                  className="flex items-center px-4 py-3 rounded-xl transition-all text-sm font-medium"
                  style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(45,120,45,0.12)', color: 'var(--text2)' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--green)'; e.currentTarget.style.color = 'var(--green)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(45,120,45,0.12)'; e.currentTarget.style.color = 'var(--text2)' }}>
                  {a.label}
                </Link>
              ))}
            </div>
          </div>

          <div className="glass rounded-2xl p-5 animate-fade-up delay-400">
            <h3 className="font-display font-semibold text-sm mb-4" style={{ color: 'var(--text)' }}>Système</h3>
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

/* ─── Caregiver dashboard ──────────────────────────────────────────── */
function CaregiverDashboard({ alerts, overview, onResolveAlert }) {
  const { user } = useAuth()
  const assignedUsers = overview?.users || []
  const urgentCount = alerts.filter(a => a.status !== 'resolved' && (a.action_required === 'emergency' || a.person_status === 'needs_help')).length
  const activeAlertsTotal = assignedUsers.reduce((sum, u) => sum + (u.active_alerts || 0), 0)

  const getSeverityColor = (severity) => {
    if (severity === 'critical' || severity === 'emergency') return 'var(--danger)'
    if (severity === 'high') return 'var(--warn)'
    return 'var(--ok)'
  }

  return (
    <div className="p-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8 animate-fade-up">
        <p className="text-sm font-medium mb-1" style={{ color: 'var(--muted)' }}>
          {new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
        <h1 className="font-display text-3xl font-bold" style={{ color: 'var(--text)' }}>
          Bonjour{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text2)' }}>
          Tableau de bord soignant · Suivi en temps réel
        </p>
      </div>

      {/* Urgent banner */}
      {urgentCount > 0 && (
        <div className="mb-6 p-4 rounded-2xl flex items-center gap-4 animate-slide-down"
          style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(239,68,68,0.15)' }}>
            <ShieldAlert size={18} style={{ color: '#f87171' }} />
          </div>
          <div className="flex-1">
            <p className="font-display font-bold" style={{ color: 'var(--text)' }}>
              {urgentCount} urgence{urgentCount > 1 ? 's' : ''} — intervention requise
            </p>
            <p className="text-sm" style={{ color: '#f87171' }}>Un de vos patients a besoin d'aide</p>
          </div>
          <Link to="/alerts" className="btn-secondary text-sm py-2 px-4" style={{ fontSize: 13 }}>
            Voir les alertes
          </Link>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard icon={Users} label="Patients assignés" value={assignedUsers.filter(u => u.role === 'elderly').length} sub="Sous votre surveillance" delay={0} />
        <StatCard icon={AlertTriangle} label="Alertes actives" value={activeAlertsTotal || alerts.length} color={activeAlertsTotal > 0 ? 'var(--warn)' : 'var(--ok)'} sub="En attente de traitement" delay={0.1} />
        <StatCard icon={Activity} label="Urgences" value={urgentCount} color={urgentCount > 0 ? 'var(--danger)' : 'var(--ok)'} sub={urgentCount > 0 ? 'Intervention requise' : 'Tout est calme'} delay={0.2} />
      </div>

      <div className="grid grid-cols-12 gap-5">
        {/* Assigned patients */}
        <div className="col-span-5 flex flex-col gap-4">
          <div className="glass rounded-2xl p-5 animate-fade-up">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-semibold text-sm" style={{ color: 'var(--text)' }}>Mes patients</h3>
              <UserCheck size={15} style={{ color: 'var(--muted)' }} />
            </div>
            {assignedUsers.filter(u => u.role === 'elderly').length === 0 ? (
              <div className="text-center py-8">
                <Users size={28} className="mx-auto mb-2" style={{ color: 'var(--muted)', opacity: 0.4 }} />
                <p className="text-sm" style={{ color: 'var(--text2)' }}>Aucun patient assigné</p>
                <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Contactez l'administrateur</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {assignedUsers.filter(u => u.role === 'elderly').map(p => (
                  <div key={p.id} className="rounded-xl p-4 transition-all"
                    style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(45,120,45,0.12)' }}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-sm"
                          style={{ background: 'rgba(30,107,46,0.1)', color: 'var(--green)' }}>
                          {p.full_name?.charAt(0) || '?'}
                        </div>
                        <div>
                          <p className="font-semibold text-sm" style={{ color: 'var(--text)' }}>{p.full_name}</p>
                          <p className="text-xs" style={{ color: 'var(--muted)' }}>
                            {p.open_reviews > 0 ? `${p.open_reviews} avis ouvert${p.open_reviews > 1 ? 's' : ''}` : 'Aucun avis en attente'}
                          </p>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        {p.active_alerts > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold"
                            style={{ background: 'rgba(185,28,28,0.1)', color: 'var(--danger)', border: '1px solid rgba(185,28,28,0.2)' }}>
                            <AlertTriangle size={10} /> {p.active_alerts} alerte{p.active_alerts > 1 ? 's' : ''}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold"
                            style={{ background: 'rgba(30,107,46,0.1)', color: 'var(--ok)', border: '1px solid rgba(30,107,46,0.2)' }}>
                            <CheckCircle size={10} /> OK
                          </span>
                        )}
                      </div>
                    </div>
                    {p.latest_alert && (
                      <div className="mt-3 pt-3 flex items-center gap-2"
                        style={{ borderTop: '1px solid rgba(45,120,45,0.1)' }}>
                        <Clock size={11} style={{ color: 'var(--muted)', flexShrink: 0 }} />
                        <p className="text-xs" style={{ color: 'var(--muted)' }}>
                          Dernière alerte:{' '}
                          <span style={{ color: getSeverityColor(p.latest_alert.severity) }}>
                            {p.latest_alert.alert_type}
                          </span>
                          {p.latest_alert.triggered_at && (
                            <> · {new Date(p.latest_alert.triggered_at).toLocaleDateString('fr-FR')}</>
                          )}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Alerts feed */}
        <div className="col-span-4 flex flex-col gap-4">
          <div className="glass rounded-2xl p-5 flex-1 animate-fade-up delay-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-semibold text-sm" style={{ color: 'var(--text)' }}>Alertes en direct</h3>
              <Link to="/alerts" className="text-xs font-medium" style={{ color: 'var(--green)' }}>Voir tout</Link>
            </div>
            <AlertFeed alerts={alerts.slice(0, 6)} maxHeight="360px" onResolve={onResolveAlert} />
          </div>
        </div>

        {/* Quick actions */}
        <div className="col-span-3 flex flex-col gap-4">
          <div className="glass rounded-2xl p-5 animate-fade-up delay-100">
            <h3 className="font-display font-semibold text-sm mb-4" style={{ color: 'var(--text)' }}>Actions</h3>
            <div className="flex flex-col gap-2">
              {[
                { label: 'Parler à Léa', path: '/voice', icon: Mic },
                { label: 'Surveillance', path: '/monitoring', icon: Monitor },
                { label: 'Alertes', path: '/alerts', icon: Bell },
                { label: 'Conversations', path: '/conversations', icon: Heart },
              ].map(a => (
                <Link key={a.path} to={a.path}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-medium"
                  style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(45,120,45,0.12)', color: 'var(--text2)' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--green)'; e.currentTarget.style.color = 'var(--green)' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(45,120,45,0.12)'; e.currentTarget.style.color = 'var(--text2)' }}>
                  <a.icon size={14} />
                  {a.label}
                </Link>
              ))}
            </div>
          </div>

          <div className="glass rounded-2xl p-5 animate-fade-up delay-300">
            <h3 className="font-display font-semibold text-sm mb-3" style={{ color: 'var(--text)' }}>Mes infos</h3>
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center py-1">
                <span className="text-xs" style={{ color: 'var(--muted)' }}>Rôle</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(6,182,212,0.1)', color: '#06b6d4', border: '1px solid rgba(6,182,212,0.2)' }}>
                  Soignant
                </span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-xs" style={{ color: 'var(--muted)' }}>Patients</span>
                <span className="text-xs font-medium" style={{ color: 'var(--text2)' }}>
                  {assignedUsers.filter(u => u.role === 'elderly').length}
                </span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-xs" style={{ color: 'var(--muted)' }}>Avis ouverts</span>
                <span className="text-xs font-medium" style={{ color: 'var(--text2)' }}>
                  {overview?.review_stats?.open_reviews ?? '—'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ─── Root export ──────────────────────────────────────────────────── */
export default function Dashboard({ alerts, onResolveAlert }) {
  const { user } = useAuth()
  const [fallStatus, setFallStatus] = useState(null)
  const [emotion, setEmotion] = useState(null)
  const [overview, setOverview] = useState(null)

  useEffect(() => {
    const fetchFall = async () => {
      try { const r = await axios.get('http://localhost:8003/status', { timeout: 2000 }); setFallStatus(r.data) } catch {}
    }
    const fetchEmotion = async () => {
      try { const r = await axios.get('http://localhost:8004/status/emotion', { timeout: 2000 }); setEmotion(r.data) } catch {}
    }
    const fetchOverview = async () => {
      try { const r = await axios.get('http://127.0.0.1:8000/dashboard/overview', { timeout: 3000 }); setOverview(r.data) } catch {}
    }
    fetchFall(); fetchEmotion(); fetchOverview()
    const t = setInterval(() => { fetchFall(); fetchEmotion(); fetchOverview() }, 5000)
    return () => clearInterval(t)
  }, [])

  if (user?.role === 'caregiver') {
    return <CaregiverDashboard alerts={alerts} overview={overview} onResolveAlert={onResolveAlert} />
  }
  return <AdminDashboard alerts={alerts} fallStatus={fallStatus} emotion={emotion} overview={overview} onResolveAlert={onResolveAlert} />
}
