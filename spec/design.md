# Project K.A.R.N.A. — System Design Document

> Derived from: [`spec/requirements.md`](file:///Users/tusharsingh/Documents/PROJECTS/Project%20KARNA/spec/requirements.md) v1.0 (Approved)

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
│                          Developer 1 — AI Architect                          │
│                                                                              │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  Role Select │  │  MediaRecorder    │  │  Terminal    │  │  Radar Chart │  │
│  │  Screen      │  │  Capture Engine   │  │  Log Panel   │  │  Dashboard   │  │
│  │             │  │  (webcam + mic)   │  │  (live ops)  │  │  (results)   │  │
│  └──────┬──────┘  └────────┬─────────┘  └──────┬──────┘  └──────┬───────┘  │
│         │                  │                    │                 │          │
│         │     ┌────────────▼────────────┐       │                │          │
│         │     │  Chunk Manager          │       │                │          │
│         │     │  (5s interval blobs)    │       │                │          │
│         │     └────────────┬────────────┘       │                │          │
│         │                  │                    │                │          │
└─────────┼──────────────────┼────────────────────┼────────────────┼──────────┘
          │                  │                    │                │
          │    HTTPS / REST  │                    │                │
          ▼                  ▼                    ▼                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI on Cloud Run)                        │
│                        Developer 2 — Backend & GCP Infra                     │
│                                                                              │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐                   │
│  │  /init        │  │  /process-chunk  │  │  /results     │                  │
│  │  endpoint     │  │  endpoint        │  │  endpoint     │                  │
│  └──────┬───────┘  └────────┬─────────┘  └──────┬───────┘                   │
│         │                   │                    │                           │
│         │          ┌────────▼─────────┐          │                           │
│         │          │  Media Processor  │          │                           │
│         │          │  (FFmpeg)         │          │                           │
│         │          └───┬─────────┬────┘          │                           │
│         │              │         │                │                           │
│         │         VIDEO│    AUDIO│                │                           │
│         │              ▼         ▼                │                           │
│         │     ┌────────────┐ ┌───────────────┐   │                           │
│         │     │  GCS Vault  │ │  Speech-to-   │   │                           │
│         │     │  (sealed)   │ │  Text API     │   │                           │
│         │     └─────────────┘ └───────┬───────┘   │                           │
│         │                            │            │                           │
│         │                    TRANSCRIPT│            │                           │
│         │                            ▼            │                           │
│         │                   ┌─────────────────┐   │                           │
│         │                   │  Gemini 3.0     │   │                           │
│         │                   │  Flash API      │◄──┘                           │
│         │                   │  (Agentic       │                               │
│         │                   │   Deep-Probe)   │                               │
│         │                   └─────────────────┘                               │
│         │                                                                    │
│  ┌──────▼───────────────────────────────────────────────────────────────┐    │
│  │                    In-Memory Session Store                            │    │
│  │   { session_id → { role, round, transcript_history, scores, ... } }  │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Ownership Matrix

| Component | Owner | Tech |
|---|---|---|
| Role Selection UI | Developer 1 (Frontend/AI) | React, CSS |
| MediaRecorder Capture Engine | Developer 1 (Frontend/AI) | MediaRecorder API, JS |
| Chunk Manager (blob slicing + upload) | Developer 1 (Frontend/AI) | JS, `fetch` / `XMLHttpRequest` |
| Terminal Log Panel | Developer 1 (Frontend/AI) | React, CSS (monospace terminal aesthetic) |
| Radar Chart Dashboard | Developer 1 (Frontend/AI) | React, Recharts / Chart.js |
| Gemini System Prompt Engineering | Developer 1 (Frontend/AI) | Prompt design (consumed by backend) |
| `/init` endpoint | Developer 2 (Backend/Infra) | FastAPI, Python |
| `/process-chunk` endpoint | Developer 2 (Backend/Infra) | FastAPI, FFmpeg, Python |
| `/results` endpoint | Developer 2 (Backend/Infra) | FastAPI, Python |
| Media Processor (FFmpeg separation) | Developer 2 (Backend/Infra) | FFmpeg, subprocess |
| GCS Video Vault | Developer 2 (Backend/Infra) | `google-cloud-storage` SDK |
| Speech-to-Text Integration | Developer 2 (Backend/Infra) | `google-cloud-speech` SDK |
| Gemini API Calls | Developer 2 (Backend/Infra) | `google-generativeai` SDK |
| Cloud Run Deployment | Developer 2 (Backend/Infra) | Docker, `gcloud` CLI |
| In-Memory Session Store | Developer 2 (Backend/Infra) | Python `dict` (ephemeral) |

