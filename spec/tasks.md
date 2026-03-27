# Project K.A.R.N.A. — Task Breakdown

> Derived from: [`spec/design.md`](file:///Users/tusharsingh/Documents/PROJECTS/Project%20KARNA/spec/design.md) v1.0 (Approved)
> Execution agent compatible: All tasks formatted as checkboxes for programmatic tracking.

---

# Part 1 — Backend / Infra (Developer 2)

Everything related to the Python FastAPI server, GCP services, Docker, Cloud Run, media processing, and deployment.

---

## 1.1 Project Scaffolding

- [ ] Create `backend/` directory with `requirements.txt`
- [ ] Add dependencies: `fastapi`, `uvicorn`, `python-multipart`, `google-cloud-storage`, `google-cloud-speech`, `google-generativeai`, `pydantic`
- [ ] Create `backend/app/` package structure: `__init__.py`, `main.py`, `models.py`, `session_store.py`, `media_processor.py`, `gemini_service.py`, `stt_service.py`, `gcs_service.py`
- [ ] Create `backend/Dockerfile` with Python 3.11 + FFmpeg installed
- [ ] Create `backend/.env.example` with placeholder GCP credentials and config vars
- [ ] Create `backend/.dockerignore` (exclude `.env`, `__pycache__`, `.git`)
- [ ] Verify FFmpeg is accessible in the Docker container (`ffmpeg -version`)

## 1.2 FastAPI Application Bootstrap

- [ ] Create `backend/app/main.py` with FastAPI app instance
- [ ] Configure CORS middleware (allow `http://localhost:5173` in dev, configurable for prod)
- [ ] Add health check endpoint `GET /health` returning `{"status": "ok"}`
- [ ] Create startup/shutdown event handlers for logging

## 1.3 Data Models (Pydantic)

- [ ] Create `backend/app/models.py` with all Pydantic models:
  - [ ] `InitRequest`: `job_role: str` with validation against allowed roles
  - [ ] `QuestionPayload`: `text: str`, `type: str`, `topic_area: str`
  - [ ] `InitResponse`: `session_id`, `current_round`, `total_rounds`, `question: QuestionPayload`, `status`
  - [ ] `OperationLog`: `op: str`, `gcs_path: str | None`, `duration_ms: int | None`
  - [ ] `EvaluationResult`: `scores: dict`, `flags: dict`, `evaluator_notes: str`
  - [ ] `NextAction`: `type: str`, `current_round: int`, `question: QuestionPayload | None`, `message: str | None`
  - [ ] `ChunkResponse`: full `/process-chunk` response shape
  - [ ] `ResultsResponse`: full `/results` response shape with `round_details`, `summary`, `video_vault_manifest`

## 1.4 Session Store (In-Memory)

- [ ] Create `backend/app/session_store.py`
- [ ] Implement `SessionState` dataclass (design §4.1)
- [ ] Implement `RoundRecord` dataclass (design §4.2)
- [ ] Implement `create_session(job_role) -> SessionState`
- [ ] Implement `get_session(session_id) -> SessionState | None`
- [ ] Implement `update_session(session_id, updates)`

## 1.5 Media Processing Pipeline (FFmpeg)

- [ ] Create `backend/app/media_processor.py`
- [ ] Implement `save_temp_chunk(session_id, chunk_index, chunk_bytes) -> str` — saves WebM to `/tmp/{session_id}/chunk_{index}.webm`
- [ ] Implement `extract_audio(webm_path) -> str` — FFmpeg: `-vn -acodec pcm_s16le -ar 16000 -ac 1`, returns WAV path
- [ ] Implement `concatenate_audio_chunks(wav_paths) -> str` — concatenates WAV files, returns combined path
- [ ] Implement `cleanup_temp_files(session_id)` — removes temp directory for session
- [ ] Add error handling for FFmpeg subprocess failures (log and raise)

## 1.6 Google Cloud Storage — Video Vault

- [ ] Create `backend/app/gcs_service.py`
- [ ] Implement `init_gcs_client()` with service account credentials
- [ ] Implement `vault_video_chunk(session_id, chunk_index, webm_bytes) -> str` — uploads to `gs://karna-vault/{session_id}/chunk_{index}.webm`, returns GCS path
- [ ] Enforce write-only behavior (no read/download methods exposed)

## 1.7 Google Cloud Speech-to-Text

- [ ] Create `backend/app/stt_service.py`
- [ ] Implement `init_stt_client()` with credentials
- [ ] Implement `transcribe_audio(wav_path) -> str` — sync `recognize` call (LINEAR16, 16kHz, en-US)
- [ ] Handle empty transcript case (return `""` with warning log)
- [ ] Add timeout handling for STT calls

## 1.8 API Endpoint: `POST /init`

- [ ] Implement `/init` endpoint in `main.py`
- [ ] Validate `job_role` against: `["Backend Engineer", "Frontend Engineer", "ML Engineer", "DevOps Engineer", "Full Stack Engineer"]`
- [ ] Create new session via `session_store.create_session()`
- [ ] Call `gemini_service.generate_initial_question()` for round 1
- [ ] Store initial question in session's `gemini_chat_history`
- [ ] Return `InitResponse` with session_id, question, round info
- [ ] Return `400` for invalid job_role

## 1.9 API Endpoint: `POST /process-chunk`

- [ ] Implement `/process-chunk` endpoint accepting `multipart/form-data`
- [ ] Extract form fields: `session_id`, `chunk_index`, `media_chunk` (file), `is_final`
- [ ] Validate `session_id` exists; return `404` if not found
- [ ] Save chunk to temp file via `media_processor.save_temp_chunk()`
- [ ] Extract audio via `media_processor.extract_audio()`
- [ ] Vault video to GCS via `gcs_service.vault_video_chunk()`
- [ ] Append extracted audio to session's `current_chunk_buffer`
- [ ] Build `operations` log array for response
- [ ] **If `is_final=false`:** return `ChunkResponse` with `status: "chunk_received"`
- [ ] **If `is_final=true`:**
  - [ ] Concatenate audio buffers via `media_processor.concatenate_audio_chunks()`
  - [ ] Transcribe via `stt_service.transcribe_audio()`
  - [ ] Evaluate via `gemini_service.evaluate_answer()`
  - [ ] Determine `next_action`:
    - [ ] If probe needed → `type: "follow_up_probe"`, include probe question, DON'T increment round
    - [ ] If last round → `type: "complete"`, call `gemini_service.generate_final_summary()`
    - [ ] If advancing → increment `current_round`, call `gemini_service.generate_initial_question()`
  - [ ] Update session state with new `RoundRecord`
  - [ ] Clear `current_chunk_buffer` for next answer
  - [ ] Return full `ChunkResponse` with evaluation, transcript, and next_action

## 1.10 API Endpoint: `GET /results/{session_id}`

- [ ] Implement `/results/{session_id}` endpoint
- [ ] Validate session exists; return `404` if not
- [ ] If session `status != "completed"`: return `409 Conflict` with progress info
- [ ] Build and return full `ResultsResponse`:
  - [ ] `overall_score`, `recommendation`, `skill_scores`
  - [ ] `flags` (memorization count, follow_up count, total questions, total rounds)
  - [ ] `round_details` array with per-round Q&A, scores, notes, nested follow_ups
  - [ ] `summary` text
  - [ ] `video_vault_manifest` with bucket, prefix, total chunks

## 1.11 Error Handling

- [ ] Invalid `job_role` in `/init` → `400` with valid options listed
- [ ] Unknown `session_id` in `/process-chunk` → `404` session-not-found
- [ ] FFmpeg processing fails → `500`, log error, skip chunk
- [ ] Speech-to-Text returns empty → `200` with `transcript: ""`, Gemini re-prompts
- [ ] Gemini API timeout (>7s) → retry once; if fails, return cached previous question
- [ ] Gemini returns invalid JSON → retry with stricter prompt; if fails, use fallback scoring
- [ ] `/results` called before completion → `409` with progress info
- [ ] Concurrent chunk processing → ensure session state locking

## 1.12 Deployment to Google Cloud Run

- [ ] Finalize `Dockerfile` with all dependencies, FFmpeg, and uvicorn entrypoint
- [ ] Build and test Docker image locally: `docker build -t karna-backend .`
- [ ] Deploy to Cloud Run: `gcloud run deploy`
- [ ] Set environment variables: `GCS_BUCKET`, `GOOGLE_APPLICATION_CREDENTIALS`, `GEMINI_API_KEY`
- [ ] Verify health check passes (`GET /health`)
- [ ] Verify CORS works with deployed frontend origin

---

# Part 2 — AI / Gemini Prompt Engineering (Developer 1)

Everything related to Gemini system prompts, evaluation logic, scoring, and agentic probe behavior. Developer 1 engineers the prompts; Developer 2 injects them into the API calls.

---

## 2.1 Gemini Client Setup

- [ ] Create `backend/app/gemini_service.py`
- [ ] Implement `init_gemini_client()` with API key configuration (Gemini 3.0 Flash)
- [ ] Store the Role & Constraints system instruction (design §6.1) as constant `SYSTEM_PROMPT`

## 2.2 System Prompt: Role & Constraints (§6.1)

- [ ] Define the foundational system prompt enforcing:
  - [ ] No visual/demographic/personal data ever considered
  - [ ] Evaluation on 5 dimensions only: System Design, Problem Solving, Communication Clarity, Depth of Knowledge, Adaptability
  - [ ] All scores constrained to integer 0-100
  - [ ] All outputs must be valid, parseable JSON (no markdown, no prose wrapping)
  - [ ] Memorization detection heuristics (5 signals: textbook phrasing, suspicious ordering, no concrete examples, filler phrases, generic answers)
  - [ ] Probe triggering logic (memorized → edge-case probe, weak/vague → clarification, strong → advance)

## 2.3 Question Generation Prompt (§6.2)

- [ ] Implement `generate_initial_question(job_role, current_round, total_rounds, covered_topics, transcript_history) -> dict`
- [ ] Construct the question generation prompt with context injection:
  - [ ] Job role
  - [ ] Round number
  - [ ] Topics already covered (avoid repetition)
  - [ ] Previous Q&A history
- [ ] Enforce strict JSON output: `{ question_text, topic_area, question_type, difficulty }`
- [ ] Add retry logic for invalid JSON responses (max 2 retries with stricter prompt)

## 2.4 Answer Evaluation Prompt (§6.3)

- [ ] Implement `evaluate_answer(job_role, question_text, topic_area, transcript, current_round, total_rounds) -> dict`
- [ ] Construct the evaluation prompt with full context:
  - [ ] Job role, question asked, topic area, candidate transcript, round info
- [ ] Enforce strict JSON output: `{ scores, flags, evaluator_notes, probe_needed, probe_question }`
- [ ] Validate all scores are integers in range 0-100
- [ ] Validate `flags.answer_quality` is one of: `"strong"`, `"moderate"`, `"weak"`, `"memorized"`, `"vague"`
- [ ] If `probe_needed=true`: validate probe question has `question_text`, `topic_area`, `question_type`
- [ ] Add retry and fallback logic for malformed Gemini responses

## 2.5 Final Summary Prompt (§6.4)

- [ ] Implement `generate_final_summary(job_role, full_transcript_history, all_round_scores) -> dict`
- [ ] Construct the final summary prompt with complete session data
- [ ] Enforce strict JSON output: `{ overall_score, recommendation, skill_scores, flags, summary }`
- [ ] Apply weighted scoring: initial questions = 1.0x, follow-up probes = 1.5x
- [ ] Compute recommendation tier:
  - [ ] `"Strong"`: overall_score ≥ 75
  - [ ] `"Moderate"`: 50 ≤ overall_score < 75
  - [ ] `"Weak"`: overall_score < 50
- [ ] Validate summary is 2-3 sentences

## 2.6 Prompt Testing & Iteration

- [ ] Test question generation across all 5 job roles — verify topic coverage and variety
- [ ] Test memorization detection — provide textbook-style answers and verify `memorization_detected: true`
- [ ] Test probe triggering — verify edge-case probes fire for memorized answers
- [ ] Test clarification triggers — provide vague answers and verify clarification questions
- [ ] Test strong answer flow — verify AI advances to next topic without probe
- [ ] Test final summary — verify weighted scoring math and recommendation tiers
- [ ] Test JSON stability — run 10+ evaluations and verify 100% valid JSON output rate

---

# Part 3 — Frontend (Developer 1)

Everything related to the React UI, webcam capture, terminal log, radar chart, and all user-facing components.

---

## 3.1 Project Scaffolding

- [ ] Initialize React project with Vite: `npx create-vite@latest ./ --template react`
- [ ] Install dependencies: `recharts`, `uuid`
- [ ] Create folder structure: `src/components/`, `src/hooks/`, `src/styles/`, `src/utils/`

## 3.2 CSS Design System

- [ ] Create `src/styles/index.css` with full design system:
  - [ ] Color tokens — dark theme (deep navy/charcoal background, vibrant accent colors for scores)
  - [ ] Typography — import Google Font: `Inter` (UI) + `JetBrains Mono` (terminal)
  - [ ] Glassmorphism card styles with `backdrop-filter: blur`
  - [ ] Terminal panel styles (monospace, green-on-dark theme)
  - [ ] Smooth transitions and micro-animation keyframes (fade-in, pulse, slide-up)
  - [ ] Button styles with hover effects and active states
  - [ ] Responsive spacing scale

## 3.3 App Shell & View Routing

- [ ] Create `src/App.jsx` with main layout and view switching:
  - [ ] `idle` → Role Selection Screen
  - [ ] `recording` → Interview Screen (webcam + terminal + question)
  - [ ] `completed` → Results Dashboard Screen
- [ ] Add SEO: proper `<title>`, meta description, heading hierarchy

## 3.4 State Management

- [ ] Create `src/hooks/useInterviewState.js` custom hook managing full `appState` (design §4.3):
  - [ ] `sessionId`, `jobRole`, `status`, `currentRound`, `totalRounds`, `currentQuestion`
  - [ ] `mediaStream`, `mediaRecorder`, `chunkQueue`
  - [ ] `roundHistory`, `terminalLogs`
  - [ ] `finalResults`
- [ ] Implement state transitions: `idle → initializing → recording → processing → completed`
- [ ] Expose methods: `initSession()`, `sendChunk()`, `endInterview()`, `fetchResults()`

## 3.5 Role Selection Screen

- [ ] Create `src/components/RoleSelect.jsx`
- [ ] Display 5 job role cards: Backend Engineer, Frontend Engineer, ML Engineer, DevOps Engineer, Full Stack Engineer
- [ ] Card hover effects and selection animation (scale, glow, border highlight)
- [ ] "Start Interview" button — disabled until role selected
- [ ] On click: call `POST /init` via `useInterviewState.initSession()`
- [ ] Show loading spinner during API call
- [ ] On success: transition to Interview Screen with first question
- [ ] On error: display error notification

## 3.6 Webcam & MediaRecorder

- [ ] Create `src/components/WebcamPanel.jsx`
- [ ] Request camera + mic permissions: `navigator.mediaDevices.getUserMedia({ video: true, audio: true })`
- [ ] Display live webcam feed in `<video>` element (mirrored, rounded corners)
- [ ] Create `src/hooks/useMediaRecorder.js` custom hook:
  - [ ] Initialize `MediaRecorder` with `mimeType: "video/webm;codecs=vp8,opus"`
  - [ ] Set `timeslice: 5000` (5-second chunks)
  - [ ] On `ondataavailable`: push blob to chunk queue
  - [ ] Expose `startRecording()`, `stopRecording()`, `isRecording` state

## 3.7 Chunk Upload Manager

- [ ] Create `src/utils/chunkUploader.js`
- [ ] Implement `uploadChunk(sessionId, chunkIndex, blob, isFinal) -> Promise<response>`:
  - [ ] Build `FormData` with `session_id`, `chunk_index`, `media_chunk`, `is_final`
  - [ ] Send `POST /process-chunk` via `fetch`
  - [ ] Return parsed JSON response
- [ ] Implement sequential chunk upload loop (process queue one at a time)
- [ ] Track `chunk_index` incrementally across the session

## 3.8 Question Display

- [ ] Create `src/components/QuestionCard.jsx`
- [ ] Display current question text with typing animation effect
- [ ] Show metadata: round number ("Round 2/5"), topic area badge, question type indicator
- [ ] Visual distinction by question type:
  - [ ] `initial` → neutral card style
  - [ ] `follow_up_probe` → amber accent + "🔍 Deep Probe" label
  - [ ] `clarification` → blue accent + "📋 Clarification" label

## 3.9 Terminal Log Panel

- [ ] Create `src/components/TerminalLog.jsx`
- [ ] Scrollable monospace panel (dark background, green text)
- [ ] Auto-scroll to bottom on new log entries
- [ ] Log entry types with color coding:
  - [ ] `info` (cyan) — general ops (e.g., "Chunk #2 sent")
  - [ ] `success` (green) — confirmations (e.g., "✓ Video vaulted to GCS")
  - [ ] `warning` (yellow) — flags (e.g., "⚠ Memorization detected")
  - [ ] `error` (red) — failures
- [ ] Parse `operations` array from `/process-chunk` response to auto-generate entries
- [ ] Timestamp prefix on each line (e.g., `[17:42:03]`)

## 3.10 Interview Controls

- [ ] Create `src/components/InterviewControls.jsx`
- [ ] "Start Answer" button — begins MediaRecorder recording
- [ ] "Submit Answer" button — stops recording, marks last chunk `is_final=true`, uploads all pending
- [ ] "End Interview" button — stops all recording, sends final chunk, transitions to results
- [ ] Pulsing red dot recording indicator when active
- [ ] Disable controls during upload/processing (show spinner)

## 3.11 Radar Chart

- [ ] Create `src/components/RadarChart.jsx`
- [ ] Implement Radar/Spider chart using `Recharts` `<RadarChart>` component
- [ ] Map 5 skill dimensions to axes
- [ ] Style with gradient fills, score labels, smooth render animation
- [ ] Display overall score prominently (large number, color-coded by recommendation tier)

## 3.12 Score Cards & Recommendation

- [ ] Create `src/components/ScoreCards.jsx`
- [ ] Individual card per skill: score, progress bar, label
- [ ] Color-coded: green (≥75), amber (50-74), red (<50)
- [ ] Recommendation tier badge: "Strong" (green), "Moderate" (amber), "Weak" (red)
- [ ] Flag indicators: 🚩 Memorization count, probe triggered count

## 3.13 Transcript Log

- [ ] Create `src/components/TranscriptLog.jsx`
- [ ] Per-round expandable/collapsible sections showing:
  - [ ] Question asked (with type badge)
  - [ ] Candidate's transcript
  - [ ] Per-dimension scores (inline bars or number pills)
  - [ ] Evaluator notes
  - [ ] Flags (memorization indicator)
  - [ ] Nested follow-up probes (same format)

## 3.14 Summary Panel

- [ ] Create `src/components/SummaryPanel.jsx`
- [ ] Display AI-generated holistic summary text
- [ ] Show video vault metadata (chunks sealed, bucket info — trust indicator)

## 3.15 Integration & Edge Cases

- [ ] Wire full flow: Role Select → Init → Record → Upload → Evaluate → Next Question → Repeat → Results
- [ ] Camera/mic permission denied → user-friendly error message
- [ ] Network failure during chunk upload → retry with exponential backoff
- [ ] Gemini timeout → display cached question with "retrying..." indicator

## 3.16 Frontend Deployment

- [ ] Update API base URL to Cloud Run backend URL
- [ ] Build production bundle: `npm run build`
- [ ] Deploy to Vercel / Firebase Hosting
- [ ] Verify CORS works with Cloud Run backend

---

## Demo Checklist (Success Criteria Validation)

- [ ] ✅ Live webcam feed visible on the frontend
- [ ] ✅ Terminal log showing chunks sent, video vaulted, audio transcribed
- [ ] ✅ AI asks initial question, receives answer, triggers follow-up probe
- [ ] ✅ Radar Chart dashboard renders with per-skill scores
- [ ] ✅ Full 5-question interview completes in under 3 minutes

---

*Document Version: 1.1*
*Last Updated: 2026-03-27*
*Derived From: design.md v1.0 (Approved)*
