# Project K.A.R.N.A. — Requirements Specification

> **K**nowledge-based **A**utonomous **R**easoning & **N**eutral **A**ssessment
> Google Solution Challenge 2026 — Unbiased AI Decision Track

---

## 1. Problem Statement

Traditional hiring interviews are plagued by **unconscious bias**. Interviewers form snap judgments based on a candidate's appearance, gender, ethnicity, accent, their background(like which college is he/she in now or was), or body language — often within the first 7 seconds. These visual and social cues have **zero correlation** with technical competence, yet they dominate hiring outcomes.

**Project K.A.R.N.A.** eliminates this by enforcing a **Blind Interview Pipeline**: the AI decision engine never sees the candidate. It only receives a text transcript of their words and evaluates the **logic, depth, and consistency** of their answers — nothing else.

---

## 2. Target Users

| User Role | Description |
|---|---|
| **Interviewer / Recruiter** | Initiates the interview session, selects the job role/domain, and reviews the final Skill Graph dashboard. |
| **Candidate** | Joins the interview session via webcam/mic. Their video is vaulted (never analyzed); only their speech is evaluated. |

> **MVP Scope:** A single-user flow where the Interviewer also acts as the session operator. There is no separate candidate portal.

---

## 3. Core MVP Features

### 3.1 Blind Media Separation Pipeline

**Goal:** Guarantee zero visual bias by architecturally separating video from audio before any AI processing.

| Step | Action | Owner |
|---|---|---|
| 1 | Frontend captures webcam + mic stream via `MediaRecorder` API | Frontend |
| 2 | Media chunks are streamed to the backend (`/process-chunk`) | Frontend |
| 3 | Backend extracts the audio track from the received media chunk | Backend |
| 4 | Raw video chunk is immediately vaulted to **Google Cloud Storage (GCS)** — never analyzed | Backend |
| 5 | Audio is routed to **Google Cloud Speech-to-Text** for transcription | Backend |
| 6 | Only the resulting **text transcript** is forwarded to the Gemini AI engine | Backend |

**Key Invariant:** At no point does the AI model receive video frames, image data, or any visual representation of the candidate.

---

### 3.2 Agentic Deep-Probe Engine

**Goal:** Go beyond surface-level Q&A. The AI dynamically adapts its questioning strategy based on the quality and authenticity of the candidate's responses.

#### Behavior Flow:

1. **Initial Question:** Gemini generates a domain-relevant technical question based on the selected job role (e.g., "Backend Engineer", "ML Engineer").
2. **Answer Evaluation:** After receiving the candidate's transcribed answer, Gemini evaluates it across multiple dimensions:
   - **Logical Coherence:** Does the answer follow a logical structure?
   - **Depth of Understanding:** Does it demonstrate first-principles thinking or just keyword regurgitation?
   - **Memorization Detection:** Does the phrasing sound rehearsed, textbook-like, or templated?
3. **Dynamic Probe (Agentic Behavior):**
   - If the answer scores **high** on memorization heuristics → Gemini triggers a **specific edge-case follow-up** designed to test genuine understanding (e.g., "What happens if that system loses network connectivity mid-transaction?").
   - If the answer is **vague or shallow** → Gemini asks a **clarifying drill-down** question (e.g., "Can you walk me through the exact data flow step by step?").
   - If the answer is **strong and original** → Gemini advances to the next topic area.
4. **Loop:** This continues for a configurable number of rounds (MVP default: **5 question rounds**).

#### Gemini System Prompt Constraints:
- The AI is **strictly forbidden** from considering any metadata about the candidate (name, gender, age, location).
- The AI must evaluate **only the textual content** of the transcript.
- The AI must output structured JSON assessments at each step (not free-form text).

---

### 3.3 Skill Graph Dashboard

**Goal:** Replace subjective "gut feel" interview notes with a **quantitative, visual skill assessment**.

#### Output Format:
After all question rounds are complete, Gemini produces a **strict JSON object** with the following structure:

```json
{
  "candidate_id": "session-uuid",
  "overall_score": 72,
  "skill_scores": {
    "System Design": 85,
    "Problem Solving": 70,
    "Communication Clarity": 65,
    "Depth of Knowledge": 78,
    "Adaptability": 60
  },
  "flags": {
    "memorization_detected": true,
    "follow_up_triggered_count": 3
  },
  "summary": "Candidate demonstrated strong system design fundamentals but struggled with edge-case scenarios, suggesting surface-level preparation."
}
```

#### Frontend Rendering:
- Scores are rendered as a **Radar Chart** (spider chart) on the dashboard.
- The dashboard also displays:
  - Per-question transcript log with AI evaluation notes.
  - Flag indicators (e.g., 🚩 Memorization Detected).
  - Overall recommendation tier: **Strong / Moderate / Weak**.

---

### 3.4 Google Cloud Native Architecture

| Service | Purpose |
|---|---|
| **Google Cloud Run** | Hosts the FastAPI backend as a containerized, auto-scaling service |
| **Google Cloud Storage (GCS)** | Vaults raw video chunks (write-only from backend; never read by AI) |
| **Google Cloud Speech-to-Text** | Converts audio chunks to text transcripts |
| **Gemini API** | Powers the agentic deep-probe evaluation engine |

---

