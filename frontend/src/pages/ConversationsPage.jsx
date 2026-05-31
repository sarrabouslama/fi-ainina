import { useEffect, useState } from 'react'
import axios from 'axios'

export default function ConversationsPage() {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await axios.get('http://localhost:8000/conversations', { timeout: 3000 })
        setConversations(res.data?.conversations || res.data || [])
      } catch {
        setConversations([])
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-8 animate-fade-up">
        <h1 className="font-display text-3xl font-bold text-white mb-1">Historique Conversations</h1>
        <p className="text-sm" style={{ color: 'var(--text2)' }}>
          Companion Backend · Mémoire long terme · PostgreSQL
        </p>
      </div>

      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-1 glass rounded-2xl p-4 animate-fade-up" style={{ height: '500px', overflowY: 'auto' }}>
          <h3 className="font-display font-semibold text-sm text-white mb-3">Sessions</h3>
          {loading ? (
            <p className="text-xs text-center py-8" style={{ color: 'var(--muted)' }}>Chargement...</p>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-2xl mb-1">💬</p>
              <p className="text-xs" style={{ color: 'var(--muted)' }}>Aucune conversation</p>
              <p className="text-xs mt-1" style={{ color: 'var(--border2)' }}>Connectez le backend</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {conversations.map((c, i) => (
                <button key={i} onClick={() => setSelected(c)}
                  className="text-left px-3 py-2.5 rounded-xl transition-all text-xs"
                  style={{
                    background: selected === c ? 'rgba(45,138,67,0.15)' : 'rgba(7,43,14,0.4)',
                    border: `1px solid ${selected === c ? 'var(--green)' : 'var(--border)'}`,
                    color: 'var(--text2)'
                  }}>
                  <p className="font-medium text-white truncate">{c.title || `Session ${i + 1}`}</p>
                  <p style={{ color: 'var(--muted)' }}>
                    {c.created_at ? new Date(c.created_at).toLocaleDateString('fr-FR') : '—'}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="col-span-2 glass rounded-2xl p-5 animate-fade-up delay-100" style={{ height: '500px' }}>
          {selected ? (
            <div>
              <h3 className="font-display font-semibold text-sm text-white mb-4">
                {selected.title || 'Conversation'}
              </h3>
              <div className="flex flex-col gap-2 overflow-y-auto" style={{ maxHeight: '400px' }}>
                {(selected.messages || []).map((m, i) => (
                  <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className="max-w-xs px-3 py-2 rounded-xl text-xs"
                      style={{
                        background: m.role === 'user' ? 'rgba(45,138,67,0.2)' : 'rgba(14,61,24,0.6)',
                        border: '1px solid var(--border)',
                        color: 'var(--text)',
                      }}>
                      {m.content || m.text || ''}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full">
              <p className="text-3xl mb-3">💬</p>
              <p className="font-display font-semibold text-white mb-1">Sélectionnez une conversation</p>
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
