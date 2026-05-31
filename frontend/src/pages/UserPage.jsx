import VoiceControl from '../components/VoiceControl'
import EmotionDisplay from '../components/EmotionDisplay'

export default function UserPage() {
  return (
    <div className="pt-20 px-6 pb-8 max-w-2xl mx-auto">
      <div className="mb-8 animate-fade-in text-center">
        <div className="text-6xl mb-3">🤖</div>
        <h1 className="font-display font-extrabold text-3xl text-white mb-2">Bonjour !</h1>
        <p className="text-sm" style={{ color: 'var(--muted)' }}>
          Je suis Léa, votre assistante personnelle. Comment puis-je vous aider ?
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {/* Wake word tip */}
        <div className="rounded-2xl p-4 animate-fade-in"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-3">
            <span className="text-2xl">💡</span>
            <div>
              <p className="text-sm font-bold text-white">Activation mains-libres</p>
              <p className="text-xs" style={{ color: 'var(--muted)' }}>
                Dites <span className="font-bold" style={{ color: 'var(--accent)' }}>"Bonjour Léa"</span> pour activer sans toucher l'écran
              </p>
            </div>
          </div>
        </div>

        <VoiceControl />
        <EmotionDisplay />

        {/* Quick phrases */}
        <div className="rounded-2xl p-5"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <h2 className="font-display font-bold text-base text-white mb-3">Phrases rapides</h2>
          <div className="flex flex-col gap-2">
            {[
              "Comment allez-vous aujourd'hui ?",
              "Pouvez-vous m'aider ?",
              "Je ne me sens pas bien",
              "Appelez ma famille",
              "Rappelle-moi de prendre mes médicaments",
            ].map((phrase, i) => (
              <button key={i}
                onClick={() => navigator.clipboard?.writeText(phrase)}
                className="text-left px-4 py-2.5 rounded-xl text-sm transition-all hover:brightness-110"
                style={{ background: 'var(--surface2)', color: 'var(--text)', border: '1px solid var(--border)' }}>
                {phrase}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
