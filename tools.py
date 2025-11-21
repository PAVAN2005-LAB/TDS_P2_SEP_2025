import httpx
import pandas as pd
import PyPDF2
import io

async def process_file_from_url(file_url: str):
    """Downloads and extracts text/data from PDF, CSV, or plain text URLs."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(file_url)
            content_type = response.headers.get("content-type", "").lower()
            
        # 1. Handle PDF
        if "pdf" in content_type or file_url.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(response.content))
            text = ""
            for i, page in enumerate(pdf_reader.pages):
                if i > 5: break 
                text += page.extract_text()
            return f"PDF Content: {text[:4000]}" 
            
        # 2. Handle CSV
        elif "csv" in content_type or file_url.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(response.content))
            return f"CSV Data Head:\n{df.head(20).to_markdown()}"
            
        # 3. Handle Plain Text / HTML / Code (NEW)
        else:
            # If it's not PDF/CSV, we assume it's text (like the secret code page)
            return f"Page Content:\n{response.text[:4000]}"

    except Exception as e:
        return f"Error downloading/processing file: {str(e)}"
