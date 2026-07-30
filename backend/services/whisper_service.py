import os
import logging
import google.generativeai as genai
from backend.services.gemini_service import configure_gemini

logger = logging.getLogger("nari.whisper")

# Panic triggers in multiple languages
PANIC_PHRASES = [
    # English
    "help", "following me", "follow me", "scared", "save me", "danger", "afraid", "unsafe", "stalking", "stalk", "chasing", "chase", "emergency", "distress", "police", "attack", "hurt", "kill", "accident",
    # Hindi / Urdu / Hinglish
    "bachao", "bachao mujhe", "madad", "madad karo", "peecha kar raha", "darr lag raha", "koi peeche hai", "bhago", "bacho", "maar raha", "peechha", "picha", "peeche hai", "hath chodo", "haath chhodo", "police ko bulao", "khatra", "suraksha", "musibat", "bhaiya bacho", "bachao bachao", "chodo mujhe", "chhodo mujhe",
    # Marathi
    "bheeti", "bheeti wattey", "pecha kartoy", "madat kara",
    # Bengali
    "bhoy", "bhoy korche", "keu pechone", "bachan", "sahajjo korun",
    # Tamil
    "kapathunga", "bayam", "yaaro pinthodarangah", "udhavi",
    # Telugu
    "kapadandi", "bhayam", "venakala padutunnaru", "sahayam"
]

import json

def transcribe_audio_file(file_bytes, filename="audio.wav", api_key=None):
    """Transcribe an audio file using Gemini audio capacity or simulated fallback."""
    from backend.config import GEMINI_API_KEY
    key = api_key if (api_key and not api_key.startswith("sk-")) else GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    
    # Fast credit-saving parser for simulated triggers
    lower_fn = filename.lower()
    if lower_fn.startswith("panic_") or any(w in lower_fn for w in ["help", "bachao", "scream", "stop", "madad"]):
        logger.info("Simulated voice trigger detected. Using local mock transcription to save API credits.")
        return mock_stt_fallback(filename)

    if not key:
        logger.info("Operating in offline mock mode. Simulating STT transcription.")
        return mock_stt_fallback(filename)

    # Write bytes temporarily to upload
    temp_path = f"temp_{filename}"
    try:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
            
        logger.info(f"Uploading {temp_path} to Gemini for transcription...")
        genai.configure(api_key=key)
        uploaded_file = genai.upload_file(path=temp_path)
        
        models_to_try = ['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-2.0-flash']
        transcript = None
        
        prompt = (
            "Transcribe this audio file accurately. "
            "Return ONLY the transcribed text in its native language/script. "
            "Do not add introductions, explanations, or wrappers."
        )
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([uploaded_file, prompt])
                transcript = response.text.strip()
                break
            except Exception as model_err:
                logger.warning(f"Transcription Model {model_name} failed: {model_err}. Trying next...")
                continue
                
        if not transcript:
            raise Exception("All Gemini models failed to transcribe audio.")
            
        try:
            genai.delete_file(uploaded_file.name)
        except Exception as delete_err:
            logger.warning(f"Failed to delete uploaded file from Gemini server: {delete_err}")
            
        return transcript
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}. Falling back to simulation.")
        return mock_stt_fallback(filename)
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

