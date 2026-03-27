Integration day checklist ✅ :

0. Merge Part 2 into Part 1 — literally copy gemini_service.py into the backend/app/ folder. It's already designed to live there.
1. Run the backend — uvicorn app.main:app
2. Point the frontend — set API_BASE_URL=http://localhost:8000 in the React app
3. Test the 3 endpoints — Postman or curl: /init → /process-chunk → /results
4. Open the frontend — npm run dev → pick a role → start talking
