import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import { Loader2, Eye, EyeOff, Heart, Stethoscope, ShieldCheck } from 'lucide-react'

const API = 'http://127.0.0.1:8000'

const ROLES = [
  { value: 'elderly',   label: 'Personne âgée',      icon: Heart,        desc: 'Je suis la personne surveillée' },
  { value: 'caregiver', label: 'Soignant / Médecin',  icon: Stethoscope,  desc: 'Professionnel de santé' },
  { value: 'admin',     label: 'Administrateur',       icon: ShieldCheck,  desc: 'Je gère le système' },
]

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    full_name: '', email: '', password: '', phone: '', role: 'elderly', consent_given: false,
  })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleChange = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await axios.post(`${API}/auth/register`, form)
      navigate('/login', { state: { registered: true } })
    } catch (err) {
      if (err.response?.status === 409) setError('Un compte avec cet email existe déjà.')
      else if (!err.response) setError('Impossible de joindre le serveur.')
      else setError(err.response?.data?.detail || "Erreur lors de l'inscription.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full blur-3xl opacity-30"
          style={{ background: 'radial-gradient(circle, rgba(5,150,105,0.15), transparent)' }} />
        <div className="absolute bottom-1/3 right-1/4 w-72 h-72 rounded-full blur-3xl opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(8,145,178,0.12), transparent)' }} />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="flex flex-col items-center mb-8">
          <h1 className="font-arabic text-4xl font-bold text-gradient mb-1">في عينينا</h1>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>elderly companion ai</p>
        </div>

        <div className="glass rounded-2xl p-8">
          <h2 className="font-display text-xl font-bold mb-1" style={{ color: 'var(--text)' }}>Créer un compte</h2>
          <p className="text-sm mb-6" style={{ color: 'var(--muted)' }}>
            Rejoignez le réseau de surveillance bienveillante
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Nom complet</label>
                <input className="input-field" placeholder="Prénom Nom" value={form.full_name}
                  onChange={e => handleChange('full_name', e.target.value)} required />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Téléphone</label>
                <input className="input-field" placeholder="+216..." value={form.phone}
                  onChange={e => handleChange('phone', e.target.value)} />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Email</label>
              <input type="email" className="input-field" placeholder="votre@email.com" value={form.email}
                onChange={e => handleChange('email', e.target.value)} required />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Mot de passe</label>
              <div className="relative">
                <input type={showPass ? 'text' : 'password'} className="input-field pr-12"
                  placeholder="••••••••" value={form.password}
                  onChange={e => handleChange('password', e.target.value)} required />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 transition-colors"
                  style={{ color: 'var(--muted)' }}>
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Rôle</label>
              <div className="flex flex-col gap-2">
                {ROLES.map(({ value, label, icon: Icon, desc }) => {
                  const active = form.role === value
                  return (
                    <label key={value} className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all"
                      style={{
                        background: active ? 'rgba(30,107,46,0.1)' : 'rgba(255,255,255,0.5)',
                        border: `1px solid ${active ? 'rgba(30,107,46,0.3)' : 'rgba(45,120,45,0.12)'}`,
                      }}>
                      <input type="radio" name="role" value={value} checked={active}
                        onChange={() => handleChange('role', value)} className="hidden" />
                      <Icon size={14} style={{ color: active ? 'var(--green)' : 'var(--muted)', flexShrink: 0 }} />
                      <div>
                        <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>{label}</p>
                        <p className="text-xs" style={{ color: 'var(--muted)' }}>{desc}</p>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>

            {/* RGPD Consent */}
            <label className="flex items-start gap-3 px-4 py-3 rounded-xl cursor-pointer transition-all"
              style={{
                background: form.consent_given ? 'rgba(30,107,46,0.08)' : 'rgba(255,255,255,0.5)',
                border: `1px solid ${form.consent_given ? 'rgba(30,107,46,0.25)' : 'rgba(45,120,45,0.12)'}`,
              }}>
              <input
                type="checkbox"
                checked={form.consent_given}
                onChange={e => handleChange('consent_given', e.target.checked)}
                className="mt-0.5 flex-shrink-0"
                style={{ accentColor: 'var(--green)', width: 15, height: 15 }}
              />
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                  Consentement RGPD
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                  J'accepte que mes données (conversations, alertes, surveillance) soient collectées et traitées à des fins d'assistance et de sécurité, conformément au RGPD.
                </p>
              </div>
            </label>

            {error && (
              <div className="px-4 py-3 rounded-xl text-sm"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary flex items-center justify-center gap-2 mt-1">
              {loading ? <><Loader2 size={16} className="animate-spin" /> Création...</> : 'Créer mon compte'}
            </button>
          </form>

          <div style={{ height: 1, background: 'rgba(45,120,45,0.1)', margin: '24px 0' }} />
          <p className="text-center text-sm" style={{ color: 'var(--muted)' }}>
            Déjà inscrit ?{' '}
            <Link to="/login" className="font-semibold" style={{ color: 'var(--green-light)' }}>Se connecter</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
