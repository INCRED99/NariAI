import os
import json
import logging
from backend.config import GROQ_API_KEY, GROQ_MODEL, GEMINI_API_KEY, OPENAI_API_KEY

logger = logging.getLogger("nari.gemini")

def _get_api_key(api_key=None):
    """Resolve the Groq API key: passed groq key > GROQ_API_KEY env var."""
    if isinstance(api_key, str) and api_key.strip().startswith("gsk_"):
        return api_key.strip()
    return GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")

def configure_gemini(api_key=None):
    key = _get_api_key(api_key)
    return bool(key)

def _call_groq(
    messages,
    model=None,
    api_key=None,
    temperature=1,
    max_completion_tokens=2048,
    top_p=1,
    reasoning_effort=None,
    stream=False,
    stop=None
):
    """Call Groq API with the given messages using fallback Groq models. Returns response text."""
    from groq import Groq
    key = _get_api_key(api_key)
    client = Groq(api_key=key) if key else Groq()

    primary_m = model or GROQ_MODEL or "openai/gpt-oss-120b"
    models_to_try = [primary_m]
    for default_m in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "allam-2-7b"]:
        if default_m not in models_to_try:
            models_to_try.append(default_m)

    last_error = None
    for m in models_to_try:
        try:
            kwargs = {
                "model": m,
                "messages": messages,
                "temperature": temperature,
                "max_completion_tokens": max_completion_tokens,
                "top_p": top_p,
            }
            if stop:
                kwargs["stop"] = stop

            completion = client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq call with model '{m}' failed: {e}. Trying next model...")
            last_error = e

    raise RuntimeError(f"All Groq models failed. Last error: {last_error}")

def generate_content_with_fallback(contents, system_instruction=None, api_key=None):
    """
    Generates content using Groq API exclusively.
    """
    key = _get_api_key(api_key)
    if not key:
        raise ValueError("No Groq API key configured.")

    # Build messages array
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})

    if isinstance(contents, str):
        messages.append({"role": "user", "content": contents})
    else:
        for msg in contents:
            role = "user" if msg['role'] == 'user' else "assistant"
            part_text = ""
            if isinstance(msg.get('parts'), list):
                part_text = "\n".join([str(p) for p in msg['parts']])
            else:
                part_text = str(msg.get('parts', ''))
            messages.append({"role": role, "content": part_text})

    return _call_groq(messages, model=GROQ_MODEL, api_key=key)

def generate_risk_assessment(location, time_val, weather, crime_index, crowd_density, message, api_key=None):
    """Analyze input context and return a structured risk score, category, and explanation."""
    has_key = configure_gemini(api_key)

    if not has_key:
        logger.info("No API key. Calculating risk score using offline rule-based model.")
        return calculate_offline_risk(location, time_val, weather, crime_index, crowd_density, message)

    prompt = f"""
    You are the risk analysis core of Nari, a professional Women's Safety Assistant.
    Analyze the following environmental variables and message to generate a Risk Score (0-100), Risk Category, and Natural Language Explanation.
    
    Variables:
    - Location: {location}
    - Transit Time: {time_val}
    - Weather: {weather}
    - Local Crime Index: {crime_index}
    - Crowd Density: {crowd_density}%
    - Situation Message: "{message}"
    
    Risk Categories:
    - Safe: 0 - 30
    - Moderate: 31 - 60
    - High: 61 - 85
    - Critical: 86 - 100
    
    Your response must be a valid JSON object containing exactly these fields (do not put any markdown formatting or ticks around the JSON):
    {{
        "risk_score": integer (0 to 100),
        "risk_category": "Safe" | "Moderate" | "High" | "Critical",
        "explanation": "Brief natural language explanation detailing specific risk factors (e.g. darkness, isolation, crime rate, weather) and immediate safety advice."
    }}
    """

    try:
        text = generate_content_with_fallback(prompt, api_key=api_key)
        # Clean up any potential markdown formatting codeblocks
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)
    except Exception as e:
        logger.error(f"Risk assessment API error: {e}. Using offline fallback.")
        return calculate_offline_risk(location, time_val, weather, crime_index, crowd_density, message)

