import streamlit as st
import os
import time
from datetime import datetime
import threading
import logging
import requests
from frontend.modules.api_client import api_post, api_get, api_post_file, BACKEND_URL

logger = logging.getLogger("nari.emergency")

IS_RENDER = os.environ.get("RENDER") == "true"
GLOBAL_THREADS = {}
GLOBAL_PANIC_TRIGGERS = {}
LATEST_MICROPHONE_AUDIO = {}

# speech_recognition requires pyaudio (system mic) — only import on non-Render environments
if not IS_RENDER:
    try:
        import speech_recognition as sr
        SR_AVAILABLE = True
    except ImportError:
        SR_AVAILABLE = False
        logger.warning("speech_recognition/pyaudio not available. Server-side mic listener disabled.")
else:
    SR_AVAILABLE = False

def bg_mic_listener(uid, user_lat, user_lng, calc_loc_val, safe_word, id_token):
    if not SR_AVAILABLE:
        logger.warning("bg_mic_listener called but speech_recognition is not available. Skipping.")
        return
    import traceback
    try:
        logger.info("bg_mic_listener thread execution starting...")
        print("\n[THREAD DEBUG] Starting background voice listener thread...")
        
        headers = {}
        if id_token:
            headers["Authorization"] = f"Bearer {id_token}"
        
        r = sr.Recognizer()
        r.energy_threshold = 150  # Highly sensitive threshold for normal speech
        r.dynamic_energy_threshold = False  # Fixed threshold to avoid desensitization
        
        print("[THREAD DEBUG] Initializing microphone...")
        mic = sr.Microphone()
        
        # Test opening the microphone once to trigger taskbar icon and verify access
        print("[THREAD DEBUG] Verifying microphone access...")
        with mic as source:
            pass
            
        logger.info("Background Voice SOS listener thread started.")
        print("[THREAD DEBUG] Microphone successfully opened! Active listening running...")
        
        distress_keywords = ["help", "save me", "bachao", "emergency", "police", "scream", "danger", "follow", "accident", "stop"]
        if safe_word:
            distress_keywords.append(safe_word.lower())

        # Continuous loop while active
        while True:
            # Check active state
            if f"voice_thread_{uid}" not in GLOBAL_THREADS:
                print("[THREAD DEBUG] Thread terminated externally (Stop Listener clicked).")
                break
                
            try:
                print("[THREAD DEBUG] Listening for vocal input...")
                with mic as source:
                    audio = r.listen(source, timeout=3, phrase_time_limit=4)
                
                LATEST_MICROPHONE_AUDIO[uid] = audio.get_wav_data()
                print("[THREAD DEBUG] Speech captured! Sending to transcription...")
                text = r.recognize_google(audio).lower()
                print(f"[THREAD DEBUG] Google Speech transcribed: '{text}'")
                
                # Check for distress keywords
                found_panic = False
                for kw in distress_keywords:
                    if kw in text:
                        found_panic = True
                        break
                        
                if found_panic:
                    print(f"[THREAD DEBUG] DISTRESS PHRASE DETECTED: '{text}'! Dispatching SOS...")
                    
                    # Upload captured audio in-memory to backend to host publicly for emergency contacts
                    audio_url = ""
                    filename = ""
                    try:
                        wav_data = audio.get_wav_data()
                        files = {"file": ("sos_audio.wav", wav_data, "audio/wav")}
                        upload_res = requests.post(f"{BACKEND_URL}/sos/upload-audio", files=files, headers=headers, timeout=6)
                        if upload_res.status_code == 200:
                            upload_data = upload_res.json()
                            audio_url = upload_data.get("audio_url", "")
                            filename = upload_data.get("filename", "")
                            print(f"[THREAD DEBUG] Emergency audio uploaded successfully: {audio_url}")
                        else:
                            print(f"[THREAD DEBUG] Emergency audio upload failed: {upload_res.status_code}")
                    except Exception as upload_err:
                        print(f"[THREAD DEBUG] Failed to upload emergency audio: {upload_err}")
                        
                    situation_text = f"Voice SOS trigger: '{text}'"
                    if audio_url:
                        situation_text += f"\nLive Audio Alert: {audio_url}"
                        
                    payload = {
                        "situation": situation_text,
                        "location_name": calc_loc_val,
                        "latitude": user_lat,
                        "longitude": user_lng,
                        "battery_level": 85
                    }
                    
                    sms_body = ""
                    try:
                        response = requests.post(f"{BACKEND_URL}/sos", headers=headers, json=payload, timeout=12)
                        if response.status_code == 200:
                            res = response.json()
                            sms_body = res.get("sms_body", "")
                            print("[THREAD DEBUG] SOS posted to MongoDB successfully.")
                        else:
                            print(f"[THREAD DEBUG] SOS post failed with status code: {response.status_code}")
                            sms_body = f"Emergency! Spoken threat detected: '{text}' at {calc_loc_val}."
                            if audio_url:
                                sms_body += f"\nAudio: {audio_url}"
                    except Exception as post_err:
                        print(f"[THREAD DEBUG] SOS post error: {post_err}")
                        sms_body = f"Emergency! Spoken threat detected: '{text}' at {calc_loc_val}."
                        if audio_url:
                            sms_body += f"\nAudio: {audio_url}"
                        
                    # Put inside shared global triggers
                    GLOBAL_PANIC_TRIGGERS[uid] = {
                        "transcript": text,
                        "sms_body": sms_body,
                        "filename": filename
                    }
                    break  # Stop thread on trigger
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                print("[THREAD DEBUG] Speech unrecognizable (ambient noise or silence).")
                continue
            except Exception as loop_ex:
                print(f"[THREAD DEBUG] Error in listening loop: {loop_ex}")
                time.sleep(1)
    except Exception as e:
        print(f"[THREAD DEBUG] CRITICAL THREAD CRASH: {e}")
        print(traceback.format_exc())
        logger.error(f"Background thread crashed: {e}")
        
    # Clean up thread reference on exit
    GLOBAL_THREADS.pop(f"voice_thread_{uid}", None)
    print("[THREAD DEBUG] Listener thread stopped and references cleaned.")
    logger.info("Background Voice SOS listener thread stopped.")

