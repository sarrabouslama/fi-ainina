import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { Loader2, Save, Lock, ShieldCheck, UserCheck, Plus, X, Trash2, ArrowLeft } from 'lucide-react'

const ROLE_CONFIG = {
  admin:     { label: 'Administrateur', color: '#f59e0b' },
  caregiver: { label: 'Soignant',       color: '#60a5fa' },
  elderly:   { label: 'Résident',       color: '#10b981' },
}

function Card({ title, icon: Icon, iconColor, children }) {
  return (
    <div className="glass rounded-2xl p-6 animate-fade-up">
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${iconColor}15`, border: `1px solid ${iconColor}25` }}>
          <Icon size={15} style={{ color: iconColor }} />
        </div>
        <h2 className="font-display font-semibold text-sm" style={{ color: 'var(--text)' }}>{title}</h2>
      </div>
      {children}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function StatusMsg({ msg }) {
  if (!msg) return null
  return (
    <div className="px-3 py-2 rounded-xl text-xs font-medium"
      style={{
        background: msg.ok ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
        color: msg.ok ? 'var(--ok)' : 'var(--danger)',
      }}>
      {msg.ok ? '✓ ' : '✗ '}{msg.text}
    </div>
  )
}

export default function ProfilePage() {
  const { userId: paramUserId } = useParams()
  const { user: me, API, refreshUser } = useAuth()
  const navigate = useNavigate()

  // Which user are we viewing?
  const targetId = paramUserId || me?.id
  const isSelf   = targetId === me?.id
  const isAdmin  = me?.role === 'admin'

  // Permissions
  const canEditInfo     = isSelf || isAdmin  // edit name/phone
  const canChangePass   = isSelf             // password: self only
  const canChangeConsent = isSelf            // consent: self only
  const canManageCarers = isSelf || isAdmin  // caregiver list for elderly

  // Target user data
  const [target, setTarget]     = useState(isSelf ? me : null)
  const [fetching, setFetching] = useState(!isSelf)

  const loadTarget = async () => {
    if (isSelf) { setTarget(me); return }
    setFetching(true)
    try {
      const r = await axios.get(`${API}/users/${targetId}`)
      setTarget(r.data)
    } catch {
      navigate(-1)
    } finally {
      setFetching(false)
    }
  }

  useEffect(() => { loadTarget() }, [targetId])
  // Keep self-profile in sync when me changes
  useEffect(() => { if (isSelf) setTarget(me) }, [me])

  const afterSave = async () => {
    if (isSelf) await refreshUser()
    else await loadTarget()
  }

  // ── Info form ────────────────────────────────────────────────
  const [info, setInfo]             = useState({ full_name: '', phone: '' })
  const [infoSaving, setInfoSaving] = useState(false)
  const [infoMsg, setInfoMsg]       = useState(null)

  useEffect(() => {
    if (target) setInfo({ full_name: target.full_name || '', phone: target.phone || '' })
  }, [target])

  const saveInfo = async (e) => {
    e.preventDefault()
    setInfoSaving(true); setInfoMsg(null)
    try {
      await axios.patch(`${API}/users/${targetId}`, {
        full_name: info.full_name.trim(),
        phone: info.phone.trim() || null,
      })
      await afterSave()
      setInfoMsg({ ok: true, text: 'Profil mis à jour' })
    } catch (err) {
      setInfoMsg({ ok: false, text: err.response?.data?.detail || 'Erreur lors de la mise à jour' })
    } finally {
      setInfoSaving(false)
    }
  }

  // ── Password (self only) ─────────────────────────────────────
  const [pwd, setPwd]             = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwdSaving, setPwdSaving] = useState(false)
  const [pwdMsg, setPwdMsg]       = useState(null)

  const changePassword = async (e) => {
    e.preventDefault()
    if (pwd.new_password !== pwd.confirm)
      return setPwdMsg({ ok: false, text: 'Les mots de passe ne correspondent pas' })
    if (pwd.new_password.length < 6)
      return setPwdMsg({ ok: false, text: 'Minimum 6 caractères' })
    setPwdSaving(true); setPwdMsg(null)
    try {
      await axios.post(`${API}/users/${targetId}/change-password`, {
        current_password: pwd.current_password,
        new_password: pwd.new_password,
      })
      setPwd({ current_password: '', new_password: '', confirm: '' })
      setPwdMsg({ ok: true, text: 'Mot de passe changé' })
    } catch (err) {
      setPwdMsg({ ok: false, text: err.response?.data?.detail || 'Erreur lors du changement' })
    } finally {
      setPwdSaving(false)
    }
  }

  // ── Consent (self only) ──────────────────────────────────────
  const [consentSaving, setConsentSaving] = useState(false)

  const toggleConsent = async () => {
    setConsentSaving(true)
    try {
      await axios.post(`${API}/users/${targetId}/consent`, { consent_given: !target.consent_given })
      await afterSave()
    } catch {}
    setConsentSaving(false)
  }

  // ── Caregivers (elderly only) ────────────────────────────────
  const [carers, setCarers]             = useState([])
  const [carerLoading, setCarerLoading] = useState(false)
  const [showAddCarer, setShowAddCarer] = useState(false)
  const [carerForm, setCarerForm]       = useState({ full_name: '', email: '', phone: '', password: '' })
  const [carerSaving, setCarerSaving]   = useState(false)
  const [carerError, setCarerError]     = useState('')
  const [deletingId, setDeletingId]     = useState(null)

  const fetchCarers = async () => {
    if (!target || target.role !== 'elderly') return
    setCarerLoading(true)
    try {
      const r = await axios.get(`${API}/users/${targetId}/caregivers`)
      setCarers(r.data || [])
    } catch { setCarers([]) }
    finally { setCarerLoading(false) }
  }

  useEffect(() => { fetchCarers() }, [targetId, target?.role])

  const addCarer = async (e) => {
    e.preventDefault()
    setCarerSaving(true); setCarerError('')
    try {
      await axios.post(`${API}/users/${targetId}/caregivers`, carerForm)
      setCarerForm({ full_name: '', email: '', phone: '', password: '' })
      setShowAddCarer(false)
      await fetchCarers()
    } catch (err) {
      setCarerError(err.response?.data?.detail || 'Erreur lors de la création')
    } finally { setCarerSaving(false) }
  }

  const removeCarer = async (carerId) => {
    if (!confirm('Dissocier ce soignant ?')) return
    setDeletingId(carerId)
    try {
      await axios.delete(`${API}/users/${targetId}/caregivers/${carerId}`)
      await fetchCarers()
    } catch {}
    setDeletingId(null)
  }

  // ── Loading ──────────────────────────────────────────────────
  if (fetching) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={28} className="animate-spin" style={{ color: 'var(--green)' }} />
      </div>
    )
  }

  if (!target) return null

  const role = ROLE_CONFIG[target.role] || ROLE_CONFIG.elderly

  return (
    <div className="p-6 max-w-2xl mx-auto flex flex-col gap-5">

      {/* Back button (only when viewing someone else) */}
      {!isSelf && (
        <button onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm font-medium self-start transition-all"
          style={{ color: 'var(--muted)' }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--text)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
          <ArrowLeft size={15} /> Retour
        </button>
      )}

      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="font-display text-2xl font-bold mb-0.5" style={{ color: 'var(--text)' }}>
          {isSelf ? 'Mon profil' : `Profil — ${target.full_name}`}
        </h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          {canEditInfo
            ? 'Gérez les informations de ce compte'
            : 'Consultation du profil · lecture seule'}
        </p>
      </div>

      {/* Avatar + role */}
      <div className="glass rounded-2xl p-5 flex items-center gap-4 animate-fade-up">
        <div className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold flex-shrink-0"
          style={{ background: `${role.color}20`, color: role.color, border: `2px solid ${role.color}40` }}>
          {target.full_name?.[0]?.toUpperCase() || '?'}
        </div>
        <div>
          <p className="font-display font-bold text-lg" style={{ color: 'var(--text)' }}>{target.full_name}</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>{target.email}</p>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
              style={{ background: `${role.color}15`, color: role.color, border: `1px solid ${role.color}30` }}>
              {role.label}
            </span>
            {!target.is_active && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
                style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--danger)', border: '1px solid rgba(239,68,68,0.2)' }}>
                Inactif
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Personal info ── */}
      <Card title="Informations personnelles" icon={Save} iconColor="var(--green)">
        {canEditInfo ? (
          <form onSubmit={saveInfo} className="flex flex-col gap-4">
            <Field label="Nom complet">
              <input className="input-field" value={info.full_name}
                onChange={e => setInfo(p => ({ ...p, full_name: e.target.value }))} required />
            </Field>
            <Field label="Email">
              <input className="input-field" value={target.email} disabled
                style={{ opacity: 0.55, cursor: 'not-allowed' }} />
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>L'email ne peut pas être modifié</p>
            </Field>
            <Field label="Téléphone">
              <input className="input-field" value={info.phone}
                onChange={e => setInfo(p => ({ ...p, phone: e.target.value }))} placeholder="+216..." />
            </Field>
            <StatusMsg msg={infoMsg} />
            <button type="submit" disabled={infoSaving} className="btn-primary flex items-center gap-2 self-start">
              {infoSaving ? <><Loader2 size={14} className="animate-spin" /> Enregistrement...</> : <><Save size={14} /> Enregistrer</>}
            </button>
          </form>
        ) : (
          <div className="flex flex-col gap-3">
            {[['Nom complet', target.full_name], ['Email', target.email], ['Téléphone', target.phone || '—']].map(([lbl, val]) => (
              <div key={lbl}>
                <p className="text-xs font-semibold uppercase tracking-wider mb-0.5" style={{ color: 'var(--muted)' }}>{lbl}</p>
                <p className="text-sm" style={{ color: 'var(--text)' }}>{val}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ── Change password (self only) ── */}
      {canChangePass && (
        <Card title="Changer le mot de passe" icon={Lock} iconColor="#60a5fa">
          <form onSubmit={changePassword} className="flex flex-col gap-4">
            <Field label="Mot de passe actuel">
              <input type="password" className="input-field" value={pwd.current_password}
                onChange={e => setPwd(p => ({ ...p, current_password: e.target.value }))}
                required autoComplete="current-password" />
            </Field>
            <Field label="Nouveau mot de passe">
              <input type="password" className="input-field" value={pwd.new_password}
                onChange={e => setPwd(p => ({ ...p, new_password: e.target.value }))}
                required autoComplete="new-password" minLength={6} />
            </Field>
            <Field label="Confirmer le nouveau mot de passe">
              <input type="password" className="input-field" value={pwd.confirm}
                onChange={e => setPwd(p => ({ ...p, confirm: e.target.value }))}
                required autoComplete="new-password" />
            </Field>
            <StatusMsg msg={pwdMsg} />
            <button type="submit" disabled={pwdSaving}
              className="flex items-center gap-2 self-start px-4 py-2 rounded-xl text-sm font-semibold"
              style={{ background: 'rgba(96,165,250,0.1)', color: '#60a5fa', border: '1px solid rgba(96,165,250,0.25)' }}>
              {pwdSaving ? <><Loader2 size={14} className="animate-spin" /> Changement...</> : <><Lock size={14} /> Changer le mot de passe</>}
            </button>
          </form>
        </Card>
      )}

      {/* ── RGPD consent ── */}
      <Card title="Consentement RGPD" icon={ShieldCheck} iconColor={target.consent_given ? 'var(--ok)' : 'var(--danger)'}>
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <p className="text-sm font-semibold mb-1"
              style={{ color: target.consent_given ? 'var(--ok)' : 'var(--danger)' }}>
              {target.consent_given ? 'Consentement donné' : 'Consentement refusé'}
            </p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              Acceptation de la collecte et du traitement des données personnelles à des fins de surveillance.
            </p>
            {target.consent_date && (
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
                Mis à jour le {new Date(target.consent_date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}
              </p>
            )}
          </div>
          {/* Toggle only for self */}
          {canChangeConsent && (
            <button onClick={toggleConsent} disabled={consentSaving}
              className="flex-shrink-0 px-4 py-2 rounded-xl text-sm font-semibold transition-all"
              style={{
                background: target.consent_given ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
                color: target.consent_given ? 'var(--danger)' : 'var(--ok)',
                border: `1px solid ${target.consent_given ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}`,
                opacity: consentSaving ? 0.6 : 1,
              }}>
              {consentSaving ? <Loader2 size={14} className="animate-spin" /> : target.consent_given ? 'Retirer' : 'Donner'}
            </button>
          )}
        </div>
      </Card>

      {/* ── Caregivers (elderly only) ── */}
      {target.role === 'elderly' && (
        <Card title="Soignants" icon={UserCheck} iconColor="#60a5fa">

          <div className="flex items-center justify-between mb-4">
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              {carerLoading ? 'Chargement...' : `${carers.length} soignant${carers.length !== 1 ? 's' : ''}`}
            </p>
            {canManageCarers && (
              <button
                onClick={() => { setShowAddCarer(v => !v); setCarerError(''); setCarerForm({ full_name: '', email: '', phone: '', password: '' }) }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                style={{
                  background: showAddCarer ? 'rgba(96,165,250,0.15)' : 'rgba(96,165,250,0.08)',
                  color: '#60a5fa', border: '1px solid rgba(96,165,250,0.25)',
                }}>
                {showAddCarer ? <><X size={11} /> Annuler</> : <><Plus size={11} /> Ajouter un soignant</>}
              </button>
            )}
          </div>

          {/* Add form */}
          {canManageCarers && showAddCarer && (
            <form onSubmit={addCarer}
              className="grid grid-cols-2 gap-3 mb-4 p-4 rounded-xl"
              style={{ background: 'rgba(96,165,250,0.05)', border: '1px solid rgba(96,165,250,0.15)' }}>
              <Field label="Nom complet">
                <input className="input-field" value={carerForm.full_name}
                  onChange={e => setCarerForm(p => ({ ...p, full_name: e.target.value }))} required />
              </Field>
              <Field label="Email">
                <input type="email" className="input-field" value={carerForm.email}
                  onChange={e => setCarerForm(p => ({ ...p, email: e.target.value }))} required />
              </Field>
              <Field label="Mot de passe">
                <input type="password" className="input-field" value={carerForm.password}
                  onChange={e => setCarerForm(p => ({ ...p, password: e.target.value }))} required minLength={6} />
              </Field>
              <Field label="Téléphone (WhatsApp)">
                <input className="input-field" value={carerForm.phone}
                  onChange={e => setCarerForm(p => ({ ...p, phone: e.target.value }))} placeholder="+216..." />
              </Field>
              {carerError && (
                <div className="col-span-2 px-3 py-2 rounded-lg text-xs"
                  style={{ background: 'rgba(239,68,68,0.08)', color: 'var(--danger)' }}>
                  ✗ {carerError}
                </div>
              )}
              <div className="col-span-2">
                <button type="submit" disabled={carerSaving}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold"
                  style={{ background: '#60a5fa', color: '#fff', opacity: carerSaving ? 0.7 : 1 }}>
                  {carerSaving ? <><Loader2 size={13} className="animate-spin" /> Création...</> : <><UserCheck size={13} /> Créer le soignant</>}
                </button>
              </div>
            </form>
          )}

          {/* Caregivers list */}
          {carerLoading ? (
            <div className="flex items-center gap-2 py-3" style={{ color: 'var(--muted)' }}>
              <Loader2 size={14} className="animate-spin" />
              <span className="text-xs">Chargement des soignants...</span>
            </div>
          ) : carers.length === 0 ? (
            <p className="text-xs py-2" style={{ color: 'var(--muted)' }}>
              {canManageCarers ? 'Aucun soignant — utilisez le bouton ci-dessus pour en ajouter un.' : 'Aucun soignant assigné.'}
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {carers.map(c => (
                <div key={c.id} className="flex items-center gap-3 px-4 py-3 rounded-xl"
                  style={{ background: 'rgba(96,165,250,0.06)', border: '1px solid rgba(96,165,250,0.15)' }}>
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                    style={{ background: 'rgba(96,165,250,0.15)', color: '#60a5fa' }}>
                    {c.full_name?.[0]?.toUpperCase() || '?'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <button
                      onClick={() => navigate(`/profile/${c.id}`)}
                      className="text-sm font-semibold truncate block text-left transition-all"
                      style={{ color: 'var(--text)' }}
                      onMouseEnter={e => e.currentTarget.style.color = '#60a5fa'}
                      onMouseLeave={e => e.currentTarget.style.color = 'var(--text)'}>
                      {c.full_name}
                    </button>
                    <p className="text-xs truncate" style={{ color: 'var(--muted)' }}>
                      {c.email}{c.phone ? ` · ${c.phone}` : ''}
                    </p>
                  </div>
                  {canManageCarers && (
                    <button onClick={() => removeCarer(c.id)} disabled={deletingId === c.id}
                      title="Dissocier" className="p-1.5 rounded-lg transition-all flex-shrink-0"
                      style={{ color: 'var(--muted)', opacity: deletingId === c.id ? 0.5 : 1 }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                      onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}>
                      {deletingId === c.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

    </div>
  )
}
