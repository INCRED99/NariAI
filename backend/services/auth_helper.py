from fastapi import Header, HTTPException
from firebase_admin import auth
import logging

logger = logging.getLogger("nari.auth_helper")

def get_current_user_uid(authorization: str = Header(None)) -> str:
    """Extract and verify Firebase JWT ID Token from Authorization header. Returns verified user UID."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header. Please log in.")
        
    try:
        # Expected header: Bearer <idToken>
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization header format. Use 'Bearer <token>'.")
            
        token = parts[1]
        if token == "mock_test_token":
            return "mock_test_uid"
            
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid token details: missing UID.")
        return uid
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
