# K.A.R.N.A. - API Integration Guide

## Quickstart

### Starting the Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies (if not already done):
   ```bash
   pip install -r requirements.txt
   ```

3. Set required environment variables:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   export GCS_BUCKET="karna-vault"  # or your custom bucket name
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"  # optional if using ADC
   export ALLOWED_ORIGINS="http://localhost:5173"  # frontend URL for CORS
   ```

4. Start the server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The backend will be available at `http://localhost:8000`

### Starting the Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. The frontend is already configured to use the backend at `http://localhost:8000` via `.env.development`.

4. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

---

## API Reference

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Health Check

**GET** `/health`

**Response:**
```json
{
  "status": "ok"
}
```

---

#### 2. Initialize Interview Session

**POST** `/init`

**Request Body (JSON):**
```json
{
  "job_role": "Frontend Engineer"  // or: Backend Engineer, ML Engineer, DevOps Engineer, Full Stack Engineer
}
```

**Response:**
```json
{
  "session_id": "string",
  "current_round": 1,
  "total_rounds": 5,
  "question": {
    "text": "Tell me about your experience with system design.",
    "type": "initial",
    "topic_area": "System Design"
  },
  "status": "active"
}
```

---

#### 3. Process Audio/Video Chunk

**POST** `/process-chunk`

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `session_id` (string) - The session ID from `/init`
- `chunk_index` (integer) - Index of this chunk (0, 1, 2, ...)
- `media_chunk` (file) - WebM video/audio file blob
- `is_final` (string: "true" or "false") - Whether this is the last chunk

**Response (Non-final Chunk):**
```json
{
  "session_id": "string",
  "chunk_index": 0,
  "status": "chunk_received",
  "operations": [
    {
      "op": "video_vaulted",
      "gcs_path": "gs://bucket/session-id/0.webm"
    },
    {
      "op": "audio_extracted"
    }
  ]
}
```

**Response (Final Chunk - with evaluation):**
```json
{
  "session_id": "string",
  "chunk_index": 2,
  "status": "answer_evaluated",
  "transcript": "The candidate's transcribed answer...",
  "evaluation": {
    "scores": {
      "System Design": 75,
      "Problem Solving": 80,
      "Communication Clarity": 70,
      "Depth of Knowledge": 85,
      "Adaptability": 72
    },
    "flags": {
      "memorization_detected": false,
      "answer_quality": "strong"
    },
    "evaluator_notes": "Clear and concise answer with good examples."
  },
  "next_action": {
    "type": "next_question"  // or "follow_up_probe", "complete"
    "current_round": 2,
    "question": {
      "text": "What about scalability considerations?",
      "type": "follow_up_probe",
      "topic_area": "System Design"
    }
  },
  "operations": [
    { "op": "video_vaulted", "gcs_path": "..." },
    { "op": "audio_extracted" },
    { "op": "audio_transcribed", "word_count": 150 },
    { "op": "gemini_evaluated", "latency_ms": 2450 }
  ]
}
```

**Notes:**
- For non-final chunks, send immediately as they are recorded
- For the final chunk: send with `is_final=true`, which triggers the full evaluation pipeline
- After the final chunk of the last round, `next_action.type` will be `"complete"`

---

#### 4. Get Interview Results

**GET** `/results/{session_id}`

**Response:**
```json
{
  "session_id": "string",
  "job_role": "Frontend Engineer",
  "status": "completed",
  "overall_score": 76,
  "recommendation": "Strong",  // or "Moderate", "Weak"
  "skill_scores": {
    "System Design": 75,
    "Problem Solving": 80,
    "Communication Clarity": 70,
    "Depth of Knowledge": 85,
    "Adaptability": 72
  },
  "flags": {
    "memorization_detected": false,
    "answer_quality": "completed"
  },
  "round_details": [
    {
      "round": 1,
      "topic_area": "System Design",
      "question": "Tell me about your experience...",
      "question_type": "initial",
      "transcript": "...",
      "scores": { ... },
      "flags": { ... },
      "evaluator_notes": "...",
      "follow_ups": []
    }
    // ... more rounds
  ],
  "summary": "The candidate demonstrated strong technical knowledge...",
  "video_vault_manifest": {
    "bucket": "karna-vault",
    "prefix": "session-id/",
    "total_chunks": 15,
    "note": "Video sealed. Not accessed by any AI model."
  }
}
```