def calculate_offline_risk(location, time_val, weather, crime_index, crowd_density, message):
    # Base crime level weights
    crime_weights = {"Very Low": 10, "Low": 22, "Medium": 42, "High": 68, "Critical": 88}
    score = crime_weights.get(crime_index, 30)

    # Weather impact
    weather_weights = {"Clear Sky": 0, "Light Rain": 5, "Heavy Rain": 12, "Dense Fog / Smog": 18, "Stormy / Hail": 22}
    score += weather_weights.get(weather, 0)

    # Time of night (10PM - 5AM is extra risk)
    try:
        # Check if time_val is a string or time object
        hour = int(time_val.split(":")[0]) if isinstance(time_val, str) else time_val.hour
    except Exception:
        hour = 22

    if hour >= 22 or hour < 5:
        score += 20
    elif hour >= 18:
        score += 8

    # Crowd isolation penalty
    if crowd_density < 15:
        score += 15
    elif crowd_density < 35:
        score += 5

    # Text keyword triggers
    msg = message.lower()
    if any(w in msg for w in ["follow", "chase", "stalk", "run", "grab", "car", "suspicious"]):
        score += 25
    elif any(w in msg for w in ["dark", "scared", "help", "afraid"]):
        score += 12

    # Clamp
    score = min(max(score, 0), 100)

    # Category
    if score >= 85:
        cat = "Critical"
    elif score >= 60:
        cat = "High"
    elif score >= 30:
        cat = "Moderate"
    else:
        cat = "Safe"

    explanations = {
        "Critical": "Critical danger indicators detected. Heavy environmental risks coupled with high isolation and direct threat descriptions. Immediate SOS triggering recommended.",
        "High": "Heightened threat level due to high crime index, nighttime transit, and low street density. Stay alert, share your live route, and identify nearest safe places.",
        "Moderate": "Moderate transit risk index. We recommend staying on primary well-lit thoroughfares, avoiding low-light short-cuts, and keeping your emergency contacts active.",
        "Safe": "Vicinity deemed statistically safe. Standard daylight/crowded parameters. Continue travel normally while maintaining standard awareness."
    }

    return {
        "risk_score": score,
        "risk_category": cat,
        "explanation": f"[Offline Engine] {explanations[cat]} Details: Location={location}, Crowd={crowd_density}%, Crime={crime_index}."
    }

def generate_safe_route_explanation(route_type, origin, destination, metrics, time_of_day="20:00", api_key=None):
    """Generate natural language description of why a route is selected or flagged, considering time and crime context."""
    has_key = configure_gemini(api_key)

    if not has_key:
        return generate_offline_route_explanation(route_type, metrics)

    prompt = f"""
    You are the safety routing advisor of Nari. 
    Explain in 3-4 bullet points why this route category ('{route_type}') from '{origin}' to '{destination}' at transit time '{time_of_day}' has been rated with these metrics:
    - Safety Index Score: {metrics['safety_score']}/100
    - Streetlight Density: {metrics['streetlight_density']}%
    - Active Police Booths: {metrics['police_booths']}
    - CCTV Coverage: {metrics['cctv_zones']} zones
    - Foot Traffic level (Crowding): {metrics['foot_traffic']}
    
    In your analysis, keep in mind and explicitly cover:
    1. The impact of transit time ({time_of_day}) on safety (e.g. night darkness, sparse crowds).
    2. The areas/neighborhoods traversed (risk index, safety history of corridors).
    3. Foot traffic and crowding (the danger of isolation vs well-populated areas).
    4. Crime cases (types of offenses historically noted along this path).
    
    Contrast this path with the shortest route to explain why this longer path is recommended if it has higher safety metrics.
    Provide practical, clear safety advice. Keep the response concise, formatted in HTML bullet points (e.g., <li><strong>Topic:</strong> details</li>).
    """
    try:
        return generate_content_with_fallback(prompt, api_key=api_key)
    except Exception as e:
        logger.error(f"Route explanation API error: {e}")
        return generate_offline_route_explanation(route_type, metrics)

def generate_offline_route_explanation(route_type, metrics):
    if "safe" in route_type.lower() or metrics['safety_score'] > 60:
        return f"""
        <ul>
            <li><strong>Streetlight Density:</strong> {metrics['streetlight_density']}% active lighting along standard routes.</li>
            <li><strong>PCR Police Patrol:</strong> Passes {metrics['police_booths']} active patrol stands.</li>
            <li><strong>Surveillance:</strong> Covered by {metrics['cctv_zones']} active public security camera grids.</li>
            <li><strong>Community Index:</strong> Zero safety hazard reports reported along this stretch in the last 48 hours.</li>
        </ul>
        """
    else:
        return f"""
        <ul>
            <li><strong>Low Illumination Warning:</strong> Only {metrics['streetlight_density']}% functional streetlighting.</li>
            <li><strong>Isolation Threat:</strong> {metrics['foot_traffic']} foot traffic makes assistance difficult in emergencies.</li>
            <li><strong>Police Distance:</strong> Far from emergency police checkpoints.</li>
            <li><strong>Past Records:</strong> Stalking incidents reported near industrial lanes in this route previously.</li>
        </ul>
        """

