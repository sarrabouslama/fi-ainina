import { useEffect, useRef, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import axios from 'axios'
import { useAuth, AuthProvider } from './context/AuthContext'
import { useWebSocket } from './hooks/useWebSocket'
import TopNav from './components/TopNav'

import LoginPage from './pages/LoginPage'
import ElderlyHome from './pages/ElderlyHome'
import Dashboard from './pages/Dashboard'
import VoicePage from './pages/VoicePage'
import AlertsPage from './pages/AlertsPage'
import MonitoringPage from './pages/MonitoringPage'
import ConversationsPage from './pages/ConversationsPage'
import UsersPage from './pages/UsersPage'
import ReviewsPage from './pages/ReviewsPage'

function RequireAuth({ children, roles }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg)' }}>
      <div className="text-center">
        <img src="/logo.png" alt="logo" className="w-20 h-20 object-contain mx-auto mb-4 animate-float" />
        <p className="text-sm" style={{ color: 'var(--muted)' }}>Chargement...</p>
      </div>
    </div>
  )
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}

function AppLayout({ children, wsConnected }) {
  return (
    <div className="min-h-screen">
      <TopNav wsConnected={wsConnected} />
      <main className="min-h-screen overflow-y-auto" style={{ paddingTop: '72px' }}>
        {children}
      </main>
    </div>
  )
}

function RootRedirect() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'elderly') return <Navigate to="/home" replace />
  return <Navigate to="/dashboard" replace />
}

