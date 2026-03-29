# K.A.R.N.A. — Manual Setup & Local Testing Guide

Everything in this file must be done by you manually to get the app running locally for testing.

---

## 1. Fill in your .env file

Open `backend/.env` and fill in all values:

```
GEMINI_API_KEY=your-actual-gemini-api-key
GCS_BUCKET=karna-vault
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/your-service-account.json
ALLOWED_ORIGINS=http://localhost:5173
TOTAL_ROUNDS=5
```

---

## 2. Get your Gemini API Key

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key and paste it into `backend/.env` as `GEMINI_API_KEY`

---

## 3. Set up Google Cloud Project

1. Go to https://console.cloud.google.com
2. Create a new project (or use an existing one)
3. Enable these two APIs:
   - Cloud Speech-to-Text API
   - Cloud Storage API

---

## 4. Create a GCP Service Account

1. Go to IAM and Admin then Service Accounts
2. Click "Create Service Account", name it `karna-backend`
3. Grant these roles:
   - Storage Object Creator (for GCS video uploads)
   - Cloud Speech Client (for Speech-to-Text)
4. Click "Create Key" then JSON then Download the file
5. Save it somewhere safe e.g. `~/keys/karna-sa.json`
6. Set the full path in `backend/.env` as `GOOGLE_APPLICATION_CREDENTIALS`

---

## 5. Create the GCS Bucket

Run in your terminal (requires gcloud CLI):

```bash
gsutil mb -l us-central1 gs://karna-vault
```

Or create it manually in GCP Console then Cloud Storage then Create Bucket and name it `karna-vault`.

---

## 6. Install and run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Verify it is working:

```bash
curl http://localhost:8080/health
```

Expected response: `{"status":"ok"}`

---

## 7. Install and run the frontend

Open a new terminal tab:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

---

## 8. Test the full flow manually

With both backend and frontend running:

1. Open http://localhost:5173
2. Select a job role e.g. "Backend Engineer"
3. Click "Start Interview" — backend calls Gemini and returns the first question
4. Allow camera and microphone access when prompted
5. Click "Start Answer" and speak your answer
6. Click "Submit Answer" — backend processes audio, transcribes via STT, evaluates via Gemini
7. The next question appears in the UI
8. Repeat for all 5 rounds
9. After the final round the Results Dashboard loads with Radar Chart and scores

---

## 9. Test the backend API directly (optional)

Initialize a session:

```bash
curl -X POST http://localhost:8080/init \
  -H "Content-Type: application/json" \
  -d "{\"job_role\": \"Backend Engineer\"}"
```

Check results for a completed session:

```bash
curl http://localhost:8080/results/YOUR_SESSION_ID
```

---

## 10. Verify FFmpeg is installed on your machine

The backend uses FFmpeg to process audio. Check it is available:

```bash
ffmpeg -version
```

If not installed:
- Mac: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`
- Windows: Download from https://ffmpeg.org/download.html

---

## Summary

| Step | What to do |
|------|------------|
| 1 | Fill in `backend/.env` |
| 2 | Get Gemini API key from aistudio.google.com |
| 3 | Enable GCP APIs (Speech-to-Text and Cloud Storage) |
| 4 | Create service account and download JSON key |
| 5 | Create GCS bucket named karna-vault |
| 6 | Run backend with uvicorn on port 8080 |
| 7 | Run frontend with npm run dev inside frontend/ |
| 8 | Open http://localhost:5173 and test the full interview flow |
| 9 | Optionally test API endpoints directly with curl |
| 10 | Make sure FFmpeg is installed locally |
