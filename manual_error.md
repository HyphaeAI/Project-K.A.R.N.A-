# K.A.R.N.A. — Known Errors & Project Drawbacks

---

## 1. Known Errors

---

### 1.1 Gemini API — Premium / Quota Errors

**Error type:** `google.api_core.exceptions.ResourceExhausted` or `429 Too Many Requests`

**When it happens:**
- When `LLM_PROVIDER=gemini` is set in `.env` and the free-tier quota is exhausted.
- Gemini 1.5 Flash free tier has strict RPM (requests per minute) and daily token limits.
- The model name in code is hardcoded to `gemini-1.5-flash` — if your API key is on a project that only has access to paid models (e.g., `gemini-2.0-pro`), the call will fail with a billing/permission error.

**Error message you will see in backend logs:**
```
Gemini API call failed attempt 1/3: ResourceExhausted: 429 You exceeded your current quota
```
or
```
Gemini API call failed attempt 1/3: PermissionDenied: 403 Gemini API is not available in your region / billing not enabled
```

**Root cause in code:** `backend/app/gemini_service.py` — `_get_gemini_model()` initialises with `gemini-1.5-flash`. No quota guard or rate-limit backoff is implemented beyond the 2-retry loop.

**Current workaround:** Switch to Groq (free, no credit card) by setting in `backend/.env`:
```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your-key-here
```

**Permanent fix needed:** Add exponential backoff + quota-aware retry logic in `_call_gemini()`.

---

### 1.2 Google Cloud Storage (GCS) — Authentication / Bucket Errors

**Error type:** `google.auth.exceptions.DefaultCredentialsError` or `google.api_core.exceptions.Forbidden`

**When it happens:**
- When `USE_LOCAL_STORAGE=false` is set and `GOOGLE_APPLICATION_CREDENTIALS` is missing or points to an invalid service account JSON.
- When the GCS bucket `karna-vault` does not exist in the project tied to the credentials.
- When the service account lacks the `storage.objects.create` IAM role on the bucket.

**Error message you will see in backend logs:**
```
GCS vault failed for session=<uuid> chunk=0
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials.
```
or
```
google.api_core.exceptions.Forbidden: 403 <service-account>@<project>.iam.gserviceaccount.com
does not have storage.objects.create access to the Google Cloud Storage object.
```

**Root cause in code:** `backend/app/gcs_service.py` — `_vault_gcs()` falls through to `storage.Client()` (ADC) when `GOOGLE_APPLICATION_CREDENTIALS` is not set. The error is caught and re-raised, which causes the entire `/process-chunk` request to fail with HTTP 500.

**Current workaround:** Keep `USE_LOCAL_STORAGE=true` (the default). Video chunks are saved to `/tmp/karna-vault/` on the local machine instead.

**Permanent fix needed:**
1. Create the GCS bucket `karna-vault` in your GCP project.
2. Create a service account with `Storage Object Creator` role.
3. Download the JSON key and set: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`
4. Set `USE_LOCAL_STORAGE=false` in `.env`.

---

## 2. Project Drawbacks

---

### 2.1 In-Memory Session Store — No Persistence

All session data (transcript history, scores, round state) lives in a Python `dict`. Any backend restart, crash, or Cloud Run cold start wipes all active sessions. There is no recovery mechanism. This is a fundamental limitation for any production or multi-user use.

---

### 2.2 Single-Instance Architecture

The session store is module-level, meaning it only works correctly when there is exactly one backend instance. Cloud Run can spin up multiple instances under load, causing sessions created on instance A to be invisible to instance B. The system will return `404 Session not found` for valid sessions.

---

### 2.3 No Real-Time Feedback During Recording

The frontend sends chunks every 5 seconds but the candidate only sees the next question after the final chunk is processed (FFmpeg + Whisper + LLM). There is no streaming or partial feedback. The UI is effectively frozen during processing, which can feel unresponsive.

---

### 2.4 Whisper Accuracy Limitations

The `base` Whisper model (default) is fast but has lower accuracy than `medium` or `large`. Technical jargon, acronyms (e.g., "gRPC", "CRDT", "k8s"), and non-native English accents are frequently mis-transcribed. Since the entire evaluation is based on the transcript, transcription errors directly degrade evaluation quality.

---

### 2.5 Gemini / Groq JSON Reliability

Both LLM providers occasionally return malformed JSON or wrap the response in markdown fences despite the strict prompt. The retry logic handles this in most cases, but after 2 retries the system falls back to a flat `50/50/50/50/50` score for all dimensions — silently masking the failure. The candidate gets a meaningless evaluation with no indication something went wrong.

---

### 2.6 No Authentication or Session Isolation

There is no user authentication. Anyone who knows a `session_id` UUID can call `/results/{session_id}` and retrieve the full interview transcript and scores. For a hackathon demo this is acceptable, but it is a serious privacy issue in any real deployment.

---

### 2.7 Evaluation Bias Toward Verbose Answers

The memorization detection heuristics and scoring prompts implicitly reward longer, more structured answers. Candidates who give concise but correct answers may be flagged as "vague" and receive lower scores, while candidates who give verbose but shallow answers may score higher on "Communication Clarity".

---

### 2.8 Fixed 5 Evaluation Dimensions

The radar chart and scoring are hardcoded to exactly 5 dimensions: System Design, Problem Solving, Communication Clarity, Depth of Knowledge, Adaptability. These dimensions are not appropriate for all roles (e.g., a DevOps Engineer interview should weight "Operational Reliability" and "Incident Response" more heavily than "System Design"). There is no per-role dimension customisation.

---

### 2.9 No Candidate-Facing Interface

The current UI is designed for the interviewer/operator. The candidate has no separate view, no ability to see the question clearly without the operator's screen, and no way to request clarification or a repeat of the question. This makes the system unsuitable for remote or async interviews.

---

### 2.10 Temp File Cleanup Race Condition

`media_processor.cleanup_temp_files(session_id)` is called at the end of every final-chunk processing cycle. If a probe follow-up is triggered and the candidate answers again, the temp directory for that session has already been deleted, which will cause `extract_audio()` to fail on the next chunk because the parent directory no longer exists.

**Affected code:** `backend/app/main.py` — `cleanup_temp_files` is called unconditionally after every `is_final=true` chunk, including probe rounds.

---

### 2.11 No Offline / Fallback Mode for LLM

If both Groq and Gemini are unavailable (network outage, quota exhausted), the system falls back to hardcoded `50` scores for all dimensions and a generic fallback question. The interview continues but produces completely meaningless results with no user-visible warning on the frontend.

---

### 2.12 GCS Bucket Must Be Pre-Created Manually

When switching to GCS mode (`USE_LOCAL_STORAGE=false`), the bucket `karna-vault` must already exist. The application does not create it automatically. If the bucket is missing, every `/process-chunk` call fails with HTTP 500 and the interview cannot proceed.

---

*Last updated: 2026-04-03*
*Project: K.A.R.N.A. — Google Solution Challenge 2026*
