export default function SummaryPanel({ results }) {
  if (!results) return null

  const { summary, video_vault_manifest } = results

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* AI Summary */}
      <div className="glass-card">
        <h3 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Assessment Summary
        </h3>
        <p style={{ lineHeight: 1.7, color: 'var(--text-primary)' }}>
          {summary}
        </p>
      </div>

      {/* Video Vault */}
      {video_vault_manifest && (
        <div className="glass-card" style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <span style={{ fontSize: '1.5rem' }}>🔒</span>
          <div>
            <p style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>
              Video Vault
            </p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 2 }}>
              Bucket: <span style={{ color: 'var(--text-secondary)' }}>{video_vault_manifest.bucket}</span>
            </p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 2 }}>
              Chunks sealed: <span style={{ color: 'var(--text-secondary)' }}>{video_vault_manifest.total_chunks}</span>
            </p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              {video_vault_manifest.note}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
