import { Link, useLocation } from 'react-router-dom'

export default function Navbar({ wsConnected }) {
  const location = useLocation()
  const links = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/user', label: 'Léa', icon: '🤖' },
    { path: '/alerts', label: 'Alertes', icon: '🔔' },
  ]

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-3"
      style={{ background: 'rgba(8,12,20,0.9)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--border)' }}>
      <div className="flex items-center gap-3">
        <span className="text-xl">🌿</span>
        <span className="font-display font-bold text-white text-lg">FiAinina</span>
        <span className="text-xs px-2 py-0.5 rounded-full font-medium"
          style={{ background: 'var(--surface2)', color: 'var(--muted)' }}>
          AI Care
        </span>
      </div>

      <div className="flex items-center gap-1">
        {links.map(link => (
          <Link key={link.path} to={link.path}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
            style={{
              background: location.pathname === link.path ? 'var(--surface2)' : 'transparent',
              color: location.pathname === link.path ? 'white' : 'var(--muted)',
            }}>
            <span>{link.icon}</span>
            <span>{link.label}</span>
          </Link>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          {wsConnected && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
              style={{ background: 'var(--ok)' }} />
          )}
          <span className="relative inline-flex rounded-full h-2 w-2"
            style={{ background: wsConnected ? 'var(--ok)' : 'var(--muted)' }} />
        </span>
        <span className="text-xs" style={{ color: wsConnected ? 'var(--ok)' : 'var(--muted)' }}>
          {wsConnected ? 'Connecté' : 'Déconnecté'}
        </span>
      </div>
    </nav>
  )
}
