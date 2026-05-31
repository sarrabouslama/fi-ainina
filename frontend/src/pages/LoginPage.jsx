import { useState } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const registered = location.state?.registered

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      if (err.response?.status === 429) {
        setError('Compte temporairement bloqué après 5 tentatives. Réessayez dans 15 minutes.')
      } else {
        setError('Email ou mot de passe incorrect.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: '#f8faf8' }}>
      {/* Left panel — green brand */}
      <div className="hidden lg:flex w-2/5 flex-col items-center justify-center p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(160deg, #041a08 0%, #0e3d18 50%, #1e6b30 100%)' }}>
        <div className="absolute top-1/3 -left-16 w-56 h-56 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #4aab60, transparent)' }} />
        <div className="absolute bottom-1/3 -right-8 w-40 h-40 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #c9a84c, transparent)' }} />

        <div className="relative z-10 text-center">
          <div className="w-36 h-36 rounded-3xl flex items-center justify-center mx-auto mb-8"
            style={{ background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.12)' }}>
            <img src="/logo.png" alt="في عينينا" className="w-28 h-28 object-contain" />
          </div>
          <h1 className="font-arabic text-5xl font-bold mb-3"
            style={{ background: 'linear-gradient(135deg, #78c98e, #c9a84c)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            في عينينا
          </h1>
          <p className="text-lg font-body mb-2" style={{ color: 'rgba(255,255,255,0.7)' }}>
            elderly companion ai
          </p>
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            Surveillance bienveillante · Sécurité · Famille
          </p>

          <div className="mt-10 flex flex-col gap-3">
            {[
              'Détection de chute en temps réel',
              'Assistant vocal "Bonjour Léa"',
              'Alertes famille immédiates',
              'Confidentialité RGPD garantie',
            ].map((f, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 rounded-xl"
                style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: '#4aab60' }} />
                <span className="text-sm" style={{ color: 'rgba(255,255,255,0.8)' }}>{f}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — white */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <img src="/logo.png" alt="logo" className="w-14 h-14 object-contain" />
            <div>
              <p className="font-arabic font-bold text-2xl" style={{ color: '#1e6b30' }}>في عينينا</p>
              <p className="text-xs text-gray-500">elderly companion ai</p>
            </div>
          </div>

          {registered && (
            <div className="mb-6 px-4 py-3 rounded-xl text-sm"
              style={{ background: '#f0faf2', border: '1px solid #86efac', color: '#166534' }}>
              ✅ Compte créé ! Connectez-vous maintenant.
            </div>
          )}

          <h2 className="font-display text-2xl font-bold mb-1" style={{ color: '#1a2d1e' }}>
            Connexion
          </h2>
          <p className="text-sm mb-8 text-gray-500">
            Accédez à votre tableau de bord de surveillance
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider text-gray-500">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="votre@email.com"
                required
                className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all"
                style={{ background: '#f1f5f1', border: '1.5px solid #d4e8d7', color: '#1a2d1e' }}
                onFocus={e => e.target.style.borderColor = '#2d8a43'}
                onBlur={e => e.target.style.borderColor = '#d4e8d7'}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider text-gray-500">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full px-4 py-3 pr-12 rounded-xl text-sm outline-none transition-all"
                  style={{ background: '#f1f5f1', border: '1.5px solid #d4e8d7', color: '#1a2d1e' }}
                  onFocus={e => e.target.style.borderColor = '#2d8a43'}
                  onBlur={e => e.target.style.borderColor = '#d4e8d7'}
                />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 transition-colors">
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="px-4 py-3 rounded-xl text-sm"
                style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626' }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2"
              style={{
                background: loading ? '#9ca3af' : 'linear-gradient(135deg, #1e6b30, #2d8a43)',
                color: 'white',
                boxShadow: loading ? 'none' : '0 4px 20px rgba(45,138,67,0.35)',
              }}>
              {loading ? <><Loader2 size={16} className="animate-spin" /> Connexion...</> : 'Se connecter'}
            </button>
          </form>

          <div style={{ height: 1, background: '#e5e7eb', margin: '24px 0' }} />

          <p className="text-center text-sm text-gray-500">
            Pas encore de compte ?{' '}
            <Link to="/register" className="font-semibold transition-colors" style={{ color: '#2d8a43' }}>
              S'inscrire
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
