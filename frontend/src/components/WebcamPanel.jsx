import { useEffect, useRef, useState } from 'react'

export default function WebcamPanel({ addLog, onRecorderReady }) {
  const videoRef = useRef(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let stream

    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((s) => {
        stream = s
        if (videoRef.current) {
          videoRef.current.srcObject = s
        }
        addLog('Camera & microphone ready', 'success')
        if (onRecorderReady) onRecorderReady(s)
      })
      .catch((err) => {
        setError('Camera/mic access denied')
        addLog('Camera/mic access denied', 'error')
      })

    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop())
      }
    }
  }, [])

  return (
    <div className="glass-card" style={{ padding: 0, overflow: 'hidden', borderRadius: 16 }}>
      {error ? (
        <div style={{
          padding: 24,
          color: 'var(--accent-red)',
          textAlign: 'center',
          fontSize: '0.875rem',
        }}>
          🚫 {error}
        </div>
      ) : (
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          style={{
            width: '100%',
            display: 'block',
            transform: 'scaleX(-1)',
            borderRadius: 16,
            background: '#000',
          }}
        />
      )}
    </div>
  )
}
