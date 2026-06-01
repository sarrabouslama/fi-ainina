import { useEffect, useState } from 'react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import { Plus, Send, Loader2 } from 'lucide-react'

export default function ReviewsPage() {
  const { user: me, API } = useAuth()
  const [reviews, setReviews] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newReview, setNewReview] = useState({ subject: '', content: '', review_type: 'feedback' })
  const [reply, setReply] = useState('')
  const [sending, setSending] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const isAdmin = me?.role === 'admin'
  const canCreate = me?.role !== 'admin'

  const fetchReviews = async () => {
    try {
      const res = await axios.get(`${API}/reviews`)
      setReviews(res.data || [])
    } catch { setReviews([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchReviews() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSending(true)
    setSubmitError('')
    try {
      await axios.post(`${API}/reviews`, newReview)
      setShowCreate(false)
      setNewReview({ subject: '', content: '', review_type: 'feedback' })
      fetchReviews()
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Erreur lors de l\'envoi'
      setSubmitError(`Erreur ${err.response?.status || ''}: ${detail}`)
    } finally { setSending(false) }
  }

  const handleReply = async () => {
    if (!reply.trim() || !selected) return
    setSending(true)
    try {
      const res = await axios.post(`${API}/reviews/${selected.id}/reply`, { content: reply })
      setSelected(res.data)
      setReply('')
      fetchReviews()
    } catch {} finally { setSending(false) }
  }

  const STATUS_COLORS = { open: 'var(--warn)', replied: 'var(--ok)', closed: 'var(--muted)' }
  const STATUS_LABELS = { open: 'Ouvert', replied: 'Répondu', closed: 'Fermé' }
  const TYPE_LABELS = { general: 'Général', alert_review: 'Alerte', feedback: 'Feedback', support: 'Support' }

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-8 animate-fade-up">
        <div>
          <h1 className="font-display text-3xl font-bold mb-1" style={{ color: 'var(--text)' }}>Revues & Feedback</h1>
          <p className="text-sm" style={{ color: 'var(--text2)' }}>
            Système de revue · Alertes · Communication équipe
          </p>
        </div>
        {canCreate && (
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary flex items-center gap-2">
            <Plus size={15} /> Nouvelle revue
          </button>
        )}
      </div>

      {showCreate && canCreate && (
        <div className="glass rounded-2xl p-6 mb-6 animate-slide-down">
          <h3 className="font-display font-semibold mb-4" style={{ color: 'var(--text)' }}>Créer une revue</h3>
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Sujet</label>
                <input className="input-field" value={newReview.subject}
                  onChange={e => setNewReview(p => ({ ...p, subject: e.target.value }))} required />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Type</label>
                <select className="input-field" value={newReview.review_type}
                  onChange={e => setNewReview(p => ({ ...p, review_type: e.target.value }))}
                  style={{ cursor: 'pointer' }}>
                  <option value="feedback">Feedback</option>
                  <option value="general">Général</option>
                  <option value="alert_review">Revue d'alerte</option>
                  <option value="support">Support</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Message</label>
              <textarea className="input-field" rows={4} value={newReview.content}
                onChange={e => setNewReview(p => ({ ...p, content: e.target.value }))} required />
            </div>
            {submitError && (
              <div className="px-3 py-2.5 rounded-xl text-xs"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171' }}>
                {submitError}
              </div>
            )}
            <div className="flex gap-3">
              <button type="submit" disabled={sending} className="btn-primary flex items-center gap-2">
                {sending ? <><Loader2 size={14} className="animate-spin" /> Envoi...</> : <><Send size={14}/> Envoyer</>}
              </button>
              <button type="button" onClick={() => { setShowCreate(false); setSubmitError('') }} className="btn-secondary">Annuler</button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-5 gap-5">
        {/* Reviews list */}
        <div className="col-span-2 flex flex-col gap-2 animate-fade-up">
          {loading ? (
            <div className="glass rounded-2xl p-8 text-center">
              <Loader2 size={20} className="animate-spin mx-auto" style={{ color: 'var(--green)' }} />
            </div>
          ) : reviews.length === 0 ? (
            <div className="glass rounded-2xl p-8 text-center">
              <p className="text-2xl mb-2">💬</p>
              <p className="text-sm" style={{ color: 'var(--muted)' }}>Aucune revue</p>
              {canCreate && (
                <button onClick={() => setShowCreate(true)} className="mt-3 text-xs font-medium" style={{ color: 'var(--green)' }}>
                  Créer la première
                </button>
              )}
            </div>
          ) : reviews.map((r, i) => (
            <button key={r.id} onClick={() => setSelected(r)}
              className="glass rounded-xl p-4 text-left transition-all animate-fade-up"
              style={{
                animationDelay: `${i * 0.05}s`,
                border: `1px solid ${selected?.id === r.id ? 'var(--green)' : 'rgba(45,120,45,0.15)'}`,
                background: selected?.id === r.id ? 'rgba(30,107,46,0.08)' : 'rgba(255,255,255,0.6)',
              }}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-semibold truncate flex-1" style={{ color: 'var(--text)' }}>{r.subject}</span>
                <span className="text-xs ml-2 font-bold flex-shrink-0"
                  style={{ color: STATUS_COLORS[r.status] || 'var(--muted)' }}>
                  {STATUS_LABELS[r.status] || r.status}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs" style={{ color: 'var(--muted)' }}>{TYPE_LABELS[r.review_type] || 'Général'}</span>
                <span className="text-xs" style={{ color: 'var(--muted)' }}>
                  {r.messages?.length || 0} msg
                </span>
                <span className="text-xs ml-auto" style={{ color: 'var(--muted)' }}>
                  {r.created_at ? new Date(r.created_at).toLocaleDateString('fr-FR') : ''}
                </span>
              </div>
            </button>
          ))}
        </div>

        {/* Review detail */}
        <div className="col-span-3 glass rounded-2xl animate-fade-up delay-100"
          style={{ height: '520px', display: 'flex', flexDirection: 'column' }}>
          {!selected ? (
            <div className="flex flex-col items-center justify-center h-full">
              <p className="text-3xl mb-2">💬</p>
              <p className="font-display font-semibold" style={{ color: 'var(--text)' }}>Sélectionnez une revue</p>
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Pour voir les messages</p>
            </div>
          ) : (
            <>
              <div className="p-5 flex-shrink-0" style={{ borderBottom: '1px solid rgba(45,120,45,0.12)' }}>
                <div className="flex items-center justify-between">
                  <h3 className="font-display font-semibold" style={{ color: 'var(--text)' }}>{selected.subject}</h3>
                  <span className="text-xs font-bold px-2 py-1 rounded-full"
                    style={{ background: `${STATUS_COLORS[selected.status]}20`, color: STATUS_COLORS[selected.status] }}>
                    {STATUS_LABELS[selected.status] || selected.status}
                  </span>
                </div>
                <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
                  {TYPE_LABELS[selected.review_type] || selected.review_type}
                </p>
              </div>

              <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-3">
                {(selected.messages || []).map((msg, i) => (
                  <div key={i} className={`flex ${msg.sender_role === 'admin' ? 'justify-end' : 'justify-start'}`}>
                    <div className="max-w-xs">
                      <p className="text-xs mb-1" style={{ color: 'var(--muted)' }}>
                        {msg.sender_role} · {new Date(msg.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                      <div className="px-4 py-3 rounded-2xl text-sm"
                        style={{
                          background: msg.sender_role === 'admin' ? 'rgba(30,107,46,0.1)' : 'rgba(255,255,255,0.75)',
                          border: '1px solid rgba(45,120,45,0.12)',
                          color: 'var(--text)',
                          borderRadius: msg.sender_role === 'admin' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                        }}>
                        {msg.content}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {isAdmin && selected.status !== 'closed' && (
                <div className="p-4 flex gap-2 flex-shrink-0" style={{ borderTop: '1px solid rgba(45,120,45,0.12)' }}>
                  <input className="input-field flex-1" placeholder="Répondre en tant qu'admin..."
                    value={reply} onChange={e => setReply(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleReply() }} />
                  <button onClick={handleReply} disabled={!reply.trim() || sending}
                    className="btn-primary flex-shrink-0 w-10 flex items-center justify-center">
                    {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