---

## 3. API Endpoint Contracts

### 3.1 `POST /init` — Initialize Interview Session

Starts a new interview session and returns the first AI-generated question.

#### Request

```json
{
  "job_role": "Backend Engineer"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `job_role` | `string` | ✅ | The role the candidate is being interviewed for. One of a predefined set (see §3.1.1). |

##### 3.1.1 Supported Job Roles (MVP)

```
"Backend Engineer" | "Frontend Engineer" | "ML Engineer" | "DevOps Engineer" | "Full Stack Engineer"
```

#### Response — `200 OK`

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "current_round": 1,
  "total_rounds": 5,
  "question": {
    "text": "Describe how you would design a rate limiter for a high-traffic API. What data structures would you choose and why?",
    "type": "initial",
    "topic_area": "System Design"
  },
  "status": "active"
}
```

| Field | Type | Description |
|---|---|---|
| `session_id` | `string (UUID)` | Unique session identifier for all subsequent requests |
| `current_round` | `integer` | Current question round (starts at 1) |
| `total_rounds` | `integer` | Total rounds configured for this session |
| `question.text` | `string` | The AI-generated question to display to the candidate |
| `question.type` | `string` | One of: `"initial"`, `"follow_up_probe"`, `"clarification"` |
| `question.topic_area` | `string` | The skill dimension being evaluated (maps to radar chart axis) |
| `status` | `string` | Session status: `"active"` or `"completed"` |

#### Error — `400 Bad Request`

```json
{
  "error": "Invalid job_role. Must be one of: Backend Engineer, Frontend Engineer, ML Engineer, DevOps Engineer, Full Stack Engineer"
}
```

---

### 3.2 `POST /process-chunk` — Process Media Chunk

Receives a media chunk (WebM blob), separates audio/video, vaults video, transcribes audio, evaluates transcript, and returns the next question or follow-up.

#### Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | `string (form field)` | ✅ | The active session UUID |
| `chunk_index` | `integer (form field)` | ✅ | Sequential chunk number (0-indexed) |
| `media_chunk` | `file (binary)` | ✅ | WebM blob from MediaRecorder (≤5s of AV data) |
| `is_final` | `boolean (form field)` | ✅ | `true` if this is the last chunk for the current answer |

#### Response — `200 OK` (when `is_final=false`)

Intermediate chunk received; no AI evaluation yet.

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "chunk_index": 0,
  "status": "chunk_received",
  "operations": [
    { "op": "video_vaulted", "gcs_path": "gs://karna-vault/a1b2c3d4/chunk_0.webm" },
    { "op": "audio_extracted", "duration_ms": 4850 }
  ]
}
```

#### Response — `200 OK` (when `is_final=true`)

Final chunk for an answer; triggers transcription + Gemini evaluation.

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "chunk_index": 3,
  "status": "answer_evaluated",
  "transcript": "I would use a sliding window approach with a Redis sorted set...",
  "evaluation": {
    "scores": {
      "System Design": 85,
      "Problem Solving": 70,
      "Communication Clarity": 75,
      "Depth of Knowledge": 60,
      "Adaptability": 65
    },
    "flags": {
      "memorization_detected": false,
      "answer_quality": "strong"
    },
    "evaluator_notes": "Candidate demonstrated practical understanding of rate limiting with good trade-off analysis."
  },
  "next_action": {
    "type": "next_question",
    "current_round": 2,
    "question": {
      "text": "How would you handle distributed rate limiting across multiple server instances?",
      "type": "initial",
      "topic_area": "System Design"
    }
  },
  "operations": [
    { "op": "video_vaulted", "gcs_path": "gs://karna-vault/a1b2c3d4/chunk_3.webm" },
    { "op": "audio_extracted", "duration_ms": 5000 },
    { "op": "audio_transcribed", "word_count": 87 },
    { "op": "gemini_evaluated", "latency_ms": 2340 }
  ]
}
```

