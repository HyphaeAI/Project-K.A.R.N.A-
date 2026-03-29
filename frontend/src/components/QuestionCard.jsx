export default function QuestionCard({ state }) {
  const { currentQuestion, currentRound, totalRounds } = state

  if (!currentQuestion) return null

  const { text, type, topic_area } = currentQuestion

  const getBadge = () => {
    if (type === 'follow_up_probe') {
      return <span className="badge badge-probe">🔍 Deep Probe</span>
    }
    if (type === 'clarification') {
      return <span className="badge badge-clarification">📋 Clarification</span>
    }
    return <span className="badge badge-initial">{topic_area}</span>
  }

  return (
    <div className="glass-card">
      <div className="flex items-center justify-between gap-sm" style={{ marginBottom: 16 }}>
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>
          Round {currentRound}/{totalRounds}
        </span>
        {getBadge()}
      </div>

      <p
        key={text}
        className="fade-in"
        style={{
          fontSize: '1.05rem',
          lineHeight: 1.7,
          color: 'var(--text-primary)',
        }}
      >
        {text}
      </p>
    </div>
  )
}