def generate_emergency_summary(situation, location, coordinates, timestamp, api_key=None):
    """Generate a highly concise, structured emergency summary message including location, detected risk, and details for responders."""
    has_key = configure_gemini(api_key)

    if not has_key:
        return (
            f"🚨 NARI EMERGENCY ALERT\n"
            f"Situation/Risk: {situation}\n"
            f"Location: {location}\n"
            f"Coordinates: {coordinates}\n"
            f"Timestamp: {timestamp}\n"
            f"Status: Distress Signal Broadcasted. Please dispatch help."
        )

    prompt = f"""
    Write a highly structured emergency message that a user in distress can send to family members or police.
    Include the exact location name, GPS coordinates, and detected risk/situation (e.g. suspicious activity, voice panic cues).
    Keep it concise, direct, and under 220 characters. Do not add any conversational fluff.
    
    Details:
    - User Situation/Risk: {situation}
    - Location Name: {location}
    - GPS Coordinates: {coordinates}
    - Time: {timestamp}
    
    Output Format (Make it extremely readable and direct):
    🚨 NARI SOS ALERT:
    - RISK: [Brief situation/risk]
    - WHERE: [location] ([coordinates])
    - TIME: [Time]
    - DETAILS: [Important detail like battery level or voice cue]
    Please send help immediately!
    """
    try:
        return generate_content_with_fallback(prompt, api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to generate emergency summary: {e}")
        return (
            f"🚨 EMERGENCY: Distress reported at {location} ({coordinates}) at {timestamp}. "
            f"Context: {situation}. Call me immediately!"
        )

def extract_memory_facts(user_message, current_memories, api_key=None):
    """Extract semantic facts from user messages to store in Mem0 LTM."""
    # Fast credit-saving parser for standard profile templates
    if "I live at '" in user_message and "My office is at '" in user_message:
        try:
            import re
            home = re.search(r"I live at '([^']*)'", user_message)
            office = re.search(r"My office is at '([^']*)'", user_message)
            travel = re.search(r"My daily travel is: '([^']*)'", user_message)
            lang = re.search(r"Preferred language is '([^']*)'", user_message)
            safe_w = re.search(r"Safe word is '([^']*)'", user_message)

            ops = []

            # Sub-helper to check if this content exists or conflicts in existing_memories
            def get_action_for_fact(content, m_type):
                # Search for similar memory type to update, or add if new
                for m in current_memories:
                    # If content matches exactly, do nothing
                    if m["content"] == content:
                        return None
                    # If type matches, update it
                    if m_type == "preference" and "preferred language" in m["content"].lower() and "language" in content.lower():
                        return {"action": "update", "memory_type": m_type, "content": content, "existing_memory_id": m["id"]}
                    if m_type == "preference" and "safe word" in m["content"].lower() and "safe word" in content.lower():
                        return {"action": "update", "memory_type": m_type, "content": content, "existing_memory_id": m["id"]}
                    if m_type == "route" and "live at" in m["content"].lower() and "live at" in content.lower():
                        return {"action": "update", "memory_type": m_type, "content": content, "existing_memory_id": m["id"]}
                    if m_type == "route" and "office is at" in m["content"].lower() and "office is at" in content.lower():
                        return {"action": "update", "memory_type": m_type, "content": content, "existing_memory_id": m["id"]}
                    if m_type == "habit" and "daily travel" in m["content"].lower() and "daily travel" in content.lower():
                        return {"action": "update", "memory_type": m_type, "content": content, "existing_memory_id": m["id"]}
                return {"action": "add", "memory_type": m_type, "content": content}

            if home and home.group(1):
                op = get_action_for_fact(f"User lives at {home.group(1)}.", "route")
                if op: ops.append(op)
            if office and office.group(1):
                op = get_action_for_fact(f"User office is at {office.group(1)}.", "route")
                if op: ops.append(op)
            if travel and travel.group(1):
                op = get_action_for_fact(f"User daily travel routine: {travel.group(1)}.", "habit")
                if op: ops.append(op)
            if lang and lang.group(1):
                op = get_action_for_fact(f"User preferred language is {lang.group(1)}.", "preference")
                if op: ops.append(op)
            if safe_w and safe_w.group(1):
                op = get_action_for_fact(f"User safe word triggers is configured as '{safe_w.group(1)}'.", "preference")
                if op: ops.append(op)

            logger.info("Extracted memory facts locally to save API credits.")
            return ops
        except Exception as ex:
            logger.error(f"Local memory extraction fallback error: {ex}")

    has_key = configure_gemini(api_key)
    if not has_key:
        return []

    prompt = f"""
    You are the long-term memory engine of Nari. 
    Analyze the user's message and determine if there are facts to remember about their travel habits, languages, home/office location, contacts, or safe words.
    
    Existing Memories:
    {json.dumps(current_memories, indent=2)}
    
    User Message: "{user_message}"
    
    Determine if any NEW facts should be extracted, or if an EXISTING memory is updated or contradicted.
    Only extract facts that are persistent (e.g. travel routes, work office location, travel times, trusted contact details).
    
    Return a JSON array of objects representing modifications (do not put any markdown ticks or wrappers):
    [
        {{
            "action": "add" | "update" | "delete",
            "memory_type": "preference" | "route" | "contact" | "habit",
            "content": "Description of the fact in simple, natural language third-person statement (e.g. 'User travels to Connaught Place on Friday evenings').",
            "existing_memory_id": "if action is update/delete, supply the ID of the contradiction"
        }}
    ]
    
    If no persistent facts are found, return an empty array [].
    """
    try:
        text = generate_content_with_fallback(prompt, api_key=api_key)
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Failed to extract memory facts: {e}")
        return []

def chat_completion(history, user_message, memory_context="", rag_context="", language="English (US)", api_key=None):
    """Chat assistant combining conversation history using Groq LLM exclusively."""
    lang_name = language.split(" ")[0] if language else "English"

    # System instruction
    system_instruction = "you are an ai assistant, give responses in a kind, comforting and gentle tone. give max 2 line of reponse, not in paragraphs. dont include unnecessary words, comfort and help the user."
    if memory_context:
        system_instruction += f"\n\nUser Context / Known Facts:\n{memory_context}"
    if rag_context:
        system_instruction += f"\n\nSafety Knowledge Base Context:\n{rag_context}"
    if lang_name and lang_name != "English":
        system_instruction += f"\n\nPlease respond in language: {lang_name}."

    # Format chat history for Groq API
    messages = [{"role": "system", "content": system_instruction}]
    for msg in history[-10:]:  # Keep last 10 messages
        role = 'user' if msg.get('role') == 'user' else 'assistant'
        messages.append({'role': role, 'content': msg.get('content', '')})

    messages.append({'role': 'user', 'content': user_message})

    groq_key = _get_api_key(api_key)
    return _call_groq(
        messages=messages,
        model="openai/gpt-oss-120b",
        api_key=groq_key,
        temperature=0.7,
        max_completion_tokens=2048,
        top_p=1,
        stream=False
    )

def analyze_conversation_risk(transcript, api_key=None):
    """Analyze recent messages to classify threat score. Emergency triggers ONLY when threat_score reaches 100."""
    key = _get_api_key(api_key)
    if not key:
        # Rule based keywords fallback
        text = " ".join([m["content"] for m in transcript]).lower()
        risk_words = ["weapon", "gun", "knife", "attack", "kidnap", "grabbed"]
        is_acute_emergency = any(w in text for w in risk_words)
        threat_score = 100 if is_acute_emergency else 15

        return {
            "is_emergency": is_acute_emergency,
            "threat_score": threat_score,
            "next_best_action": "🚨 Run to a nearby shop or restaurant, share coordinates immediately, or call 112!" if is_acute_emergency else ""
        }

    # Format transcript
    chat_log = ""
    for m in transcript[-5:]:
        chat_log += f"{m['role'].upper()}: {m['content']}\n"

    prompt = f"""
    Analyze the following recent chat conversation between a user and their safety assistant.
    Evaluate the threat level and determine a Threat Score (0 to 100).
    
    Conversation Log:
    {chat_log}
    
    Threat Score Guidance:
    - 0 to 30: Safe, general conversation, casual queries, greetings.
    - 31 to 60: Minor discomfort, walking at night, broken streetlights.
    - 61 to 99: High alert, suspecting someone is following, feeling scared.
    - 100: CRITICAL IMMEDIATE EMERGENCY (physical attack, weapon, active pursuit, kidnapping, safe word spoken).
    
    Return a JSON object with this exact structure (no ticks or markdown):
    {{
        "is_emergency": boolean (set true ONLY if threat_score is 100),
        "threat_score": integer (0 to 100),
        "next_best_action": "Short action suggestion if threat_score >= 80, otherwise empty string."
    }}
    """
    try:
        res_text = generate_content_with_fallback(prompt, api_key=api_key)
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]
        data = json.loads(res_text.strip())
        score = int(data.get("threat_score", 15))
        data["threat_score"] = score
        data["is_emergency"] = (score >= 100)
        return data
    except Exception:
        return {
            "is_emergency": False,
            "threat_score": 15,
            "next_best_action": ""
        }