#### Response — `200 OK` (when `is_final=true` AND follow-up probe triggered)

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "chunk_index": 5,
  "status": "answer_evaluated",
  "transcript": "A rate limiter is basically like a token bucket where tokens are added at a fixed rate...",
  "evaluation": {
    "scores": {
      "System Design": 55,
      "Problem Solving": 40,
      "Communication Clarity": 70,
      "Depth of Knowledge": 35,
      "Adaptability": 30
    },
    "flags": {
      "memorization_detected": true,
      "answer_quality": "memorized"
    },
    "evaluator_notes": "Response closely mirrors textbook definitions. Testing with edge-case probe."
  },
  "next_action": {
    "type": "follow_up_probe",
    "current_round": 2,
    "question": {
      "text": "What happens to your rate limiter if the Redis instance goes down mid-request? How would the system degrade?",
      "type": "follow_up_probe",
      "topic_area": "System Design"
    }
  },
  "operations": [
    { "op": "video_vaulted", "gcs_path": "gs://karna-vault/a1b2c3d4/chunk_5.webm" },
    { "op": "audio_extracted", "duration_ms": 4200 },
    { "op": "audio_transcribed", "word_count": 42 },
    { "op": "gemini_evaluated", "latency_ms": 1890 },
    { "op": "probe_triggered", "reason": "memorization_detected" }
  ]
}
```

#### Response — `200 OK` (when interview is complete — final round, `is_final=true`)

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "chunk_index": 12,
  "status": "interview_complete",
  "transcript": "...",
  "evaluation": { "..." : "..." },
  "next_action": {
    "type": "complete",
    "current_round": 5,
    "message": "Interview complete. Retrieve results via GET /results/{session_id}."
  },
  "operations": [ "..." ]
}
```

#### Error — `404 Not Found`

```json
{
  "error": "Session not found or expired",
  "session_id": "invalid-uuid"
}
```

---

### 3.3 `GET /results/{session_id}` — Retrieve Final Results

Returns the aggregated skill assessment for a completed interview session.

