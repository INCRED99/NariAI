import logging
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from backend.config import GROQ_API_KEY
from backend.database import get_user_profiles_col
from backend.services import agent_service, memory_service

logger = logging.getLogger("nari.chat")
router = APIRouter(tags=["AI Chat & State Orchestration"])

class MessageItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    history: List[MessageItem]
    user_message: str
    user_id: Optional[str] = "priya_sharma"

class ChatResponse(BaseModel):
    reply: str
    state: str  # "Normal" | "Warning" | "Emergency"
    next_action: str
    is_emergency: bool
    threat_score: Optional[int] = 0

from backend.services.auth_helper import get_current_user_uid

@router.post("/conversation-risk", response_model=ChatResponse)
@router.post("/chat", response_model=ChatResponse)
def handle_chat_message(
    request: ChatRequest,
    authorization: Optional[str] = Header(None),
    x_gemini_key: Optional[str] = Header(None),
    x_groq_key: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """Analyze conversation history and reply using RAG context, LTM, and Safety agent state classifiers."""
    try:
        # 1. Retrieve user's UID (fall back to request.user_id / priya_sharma if unauthenticated)
        uid = request.user_id or "priya_sharma"
        if authorization and isinstance(authorization, str):
            try:
                uid = get_current_user_uid(authorization)
            except Exception:
                pass

        api_key = next((k for k in [x_groq_key, x_api_key, x_gemini_key] if isinstance(k, str) and k.startswith("gsk_")), None) or GROQ_API_KEY

        profiles_col = get_user_profiles_col()
        user_profile = profiles_col.find_one({"uid": uid}) if profiles_col is not None else None
        
        safe_word = "Blue Moon"
        preferred_lang = "English (US)"
        
        if user_profile:
            safe_word = user_profile.get("safe_word", "Blue Moon")
            preferred_lang = user_profile.get("preferred_language", "English (US)")
            
        # 2. Format history for agent service processing
        history_formatted = [{"role": m.role, "content": m.content} for m in request.history]
        
        # 3. Process message through state machine agent
        agent_result = agent_service.run_safety_agent(
            history=history_formatted,
            user_message=request.user_message,
            safe_word=safe_word,
            api_key=api_key,
            user_id=uid
        )
        
        # 4. Asynchronously extract and commit new LTM facts if situation is Normal/Warning
        if agent_result["state"] != "Emergency":
            try:
                memory_service.process_and_extract_memory(
                    user_message=request.user_message,
                    user_id=uid,
                    api_key=api_key
                )
            except Exception as ex:
                logger.error(f"LTM background memory extraction failed: {ex}")
                
        return ChatResponse(
            reply=agent_result["reply"],
            state=agent_result["state"],
            next_action=agent_result["next_action"],
            is_emergency=agent_result["is_emergency"],
            threat_score=agent_result.get("threat_score", 0)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat route processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
