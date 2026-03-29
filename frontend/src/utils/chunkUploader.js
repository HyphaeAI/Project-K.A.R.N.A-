const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export async function uploadChunk(sessionId, chunkIndex, blob, isFinal) {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  formData.append('chunk_index', String(chunkIndex))
  formData.append('media_chunk', blob, `chunk_${chunkIndex}.webm`)
  formData.append('is_final', isFinal ? 'true' : 'false')

  const response = await fetch(`${API_BASE}/process-chunk`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `HTTP ${response.status}`)
  }

  return response.json()
}

export async function postInit(jobRole) {
  const response = await fetch(`${API_BASE}/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_role: jobRole }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function getResults(sessionId) {
  const response = await fetch(`${API_BASE}/results/${sessionId}`)
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `HTTP ${response.status}`)
  }
  return response.json()
}
