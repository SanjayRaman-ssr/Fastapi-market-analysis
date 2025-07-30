from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from starlette.responses import PlainTextResponse
from dotenv import load_dotenv
import os
import google.generativeai as genai

import webbrowser
import threading
import uvicorn

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8000/docs")

if __name__== "_main_":
    threading.Timer(1.5, open_browser).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000,reload=True)
# Load env variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
USERNAME = "admin"
PASSWORD = "admin123"

# Setup Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-pro-latest")

# FastAPI App
app = FastAPI()

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Basic Auth
security = HTTPBasic()

def validate_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != USERNAME or credentials.password != PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials.username

# Fetch mock data
async def fetch_sector_data(sector: str) -> str:
    return f"Latest news and reports about Indian {sector} sector from trusted sources."

# Analyze with Gemini
def analyze_sector_with_ai(data: str, sector: str) -> dict:
    try:
        prompt = f"""Analyze the current market data for the {sector} sector in India and generate a structured markdown report.

Data: {data}
"""
        response = model.generate_content([prompt])

        if not response or not hasattr(response, "text"):
            return {
                "sector": sector,
                "report": f"Error: Gemini response missing 'text'. Full response: {response}"
            }

        return {
            "sector": sector,
            "report": response.text
        }
    except Exception as e:
        return {
            "sector": sector,
            "report": f"Error: {e}"
        }

# API Endpoint
@app.get("/analyze/{sector}")
@limiter.limit("5/minute")
def analyze_sector(request: Request, sector: str, username: str = Depends(validate_credentials)):
    try:
        raw_data = fetch_sector_data(sector)
        report = analyze_sector_with_ai(raw_data, sector)

        if not isinstance(report, dict):
            raise HTTPException(status_code=500, detail="Invalid AI response format.")

        return {"sector": sector, "report": report["report"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")