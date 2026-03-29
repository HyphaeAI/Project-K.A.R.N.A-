function getScoreColor(score) {
  if (score >= 75) return 'var(--score-strong)'
  if (score >= 50) return 'var(--score-moderate)'
  return 'var(--score-weak)'
}

export default function ScoreCards({ results }) {
  if (!results) return null

  const { skill_scores, flags } = results

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {Object.entries(skill_scores).map(([skill, score]) => {
        const color = getScoreColor(score)
        return (
          <div key={skill} className="glass-card" style={{ padding: '16px 20px' }}>
            <div className="flex justify-between items-center" style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8,
            }}>
              <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>{skill}</span>
              <span style={{ fontWeight: 700, color, fontSize: '1rem' }}>{score}</span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${score}%`, background: color }}
              />
            </div>
          </div>
        )
      })}

      {/* Flags */}
      {flags && (
        <div className="glass-card" style={{ padding: '12px 20px', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            🚩 Memorization flags: <strong style={{ color: 'var(--text-primary)' }}>{flags.memorization_detected ? 1 : 0}</strong>
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            🔍 Follow-ups triggered: <strong style={{ color: 'var(--text-primary)' }}>{flags.follow_up_triggered_count ?? 0}</strong>
          </span>
        </div>
      )}
    </div>
  )
}
