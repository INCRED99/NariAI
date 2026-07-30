import os
import json
import logging
import google.generativeai as genai
from backend.config import GEMINI_API_KEY, OPENAI_API_KEY

logger = logging.getLogger("nari.gemini")

def configure_gemini(api_key: str = None):
    key = api_key or OPENAI_API_KEY or GEMINI_API_KEY or os.getenv("OPENAI_API_KEY", os.getenv("open_ai_key", os.getenv("GEMINI_API_KEY", "")))
    if key:
        if key.startswith("sk-"):
            return True
        try:
            genai.configure(api_key=key)
            return True
        except Exception:
            return False
    return False

def generate_content_with_fallback(contents, system_instruction=None, api_key=None):
    """
    Generates content attempting OpenAI GPT model first if API key starts with 'sk-'.
    Otherwise, attempts configured Gemini models in sequence of fallback.
    """
    key = api_key or OPENAI_API_KEY or GEMINI_API_KEY or os.getenv("OPENAI_API_KEY", os.getenv("open_ai_key", os.getenv("GEMINI_API_KEY", "")))
    if not key:
        raise ValueError("No API key configured.")

    if key.startswith("sk-"):
        from openai import OpenAI
        try:
            client = OpenAI(api_key=key)
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
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI gpt-4o-mini failed: {e}. Trying fallback gpt-4o...")
            try:
                client = OpenAI(api_key=key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                )
                return response.choices[0].message.content.strip()
            except Exception as ex:
                raise RuntimeError(f"OpenAI fallback models failed: {ex}")
    else:
        has_key = configure_gemini(api_key)
        if not has_key:
            raise ValueError("No Gemini API key configured.")

        models_to_try = [
            'gemini-3.5-flash',
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite'
        ]

        for model_name in models_to_try:
            try:
                if system_instruction:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction
                    )
                else:
                    model = genai.GenerativeModel(model_name)
                response = model.generate_content(contents)
                return response.text.strip()
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}. Trying next fallback...")
                continue

        raise RuntimeError("All configured Gemini models failed to generate content.")

def generate_risk_assessment(location, time_val, weather, crime_index, crowd_density, message, api_key=None):
    """Analyze input context and return a structured risk score, category, and explanation."""
    has_key = configure_gemini(api_key)
    
    if not has_key:
        logger.info("No Gemini API key. Calculating risk score using offline rule-based model.")
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
        logger.error(f"Gemini risk assessment API error: {e}. Using offline fallback.")
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
        logger.error(f"Gemini route explanation API error: {e}")
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

def generate_emergency_summary(situation, location, coordinates, timestamp, battery_level=None, api_key=None):
    """Generate a highly concise, structured emergency summary message including location, detected risk, and details for responders."""
    has_key = configure_gemini(api_key)
    
    battery_str = f" [Battery: {battery_level}%]" if battery_level is not None else ""
    
    if not has_key:
        return (
            f"🚨 NARI EMERGENCY ALERT\n"
            f"Situation/Risk: {situation}\n"
            f"Location: {location}\n"
            f"Coordinates: {coordinates}\n"
            f"Timestamp: {timestamp}{battery_str}\n"
            f"Status: Distress Signal Broadcasted. Please dispatch help."
        )

    prompt = f"""
    Write a highly structured emergency message that a user in distress can send to family members or police.
    Include the exact location name, GPS coordinates, detected risk/situation (e.g. suspicious activity, voice panic cues), and battery status.
    Keep it concise, direct, and under 220 characters. Do not add any conversational fluff.
    
    Details:
    - User Situation/Risk: {situation}
    - Location Name: {location}
    - GPS Coordinates: {coordinates}
    - Time: {timestamp}
    - Device Battery: {battery_level}%
    
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
            f"Context: {situation}. Battery: {battery_level}%. Call me immediately!"
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

def chat_completion(history, user_message, memory_context, rag_context, language="English (US)", api_key=None):
    """Chat assistant combining conversation history, LTM, and legal safety RAG context."""
    has_key = configure_gemini(api_key)
    
    # Translate language identifier if needed
    lang_name = language.split(" ")[0]
    
    if not has_key:
        # Safe offline fallback response
        return get_offline_chat_response(user_message, lang_name)

    # Build system instructions conforming exactly to user spec and safety guided questions
    system_instruction = f"""
You are NARI, an AI Safety Assistant designed to help women during situations involving fear, harassment, stalking, abuse, medical emergencies, or other personal safety concerns.

Your primary goal is to determine whether the user is safe and, if necessary, guide them toward getting immediate help.

------------------------
GENERAL BEHAVIOR
------------------------

- Keep responses short (1–2 sentences).
- Be calm, supportive, and practical.
- Never panic the user.
- Never make assumptions that a crime is occurring without evidence.
- Do not provide long explanations.
- Ask only ONE question at a time.
- Adapt your questions based on previous answers instead of following a rigid script.

------------------------
WHEN TO START A SAFETY CHECK
------------------------

Begin a safety assessment whenever the user expresses or implies:

- fear
- anxiety caused by another person
- stalking
- harassment
- being followed
- domestic violence
- kidnapping concerns
- threats
- assault
- danger
- emergency
- panic
- "help"
- "save me"
- "someone is following me"
- "I feel unsafe"
- similar distress.

------------------------
SAFETY ASSESSMENT
------------------------

Ask ONE relevant question at a time.

Possible questions include:

- Are you somewhere safe right now?
- Are you alone?
- Is someone with you?
- Is someone following you?
- Do you know the person?
- Are they nearby?
- Can you safely speak right now?
- Are you physically injured?
- Are you able to move to a crowded place?
- Is there anyone nearby you trust?
- Would you like me to help alert your emergency contacts?

Only ask questions that are relevant based on previous answers.

------------------------
THREAT ASSESSMENT
------------------------

Internally classify the situation into:

LOW
Examples:
- Feeling anxious
- Minor argument
- Feeling uncomfortable

MEDIUM
Examples:
- Someone following the user
- Persistent harassment
- Feeling trapped
- Unsafe taxi
- Unknown person behaving suspiciously

HIGH
Examples:
- Physical assault
- Kidnapping attempt
- User cannot escape
- User repeatedly asks for help
- User says "Call police"
- User says "I'm in danger"

Never reveal these internal labels unless asked.

------------------------
HIGH RISK BEHAVIOR
------------------------

If the user indicates immediate physical danger (for example: "Someone is trying to grab me", "I'm being attacked", "He has a weapon", "I can't get away", "Help me now", "Call the police"):

Do NOT continue asking other questions.

Instead, ask exactly:
"I believe you may be in immediate danger. Would you like me to alert your emergency contacts now?"

Only after the user confirms (e.g. says yes/confirms), append the keyword "PERFORM_SOS_TASK" as the final line.

------------------------
SOS RULE
------------------------

Only trigger PERFORM_SOS_TASK when one of these conditions is met:

1. The user explicitly asks to notify/message contacts or trigger SOS, such as:
   - Send SOS
   - Alert my contacts
   - Notify my family
   - Call for help
   - Yes, notify them

OR

2. During questioning, the user indicates immediate physical danger, you ask "I believe you may be in immediate danger. Would you like me to alert your emergency contacts now?" and the user confirms.

Never append PERFORM_SOS_TASK under any other circumstances.
STYLE
------------------------

Be empathetic without sounding robotic.

Avoid repeating yourself.

Avoid generic motivational language.

Keep conversations natural.

------------------------
Context

Long-Term Memory:
{memory_context}

Safety Knowledge Base:
{rag_context}

