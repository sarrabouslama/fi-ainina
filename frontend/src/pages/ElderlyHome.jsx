import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { Mic, MessageSquare, Star, LogOut, Bell, Phone, Heart } from 'lucide-react'

export default function ElderlyHome() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Bonjour' : hour < 18 ? 'Bon après-midi' : 'Bonsoir'
  const firstName = user?.full_name?.split(' ')[0] || ''

  const handleLogout = async () => { await logout(); navigate('/login') }

  const actions = [
    { label: 'Parler à Léa', desc: 'Votre assistante vocale', path: '/voice', Icon: Mic, color: 'var(--green)', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.25)' },
    { label: 'Mes conversations', desc: 'Historique avec Léa', path: '/conversations', Icon: MessageSquare, color: 'var(--teal)', bg: 'rgba(6,182,212,0.08)', border: 'rgba(6,182,212,0.15)' },
    { label: 'Mes alertes', desc: 'Notifications reçues', path: '/alerts', Icon: Bell, color: 'var(--warn)', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.15)' },
    { label: 'Laisser un avis', desc: 'Feedback et questions', path: '/reviews', Icon: Star, color: 'var(--gold)', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.15)' },
  ]

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <div className="fixed inset-0 pointer-events-none overflow-hidden" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <img src="/logo.png" alt="logo" className="w-100 h-100 object-contain mx-auto mb-4" />
          <h1 className="font-display text-4xl font-bold" style={{ color: 'var(--text)' }}>
            {greeting}{firstName ? `, ${firstName}` : ''}
          </h1>
          <p className="text-base mt-2" style={{ color: 'var(--text2)' }}>
            {new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
        </div>

        {/* Wellness check */}
        <div className="glass rounded-2xl p-5 mb-6 text-center"
          style={{ border: '1px solid rgba(16,185,129,0.15)' }}>
          <Heart size={20} className="mx-auto mb-2" style={{ color: 'var(--green)' }} />
          <p className="text-sm font-medium mb-1" style={{ color: 'var(--text)' }}>Comment vous sentez-vous ?</p>
          <div className="flex justify-center gap-3 mt-3">
            {['Bien', 'Moyen', 'Pas bien'].map((s, i) => (
              <button key={s} onClick={() => navigate('/voice')}
                className="px-4 py-2 rounded-xl text-sm font-medium transition-all"
                style={{
                  background: i === 0 ? 'rgba(16,185,129,0.15)' : i === 1 ? 'rgba(245,158,11,0.1)' : 'rgba(239,68,68,0.1)',
                  border: `1px solid ${i === 0 ? 'rgba(16,185,129,0.3)' : i === 1 ? 'rgba(245,158,11,0.2)' : 'rgba(239,68,68,0.2)'}`,
                  color: i === 0 ? 'var(--green)' : i === 1 ? 'var(--warn)' : 'var(--danger)',
                }}>
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Main actions */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {actions.map(({ label, desc, path, Icon, color, bg, border }) => (
            <button key={path} onClick={() => navigate(path)}
              className="flex flex-col items-start p-5 rounded-2xl transition-all text-left"
              style={{ background: bg, border: `1px solid ${border}` }}
              onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
              onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
              <Icon size={22} style={{ color, marginBottom: 12 }} />
              <p className="text-sm font-bold leading-snug" style={{ color: 'var(--text)' }}>{label}</p>
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{desc}</p>
            </button>
          ))}
        </div>

        {/* Emergency */}
        <button onClick={() => navigate('/voice')}
          className="w-full py-4 rounded-2xl text-base font-bold mb-6 transition-all flex items-center justify-center gap-3"
          style={{
            background: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.3)',
            color: '#f87171',
          }}>
          <Phone size={18} />
          Urgence — Appeler à l'aide
        </button>

        <button onClick={handleLogout}
          className="flex items-center justify-center gap-2 mx-auto text-sm transition-colors"
          style={{ color: 'var(--muted)' }}>
          <LogOut size={15} />
          Déconnexion
        </button>
      </div>
    </div>
  )
}
