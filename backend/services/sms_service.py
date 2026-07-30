import logging
import requests
import json
from requests.auth import HTTPBasicAuth
from backend.config import (
    SMS_PROVIDER,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
    MSG91_AUTH_KEY,
    MSG91_SENDER_ID,
    MSG91_ROUTE,
    TEXTLOCAL_API_KEY,
    TEXTLOCAL_SENDER,
    EXOTEL_ACCOUNT_SID,
    EXOTEL_AUTH_TOKEN,
    EXOTEL_FROM_NUMBER
)

logger = logging.getLogger("nari.sms")

def send_twilio_sms(to_phone: str, body: str) -> dict:
    """Send SMS via Twilio API."""
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
        raise ValueError("Missing Twilio credentials in environment.")
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = {
        "From": TWILIO_FROM_NUMBER,
        "To": to_phone,
        "Body": body
    }
    response = requests.post(
        url,
        data=data,
        auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        timeout=10
    )
    response.raise_for_status()
    return response.json()

def send_msg91_sms(to_phone: str, body: str) -> dict:
    """Send SMS via Msg91 HTTP API."""
    if not MSG91_AUTH_KEY:
        raise ValueError("Missing MSG91 auth key in environment.")
    
    url = "https://control.msg91.com/api/v5/sms"
    headers = {
        "authkey": MSG91_AUTH_KEY,
        "Content-Type": "application/json"
    }
    # MSG91 expects format without '+'
    clean_phone = to_phone.replace("+", "").replace(" ", "").strip()
    payload = {
        "route": MSG91_ROUTE,
        "sender": MSG91_SENDER_ID if MSG91_SENDER_ID else "NARISE",
        "sms": [
            {
                "message": body,
                "to": [clean_phone]
            }
        ]
    }
    response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def send_textlocal_sms(to_phone: str, body: str) -> dict:
    """Send SMS via Textlocal India API."""
    if not TEXTLOCAL_API_KEY:
        raise ValueError("Missing Textlocal API key in environment.")
    
    url = "https://api.textlocal.in/send/"
    clean_phone = to_phone.replace("+", "").replace(" ", "").strip()
    data = {
        "apikey": TEXTLOCAL_API_KEY,
        "numbers": clean_phone,
        "message": body,
        "sender": TEXTLOCAL_SENDER if TEXTLOCAL_SENDER else "TXTLCL"
    }
    response = requests.post(url, data=data, timeout=10)
    response.raise_for_status()
    res_json = response.json()
    if res_json.get("status") == "failure":
        raise Exception(f"Textlocal API error: {res_json}")
    return res_json

def send_exotel_sms(to_phone: str, body: str) -> dict:
    """Send SMS via Exotel API."""
    if not (EXOTEL_ACCOUNT_SID and EXOTEL_AUTH_TOKEN and EXOTEL_FROM_NUMBER):
        raise ValueError("Missing Exotel credentials in environment.")
    
    url = f"https://api.exotel.com/v1/Accounts/{EXOTEL_ACCOUNT_SID}/Sms/send.json"
    data = {
        "From": EXOTEL_FROM_NUMBER,
        "To": to_phone,
        "Body": body
    }
    response = requests.post(
        url,
        data=data,
        auth=HTTPBasicAuth(EXOTEL_ACCOUNT_SID, EXOTEL_AUTH_TOKEN),
        timeout=10
    )
    response.raise_for_status()
    return response.json()

def send_single_sms(to_phone: str, body: str, provider: str = None) -> dict:
    """Send an SMS to a single number using the configured or explicitly specified provider."""
    active_provider = (provider or SMS_PROVIDER or "mock").strip().lower()
    
    # Clean phone to normalize standard formats
    to_phone = to_phone.strip()
    
    try:
        if active_provider == "twilio":
            res = send_twilio_sms(to_phone, body)
            logger.info(f"SMS successfully sent via Twilio to {to_phone}")
            return {"success": True, "provider": "twilio", "response": res}
            
        elif active_provider == "msg91":
            res = send_msg91_sms(to_phone, body)
            logger.info(f"SMS successfully sent via Msg91 to {to_phone}")
            return {"success": True, "provider": "msg91", "response": res}
            
        elif active_provider == "textlocal":
            res = send_textlocal_sms(to_phone, body)
            logger.info(f"SMS successfully sent via Textlocal to {to_phone}")
            return {"success": True, "provider": "textlocal", "response": res}
            
        elif active_provider == "exotel":
            res = send_exotel_sms(to_phone, body)
            logger.info(f"SMS successfully sent via Exotel to {to_phone}")
            return {"success": True, "provider": "exotel", "response": res}
            
        else:
            # Mock mode / fallback simulation
            logger.warning(f"[MOCK SMS DISPATCH] To: {to_phone} | Body: {body}")
            return {"success": True, "provider": "mock", "message": "Simulated SMS sent successfully"}
            
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_phone} via provider '{active_provider}': {e}")
        # Return fallback status rather than crashing backend, so app is resilient
        return {"success": False, "provider": active_provider, "error": str(e)}

def broadcast_emergency_sms(contacts: list, base_message: str, latitude: float = None, longitude: float = None) -> list:
    """
    Broadcasts emergency messages to a list of contacts.
    Automatically appends a clickable Google Maps live tracking URL if coordinates are available.
    """
    final_body = base_message
    if latitude is not None and longitude is not None:
        maps_link = f"https://maps.google.com/?q={latitude:.6f},{longitude:.6f}"
        if "maps.google.com" not in final_body:
            final_body += f"\nLive Map: {maps_link}"
            
    results = []
    for contact in contacts:
        phone = contact.get("phone")
        name = contact.get("name", "Emergency Contact")
        if not phone:
            logger.warning(f"Contact '{name}' is missing a phone number. Skipping SMS.")
            continue
            
        personal_body = f"Hello {name}, {final_body}"
        logger.warning(f"Dispatching SMS to {name} ({phone})")
        res = send_single_sms(phone, personal_body)
        results.append({
            "name": name,
            "phone": phone,
            "success": res.get("success", False),
            "provider": res.get("provider", "mock"),
            "error": res.get("error")
        })
        
    return results
