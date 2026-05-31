export default function StatCard({ icon, label, value, sub, color = 'var(--green)', delay = 0 }) {
  return (
    <div className="glass rounded-2xl p-5 animate-fade-up"
      style={{ animationDelay: `${delay}s` }}>
      <div className="flex items-start justify-between mb-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
          style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold font-display text-white mb-1">{value}</p>
      <p className="text-sm font-medium" style={{ color: 'var(--text2)' }}>{label}</p>
      {sub && <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{sub}</p>}
    </div>
  )
}
