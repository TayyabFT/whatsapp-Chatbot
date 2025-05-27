from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import json

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

@app.post("/chat")
async def chat_with_bot(request: ChatRequest):
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://whatsapp-chatbot-sigma-three.vercel.app",  # Your Vercel URL
                "X-Title": "WhatsApp ChatBot"  # Any identifiable name
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": f"Role: {request.role}\nQuestion: {request.question}"}]
            }),
            timeout=10
        )
        response.raise_for_status()  # Raise HTTP errors
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/")
async def health_check():
    return {"status": "healthy"}