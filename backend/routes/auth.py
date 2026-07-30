import logging
import requests
import json
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from firebase_admin import auth
from backend.config import FIREBASE_API_KEY
from backend.database import get_user_profiles_col

logger = logging.getLogger("nari.auth")
router = APIRouter(prefix="/auth", tags=["User Authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def format_phone_number(phone: str) -> str:
    """Format user phone number to standard E.164 format for Firebase."""
    cleaned = "".join([c for c in phone if c.isdigit() or c == "+"])
    if not cleaned.startswith("+"):
        if len(cleaned) == 10:
            cleaned = "+91" + cleaned
        else:
            cleaned = "+" + cleaned
    return cleaned

@router.post("/register")
def register_user(request: RegisterRequest):
    """Register a new user in Firebase Auth and seed their profile in MongoDB."""
    try:
        formatted_phone = format_phone_number(request.phone)
        
        # 1. Create user in Firebase Authentication
        user_record = auth.create_user(
            email=request.email,
            password=request.password,
            phone_number=formatted_phone,
            display_name=request.name
        )
        
        # 2. Seed profile in MongoDB linked to Firebase localId (UID)
        profiles_col = get_user_profiles_col()
        
        # Check if profile already exists (e.g. if DB got out of sync)
        existing = profiles_col.find_one({"uid": user_record.uid})
        if not existing:
            default_profile = {
                "uid": user_record.uid,
                "name": request.name,
                "phone": request.phone,
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
            profiles_col.insert_one(default_profile)
            logger.info(f"Seeded MongoDB profile for newly registered user UID: {user_record.uid}")
            
        return {
            "success": True,
            "uid": user_record.uid,
            "message": "User registered successfully."
        }
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login")
def login_user(request: LoginRequest):
    """Authenticate user credentials using Firebase Auth REST API."""
    if not FIREBASE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase API key not configured on the server."
        )
        
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": request.email,
        "password": request.password,
        "returnSecureToken": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        
        if response.status_code == 200:
            # Fetch profile details from MongoDB to return to frontend
            uid = res_data.get("localId")
            profiles_col = get_user_profiles_col()
            profile = profiles_col.find_one({"uid": uid})
            
            fb_name = res_data.get("displayName")
            if not profile:
                profile = {
                    "uid": uid,
                    "name": fb_name or "User",
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
                profiles_col.insert_one(profile)
            elif fb_name and profile.get("name") != fb_name:
                profiles_col.update_one({"uid": uid}, {"$set": {"name": fb_name}})
                profile["name"] = fb_name
            
            # Remove MongoDB internal ID from profile dict
            if "_id" in profile:
                profile.pop("_id")
                
            return {
                "success": True,
                "idToken": res_data.get("idToken"),
                "email": res_data.get("email"),
                "uid": uid,
                "name": fb_name or profile.get("name", "User"),
                "profile": profile
            }
        else:
            error_msg = res_data.get("error", {}).get("message", "Authentication failed.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Login failed: {error_msg}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login service temporarily unavailable: {str(e)}"
        )
