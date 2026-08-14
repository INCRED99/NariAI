import streamlit as st
import os
import sys

# Ensure workspace root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set page config
st.set_page_config(
    page_title="Nari - AI Women's Safety Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session States
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = True
if "active_page" not in st.session_state:
    st.session_state["active_page"] = "Dashboard"

# Load persistent credentials from query parameters if present
q_params = st.query_params
if "uid" in q_params and "idToken" in q_params:
    st.session_state["authenticated"] = True
    st.session_state["idToken"] = q_params["idToken"]
    st.session_state["uid"] = q_params["uid"]
    st.session_state["user_email"] = q_params.get("email", "")
    st.session_state["user_name"] = q_params.get("name", "User")
else:
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

# Load environment keys from .env if present
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(dotenv_path):
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

if "gemini_key" not in st.session_state:
    st.session_state["gemini_key"] = os.getenv("GEMINI_API_KEY", "")
if "gmaps_key" not in st.session_state:
    st.session_state["gmaps_key"] = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Load modules
from modules.dashboard import render_dashboard
from modules.ai_assistant import render_ai_assistant
from modules.route_safety import render_route_safety
from modules.nearby_places import render_nearby_places
from modules.emergency import render_emergency
from modules.profile import render_profile
from modules.settings import render_settings
from modules.incident_reporting import render_incident_reporting

st.markdown(
    """
    <img src="x" onerror="
        var url = new URL(window.location.href);
        if (!url.searchParams.has('lat') && !url.searchParams.has('geo_tried') && navigator.geolocation) {
            url.searchParams.set('geo_tried', '1');
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    url.searchParams.set('lat', position.coords.latitude);
                    url.searchParams.set('lng', position.coords.longitude);
                    window.history.pushState(null, '', url.href);
                    var btns = document.querySelectorAll('button');
                    for(var i=0; i<btns.length; i++) {
                        if(btns[i].innerText.indexOf('NariHiddenGeoTrigger') !== -1) {
                            btns[i].click();
                            break;
                        }
                    }
                },
                function(error) {
                    window.history.pushState(null, '', url.href);
                    var btns = document.querySelectorAll('button');
                    for(var i=0; i<btns.length; i++) {
                        if(btns[i].innerText.indexOf('NariHiddenGeoTrigger') !== -1) {
                            btns[i].click();
                            break;
                        }
                    }
                },
                {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
            );
        }
    " style="display:none;">
    <div style='height:0; width:0; overflow:hidden; opacity:0; position:absolute; z-index:-1;'>
    """, unsafe_allow_html=True
)
if st.button("NariHiddenGeoTrigger", key="hidden_geo"): pass
st.markdown("</div>", unsafe_allow_html=True)

# Check query params for coordinates
q_params = st.query_params
if "lat" in q_params and "lng" in q_params:
    new_lat = float(q_params["lat"])
    new_lng = float(q_params["lng"])
    if st.session_state.get("current_lat") != new_lat or st.session_state.get("current_lng") != new_lng:
        st.session_state["current_lat"] = new_lat
        st.session_state["current_lng"] = new_lng
        
        # Immediately fetch from reverse-geocode endpoint
        from frontend.modules.api_client import api_get
        g_res = api_get("/nearby-places/reverse-geocode", {"latitude": new_lat, "longitude": new_lng})
        if g_res and "address" in g_res:
            st.session_state["current_address"] = g_res["address"]

# Fallback if coordinates are not available yet (e.g. user denied permission or waiting)
if "current_lat" not in st.session_state:
    st.session_state["current_lat"] = 28.6273
    st.session_state["current_lng"] = 77.3725
    st.session_state["current_address"] = "Your Location"

# Resolve address string using Google Maps reverse-geocoding API if coordinates changed
if "current_address" not in st.session_state or st.session_state.get("current_address") == "Your Location":
    if "current_lat" in st.session_state and "current_lng" in st.session_state:
        from frontend.modules.api_client import api_get
        g_res = api_get("/nearby-places/reverse-geocode", {
            "latitude": st.session_state["current_lat"], 
            "longitude": st.session_state["current_lng"]
        })
        if g_res and "address" in g_res:
            st.session_state["current_address"] = g_res["address"]


# Styling theme variables injection
is_dark = st.session_state["dark_mode"]
if is_dark:
    theme_css = """
    <style>
    :root {
        --bg-primary: #0D0B1C;
        --bg-card: rgba(26, 21, 44, 0.65);
        --text-primary: #F6F5FB;
        --text-secondary: #9E9EAF;
        --border-color: rgba(255, 255, 255, 0.08);
        --shadow-color: rgba(0, 0, 0, 0.4);
        --accent-glow: rgba(122, 92, 255, 0.3);
        --sidebar-bg: #151030;
    }
    .stApp {
        background-color: #0D0B1C !important;
        color: #F6F5FB !important;
    }
    div[data-testid="stSidebar"] {
        background-color: #151030 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    </style>
    """
else:
    theme_css = """
    <style>
    :root {
        --bg-primary: #F6F5FB;
        --bg-card: rgba(255, 255, 255, 0.75);
        --text-primary: #1A1D35;
        --text-secondary: #686C80;
        --border-color: rgba(122, 92, 255, 0.15);
        --shadow-color: rgba(31, 38, 135, 0.05);
        --accent-glow: rgba(122, 92, 255, 0.15);
        --sidebar-bg: #EAE8F5;
    }
    .stApp {
        background-color: #F6F5FB !important;
        color: #1A1D35 !important;
    }
    div[data-testid="stSidebar"] {
        background-color: #EAE8F5 !important;
        border-right: 1px solid rgba(122, 92, 255, 0.15) !important;
    }
    </style>
    """

# Inject custom variables
st.markdown(theme_css, unsafe_allow_html=True)

# Load global CSS
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
with open(css_path, "r", encoding="utf-8") as f:
    global_css = f.read()
st.markdown(f"<style>{global_css}</style>", unsafe_allow_html=True)

# Authentication access gate
if not st.session_state["authenticated"]:
    from modules.auth import render_auth_page
    render_auth_page()
    st.stop()

# Sidebar Design
st.sidebar.markdown(
    """
    <div style='text-align: center; padding: 15px 0;'>
        <span class='material-icons-outlined' style='font-size: 45px; background: linear-gradient(135deg, #7A5CFF 0%, #00C6FF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>shield</span>
        <h2 style='margin: 10px 0 0 0; font-size: 24px; font-weight:800; background: linear-gradient(135deg, #7A5CFF 0%, #00C6FF 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>NARI AI</h2>
        <p style='color: var(--text-secondary); font-size: 12px; margin-top:2px;'>AI Safety & Security Hub</p>
    </div>
    <hr style='border: 0; border-top: 1px solid var(--border-color); margin-bottom: 20px;'>
    """, 
    unsafe_allow_html=True
)

menu_mapping = {
    "📊 Dashboard": "Dashboard",
    "💬 AI Assistant": "AI Assistant",
    "🗺️ Safe Route": "Safe Route",
    "📍 Nearby Safe Places": "Nearby Safe Places",
    "🚨 Emergency": "Emergency",
    "👤 Profile": "Profile",
    "⚙️ Settings": "Settings"
}

# Find active index (handling cases where active page is not in sidebar, e.g. Incident Reporting)
active_page = st.session_state.get("active_page", "Dashboard")
if active_page in menu_mapping.values():
    active_idx = list(menu_mapping.values()).index(active_page)
else:
    active_idx = None

# If the active page is not in the sidebar (like Incident Reporting), we don't select any radio button pre-selection,
# or we let user select Dashboard to clear it. In Streamlit, radio needs a default index.
# We can default to first item, but we must update page state if the user clicks the radio.
selected_display = st.sidebar.radio(
    "Navigation Menu",
    list(menu_mapping.keys()),
    index=active_idx if active_idx is not None else 0,
    label_visibility="collapsed"
)

# Only override if the user clicks sidebar. If they were routed to Incident Reporting,
# we only change page if the user selects a new sidebar option (i.e. selected_display matches active index,
# but since active index was None, we know the user is on Incident Reporting, and clicking the sidebar should route them out).
if active_idx is None:
    # If on Incident Reporting, and radio shows Dashboard (default), and user clicks it, it should switch.
    # To detect click, check if the selected radio corresponds to the page state.
    if menu_mapping[selected_display] != "Dashboard":
        st.session_state["active_page"] = menu_mapping[selected_display]
        st.rerun()
    # If the user clicks Dashboard while on Incident Reporting, switch to Dashboard:
    # (Since index defaults to 0, if they want Dashboard, we need to let them click it or click something else first.
    # Let's add a back button on the Incident Reporting page, which is very natural, or just handle it here.)
    # A simple back button on Incident Reporting is the most clean UX.
else:
    st.session_state["active_page"] = menu_mapping[selected_display]

# Sidebar Footer / Theme quick switcher
st.sidebar.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
quick_theme = st.sidebar.toggle("Dark Mode Toggle", value=st.session_state["dark_mode"], key="sidebar_dark_toggle")
if quick_theme != st.session_state["dark_mode"]:
    st.session_state["dark_mode"] = quick_theme
    st.rerun()

st.sidebar.markdown("<hr style='border:0; border-top: 1px solid var(--border-color); margin:10px 0;'>", unsafe_allow_html=True)
if st.sidebar.button("🚪 Logout", key="logout_btn", width="stretch"):
    st.session_state["authenticated"] = False
    st.session_state["idToken"] = ""
    st.session_state["uid"] = ""
    st.session_state["user_email"] = ""
    st.session_state["user_name"] = ""
    st.session_state["wa_opened"] = False
    st.query_params.clear()
    st.toast("Logged out successfully.")
    st.rerun()

st.sidebar.markdown(
    """
    <div style='padding: 20px 10px; font-size: 11px; color: var(--text-secondary); line-height: 1.4;'>
        Nari Safety v1.0.0 (Production Mock)<br>
        © 2026 Nari Secure Inc.
    </div>
    """,
    unsafe_allow_html=True
)

# Render Page
active = st.session_state["active_page"]
if active == "Dashboard":
    render_dashboard()
elif active == "AI Assistant":
    render_ai_assistant()
elif active == "Safe Route":
    render_route_safety()
elif active == "Nearby Safe Places":
    render_nearby_places()
elif active == "Emergency":
    render_emergency()
elif active == "Profile":
    render_profile()
elif active == "Settings":
    render_settings()
elif active == "Incident Reporting":
    # Let's add a tiny back navigation
    if st.button("← Back to Dashboard", key="back_to_dash"):
        st.session_state["active_page"] = "Dashboard"
        st.rerun()
    render_incident_reporting()
