import streamlit as st
import requests
import logging

logger = logging.getLogger("nari.frontend_client")
BACKEND_URL = "http://127.0.0.1:8000/api"

def get_headers():
    """Build request headers, injecting API keys from streamlit state if available."""
    headers = {}
    
    gemini_key = st.session_state.get("gemini_key", "").strip()
    if gemini_key:
        headers["X-Gemini-Key"] = gemini_key
        
    gmaps_key = st.session_state.get("gmaps_key", "").strip()
    if gmaps_key:
        headers["X-Gmaps-Key"] = gmaps_key
        
    id_token = st.session_state.get("idToken", "").strip()
    if id_token:
        headers["Authorization"] = f"Bearer {id_token}"
        
    return headers

def check_token_expiry(response):
    """Automatically logs the user out if their Firebase token is detected as expired."""
    try:
        if response.status_code in [401, 500]:
            body = response.text.lower()
            if "token expired" in body or "expired" in body or "verification failed" in body:
                st.session_state["authenticated"] = False
                st.session_state["idToken"] = ""
                st.session_state["uid"] = ""
                st.session_state["user_email"] = ""
                st.session_state["user_name"] = ""
                st.query_params.clear()
                st.rerun()
    except Exception:
        pass

def api_get(endpoint, params=None):
    """Perform a GET request to the FastAPI backend."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            check_token_expiry(response)
            logger.error(f"API GET {endpoint} failed: Status {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"API GET connection error to {url}: {e}")
        return None

def api_post(endpoint, data=None):
    """Perform a POST request to the FastAPI backend."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        response = requests.post(url, headers=get_headers(), json=data, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            check_token_expiry(response)
            logger.error(f"API POST {endpoint} failed: Status {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"API POST connection error to {url}: {e}")
        return None

def api_post_file(endpoint, files, data=None):
    """Perform a POST request with file uploads (multipart)."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        # Extract headers except Content-Type as requests sets boundaries automatically for files
        headers = get_headers()
        response = requests.post(url, headers=headers, files=files, data=data, timeout=20)
        if response.status_code == 200:
            return response.json()
        else:
            check_token_expiry(response)
            logger.error(f"API File POST {endpoint} failed: Status {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"API File POST connection error to {url}: {e}")
        return None

def api_delete(endpoint):
    """Perform a DELETE request to the FastAPI backend."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        response = requests.delete(url, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            check_token_expiry(response)
            logger.error(f"API DELETE {endpoint} failed: Status {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"API DELETE connection error to {url}: {e}")
        return None