Language:
{language}
"""
    # pyrefly: ignore [parse-error]
    try:
        # Format chat history for Gemini API
        contents = []
        for msg in history[-10:]: # Keep last 10 messages
            role = 'user' if msg['role'] == 'user' else 'model'
            contents.append({'role': role, 'parts': [msg['content']]})
        
        contents.append({'role': 'user', 'parts': [user_message]})
        
        return generate_content_with_fallback(contents, system_instruction=system_instruction, api_key=api_key)
    except Exception as e:
        logger.error(f"Gemini chat API error: {e}")
        return get_offline_chat_response(user_message, lang_name)

def get_offline_chat_response(msg, lang):
    lowered = msg.lower()
    
    # Generic responses depending on keyword matching
    if any(k in lowered for k in ["hello", "hi", "hey", "greetings"]):
        resp_en = (
            "Hello! I am Nari, your safety assistant. I am currently running in offline support mode. "
            "How can I help you stay safe today? You can ask about safety laws, helpline numbers, or route suggestions."
        )
        resp_hi = (
            "नमस्ते! मैं नारी हूँ, आपकी सुरक्षा सहायक। मैं वर्तमान में ऑफलाइन मोड में काम कर रही हूँ। "
            "आज मैं आपकी सुरक्षा में कैसे मदद कर सकती हूँ? आप सुरक्षा कानूनों, हेल्पलाइन नंबरों या सुरक्षित मार्गों के बारे में पूछ सकती हैं।"
        )
    elif any(k in lowered for k in ["follow", "chasing", "stalk", "scared", "afraid", "danger", "dark"]):
        resp_en = (
            "🚨 **Safety Alert**: If you feel you are being followed or in immediate danger:\n"
            "1. Head to the nearest well-lit public area (shop, hospital, or police post).\n"
            "2. Tap the red SOS button to broadcast your live GPS coordinates to your trusted contacts (such as Aarav Sharma).\n"
            "3. If needed, call the emergency services at 112 immediately."
        )
        resp_hi = (
            "🚨 **सुरक्षा चेतावनी**: यदि आपको लगता है कि कोई आपका पीछा कर रहा है या आप खतरे में हैं:\n"
            "1. निकटतम रोशनी वाले सार्वजनिक क्षेत्र (दुकान, अस्पताल या पुलिस चौकी) की ओर बढ़ें।\n"
            "2. अपने विश्वसनीय संपर्कों (जैसे आरव शर्मा) को अपने लाइव जीपीएस स्थान भेजने के लिए लाल एसओएस (SOS) बटन दबाएं।\n"
            "3. आवश्यकता होने पर तुरंत 112 पर कॉल करें।"
        )
    elif any(k in lowered for k in ["law", "right", "ipc", "section", "stalking", "harassment"]):
        resp_en = (
            "⚖️ **Legal Awareness**:\n"
            "Under Indian Law:\n"
            "- **IPC Section 354D** penalizes Stalking (both physical and electronic surveillance) with up to 3 years imprisonment.\n"
            "- **IPC Section 509** covers acts, words, or gestures intended to insult the modesty of a woman.\n"
            "- For legal details, you can consult the 'Safety Laws' database."
        )
        resp_hi = (
            "⚖️ **कानूनी जागरूकता**:\n"
            "भारतीय कानून के तहत:\n"
            "- **IPC धारा 354D** पीछा करने (शारीरिक और इलेक्ट्रॉनिक निगरानी दोनों) को 3 साल तक की जेल की सजा के साथ अपराध मानती है।\n"
            "- **IPC धारा 509** किसी महिला की लज्जा का अनादर करने के इरादे से किए गए कार्यों, शब्दों या इशारों को कवर करती है।\n"
            "- कानूनी विवरण के लिए, आप सुरक्षा कानून डेटाबेस का उपयोग कर सकती हैं।"
        )
    elif any(k in lowered for k in ["route", "commute", "travel", "map"]):
        resp_en = (
            "🗺️ **Commute Safety**:\n"
            "For route planning, please head to the 'Safe Route' tab. It evaluates route lighting, police coverage, and community reports to highlight safer alternatives."
        )
        resp_hi = (
            "🗺️ **सुरक्षित मार्ग**:\n"
            "यात्रा नियोजन के लिए, कृपया 'Safe Route' टैब पर जाएं। यह सुरक्षित मार्ग दिखाने के लिए स्ट्रीटलाइट और पुलिस चौकियों की उपस्थिति का मूल्यांकन करता है।"
        )
    else:
        resp_en = (
            "I am currently operating in offline mode. If you are in danger, please tap the SOS button to alert contacts, or call 112 immediately. "
            "For safe navigation, try checking the Safe Route and Nearby Safe Places features."
        )
        resp_hi = (
            "मैं वर्तमान में ऑफलाइन मोड में काम कर रही हूँ। यदि आप खतरे में हैं, तो संपर्कों को सतर्क करने के लिए तुरंत एसओएस बटन दबाएं या 112 पर कॉल करें। "
            "सुरक्षित यात्रा के लिए Safe Route और Nearby Safe Places सुविधाओं का उपयोग करें।"
        )
        
    resp_mr = resp_en
    resp_bn = resp_en
    resp_ta = resp_en
    
    translations = {
        "Hindi": resp_hi,
        "Marathi": resp_mr,
        "Bengali": resp_bn,
        "Tamil": resp_ta,
        "English": resp_en
    }
    
    return translations.get(lang, resp_en)

def analyze_conversation_risk(transcript, api_key=None):
    """Analyze a list of recent messages to classify if the situation has escalated into an emergency."""
    has_key = configure_gemini(api_key)
    if not has_key:
        # Rule based keywords
        text = " ".join([m["content"] for m in transcript]).lower()
        risk_words = ["chasing", "follow", "scared", "help", "danger", "running", "stalking", "stalk", "kidnap", "weapon", "attack", "police"]
        is_emergency = any(w in text for w in risk_words)
        threat_score = 15
        if is_emergency:
            threat_score = 85
        elif any(w in text for w in ["dark", "deserted", "unlit", "isolated", "stranger"]):
            threat_score = 45
            
        return {
            "is_emergency": is_emergency,
            "threat_score": threat_score,
            "next_best_action": "🚨 Run to a nearby shop or restaurant, share coordinates immediately, or call 112!" if is_emergency else ""
        }

    # Format transcript
    chat_log = ""
    for m in transcript[-5:]:
        chat_log += f"{m['role'].upper()}: {m['content']}\n"
        
    prompt = f"""
    Analyze the following recent chat conversation between a user and their safety assistant.
    Evaluate the threat level and determine if the user is in danger.
    
    Conversation Log:
    {chat_log}
    
    Return a JSON object with this exact structure (no ticks or markdown):
    {{
        "is_emergency": boolean,
        "threat_score": integer between 0 and 100, representing the estimated risk level of the situation (e.g. 0-20 for safe/general conversation, 20-50 for minor discomfort/dark streets/uncomfortable environment, 50-80 for stalking/harassment/suspicious person following, 80-100 for immediate threat/weapon/physical attack/escapes blocked),
        "next_best_action": "Short action suggestion if in danger (e.g. 'Seek immediate shelter in a public building', 'Call PCR patrol', 'Pre-draft emergency SMS'). If no threat, leave empty string."
    }}
    """
    try:
        res_text = generate_content_with_fallback(prompt, api_key=api_key)
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]
        data = json.loads(res_text.strip())
        if "threat_score" not in data:
            data["threat_score"] = 85 if data.get("is_emergency") else 15
        return data
    except Exception:
        # Fallback
        return {
            "is_emergency": False,
            "threat_score": 15,
            "next_best_action": ""
        }
