import { useEffect, useRef } from 'react'

export default function TerminalLog({ logs }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="terminal">
      <span className="log-success">K.A.R.N.A. Terminal v1.0 — Ready</span>
      {logs.map((log, i) => (
        <div key={i}>
          <span className={`log-${log.type}`}>
            [{log.timestamp}] {log.message}
          </span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
