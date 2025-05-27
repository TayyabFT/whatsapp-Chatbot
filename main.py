from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

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

# Load API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is missing from .env file")

class ChatRequest(BaseModel):
    role: str
    question: str

@app.post("/chat")
async def chat_with_bot(request: ChatRequest):
    """
    Get a response from JapaMate Bot based on user role and question
    """
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
                "HTTP-Referer": "https://yourdomain.com",  # Update this
                "X-Title": "JapaMate Bot API",  # Update this
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }),
            timeout=30
        )
        
        response.raise_for_status()
        return {
            "response": response.json()["choices"][0]["message"]["content"],
            "status": "success"
        }
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")
    except (KeyError, IndexError) as e:
        raise HTTPException(status_code=500, detail="Failed to process API response")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}