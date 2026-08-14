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
                
                # Audio recording removed
                print("[THREAD DEBUG] Speech captured! Sending to transcription...")
                text = r.recognize_google(audio).lower()
                print(f"[THREAD DEBUG] Google Speech transcribed: '{text}'")
                
                # Trigger on ANY spoken phrase
                found_panic = True
                        
                if found_panic:
                    print(f"[THREAD DEBUG] SPOKEN PHRASE DETECTED: '{text}'! Dispatching SOS...")
                    
                    # Audio recording upload removed per user request
                        
                    situation_text = f"Voice SOS trigger: '{text}'"
                        
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
                    except Exception as post_err:
                        print(f"[THREAD DEBUG] SOS post error: {post_err}")
                        sms_body = f"Emergency! Spoken threat detected: '{text}' at {calc_loc_val}."
                        
                    # Put inside shared global triggers
                    GLOBAL_PANIC_TRIGGERS[uid] = {
                        "transcript": text,
                        "sms_body": sms_body,
                        "filename": ""
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
    # Inject message listener to handle navigation from the speech recording iframe securely
    st.markdown(
        """
        <img src="x" onerror="
            console.log('Nari parent window: checking/registering message listener...');
            if (!window.nariPanicListenerRegistered) {
                window.nariPanicListenerRegistered = true;
                console.log('Nari parent window: registering message listener for nari_panic');
                window.addEventListener('message', function(event) {
                    console.log('Nari parent window received message:', event.data);
                    if (event.data && event.data.type === 'nari_panic') {
                        console.log('Nari parent window: panic triggered! Navigating parent...');
                        const url = new URL(window.location.href);
                        url.searchParams.set('panic', '1');
                        url.searchParams.set('transcript', event.data.transcript || 'voice sos triggered');
                        if (event.data.audio_url) url.searchParams.set('audio_url', event.data.audio_url);
                        if (event.data.audio_filename) url.searchParams.set('audio_filename', event.data.audio_filename);
                        console.log('Nari parent window: Redirecting to:', url.href);
                        window.location.href = url.href;
                    }
                });
            }
        " style="display:none;">
        """,
        unsafe_allow_html=True
    )

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

    # Check browser mic panic trigger from URL query params (set by JS Web Speech API)
    _q = st.query_params
    if _q.get("panic") == "1":
        _transcript = _q.get("transcript", "distress detected")
        _audio_url = _q.get("audio_url", "")
        _audio_filename = _q.get("audio_filename", "")
        st.query_params.pop("panic", None)
        st.query_params.pop("transcript", None)
        st.query_params.pop("audio_url", None)
        st.query_params.pop("audio_filename", None)
        # Store transcript for use if Stop Listener is clicked after detection
        st.session_state["last_mic_transcript"] = _transcript
        if not st.session_state.get("sos_sent", False):
            _user_lat = st.session_state.get("current_lat", 28.6273)
            _user_lng = st.session_state.get("current_lng", 77.3725)
            _loc = st.session_state.get("current_address", "Your Location")
            # Include exact transcript in situation
            _situation = f"Voice SOS trigger: '{_transcript}'"
            _payload = {
                "situation": _situation,
                "location_name": _loc,
                "latitude": _user_lat,
                "longitude": _user_lng,
                "battery_level": 85
            }
            _res = api_post("/sos", _payload)
            if _res and _res.get("success"):
                st.session_state["sos_sms_body"] = _res.get("sms_body", "")
            else:
                _fallback = f"🚨 EMERGENCY! Distress detected: '{_transcript}'. Location: {_loc}."
                st.session_state["sos_sms_body"] = _fallback
            st.session_state["sos_sent"] = True
            st.session_state["wa_opened"] = False
            st.session_state["voice_listener_active"] = False
            st.session_state["audio_filename"] = _audio_filename  # saved for auto-delete on reset
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
                    # Don't immediately trigger SOS — let JS finish audio upload and capture final transcript
                    # Set a flag the JS component will detect, finalize recording, then navigate with ?panic=1
                    st.session_state["voice_listener_active"] = False
                    st.session_state["stop_listener_requested"] = True
                    GLOBAL_THREADS.pop(thread_key, None)
                else:
                    st.session_state["voice_listener_active"] = True
                    st.session_state["stop_listener_requested"] = False
                    st.session_state["last_mic_transcript"] = ""
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
                
            # Show mic component when actively listening OR once when stop was just requested (to finalize upload)
            stop_requested = st.session_state.get("stop_listener_requested", False)

            if is_listening or stop_requested:
                import streamlit.components.v1 as components
                import json

                q = st.query_params
                if q.get("panic") == "1":
                    st.rerun()

                # Clear stop flag immediately so it only fires STOP_MODE once
                if stop_requested:
                    st.session_state["stop_listener_requested"] = False

                if stop_requested:
                    # STOP MODE: stop recognition, grab last transcript, trigger SOS
                    st.markdown("""
                    <img src="x" onerror="
                        window._nariMicActive = false;
                        if(window._nariRecognition) { try { window._nariRecognition.stop(); } catch(e) {} window._nariRecognition = null; }
                        var lastT = localStorage.getItem('nari_last_transcript') || 'voice sos triggered';
                        localStorage.removeItem('nari_last_transcript');
                        var url = new URL(window.location.href);
                        url.searchParams.set('panic', '1');
                        url.searchParams.set('transcript', lastT);
                        window.location.href = url.href;
                    " style="display:none">
                    """, unsafe_allow_html=True)
                else:
                    # LISTEN MODE: mic status UI + SpeechRecognition in parent document
                    # Runs in the PARENT document (not iframe) so mic works on Render/HTTPS
                    st.markdown("""
                    <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
                    <style>
                        @keyframes pulse-sos { 0% { opacity:0.6; transform:scale(1); } 50% { opacity:1; transform:scale(1.1); } 100% { opacity:0.6; transform:scale(1); } }
                    </style>
                    <div style="display:flex; align-items:center; gap:15px; padding:15px; background:rgba(255,59,48,0.08); border-radius:12px; border:1px solid rgba(255,59,48,0.3); color:#FFFFFF; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
                        <span class="material-icons-outlined" id="nari_mic_icon" style="font-size:32px; color:#FF3B30; animation:pulse-sos 1.5s infinite;">settings_voice</span>
                        <div>
                            <span id="nari_mic_status" style="font-size:14px; font-weight:600; display:block; color:#FF3B30;">🟢 Listening — say anything...</span>
                            <span id="nari_mic_sub" style="font-size:12px; color:#9E9EAF; display:block; margin-top:2px;">Any spoken phrase will auto-trigger SOS. Or click Stop Listener.</span>
                        </div>
                    </div>
                    <img src="x" onerror="
                        var statusEl = document.getElementById('nari_mic_status');
                        var subEl = document.getElementById('nari_mic_sub');
                        var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                        if(!SR) {
                            if(statusEl) statusEl.innerText = 'Browser Speech API Unsupported';
                            if(subEl) subEl.innerText = 'Use Chrome or Edge for voice SOS.';
                        } else if(!window._nariMicActive) {
                            window._nariMicActive = true;
                            var r = new SR();
                            window._nariRecognition = r;
                            r.continuous = true;
                            r.interimResults = false;
                            r.lang = 'en-IN';
                            r.onresult = function(e) {
                                var t = e.results[e.results.length-1][0].transcript;
                                if(statusEl) statusEl.innerText = 'Heard: ' + t;
                                localStorage.setItem('nari_last_transcript', t);
                                r.stop();
                                window._nariMicActive = false;
                                
                                // Direct page navigation works perfectly from parent document!
                                var url = new URL(window.location.href);
                                url.searchParams.set('panic', '1');
                                url.searchParams.set('transcript', t);
                                window.location.href = url.href;
                            };
                            r.onerror = function(ev) {
                                if(ev.error === 'not-allowed') {
                                    if(statusEl) statusEl.innerText = 'Microphone Permission Blocked';
                                    if(subEl) subEl.innerText = 'Allow mic access in browser settings.';
                                }
                            };
                            r.onend = function() {
                                if(window._nariMicActive) {
                                    try { r.start(); } catch(e) {}
                                }
                            };
                            try { r.start(); } catch(e) {}
                        }
                    " style="display:none">
                    """, unsafe_allow_html=True)

            if is_listening:
                st.markdown("<p style='font-size:12px; font-weight:600; margin:20px 0 8px 0;'>Simulate Vocal Panic Sample (Whisper):</p>", unsafe_allow_html=True)
                
                # Simulation buttons
                t1, t2, t3 = st.columns(3)
                with t1:
                    scream = st.button("Scream", key="sim_scream", width="stretch")
                with t2:
                    help_btn = st.button("Help", key="sim_help", width="stretch")
                with t3:
                    bachao = st.button("Bachao", key="sim_bachao", width="stretch")
                    
                custom_input = st.text_input("Or simulate custom spoken phrase", placeholder="Say something...", key="sim_custom_voice")
                
                sim_word = None
                if scream: sim_word = "Scream"
                elif help_btn: sim_word = "Help"
                elif bachao: sim_word = "Bachao"
                elif custom_input:
                    if st.button("🎤 Parse Custom Spoken Phrase", key="btn_parse_custom_voice"):
                        sim_word = custom_input
                
                if sim_word:
                    st.session_state["sos_sent"] = True
                    st.session_state["sos_situation"] = f"Voice SOS trigger: {sim_word}"
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Transcribe & trigger state monitor
        if st.session_state.get("stt_processing", False):
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
