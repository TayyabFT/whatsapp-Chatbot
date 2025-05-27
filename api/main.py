from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import json

from dotenv import load_dotenv
load_dotenv()  # Load .env file

app = FastAPI(
    title="JapaMate Bot API",
    description="API for DeepSeek-powered chatbot with role-based responses",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    role: str
    question: str

@app.get("/debug-env")
async def debug_env():
    api_key = os.getenv("OPENROUTER_API_KEY")
    return {
        "OPENROUTER_API_KEY": "Set" if api_key else "Not set",
        "key_length": len(api_key) if api_key else 0
    }

@app.post("/chat")
async def chat_with_bot(request: ChatRequest):
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://whatsapp-chatbot-sigma-three.vercel.app",
        "X-Title": "WhatsApp ChatBot"
    }
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": f"Role: {request.role}\nQuestion: {request.question}"}]
            }),
            timeout=30  # Increased timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_detail = {
            "status_code": response.status_code,
            "detail": str(http_err),
            "response_text": response.text,
            "sent_headers": {k: v if k != "Authorization" else "Bearer [REDACTED]" for k, v in headers.items()}
        }
        raise HTTPException(status_code=500, detail=error_detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def health_check():
    return {"status": "healthy"}