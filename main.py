# ===== IMPORTS =====
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from openai import OpenAI
from fuzzywuzzy import fuzz
from typing import Optional, Dict
import os
import logging

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO, filename="chatbot.log", 
                   format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize clients
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0,  # Recommended timeout
    max_retries=3  # Recommended retries
)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# CORE PERSONA CONFIGURATION
# ======================

PERSONAS = {
    "jayjay": {
        "name": "Jayjay",
        "greeting": "Hello! I'm Jayjay - your career and migration guide.",
        "prompt": """You are Josiah Jackson-Okesola's AI twin. Respond as a:
        - UK mental health nurse with 25+ years experience
        - Digital innovator specializing in NHS careers
        - Big brother mentor tone (warm but direct)
        Always provide:
        1. Empathy first
        2. Actionable steps
        3. Motivational closure""",
        "fallback": "Let's strategize your next move. Where shall we begin?"
    },
    "queen": {
        "name": "Queen",
        "greeting": "Hello dear one. I'm Queen - here to nurture your spirit.",
        "prompt": """You are Queen Okesola's AI twin. Respond as a:
        - Spiritual guide and caregiver mentor
        - Gentle but powerful elder sister tone
        - Focused on emotional healing
        Always provide:
        1. Emotional validation
        2. Healing metaphor
        3. Affirmation/prayer""",
        "fallback": "Take a deep breath. You're safe here. How can I support you?"
    }
}

RESPONSE_TEMPLATES = {
    "queen": {
        "self_care": """Caregivers like us forget: You cannot pour from a soul on E.
Schedule your soul into your calendar. Yes, literally.
Run the bath. Step outside. Journal your joy.
And here's your affirmation for today:
"I am allowed to care for myself without guilt."
Say it three times. Let it sit in your bones. Then choose you - even for 15 minutes.""",
        "faith": """My love... faith isn't about having all the answers, but trusting in the midst of questions. 
When I've walked through valleys, I held onto this: 
"The same God who brought you this far won't abandon you now."
Would you like me to share a prayer with you today?"""
    },
    "jayjay": {
        "career": """I hear you. Career transitions can feel like a maze - especially from outside. 
Let's build your map:
1. Skill Audit (what you already have)
2. Gap Analysis (what's needed)
3. Pivot Plan (3 achievable steps)
Ready to begin?""",
        "tech": """Too late? That's a myth designed to scare dreamers. 
I started learning AI in my 40s with just WiFi and willingness. 
Tech rewards practice, not pedigree. 
What problem would you love to solve? We'll find tools together."""
    }
}

# ======================
# CONVERSATION ENGINE
# ======================

sessions: Dict[str, Dict] = {}

def get_session(user_id: str) -> Dict:
    if user_id not in sessions:
        sessions[user_id] = {
            "persona": None,
            "state": "start",
            "context": []
        }
    return sessions[user_id]

def detect_intent(text: str) -> str:
    text = text.lower()
    
    # Queen's domain
    if (fuzz.partial_ratio("faith", text) > 80 or 
        fuzz.partial_ratio("pray", text) > 80 or
        fuzz.partial_ratio("care for myself", text) > 75 or
        any(w in text for w in ["emotional", "tired", "exhausted", "overwhelmed"])):
        return "queen"
        
    # Jayjay's domain
    if (fuzz.partial_ratio("career", text) > 80 or
        fuzz.partial_ratio("nhs", text) > 85 or
        fuzz.partial_ratio("tech", text) > 80 or
        any(w in text for w in ["job", "work", "ai", "money"])):
        return "jayjay"
    
    return "jayjay"  # Default

def generate_response(text: str, persona: str, context: list) -> str:
    # Check for exact template matches first
    if persona == "queen":
        if fuzz.partial_ratio("care for myself", text) > 75:
            return RESPONSE_TEMPLATES["queen"]["self_care"]
        if fuzz.partial_ratio("faith", text) > 80:
            return RESPONSE_TEMPLATES["queen"]["faith"]
    
    if persona == "jayjay":
        if fuzz.partial_ratio("career", text) > 80:
            return RESPONSE_TEMPLATES["jayjay"]["career"]
        if fuzz.partial_ratio("tech", text) > 80:
            return RESPONSE_TEMPLATES["jayjay"]["tech"]
    
    # Fallback to AI with strict prompting
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": PERSONAS[persona]["prompt"]},
                *context,
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return PERSONAS[persona]["fallback"]

# ======================
# CAMPAIGN DETECTION
# ======================

CAMPAIGN_TRIGGERS = {
    "test_campaign": ["test drive", "try campaign", "demo mode", "campaign test"],
    "feedback": ["give feedback", "share thoughts", "how did i do"]
}

def detect_campaign(text: str) -> Optional[str]:
    text = text.lower()
    for campaign, triggers in CAMPAIGN_TRIGGERS.items():
        if any(trigger in text for trigger in triggers):
            return campaign
    return None

# ======================
# TWILIO WEBHOOK
# ======================

@app.post("/twilio-web")
async def twilio_webhook(request: Request):
    try:
        form_data = await request.form()
        from_number = form_data.get('From')
        body = form_data.get('Body', '').strip()
        
        # Check for campaigns first
        campaign = detect_campaign(body)
        if campaign == "test_campaign":
            twiml = MessagingResponse()
            twiml.message("""🚀 Launching Test Campaign!
You'll receive:
1. Sample career questions (Jayjay)
2. Emotional support scenarios (Queen)
3. Feedback request after 5 messages
Reply STOP to opt out""")
            return Response(content=str(twiml), media_type="application/xml")
        
        # Validate Twilio signature
        validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))
        signature = request.headers.get('X-TWILIO-SIGNATURE', '')
        if not validator.validate(str(request.url).split('?')[0], dict(form_data), signature):
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Process normal messages
        session = get_session(from_number)
        if not session["persona"]:
            session["persona"] = detect_intent(body)
        
        response_text = generate_response(body, session["persona"], session["context"])
        
        # Update context
        session["context"].append({"role": "user", "content": body})
        session["context"].append({"role": "assistant", "content": response_text})
        session["context"] = session["context"][-10:]  # Keep last 5 exchanges
        
        # Return response
        twiml = MessagingResponse()
        twiml.message(response_text)
        return Response(content=str(twiml), media_type="application/xml")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        twiml = MessagingResponse()
        twiml.message("Please try again later. I'm having trouble responding.")
        return Response(content=str(twiml), media_type="application/xml", status_code=500)

@app.get("/")
async def health_check():
    return {"status": "active", "personas": list(PERSONAS.keys())}
