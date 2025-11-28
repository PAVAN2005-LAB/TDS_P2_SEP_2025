from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
# NOTE: This assumes a synchronous function 'run_agent' exists in agent.py
from agent import run_agent 
import uvicorn
import os
import time
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
# NOTE: This assumes a synchronous function 'run_agent' exists in agent.py
from agent import run_agent 
import uvicorn
import os
import time

# ------------------------------------------------------
# ⚙️ CONFIGURATION & SETUP
# ------------------------------------------------------

# Load environment variables (e.g., EMAIL, SECRET)
load_dotenv()
EMAIL = os.getenv("EMAIL")
SECRET = os.getenv("SECRET")

# In-memory log storage for storing task metadata and the full trace log
QUIZ_LOGS = []
TASK_ID = 0

# Initialize the FastAPI application
app = FastAPI(
    title="Autonomous Quiz Agent Backend", 
    description="Manages asynchronous execution and logging of the LangGraph quiz solver."
)

# CORS Middleware setup to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

# Helper function to format timestamps for display
def fmt_time(t):
    return "N/A" if t is None else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))

# ------------------------------------------------------
# 🔗 ROOT ENDPOINT
# ------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def homepage():
    """Provides basic information and links to key endpoints."""
    # NOTE: CSS braces are escaped here too, just in case, though this function 
    # uses f-string formatting which is generally safer than .format()
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent Backend</title>
        <style>
            body {{ font-family: sans-serif; margin: 2rem; background-color: #f4f4f9; }}
            h2 {{ color: #333; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ margin-bottom: 0.5rem; }}
            a {{ color: #007bff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .secret-note {{ color: #d9534f; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>Autonomous Quiz Agent Backend Running</h2>
        <p>Available endpoints:</p>
        <ul>
            <li><b><a href="/healthz">GET /healthz</a></b> - health check</li>
            <li><b>POST /quiz</b> - submit a task (requires JSON body with "url" and "secret")</li>
            <li><b><a href="/history">GET /history</a></b> - view overall log history (List View)</li>
            <li><b>GET /task/{{task_id}}</b> - view detailed trace for a single task (Detail View)</li>
        </ul>
        <p class="secret-note">Current System Secret: **{SECRET}**</p>
    </body>
    </html>
    """

# ------------------------------------------------------
# 🩺 HEALTH ENDPOINT
# ------------------------------------------------------
@app.get("/healthz")
def health():
    """Standard health check endpoint."""
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME)
    }

# ------------------------------------------------------
# 🏃 BACKGROUND TASK WITH LOGGING
# ------------------------------------------------------
def run_agent_with_logging(url, log_entry):
    """
    Executes the synchronous agent in a background thread and captures the full trace.
    """
    log_entry["status"] = "running"
    try:
        # Blocking call to the synchronous agent
        trace_log = run_agent(url) 
        log_entry["status"] = "completed"
        log_entry["completed_at"] = time.time()
        # Store the full execution log returned by the agent
        log_entry["trace_log"] = trace_log 
    except Exception as e:
        log_entry["status"] = "failed"
        log_entry["completed_at"] = time.time()
        log_entry["trace_log"] = f"Agent execution failed: {str(e)}"

# ------------------------------------------------------
# 🎯 SOLVE ENDPOINT (Task Submission)
# ------------------------------------------------------
@app.post("/quiz")
async def solve(request: Request, background_tasks: BackgroundTasks):
    """
    Accepts a quiz URL, validates the secret, and queues the agent execution.
    """
    global TASK_ID

    # Input parsing and validation
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
        "trace_log": "Task queued. Waiting for execution..."
    }
    QUIZ_LOGS.append(log_entry)

    # Offload the blocking agent execution to a background thread
    background_tasks.add_task(run_agent_with_logging, url, log_entry)

    # Return an immediate 200 response
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "task_id": TASK_ID, "message": f"Task {TASK_ID} submitted. Check /task/{TASK_ID} for trace."}
    )

# ------------------------------------------------------
# 📝 HISTORY ENDPOINT (List View)
# ------------------------------------------------------
@app.get("/history", response_class=HTMLResponse)
def history_list():
    """
    Generates an HTML list view of all tasks submitted.
    """
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent Execution History</title>
        <style>
            /* ESCAPE CURLY BRACES IN CSS HERE */
            body {{ font-family: sans-serif; margin: 2rem; background-color: #f4f4f9; }}
            h1 {{ color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); background-color: white; }}
            th, td {{ padding: 12px 15px; text-align: left; border: 1px solid #ddd; }}
            th {{ background-color: #007bff; color: white; text-transform: uppercase; }}
            tr:hover {{ background-color: #e6f7ff; cursor: pointer; }}
            .status-completed {{ color: green; font-weight: bold; }}
            .status-failed {{ color: red; font-weight: bold; }}
            .status-running, .status-queued {{ color: orange; }}
            a {{ text-decoration: none; color: inherit; }}
        </style>
    </head>
    <body>
        <h1>Agent Execution History</h1>
        <p><a href="/">← Back to Home</a> | Total Tasks: {count}</p>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Status</th>
                    <th>URL</th>
                    <th>Submitted At</th>
                    <th>Completed At</th>
                    <th>View Trace</th>
                </tr>
            </thead>
            <tbody>
    """.format(count=len(QUIZ_LOGS)) # Error fix was on this line's argument and the CSS above

    for log in QUIZ_LOGS:
        status_class = f"status-{log['status'].lower()}"
        # Direct link to the detail view
        html_content += f"""
                <tr>
                    <td>{log["id"]}</td>
                    <td class="{status_class}">{log["status"].upper()}</td>
                    <td>{log["url"]}</td>
                    <td>{fmt_time(log["submitted_at"])}</td>
                    <td>{fmt_time(log["completed_at"])}</td>
                    <td><a href="/task/{log["id"]}">View Trace</a></td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------------------------------------
# 🔎 TASK DETAIL ENDPOINT (site_task)
# ------------------------------------------------------
@app.get("/task/{task_id}", response_class=HTMLResponse)
def site_task(task_id: int):
    """
    Dedicated function to display the detailed execution trace for a single task ID.
    """

    # Search for the specific log entry
    log = next((l for l in QUIZ_LOGS if l["id"] == task_id), None)
    
    if log is None:
        raise HTTPException(status_code=404, detail=f"Task ID {task_id} not found.")

    status_class = f"status-{log['status'].lower()}"
    
    # Escape HTML entities for safe rendering and use pre-wrap for line breaks
    trace_display = log.get('trace_log', 'No trace log available.').replace('<', '&lt;').replace('>', '&gt;')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Task {task_id} Trace</title>
        <style>
            /* ESCAPE CURLY BRACES IN CSS HERE */
            body {{ font-family: sans-serif; margin: 2rem; background-color: #f4f4f9; }}
            h1 {{ color: #333; }}
            .metadata {{ background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .metadata p {{ margin: 5px 0; }}
            .status-completed {{ color: green; font-weight: bold; }}
            .status-failed {{ color: red; font-weight: bold; }}
            .status-running, .status-queued {{ color: orange; }}
            .trace-box {{ background-color: #272822; color: #f8f8f2; padding: 15px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; font-family: monospace; font-size: 0.9em; line-height: 1.4; }}
            a {{ color: #007bff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>Execution Trace for Task #{task_id}</h1>
        <p><a href="/history">← Back to History List</a> | <a href="/">Back to Home</a></p>
        
        <div class="metadata">
            <p><strong>Status:</strong> <span class="{status_class}">{log["status"].upper()}</span></p>
            <p><strong>Start URL:</strong> <a href="{log["url"]}" target="_blank">{log["url"]}</a></p>
            <p><strong>Submitted At:</strong> {fmt_time(log["submitted_at"])}</p>
            <p><strong>Completed At:</strong> {fmt_time(log["completed_at"])}</p>
        </div>

        <h2>Detailed Execution Log</h2>
        <div class="trace-box">
            {trace_display}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------------------------------------
# 🖥️ DEV MODE EXECUTION
# ------------------------------------------------------
if __name__ == "__main__":
    # Standard Uvicorn execution command
    uvicorn.run(app, host="0.0.0.0", port=7860)
# ------------------------------------------------------
# ⚙️ CONFIGURATION & SETUP
# ------------------------------------------------------

# Load environment variables (e.g., EMAIL, SECRET)
load_dotenv()
EMAIL = os.getenv("EMAIL")
SECRET = os.getenv("SECRET")

# In-memory log storage for storing task metadata and the full trace log
QUIZ_LOGS = []
TASK_ID = 0

# Initialize the FastAPI application
app = FastAPI(
    title="Autonomous Quiz Agent Backend", 
    description="Manages asynchronous execution and logging of the LangGraph quiz solver."
)

# CORS Middleware setup to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

# Helper function to format timestamps for display
def fmt_time(t):
    return "N/A" if t is None else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))

# ------------------------------------------------------
# 🔗 ROOT ENDPOINT
# ------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def homepage():
    """Provides basic information and links to key endpoints."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent Backend</title>
        <style>
            body {{ font-family: sans-serif; margin: 2rem; background-color: #f4f4f9; }}
            h2 {{ color: #333; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ margin-bottom: 0.5rem; }}
            a {{ color: #007bff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .secret-note {{ color: #d9534f; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>Autonomous Quiz Agent Backend Running</h2>
        <p>Available endpoints:</p>
        <ul>
            <li><b><a href="/healthz">GET /healthz</a></b> - health check</li>
            <li><b>POST /quiz</b> - submit a task (requires JSON body with "url" and "secret")</li>
            <li><b><a href="/history">GET /history</a></b> - view overall log history (List View)</li>
            <li><b>GET /task/{{task_id}}</b> - view detailed trace for a single task (Detail View)</li>
        </ul>
        <p class="secret-note">Current System Secret: **{SECRET}**</p>
    </body>
    </html>
    """

# ------------------------------------------------------
# 🩺 HEALTH ENDPOINT
# ------------------------------------------------------
@app.get("/healthz")
def health():
    """Standard health check endpoint."""
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME)
    }

# ------------------------------------------------------
# 🏃 BACKGROUND TASK WITH LOGGING
# ------------------------------------------------------
def run_agent_with_logging(url, log_entry):
    """
    Executes the synchronous agent in a background thread and captures the full trace.
    """
    log_entry["status"] = "running"
    try:
        # Blocking call to the synchronous agent
        trace_log = run_agent(url) 
        log_entry["status"] = "completed"
        log_entry["completed_at"] = time.time()
        # Store the full execution log returned by the agent
        log_entry["trace_log"] = trace_log 
    except Exception as e:
        log_entry["status"] = "failed"
        log_entry["completed_at"] = time.time()
        log_entry["trace_log"] = f"Agent execution failed: {str(e)}"

# ------------------------------------------------------
# 🎯 SOLVE ENDPOINT (Task Submission)
# ------------------------------------------------------
@app.post("/quiz")
async def solve(request: Request, background_tasks: BackgroundTasks):
    """
    Accepts a quiz URL, validates the secret, and queues the agent execution.
    """
    global TASK_ID

    # Input parsing and validation
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
        "trace_log": "Task queued. Waiting for execution..."
    }
    QUIZ_LOGS.append(log_entry)

    # Offload the blocking agent execution to a background thread
    background_tasks.add_task(run_agent_with_logging, url, log_entry)

    # Return an immediate 200 response
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "task_id": TASK_ID, "message": f"Task {TASK_ID} submitted. Check /task/{TASK_ID} for trace."}
    )

# ------------------------------------------------------
# 📝 HISTORY ENDPOINT (List View)
# ------------------------------------------------------
@app.get("/history", response_class=HTMLResponse)
def history_list():
    """
    Generates an HTML list view of all tasks submitted.
    """
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agent Execution History</title>
        <style>
            body { font-family: sans-serif; margin: 2rem; background-color: #f4f4f9; }
            h1 { color: #333; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); background-color: white; }
            th, td { padding: 12px 15px; text-align: left; border: 1px solid #ddd; }
            th { background-color: #007bff; color: white; text-transform: uppercase; }
            tr:hover { background-color: #e6f7ff; cursor: pointer; }
            .status-completed { color: green; font-weight: bold; }
            .status-failed { color: red; font-weight: bold; }
            .status-running, .status-queued { color: orange; }
            a { text-decoration: none; color: inherit; }
        </style>
    </head>
    <body>
        <h1>Agent Execution History</h1>
        <p><a href="/">← Back to Home</a> | Total Tasks: {count}</p>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Status</th>
                    <th>URL</th>
                    <th>Submitted At</th>
                    <th>Completed At</th>
                    <th>View Trace</th>
                </tr>
            </thead>
            <tbody>
    """.format(count=len(QUIZ_LOGS))

    for log in QUIZ_LOGS:
        status_class = f"status-{log['status'].lower()}"
        # Direct link to the detail view
        html_content += f"""
                <tr>
                    <td>{log["id"]}</td>
                    <td class="{status_class}">{log["status"].upper()}</td>
                    <td>{log["url"]}</td>
                    <td>{fmt_time(log["submitted_at"])}</td>
                    <td>{fmt_time(log["completed_at"])}</td>
                    <td><a href="/task/{log["id"]}">View Trace</a></td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------------------------------------
# 🔎 TASK DETAIL ENDPOINT (site_task)
# ------------------------------------------------------
@app.get("/task/{task_id}", response_class=HTMLResponse)
def site_task(task_id: int):
    """
    Dedicated function to display the detailed execution trace for a single task ID.
    """

    # Search for the specific log entry
    log = next((l for l in QUIZ_LOGS if l["id"] == task_id), None)
    
    if log is None:
        raise HTTPException(status_code=404, detail=f"Task ID {task_id} not found.")

    status_class = f"status-{log['status'].lower()}"
    
    # Escape HTML entities for safe rendering and use pre-wrap for line breaks
    trace_display = log.get('trace_log', 'No trace log available.').replace('<', '&lt;').replace('>', '&gt;')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Task {task_id} Trace</title>
        <style>
            body {{ font-family: sans-serif; margin: 2rem; background-color: #f4f4f9; }}
            h1 {{ color: #333; }}
            .metadata {{ background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .metadata p {{ margin: 5px 0; }}
            .status-completed {{ color: green; font-weight: bold; }}
            .status-failed {{ color: red; font-weight: bold; }}
            .status-running, .status-queued {{ color: orange; }}
            .trace-box {{ background-color: #272822; color: #f8f8f2; padding: 15px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; font-family: monospace; font-size: 0.9em; line-height: 1.4; }}
            a {{ color: #007bff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>Execution Trace for Task #{task_id}</h1>
        <p><a href="/history">← Back to History List</a> | <a href="/">Back to Home</a></p>
        
        <div class="metadata">
            <p><strong>Status:</strong> <span class="{status_class}">{log["status"].upper()}</span></p>
            <p><strong>Start URL:</strong> <a href="{log["url"]}" target="_blank">{log["url"]}</a></p>
            <p><strong>Submitted At:</strong> {fmt_time(log["submitted_at"])}</p>
            <p><strong>Completed At:</strong> {fmt_time(log["completed_at"])}</p>
        </div>

        <h2>Detailed Execution Log</h2>
        <div class="trace-box">
            {trace_display}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------------------------------------
# 🖥️ DEV MODE EXECUTION
# ------------------------------------------------------
if __name__ == "__main__":
    # Standard Uvicorn execution command
    uvicorn.run(app, host="0.0.0.0", port=7860)