#### Response — `200 OK`

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "job_role": "Backend Engineer",
  "status": "completed",
  "overall_score": 72,
  "recommendation": "Moderate",
  "skill_scores": {
    "System Design": 85,
    "Problem Solving": 70,
    "Communication Clarity": 65,
    "Depth of Knowledge": 78,
    "Adaptability": 60
  },
  "flags": {
    "memorization_detected": true,
    "follow_up_triggered_count": 3,
    "total_questions_asked": 8,
    "total_rounds": 5
  },
  "round_details": [
    {
      "round": 1,
      "topic_area": "System Design",
      "question": "Describe how you would design a rate limiter...",
      "question_type": "initial",
      "transcript": "I would use a sliding window approach...",
      "scores": {
        "System Design": 85,
        "Problem Solving": 70,
        "Communication Clarity": 75,
        "Depth of Knowledge": 60,
        "Adaptability": 65
      },
      "flags": { "memorization_detected": false, "answer_quality": "strong" },
      "evaluator_notes": "Strong practical understanding...",
      "follow_ups": []
    },
    {
      "round": 2,
      "topic_area": "Problem Solving",
      "question": "How would you debug a memory leak in a production Node.js service?",
      "question_type": "initial",
      "transcript": "A memory leak is when memory is not freed...",
      "scores": { "..." : "..." },
      "flags": { "memorization_detected": true, "answer_quality": "memorized" },
      "evaluator_notes": "Textbook definition detected.",
      "follow_ups": [
        {
          "question": "What specific tool would you use to capture a heap snapshot, and how would you interpret the output?",
          "question_type": "follow_up_probe",
          "transcript": "I would... um... use Chrome DevTools...",
          "scores": { "..." : "..." },
          "flags": { "memorization_detected": false, "answer_quality": "weak" },
          "evaluator_notes": "Unable to provide concrete debugging workflow."
        }
      ]
    }
  ],
  "summary": "Candidate demonstrated strong system design fundamentals but struggled with edge-case scenarios and debugging workflows, suggesting surface-level preparation in some areas.",
  "video_vault_manifest": {
    "bucket": "karna-vault",
    "prefix": "a1b2c3d4/",
    "total_chunks": 13,
    "note": "Video sealed. Not accessed by any AI model."
  }
}
```

#### Error — `404 Not Found`

```json
{
  "error": "Session not found",
  "session_id": "invalid-uuid"
}
```

#### Error — `409 Conflict`

```json
{
  "error": "Interview still in progress. Cannot retrieve results until session is complete.",
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "current_round": 3,
  "total_rounds": 5
}
```

---

## 4. Data Payload Structures

### 4.1 In-Memory Session Object (Backend)

```python
# Stored in a Python dict: sessions[session_id] = SessionState

@dataclass
class SessionState:
    session_id: str               # UUID
    job_role: str                 # e.g., "Backend Engineer"
    status: str                   # "active" | "completed"
    total_rounds: int             # Default: 5
    current_round: int            # 1-indexed
    current_chunk_buffer: list    # List of audio bytes for current answer
    transcript_history: list      # List[RoundRecord]
    cumulative_scores: dict       # Running average of per-skill scores
    flags: dict                   # Global flags (memorization count, etc.)
    created_at: datetime
    gemini_chat_history: list     # Conversation context for Gemini
```

### 4.2 Round Record (per question-answer cycle)

```python
@dataclass
class RoundRecord:
    round: int
    topic_area: str
    question: str
    question_type: str            # "initial" | "follow_up_probe" | "clarification"
    transcript: str
    scores: dict                  # { "System Design": 85, ... }
    flags: dict                   # { "memorization_detected": bool, "answer_quality": str }
    evaluator_notes: str
    follow_ups: list              # List[RoundRecord] (nested for probes)
