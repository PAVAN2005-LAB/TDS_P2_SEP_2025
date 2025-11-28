from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
# Import the synchronous agent execution function
from agent import run_agent 
import uvicorn
import os
import time

# ------------------------------------------------------
# ⚙️ CONFIGURATION & SETUP
# ------------------------------------------------------

# Load environment variables from .env file
load_dotenv()
EMAIL = os.getenv("EMAIL")
SECRET = os.getenv("SECRET")

# In-memory log storage for simplicity. In production, this would be 
# replaced by a persistent database (e.g., PostgreSQL, MongoDB, Redis).
QUIZ_LOGS = []
TASK_ID = 0 # Simple counter for unique task IDs

# App setup: Initialize the FastAPI application
app = FastAPI(
    title="Autonomous Quiz Agent Backend", 
    description="Manages asynchronous execution and logging of the LangGraph quiz solver."
)

# Middleware setup
# Why CORS is needed: Allows a frontend client running on a different origin 
# (e.g., a local development server) to make requests to this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins (can be restricted in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Record application start time for uptime tracking
START_TIME = time.time()

# ------------------------------------------------------
# 🔗 ROOT ENDPOINT
# ------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def homepage():
    """Provides basic information and available endpoints."""
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
# 🩺 HEALTH ENDPOINT
# ------------------------------------------------------
@app.get("/healthz")
def health():
    """Standard health check endpoint to monitor application status and uptime."""
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME)
    }

# ------------------------------------------------------
# 🏃 BACKGROUND TASK EXECUTION LOGIC
# ------------------------------------------------------
def run_agent_with_logging(url, log_entry):
    """
    Executes the synchronous LangGraph agent function and updates the log entry
    with the final status and result.

    Why a background task?
    The `run_agent(url)` call is synchronous and blocking. If we ran it directly 
    in the `/quiz` endpoint handler, the server would be blocked for the 
    entire duration of the quiz (potentially several minutes). 
    `BackgroundTasks` allows the `/quiz` endpoint to immediately return a 200 
    response while the long-running agent task executes separately, keeping 
    the API responsive.
    """
    try:
        # Execute the synchronous agent, which blocks this thread until completion.
        result = run_agent(url) 
        log_entry["status"] = "completed"
        log_entry["completed_at"] = time.time()
        log_entry["result"] = result
    except Exception as e:
        # Log any exceptions that occur during the agent's execution.
        log_entry["status"] = "failed"
        log_entry["completed_at"] = time.time()
        log_entry["result"] = str(e)

# ------------------------------------------------------
# 🎯 SOLVE ENDPOINT (Task Submission)
# ------------------------------------------------------
@app.post("/quiz")
async def solve(request: Request, background_tasks: BackgroundTasks):
    """
    Accepts a quiz URL, validates the secret, queues the agent execution, 
    and immediately returns a task ID.
    """
    global TASK_ID

    # 1. Input Parsing and Validation
    try:
        # Request body must be parsed asynchronously
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    url = data.get("url")
    secret = data.get("secret")

    if not url or not secret:
        raise HTTPException(status_code=400, detail="Missing url or secret")

    # Security check: Ensure the request contains the correct SECRET
    if secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # 2. Log Entry Creation
    TASK_ID += 1
    log_entry = {
        "id": TASK_ID,
        "url": url,
        "submitted_at": time.time(),
        "completed_at": None,
        "status": "queued", # Initial status
        "result": None
    }
    QUIZ_LOGS.append(log_entry)

    # 3. Task Offloading
    # Add the agent execution function to the BackgroundTasks list.
    # FastAPI will ensure this function is called after the HTTP response is sent.
    background_tasks.add_task(run_agent_with_logging, url, log_entry)

    # 4. Immediate Response
    # Respond immediately to the client to confirm the task is accepted.
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "task_id": TASK_ID}
    )

# ------------------------------------------------------
# 📝 HISTORY ENDPOINT
# ------------------------------------------------------
@app.get("/history")
def history():
    """
    Retrieves the in-memory log of all submitted quiz tasks, formatted for readability.
    """
    # Helper function to format timestamps into readable strings
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
            # The 'result' field holds the final output or error message from the agent.
            "result": log["result"],
        })

    return {"count": len(readable_logs), "logs": readable_logs}

# ------------------------------------------------------
# 🖥️ DEV MODE EXECUTION
# ------------------------------------------------------
if __name__ == "__main__":
    # Standard entry point for running the application locally using Uvicorn.
    uvicorn.run(app, host="0.0.0.0", port=7860)
