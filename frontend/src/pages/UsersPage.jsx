import { useEffect, useState, Fragment } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { UserPlus, Trash2, Shield, Loader2, ChevronDown, ChevronUp, UserCheck, X, Plus } from 'lucide-react'

const EMPTY_CARER_FORM_LOCAL = { email: '', password: '', full_name: '', phone: '' }

function CarerForm({ elderlyId, API, onSuccess, onCancel }) {
  const [form, setForm]       = useState(EMPTY_CARER_FORM_LOCAL)
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await axios.post(`${API}/users/${elderlyId}/caregivers`, form)
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la création')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}
      className="grid grid-cols-2 gap-3 mb-4 p-3 rounded-xl"
      style={{ background: 'rgba(96,165,250,0.05)', border: '1px solid rgba(96,165,250,0.12)' }}>
      <div>
        <label className="block text-xs font-semibold mb-1 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Nom complet</label>
        <input className="input-field" value={form.full_name}
          onChange={e => setForm(p => ({ ...p, full_name: e.target.value }))} required />
      </div>
      <div>
        <label className="block text-xs font-semibold mb-1 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Email</label>
        <input type="email" className="input-field" value={form.email}
          onChange={e => setForm(p => ({ ...p, email: e.target.value }))} required />
      </div>
      <div>
        <label className="block text-xs font-semibold mb-1 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Mot de passe</label>
        <input type="password" className="input-field" value={form.password}
          onChange={e => setForm(p => ({ ...p, password: e.target.value }))} required />
      </div>
      <div>
        <label className="block text-xs font-semibold mb-1 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Téléphone (WhatsApp)</label>
        <input className="input-field" value={form.phone}
          onChange={e => setForm(p => ({ ...p, phone: e.target.value }))} placeholder="+216..." />
      </div>
      {error && (
        <div className="col-span-2 px-3 py-2 rounded-lg text-xs"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}>
          {error}
        </div>
      )}
      <div className="col-span-2 flex gap-2">
        <button type="submit" disabled={saving}
          className="px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2"
          style={{ background: '#60a5fa', color: '#fff', opacity: saving ? 0.7 : 1 }}>
          {saving ? <><Loader2 size={12} className="animate-spin" /> Création...</> : 'Créer le soignant'}
        </button>
        <button type="button" onClick={onCancel}
          className="px-4 py-2 rounded-xl text-xs font-semibold transition-all"
          style={{ background: 'rgba(239,68,68,0.08)', color: '#f87171' }}>
          Annuler
        </button>
      </div>
    </form>
  )
}

const ROLE_CONFIG = {
  elderly:   { label: 'Personne âgée',  color: '#78c98e' },
  caregiver: { label: 'Soignant',       color: '#60a5fa' },
  admin:     { label: 'Administrateur', color: '#c9a84c' },
}

const EMPTY_USER_FORM = { email: '', password: '', full_name: '', phone: '', role: 'elderly' }

