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
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full blur-3xl opacity-30"
          style={{ background: 'radial-gradient(circle, rgba(5,150,105,0.15), transparent)' }} />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full blur-3xl opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(8,145,178,0.12), transparent)' }} />
        <div className="absolute top-1/2 right-1/3 w-64 h-64 rounded-full blur-3xl opacity-15"
          style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.08), transparent)' }} />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Big logo — centered, no text beside it */}
        <div className="flex flex-col items-center mb-8">
          <h1 className="font-arabic text-4xl font-bold text-gradient mb-1">في عينينا</h1>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>elderly companion ai</p>
        </div>

        <div className="glass rounded-2xl p-8">
          <h2 className="font-display text-xl font-bold text-white mb-1">Connexion</h2>
          <p className="text-sm mb-6" style={{ color: 'var(--muted)' }}>
            Accédez à votre espace de surveillance
          </p>

          {registered && (
            <div className="mb-5 px-4 py-3 rounded-xl text-sm"
              style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', color: 'var(--ok)' }}>
              Compte créé. Connectez-vous maintenant.
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>
                Email
              </label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="votre@email.com" required className="input-field" />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>
                Mot de passe
              </label>
              <div className="relative">
                <input type={showPass ? 'text' : 'password'} value={password}
                  onChange={e => setPassword(e.target.value)} placeholder="••••••••"
                  required className="input-field pr-12" />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 transition-colors"
                  style={{ color: 'var(--muted)' }}>
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="px-4 py-3 rounded-xl text-sm"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary flex items-center justify-center gap-2 mt-1">
              {loading ? <><Loader2 size={16} className="animate-spin" /> Connexion...</> : 'Se connecter'}
            </button>
          </form>

          <div style={{ height: 1, background: 'rgba(99,179,237,0.1)', margin: '24px 0' }} />
          <p className="text-center text-sm" style={{ color: 'var(--muted)' }}>
            Pas encore de compte ?{' '}
            <Link to="/register" className="font-semibold" style={{ color: 'var(--green-light)' }}>S'inscrire</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
