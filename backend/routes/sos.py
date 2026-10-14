from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.services import gemini_service
from backend.database import get_user_profiles_col, get_incident_reports_col
from backend.config import GROQ_API_KEY
import logging

logger = logging.getLogger("nari.sos")

router = APIRouter(prefix="/sos", tags=["SOS Assistant"])

class SOSRequest(BaseModel):
    situation: str
    location_name: str
    latitude: float
    longitude: float
    battery_level: Optional[int] = None
    user_id: Optional[str] = "priya_sharma"
    trigger_type: Optional[str] = "Manual"

class ContactResponse(BaseModel):
    name: str
    relation: str
    phone: str

class WhatsAppLinkItem(BaseModel):
    name: str
    phone: str
    wa_link: str

class SOSResponse(BaseModel):
    success: bool
    sms_body: str
    contacts: List[ContactResponse]
    whatsapp_links: List[WhatsAppLinkItem] = []
    timestamp: str

from backend.services.auth_helper import get_current_user_uid

@router.post("", response_model=SOSResponse)
def trigger_sos(
    request: SOSRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    x_gemini_key: Optional[str] = Header(None),
    x_groq_key: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    x_gmaps_key: Optional[str] = Header(None)
):
    """Log the emergency incident, fetch address via OpenStreetMap, alert safety circles, and compile the emergency summary block."""
    try:
        # 1. Resolve user UID safely — never let auth failure block SOS dispatch
        uid = request.user_id or "priya_sharma"
        if authorization and isinstance(authorization, str):
            try:
                uid = get_current_user_uid(authorization)
            except Exception as auth_err:
                logger.warning(f"SOS auth fallback (non-blocking): {auth_err}")
                # Continue with request.user_id fallback — SOS must never be blocked by auth

        # Resolve the best available Groq API key
        api_key = next((k for k in [x_groq_key, x_api_key, x_gemini_key] if isinstance(k, str) and k.startswith("gsk_")), None) or GROQ_API_KEY

        profiles_col = get_user_profiles_col()
        user_profile = None
        if profiles_col is not None:
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
        
        if not contacts:
            # Fallback hardcoded contacts — SOS must always have recipients
            contacts = [
                ContactResponse(name="Aarav Sharma", relation="Husband", phone="7007914594"),
                ContactResponse(name="Neha Verma", relation="Sister", phone="+91 91234 56789")
            ]
            
        # 2. Fetch location address from OpenStreetMap Nominatim
        from backend.routes.nearby import reverse_geocode
        
        resolved_address = reverse_geocode(request.latitude, request.longitude)
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
            "trigger_type": request.trigger_type or "Manual",
            "created_at": iso_now
        }
        try:
            reports_col.insert_one(incident_doc)
        except Exception as db_err:
            logger.error(f"SOS incident DB log failed (non-blocking): {db_err}")
        
        # 4. Generate structured AI Emergency Summary via Groq (bypass for Voice triggers and pre-formatted alerts to use custom messages directly)
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
                f"- WHERE: {location_name} ({request.latitude:.6f}, {request.longitude:.6f})\n"
                f"- TIME: {datetime.now().strftime('%H:%M')}\n"
                f"Please send help immediately!{audio_part}\n"
                f"Live Location: https://www.openstreetmap.org/?mlat={request.latitude:.6f}&mlon={request.longitude:.6f}#map=18/{request.latitude:.6f}/{request.longitude:.6f}"
            )
        else:
            coordinates = f"{request.latitude:.4f}° N, {request.longitude:.4f}° E"
            try:
                sms_body = gemini_service.generate_emergency_summary(
                    situation=situation_text,
                    location=location_name,
                    coordinates=coordinates,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    api_key=api_key
                )
            except Exception as ai_err:
                logger.error(f"AI emergency summary generation failed (using template): {ai_err}")
                sms_body = (
                    f"🚨 NARI SOS ALERT:\n"
                    f"- RISK: {request.situation}\n"
                    f"- WHERE: {location_name} ({coordinates})\n"
                    f"- TIME: {datetime.now().strftime('%H:%M')}\n"
                    f"Please send help immediately!\n"
                    f"Live Location: https://www.openstreetmap.org/?mlat={request.latitude:.6f}&mlon={request.longitude:.6f}#map=18/{request.latitude:.6f}/{request.longitude:.6f}"
                )
        
        # 5. Send alerts to all emergency contacts via both SMS and WhatsApp
        from backend.services.sms_service import broadcast_emergency_sms
        from backend.services.whatsapp_service import broadcast_emergency_whatsapp
        
        contacts_dict_list = [{"name": c.name, "relation": c.relation, "phone": c.phone} for c in contacts]
        
        # SMS broadcast (background)
        background_tasks.add_task(
            broadcast_emergency_sms,
            contacts=contacts_dict_list,
            base_message=sms_body,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        # WhatsApp broadcast (synchronous so we can return wa.me links immediately)
        wa_results = []
        try:
            wa_results = broadcast_emergency_whatsapp(
                contacts=contacts_dict_list,
                base_message=sms_body,
                latitude=request.latitude,
                longitude=request.longitude
            )
        except Exception as wa_err:
            logger.error(f"WhatsApp broadcast error (non-blocking): {wa_err}")
        
        # Build WhatsApp link items for frontend auto-open
        whatsapp_links = []
        for wa_r in wa_results:
            whatsapp_links.append(WhatsAppLinkItem(
                name=wa_r.get("name", "Contact"),
                phone=wa_r.get("phone", ""),
                wa_link=wa_r.get("wa_link", "")
            ))
        
        logger.warning(f"🚨 SOS DISPATCHED for {user_name} at {location_name} ({request.latitude:.6f}, {request.longitude:.6f}) — {len(contacts)} contacts alerted via SMS + WhatsApp")
        
        return SOSResponse(
            success=True,
            sms_body=sms_body,
            contacts=contacts,
            whatsapp_links=whatsapp_links,
            timestamp=timestamp_str
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"SOS route critical failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import UploadFile, File, Request
import shutil
import uuid
import os

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "audio")

@router.post("/upload-audio")
def upload_sos_audio(request: Request, file: UploadFile = File(...)):
    """Upload dynamic emergency audio WAV recording captured by speech listener."""
    try:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        file_id = str(uuid.uuid4())
        filename = f"SOS_{file_id}.wav"
        file_path = os.path.join(AUDIO_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Resolve public URL — use https on Render, http on localhost
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:8000")
        scheme = request.headers.get("x-forwarded-proto") or ("https" if "render.com" in host else "http")
        audio_url = f"{scheme}://{host}/static/audio/{filename}"
        return {"audio_url": audio_url, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-audio/{filename}")
def delete_sos_audio(filename: str):
    """Delete safety audio file once SOS is resolved/reset."""
    try:
        file_path = os.path.join(AUDIO_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"status": "success", "message": "Audio file deleted"}
        return {"status": "not_found", "message": "File not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
