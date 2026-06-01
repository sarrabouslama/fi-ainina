import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LayoutDashboard, Mic, Bell, Activity, Users, MessageSquare, Star, LogOut } from 'lucide-react'

const NAV = [
  { path: '/dashboard',     icon: LayoutDashboard, label: 'Tableau de bord' },
  { path: '/voice',         icon: Mic,             label: 'Léa' },
  { path: '/alerts',        icon: Bell,            label: 'Alertes' },
  { path: '/monitoring',    icon: Activity,        label: 'Surveillance' },
  { path: '/conversations', icon: MessageSquare,   label: 'Conversations' },
  { path: '/reviews',       icon: Star,            label: 'Revues' },
  { path: '/users',         icon: Users,           label: 'Utilisateurs', adminOnly: true },
]

const ROLE_COLORS = { admin: '#f59e0b', caregiver: '#06b6d4', elderly: '#10b981' }

export default function TopNav({ wsConnected }) {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => { await logout(); navigate('/login') }
  const visibleNav = NAV.filter(n => !n.adminOnly || user?.role === 'admin')
  const roleColor = ROLE_COLORS[user?.role] || 'var(--muted)'

  return (
    <header className="fixed top-0 left-0 right-0 z-40 glass-dark flex items-center px-5 gap-5"
      style={{ height: 72, borderBottom: '1px solid rgba(45,120,45,0.12)' }}>

      {/* Logo */}
      <Link to="/" className="flex items-center gap-2.5 flex-shrink-0">
        <img src="/logo.png" alt="logo" style={{ width: 160, height: 160, objectFit: 'contain' }} />
        <span className="font-arabic font-bold text-xl text-gradient hidden sm:block">في عينينا</span>
      </Link>

      <div className="w-px h-10 flex-shrink-0" style={{ background: 'rgba(0,0,0,0.08)' }} />

      {/* Nav links */}
      <nav className="flex items-center gap-2 flex-1 overflow-x-auto">
        {visibleNav.map(({ path, icon: Icon, label }) => {
          const active = pathname === path
          return (
            <Link key={path} to={path}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-base font-medium transition-all whitespace-nowrap flex-shrink-0"
              style={{
                background: active ? 'rgba(16,185,129,0.15)' : 'transparent',
                color: active ? 'var(--green-light)' : 'var(--text2)',
                borderBottom: active ? '2px solid var(--green)' : '2px solid transparent',
              }}>
              <Icon size={18} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Right side */}
      <div className="flex items-center gap-4 flex-shrink-0">
        {/* WS indicator */}
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full"
            style={{ background: wsConnected ? 'var(--ok)' : 'var(--muted)' }} />
          <span className="text-sm hidden md:block" style={{ color: wsConnected ? 'var(--ok)' : 'var(--muted)' }}>
            {wsConnected ? 'En direct' : 'Hors ligne'}
          </span>
        </div>

        <div className="w-px h-6" style={{ background: 'rgba(0,0,0,0.08)' }} />

        {/* User */}
        {user && (
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
              style={{ background: `${roleColor}20`, color: roleColor, border: `1px solid ${roleColor}30` }}>
              {user.full_name?.[0] || '?'}
            </div>
            <div className="hidden md:block">
              <p className="text-sm font-semibold text-white leading-none">{user.full_name}</p>
              <p className="text-xs mt-0.5" style={{ color: roleColor }}>{user.role}</p>
            </div>
          </div>
        )}

        <button onClick={handleLogout}
          className="p-2 rounded-lg transition-all flex-shrink-0"
          style={{ color: 'var(--muted)' }}
          onMouseEnter={e => e.currentTarget.style.color = '#f87171'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
          <LogOut size={18} />
        </button>
      </div>
    </header>
  )
}