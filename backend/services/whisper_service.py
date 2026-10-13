import os
import json
import logging
from groq import Groq
from backend.config import GROQ_API_KEY

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

def transcribe_audio_file(file_bytes, filename="audio.wav", api_key=None):
    """Transcribe an audio file using Groq Whisper API or simulated fallback."""
    key = api_key if (isinstance(api_key, str) and api_key.startswith("gsk_")) else (GROQ_API_KEY or os.getenv("GROQ_API_KEY", ""))
    
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
            
        logger.info(f"Transcribing {temp_path} using Groq Whisper API...")
        client = Groq(api_key=key)
        with open(temp_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(filename, audio_file.read()),
                model="whisper-large-v3-turbo",
                response_format="text"
            )
        return str(transcription).strip()
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
    """Analyze audio file using Groq Whisper + Groq LLM panic classifier."""
    key = api_key or GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
    
    # Fast credit-saving parser for simulated triggers
    lower_fn = filename.lower()
    if lower_fn.startswith("panic_") or any(w in lower_fn for w in ["help", "bachao", "scream", "stop", "madad"]):
        logger.info("Simulated voice trigger detected. Using local mock analysis to save API credits.")
        return mock_voice_analysis(filename)

    if not key:
        logger.info("Operating in offline mock mode for voice panic.")
        return mock_voice_analysis(filename)
        
    try:
        transcript = transcribe_audio_file(file_bytes, filename=filename, api_key=key)
        is_panic, words = check_for_panic(transcript)

        # Call Groq LLM to perform sentiment and distress analysis on transcript
        from backend.services.gemini_service import _call_groq
        prompt = f"""
        Analyze this user audio transcript for distress and safety panic:
        "{transcript}"
        
        Return a valid JSON object strictly matching this format (no ticks or markdown):
        {{
            "transcript": {json.dumps(transcript)},
            "panic_detected": boolean,
            "distress_indicators": ["list", "of", "keywords"],
            "explanation": "Detailed explanation of emotional distress/panic level"
        }}
        """
        response_text = _call_groq([{"role": "user", "content": prompt}], api_key=key)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        return json.loads(response_text.strip())
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