```

### 4.3 Frontend State Shape

```javascript
const appState = {
  // Session
  sessionId: null,              // string | null
  jobRole: "",                  // selected role
  status: "idle",               // "idle" | "initializing" | "recording" | "processing" | "completed"

  // Interview Progress
  currentRound: 0,
  totalRounds: 5,
  currentQuestion: null,        // { text, type, topic_area }

  // Media
  mediaStream: null,            // MediaStream object
  mediaRecorder: null,          // MediaRecorder instance
  chunkQueue: [],               // pending Blob chunks

  // Transcript & Evaluation Log
  roundHistory: [],             // array of round results (mirrors backend RoundRecord)
  terminalLogs: [],             // array of { timestamp, message, type: "info"|"success"|"warning"|"error" }

  // Results
  finalResults: null,           // full /results response object
};
```

---

## 5. Frontend ↔ Backend Data Flow (Sequence)

```
Frontend                          Backend                        GCP Services
   │                                 │                               │
   │─── POST /init ─────────────────►│                               │
   │    { job_role }                  │── Gemini: generate Q1 ──────►│ Gemini API
   │                                 │◄── Q1 text ──────────────────│
   │◄── { session_id, question } ────│                               │
   │                                 │                               │
   │  [User speaks answer]           │                               │
   │                                 │                               │
   │─── POST /process-chunk ────────►│                               │
   │    { chunk, is_final=false }    │── FFmpeg: split AV ──────────│
   │                                 │── Video → GCS vault ─────────►│ Cloud Storage
   │                                 │── Audio → buffer ────────────│
   │◄── { status: chunk_received } ──│                               │
   │                                 │                               │
   │─── POST /process-chunk ────────►│                               │
   │    { chunk, is_final=false }    │── FFmpeg → GCS + buffer ─────►│
   │◄── { status: chunk_received } ──│                               │
   │                                 │                               │
   │─── POST /process-chunk ────────►│                               │
   │    { chunk, is_final=true  }    │── FFmpeg → GCS + buffer ─────►│
   │                                 │── Concat audio buffers ──────│
   │                                 │── Audio → STT ───────────────►│ Speech-to-Text
   │                                 │◄── transcript ───────────────│
   │                                 │── transcript → Gemini ───────►│ Gemini API
   │                                 │◄── evaluation + next Q ──────│
   │◄── { evaluation, next_action }──│                               │
   │                                 │                               │
   │  [Repeat for rounds 2..N]       │                               │
   │                                 │                               │
   │─── GET /results/{session_id} ──►│                               │
   │◄── { full results JSON }  ──────│                               │
   │                                 │                               │
   │  [Render Radar Chart + Log]     │                               │
```

---

## 6. Gemini System Prompt Architecture

### 6.1 Role & Constraints Prompt (System Instruction)

This is the foundational system prompt sent with every Gemini API call. **Developer 1 engineers this; Developer 2 injects it into the API call.**

```
You are K.A.R.N.A. (Knowledge-based Autonomous Reasoning & Neutral Assessment), 
an unbiased technical interview evaluator.

ABSOLUTE RULES:
1. You will NEVER receive or consider any visual, demographic, or personal 
   information about the candidate. You evaluate ONLY the text transcript of 
   their spoken answers.
2. You must NEVER reference or infer the candidate's gender, age, race, 
   ethnicity, accent, educational background, or institutional affiliation.
3. You evaluate answers solely on: logical coherence, depth of technical 
   understanding, problem-solving approach, communication clarity, and 
   adaptability to edge cases.
4. You must NEVER produce a final score below 0 or above 100 for any dimension.
5. All your outputs must be valid, parseable JSON. No markdown, no prose wrapping.

EVALUATION DIMENSIONS (all scores 0-100):
- System Design
- Problem Solving
- Communication Clarity
- Depth of Knowledge
- Adaptability

MEMORIZATION DETECTION:
If a candidate's answer exhibits 2 or more of the following signals, flag 
"memorization_detected": true:
- Uses textbook-exact phrasing or definitions verbatim
- Lists concepts in a suspiciously ordered, enumerated fashion without 
  connecting them to the specific question context
- Fails to provide concrete examples or personal experience
- Uses filler phrases like "as we know" or "it is well known that"
- Provides a generic answer that could apply to any similar question

PROBE TRIGGERING LOGIC:
- If memorization_detected == true → Generate a specific EDGE-CASE follow-up 
  that forces the candidate to think beyond the memorized answer.
- If answer_quality == "weak" or "vague" → Generate a CLARIFICATION question 
  that drills into the specifics of what they said.
- If answer_quality == "strong" → Advance to the next topic area.
```

### 6.2 Question Generation Prompt (per round)

```
CONTEXT:
- Job Role: {job_role}
- Round: {current_round} of {total_rounds}
- Topics already covered: {list_of_covered_topics}
- Previous Q&A history: {transcript_history_json}

TASK:
Generate the next interview question. Choose a topic area from the EVALUATION 
DIMENSIONS list that has NOT been the primary focus of previous rounds (unless 
probing a weak area).