function InnerApp() {
  const { token, user } = useAuth()
  const wsUrl = token ? `ws://127.0.0.1:8000/ws/events?token=${token}` : null
  const { messages: backendEvents, connected: backendWsConnected } = useWebSocket(wsUrl)
  const { messages: alertMessages, connected: alertWsConnected } = useWebSocket('ws://127.0.0.1:8005/ws')
  const wsConnected = backendWsConnected || alertWsConnected

  // Fetch persisted alerts from the DB so staff see history on load/refresh
  const [dbAlerts, setDbAlerts] = useState([])
  const [alertRefreshKey, setAlertRefreshKey] = useState(0)
  const refreshAlerts = () => setAlertRefreshKey(k => k + 1)

  useEffect(() => {
    if (!user || (user.role !== 'admin' && user.role !== 'caregiver')) return
    const load = async () => {
      try {
        const r = await axios.get('http://127.0.0.1:8000/alerts', { timeout: 5000 })
        setDbAlerts(r.data.map(a => ({
          event_type: a.alert_type === 'manual_emergency' ? 'fall_detected' : a.alert_type,
          person_status: a.severity === 'critical' ? 'needs_help' : 'okay',
          action_required: a.severity === 'critical' ? 'emergency' : null,
          severity: a.severity,
          status: a.status,
          _ts: a.triggered_at,
          alert_id: a.id,
          response_text: a.metadata_json?.message,
          message_for_family: a.metadata_json?.message_for_family,
        })))
      } catch {}
    }
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [user, alertRefreshKey])

  // Merge real-time WS alerts with DB history; deduplicate by alert_id
  const wsAlerts = [...alertMessages, ...backendEvents.filter(m => m.type === 'alert_escalated')]
    .map(m => m.payload || m)
  const wsAlertIds = new Set(wsAlerts.map(a => a.alert_id).filter(Boolean))
  const allAlerts = [...wsAlerts, ...dbAlerts.filter(a => !wsAlertIds.has(a.alert_id))].slice(0, 100)

  // ── In-app toast + browser notification for new emergency alerts ──────────
  const [toast, setToast] = useState(null)
  const prevCountRef = useRef(0)
  const isStaff = user?.role === 'admin' || user?.role === 'caregiver'

  useEffect(() => {
    if (!isStaff) return
    // Request browser notification permission once
    if (Notification.permission === 'default') Notification.requestPermission()
  }, [isStaff])

  useEffect(() => {
    if (!isStaff || allAlerts.length === 0) return
    if (allAlerts.length <= prevCountRef.current) { prevCountRef.current = allAlerts.length; return }

    const newest = allAlerts[0]
    const isEmergency =
      newest?.status !== 'resolved' &&
      (newest?.event_type === 'fall_detected' || newest?.person_status === 'needs_help' || newest?.severity === 'high')
    prevCountRef.current = allAlerts.length

    if (isEmergency) {
      const msg = newest?.event_type === 'fall_detected' ? 'Chute détectée — intervention requise' : 'Alerte urgente reçue'
      setToast(msg)
      setTimeout(() => setToast(null), 6000)
      if (Notification.permission === 'granted') {
        new Notification('🚨 في عينينا — Urgence', { body: msg, icon: '/logo.png' })
      }
    }
  }, [allAlerts.length, isStaff])


  return (
    <>
    {/* Emergency toast notification */}
    {toast && (
      <div style={{
        position: 'fixed', top: 84, right: 16, zIndex: 9999,
        background: 'rgba(185,28,28,0.95)', color: '#fff',
        borderRadius: 16, padding: '14px 20px',
        boxShadow: '0 4px 24px rgba(185,28,28,0.4)',
        display: 'flex', alignItems: 'center', gap: 10,
        fontSize: 14, fontWeight: 600, maxWidth: 320,
        animation: 'slideIn 0.3s ease',
      }}>
        <span style={{ fontSize: 20 }}>🚨</span>
        <div>
          <div style={{ fontWeight: 700 }}>Alerte urgente</div>
          <div style={{ fontWeight: 400, fontSize: 12, opacity: 0.9, marginTop: 2 }}>{toast}</div>
        </div>
        <button onClick={() => setToast(null)}
          style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: 18, opacity: 0.7 }}>
          ×
        </button>
      </div>
    )}
    <Routes>
      {/* Public — login only, no self-registration (admin creates accounts) */}
      <Route path="/login" element={<LoginPage />} />
      {/* Redirect old /register to /login */}
      <Route path="/register" element={<Navigate to="/login" replace />} />

      {/* Elderly — dedicated home */}
      <Route path="/home" element={
        <RequireAuth roles={['elderly']}>
          <ElderlyHome />
        </RequireAuth>
      } />

      {/* Léa voice assistant — ELDERLY ONLY */}
      <Route path="/voice" element={
        <RequireAuth roles={['elderly']}>
          <AppLayout wsConnected={wsConnected}><VoicePage /></AppLayout>
        </RequireAuth>
      } />

      {/* Admin & caregiver dashboard */}
      <Route path="/dashboard" element={
        <RequireAuth roles={['admin', 'caregiver']}>
          <AppLayout wsConnected={wsConnected}><Dashboard alerts={allAlerts} onResolveAlert={refreshAlerts} /></AppLayout>
        </RequireAuth>
      } />

      {/* Alerts — admin & caregiver */}
      <Route path="/alerts" element={
        <RequireAuth roles={['admin', 'caregiver']}>
          <AppLayout wsConnected={wsConnected}><AlertsPage alerts={allAlerts} onResolveAlert={refreshAlerts} /></AppLayout>
        </RequireAuth>
      } />

      {/* Monitoring — all roles, content differs per role */}
      <Route path="/monitoring" element={
        <RequireAuth roles={['admin', 'caregiver', 'elderly']}>
          <AppLayout wsConnected={wsConnected}><MonitoringPage /></AppLayout>
        </RequireAuth>
      } />

      {/* Conversations — all roles, filtered by role in component */}
      <Route path="/conversations" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}><ConversationsPage /></AppLayout>
        </RequireAuth>
      } />

      {/* Users — admin only */}
      <Route path="/users" element={
        <RequireAuth roles={['admin']}>
          <AppLayout wsConnected={wsConnected}><UsersPage /></AppLayout>
        </RequireAuth>
      } />

      {/* Reviews — all roles */}
      <Route path="/reviews" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}><ReviewsPage /></AppLayout>
        </RequireAuth>
      } />

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<RootRedirect />} />
    </Routes>
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <InnerApp />
      </BrowserRouter>
    </AuthProvider>
  )
}
