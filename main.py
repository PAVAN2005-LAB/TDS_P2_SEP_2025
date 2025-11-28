from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from agent import run_agent
import uvicorn
import os
import time

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL")
SECRET = os.getenv("SECRET")

# In-memory log storage
QUIZ_LOGS = []
TASK_ID = 0

# App setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

# ------------------------------------------------------
# ROOT ENDPOINT
# ------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def homepage():
    return """
    <h2>TDSP2 Backend Running</h2>
    <p>Available endpoints:</p>
    <ul>
        <li><b>GET /healthz</b> - health check</li>
        <li><b>POST /quiz</b> - submit a task</li>
        <li><b>GET /history</b> - view log history</li>
    </ul>
    """

# ------------------------------------------------------
# HEALTH ENDPOINT
# ------------------------------------------------------
@app.get("/healthz")
def health():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME)
    }

# ------------------------------------------------------
# BACKGROUND TASK WITH LOGGING
# ------------------------------------------------------
def run_agent_with_logging(url, log_entry):
    try:
        result = run_agent(url)  # RUN YOUR AGENT
        log_entry["status"] = "completed"
        log_entry["completed_at"] = time.time()
        log_entry["result"] = result
    except Exception as e:
        log_entry["status"] = "failed"
        log_entry["completed_at"] = time.time()
        log_entry["result"] = str(e)

# ------------------------------------------------------
# SOLVE ENDPOINT
# ------------------------------------------------------
@app.post("/quiz")
async def solve(request: Request, background_tasks: BackgroundTasks):
    global TASK_ID

    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    url = data.get("url")
    secret = data.get("secret")

    if not url or not secret:
        raise HTTPException(status_code=400, detail="Missing url or secret")

    if secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Create log entry
    TASK_ID += 1
    log_entry = {
        "id": TASK_ID,
        "url": url,
        "submitted_at": time.time(),
        "completed_at": None,
        "status": "queued",
        "result": None
    }
    QUIZ_LOGS.append(log_entry)

    # Assign background task
    background_tasks.add_task(run_agent_with_logging, url, log_entry)

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "task_id": TASK_ID}
    )

# ------------------------------------------------------
# HISTORY ENDPOINT
# ------------------------------------------------------
@app.get("/history")
def history():
    def fmt(t):
        return None if t is None else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))

    readable_logs = []
    for log in QUIZ_LOGS:
        readable_logs.append({
            "id": log["id"],
            "url": log["url"],
            "submitted_at": fmt(log["submitted_at"]),
            "completed_at": fmt(log["completed_at"]),
            "status": log["status"],
            "result": log["result"],
        })

    return {"count": len(readable_logs), "logs": readable_logs}

# ------------------------------------------------------
# DEV MODE
# ------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
