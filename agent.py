
import os
import json
from urllib.parse import urljoin
from openai import OpenAI
from tools import process_file_from_url

# --- CONFIGURATION ---
api_key = os.getenv("OPENAI_API_KEY")
client = None

if api_key:
    client = OpenAI(api_key=api_key)
else:
    print("WARNING: OPENAI_API_KEY not found. Agent will fail if called.")

async def get_llm_response(html_content: str, current_url: str, email: str, secret: str):
    
    # 1. Fail Gracefully
    if not client:
        return {
            "email": email,
            "secret": secret,
            "url": current_url,
            "answer": "Server Error: OPENAI_API_KEY is missing."
        }

    # --- STEP 1: PLAN ---
    system_prompt_1 = """
    You are an automated data extraction agent. 
    Analyze the provided HTML content.
    
    YOUR TASKS:
    1. Identify the core question.
    2. LOOK FOR DATA LINKS: If the text mentions "Get code from...", "Data is at...", or provides a link for the answer, you MUST extract that link.
    3. DECIDE ACTION:
       - If there is a link (PDF, CSV, OR a relative path like '/demo-data'), set action to "download".
       - If the answer is visible directly in the text, set action to "answer".
    4. Identify the submission URL.
    Output JSON ONLY:
    {
        "action": "download" or "answer",
        "file_url": "link_to_data_or_page" (null if not downloading),
        "submit_url": "link_to_submit" (null if not found),
        "reasoning_answer": "Answer string" (null if downloading)
    }
    """
    
    # Truncate HTML to avoid token limits
    truncated_html = html_content[:15000] 
    
    try:
        response_1 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt_1},
                {"role": "user", "content": f"HTML content: {truncated_html}"}
            ],
            response_format={"type": "json_object"}
        )
        
        plan = json.loads(response_1.choices[0].message.content)
        final_answer = None
        
        # --- FIX: RESOLVE RELATIVE URLS ---
        if plan.get("file_url"):
            plan['file_url'] = urljoin(current_url, plan['file_url'])
            
        if plan.get("submit_url"):
            plan['submit_url'] = urljoin(current_url, plan['submit_url'])

        # --- STEP 2: EXECUTE ---
        if plan.get("action") == "download" and plan.get("file_url"):
            print(f"Agent downloading: {plan['file_url']}")
            file_summary = await process_file_from_url(plan['file_url'])
            
            system_prompt_2 = f"""
            You are a data analyst. 
            The user has provided a file/page content.
            Your job is to EXTRACT the specific answer requested in the context.
            
            CONTEXT: {current_url}
            
            FILE CONTENT:
            {file_summary}
            
            INSTRUCTIONS:
            - If the content is a code (e.g. "4539_SECRET"), output the code exactly.
            - If the content is a CSV, perform the calculation.
            - Do NOT output the word "result". Output the ACTUAL extracted value.
            
            Output JSON: {{"answer": "THE_EXTRACTED_VALUE_HERE"}}
            """
            
            response_2 = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt_2},
                    {"role": "user", "content": "Extract the answer."}
                ],
                response_format={"type": "json_object"}
            )
            final_answer = json.loads(response_2.choices[0].message.content).get("answer")
        else:
            final_answer = plan.get("reasoning_answer")

        # --- SAFETY FALLBACK (Fixes "Missing field answer") ---
        if final_answer is None or str(final_answer).strip() == "":
            final_answer = "Demo Submission"

        # --- STEP 3: FORMAT ---
        return {
            "email": email,
            "secret": secret,
            "url": current_url,
            "answer": final_answer,
            "submit_url_override": plan.get("submit_url") 
        }

    except Exception as e:
        print(f"LLM Error: {e}")
        # Even in error, we return a string to prevent "Missing field" errors
        return {
            "email": email,
            "secret": secret,
            "url": current_url,
            "answer": f"Error: {str(e)}"
        }
