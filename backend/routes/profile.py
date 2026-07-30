import json
from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List
from backend.database import get_user_profiles_col
from backend.services import memory_service

router = APIRouter(prefix="/profile", tags=["User Profile & Memory"])

from backend.services.auth_helper import get_current_user_uid

class ContactItem(BaseModel):
    name: str
    relation: str
    phone: str

class ProfileUpdateRequest(BaseModel):
    name: str
    phone: str
    preferred_language: str
    safe_word: str
    home_address: str
    home_lat: float
    home_lng: float
    office_address: str
    office_lat: float
    office_lng: float
    travel_routine: str
    emergency_contacts: List[ContactItem]

@router.get("")
def get_profile(authorization: Optional[str] = Header(None)):
    """Retrieve user profile configurations and long-term memory statements."""
    try:
        uid = get_current_user_uid(authorization)
        col = get_user_profiles_col()
        profile = col.find_one({"uid": uid})
        
        if not profile:
            # Seed default profile if not found
            default_profile = {
                "uid": uid,
                "name": "User",
                "phone": "",
                "preferred_language": "English (US)",
                "safe_word": "Blue Moon",
                "home_address": "",
                "home_lat": 0.0,
                "home_lng": 0.0,
                "office_address": "",
                "office_lat": 0.0,
                "office_lng": 0.0,
                "travel_routine": "",
                "emergency_contacts": [
                    {"name": "Aarav Sharma", "relation": "Husband", "phone": "7007914594"},
                    {"name": "Neha Verma", "relation": "Sister", "phone": "+91 91234 56789"},
                    {"name": "Siddharth", "relation": "Roommate", "phone": "+91 99887 76655"}
                ]
            }
            col.insert_one(default_profile)
            profile = col.find_one({"uid": uid})

        # Get memories
        memories = memory_service.get_all_memories(uid)
        memories_text = [m["content"] for m in memories]
        
        # Clean Mongo _id for JSON output
        profile_data = dict(profile)
        profile_data["_id"] = str(profile_data["_id"])
        
        # Convert emergency contacts format
        contacts = []
        for c in profile_data.get("emergency_contacts", []):
            contacts.append({
                "name": c.get("name"),
                "relation": c.get("relation"),
                "phone": c.get("phone")
            })
            
        return {
            "profile": {
                "name": profile_data.get("name"),
                "phone": profile_data.get("phone"),
                "preferred_language": profile_data.get("preferred_language"),
                "safe_word": profile_data.get("safe_word"),
                "home_address": profile_data.get("home_address"),
                "home_lat": profile_data.get("home_lat"),
                "home_lng": profile_data.get("home_lng"),
                "office_address": profile_data.get("office_address"),
                "office_lat": profile_data.get("office_lat"),
                "office_lng": profile_data.get("office_lng"),
                "travel_routine": profile_data.get("travel_routine"),
                "emergency_contacts": contacts
            },
            "memories": memories,
            "memories_text": memories_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
def update_profile(request: ProfileUpdateRequest, authorization: Optional[str] = Header(None), x_gemini_key: Optional[str] = Header(None)):
    """Save user parameters and extract long-term safety memory cues."""
    try:
        uid = get_current_user_uid(authorization)
        col = get_user_profiles_col()
        
        contacts_dict = [c.dict() for c in request.emergency_contacts]
        
        # Update MongoDB
        col.update_one(
            {"uid": uid},
            {"$set": {
                "name": request.name,
                "phone": request.phone,
                "preferred_language": request.preferred_language,
                "safe_word": request.safe_word,
                "home_address": request.home_address,
                "home_lat": request.home_lat,
                "home_lng": request.home_lng,
                "office_address": request.office_address,
                "office_lat": request.office_lat,
                "office_lng": request.office_lng,
                "travel_routine": request.travel_routine,
                "emergency_contacts": contacts_dict
            }},
            upsert=True
        )
        
        # Process and update semantic LTM (Mem0 style)
        memory_service.process_and_extract_memory(
            user_message=f"I live at '{request.home_address}'. My office is at '{request.office_address}'. My daily travel is: '{request.travel_routine}'. Preferred language is '{request.preferred_language}'. Safe word is '{request.safe_word}'.",
            user_id=uid,
            api_key=x_gemini_key
        )
        
        return {"success": True, "message": "Profile updated and AI safety memory extracted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-memories")
def clear_memories(authorization: Optional[str] = Header(None)):
    """Wipe out the safety memories collection for the user."""
    try:
        uid = get_current_user_uid(authorization)
        from backend.database import get_safety_memories_col
        col = get_safety_memories_col()
        col.delete_many({"user_id": uid})
        return {"success": True, "message": "All long-term memories cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
