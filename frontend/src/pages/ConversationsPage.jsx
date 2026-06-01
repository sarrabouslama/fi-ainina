import { useEffect, useState } from 'react'
import axios from 'axios'
import { MessageSquare, ChevronDown } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function ConversationsPage() {
  const { user: me, API } = useAuth()
  const isAdmin = me?.role === 'admin'

  const [allUsers, setAllUsers] = useState([])
  const [selectedUserId, setSelectedUserId] = useState(null)

  const [conversations, setConversations] = useState([])
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [selected, setSelected] = useState(null)
  const [messages, setMessages] = useState([])
  const [messagesLoading, setMessagesLoading] = useState(false)

  // Admin: load users for the picker
  useEffect(() => {
    if (!isAdmin) return
    axios.get(`${API}/users`, { timeout: 3000 })
      .then(r => setAllUsers(r.data || []))
      .catch(() => {})
  }, [isAdmin])

  // Load sessions whenever user filter changes
  useEffect(() => {
    setLoadingSessions(true)
    setSelected(null)
    setMessages([])
    const params = isAdmin && selectedUserId ? { user_id: selectedUserId } : {}
    axios.get('http://127.0.0.1:8000/conversations/sessions', { params, timeout: 3000 })
      .then(r => setConversations(r.data?.conversations || r.data || []))
      .catch(() => setConversations([]))
      .finally(() => setLoadingSessions(false))
  }, [selectedUserId, isAdmin])

  const handleSelect = async (c) => {
    setSelected(c)
    setMessages([])
    setMessagesLoading(true)
    try {
      const res = await axios.get(`http://127.0.0.1:8000/conversations/messages/${c.id}`, { timeout: 3000 })
      setMessages(res.data || [])
    } catch {
      setMessages([])
    } finally {
      setMessagesLoading(false)
    }
  }

  const selectedUserName = isAdmin && selectedUserId
    ? allUsers.find(u => u.id === selectedUserId)?.full_name || 'Utilisateur'
    : null

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl font-bold mb-1" style={{ color: 'var(--text)' }}>
          Historique Conversations
        </h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          Companion Backend · Mémoire long terme · PostgreSQL
        </p>
      </div>

      {/* Admin user selector */}
      {isAdmin && (
        <div className="mb-5 animate-fade-up">
          <div className="flex items-center gap-3">
            <p className="text-sm font-medium" style={{ color: 'var(--text2)' }}>Voir les conversations de :</p>
            <div className="relative">
              <select
                value={selectedUserId || ''}
                onChange={e => setSelectedUserId(e.target.value || null)}
                className="input-field pr-8 text-sm"
                style={{ minWidth: 200, cursor: 'pointer' }}>
                <option value="">Tous les utilisateurs</option>
                {allUsers.map(u => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.role})
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
                style={{ color: 'var(--muted)' }} />
            </div>
            {selectedUserName && (
              <button onClick={() => setSelectedUserId(null)}
                className="text-xs" style={{ color: 'var(--muted)' }}>
                Réinitialiser
              </button>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-5">
        {/* Session list */}
        <div className="col-span-1 glass rounded-2xl p-4 animate-fade-up" style={{ height: '500px', overflowY: 'auto' }}>
          <h3 className="font-display font-semibold text-sm mb-3" style={{ color: 'var(--text)' }}>
            Sessions {selectedUserName ? `— ${selectedUserName}` : ''}
          </h3>
          {loadingSessions ? (
            <p className="text-xs text-center py-8" style={{ color: 'var(--muted)' }}>Chargement...</p>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-2xl mb-1">💬</p>
              <p className="text-xs" style={{ color: 'var(--muted)' }}>Aucune conversation</p>
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
                {isAdmin ? 'Aucune session trouvée' : 'Commencez à parler à Léa'}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {conversations.map((c, i) => {
                const isActive = selected?.id === c.id
                return (
                  <button key={c.id ?? i} onClick={() => handleSelect(c)}
                    className="text-left px-3 py-2.5 rounded-xl transition-all text-xs"
                    style={{
                      background: isActive ? 'rgba(30,107,46,0.12)' : 'rgba(255,255,255,0.6)',
                      border: `1px solid ${isActive ? 'var(--green)' : 'rgba(45,120,45,0.15)'}`,
                    }}>
                    <p className="font-medium truncate" style={{ color: 'var(--text)' }}>
                      {c.title || `Session ${i + 1}`}
                    </p>
                    <p style={{ color: 'var(--muted)' }}>
                      {c.started_at ? new Date(c.started_at).toLocaleDateString('fr-FR') : '—'}
                      {c.message_count ? ` · ${c.message_count} msg` : ''}
                    </p>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Message panel */}
        <div className="col-span-2 glass rounded-2xl p-5 animate-fade-up delay-100"
          style={{ height: '500px', display: 'flex', flexDirection: 'column' }}>
          {selected ? (
            <>
              <div className="mb-4 flex-shrink-0">
                <h3 className="font-display font-semibold text-sm" style={{ color: 'var(--text)' }}>
                  {selected.title || `Session ${conversations.findIndex(c => c.id === selected.id) + 1}`}
                </h3>
                <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                  {selected.started_at ? new Date(selected.started_at).toLocaleString('fr-FR') : ''}
                  {selected.message_count ? ` · ${selected.message_count} messages` : ''}
                </p>
              </div>

              {messagesLoading ? (
                <div className="flex-1 flex items-center justify-center">
                  <p className="text-xs" style={{ color: 'var(--muted)' }}>Chargement des messages...</p>
                </div>
              ) : messages.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center">
                  <MessageSquare size={28} className="mb-3" style={{ color: 'var(--muted)', opacity: 0.5 }} />
                  <p className="text-sm font-medium" style={{ color: 'var(--text2)' }}>Aucun message</p>
                  <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Cette session ne contient pas de messages</p>
                </div>
              ) : (
                <div className="flex flex-col gap-2 overflow-y-auto flex-1">
                  {messages.map((m, i) => (
                    <div key={m.id ?? i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className="max-w-xs px-3 py-2 rounded-xl text-xs"
                        style={{
                          background: m.role === 'user' ? 'rgba(30,107,46,0.12)' : 'rgba(255,255,255,0.75)',
                          border: '1px solid rgba(45,120,45,0.15)',
                          color: 'var(--text)',
                        }}>
                        <p className="font-semibold mb-0.5" style={{ color: 'var(--muted)', fontSize: '10px' }}>
                          {m.role === 'user' ? 'Utilisateur' : 'Léa'}
                          {m.timestamp ? ` · ${new Date(m.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}` : ''}
                        </p>
                        {m.content || m.text || ''}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full">
              <p className="text-3xl mb-3">💬</p>
              <p className="font-display font-semibold mb-1" style={{ color: 'var(--text)' }}>
                Sélectionnez une conversation
              </p>
              <p className="text-xs" style={{ color: 'var(--muted)' }}>
                Choisissez une session dans la liste
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
