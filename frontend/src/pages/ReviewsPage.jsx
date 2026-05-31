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
  const [newReview, setNewReview] = useState({ subject: '', content: '', review_type: 'general' })
  const [reply, setReply] = useState('')
  const [sending, setSending] = useState(false)

  const isAdmin = me?.role === 'admin'

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
    try {
      await axios.post(`${API}/reviews`, newReview)
      setShowCreate(false)
      setNewReview({ subject: '', content: '', review_type: 'general' })
      fetchReviews()
    } catch {} finally { setSending(false) }
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
  const TYPE_ICONS = { general: '💬', alert_review: '🚨', feedback: '⭐', support: '🔧' }

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-8 animate-fade-up">
        <div>
          <h1 className="font-display text-3xl font-bold text-white mb-1">Revues & Feedback</h1>
          <p className="text-sm" style={{ color: 'var(--text2)' }}>
            Système de revue · Alertes · Communication équipe
          </p>
        </div>
        {!isAdmin && (
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary flex items-center gap-2">
            <Plus size={15} /> Nouvelle revue
          </button>
        )}
      </div>

      {showCreate && !isAdmin && (
        <div className="glass rounded-2xl p-6 mb-6 animate-slide-down">
          <h3 className="font-display font-semibold text-white mb-4">Créer une revue</h3>
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
                  <option value="general">💬 Général</option>
                  <option value="alert_review">🚨 Revue d'alerte</option>
                  <option value="feedback">⭐ Feedback</option>
                  <option value="support">🔧 Support</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text2)' }}>Message</label>
              <textarea className="input-field" rows={4} value={newReview.content}
                onChange={e => setNewReview(p => ({ ...p, content: e.target.value }))} required />
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={sending} className="btn-primary flex items-center gap-2">
                {sending ? <><Loader2 size={14} className="animate-spin" /> Envoi...</> : <><Send size={14}/> Envoyer</>}
              </button>
              <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">Annuler</button>
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
            </div>
          ) : reviews.map((r, i) => (
            <button key={r.id} onClick={() => setSelected(r)}
              className="glass rounded-xl p-4 text-left transition-all animate-fade-up"
              style={{
                animationDelay: `${i * 0.05}s`,
                border: `1px solid ${selected?.id === r.id ? 'var(--green)' : 'rgba(45,138,67,0.15)'}`,
                background: selected?.id === r.id ? 'rgba(45,138,67,0.1)' : 'rgba(7,43,14,0.5)',
              }}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-semibold text-white truncate flex-1">{r.subject}</span>
                <span className="text-xs ml-2 font-bold flex-shrink-0"
                  style={{ color: STATUS_COLORS[r.status] || 'var(--muted)' }}>
                  {r.status}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs">{TYPE_ICONS[r.review_type] || '💬'}</span>
                <span className="text-xs" style={{ color: 'var(--muted)' }}>
                  {r.messages?.length || 0} message(s)
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
              <p className="font-display font-semibold text-white">Sélectionnez une revue</p>
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Pour voir les messages</p>
            </div>
          ) : (
            <>
              <div className="p-5 border-b" style={{ borderColor: 'var(--border)' }}>
                <div className="flex items-center justify-between">
                  <h3 className="font-display font-semibold text-white">{selected.subject}</h3>
                  <span className="text-xs font-bold px-2 py-1 rounded-full"
                    style={{ background: `${STATUS_COLORS[selected.status]}20`, color: STATUS_COLORS[selected.status] }}>
                    {selected.status}
                  </span>
                </div>
                <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
                  {TYPE_ICONS[selected.review_type]} {selected.review_type}
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
                          background: msg.sender_role === 'admin' ? 'rgba(45,138,67,0.2)' : 'rgba(14,61,24,0.6)',
                          border: '1px solid var(--border)',
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
                <div className="p-4 border-t flex gap-2" style={{ borderColor: 'var(--border)' }}>
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
