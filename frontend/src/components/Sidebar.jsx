import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LayoutDashboard, Mic, Bell, Activity, Users, MessageSquare, LogOut, Star } from 'lucide-react'

const NAV = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord' },
  { path: '/voice', icon: Mic, label: 'Léa — Voix' },
  { path: '/alerts', icon: Bell, label: 'Alertes' },
  { path: '/monitoring', icon: Activity, label: 'Surveillance' },
  { path: '/conversations', icon: MessageSquare, label: 'Conversations' },
  { path: '/users', icon: Users, label: 'Utilisateurs', adminOnly: true },
  { path: '/reviews', icon: Star, label: 'Revues' },
]

export default function Sidebar({ wsConnected }) {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => { await logout(); navigate('/login') }
  const visibleNav = NAV.filter(n => !n.adminOnly || user?.role === 'admin')
  const ROLE_COLORS = { admin: '#c9a84c', caregiver: '#60a5fa', elderly: '#78c98e', family: '#f9a8d4' }
  const roleColor = ROLE_COLORS[user?.role] || 'var(--muted)'

  return (
    <aside className="fixed left-0 top-0 h-full w-64 flex flex-col z-40 glass-dark" style={{ borderRight: '1px solid var(--border)' }}>
      <div className="p-5 pb-4">
        <Link to="/dashboard" className="flex items-center gap-3 group">
          <div className="w-11 h-11 rounded-xl flex items-center justify-center transition-all group-hover:scale-105" style={{ background: 'var(--surface2)', boxShadow: '0 0 16px rgba(45,138,67,0.2)' }}>
            <img src="/logo.png" alt="logo" className="w-9 h-9 object-contain" />
          </div>
          <div>
            <p className="font-arabic font-bold text-base leading-none text-gradient">في عينينا</p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>elderly companion ai</p>
          </div>
        </Link>
      </div>
      <div className="px-4 pb-3">
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: 'rgba(7,43,14,0.6)', border: '1px solid var(--border)' }}>
          <span className="relative flex h-2 w-2 flex-shrink-0">
            {wsConnected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ background: 'var(--ok)' }} />}
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: wsConnected ? 'var(--ok)' : 'var(--muted)' }} />
          </span>
          <span className="text-xs font-medium" style={{ color: wsConnected ? 'var(--ok)' : 'var(--muted)' }}>
            {wsConnected ? 'Alertes en direct' : 'Non connecté'}
          </span>
        </div>
      </div>
      <div style={{ height: 1, background: 'linear-gradient(90deg, transparent, var(--border), transparent)', margin: '0 16px 12px' }} />
      <nav className="flex-1 px-3 overflow-y-auto">
        <p className="text-xs font-semibold uppercase tracking-widest px-3 mb-3" style={{ color: 'var(--border2)' }}>Menu</p>
        <div className="flex flex-col gap-0.5">
          {visibleNav.map(({ path, icon: Icon, label }) => {
            const active = pathname === path
            return (
              <Link key={path} to={path} className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-sm font-medium group"
                style={{ background: active ? 'rgba(45,138,67,0.18)' : 'transparent', color: active ? '#78c98e' : 'var(--text2)', borderLeft: active ? '2px solid var(--green)' : '2px solid transparent' }}>
                <Icon size={15} className="flex-shrink-0 transition-transform group-hover:scale-110" />
                {label}
              </Link>
            )
          })}
        </div>
      </nav>
      <div className="p-4" style={{ borderTop: '1px solid var(--border)' }}>
        {user && (
          <div className="flex items-center gap-3 px-3 py-2.5 mb-2 rounded-xl" style={{ background: 'rgba(7,43,14,0.6)', border: '1px solid var(--border)' }}>
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0" style={{ background: `${roleColor}25`, color: roleColor }}>
              {user.full_name?.[0] || '?'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate">{user.full_name}</p>
              <p className="text-xs font-medium" style={{ color: roleColor }}>{user.role}</p>
            </div>
          </div>
        )}
        <button onClick={handleLogout} className="flex items-center gap-2 w-full px-3 py-2 rounded-xl text-sm transition-all" style={{ color: 'var(--muted)' }}
          onMouseEnter={e => { e.currentTarget.style.color = '#f87171'; e.currentTarget.style.background = 'rgba(239,68,68,0.05)' }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--muted)'; e.currentTarget.style.background = 'transparent' }}>
          <LogOut size={14} /> Déconnexion
        </button>
      </div>
    </aside>
  )
}
