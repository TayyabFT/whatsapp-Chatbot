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
    """Get a response from JapaMate Bot"""
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    prompt = f"""
    You are a helpful assistant named JapaMate Bot that supports users based on their role.
    
    User Role: {request.role}
    Question: {request.question}
    
    Answer helpfully and kindly based on the role.
    """
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://japamate-bot.vercel.app",
                "X-Title": "JapaMate Bot API",
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": prompt}]
            }),
            timeout=30
        )
        response.raise_for_status()
        return {
            "response": response.json()["choices"][0]["message"]["content"],
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def health_check():
    return {"status": "healthy"}