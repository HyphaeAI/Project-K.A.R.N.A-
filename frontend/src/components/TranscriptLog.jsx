function TypeBadge({ type }) {
  if (type === 'follow_up_probe') return <span className="badge badge-probe">🔍 Deep Probe</span>
  if (type === 'clarification')  return <span className="badge badge-clarification">📋 Clarification</span>
  return <span className="badge badge-initial">Initial</span>
}

function ScorePills({ scores }) {
  if (!scores) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
      {Object.entries(scores).map(([dim, val]) => (
        <span
          key={dim}
          style={{
            fontSize: '0.7rem',
            padding: '2px 8px',
            borderRadius: 12,
            background: 'rgba(255,255,255,0.07)',
            color: 'var(--text-secondary)',
          }}
        >
          {dim}: <strong style={{ color: 'var(--text-primary)' }}>{val}</strong>
        </span>
      ))}
    </div>
  )
}

function RoundEntry({ round, nested }) {
  return (
    <div style={nested ? {
      borderLeft: '3px solid var(--accent-amber)',
      paddingLeft: 16,
      marginTop: 12,
    } : {}}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <TypeBadge type={round.question_type} />
        {round.flags?.memorization_detected && (
          <span style={{ fontSize: '0.75rem', color: 'var(--accent-amber)' }}>🚩 Memorization</span>
        )}
      </div>

      <p style={{ fontSize: '0.9rem', fontWeight: 500, marginBottom: 6 }}>
        {round.question}
      </p>

      {round.transcript && (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 6, fontStyle: 'italic' }}>
          "{round.transcript}"
        </p>
      )}

      <ScorePills scores={round.scores} />

      {round.evaluator_notes && (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 8 }}>
          📝 {round.evaluator_notes}
        </p>
      )}
    </div>
  )
}

export default function TranscriptLog({ results }) {
  if (!results?.round_details) return null

  return (
    <div className="flex-col gap-md" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {results.round_details.map((round, i) => (
        <details key={i} className="glass-card" style={{ padding: '16px 20px' }}>
          <summary style={{
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.9rem',
            listStyle: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <span style={{ color: 'var(--accent-cyan)' }}>Round {round.round}</span>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>— {round.topic_area}</span>
          </summary>

          <div style={{ marginTop: 16 }}>
            <RoundEntry round={round} nested={false} />

            {round.follow_ups?.map((fu, j) => (
              <RoundEntry key={j} round={fu} nested={true} />
            ))}
          </div>
        </details>
      ))}
    </div>
  )
}
