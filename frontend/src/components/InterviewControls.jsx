export default function InterviewControls({
  state,
  sendChunk,
  endInterview,
  addLog,
  isRecording = false,
  onStartRecording,
  onStopRecording,
}) {
  const isProcessing = state.status === 'processing'
  const disabled = isProcessing

  return (
    <div className="glass-card flex-col gap-md" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Recording indicator */}
      {isRecording && (
        <div className="flex items-center gap-sm" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="recording-dot" />
          <span style={{ color: 'var(--accent-red)', fontSize: '0.875rem', fontWeight: 500 }}>
            Recording...
          </span>
        </div>
      )}

      {/* Processing spinner */}
      {isProcessing && (
        <div className="flex items-center gap-sm" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            ⏳ Processing...
          </span>
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <button
          className="btn-primary"
          onClick={onStartRecording}
          disabled={disabled || isRecording}
        >
          🎙 Start Answer
        </button>

        <button
          className="btn-secondary"
          onClick={onStopRecording}
          disabled={disabled || !isRecording}
        >
          ✅ Submit Answer
        </button>

        <button
          className="btn-danger"
          onClick={endInterview}
          disabled={disabled}
        >
          🛑 End Interview
        </button>
      </div>
    </div>
  )
}