**Requirements:**
- The session must have `status: "completed"`; otherwise returns 409 Conflict

---

## Frontend Integration Details

### Environment Configuration

The frontend reads the API base URL from `import.meta.env.VITE_API_URL`, set in `frontend/.env.development`:

```env
VITE_API_URL=http://localhost:8000
```

This is used in `src/utils/chunkUploader.js`:

```javascript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080'
```

### State Machine

The frontend manages interview state via `useInterviewState` hook:

```
idle → initializing → recording → processing → completed
```

**Key transitions:**
- `idle` → `initializing`: User selects role and calls `initSession()`
- `initializing` → `recording`: `/init` succeeds
- `recording` → `processing`: User ends interview (final chunk sent with `is_final=true`)
- `processing` → `completed`: Final chunk returns `next_action.type="complete"`, then `fetchResults()` is called

---

## CORS Configuration

Backend CORS is controlled by `ALLOWED_ORIGINS` environment variable (default: `http://localhost:5173`).

To allow multiple origins:
```bash
export ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```

---

## Troubleshooting

### "Address already in use" when starting backend
Kill the process on port 8000:
```bash
lsof -ti:8000 | xargs kill -9
```

### CORS errors in browser console
Ensure the frontend URL is in `ALLOWED_ORIGINS` and restart the backend.

### Network error when attempting to fetch
1. Check backend is running (`curl http://localhost:8000/health`)
2. Verify `VITE_API_URL` in `.env.development` points to correct port
3. Restart frontend after changing `.env` files
4. Check browser DevTools Network tab for details

### Google cloud warnings about Python 3.9
These are non-fatal warnings. For production, upgrade to Python 3.10+.

---

## Data Models Summary

### Key Models (from `backend/app/models.py`)

**InitRequest**: `{ job_role: string }`

**InitResponse**: `{ session_id: string, current_round: int, total_rounds: int, question: QuestionPayload, status: string }`

**QuestionPayload**: `{ text: string, type: string, topic_area: string }`

**ChunkResponse**: `{ session_id, chunk_index, status, transcript?, evaluation?, next_action?, operations[] }`

**EvaluationResult**: `{ scores: EvaluationScores, flags: EvaluationFlags, evaluator_notes: string }`

**EvaluationScores**: `{ System Design, Problem Solving, Communication Clarity, Depth of Knowledge, Adaptability }` (all 0-100)

**NextAction**: `{ type: "next_question" | "follow_up_probe" | "complete", current_round, question?, message? }`

**ResultsResponse**: `{ session_id, job_role, status, overall_score, recommendation, skill_scores, flags, round_details[], summary, video_vault_manifest }`

---

## Interview Flow

1. **Client** → `POST /init` with job role → **Server** creates session, returns first question
2. **Client** records audio/video in chunks
3. **Client** → `POST /process-chunk` for each chunk (non-final)
4. **Client** → `POST /process-chunk` with `is_final=true` → **Server**:
   - Concatenates audio
   - Transcribes via STT
   - Evaluates via Gemini
   - Generates next action (next question / follow-up / complete)
5. If `next_action.type != "complete"`, go back to step 2
6. If `next_action.type == "complete"` → **Client** calls `GET /results/{session_id}` to fetch final report

---

## Notes

- All timestamps, video storage, and intermediate artifacts are handled by the backend (GCS for video vault, temporary local storage for audio processing)
- The backend runs on port 8000 by default; change via `--port` flag or proxy if needed
- The frontend uses Vite's dev server on port 5173 by default

---

**For any issues, check the browser console, backend terminal logs, and ensure all environment variables are set correctly.**
