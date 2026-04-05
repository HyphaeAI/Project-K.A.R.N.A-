# In your terminal (where venv is activated or will be):                                                      
  cd /Users/tusharsingh/Documents/PROJECTS/Project\ KARNA/backend                                            
                                                                                                                
  # Set your OpenRouter API key                                                                                 
  export OPENROUTER_API_KEY="your-openrouter-api-key-here"                                                   

  # Start the backend (using venv)
  source ../.venv/bin/activate
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  After startup, test:

  curl -s -X POST http://localhost:8000/init -H "Content-Type: application/json" -d '{"job_role": "Frontend
  Engineer"}' | python3 -m json.tool

  Expected: A successful response with session_id, current_round, total_rounds, and a question object.

  ---
  Changes made:
  - ✅ Added requests to requirements.txt
  - ✅ Replaced Gemini SDK with OpenRouter HTTP API
  - ✅ Uses stepfun/step-3.5-flash model (you can change model name in MODEL_NAME constant)
  - ✅ Reads OPENROUTER_API_KEY instead of GEMINI_API_KEY
  - ✅ Same interface: /init, /process-chunk, /results/{id} unchanged

  Let me know once you've started it with the OpenRouter key!