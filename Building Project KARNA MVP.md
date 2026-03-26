# Chat Conversation

Note: _This is purely the output of the chat conversation and does not contain any raw data, codebase snippets, etc. used to generate the output._

### User Input

System Role: You are an elite AI Architect and Technical Project Manager. We are building a hackathon MVP named "Project K.A.R.N.A." (Knowledge-based Autonomous Reasoning & Neutral Assessment) for the Google Solution Challenge (Unbiased AI Decision track).

Team Structure & Division of Labor:
This is a two-person team. The architecture must clearly separate these concerns:

Developer 1 (Me - AI Architect & Frontend): Handling the Web UI (React/JS), MediaRecorder API for webcam/mic capture, audio chunking, the visual "terminal log" UI, rendering the final Radar Chart dashboard, and engineering the strict Gemini System Prompts.

Developer 2 (My Friend - Backend & GCP Infra): Handling the Python FastAPI server, Google Cloud Run deployment, receiving media chunks, separating audio from video, vaulting video to Google Cloud Storage (GCS), routing audio to Google Cloud Speech-to-Text, and managing the API calls to Gemini.

Project Core Features (MVP Scope strictly limited to this):

Blind Media Separation: Frontend captures video/audio. Backend vaults the video to GCS (to ensure zero visual bias) and only passes transcribed audio text to the AI.

Agentic Deep-Probe Engine: The Gemini AI evaluates the logic of candidate answers. If an answer sounds memorized, it dynamically triggers a specific edge-case question.

Skill Graph Dashboard: The system outputs a strict JSON object mapping the candidate's exact scores (e.g., System Design: 85/100) instead of a resume.

Google Cloud Native: Deployed via Cloud Run, GCS, Speech-to-Text, and the Gemini API.

Execution Rules (The Spec-Driven Kiro Workflow):
You must act sequentially and strictly follow this file generation process. You are strictly forbidden from generating code or moving to the next step until I explicitly type "Approved."

Step 1: The Requirements Phase

Create a folder named spec/ in the root directory.

Generate a spec/requirements.md file detailing the core MVP features, user flows, and strictly defining what is out-of-scope.

STOP. Ask me to review it. Wait for my feedback or approval.

Step 2: The Design Phase

Once requirements are approved, generate a spec/design.md file.

This must include the system architecture, the exact Frontend/Backend data payload structures, the API endpoint contracts (/init, /process-chunk, /results), and the Gemini System Prompt logic flow.

STOP. Ask me to review it. Wait for my feedback or approval.

Step 3: The Task Breakdown Phase

Once design is approved, generate a spec/tasks.md file.

This file must break the entire build down into granular, step-by-step tasks and subtasks, explicitly assigned to either "Frontend/AI" or "Backend/Infra".

Crucial Formatting Rule: Every single task and subtask MUST be formatted as a markdown checkbox (e.g., - [ ] [Backend] Build /init endpoint). This is mandatory so our execution agent (Claude Code) can programmatically check them off (- [x]) as it builds.

STOP. Ask me to review the final tasks list.

Begin Step 1 now.

### Planner Response

Starting Step 1: The Requirements Phase. I'll create the `spec/requirements.md` now.

*Listed directory [Project KARNA](file:///Users/tusharsingh/Documents/PROJECTS/Project%20KARNA) *

*Edited relevant file*

### Planner Response

## ✅ Step 1 Complete — `spec/requirements.md` Generated

**📄 File:** [`spec/requirements.md`](file:///Users/tusharsingh/Documents/PROJECTS/Project%20KARNA/spec/requirements.md)

Here's what it covers:

| Section | Highlights |
|---|---|
| **Problem Statement** | Unconscious bias in hiring; K.A.R.N.A.'s blind pipeline approach |
| **Core Features (3.1–3.4)** | Blind Media Separation, Agentic Deep-Probe Engine, Skill Graph Dashboard, GCP-native architecture |
| **User Flow** | Full 10-step end-to-end interviewer flow with ASCII diagram |
| **Functional Reqs (14)** | Prioritized P0/P1/P2 with explicit IDs (FR-01 through FR-14) |
| **Non-Functional Reqs (6)** | Latency targets, security invariants, browser compat |
| **Out-of-Scope (12 items)** | Explicitly lists what is **not** in the MVP (auth, mobile, multi-session, etc.) |
| **Technical Constraints** | Locked tech stack — React, FastAPI, WebM, FFmpeg, Gemini 2.0 Flash |
| **Success Criteria** | 5 checkboxes for what a successful hackathon demo must show |

---

### 🛑 STOPPED — Awaiting Your Review

Please review the requirements document. Let me know if you want any changes, additions, or clarifications. I will **not** proceed to Step 2 (Design) until you explicitly type **"Approved."**

### User Input

Approved

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

### Planner Response

Requirements approved (with your edits noted — background bias added, latency tightened to 7s, Gemini bumped to 3.0 Flash). Moving to **Step 2: The Design Phase**.

### User Input

yes proceed for Step 2

*Edited relevant file*

### Planner Response

## ✅ Step 2 Complete — `spec/design.md` Generated

**📄 File:** [`spec/design.md`](file:///Users/tusharsingh/Documents/PROJECTS/Project%20KARNA/spec/design.md)

Here's what it covers:

| Section | Highlights |
|---|---|
| **§1 Architecture** | Full ASCII diagram showing Frontend → Backend → GCP services data flow |
| **§2 Ownership Matrix** | Every component explicitly tagged to Developer 1 or Developer 2 |
| **§3 API Contracts** | Complete request/response schemas for all 3 endpoints (`/init`, `/process-chunk`, `/results`) including all edge-case response variants (probe triggered, interview complete, errors) |
| **§4 Data Structures** | Backend `SessionState` + `RoundRecord` dataclasses, Frontend state shape |
| **§5 Sequence Diagram** | Full Frontend ↔ Backend ↔ GCP message flow |
| **§6 Gemini Prompts** | 4 engineered prompts — Role/Constraints, Question Generation, Answer Evaluation, Final Summary — all with strict JSON output formats |
| **§7 Media Pipeline** | FFmpeg commands, chunk processing flow, GCS vault structure |
| **§8 Error Handling** | 8 failure scenarios with HTTP codes and fallback behaviors |
| **§9 Security** | Privacy mitigations for video leakage, PII, CORS, HTTPS |
| **§10 Deployment** | Cloud Run topology diagram |
| **§11 Design Decisions** | 7 key architectural choices with rationale (why REST not WebSocket, why in-memory not DB, etc.) |

### Key design decisions to review:

1. **Follow-up probes don't consume a round** — probes are "bonus" questions within a round so all 5 topic areas get covered
2. **Sync STT over streaming** — simpler, and we need the full answer before evaluating anyway
3. **REST over WebSocket** — 5s chunk intervals are infrequent enough; MVP simplicity wins
4. **Probe weight = 1.5x** in final scoring — because probes reveal deeper understanding

---

### 🛑 STOPPED — Awaiting Your Review

Please review the design document. I will **not** proceed to Step 3 (Task Breakdown) until you explicitly type **"Approved."**