def render_emergency():
    # Check background voice panic triggers
    uid = st.session_state.get("uid", "default_user")
    if uid in GLOBAL_PANIC_TRIGGERS:
        trigger_data = GLOBAL_PANIC_TRIGGERS.pop(uid)
        st.session_state["sos_sms_body"] = trigger_data["sms_body"]
        st.session_state["sos_sent"] = True
        st.session_state["wa_opened"] = False
        st.session_state["audio_filename"] = trigger_data.get("filename", "")
        st.session_state["voice_listener_active"] = False
        GLOBAL_THREADS.pop(f"voice_thread_{uid}", None)
        st.rerun()

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
    if "connaught" in calc_loc_val.lower() or "cp" in calc_loc_val.lower():
        user_lat = 28.6304
        user_lng = 77.2177



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
            # wa.me URL for the button click (opens WhatsApp Web or app)
            contact_rows_html += f"""
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.1);
                        border-radius:8px; padding:12px 18px; margin-bottom:10px;
                        display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong style="color:#FFFFFF; font-size:14px; display:block;">{name}</strong>
                    <span style="font-size:11px; color:#9E9EAF;">{rel}</span>
                </div>
                <a href="{url}"
                   onclick="window.top.location.href=this.href; return false;"
                   style="background-color:#25D366; color:white; padding:10px 20px;
                          border-radius:6px; text-decoration:none; font-size:13px;
                          font-weight:600; display:inline-block; cursor:pointer;">
                    💬 Send on WhatsApp
                </a>
            </div>"""

        # Auto-open strategy:
        # 1. Try whatsapp:// deep link first — opens desktop app directly if installed
        # 2. After 2s fallback to wa.me — opens WhatsApp Web if app didn't handle it
        auto_nav_js = ""
        if auto_open and wa_urls:
            first_url = wa_urls[0][2]  # wa.me URL
            # Extract phone and text from wa.me URL to build whatsapp:// URI
            # wa.me URL format: https://wa.me/PHONE?text=MSG
            import urllib.parse as _up
            parsed = _up.urlparse(first_url)
            phone_part = parsed.path.lstrip("/")
            text_part = _up.parse_qs(parsed.query).get("text", [""])[0]
            encoded_text = _up.quote(text_part)
            whatsapp_uri = f"whatsapp://send?phone={phone_part}&text={encoded_text}"

            auto_nav_js = f"""
                // Try whatsapp:// deep link — opens desktop app if installed
                var deepLink = "{whatsapp_uri}";
                var webLink = "{first_url}";
                
                // Use hidden iframe to attempt deep link without navigating away
                var iframe = document.createElement('iframe');
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
                
                var appOpened = false;
                
                // Listen for page blur — if app opened, page loses focus
                window.top.addEventListener('blur', function() {{
                    appOpened = true;
                }}, {{ once: true }});
                
                iframe.src = deepLink;
                
                // After 2.5s, if app didn't open (no blur), redirect to wa.me web
                setTimeout(function() {{
                    if (!appOpened) {{
                        window.top.location.href = webLink;
                    }}
                }}, 2500);
            """

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
                <script>
                    {auto_nav_js}
                </script>
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
                    "longitude": user_lng,
                    "battery_level": 84
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
                    <span class="material-icons-outlined" style="color: #FF3B30;">mic</span> Voice SOS Listener
                </h3>
                <p style="color: var(--text-secondary); font-size:13px; margin-top:-5px; margin-bottom:20px;">
                    Background vocal alarm listener. Active monitoring transcribes your voice via Whisper AI to instantly recognize emergencies.
                </p>
                """,
                unsafe_allow_html=True
            )
            
            # Micro active state indicator
            is_listening = st.session_state["voice_listener_active"]
            mic_class = "panic-mic-active" if is_listening else ""
            btn_label = "🔴 Stop Listener" if is_listening else "🎤 Activate Safety Listener"
            thread_key = f"voice_thread_{uid}"
            
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:20px; padding:15px; background:rgba(255,255,255,0.03); border-radius:12px; border:1px solid var(--border-color); margin-bottom:25px;">
                    <span class="material-icons-outlined {mic_class}" style="font-size:36px; color:#9E9EAF;">settings_voice</span>
                    <div>
                        <strong style="font-size:14px; display:block;">Safety Mic Status</strong>
                        <span style="font-size:12px; color:var(--text-secondary);">{ "🟢 Active Listening - Monitoring..." if is_listening else "Standby - Listener inactive" }</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Retrieve user profile info for background thread
            profile_data = api_get("/profile")
            profile_db = profile_data.get("profile", {}) if profile_data else {}
            contacts = profile_db.get("emergency_contacts", [])
            safe_word = profile_db.get("safe_word", "Blue Moon")
            
            if st.button(btn_label, key="toggle_voice_listener", width="stretch", type="primary" if is_listening else "secondary"):
                if is_listening:
                    # User clicked "Stop Listener" -> trigger SOS immediately!
                    st.session_state["voice_listener_active"] = False
                    GLOBAL_THREADS.pop(thread_key, None)
                    
                    if not IS_RENDER:
                        # Upload the last captured voice audio clip if available (server-mic mode only)
                        wav_data = LATEST_MICROPHONE_AUDIO.pop(uid, None)
                        audio_url = ""
                        filename = ""
                        if wav_data:
                            try:
                                import requests
                                from frontend.modules.api_client import BACKEND_URL
                                headers = {}
                                id_token = st.session_state.get("idToken")
                                if id_token:
                                    headers["Authorization"] = f"Bearer {id_token}"
                                files = {"file": ("sos_audio.wav", wav_data, "audio/wav")}
                                upload_res = requests.post(f"{BACKEND_URL}/sos/upload-audio", files=files, headers=headers, timeout=5)
                                if upload_res.status_code == 200:
                                    upload_data = upload_res.json()
                                    audio_url = upload_data.get("audio_url", "")
                                    filename = upload_data.get("filename", "")
                            except Exception as upload_err:
                                logger.error(f"Failed uploading final audio clip: {upload_err}")
                                
                        situation_text = "Voice listener stopped manually by user (SOS Alert)."
                        if audio_url:
                            situation_text += f"\nLive Audio Alert: {audio_url}"
                            
                        payload = {
                            "situation": situation_text,
                            "location_name": calc_loc_val,
                            "latitude": user_lat,
                            "longitude": user_lng,
                            "battery_level": 85
                        }
                        res = api_post("/sos", payload)
                        if res and res.get("success"):
                            st.session_state["sos_sms_body"] = res.get("sms_body", "")
                            st.session_state["sos_sent"] = True
                            st.session_state["wa_opened"] = False
                            st.session_state["audio_filename"] = filename
                else:
                    # User clicked "Activate Safety Listener"
                    st.session_state["voice_listener_active"] = True
                    # On Render (hosted), skip server-side mic thread — browser Web Speech API handles it below
                    if not IS_RENDER and SR_AVAILABLE and thread_key not in GLOBAL_THREADS:
                        id_token = st.session_state.get("idToken", "")
                        t = threading.Thread(
                            target=bg_mic_listener,
                            args=(uid, user_lat, user_lng, calc_loc_val, safe_word, id_token),
                            daemon=True
                        )
                        GLOBAL_THREADS[thread_key] = t
                        t.start()
                st.rerun()
                
            if is_listening:
                import streamlit.components.v1 as components
                import json

                # Check if browser mic already triggered a panic via query param
                q = st.query_params
                if q.get("panic") == "1":
                    transcript = q.get("transcript", "distress detected")
                    # Clear the param immediately to avoid re-triggering on rerun
                    st.query_params.pop("panic", None)
                    st.query_params.pop("transcript", None)

                    last_mic_trigger = st.session_state.get("last_mic_trigger_time", 0)
                    now_ts = int(time.time() * 1000)
                    if now_ts > last_mic_trigger + 3000:
                        st.session_state["last_mic_trigger_time"] = now_ts
                        st.toast(f"🚨 Vocal Panic Detected: '{transcript}'", icon="🚨")
                        payload = {
                            "situation": f"Voice SOS listener detected: '{transcript}'",
                            "location_name": calc_loc_val,
                            "latitude": user_lat,
                            "longitude": user_lng,
                            "battery_level": 85
                        }
                        res = api_post("/sos", payload)
                        if res and res.get("success"):
                            st.session_state["sos_sms_body"] = res.get("sms_body", "")
                            st.session_state["sos_sent"] = True
                            st.session_state["wa_opened"] = False
                            st.session_state["voice_listener_active"] = False
                            st.rerun()

                # Setup distress keywords
                distress_keywords = ["help", "save me", "bachao", "emergency", "police", "scream", "danger", "follow", "accident", "stop", "bachao bachao", "madad"]
                if safe_word:
                    distress_keywords.append(safe_word.lower())

                keywords_js = json.dumps(distress_keywords)
                disp_safe_word = safe_word if safe_word else "None"

                # Get the current page URL to append panic params
                current_url_js = "window.top.location.href.split('?')[0]"

                components.html(
                    f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
                        <style>
                            body {{ margin:0; padding:0; background:transparent; }}
                            .mic-box {{
                                display: flex; align-items: center; gap: 15px; padding: 15px;
                                background: rgba(255, 59, 48, 0.08); border-radius: 12px;
                                border: 1px solid rgba(255, 59, 48, 0.3); color: #FFFFFF;
                                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                            }}
                            .material-icons-outlined {{ font-size: 32px; color: #FF3B30; animation: pulse-sos 1.5s infinite; }}
                            @keyframes pulse-sos {{
                                0% {{ opacity: 0.6; transform: scale(1); }}
                                50% {{ opacity: 1; transform: scale(1.1); }}
                                100% {{ opacity: 0.6; transform: scale(1); }}
                            }}
                            .status-text {{ font-size: 14px; font-weight: 600; display: block; color: #FF3B30; }}
                            .sub-text {{ font-size: 12px; color: #9E9EAF; display: block; margin-top: 2px; }}
                            .error-box {{ background: rgba(255,149,0,0.08); border-color: rgba(255,149,0,0.3); }}
                            .error-box .material-icons-outlined {{ color: #FF9500; animation: none; }}
                            .error-box .status-text {{ color: #FF9500; }}
                        </style>
                    </head>
                    <body>
                        <div id="mic_box" class="mic-box">
                            <span id="mic_icon" class="material-icons-outlined">settings_voice</span>
                            <div>
                                <span class="status-text" id="status_text">🟢 Listening for distress words...</span>
                                <span class="sub-text" id="sub_text">Say "help", "bachao", or your safe word (<strong>{disp_safe_word}</strong>) to trigger SOS.</span>
                            </div>
                        </div>
                        <script>
                            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                            const micBox = document.getElementById("mic_box");
                            const micIcon = document.getElementById("mic_icon");
                            const statusText = document.getElementById("status_text");
                            const subText = document.getElementById("sub_text");
                            const distressKeywords = {keywords_js};

                            if (!SpeechRecognition) {{
                                micBox.className = "mic-box error-box";
                                micIcon.innerText = "warning";
                                statusText.innerText = "Browser Speech API Unsupported";
                                subText.innerText = "Use Chrome, Edge, or Safari for voice SOS.";
                            }} else {{
                                let recognition = new SpeechRecognition();
                                recognition.continuous = true;
                                recognition.interimResults = false;
                                recognition.lang = 'en-IN';

                                recognition.onresult = function(event) {{
                                    const lastIndex = event.results.length - 1;
                                    const transcript = event.results[lastIndex][0].transcript.toLowerCase();
                                    console.log("Heard:", transcript);

                                    let found = false;
                                    for (const kw of distressKeywords) {{
                                        if (transcript.includes(kw)) {{ found = true; break; }}
                                    }}

                                    if (found) {{
                                        statusText.innerText = "🚨 PANIC DETECTED: " + transcript;
                                        // Navigate top window to current URL with panic query params
                                        // Streamlit will detect these on next render cycle
                                        const base = window.top.location.href.split('?')[0];
                                        const params = new URLSearchParams(window.top.location.search);
                                        params.set('panic', '1');
                                        params.set('transcript', transcript);
                                        window.top.location.href = base + '?' + params.toString();
                                    }}
                                }};

                                recognition.onerror = function(event) {{
                                    console.error("Speech error:", event.error);
                                    if (event.error === 'not-allowed') {{
                                        micBox.className = "mic-box error-box";
                                        micIcon.innerText = "gpp_bad";
                                        statusText.innerText = "Microphone Permission Blocked";
                                        subText.innerText = "Allow microphone access in browser settings.";
                                    }}
                                }};

                                recognition.onend = function() {{
                                    try {{ recognition.start(); }} catch(e) {{}}
                                }};

                                try {{ recognition.start(); }} catch(e) {{
                                    console.error("Start error:", e);
                                }}
                            }}
                        </script>
                    </body>
                    </html>
                    """,
                    height=100
                )

            if is_listening:
                st.markdown("<p style='font-size:12px; font-weight:600; margin:20px 0 8px 0;'>Simulate Vocal Panic Sample (Whisper):</p>", unsafe_allow_html=True)
                
                # Simulation buttons
                t1, t2, t3 = st.columns(3)
                with t1:
                    scream = st.button("Scream", key="sim_scream", width="stretch")
                with t2:
                    help_word = st.button("Help", key="sim_help", width="stretch")
                with t3:
                    bachao = st.button("Bachao", key="sim_bachao", width="stretch")
                    
                custom_input = st.text_input("Or simulate custom spoken phrase", placeholder="Say something...", key="sim_custom_voice")
                
                sim_word_key = ""
                if scream: sim_word_key = "panic_scream"
                elif help_word: sim_word_key = "panic_help"
                elif bachao: sim_word_key = "panic_bachao"
                elif custom_input:
                    if st.button("🎤 Parse Custom Spoken Phrase", key="btn_parse_custom_voice"):
                        sim_word_key = custom_input
                
                if sim_word_key:
                    files = {
                        "file": (f"{sim_word_key}.wav", b"fake audio content bytes")
                    }
                    data = {
                        "latitude": user_lat,
                        "longitude": user_lng,
                        "location_name": calc_loc_val
                    }
                    
                    with st.spinner("Whisper transcribing vocal cues..."):
                        res = api_post_file("/voice-panic", files=files, data=data)
                        
                    if res:
                        st.session_state["stt_processing"] = True
                        st.session_state["stt_result"] = res.get("transcript", "")
                        st.session_state["stt_urgency"] = "CRITICAL / PANIC THREAT DETECTED" if res.get("panic_detected") else "LOW URGENCY"
                        st.session_state["stt_db_status"] = res.get("db_connection_status", "Disconnected")
                        st.session_state["stt_msg_sent"] = res.get("emergency_message_sent", False)
                        st.session_state["stt_recipients"] = res.get("emergency_message_recipients", [])
                        st.session_state["stt_sms_body"] = res.get("emergency_message_body", "")
                        
                        if res.get("panic_detected"):
                            st.session_state["sos_sms_body"] = res.get("emergency_message_body", "")
                            st.session_state["sos_sent"] = True
                            st.session_state["stt_processing"] = False
                            st.toast("🔥 Panic Vocal Detected! Activating SOS...", icon="🚨")
                        else:
                            st.session_state["sos_situation"] = "Emergency SOS button pressed by user."
                        st.rerun()
                    else:
                        st.error("Audio parser connection failed.")
            st.markdown('</div>', unsafe_allow_html=True)

        # Transcribe & trigger state monitor
        if st.session_state["stt_processing"]:
            db_status = st.session_state.get("stt_db_status", "Disconnected")
            if "MongoDB" in db_status and "offline" not in db_status.lower() and "failed" not in db_status.lower():
                db_badge = f'<span style="background-color: #34C759; color: white; padding: 4px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; display: inline-block; margin-top: 4px;">🟢 {db_status}</span>'
            elif "fallback" in db_status.lower() or "offline" in db_status.lower():
                db_badge = f'<span style="background-color: #FF9500; color: white; padding: 4px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; display: inline-block; margin-top: 4px;">🟡 {db_status}</span>'
            else:
                db_badge = f'<span style="background-color: #FF3B30; color: white; padding: 4px 8px; border-radius: 8px; font-size: 11px; font-weight: 600; display: inline-block; margin-top: 4px;">🔴 {db_status}</span>'

            recipients = st.session_state.get("stt_recipients", [])
            sms_body = st.session_state.get("stt_sms_body", "")
            msg_sent = st.session_state.get("stt_msg_sent", False)
            
            recipients_html = ""
            if msg_sent and recipients:
                recipients_str = ", ".join(recipients)
                recipients_html = f"""
                <div style="margin-top:12px;">
                    <span style="font-size:11px; color:var(--text-secondary); display:block;">EMERGENCY BROADCAST RECIPIENTS</span>
                    <strong style="color:#00C6FF; font-size:14px;">📡 {recipients_str}</strong>
                </div>
                <div style="margin-top:12px; background:rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius:8px; padding:12px;">
                    <span style="font-size:11px; color:var(--text-secondary); display:block; margin-bottom: 4px;">BROADCAST MESSAGE BODY</span>
                    <span style="font-family: monospace; font-size: 12px; color: var(--text-primary); white-space: pre-wrap;">{sms_body}</span>
                </div>
                """

            st.markdown('<div class="safety-card" style="margin-top:20px; border-left: 5px solid #FF3B30;">', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <span style="font-size:11px; color:var(--text-secondary); display:block;">DATABASE CONNECTION STATUS</span>
                        {db_badge}
                    </div>
                </div>
                <span style="font-size:11px; color:var(--text-secondary); display:block;">SPEECH TO TEXT TRANSCRIPTION (GEMINI STT)</span>
                <strong style="font-size:15px; color:var(--text-primary);">"{st.session_state['stt_result']}"</strong>
                <div style="margin-top:10px;">
                    <span style="font-size:11px; color:var(--text-secondary); display:block;">LLM URGENCY CLASSIFIER</span>
                    <strong style="color:#FF3B30; font-size:15px;">🚨 {st.session_state['stt_urgency']}</strong>
                </div>
                {recipients_html}
                """,
                unsafe_allow_html=True
            )
            
            if "CRITICAL" in st.session_state["stt_urgency"]:
                st.toast("🔥 Panic Vocal Detected! Activating SOS...", icon="🚨")
                st.session_state["stt_processing"] = False
                situation_desc = f"Voice panic/distress detected: '{st.session_state.get('stt_result')}'"
                payload = {
                    "situation": situation_desc,
                    "location_name": calc_loc_val,
                    "latitude": user_lat,
                    "longitude": user_lng,
                    "battery_level": 84
                }
                res = api_post("/sos", payload)
                if res and res.get("success"):
                    st.session_state["sos_sms_body"] = res.get("sms_body", "")
                    st.session_state["sos_sent"] = True
                st.rerun()
            else:
                if st.button("Clear analysis log", key="clear_stt"):
                    st.session_state["stt_processing"] = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
