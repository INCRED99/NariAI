import logging
from datetime import datetime
from backend.services import gemini_service
from backend.database import get_user_profiles_col

logger = logging.getLogger("nari.agent")

def run_safety_agent(history, user_message, safe_word="Blue Moon", api_key=None, user_id="priya_sharma"):
    """
    Process conversation history and classifies the active safety state.
    Returns:
        state: "Normal" | "Warning" | "Emergency"
        reply: string (AI assistant reply)
        next_action: string (Suggested immediate action, if high risk)
    """
    # 1. First check if user message matches the designated safe word (immediate override)
    cleaned_msg = user_message.strip().lower()
    cleaned_safe_word = safe_word.strip().lower()
    
    # Check both direct match and contains match (e.g. user slips safe word in a sentence)
    is_safe_word_triggered = (cleaned_msg == cleaned_safe_word) or (len(cleaned_safe_word) > 3 and cleaned_safe_word in cleaned_msg)
    
    # 2. Extract recent transcript formatting for LLM analysis
    transcript = []
    for msg in history[-4:]:
        transcript.append({"role": msg["role"], "content": msg["content"]})
    transcript.append({"role": "user", "content": user_message})

    # 3. Assess risk classification
    if is_safe_word_triggered:
        logger.info("🚨 SOS Agent: Safe Word Triggered!")
        risk_evaluation = {
            "is_emergency": True,
            "next_best_action": f"🚨 SAFE WORD '{safe_word}' DETECTED! Activating immediate location broadcast & trust circle dispatch."
        }
        state = "Emergency"
    else:
        # Evaluate conversation via Gemini risk parser
        risk_evaluation = gemini_service.analyze_conversation_risk(transcript, api_key)
        
        # Check if emergency is detected
        if risk_evaluation.get("is_emergency", False):
            state = "Emergency"
        else:
            # Check for lower level warnings (e.g. keywords about dark, following but not acute panic)
            text_lower = user_message.lower()
            warning_keywords = ["dark", "flicker", "broken", "deserted", "unlit", "isolated", "stranger"]
            if any(w in text_lower for w in warning_keywords):
                state = "Warning"
            else:
                state = "Normal"

    # 4. Extract action
    next_action = risk_evaluation.get("next_best_action", "")
    
    # 5. Fetch RAG content and LTM memories to build the customized reply
    # Build a simple query to fetch context from RAG based on the user's message
    from backend.services.qdrant_service import search_safety_kb
    from backend.services.memory_service import get_memories_as_text
    
    rag_matches = search_safety_kb(user_message, limit=2, api_key=api_key)
    rag_context = "\n\n".join([f"Source ({m['category']}): {m['title']}\n{m['text']}" for m in rag_matches])
    
    memory_context = get_memories_as_text(user_id)
    # Generate chat reply grounded in context
    reply = gemini_service.chat_completion(
        history=history,
        user_message=user_message,
        memory_context=memory_context,
        rag_context=rag_context,
        language="English (US)", # Will be updated dynamically in routes based on user profile
        api_key=api_key
    )
    
    # Intercept PERFORM_SOS_TASK keyword trigger
    is_sos_triggered = False
    if "PERFORM_SOS_TASK" in reply:
        is_sos_triggered = True
        state = "Emergency"
        reply = reply.replace("PERFORM_SOS_TASK", "").strip()
        next_action = "🚨 Emergency safety conversation escalated! Alerts sent to emergency contacts."
    
    # Override reply if safe word was triggered
    if is_safe_word_triggered:
        reply = f"🚨 EMERGENCY STATE ACTIVATED. Safe word '{safe_word}' detected. Directing user to immediate safety centers and alerting contacts."
        state = "Emergency"
        next_action = "🚨 Safe word triggered. Alerting contacts."

    threat_score = risk_evaluation.get("threat_score", 0)
    if state == "Emergency" or is_safe_word_triggered or is_sos_triggered:
        threat_score = 100

    is_emergency = is_safe_word_triggered or is_sos_triggered

    return {
        "state": state,
        "reply": reply,
        "next_action": next_action,
        "is_emergency": is_emergency,
        "threat_score": threat_score
    }

def compute_threat_score(history, user_message):
    # Combine history and current message
    all_msgs = []
    for m in history:
        all_msgs.append(m)
    all_msgs.append({"role": "user", "content": user_message})
    
    score = 0
    # Analyze pairs of Assistant questions and User responses
    for i in range(len(all_msgs) - 1):
        ast = all_msgs[i]
        usr = all_msgs[i+1]
        if ast["role"] == "assistant" and usr["role"] == "user":
            ast_content = ast["content"].lower()
            usr_content = usr["content"].lower()
            
            # Question 1: alone
            if "alone" in ast_content:
                if any(w in usr_content for w in ["yes", "yeah", "alone", "am alone", "i am"]):
                    score += 20
                elif "no" in usr_content:
                    score += 5
                    
            # Question 2: following
            if "following" in ast_content or "follow" in ast_content:
                if any(w in usr_content for w in ["yes", "yeah", "following", "behind", "someone"]):
                    score += 20
                elif "no" in usr_content:
                    score += 5
                    
            # Question 3: know them
            if "know them" in ast_content or "know him" in ast_content:
                if any(w in usr_content for w in ["no", "don't", "stranger", "never seen"]):
                    score += 20
                elif "yes" in usr_content:
                    score += 10
                    
            # Question 4: safely talk
            if "safely talk" in ast_content or "can you talk" in ast_content:
                if any(w in usr_content for w in ["no", "cannot", "hard", "not safely"]):
                    score += 20
                elif "yes" in usr_content:
                    score += 5
                    
            # Question 5: need police
            if "need police" in ast_content or "call police" in ast_content or "officer" in ast_content:
                if any(w in usr_content for w in ["yes", "yeah", "please", "help"]):
                    score += 20
                elif "no" in usr_content:
                    score += 5
                    
    # Analyze distress keywords in user's latest message
    latest_lower = user_message.lower()
    distress_triggers = ["unsafe", "help", "emergency", "danger", "scared", "stalker", "threat", "panic"]
    if any(w in latest_lower for w in distress_triggers):
        score = max(score, 15)  # Base threat score of 15 if distress indicators are found
        
    return min(score, 100)
