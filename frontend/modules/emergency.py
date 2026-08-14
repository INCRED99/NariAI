import streamlit as st
import os
import time
from datetime import datetime
import threading
import logging
import requests
from frontend.modules.api_client import api_post, api_get, api_post_file, BACKEND_URL

logger = logging.getLogger("nari.emergency")

IS_RENDER = True

def render_emergency():

    # Page Header
    st.markdown(
        """
        <div style='text-align: left; margin-bottom: 25px;'>
            <h1 style='margin: 0; font-size: 38px;'><span class='gradient-text'>Emergency Hub</span></h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                One-tap SOS dispatch, AI voice panic listeners, and custom text distress signals.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Initialize session states
    if "sos_triggered" not in st.session_state:
        st.session_state["sos_triggered"] = False
    if "sos_sent" not in st.session_state:
        st.session_state["sos_sent"] = False
    if "voice_listener_active" not in st.session_state:
        st.session_state["voice_listener_active"] = False
    if "stt_processing" not in st.session_state:
        st.session_state["stt_processing"] = False
    if "stt_result" not in st.session_state:
        st.session_state["stt_result"] = ""
    if "stt_urgency" not in st.session_state:
        st.session_state["stt_urgency"] = ""
    if "sos_sms_body" not in st.session_state:
        st.session_state["sos_sms_body"] = ""
    if "wa_opened" not in st.session_state:
        st.session_state["wa_opened"] = False

    # Check settings for custom GPS override, fallback to live session state coordinates if available
    user_lat = st.session_state.get("current_lat", 28.6273)
    user_lng = st.session_state.get("current_lng", 77.3725)
    calc_loc_val = st.session_state.get("current_address", "Your Location")



    # SOS Card layout
    if st.session_state["sos_sent"]:
        st.markdown('<div class="safety-card" style="text-align: center; max-width:600px; margin: 0 auto; padding: 30px;">', unsafe_allow_html=True)
        # Fetch current contacts from profile API
        profile_data = api_get("/profile")
        contacts = []
        if profile_data and "profile" in profile_data:
            contacts = profile_data["profile"].get("emergency_contacts", [])
        
        valid_contacts = [c for c in contacts if c.get("name") and c.get("phone")]
        contact_names = ", ".join([f"{c['name']} ({c['phone']})" for c in valid_contacts]) if valid_contacts else "your emergency contacts"
        
        st.markdown(
            f"""
            <div style="text-align:center;">
                <span class="material-icons-outlined" style="font-size: 80px; color: #FF9500; animation: pulse-sos 1.5s infinite;">warning</span>
                <h2 style="color: #FF9500; margin-top: 15px;">Emergency SOS Signal Active</h2>
                <p style="font-size:15px; color:var(--text-primary); margin-bottom: 25px; line-height:1.5;">
                    Distress summary generated. Open WhatsApp to send the alert to your emergency contacts:<br>
                    <strong style="color: #00C6FF; font-size:16px;">{contact_names}</strong>
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Display the message body to be sent
        body_sms = st.session_state.get("sos_sms_body", "")
        if not body_sms:
            situation_desc = st.session_state.get("sos_situation", "Urgent Distress SOS Signal Triggered.")
            body_sms = f"Emergency! I need help. I'm currently at {calc_loc_val} ({user_lat}, {user_lng}). Situation: {situation_desc}."
            
        # Append clickable Google Maps location URL
        maps_link = f"https://www.google.com/maps?q={user_lat:.6f},{user_lng:.6f}"
        if "google.com/maps" not in body_sms and "maps.google.com" not in body_sms:
            body_sms += f"\nLive Location: {maps_link}"
            
        st.markdown(
            f"""
            <div style="background:rgba(255, 149, 0, 0.08); border-radius:12px; padding:20px; width:100%; margin-bottom:25px; border:1px solid rgba(255, 149, 0, 0.3); text-align:left;">
                <p style="margin:0 0 8px 0; font-size:12px; font-weight:600; color:#FF9500; letter-spacing:1px; text-transform:uppercase;">📝 Pre-Typed distress message:</p>
                <p style="margin:0; font-size:14px; line-height:1.5; color:var(--text-primary); font-family: monospace; white-space: pre-wrap;">{body_sms}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Helper to construct WhatsApp URLs
        import urllib.parse
        
        # Clean helper for formatting country codes
        def clean_phone(phone):
            clean = "".join(filter(str.isdigit, phone))
            if len(clean) == 10:
                clean = "91" + clean
            elif len(clean) == 11 and clean.startswith("0"):
                clean = "91" + clean[1:]
            return clean

        # Build wa.me links — most reliable universal WhatsApp link (opens app on desktop/mobile, WhatsApp Web as fallback)
        wa_urls = []
        for c in contacts:
            ph = clean_phone(c.get("phone", ""))
            if ph:
                encoded = urllib.parse.quote(body_sms)
                wa_urls.append((c.get("name", "Contact"), c.get("relation", "Emergency Contact"), f"https://wa.me/{ph}?text={encoded}"))
                
        # Fallback if no valid contacts
        if not wa_urls:
            encoded = urllib.parse.quote(body_sms)
            wa_urls = [("Emergency Share", "Broadcast", f"https://wa.me/?text={encoded}")]

        import streamlit.components.v1 as components

        auto_open = not st.session_state.get("wa_opened", False)
        if auto_open:
            st.session_state["wa_opened"] = True

        # Build contact rows HTML
        contact_rows_html = ""
        for i, (name, rel, url) in enumerate(wa_urls):
            # Use target="_blank" so it opens in a new tab without cross-origin iframe security issues
            contact_rows_html += f"""
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.1);
                        border-radius:8px; padding:12px 18px; margin-bottom:10px;
                        display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong style="color:#FFFFFF; font-size:14px; display:block;">{name}</strong>
                    <span style="font-size:11px; color:#9E9EAF;">{rel}</span>
                </div>
                <a href="{url}"
                   target="_blank"
                   style="background-color:#25D366; color:white; padding:10px 20px;
                          border-radius:6px; text-decoration:none; font-size:13px;
                          font-weight:600; display:inline-block; cursor:pointer;">
                    💬 Send on WhatsApp
                </a>
            </div>"""

        if auto_open and wa_urls:
            first_url = wa_urls[0][2]  # wa.me URL
            first_name = wa_urls[0][0]
            
            import urllib.parse as _up
            parsed = _up.urlparse(first_url)
            phone_part = parsed.path.lstrip("/")
            text_part = _up.parse_qs(parsed.query).get("text", [""])[0]
            encoded_text = _up.quote(text_part)
            whatsapp_uri = f"whatsapp://send?phone={phone_part}&text={encoded_text}"
            
            # 1. Attempt automatic launch using a hidden iframe with the deep link.
            # This often bypasses popup blockers for custom protocols like whatsapp://
            import streamlit.components.v1 as components
            components.html(f'<iframe src="{whatsapp_uri}" style="display:none;"></iframe>', height=0)
            
            # 2. Provide a highly visible manual fallback button
            st.link_button(
                f"💬 Open WhatsApp → Send to {first_name}",
                first_url,
                use_container_width=True,
                type="primary"
            )

        total_height = 80 + len(wa_urls) * 75
        components.html(
            f"""<!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"></head>
            <body style="margin:0;padding:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
                <div style="background:rgba(37,211,102,0.08);border-radius:10px;padding:14px 18px;
                            border:1px solid rgba(37,211,102,0.3);margin-bottom:12px;">
                    <strong style="color:#25D366;font-size:14px;">💬 WhatsApp Dispatch Hub</strong>
                    <p style="margin:4px 0 0 0;font-size:12px;color:#9E9EAF;">
                        {"Launching WhatsApp... (or click the button below)" if auto_open else "Click below to send the pre-filled alert on WhatsApp."}
                    </p>
                </div>
                {contact_rows_html}
            </body>
            </html>""",
            height=total_height,
            scrolling=False
        )
            
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        
        if st.button("Reset SOS Status", width="stretch", key="reset_sos", type="primary"):
            filename = st.session_state.get("audio_filename", "")
            if filename:
                from frontend.modules.api_client import api_delete
                api_delete(f"/sos/delete-audio/{filename}")
                st.session_state["audio_filename"] = ""
            st.session_state["sos_sent"] = False
            st.session_state["sos_sms_body"] = ""
            st.session_state["wa_opened"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            st.markdown('<div class="safety-card" style="min-height: 420px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; padding: 25px;">', unsafe_allow_html=True)
            st.markdown("<h3 style='margin-top:0; font-size:20px; text-align:center;'>🚨 Emergency SOS Dispatch</h3>", unsafe_allow_html=True)
            
            st.markdown(
                """
                <div class="sos-outer" style="margin: 20px 0;">
                    <button class="sos-button" onclick="document.getElementById('hidden_sos_trigger').click();">
                        <span class="material-icons-outlined" style="font-size: 40px; margin-bottom:5px;">gpp_bad</span><br>SOS
                    </button>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Type distress message section
            custom_message = st.text_input("Type distress message (optional)", placeholder="E.g., Someone is following me near Block C...", key="sos_custom_message")
            
            # Hidden button mapped to CSS click action
            if st.button("🚨 TRIGGER SOS NOW", key="hidden_sos_trigger", width="stretch", type="primary"):
                situation_desc = custom_message if custom_message else "Urgent Distress SOS Signal Triggered by user."
                payload = {
                    "situation": situation_desc,
                    "location_name": calc_loc_val,
                    "latitude": user_lat,
                    "longitude": user_lng
                }
                res = api_post("/sos", payload)
                if res and res.get("success"):
                    st.session_state["sos_sms_body"] = res.get("sms_body", "")
                    st.session_state["sos_sent"] = True
                    st.session_state["wa_opened"] = False
                    st.rerun()
                else:
                    st.error("Failed to transmit SOS signal to emergency backend.")
                
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="safety-card" style="min-height: 420px; padding: 25px;">', unsafe_allow_html=True)
            st.markdown(
                """
                <h3 style='margin-top:0; font-size:20px;' class="icon-text-align">
                    <span class="material-icons-outlined" style="color: #FF9500;">bolt</span> Quick Auto-fill Messages
                </h3>
                <p style="color: var(--text-secondary); font-size:13px; margin-top:-5px; margin-bottom:20px;">
                    Tap any button below to instantly trigger an SOS with the selected message.
                </p>
                """,
                unsafe_allow_html=True
            )

            # Quick action buttons
            quick_msg = None
            if st.button("Help!", key="qa_help", use_container_width=True): quick_msg = "Help!"
            if st.button("Bachao!", key="qa_bachao", use_container_width=True): quick_msg = "Bachao!"
            if st.button("Emergency! Send Police.", key="qa_emergency", use_container_width=True): quick_msg = "Emergency! Send Police."
            if st.button("Someone is following me", key="qa_following", use_container_width=True): quick_msg = "Someone is following me"
            if st.button("I feel unsafe", key="qa_unsafe", use_container_width=True): quick_msg = "I feel unsafe"
            if st.button("Medical Emergency", key="qa_medical", use_container_width=True): quick_msg = "Medical Emergency"
            
            if quick_msg:
                payload = {
                    "situation": quick_msg,
                    "location_name": calc_loc_val,
                    "latitude": user_lat,
                    "longitude": user_lng
                }
                res = api_post("/sos", payload)
                if res and res.get("success"):
                    st.session_state["sos_sms_body"] = res.get("sms_body", "")
                    st.session_state["sos_situation"] = quick_msg
                    st.session_state["sos_sent"] = True
                    st.session_state["wa_opened"] = False
                    st.rerun()
                else:
                    st.error("Failed to transmit SOS signal to emergency backend.")
            st.markdown('</div>', unsafe_allow_html=True)
