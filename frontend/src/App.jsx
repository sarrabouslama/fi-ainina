import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuth, AuthProvider } from './context/AuthContext'
import { useWebSocket } from './hooks/useWebSocket'
import TopNav from './components/TopNav'

import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
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

  const allAlerts = [...alertMessages, ...backendEvents.filter(m => m.type === 'alert_escalated' || m.payload)]
    .map(m => m.payload || m).slice(0, 100)
  const wsConnected = backendWsConnected || alertWsConnected

  return (
    <Routes>
      {/* Public */}
      <Route path="/login"    element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Elderly-only home */}
      <Route path="/home" element={
        <RequireAuth roles={['elderly']}>
          <ElderlyHome />
        </RequireAuth>
      } />

      {/* Staff/admin pages */}
      <Route path="/dashboard" element={
        <RequireAuth roles={['admin', 'caregiver']}>
          <AppLayout wsConnected={wsConnected}><Dashboard alerts={allAlerts} /></AppLayout>
        </RequireAuth>
      } />
      <Route path="/voice" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}><VoicePage /></AppLayout>
        </RequireAuth>
      } />
      <Route path="/alerts" element={
        <RequireAuth roles={['admin', 'caregiver']}>
          <AppLayout wsConnected={wsConnected}><AlertsPage alerts={allAlerts} /></AppLayout>
        </RequireAuth>
      } />
      <Route path="/monitoring" element={
        <RequireAuth roles={['admin', 'caregiver']}>
          <AppLayout wsConnected={wsConnected}><MonitoringPage /></AppLayout>
        </RequireAuth>
      } />
      <Route path="/conversations" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}><ConversationsPage /></AppLayout>
        </RequireAuth>
      } />
      <Route path="/users" element={
        <RequireAuth roles={['admin']}>
          <AppLayout wsConnected={wsConnected}><UsersPage /></AppLayout>
        </RequireAuth>
      } />
      <Route path="/reviews" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}><ReviewsPage /></AppLayout>
        </RequireAuth>
      } />

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<RootRedirect />} />
    </Routes>
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
