import {
  RadarChart as RechartsRadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from 'recharts'

const SCORE_COLORS = {
  Strong:   'var(--score-strong)',
  Moderate: 'var(--score-moderate)',
  Weak:     'var(--score-weak)',
}

export default function RadarChart({ results }) {
  if (!results) return null

  const { skill_scores, overall_score, recommendation } = results

  const data = Object.entries(skill_scores).map(([skill, score]) => ({
    subject: skill,
    score,
  }))

  const scoreColor = SCORE_COLORS[recommendation] || 'var(--text-primary)'

  return (
    <div className="glass-card" style={{ textAlign: 'center' }}>
      {/* Overall score */}
      <div style={{ marginBottom: 8 }}>
        <span style={{ fontSize: '3rem', fontWeight: 700, color: scoreColor }}>
          {overall_score}
        </span>
        <span style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', marginLeft: 4 }}>
          / 100
        </span>
      </div>

      <span
        className="badge"
        style={{
          background: `${scoreColor}22`,
          color: scoreColor,
          marginBottom: 24,
          display: 'inline-flex',
        }}
      >
        {recommendation}
      </span>

      <ResponsiveContainer width="100%" height={300}>
        <RechartsRadarChart data={data} style={{ background: 'transparent' }}>
          <PolarGrid stroke="rgba(255,255,255,0.1)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="var(--accent-cyan)"
            fill="var(--accent-cyan)"
            fillOpacity={0.3}
          />
        </RechartsRadarChart>
      </ResponsiveContainer>
    </div>
  )
}
