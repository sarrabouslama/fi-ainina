import { useEffect, useState } from 'react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { UserPlus, Trash2, Shield, Heart, User, Loader2 } from 'lucide-react'

const ROLE_CONFIG = {
  elderly: { icon: '👴', label: 'Personne âgée', color: '#78c98e' },
  caregiver: { icon: '👩‍⚕️', label: 'Soignant', color: '#60a5fa' },
  admin: { icon: '⚙️', label: 'Administrateur', color: '#c9a84c' },
  family: { icon: '👨‍👩‍👧', label: 'Famille', color: '#f9a8d4' },
}

export default function UsersPage() {
  const { user: me, API } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '', role: 'elderly' })
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const isAdmin = me?.role === 'admin'

  const fetchUsers = async () => {
    try {
      const res = await axios.get(`${API}/users`)
      setUsers(res.data || [])
    } catch {
      setUsers([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      await axios.post(`${API}/users`, form)
      setShowForm(false)
      setForm({ email: '', password: '', full_name: '', phone: '', role: 'elderly' })
      fetchUsers()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la création')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Supprimer cet utilisateur ?')) return
    try { await axios.delete(`${API}/users/${id}`); fetchUsers() } catch {}
  }

  const handleGdprErase = async (id) => {
    if (!confirm('Effacer toutes les données (RGPD) ? Cette action est irréversible.')) return
    try { await axios.delete(`${API}/users/${id}/data`); fetchUsers() } catch {}
  }

  const handleConsent = async (id, value) => {
    try { await axios.post(`${API}/users/${id}/consent`, { consent_given: value }); fetchUsers() } catch {}
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-8 animate-fade-up">
        <div>
          <h1 className="font-display text-3xl font-bold text-white mb-1">Utilisateurs</h1>
          <p className="text-sm" style={{ color: 'var(--text2)' }}>
            Gestion des comptes · RGPD · Consentements
          </p>
        </div>
        {isAdmin && (
          <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
            <UserPlus size={15} />
            Nouvel utilisateur
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && isAdmin && (
        <div className="glass rounded-2xl p-6 mb-6 animate-slide-down">
          <h3 className="font-display font-semibold text-white mb-4">Créer un utilisateur</h3>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Nom complet</label>
              <input className="input-field" value={form.full_name} onChange={e => setForm(p => ({ ...p, full_name: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Email</label>
              <input type="email" className="input-field" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Mot de passe</label>
              <input type="password" className="input-field" value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Téléphone</label>
              <input className="input-field" value={form.phone} onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} placeholder="+216..." />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Rôle</label>
              <div className="flex gap-2">
                {Object.entries(ROLE_CONFIG).map(([key, cfg]) => (
                  <button key={key} type="button" onClick={() => setForm(p => ({ ...p, role: key }))}
                    className="flex-1 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all"
                    style={{
                      background: form.role === key ? `${cfg.color}20` : 'rgba(7,43,14,0.4)',
                      border: `1px solid ${form.role === key ? cfg.color + '50' : 'var(--border)'}`,
                      color: form.role === key ? cfg.color : 'var(--muted)',
                    }}>
                    {cfg.icon} {cfg.label}
                  </button>
                ))}
              </div>
            </div>
            {error && (
              <div className="col-span-2 px-4 py-3 rounded-xl text-sm"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171' }}>
                {error}
              </div>
            )}
            <div className="col-span-2 flex gap-3">
              <button type="submit" disabled={creating} className="btn-primary flex items-center gap-2">
                {creating ? <><Loader2 size={14} className="animate-spin" /> Création...</> : 'Créer'}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Annuler</button>
            </div>
          </form>
        </div>
      )}

      {/* Users table */}
      <div className="glass rounded-2xl overflow-hidden animate-fade-up delay-100">
        {loading ? (
          <div className="text-center py-16">
            <Loader2 size={24} className="animate-spin mx-auto mb-2" style={{ color: 'var(--green)' }} />
            <p className="text-sm" style={{ color: 'var(--muted)' }}>Chargement...</p>
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-3xl mb-2">👥</p>
            <p className="text-sm" style={{ color: 'var(--muted)' }}>Aucun utilisateur</p>
            {!isAdmin && <p className="text-xs mt-1" style={{ color: 'var(--border2)' }}>Accès administrateur requis</p>}
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Utilisateur</th>
                <th>Rôle</th>
                <th>Consentement</th>
                <th>Alertes actives</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {users.map((u, i) => {
                const cfg = ROLE_CONFIG[u.role] || ROLE_CONFIG.family
                return (
                  <tr key={u.id} className="animate-fade-up" style={{ animationDelay: `${i * 0.04}s` }}>
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                          style={{ background: `${cfg.color}20`, color: cfg.color }}>
                          {u.full_name?.[0] || '?'}
                        </div>
                        <div>
                          <p className="font-medium text-white text-sm">{u.full_name}</p>
                          <p className="text-xs" style={{ color: 'var(--muted)' }}>{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
                        style={{ background: `${cfg.color}15`, color: cfg.color, border: `1px solid ${cfg.color}30` }}>
                        {cfg.icon} {cfg.label}
                      </span>
                    </td>
                    <td>
                      {isAdmin ? (
                        <button onClick={() => handleConsent(u.id, !u.consent_given)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-all"
                          style={{
                            background: u.consent_given ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                            color: u.consent_given ? 'var(--ok)' : 'var(--danger)',
                            border: `1px solid ${u.consent_given ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                          }}>
                          {u.consent_given ? '✓ Donné' : '✗ Refusé'}
                        </button>
                      ) : (
                        <span style={{ color: u.consent_given ? 'var(--ok)' : 'var(--danger)', fontSize: 12 }}>
                          {u.consent_given ? '✓ Donné' : '✗ Refusé'}
                        </span>
                      )}
                    </td>
                    <td>
                      <span className="font-bold" style={{ color: u.active_alerts > 0 ? 'var(--danger)' : 'var(--muted)' }}>
                        {u.active_alerts ?? '—'}
                      </span>
                    </td>
                    {isAdmin && (
                      <td>
                        <div className="flex items-center gap-1">
                          <button onClick={() => handleGdprErase(u.id)}
                            title="Effacer données RGPD"
                            className="p-1.5 rounded-lg transition-all"
                            style={{ color: 'var(--muted)' }}
                            onMouseEnter={e => e.currentTarget.style.color = '#f59e0b'}
                            onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                            <Shield size={13} />
                          </button>
                          <button onClick={() => handleDelete(u.id)}
                            title="Supprimer"
                            className="p-1.5 rounded-lg transition-all"
                            style={{ color: 'var(--muted)' }}
                            onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                            onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