OUTPUT FORMAT (strict JSON, no wrapping):
{
  "question_text": "...",
  "topic_area": "...",
  "question_type": "initial",
  "difficulty": "medium" | "hard"
}
```

### 6.3 Answer Evaluation Prompt (per answer)

```
CONTEXT:
- Job Role: {job_role}
- Current Question: {question_text}
- Topic Area: {topic_area}
- Candidate's Transcript: "{transcript_text}"
- Round: {current_round} of {total_rounds}

TASK:
Evaluate the candidate's answer. Score each dimension. Detect memorization.
Determine if a follow-up probe is needed.

OUTPUT FORMAT (strict JSON, no wrapping):
{
  "scores": {
    "System Design": <int 0-100>,
    "Problem Solving": <int 0-100>,
    "Communication Clarity": <int 0-100>,
    "Depth of Knowledge": <int 0-100>,
    "Adaptability": <int 0-100>
  },
  "flags": {
    "memorization_detected": <bool>,
    "answer_quality": "strong" | "moderate" | "weak" | "memorized" | "vague"
  },
  "evaluator_notes": "<1-2 sentence assessment>",
  "probe_needed": <bool>,
  "probe_question": {
    "question_text": "..." | null,
    "topic_area": "...",
    "question_type": "follow_up_probe" | "clarification"
  }
}
```

### 6.4 Final Summary Prompt (end of interview)

```
CONTEXT:
- Job Role: {job_role}
- Complete Q&A History: {full_transcript_history_json}
- Per-Round Scores: {all_round_scores_json}

TASK:
Produce the final aggregated assessment. Average the per-round scores for each 
dimension (weighted: initial questions = 1.0x, follow-up probes = 1.5x weight 
since they reveal true understanding). Generate an overall score and a 
recommendation tier.

RECOMMENDATION TIERS:
- "Strong": overall_score >= 75
- "Moderate": 50 <= overall_score < 75
- "Weak": overall_score < 50

OUTPUT FORMAT (strict JSON, no wrapping):
{
  "overall_score": <int 0-100>,
  "recommendation": "Strong" | "Moderate" | "Weak",
  "skill_scores": {
    "System Design": <int>,
    "Problem Solving": <int>,
    "Communication Clarity": <int>,
    "Depth of Knowledge": <int>,
    "Adaptability": <int>
  },
  "flags": {
    "memorization_detected": <bool>,
    "follow_up_triggered_count": <int>,
    "total_questions_asked": <int>,
    "total_rounds": <int>
  },
  "summary": "<2-3 sentence holistic assessment>"
}
```

---

## 7. Media Processing Pipeline (Backend Detail)

### 7.1 Chunk Reception & FFmpeg Processing

```
Incoming WebM Chunk (VP8 video + Opus audio)
              │
              ▼
    ┌─────────────────────┐
    │  Save to temp file   │   /tmp/{session_id}/chunk_{index}.webm
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  FFmpeg: Extract     │   ffmpeg -i chunk.webm -vn -acodec pcm_s16le
    │  Audio Track         │         -ar 16000 -ac 1 chunk_audio.wav
    └──────────┬──────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
  ┌─────────┐   ┌──────────────┐
  │  Upload  │   │  Append to   │
  │  .webm   │   │  Audio       │
  │  to GCS  │   │  Buffer      │
  └──────────┘   └──────────────┘
                        │
                  (on is_final=true)
                        │
                        ▼
               ┌─────────────────┐
               │  Concatenate    │
               │  Audio Buffers   │
               │  → full_answer  │
               │    .wav          │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │  Google Cloud   │
               │  Speech-to-Text  │
               │  (sync recognize)│
               └────────┬────────┘
                        │
                        ▼
                   Transcript
                    (string)
```

### 7.2 FFmpeg Commands

```bash
# Extract audio from WebM chunk (mono, 16kHz, 16-bit PCM — optimal for STT)
ffmpeg -i input_chunk.webm -vn -acodec pcm_s16le -ar 16000 -ac 1 output_audio.wav

