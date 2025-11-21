import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
from agent import get_llm_response
import uvicorn
import httpx
from urllib.parse import urljoin
from datetime import datetime
import json

app = FastAPI()

# Secrets
MY_SECRET = os.getenv("MY_SECRET")
MY_EMAIL = os.getenv("MY_EMAIL")

# --- IN-MEMORY LOGGING ---
QUIZ_LOGS = []

class RequestData(BaseModel):
    email: str
    secret: str
    url: str

# --- ROOT ENDPOINT ---
@app.get("/")
def read_root():
    return {
        "status": "API is running",
        "documentation": "Send POST requests to /quiz",
        "history": "/history"
    }

# --- HISTORY ENDPOINT ---
@app.get("/history")
def get_history():
    return {"count": len(QUIZ_LOGS), "logs": QUIZ_LOGS}

@app.post("/quiz")
async def solve_quiz(data: RequestData):
    # 1. Validate Secret
    if data.secret != MY_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Secret")

    current_url = data.url
    final_result = {}
    
    # Start Logging
    session_log = {
        "timestamp": datetime.now().isoformat(),
        "start_url": data.url,
        "steps": []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        
        step_count = 0
        max_steps = 10 
        
        while step_count < max_steps:
            print(f"--- Step {step_count + 1}: Processing {current_url} ---")
            step_record = {"step": step_count + 1, "url": current_url, "status": "processing"}
            
            try:
                # A. Scrape
                await page.goto(current_url, timeout=60000)
                await page.wait_for_load_state("networkidle")
                html_content = await page.content()
                
                # B. Solve
                submission_payload = await get_llm_response(html_content, current_url, MY_EMAIL, MY_SECRET)
                step_record["llm_answer"] = submission_payload.get("answer")
                
                # C. Submit
                submit_url = submission_payload.get("submit_url_override") or "https://tds-llm-analysis.s-anand.net/demo/submit"
                if "submit_url_override" in submission_payload:
                    del submission_payload["submit_url_override"]
                submit_url = urljoin(current_url, submit_url)

                async with httpx.AsyncClient() as client:
                    resp = await client.post(submit_url, json=submission_payload, timeout=30.0)
                    
                    # --- NEW: ROBUST ERROR HANDLING ---
                    try:
                        result = resp.json()
                    except json.JSONDecodeError:
                        # If server returns HTML/Text instead of JSON, catch it
                        print(f"Warning: Non-JSON response from {submit_url}")
                        result = {
                            "correct": False, 
                            "error": "External server returned non-JSON response.",
                            "raw_response": resp.text[:200] # Log first 200 chars
                        }
                    # ----------------------------------
                    
                    final_result = result
                
                # Record result
                step_record["status"] = "submitted"
                step_record["server_response"] = result
                session_log["steps"].append(step_record)

                # D. Recursion
                if result.get("correct") and result.get("url"):
                    next_url = result["url"]
                    current_url = urljoin(current_url, next_url)
                    step_count += 1
                    continue 
                
                break

            except Exception as e:
                step_record["status"] = "error"
                step_record["error"] = str(e)
                session_log["steps"].append(step_record)
                print(f"Error: {e}")
                # Return whatever we have instead of crashing the whole API
                return {"status": "Error in processing", "detail": str(e), "partial_logs": session_log}

        await browser.close()
        
    QUIZ_LOGS.append(session_log)
    return final_result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
