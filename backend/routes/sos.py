from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.services import gemini_service
from backend.database import get_user_profiles_col, get_incident_reports_col

router = APIRouter(prefix="/sos", tags=["SOS Assistant"])

class SOSRequest(BaseModel):
    situation: str
    location_name: str
    latitude: float
    longitude: float
    battery_level: Optional[int] = None
    user_id: Optional[str] = "priya_sharma"

class ContactResponse(BaseModel):
    name: str
    relation: str
    phone: str

class SOSResponse(BaseModel):
    success: bool
    sms_body: str
    contacts: List[ContactResponse]
    timestamp: str

from backend.services.auth_helper import get_current_user_uid

@router.post("", response_model=SOSResponse)
def trigger_sos(
    request: SOSRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    x_gemini_key: Optional[str] = Header(None),
    x_gmaps_key: Optional[str] = Header(None)
):
    """Log the emergency incident, fetch address via Google Maps, alert safety circles, and compile the emergency summary block."""
    try:
        # 1. Fetch user details and emergency contacts from MongoDB linked to authenticated UID
        uid = get_current_user_uid(authorization)
        profiles_col = get_user_profiles_col()
        user_profile = profiles_col.find_one({"uid": uid})
        
        # Fallback to general lookup by name if not found
        if not user_profile:
            user_profile = profiles_col.find_one({"name": "Priya Sharma"})
        if not user_profile:
            user_profile = profiles_col.find_one()
            
        user_name = user_profile.get("name", "User") if user_profile else "User"
        user_phone = user_profile.get("phone", "Unknown") if user_profile else "Unknown"
        
        contacts = []
        if user_profile and "emergency_contacts" in user_profile:
            for c in user_profile["emergency_contacts"]:
                contacts.append(ContactResponse(name=c["name"], relation=c["relation"], phone=c["phone"]))
        else:
            # Fallback hardcoded contacts
            contacts = [
                ContactResponse(name="Aarav Sharma", relation="Husband", phone="7007914594"),
                ContactResponse(name="Neha Verma", relation="Sister", phone="+91 91234 56789")
            ]
            
        # 2. Fetch location address from Google Maps Geocoding API if key is present
        from backend.config import GOOGLE_MAPS_API_KEY
        from backend.routes.nearby import reverse_geocode
        
        gmaps_key = x_gmaps_key or GOOGLE_MAPS_API_KEY
        resolved_address = None
        if gmaps_key:
            resolved_address = reverse_geocode(request.latitude, request.longitude, gmaps_key)
            
        location_name = resolved_address if resolved_address else request.location_name
            
        # 3. Save incident report to MongoDB log
        reports_col = get_incident_reports_col()
        timestamp_str = datetime.now().strftime("%I:%M %p")
        iso_now = datetime.utcnow()
        
        situation_text = f"User {user_name} ({user_phone}) is in distress: {request.situation}"
        
        # Save as high-urgency reported event
        incident_doc = {
            "category": "SOS Dispatch",
            "description": situation_text,
            "location_name": location_name,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "urgency": "Critical",
            "ai_summary": situation_text,
            "created_at": iso_now
        }
        reports_col.insert_one(incident_doc)
        
        # 4. Generate structured AI Emergency Summary via Gemini (bypass for Voice triggers and pre-formatted alerts to use custom messages directly)
        if "🚨 NARI SOS ALERT:" in request.situation or "RECENT CHAT HISTORY:" in request.situation:
            sms_body = request.situation
        elif "Voice SOS trigger" in situation_text or "Voice listener stopped" in situation_text:
            audio_part = ""
            if "Live Audio Alert:" in situation_text:
                parts = situation_text.split("Live Audio Alert:")
                audio_link = parts[-1].strip()
                audio_part = f"\n- 🎙️ VOICE CLIP: {audio_link}"

            if "Voice SOS trigger:" in situation_text:
                spoken_threat = situation_text.split("Voice SOS trigger:")[-1].split("\n")[0].replace("'", "").strip()
                risk_label = f"Voice SOS"
                spoken_line = f"\n- SPOKEN: \"{spoken_threat}\""
            else:
                risk_label = "Voice SOS (Manually Stopped)"
                spoken_line = ""

            sms_body = (
                f"🚨 NARI SOS ALERT:\n"
                f"- RISK: {risk_label}{spoken_line}\n"
                f"- WHERE: {location_name} ({request.latitude:.4f}, {request.longitude:.4f})\n"
                f"- TIME: {datetime.now().strftime('%H:%M')}\n"
                f"Please send help immediately!{audio_part}\n"
                f"Live Location: https://www.google.com/maps?q={request.latitude:.6f},{request.longitude:.6f}"
            )
        else:
            coordinates = f"{request.latitude:.4f}° N, {request.longitude:.4f}° E"
            sms_body = gemini_service.generate_emergency_summary(
                situation=situation_text,
                location=location_name,
                coordinates=coordinates,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                api_key=x_gemini_key
            )
        
        # 5. Send actual SMS alerts to all emergency contacts in the background
        from backend.services.sms_service import broadcast_emergency_sms
        contacts_dict_list = [{"name": c.name, "relation": c.relation, "phone": c.phone} for c in contacts]
        background_tasks.add_task(
            broadcast_emergency_sms,
            contacts=contacts_dict_list,
            base_message=sms_body,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        return SOSResponse(
            success=True,
            sms_body=sms_body,
            contacts=contacts,
            timestamp=timestamp_str
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import UploadFile, File, Request
import shutil
import uuid
import os

@router.post("/upload-audio")
def upload_sos_audio(request: Request, file: UploadFile = File(...)):
    """Upload dynamic emergency audio WAV recording captured by speech listener."""
    try:
        os.makedirs("backend/static/audio", exist_ok=True)
        file_id = str(uuid.uuid4())
        filename = f"SOS_{file_id}.wav"
        file_path = os.path.join("backend/static/audio", filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Resolve public URL — use https on Render, http on localhost
        host = request.headers.get("host", "localhost:8000")
        scheme = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
        audio_url = f"{scheme}://{host}/static/audio/{filename}"
        return {"audio_url": audio_url, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-audio/{filename}")
def delete_sos_audio(filename: str):
    """Delete safety audio file once SOS is resolved/reset."""
    try:
        file_path = os.path.join("backend/static/audio", filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"status": "success", "message": "Audio file deleted"}
        return {"status": "not_found", "message": "File not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
