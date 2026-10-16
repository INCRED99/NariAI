import json
from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List
from backend.database import get_user_profiles_col
from backend.services import memory_service

router = APIRouter(prefix="/profile", tags=["User Profile & Memory"])

from backend.services.auth_helper import get_current_user_uid

class ContactItem(BaseModel):
    name: Optional[str] = ""
    relation: Optional[str] = "Contact"
    phone: Optional[str] = ""

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = "User"
    phone: Optional[str] = ""
    preferred_language: Optional[str] = "English (US)"
    safe_word: Optional[str] = "Blue Moon"
    home_address: Optional[str] = None
    home_lat: Optional[float] = None
    home_lng: Optional[float] = None
    office_address: Optional[str] = None
    office_lat: Optional[float] = None
    office_lng: Optional[float] = None
    travel_routine: Optional[str] = None
    emergency_contacts: Optional[List[ContactItem]] = []

@router.get("")
def get_profile(authorization: Optional[str] = Header(None)):
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authentication required. Please log in.")
        uid = get_current_user_uid(authorization)

        col = get_user_profiles_col()
        profile = col.find_one({"uid": uid}) if col is not None else None
        
        if not profile:
            # Seed default profile if not found
            default_profile = {
                "uid": uid,
                "name": "Priya Sharma",
                "phone": "+91 98765 43210",
                "preferred_language": "English (US)",
                "safe_word": "Blue Moon",
                "home_address": "Waranga, Nagpur",
                "home_lat": 21.1458,
                "home_lng": 79.0882,
                "office_address": "IT Park, Nagpur",
                "office_lat": 21.1250,
                "office_lng": 79.0500,
                "travel_routine": "Daily commute via Metro & Auto",
                "emergency_contacts": [
                    {"name": "Aarav Sharma", "relation": "Husband", "phone": "7007914594"},
                    {"name": "Neha Verma", "relation": "Sister", "phone": "+91 91234 56789"},
                    {"name": "Siddharth", "relation": "Roommate", "phone": "+91 99887 76655"}
                ]
            }
            if col is not None:
                col.insert_one(default_profile)
            profile = default_profile

        # Get memories
        memories = memory_service.get_all_memories(uid)
        memories_text = [m["content"] for m in memories]
        
        # Clean Mongo _id for JSON output
        profile_data = dict(profile)
        if "_id" in profile_data:
            profile_data["_id"] = str(profile_data["_id"])
        
        # Convert emergency contacts format
        contacts = []
        for c in profile_data.get("emergency_contacts", []):
            contacts.append({
                "name": c.get("name") or "",
                "relation": c.get("relation") or "Contact",
                "phone": c.get("phone") or ""
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
def update_profile(
    request: ProfileUpdateRequest,
    authorization: Optional[str] = Header(None),
    x_gemini_key: Optional[str] = Header(None),
    x_groq_key: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """Save user parameters and extract long-term safety memory cues."""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authentication required. Please log in.")
        uid = get_current_user_uid(authorization)

        api_key = x_groq_key or x_api_key or x_gemini_key
        col = get_user_profiles_col()
        
        contacts_dict = [c.dict() for c in (request.emergency_contacts or [])]
        
        # Build update fields cleanly
        set_fields = {
            "name": request.name or "User",
            "phone": request.phone or "",
            "preferred_language": request.preferred_language or "English (US)",
            "safe_word": request.safe_word or "Blue Moon",
            "emergency_contacts": contacts_dict
        }
        if request.home_address is not None:
            set_fields["home_address"] = request.home_address
            if request.home_lat is not None:
                set_fields["home_lat"] = request.home_lat
            if request.home_lng is not None:
                set_fields["home_lng"] = request.home_lng
        if request.office_address is not None:
            set_fields["office_address"] = request.office_address
            if request.office_lat is not None:
                set_fields["office_lat"] = request.office_lat
            if request.office_lng is not None:
                set_fields["office_lng"] = request.office_lng
        if request.travel_routine is not None:
            set_fields["travel_routine"] = request.travel_routine

        # Update MongoDB
        if col is not None:
            col.update_one(
                {"uid": uid},
                {"$set": set_fields},
                upsert=True
            )
        
        # Process and update semantic LTM (Mem0 style) non-blockingly
        try:
            home_txt = request.home_address or ""
            off_txt = request.office_address or ""
            trv_txt = request.travel_routine or ""
            memory_service.process_and_extract_memory(
                user_message=f"I live at '{home_txt}'. My office is at '{off_txt}'. My daily travel is: '{trv_txt}'. Preferred language is '{request.preferred_language}'. Safe word is '{request.safe_word}'.",
                user_id=uid,
                api_key=api_key
            )
        except Exception as mem_err:
            pass
        
        return {"success": True, "message": "Profile updated successfully.", "emergency_contacts": contacts_dict}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contacts")
def update_contacts(
    contacts: List[ContactItem] = Body(...),
    authorization: Optional[str] = Header(None)
):
    """Directly update and persist emergency contacts."""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authentication required. Please log in.")
        uid = get_current_user_uid(authorization)
        col = get_user_profiles_col()
        contacts_dict = [c.dict() for c in contacts]
        if col is not None:
            col.update_one(
                {"uid": uid},
                {"$set": {"emergency_contacts": contacts_dict}},
                upsert=True
            )
        return {"success": True, "emergency_contacts": contacts_dict, "message": "Emergency contacts saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
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
