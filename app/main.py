import time
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from solver import solve_quiz

SECRET = os.getenv("SECRET")       # from HF secrets
LLM_KEY = os.getenv("LLM_KEY")     # if needed

app = FastAPI()

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.post("/solve")
async def solve_endpoint(payload: QuizRequest):
    if payload.secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    start_time = time.time()

    result = await solve_quiz(
        email=payload.email,
        secret=payload.secret,
        url=payload.url,
        deadline=start_time + 180
    )

    return {"ok": True, "result": result}
