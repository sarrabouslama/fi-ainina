import { useEffect, useState } from 'react'
import axios from 'axios'

const EMOTIONS = {
  happy: { icon: '😊', label: 'Heureux', color: '#fbbf24' },
  sad: { icon: '😢', label: 'Triste', color: '#60a5fa' },
  angry: { icon: '😠', label: 'En colère', color: '#f87171' },
  fear: { icon: '😨', label: 'Peur', color: '#a78bfa' },
  surprise: { icon: '😲', label: 'Surpris', color: '#fb923c' },
  neutral: { icon: '😐', label: 'Neutre', color: '#94a3b8' },
  disgust: { icon: '🤢', label: 'Dégoût', color: '#4ade80' },
}

export default function EmotionDisplay() {
  const [emotion, setEmotion] = useState(null)
  const [confidence, setConfidence] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await axios.get('http://localhost:8004/status/emotion', { timeout: 2000 })
        setEmotion(res.data?.emotion || res.data?.current_emotion)
        setConfidence(res.data?.confidence)
      } catch {
        setEmotion(null)
      } finally {
        setLoading(false)
      }
    }
    fetch()
    const interval = setInterval(fetch, 3000)
    return () => clearInterval(interval)
  }, [])

  const data = EMOTIONS[emotion] || null

  return (
    <div className="rounded-2xl p-5 text-center"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <h2 className="font-display font-bold text-base text-white mb-4">Émotion Détectée</h2>
      {loading ? (
        <p className="text-sm py-6" style={{ color: 'var(--muted)' }}>Chargement...</p>
      ) : data ? (
        <>
          <div className="text-5xl mb-3 animate-fade-in">{data.icon}</div>
          <p className="font-display font-bold text-xl mb-3" style={{ color: data.color }}>
            {data.label}
          </p>
          {confidence != null && (
            <div className="mt-2">
              <div className="rounded-full h-1.5 w-full" style={{ background: 'var(--surface2)' }}>
                <div className="h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${Math.round(confidence * 100)}%`, background: data.color }} />
              </div>
              <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>
                {Math.round(confidence * 100)}% confiance
              </p>
            </div>
          )}
        </>
      ) : (
        <div className="py-6">
          <p className="text-3xl mb-2">👁️</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>En attente de détection...</p>
        </div>
      )}
    </div>
  )
}
