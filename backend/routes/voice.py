import logging
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.services import whisper_service, gemini_service
from backend.services.auth_helper import get_current_user_uid
from backend.database import db_manager, get_user_profiles_col, get_incident_reports_col

logger = logging.getLogger("nari.voice")
router = APIRouter(prefix="/voice-panic", tags=["Voice Panic Detection"])

class VoicePanicResponse(BaseModel):
    transcript: str
    panic_detected: bool
    triggered_phrases: List[str]
    elevate_risk: bool
    next_action: str
    distress_indicators: List[str] = []
    explanation: str = ""
    db_connection_status: str
    emergency_message_sent: bool
    emergency_message_recipients: List[str] = []
    emergency_message_body: Optional[str] = None

@router.post("", response_model=VoicePanicResponse)
async def process_voice_panic(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    location_name: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    x_gemini_key: Optional[str] = Header(None),
    x_gmaps_key: Optional[str] = Header(None)
):
    """Transcribe voice sample, verify database connection, analyze for distress words, and notify emergency contacts with live location."""
    try:
        # 1. Check database connection
        db_connected, db_status = db_manager.check_connection_and_fallback()

        # 2. Retrieve emergency contacts and location details from Database
        contacts = []
        lat = latitude if latitude is not None else 28.6273
        lng = longitude if longitude is not None else 77.3725
        resolved_loc_name = location_name if location_name is not None else "Sector 62 Noida"
        
        if db_connected:
            try:
                profiles_col = get_user_profiles_col()
                user_profile = None
                
                # Fetch profile based on authorization header if available
                if authorization:
                    try:
                        uid = get_current_user_uid(authorization)
                        user_profile = profiles_col.find_one({"uid": uid})
                    except Exception:
                        pass
                
                # Fallback to the default profile if authorization matches no user or is absent
                if not user_profile:
                    user_profile = profiles_col.find_one({"name": "Priya Sharma"})
                if not user_profile:
                    user_profile = profiles_col.find_one()
                
                if user_profile:
                    if "emergency_contacts" in user_profile:
                        contacts = user_profile["emergency_contacts"]
                    
                    if latitude is None:
                        lat = user_profile.get("home_lat", lat)
                    if longitude is None:
                        lng = user_profile.get("home_lng", lng)
                    if location_name is None:
                        resolved_loc_name = user_profile.get("home_address", resolved_loc_name)
            except Exception as ex:
                logger.error(f"Error fetching user profile from database: {ex}")

        # Resolve address name dynamically using Google Maps API if key is present
        from backend.config import GOOGLE_MAPS_API_KEY
        from backend.routes.nearby import reverse_geocode
        
        gmaps_key = x_gmaps_key or GOOGLE_MAPS_API_KEY
        if gmaps_key:
            address = reverse_geocode(lat, lng, gmaps_key)
            if address:
                resolved_loc_name = address

        # Default fallback contacts if database has none
        if not contacts:
            contacts = [
                {"name": "Aarav Sharma", "relation": "Husband", "phone": "7007914594"},
                {"name": "Neha Verma", "relation": "Sister", "phone": "+91 91234 56789"}
            ]

        # 3. Read uploaded audio bytes
        content = await file.read()
        filename = file.filename
        
        # 4. Transcribe and analyze voice audio with Gemini (forcing Gemini over OpenAI)
        analysis = whisper_service.analyze_voice_audio(
            file_bytes=content,
            filename=filename,
            api_key=x_gemini_key
        )
        
        transcript = analysis.get("transcript", "")
        panic_detected = analysis.get("panic_detected", False)
        distress_indicators = analysis.get("distress_indicators", [])
        explanation = analysis.get("explanation", "")
        
        # 5. Fallback/supplementary phrase matching locally (checking for expanded panic words)
        local_panic, phrases = whisper_service.check_for_panic(transcript)
        
        is_distress = panic_detected or local_panic
        
        # 6. Send emergency alerts to contacts if distress/panic detected
        emergency_message_sent = False
        emergency_message_body = None
        recipients = []
        
        if is_distress:
            # Map contact recipients
            recipients = [f"{c['name']} ({c['phone']})" for c in contacts]
                
            coordinates = f"{lat:.4f}° N, {lng:.4f}° E"
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # Generate high-quality emergency alert SMS with Gemini
                emergency_message_body = gemini_service.generate_emergency_summary(
                    situation=f"Voice distress alert: '{transcript}'",
                    location=resolved_loc_name,
                    coordinates=coordinates,
                    timestamp=timestamp_str,
                    battery_level=85,
                    api_key=x_gemini_key
                )
                
                # Save reported incident in database
                if db_connected:
                    try:
                        reports_col = get_incident_reports_col()
                        incident_doc = {
                            "category": "Voice Distress Trigger",
                            "description": f"Voice panic/distress detected: '{transcript}'",
                            "location_name": resolved_loc_name,
                            "latitude": lat,
                            "longitude": lng,
                            "urgency": "Critical",
                            "ai_summary": emergency_message_body,
                            "created_at": datetime.utcnow()
                        }
                        reports_col.insert_one(incident_doc)
                    except Exception as ex:
                        logger.error(f"Failed to save incident report: {ex}")
                
                # Log actual "sending message" action and broadcast SMS
                logger.warning(f"SMS Broadcast Triggered to: {recipients}")
                
                from backend.services.sms_service import broadcast_emergency_sms
                broadcast_emergency_sms(
                    contacts=contacts,
                    base_message=emergency_message_body,
                    latitude=lat,
                    longitude=lng
                )
                
                emergency_message_sent = True
            except Exception as ex:
                logger.error(f"Failed to generate/broadcast emergency alerts: {ex}")

        # Assemble safety response guidance
        next_action = ""
        if is_distress:
            next_action = "🚨 EMERGENCY ACTIVE: Distress alerts sent to emergency contacts. Find a public crowded space or call 112 immediately."
            logger.warning(f"Emergency voice distress active: {explanation}")
            
        return VoicePanicResponse(
            transcript=transcript,
            panic_detected=is_distress,
            triggered_phrases=phrases,
            elevate_risk=is_distress,
            next_action=next_action,
            distress_indicators=distress_indicators,
            explanation=explanation,
            db_connection_status=db_status,
            emergency_message_sent=emergency_message_sent,
            emergency_message_recipients=recipients,
            emergency_message_body=emergency_message_body
        )
    except Exception as e:
        logger.error(f"Voice panic processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
