import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuth, AuthProvider } from './context/AuthContext'
import { useWebSocket } from './hooks/useWebSocket'
import Sidebar from './components/Sidebar'

// Pages
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import Dashboard from './pages/Dashboard'
import VoicePage from './pages/VoicePage'
import AlertsPage from './pages/AlertsPage'
import MonitoringPage from './pages/MonitoringPage'
import ConversationsPage from './pages/ConversationsPage'
import UsersPage from './pages/UsersPage'
import ReviewsPage from './pages/ReviewsPage'

// Auth guard
function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <img src="/logo.png" alt="logo" className="w-16 h-16 object-contain mx-auto mb-4 animate-float" />
        <p className="text-sm" style={{ color: 'var(--muted)' }}>Chargement...</p>
      </div>
    </div>
  )
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}

// Layout with sidebar
function AppLayout({ children, wsConnected }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar wsConnected={wsConnected} />
      <main className="flex-1 ml-64 min-h-screen overflow-y-auto">
        {children}
      </main>
    </div>
  )
}

function InnerApp() {
  const { token } = useAuth()

  // Connect to companion backend WebSocket with auth token
  const wsUrl = token ? `ws://localhost:8000/ws/events?token=${token}` : null
  const { messages: backendEvents, connected: backendWsConnected } = useWebSocket(wsUrl)

  // Also connect to alert service WebSocket for real-time alerts
  const { messages: alertMessages, connected: alertWsConnected } = useWebSocket('ws://localhost:8005/ws')

  // Combine all WebSocket messages as alerts
  const allAlerts = [...alertMessages, ...backendEvents.filter(m => m.type === 'alert_escalated' || m.payload)]
    .map(m => m.payload || m)
    .slice(0, 100)

  const wsConnected = backendWsConnected || alertWsConnected

  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected */}
      <Route path="/dashboard" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}>
            <Dashboard alerts={allAlerts} />
          </AppLayout>
        </RequireAuth>
      } />
      <Route path="/voice" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}>
            <VoicePage />
          </AppLayout>
        </RequireAuth>
      } />
      <Route path="/alerts" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}>
            <AlertsPage alerts={allAlerts} />
          </AppLayout>
        </RequireAuth>
      } />
      <Route path="/monitoring" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}>
            <MonitoringPage />
          </AppLayout>
        </RequireAuth>
      } />
      <Route path="/conversations" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}>
            <ConversationsPage />
          </AppLayout>
        </RequireAuth>
      } />
      <Route path="/users" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}>
            <UsersPage />
          </AppLayout>
        </RequireAuth>
      } />
      <Route path="/reviews" element={
        <RequireAuth>
          <AppLayout wsConnected={wsConnected}>
            <ReviewsPage />
          </AppLayout>
        </RequireAuth>
      } />

      {/* Default */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
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
