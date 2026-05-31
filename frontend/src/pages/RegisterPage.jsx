import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import { Loader2, Eye, EyeOff, User, Stethoscope, ShieldCheck, Heart } from 'lucide-react'

const API = 'http://localhost:8000'

const ROLES = [
  { value: 'elderly', label: 'Personne âgée', icon: Heart, desc: 'Je suis la personne surveillée' },
  { value: 'caregiver', label: 'Soignant / Médecin', icon: Stethoscope, desc: 'Je suis un professionnel de santé' },
  { value: 'admin', label: 'Administrateur', icon: ShieldCheck, desc: 'Je gère le système' },
]

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '', phone: '', role: 'elderly' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      // Use a temporary admin token or public registration endpoint
      // Try POST /auth/register first, fallback to POST /users
      try {
        await axios.post(`${API}/auth/register`, form)
      } catch {
        // Some backends expose /users as public for initial setup
        await axios.post(`${API}/users`, form)
      }
      navigate('/login', { state: { registered: true } })
    } catch (err) {
      const detail = err.response?.data?.detail
      if (err.response?.status === 403) {
        setError('Inscription non autorisée. Contactez votre administrateur pour créer un compte.')
      } else if (err.response?.status === 409) {
        setError('Un compte avec cet email existe déjà.')
      } else {
        setError(detail || 'Erreur lors de l\'inscription. Vérifiez vos informations.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: '#f8faf8' }}>
      {/* Left panel — green brand side */}
      <div className="hidden lg:flex w-2/5 flex-col items-center justify-center p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(160deg, #041a08 0%, #0e3d18 50%, #1e6b30 100%)' }}>
        {/* Decorative circles */}
        <div className="absolute top-1/4 -left-20 w-64 h-64 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #4aab60, transparent)' }} />
        <div className="absolute bottom-1/4 -right-10 w-48 h-48 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #c9a84c, transparent)' }} />

        <div className="relative z-10 text-center">
          <div className="w-32 h-32 rounded-3xl flex items-center justify-center mx-auto mb-8"
            style={{ background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.12)' }}>
            <img src="/logo.png" alt="في عينينا" className="w-24 h-24 object-contain" />
          </div>
          <h1 className="font-arabic text-4xl font-bold mb-2"
            style={{ background: 'linear-gradient(135deg, #78c98e, #c9a84c)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            في عينينا
          </h1>
          <p className="text-lg mb-8 font-body" style={{ color: 'rgba(255,255,255,0.7)' }}>
            elderly companion ai
          </p>
          <div className="flex flex-col gap-4 text-left">
            {[
              { icon: '🛡️', text: 'Surveillance 24/7 bienveillante' },
              { icon: '🎙️', text: 'Assistant vocal naturel en français' },
              { icon: '🔒', text: 'Données privées — 100% local' },
              { icon: '👨‍👩‍👧', text: 'Famille alertée en temps réel' },
            ].map((f, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3 rounded-xl"
                style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <span className="text-xl">{f.icon}</span>
                <span className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.85)' }}>{f.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — white form side */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <img src="/logo.png" alt="logo" className="w-12 h-12 object-contain" />
            <div>
              <p className="font-arabic font-bold text-xl" style={{ color: '#1e6b30' }}>في عينينا</p>
              <p className="text-xs text-gray-500">elderly companion ai</p>
            </div>
          </div>

          <h2 className="font-display text-2xl font-bold mb-1" style={{ color: '#1a2d1e' }}>
            Créer un compte
          </h2>
          <p className="text-sm mb-8 text-gray-500">
            Rejoignez le réseau de surveillance bienveillante
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {/* Name + Email */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold mb-2 uppercase tracking-wider text-gray-500">
                  Nom complet
                </label>
                <input
                  className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all"
                  style={{ background: '#f1f5f1', border: '1.5px solid #d4e8d7', color: '#1a2d1e' }}
                  onFocus={e => e.target.style.borderColor = '#2d8a43'}
                  onBlur={e => e.target.style.borderColor = '#d4e8d7'}
                  placeholder="Prénom Nom"
                  value={form.full_name}
                  onChange={e => handleChange('full_name', e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-2 uppercase tracking-wider text-gray-500">
                  Téléphone
                </label>
                <input
                  className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all"
                  style={{ background: '#f1f5f1', border: '1.5px solid #d4e8d7', color: '#1a2d1e' }}
                  onFocus={e => e.target.style.borderColor = '#2d8a43'}
                  onBlur={e => e.target.style.borderColor = '#d4e8d7'}
                  placeholder="+216..."
                  value={form.phone}
                  onChange={e => handleChange('phone', e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider text-gray-500">
                Email
              </label>
              <input
                type="email"
                className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all"
                style={{ background: '#f1f5f1', border: '1.5px solid #d4e8d7', color: '#1a2d1e' }}
                onFocus={e => e.target.style.borderColor = '#2d8a43'}
                onBlur={e => e.target.style.borderColor = '#d4e8d7'}
                placeholder="votre@email.com"
                value={form.email}
                onChange={e => handleChange('email', e.target.value)}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider text-gray-500">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  className="w-full px-4 py-3 pr-12 rounded-xl text-sm outline-none transition-all"
                  style={{ background: '#f1f5f1', border: '1.5px solid #d4e8d7', color: '#1a2d1e' }}
                  onFocus={e => e.target.style.borderColor = '#2d8a43'}
                  onBlur={e => e.target.style.borderColor = '#d4e8d7'}
                  placeholder="Minimum 8 caractères"
                  value={form.password}
                  onChange={e => handleChange('password', e.target.value)}
                  required
                />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 transition-colors">
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Role selection */}
            <div>
              <label className="block text-xs font-semibold mb-3 uppercase tracking-wider text-gray-500">
                Votre rôle
              </label>
              <div className="grid grid-cols-2 gap-2">
                {ROLES.map(({ value, label, icon: Icon, desc }) => {
                  const active = form.role === value
                  return (
                    <button key={value} type="button" onClick={() => handleChange('role', value)}
                      className="flex flex-col items-start gap-1 p-3 rounded-xl transition-all text-left"
                      style={{
                        background: active ? '#f0faf2' : '#f8faf8',
                        border: `1.5px solid ${active ? '#2d8a43' : '#e2ece4'}`,
                      }}>
                      <div className="flex items-center gap-2">
                        <Icon size={15} style={{ color: active ? '#2d8a43' : '#9ca3af' }} />
                        <span className="text-xs font-semibold" style={{ color: active ? '#1e6b30' : '#374151' }}>
                          {label}
                        </span>
                      </div>
                      <span className="text-xs" style={{ color: '#9ca3af' }}>{desc}</span>
                    </button>
                  )
                })}
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
              {loading ? <><Loader2 size={16} className="animate-spin" /> Création...</> : 'Créer mon compte'}
            </button>
          </form>

          <p className="text-center text-sm mt-6 text-gray-500">
            Déjà inscrit ?{' '}
            <Link to="/login" className="font-semibold transition-colors" style={{ color: '#2d8a43' }}>
              Se connecter
            </Link>
          </p>

          <p className="text-center text-xs mt-4 text-gray-400">
            Note: La création de compte peut nécessiter l'approbation d'un administrateur.
          </p>
        </div>
      </div>
    </div>
  )
}