export default function UsersPage() {
  const { user: me, API } = useAuth()
  const [users, setUsers]           = useState([])
  const [loading, setLoading]       = useState(true)
  const [showForm, setShowForm]     = useState(false)
  const [form, setForm]             = useState(EMPTY_USER_FORM)
  const [creating, setCreating]     = useState(false)
  const [formError, setFormError]   = useState('')

  // Expanded elderly panel state
  const [expandedElderly, setExpandedElderly] = useState(null)
  // Per-elderly: caregivers list
  const [elderlyCarers, setElderlyCarers]     = useState({})
  // Per-elderly: show/hide add-caregiver inline form
  const [showCarerForm, setShowCarerForm]     = useState(null)

  const navigate = useNavigate()
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

  // Load caregivers for an elderly user
  const fetchCarers = async (elderlyId) => {
    try {
      const res = await axios.get(`${API}/users/${elderlyId}/caregivers`)
      setElderlyCarers(prev => ({ ...prev, [elderlyId]: res.data || [] }))
    } catch {
      setElderlyCarers(prev => ({ ...prev, [elderlyId]: [] }))
    }
  }

  const toggleElderlyPanel = async (elderlyId) => {
    if (expandedElderly === elderlyId) {
      setExpandedElderly(null)
      setShowCarerForm(null)
    } else {
      setExpandedElderly(elderlyId)
      setShowCarerForm(null)
      await fetchCarers(elderlyId)
    }
  }

  // Create an elderly or admin user
  const handleCreate = async (e) => {
    e.preventDefault()
    setCreating(true)
    setFormError('')
    try {
      await axios.post(`${API}/users`, form)
      setShowForm(false)
      setForm(EMPTY_USER_FORM)
      fetchUsers()
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Erreur lors de la création')
    } finally {
      setCreating(false)
    }
  }

  // Unlink a caregiver from an elderly person
  const handleUnlinkCarer = async (elderlyId, carerId) => {
    if (!confirm('Dissocier ce soignant ?')) return
    try {
      await axios.delete(`${API}/users/${elderlyId}/caregivers/${carerId}`)
      await fetchCarers(elderlyId)
      fetchUsers()
    } catch {}
  }

  const handleDelete = async (id) => {
    if (!confirm('Supprimer cet utilisateur ?')) return
    try {
      await axios.delete(`${API}/users/${id}`)
      if (expandedElderly === id) setExpandedElderly(null)
      fetchUsers()
    } catch {}
  }

  const handleGdprErase = async (id) => {
    if (!confirm('Effacer toutes les données (RGPD) ? Cette action est irréversible.')) return
    try { await axios.delete(`${API}/users/${id}/data`); fetchUsers() } catch {}
  }

  const handleConsent = async (id, value) => {
    try { await axios.post(`${API}/users/${id}/consent`, { consent_given: value }); fetchUsers() } catch {}
  }

  const elderlyUsers   = users.filter(u => u.role === 'elderly')
  const adminUsers     = users.filter(u => u.role === 'admin')
  const caregiverUsers = users.filter(u => u.role === 'caregiver')

  const Section = ({ title, count, color, children }) => (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-3 px-1">
        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
        <h2 className="font-display font-semibold text-sm" style={{ color: 'var(--text2)' }}>
          {title} <span className="font-normal" style={{ color: 'var(--muted)' }}>({count})</span>
        </h2>
      </div>
      {children}
    </div>
  )

  return (
    <div className="p-8 max-w-5xl mx-auto">

      {/* Page header */}
      <div className="flex items-center justify-between mb-8 animate-fade-up">
        <div>
          <h1 className="font-display text-3xl font-bold mb-1" style={{ color: 'var(--text)' }}>Utilisateurs</h1>
          <p className="text-sm" style={{ color: 'var(--text2)' }}>
            Gestion des comptes · RGPD · Consentements
          </p>
        </div>
        {isAdmin && (
          <button onClick={() => { setShowForm(!showForm); setFormError('') }}
            className="btn-primary flex items-center gap-2">
            <UserPlus size={15} />
            Nouvel utilisateur
          </button>
        )}
      </div>

      {/* ── Create user form (elderly / admin only) ── */}
      {showForm && isAdmin && (
        <div className="glass rounded-2xl p-6 mb-6 animate-slide-down">
          <h3 className="font-display font-semibold mb-1" style={{ color: 'var(--text)' }}>Créer un utilisateur</h3>
          <p className="text-xs mb-4" style={{ color: 'var(--muted)' }}>
            Les soignants sont créés via le bouton <strong>+ Soignant</strong> sur chaque résident.
          </p>
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

            {/* Role — only elderly or admin */}
            <div className="col-span-2">
              <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Rôle</label>
              <div className="flex gap-2">
                {['elderly', 'admin'].map(key => {
                  const cfg = ROLE_CONFIG[key]
                  return (
                    <button key={key} type="button" onClick={() => setForm(p => ({ ...p, role: key }))}
                      className="flex-1 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all"
                      style={{
                        background: form.role === key ? `${cfg.color}20` : 'rgba(255,255,255,0.5)',
                        border: `1px solid ${form.role === key ? cfg.color + '50' : 'rgba(45,120,45,0.15)'}`,
                        color: form.role === key ? cfg.color : 'var(--muted)',
                      }}>
                      {cfg.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {formError && (
              <div className="col-span-2 px-4 py-3 rounded-xl text-sm"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171' }}>
                {formError}
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

      {loading ? (
        <div className="glass rounded-2xl py-16 text-center">
          <Loader2 size={24} className="animate-spin mx-auto mb-2" style={{ color: 'var(--green)' }} />
          <p className="text-sm" style={{ color: 'var(--muted)' }}>Chargement...</p>
        </div>
      ) : users.length === 0 ? (
        <div className="glass rounded-2xl py-16 text-center">
          <p className="text-3xl mb-2">👥</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>Aucun utilisateur</p>
        </div>
      ) : (
        <>
          {/* ── RÉSIDENTS (elderly) ── */}
          <Section title="Résidents" count={elderlyUsers.length} color={ROLE_CONFIG.elderly.color}>
            <div className="glass rounded-2xl overflow-hidden animate-fade-up">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Résident</th>
                    <th>Consentement <span className="font-normal text-xs" style={{ color: 'var(--muted)' }}>(RGPD)</span></th>
                    <th>Soignants</th>
                    {isAdmin && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {elderlyUsers.length === 0 ? (
                    <tr><td colSpan={4} className="text-center py-8" style={{ color: 'var(--muted)' }}>Aucun résident</td></tr>
                  ) : elderlyUsers.map((u, i) => {
                    const isExpanded = expandedElderly === u.id
                    const carers = elderlyCarers[u.id] || []
                    const cfg = ROLE_CONFIG.elderly

                    return (
                      <Fragment key={u.id}>
                        <tr className="animate-fade-up" style={{ animationDelay: `${i * 0.04}s` }}>
                          <td>
                            <button onClick={() => navigate(`/profile/${u.id}`)}
                              className="flex items-center gap-3 text-left w-full transition-all"
                              onMouseEnter={e => e.currentTarget.style.opacity = '0.75'}
                              onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
                              <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                                style={{ background: `${cfg.color}20`, color: cfg.color }}>
                                {u.full_name?.[0] || '?'}
                              </div>
                              <div>
                                <p className="font-medium text-sm" style={{ color: 'var(--text)' }}>{u.full_name}</p>
                                <p className="text-xs" style={{ color: 'var(--muted)' }}>{u.email}</p>
                              </div>
                            </button>
                          </td>
                          <td>
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
                              style={{
                                background: u.consent_given ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                                color: u.consent_given ? 'var(--ok)' : 'var(--danger)',
                                border: `1px solid ${u.consent_given ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                              }}>
                              {u.consent_given ? '✓ Donné' : '✗ Refusé'}
                            </span>
                          </td>
                          <td>
                            <button onClick={() => toggleElderlyPanel(u.id)}
                              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                              style={{
                                background: isExpanded ? 'rgba(96,165,250,0.1)' : 'rgba(255,255,255,0.5)',
                                color: isExpanded ? '#60a5fa' : 'var(--muted)',
                                border: `1px solid ${isExpanded ? 'rgba(96,165,250,0.3)' : 'rgba(45,120,45,0.12)'}`,
                              }}>
                              <UserCheck size={12} />
                              Soignants ({(elderlyCarers[u.id] || []).length})
                              {isExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                            </button>
                          </td>
                          {isAdmin && (
                            <td>
                              <div className="flex items-center gap-1">
                                <button onClick={() => handleGdprErase(u.id)} title="Effacer données RGPD"
                                  className="p-1.5 rounded-lg transition-all" style={{ color: 'var(--muted)' }}
                                  onMouseEnter={e => e.currentTarget.style.color = '#f59e0b'}
                                  onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                                  <Shield size={13} />
                                </button>
                                <button onClick={() => handleDelete(u.id)} title="Supprimer"
                                  className="p-1.5 rounded-lg transition-all" style={{ color: 'var(--muted)' }}
                                  onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                                  onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                                  <Trash2 size={13} />
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>

                        {/* ── Caregivers panel for this elderly ── */}
                        {isExpanded && (
                          <tr key={`${u.id}-carers`}>
                            <td colSpan={isAdmin ? 4 : 3} style={{ padding: '0 12px 12px', background: 'rgba(96,165,250,0.03)' }}>
                              <div className="rounded-xl p-4" style={{ border: '1px solid rgba(96,165,250,0.15)', background: 'rgba(255,255,255,0.55)' }}>

                                <div className="flex items-center justify-between mb-3">
                                  <p className="text-xs font-semibold" style={{ color: 'var(--text2)' }}>
                                    Soignants de <span style={{ color: ROLE_CONFIG.elderly.color }}>{u.full_name}</span>
                                  </p>
                                  {isAdmin && (
                                    <button
                                      onClick={() => {
                                        setShowCarerForm(showCarerForm === u.id ? null : u.id)
                                        setCarerForm(EMPTY_CARER_FORM)
                                        setCarerError('')
                                      }}
                                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                                      style={{
                                        background: showCarerForm === u.id ? 'rgba(96,165,250,0.15)' : 'rgba(96,165,250,0.08)',
                                        color: '#60a5fa',
                                        border: '1px solid rgba(96,165,250,0.25)',
                                      }}>
                                      {showCarerForm === u.id ? <X size={11} /> : <Plus size={11} />}
                                      {showCarerForm === u.id ? 'Annuler' : '+ Soignant'}
                                    </button>
                                  )}
                                </div>

                                {/* Inline create-caregiver form — own component so typing doesn't re-render the table */}
                                {isAdmin && showCarerForm === u.id && (
                                  <CarerForm
                                    elderlyId={u.id}
                                    API={API}
                                    onSuccess={async () => { setShowCarerForm(null); await fetchCarers(u.id); fetchUsers() }}
                                    onCancel={() => setShowCarerForm(null)}
                                  />
                                )}

                                {/* Caregivers list */}
                                {carers.length === 0 ? (
                                  <p className="text-xs py-2" style={{ color: 'var(--muted)' }}>
                                    Aucun soignant assigné — utilisez le bouton + Soignant ci-dessus.
                                  </p>
                                ) : (
                                  <div className="flex flex-col gap-2">
                                    {carers.map(c => (
                                      <div key={c.id} className="flex items-center gap-3 px-3 py-2 rounded-xl"
                                        style={{ background: 'rgba(96,165,250,0.07)', border: '1px solid rgba(96,165,250,0.15)' }}>
                                        <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                                          style={{ background: 'rgba(96,165,250,0.15)', color: '#60a5fa' }}>
                                          {c.full_name?.[0] || '?'}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                          <button onClick={() => navigate(`/profile/${c.id}`)}
                                            className="text-xs font-semibold truncate block text-left transition-all"
                                            style={{ color: 'var(--text)' }}
                                            onMouseEnter={e => e.currentTarget.style.color = '#60a5fa'}
                                            onMouseLeave={e => e.currentTarget.style.color = 'var(--text)'}>
                                            {c.full_name}
                                          </button>
                                          <p className="text-xs truncate" style={{ color: 'var(--muted)' }}>
                                            {c.email}{c.phone ? ` · ${c.phone}` : ''}
                                          </p>
                                        </div>
                                        {isAdmin && (
                                          <button onClick={() => handleUnlinkCarer(u.id, c.id)}
                                            title="Dissocier ce soignant"
                                            className="p-1 rounded-lg transition-all flex-shrink-0"
                                            style={{ color: 'var(--muted)' }}
                                            onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                                            onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                                            <X size={13} />
                                          </button>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Section>

          {/* ── ADMINS ── */}
          {adminUsers.length > 0 && (
            <Section title="Administrateurs" count={adminUsers.length} color={ROLE_CONFIG.admin.color}>
              <div className="glass rounded-2xl overflow-hidden animate-fade-up delay-100">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Administrateur</th>
                      <th>Consentement</th>
                      {isAdmin && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {adminUsers.map((u, i) => {
                      const cfg = ROLE_CONFIG.admin
                      return (
                        <tr key={u.id} className="animate-fade-up" style={{ animationDelay: `${i * 0.04}s` }}>
                          <td>
                            <button onClick={() => navigate(`/profile/${u.id}`)}
                              className="flex items-center gap-3 text-left w-full transition-all"
                              onMouseEnter={e => e.currentTarget.style.opacity = '0.75'}
                              onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
                              <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                                style={{ background: `${cfg.color}20`, color: cfg.color }}>
                                {u.full_name?.[0] || '?'}
                              </div>
                              <div>
                                <p className="font-medium text-sm" style={{ color: 'var(--text)' }}>{u.full_name}</p>
                                <p className="text-xs" style={{ color: 'var(--muted)' }}>{u.email}</p>
                              </div>
                            </button>
                          </td>
                          <td>
                            <span style={{ color: u.consent_given ? 'var(--ok)' : 'var(--danger)', fontSize: 12 }}>
                              {u.consent_given ? '✓ Donné' : '✗ Refusé'}
                            </span>
                          </td>
                          {isAdmin && (
                            <td>
                              <div className="flex items-center gap-1">
                                <button onClick={() => handleGdprErase(u.id)} title="Effacer données RGPD"
                                  className="p-1.5 rounded-lg transition-all" style={{ color: 'var(--muted)' }}
                                  onMouseEnter={e => e.currentTarget.style.color = '#f59e0b'}
                                  onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                                  <Shield size={13} />
                                </button>
                                {me?.id !== u.id && (
                                  <button onClick={() => handleDelete(u.id)} title="Supprimer"
                                    className="p-1.5 rounded-lg transition-all" style={{ color: 'var(--muted)' }}
                                    onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                                    onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                                    <Trash2 size={13} />
                                  </button>
                                )}
                              </div>
                            </td>
                          )}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Section>
          )}

          {/* ── SOIGNANTS (read-only list — managed via elderly panel) ── */}
          {caregiverUsers.length > 0 && (
            <Section title="Soignants" count={caregiverUsers.length} color={ROLE_CONFIG.caregiver.color}>
              <div className="glass rounded-2xl overflow-hidden animate-fade-up delay-200">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Soignant</th>
                      <th>Contact</th>
                      <th>Consentement</th>
                      {isAdmin && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {caregiverUsers.map((u, i) => {
                      const cfg = ROLE_CONFIG.caregiver
                      return (
                        <tr key={u.id} className="animate-fade-up" style={{ animationDelay: `${i * 0.04}s` }}>
                          <td>
                            <button onClick={() => navigate(`/profile/${u.id}`)}
                              className="flex items-center gap-3 text-left w-full transition-all"
                              onMouseEnter={e => e.currentTarget.style.opacity = '0.75'}
                              onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
                              <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                                style={{ background: `${cfg.color}20`, color: cfg.color }}>
                                {u.full_name?.[0] || '?'}
                              </div>
                              <div>
                                <p className="font-medium text-sm" style={{ color: 'var(--text)' }}>{u.full_name}</p>
                                <p className="text-xs" style={{ color: 'var(--muted)' }}>{u.email}</p>
                              </div>
                            </button>
                          </td>
                          <td>
                            <span className="text-xs" style={{ color: 'var(--muted)' }}>{u.phone || '—'}</span>
                          </td>
                          <td>
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
                              style={{
                                background: u.consent_given ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                                color: u.consent_given ? 'var(--ok)' : 'var(--danger)',
                                border: `1px solid ${u.consent_given ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                              }}>
                              {u.consent_given ? '✓ Donné' : '✗ Refusé'}
                            </span>
                          </td>
                          {isAdmin && (
                            <td>
                              <div className="flex items-center gap-1">
                                <button onClick={() => handleGdprErase(u.id)} title="Effacer données RGPD"
                                  className="p-1.5 rounded-lg transition-all" style={{ color: 'var(--muted)' }}
                                  onMouseEnter={e => e.currentTarget.style.color = '#f59e0b'}
                                  onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                                  <Shield size={13} />
                                </button>
                                <button onClick={() => handleDelete(u.id)} title="Supprimer"
                                  className="p-1.5 rounded-lg transition-all" style={{ color: 'var(--muted)' }}
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
              </div>
            </Section>
          )}
        </>
      )}

      {/* RGPD note */}
      <div className="mt-4 px-4 py-3 rounded-xl animate-fade-up"
        style={{ background: 'rgba(255,255,255,0.5)', border: '1px solid rgba(45,120,45,0.1)' }}>
        <p className="text-xs" style={{ color: 'var(--muted)' }}>
          <span className="font-semibold" style={{ color: 'var(--text2)' }}>Consentement RGPD</span> — Le consentement
          indique que l'utilisateur a accepté la collecte et le traitement de ses données personnelles pour la
          surveillance et l'assistance. Sans consentement, les données de surveillance ne peuvent pas être collectées légalement.
        </p>
      </div>
    </div>
  )
}