# Concatenate multiple WAV chunks into a single file
ffmpeg -i "concat:chunk_0.wav|chunk_1.wav|chunk_2.wav" -acodec pcm_s16le -ar 16000 -ac 1 full_answer.wav
```

### 7.3 GCS Vault Structure

```
gs://karna-vault/
  └── {session_id}/
      ├── chunk_000.webm
      ├── chunk_001.webm
      ├── chunk_002.webm
      └── ...
```

> **Access Policy:** The GCS bucket is configured as **write-only** from the application. No read or download operations are performed by any application component. The vault exists solely for audit/compliance purposes.

---

## 8. Error Handling Strategy

| Scenario | HTTP Code | Behavior |
|---|---|---|
| Invalid `job_role` in `/init` | `400` | Return error message with valid options |
| Unknown `session_id` in `/process-chunk` | `404` | Return session-not-found error |
| FFmpeg processing fails | `500` | Log error, return `processing_failed` status; skip chunk |
| Speech-to-Text returns empty transcript | `200` | Return `transcript: ""` with a note; Gemini asked to re-prompt |
| Gemini API timeout (>7s) | `504` | Retry once; if still fails, return cached previous question |
| Gemini returns invalid JSON | `500` | Retry with stricter prompt; if fails, use fallback scoring |
| `/results` called before completion | `409` | Return conflict with progress info |
| Chunk received out of order | `200` | Accept and process; chunks are independent after buffering |

---

## 9. Security & Privacy Considerations (MVP)

| Concern | Mitigation |
|---|---|
| Video data leakage to AI | Architectural enforcement: video goes to GCS only; never passed to any model |
| Candidate PII in transcript | Gemini system prompt explicitly forbids referencing personal identifiers |
| Session data exposure | Sessions are ephemeral (in-memory); destroyed on server restart |
| HTTPS enforcement | Cloud Run enforces HTTPS by default |
| CORS | Backend configures CORS to allow only the frontend origin |

---

## 10. Deployment Topology (MVP)

```
┌────────────────────────┐        ┌────────────────────────────────┐
│   Frontend (React)      │        │   Backend (FastAPI)             │
│   Static hosting         │  HTTPS │   Cloud Run (1 instance)        │
│   (Vercel / Firebase     │◄──────►│   Docker container              │
│    Hosting / local)      │        │   - FFmpeg installed            │
│                          │        │   - Python 3.11+                │
└────────────────────────┘        └──────────┬─────────────────────┘
                                             │
                                     ┌───────┴───────┐
                                     │               │
                              ┌──────▼──────┐  ┌─────▼──────────┐
                              │  GCS Bucket  │  │  GCP APIs       │
                              │  karna-vault │  │  - Speech-to-Text│
                              └─────────────┘  │  - Gemini 3.0    │
                                               └──────────────────┘
```

---

## 11. Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| In-memory session store (no DB) | MVP simplicity. Single Cloud Run instance. No persistence needed beyond the session. |
| Chunked upload (not full file) | Enables real-time terminal log UX and progressive processing. Avoids large single uploads. |
| FFmpeg for AV separation | Battle-tested, fast, available as a system package in Docker. No SDK dependency. |
| Sync STT (not streaming) | Simpler implementation. Full-answer accuracy > partial-answer speed for evaluation quality. |
| REST (not WebSocket) | Simpler to implement for MVP. Chunk intervals (5s) are infrequent enough for REST. |
| 5 evaluation dimensions fixed | Keeps the radar chart clean and comparable. More dimensions = diluted signal for MVP. |
| Follow-up probes don't consume a round | Probes are "bonus" questions within a round, not counted. This ensures 5 full topics are covered. |

---

*Document Version: 1.0*
*Last Updated: 2026-03-26*
*Derived From: requirements.md v1.0 (Approved)*
