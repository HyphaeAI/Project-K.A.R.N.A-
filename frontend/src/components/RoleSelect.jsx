import { useState } from 'react'

const ROLES = [
  { name: 'Backend Engineer',   emoji: '⚙️' },
  { name: 'Frontend Engineer',  emoji: '🎨' },
  { name: 'ML Engineer',        emoji: '🤖' },
  { name: 'DevOps Engineer',    emoji: '🚀' },
  { name: 'Full Stack Engineer', emoji: '🧩' },
]

export default function RoleSelect({ onStart, error }) {
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleStart = async () => {
    if (!selected) return
    setLoading(true)
    await onStart(selected)
    setLoading(false)
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '40px 16px' }}>
      <h2 style={{ textAlign: 'center', marginBottom: 8, fontSize: '1.5rem' }}>
        Select Your Role
      </h2>
      <p style={{ textAlign: 'center', color: 'var(--text-secondary)', marginBottom: 32 }}>
        Choose the position you're interviewing for
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: 16,
        marginBottom: 32,
      }}>
        {ROLES.map((role) => {
          const isSelected = selected === role.name
          return (
            <button
              key={role.name}
              onClick={() => setSelected(role.name)}
              className="glass-card"
              style={{
                cursor: 'pointer',
                textAlign: 'center',
                padding: '24px 16px',
                border: isSelected
                  ? '1px solid var(--accent-cyan)'
                  : '1px solid var(--border)',
                boxShadow: isSelected
                  ? '0 0 16px rgba(0, 212, 255, 0.3)'
                  : 'none',
                background: isSelected
                  ? 'rgba(0, 212, 255, 0.06)'
                  : 'rgba(255, 255, 255, 0.04)',
                transition: 'border 0.2s ease, box-shadow 0.2s ease, background 0.2s ease',
                borderRadius: 16,
              }}
            >
              <div style={{ fontSize: '2rem', marginBottom: 12 }}>{role.emoji}</div>
              <div style={{
                fontSize: '0.9rem',
                fontWeight: 500,
                color: isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)',
              }}>
                {role.name}
              </div>
            </button>
          )
        })}
      </div>

      {error && (
        <p style={{ color: 'var(--accent-red)', textAlign: 'center', marginBottom: 16, fontSize: '0.875rem' }}>
          {error}
        </p>
      )}

      <div style={{ textAlign: 'center' }}>
        <button
          className="btn-primary"
          onClick={handleStart}
          disabled={!selected || loading}
          style={{ minWidth: 180 }}
        >
          {loading ? (
            <>
              <span className="recording-dot" style={{ background: 'white', animation: 'none' }} />
              Initializing...
            </>
          ) : 'Start Interview'}
        </button>
      </div>
    </div>
  )
}
