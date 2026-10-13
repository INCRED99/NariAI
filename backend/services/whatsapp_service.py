import logging
import requests
import urllib.parse
from backend.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    CALLMEBOT_API_KEYS,
)

logger = logging.getLogger("nari.whatsapp")


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to international format for WhatsApp (digits only, with country code)."""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    # Remove leading + for wa.me format
    if phone.startswith("+"):
        phone = phone[1:]
    # If Indian number without country code (starts with 6-9 and is 10 digits)
    if len(phone) == 10 and phone[0] in "6789":
        phone = "91" + phone
    return phone


def generate_whatsapp_link(phone: str, message: str) -> str:
    """Generate a clickable WhatsApp deep link (wa.me URL) for a contact."""
    clean_phone = _normalize_phone(phone)
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_msg}"


def send_via_twilio_whatsapp(to_phone: str, body: str) -> dict:
    """Send WhatsApp message via Twilio WhatsApp Business API."""
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
        return {"success": False, "provider": "twilio_whatsapp", "error": "Twilio WhatsApp credentials not configured"}

    clean_phone = _normalize_phone(to_phone)
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = {
        "From": f"whatsapp:{TWILIO_WHATSAPP_FROM}",
        "To": f"whatsapp:+{clean_phone}",
        "Body": body
    }
    try:
        from requests.auth import HTTPBasicAuth
        response = requests.post(
            url, data=data,
            auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"WhatsApp sent via Twilio to +{clean_phone}")
        return {"success": True, "provider": "twilio_whatsapp", "response": response.json()}
    except Exception as e:
        logger.error(f"Twilio WhatsApp send failed: {e}")
        return {"success": False, "provider": "twilio_whatsapp", "error": str(e)}


def send_via_callmebot(to_phone: str, body: str, apikey: str = None) -> dict:
    """
    Send WhatsApp message via CallMeBot free API.
    Requires recipient to first register by sending:
      'I allow callmebot to send me messages'
    to +34 644 47 47 38 on WhatsApp.
    """
    if not apikey:
        # Try to find the API key for this phone number from config
        clean_phone = _normalize_phone(to_phone)
        apikey = CALLMEBOT_API_KEYS.get(clean_phone, "")
    
    if not apikey:
        return {"success": False, "provider": "callmebot", "error": f"No CallMeBot API key for {to_phone}. Recipient must register first."}
    
    clean_phone = _normalize_phone(to_phone)
    encoded_msg = urllib.parse.quote(body)
    url = f"https://api.callmebot.com/whatsapp.php?phone=+{clean_phone}&text={encoded_msg}&apikey={apikey}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "Message queued" in response.text:
            logger.info(f"WhatsApp sent via CallMeBot to +{clean_phone}")
            return {"success": True, "provider": "callmebot", "response": response.text}
        else:
            logger.warning(f"CallMeBot response: {response.status_code} — {response.text[:200]}")
            return {"success": False, "provider": "callmebot", "error": f"Unexpected response: {response.text[:200]}"}
    except Exception as e:
        logger.error(f"CallMeBot WhatsApp send failed: {e}")
        return {"success": False, "provider": "callmebot", "error": str(e)}


def send_whatsapp_message(to_phone: str, body: str) -> dict:
    """
    Send a WhatsApp message using the best available provider.
    Priority: Twilio WhatsApp → CallMeBot → Generate wa.me link (fallback).
    """
    # 1. Try Twilio WhatsApp
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM:
        result = send_via_twilio_whatsapp(to_phone, body)
        if result["success"]:
            return result
        logger.warning(f"Twilio WhatsApp failed for {to_phone}, trying CallMeBot...")

    # 2. Try CallMeBot
    clean_phone = _normalize_phone(to_phone)
    callmebot_key = CALLMEBOT_API_KEYS.get(clean_phone, "")
    if callmebot_key:
        result = send_via_callmebot(to_phone, body, apikey=callmebot_key)
        if result["success"]:
            return result
        logger.warning(f"CallMeBot failed for {to_phone}, generating wa.me link...")

    # 3. Fallback: generate wa.me link for frontend-driven sending
    wa_link = generate_whatsapp_link(to_phone, body)
    logger.warning(f"[WHATSAPP LINK GENERATED] To: {to_phone} | Link: {wa_link}")
    return {
        "success": True,
        "provider": "wa_link",
        "wa_link": wa_link,
        "message": "WhatsApp link generated. User can tap to send."
    }


def broadcast_emergency_whatsapp(contacts: list, base_message: str, latitude: float = None, longitude: float = None) -> list:
    """
    Broadcast emergency WhatsApp messages to all contacts.
    Returns list of results with wa.me links for frontend use.
    """
    final_body = base_message
    if latitude is not None and longitude is not None:
        maps_link = f"https://www.openstreetmap.org/?mlat={latitude:.6f}&mlon={longitude:.6f}#map=18/{latitude:.6f}/{longitude:.6f}"
        if "openstreetmap.org" not in final_body:
            final_body += f"\nLive Map: {maps_link}"

    results = []
    for contact in contacts:
        phone = contact.get("phone")
        name = contact.get("name", "Emergency Contact")
        if not phone:
            logger.warning(f"Contact '{name}' is missing a phone number. Skipping WhatsApp.")
            continue

        personal_body = f"🚨 NARI SOS ALERT for you, {name}!\n\n{final_body}"
        logger.warning(f"Dispatching WhatsApp to {name} ({phone})")
        
        res = send_whatsapp_message(phone, personal_body)
        
        # Always generate the wa.me link for frontend backup
        wa_link = generate_whatsapp_link(phone, personal_body)
        
        results.append({
            "name": name,
            "phone": phone,
            "success": res.get("success", False),
            "provider": res.get("provider", "wa_link"),
            "wa_link": wa_link,
            "error": res.get("error")
        })

    return results