## 4. User Flow (End-to-End)

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERVIEWER FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Open Web UI → Select Job Role (e.g., "Backend Engineer")    │
│  2. Click "Start Interview" → Camera/Mic permissions granted    │
│  3. Backend initializes session → returns session_id            │
│  4. AI generates first question → displayed on screen           │
│  5. Candidate speaks answer → audio captured in chunks          │
│  6. Chunks streamed to backend:                                 │
│     ├── Video → GCS vault (sealed)                              │
│     ├── Audio → Speech-to-Text → transcript                    │
│     └── Transcript → Gemini evaluation                         │
│  7. Gemini returns:                                             │
│     ├── Score for current answer                                │
│     ├── Next question (or follow-up probe)                      │
│     └── Flags (memorization, shallow, etc.)                     │
│  8. Repeat steps 5-7 for N rounds (default: 5)                  │
│  9. Click "End Interview" → triggers final evaluation           │
│ 10. Dashboard renders:                                          │
│     ├── Radar Chart with skill scores                           │
│     ├── Full transcript with per-answer notes                   │
│     └── Overall recommendation (Strong/Moderate/Weak)           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| **FR-01** | System shall capture webcam and microphone streams simultaneously | P0 |
| **FR-02** | System shall stream media chunks to backend in near real-time (≤5s intervals) | P0 |
| **FR-03** | Backend shall separate audio from video in each received chunk | P0 |
| **FR-04** | Backend shall vault video to GCS without any AI processing | P0 |
| **FR-05** | Backend shall transcribe audio using Google Cloud Speech-to-Text | P0 |
| **FR-06** | System shall forward only text transcripts to the Gemini API | P0 |
| **FR-07** | Gemini shall generate an initial question based on the selected job role | P0 |
| **FR-08** | Gemini shall evaluate answers and detect memorization patterns | P0 |
| **FR-09** | Gemini shall dynamically generate follow-up probes when triggered | P0 |
| **FR-10** | System shall produce a structured JSON skill assessment after all rounds | P0 |
| **FR-11** | Frontend shall render a Radar Chart from the skill scores JSON | P0 |
| **FR-12** | Frontend shall display a real-time "terminal log" of system operations | P1 |
| **FR-13** | Frontend shall display per-answer evaluation notes and flags | P1 |
| **FR-14** | System shall support configurable number of interview rounds (default: 5) | P2 |

---

## 6. Non-Functional Requirements

| ID | Requirement |
|---|---|
| **NFR-01** | End-to-end latency from speech to AI response shall be under 7 seconds |
| **NFR-02** | Video data shall never be exposed to any AI model or analysis pipeline |
| **NFR-03** | The system shall run entirely on Google Cloud infrastructure |
| **NFR-04** | The backend shall be stateless and horizontally scalable via Cloud Run |
| **NFR-05** | The frontend shall work on modern browsers (Chrome 90+, Firefox 90+, Edge 90+) |
| **NFR-06** | All API communication shall use HTTPS |

---

## 7. Strictly Out-of-Scope (MVP)

The following are **explicitly excluded** from the MVP build. These are potential future features but must NOT be implemented, designed for, or referenced in the current codebase:

| Excluded Feature | Reason |
|---|---|
| ❌ Multi-candidate simultaneous sessions | MVP is single-session only |
| ❌ Candidate self-service portal | Interviewer operates the session |
| ❌ Video analysis / facial recognition | Directly contradicts the anti-bias mission |
| ❌ Resume/CV upload and parsing | MVP evaluates live answers only |
| ❌ User authentication / login system | Not needed for hackathon demo |
| ❌ Database / persistent storage (beyond GCS) | Session data is ephemeral |
| ❌ Email notifications or scheduling | Out of scope |
| ❌ Mobile-responsive design | Desktop-first for hackathon demo |
| ❌ Multilingual support | English-only MVP |
| ❌ Custom question bank import | AI generates questions dynamically |
| ❌ Candidate comparison / ranking across sessions | Single session scope |
| ❌ Export to PDF / ATS integration | Future feature |

---

## 8. Technical Constraints

| Constraint | Detail |
|---|---|
| **Frontend** | React (JavaScript), MediaRecorder API, Chart.js or Recharts for Radar Chart |
| **Backend** | Python, FastAPI, FFmpeg (for audio extraction) |
| **Cloud** | Google Cloud Run, GCS, Speech-to-Text v2, Gemini 3.0 Flash |
| **Media Format** | WebM (VP8+Opus) from MediaRecorder; audio extracted as FLAC/WAV for STT |
| **API Protocol** | REST (JSON payloads) over HTTPS |
| **Deployment** | Docker container → Cloud Run |

---

## 9. Success Criteria (Hackathon Demo)

A successful demo must show:

1. ✅ A live webcam feed visible on the frontend (proving capture works).
2. ✅ A terminal log showing chunks being sent, video being vaulted, audio being transcribed.
3. ✅ The AI asking an initial question, receiving an answer, and triggering a follow-up probe.
4. ✅ A final Radar Chart dashboard appearing with per-skill scores.
5. ✅ The entire flow completing in under 3 minutes for a 5-question interview.

---

*Document Version: 1.0*
*Last Updated: 2026-03-26*
*Authors: Project K.A.R.N.A. Team*