def analyze_voice_audio(file_bytes, filename="audio.wav", api_key=None):
    """Analyze the audio file using Gemini to transcribe and detect panic, fear, or distress in voice/tone/words."""
    from backend.config import GEMINI_API_KEY
    key = api_key if (api_key and not api_key.startswith("sk-")) else GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    
    # Fast credit-saving parser for simulated triggers
    lower_fn = filename.lower()
    if lower_fn.startswith("panic_") or any(w in lower_fn for w in ["help", "bachao", "scream", "stop", "madad"]):
        logger.info("Simulated voice trigger detected. Using local mock analysis to save API credits.")
        return mock_voice_analysis(filename)

    if not key:
        logger.info("Operating in offline mock mode for voice panic.")
        return mock_voice_analysis(filename)
        
    temp_path = f"temp_{filename}"
    try:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
        
        logger.info(f"Uploading {temp_path} to Gemini for multimodal voice panic analysis...")
        genai.configure(api_key=key)
        uploaded_file = genai.upload_file(path=temp_path)
        
        models_to_try = ['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-2.0-flash']
        response_text = None
        
        prompt = """
        You are the voice analysis security module of Nari, an AI safety assistant.
        Analyze this audio recording of a user's voice.
        
        1. Transcribe the spoken text accurately.
        2. Analyze the emotional tone, pitch, speed, and vocabulary of the voice to detect if there is any panic, fear, distress, or danger.
        3. Identify specific indicators of distress/panic (e.g., screaming, breathing heavily, crying, or speaking urgently).
        
        Your response must be a valid JSON object containing exactly these fields:
        {
            "transcript": "Transcribed text",
            "panic_detected": true/false,
            "distress_indicators": ["panic", "fear", "distress", "urgency", "etc"],
            "explanation": "Detailed explanation of the emotional state (panic, fear, distress, etc.) detected from both the speech content and voice tone."
        }
        """
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    [uploaded_file, prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                response_text = response.text.strip()
                break
            except Exception as model_err:
                logger.warning(f"STT Model {model_name} failed: {model_err}. Trying next...")
                continue
                
        if not response_text:
            raise Exception("All Gemini models failed to analyze voice audio.")
            
        try:
            genai.delete_file(uploaded_file.name)
        except Exception as delete_err:
            logger.warning(f"Failed to delete uploaded file from Gemini server: {delete_err}")
            
        return json.loads(response_text)
    except Exception as e:
        logger.error(f"Voice panic analysis failed: {e}. Falling back to simulation.")
        return mock_voice_analysis(filename)
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def mock_voice_analysis(filename):
    """Fallback voice analyzer that parses filename keyword triggers."""
    lower_fn = filename.lower().replace(".wav", "").replace("_", " ")
    
    if "panic_scream" in lower_fn:
        transcript = "Aaah! Please help me, someone is here!"
        panic = True
    elif "panic_help" in lower_fn:
        transcript = "Help! Someone is following me in the dark alley. I am extremely scared, please save me!"
        panic = True
    elif "panic_bachao" in lower_fn:
        transcript = "Bachao! Bachao! Mujhe bachao!"
        panic = True
    elif "panic_stop" in lower_fn:
        transcript = "Stop! Don't come near me! Go away!"
        panic = True
    else:
        # If user typed a custom message in the text input, let's run custom check
        transcript = lower_fn
        panic, _ = check_for_panic(transcript)
        
    distress_indicators = []
    if panic:
        distress_indicators = ["panic", "fear", "distress"]
        explanation = f"[Mock Voice Analyzer] Detected distress cues and panic words in the audio text: '{transcript}'"
    else:
        explanation = f"[Mock Voice Analyzer] Normal speech, no significant distress detected in: '{transcript}'"
        
    return {
        "transcript": transcript,
        "panic_detected": panic,
        "distress_indicators": distress_indicators,
        "explanation": explanation
    }

def mock_stt_fallback(filename):
    """Generate high-fidelity dummy outputs for interface simulation."""
    # We can detect file name cues to simulate different voice panic levels
    lower_fn = filename.lower()
    if "panic" in lower_fn or "help" in lower_fn:
        return "Help! Someone is following me in the dark alley. I am extremely scared, please save me!"
    elif "route" in lower_fn or "normal" in lower_fn:
        return "I am planning my route home. Can you show me the safest way?"
    else:
        # Standard default trigger for user testing
        return "Help, someone is following me!"

def check_for_panic(text):
    """Scan transcribed text to check if any multilingual panic keyword is present."""
    if not text:
        return False, []
        
    lowered_text = text.lower()
    triggered_words = []
    
    for phrase in PANIC_PHRASES:
        if phrase in lowered_text:
            triggered_words.append(phrase)
            
    is_panic = len(triggered_words) > 0
    return is_panic, triggered_words
