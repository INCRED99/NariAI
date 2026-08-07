import streamlit as st
import time
from datetime import datetime
from frontend.modules.api_client import api_post, api_get, api_post_file

# Multilingual Translations dictionary
LANG_DATA = {
    "English (US)": {
        "greeting": "Hello Priya! I am your AI Safety Assistant. How can I help you stay secure today?",
        "placeholder": "Type your message here...",
        "send": "Send",
        "chat_history": "Chat History",
        "quick_prompts": "Quick Prompts",
        "emergency_flag": "🚨 HIGH RISK SITUATION DETECTED",
        "action_prompt": "Emergency detected. What should I do?",
        "btn_call_ems": "📞 Call Emergency (112)",
        "btn_share_loc": "📍 Share Coordinates",
        "btn_find_police": "👮 Find Police Booth",
        "summary_title": "📋 AI Emergency Situation Summary",
        "send_summary": "📤 Send Summary to Trust Circle",
        "history_1": "CP Late-night Route Audit",
        "history_2": "Metro security procedures",
        "history_3": "SOS key configurations"
    },
    "Hindi (हिंदी)": {
        "greeting": "नमस्ते प्रिया! मैं आपकी सुरक्षा सहायक हूँ। आज मैं आपकी सुरक्षा में कैसे मदद कर सकती हूँ?",
        "placeholder": "अपना संदेश यहाँ लिखें...",
        "send": "भेजें",
        "chat_history": "वार्तालाप इतिहास",
        "quick_prompts": "त्वरित निर्देश",
        "emergency_flag": "🚨 उच्च जोखिम स्थिति का पता चला",
        "action_prompt": "आपातकालीन स्थिति। मुझे क्या करना चाहिए?",
        "btn_call_ems": "📞 पुलिस को कॉल करें (112)",
        "btn_share_loc": "📍 स्थान साझा करें",
        "btn_find_police": "👮 पुलिस बूथ खोजें",
        "summary_title": "📋 एआई आपातकालीन सारांश",
        "send_summary": "📤 ट्रस्ट सर्कल को सारांश भेजें",
        "history_1": "कनॉट प्लेस नाइट ऑडिट",
        "history_2": "मेट्रो सुरक्षा नियम",
        "history_3": "एसओएस कुंजी सेटिंग्स"
    },
    "Marathi (मराठी)": {
        "greeting": "नमस्कार प्रिया! मी तुझी सुरक्षा सहाय्यक आहे. आज मी तुला कशी मदत करू शकते?",
        "placeholder": "तुमचा संदेश येथे लिहा...",
        "send": "पाठवा",
        "chat_history": "संभाषण इतिहास",
        "quick_prompts": "द्रुत मार्गदर्शक",
        "emergency_flag": "🚨 उच्च जोखीम परिस्थिती आढळली",
        "action_prompt": "आपत्कालीन परिस्थिती. मी काय करू?",
        "btn_call_ems": "📞 पोलिसांना कॉल करा (112)",
        "btn_share_loc": "📍 स्थान सामायिक करा",
        "btn_find_police": "👮 पोलीस चौकी शोधा",
        "summary_title": "📋 एआय आपत्कालीन सारांश",
        "send_summary": "📤 ट्रस्ट सर्कलला पाठवा",
        "history_1": "रात्रीचा प्रवास ऑडिट",
        "history_2": "मेट्रो सुरक्षा नियम",
        "history_3": "एसओएस संरचना"
    },
    "Bengali (বাংলা)": {
        "greeting": "নমস্কার প্রিয়া! আমি আপনার নিরাপত্তা সহকারী। আজ আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
        "placeholder": "আপনার বার্তা এখানে লিখুন...",
        "send": "পাঠান",
        "chat_history": "চ্যাট ইতিহাস",
        "quick_prompts": "দ্রুত প্রম্পট",
        "emergency_flag": "🚨 উচ্চ ঝুঁকিপূর্ণ পরিস্থিতি সনাক্ত হয়েছে",
        "action_prompt": "জরুরী অবস্থা। আমি কি করতে পারি?",
        "btn_call_ems": "📞 পুলিশে ফোন করুন (112)",
        "btn_share_loc": "📍 অবস্থান শেয়ার করুন",
        "btn_find_police": "👮 পুলিশ বুথ খুঁজুন",
        "summary_title": "📋 এআই জরুরী পরিস্থিতি সারাংশ",
        "send_summary": "📤 ট্রাস্ট সার্কেলে পাঠান",
        "history_1": "লেট-নাইট রুট অডিট",
        "history_2": "মেট্রো নিরাপত্তা তথ্য",
        "history_3": "এসओएस কনফিগারেশন"
    },
    "Tamil (தமிழ்)": {
        "greeting": "வணக்கம் பிரியா! நான் உங்கள் பாதுகாப்பு உதவியாளர். இன்று நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
        "placeholder": "உங்கள் செய்தியை இங்கே தட்டச்சு செய்யவும்...",
        "send": "அனுப்பு",
        "chat_history": "உரையாடல் வரலாறு",
        "quick_prompts": "விரைவான கேள்விகள்",
        "emergency_flag": "🚨 அதிக ஆபத்து கண்டறியப்பட்டது",
        "action_prompt": "அவசரகால நிலைமை. நான் என்ன செய்ய வேண்டும்?",
        "btn_call_ems": "📞 அவசர எண் அழைக்கவும் (112)",
        "btn_share_loc": "📍 இருப்பிடத்தை பகிரவும்",
        "btn_find_police": "👮 காவல் நிலையத்தை கண்டறியவும்",
        "summary_title": "📋 ஏஐ அவசர சுருக்கம்",
        "send_summary": "📤 அவசர வட்டத்திற்கு அனுப்பவும்",
        "history_1": "நள்ளிரவு வழி தணிக்கை",
        "history_2": "மெদ্রোহ பாதுகாப்பு நெறிமுறைகள்",
        "history_3": "எஸ்ஓஎஸ் அமைப்புகள்"
    }
}

def submit_user_message(user_text):
    current_time = datetime.now().strftime("%I:%M %p")
    st.session_state["chat_messages"].append({
        "role": "user",
        "content": user_text,
        "time": current_time
    })
    st.session_state["typing"] = True
    st.rerun()

def render_ai_assistant():
    # Retrieve configuration settings
    user_lang = st.session_state.get("language", "English (US)")
    
    # Fallback to English if translation missing
    if user_lang not in LANG_DATA:
        user_lang = "English (US)"
        
    t_dict = LANG_DATA[user_lang]

    # Page Header
    st.markdown(
        f"""
        <div style='text-align: left; margin-bottom: 25px;'>
            <h1 style='margin: 0; font-size: 38px;'><span class='gradient-text'>AI Safety Assistant</span></h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                Your 24/7 personal safety coach. Instantly monitors risk, extracts emergency summaries, and detects vocal panic.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Multi-language selector pill inside the Assistant
    st.markdown('<div style="margin-bottom: 20px; display:flex; justify-content:flex-end;">', unsafe_allow_html=True)
    lang_opts = ["English (US)", "Hindi (हिंदी)", "Marathi (मराठी)", "Bengali (বাংলা)", "Tamil (தமிழ்)"]
    sel_lang = st.selectbox("Preferred Assistant Language", lang_opts, index=lang_opts.index(user_lang), key="assist_lang")
    if sel_lang != user_lang:
        st.session_state["language"] = sel_lang
        # Reset greeting based on new language
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": LANG_DATA[sel_lang]["greeting"],
                "time": datetime.now().strftime("%I:%M %p")
            }
        ]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Initialize chat state
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": t_dict["greeting"],
                "time": datetime.now().strftime("%I:%M %p")
            }
        ]
    if "active_safety_state" not in st.session_state:
        st.session_state["active_safety_state"] = "Normal"
    if "active_next_action" not in st.session_state:
        st.session_state["active_next_action"] = ""
    if "chat_threat_score" not in st.session_state:
        st.session_state["chat_threat_score"] = 0

    # Grid (Left History/Suggestions, Right Chat Box)
    col1, col2 = st.columns([1, 2.5], gap="large")

    with col1:
        # Live Threat Assessment Card
        score_val = st.session_state.get("chat_threat_score", 0)
        border_clr = "#FF3B30" if score_val >= 70 else "#FFD60A" if score_val >= 30 else "#30D158"
        status_info = "⚠️ HIGH RISK SITUATION: Emergency dispatch triggered!" if score_val >= 70 else "⚠️ MODERATE RISK: Guided safety conversation active." if score_val >= 30 else "🟢 LOW RISK: Normal safety assistant environment."
        
        st.markdown(
            f"""
            <div class="safety-card" style="margin-bottom: 20px; border-left: 5px solid {border_clr};">
                <h4 style="margin: 0 0 10px 0; font-size: 14px; font-weight: 700; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.5px;">
                    🛡️ Live Threat Level
                </h4>
                <div style="font-size: 28px; font-weight: 800; color: {border_clr}; margin-bottom: 5px;">
                    {score_val}%
                </div>
                <div style="width: 100%; background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px; overflow: hidden; margin-bottom: 8px;">
                    <div style="width: {score_val}%; background: {border_clr}; height: 100%; transition: width 0.4s ease;"></div>
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">
                    {status_info}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown(f"<h4 style='margin-top:0;'>{t_dict['chat_history']}</h4>", unsafe_allow_html=True)
        
        history_items = [
            (t_dict["history_1"], "2 days ago"),
            (t_dict["history_2"], "5 days ago"),
            (t_dict["history_3"], "1 week ago")
        ]
        for title, age in history_items:
            st.markdown(
                f"""
                <div style="padding: 10px; border-radius: 8px; background: rgba(122,92,255,0.05); margin-bottom: 8px; border: 1px solid var(--border-color);">
                    <p style="margin:0; font-size:13px; font-weight:600;">{title}</p>
                    <p style="margin:0; font-size:11px; color: var(--text-secondary);">{age}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown(f"<h4 style='margin-top:20px; margin-bottom: 10px;'>{t_dict['quick_prompts']}</h4>", unsafe_allow_html=True)
        prompts = [
            "Analyze my route home",
            "Draft emergency SMS",
            "Tips for solo transit"
        ]
        
        # Add visible "I'm Unsafe" emergency conversation starter button
        if st.button("🚨 I'm Unsafe", width="stretch", key="btn_unsafe_trigger", type="primary"):
            submit_user_message("I'm Unsafe")
            
        for prompt in prompts:
            display_prompt = prompt
            if user_lang == "Hindi (हिंदी)":
                if prompt == "Analyze my route home": display_prompt = "घर का मार्ग विश्लेषित करें"
                elif prompt == "Draft emergency SMS": display_prompt = "एसओएस एसएमएस तैयार करें"
                elif prompt == "Tips for solo transit": display_prompt = "अकेले यात्रा के सुझाव"
                
            if st.button(display_prompt, width="stretch", key=f"quick_{prompt}"):
                submit_user_message(display_prompt)

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Render messages in a self-contained glassmorphic card
        chat_html = '<div class="safety-card" style="height: 380px; display:flex; flex-direction:column; justify-content:space-between; margin-bottom: 15px;">'
        chat_html += '<div class="chat-container" id="chat-box" style="flex-grow: 1; overflow-y: auto; max-height: 320px;">'
        for msg in st.session_state["chat_messages"]:
            bubble_class = "user" if msg["role"] == "user" else "assistant"
            content = msg["content"].replace('\n', '<br>')
            
            copy_btn = ""
            if msg["role"] == "assistant":
                escaped_content = msg["content"].replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace('\n', '\\n')
                copy_btn = (
                    f'<span class="material-icons-outlined" '
                    f'style="font-size:16px; position:absolute; right:10px; top:10px; cursor:pointer; color:var(--text-secondary);" '
                    f'onclick="navigator.clipboard.writeText(\'{escaped_content}\'); alert(\'Response copied!\');">'
                    f'content_copy</span>'
                )
            
            chat_html += f'<div class="chat-bubble {bubble_class}">'
            if copy_btn:
                chat_html += copy_btn
            chat_html += f'<div style="margin-top: 5px;">{content}</div>'
            chat_html += f'<div class="chat-time">{msg["time"]}</div>'
            chat_html += '</div>'
        chat_html += '</div></div>'
        st.markdown(chat_html, unsafe_allow_html=True)


        # 1. Check if high-risk Emergency State is currently active in session
        is_high_risk = (st.session_state["active_safety_state"] == "Emergency")

        # 2. Render High Risk Controls & AI Situation Summarizer inside Chat Box
        if is_high_risk:
            st.markdown(
                f"""
                <div class="danger-container" style="margin-top:10px;">
                    <h4 style="margin:0 0 5px 0; color:#FF3B30; font-size:15px;" class="icon-text-align">
                        <span class="material-icons-outlined" style="font-size:16px;">gpp_maybe</span> {t_dict['emergency_flag']}
                    </h4>
                    <p style="margin:0 0 10px 0; font-size:12px; color:var(--text-primary); line-height:1.4;">
                        <strong>Next Best Action Suggested:</strong> {st.session_state['active_next_action']}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Action Buttons Row (Call Emergency button removed)
            erc1, erc2 = st.columns(2)
            with erc1:
                if st.button(t_dict["btn_share_loc"], key="chat_share_loc", width="stretch"):
                    st.toast("🚨 Triggering SOS alert procedure...", icon="🚨")
                    user_lat = st.session_state.get("current_lat", 26.8346)
                    user_lng = st.session_state.get("current_lng", 80.9249)
                    calc_loc_val = st.session_state.get("current_address", "Your Location")
                    
                    chat_history_str = ""
                    for msg in st.session_state["chat_messages"][-5:]:
                        role_name = "User" if msg["role"] == "user" else "Assistant"
                        chat_history_str += f"  * {role_name}: {msg['content']}\n"
                        
                    custom_message = (
                        f"🚨 NARI SOS ALERT:\n"
                        f"- RISK: Manual Trigger from AI Safety Assistant\n"
                        f"- RECENT CONVERSATION HISTORY:\n"
                        f"{chat_history_str}"
                        f"- WHERE: {calc_loc_val} ({user_lat:.4f}, {user_lng:.4f})\n"
                        f"- TIME: {datetime.now().strftime('%H:%M')}\n"
                        f"Please send help immediately!\n"
                        f"Live Location: https://www.google.com/maps?q={user_lat:.6f},{user_lng:.6f}"
                    )
                    
                    payload_sos = {
                        "situation": custom_message,
                        "location_name": calc_loc_val,
                        "latitude": user_lat,
                        "longitude": user_lng,
                        "battery_level": 85
                    }
                    res_sos = api_post("/sos", payload_sos)
                    sms_body = ""
                    if res_sos and res_sos.get("success"):
                        sms_body = res_sos.get("sms_body", "")
                    else:
                        sms_body = custom_message
                        
                    st.session_state["sos_sms_body"] = sms_body
                    st.session_state["sos_sent"] = True
                    st.session_state["wa_opened"] = False
                    st.session_state["active_page"] = "Emergency"
                    st.rerun()
            with erc2:
                if st.button(t_dict["btn_find_police"], key="chat_find_police", width="stretch"):
                    st.session_state["active_page"] = "Nearby Safe Places"
                    st.session_state["selected_category"] = "Police Station"
                    st.rerun()
 
            # Query nearby stations and hospitals immediately to display
            with st.expander("📍 Emergency Assets - Nearby Safe Havens", expanded=True):
                # Use current detected user coordinates (default to Lucknow coordinate center)
                user_lat = st.session_state.get("current_lat", 26.8346)
                user_lng = st.session_state.get("current_lng", 80.9249)
                calc_loc_val = st.session_state.get("current_address", "Your Location")
                
                # Fetch police stations
                police_spots = api_get("/nearby-places", {"latitude": user_lat, "longitude": user_lng, "category": "Police Station"})
                # Fetch hospitals
                hosp_spots = api_get("/nearby-places", {"latitude": user_lat, "longitude": user_lng, "category": "Hospital"})
                
                spot_items = []
                if police_spots: spot_items.extend(police_spots[:2])
                if hosp_spots: spot_items.extend(hosp_spots[:2])
                
                import urllib.parse
                for idx, item in enumerate(spot_items):
                    query_str = urllib.parse.quote(f"{item['name']} {item.get('address', '')}")
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={query_str}"
                    st.markdown(
                        f"""
                        <div style="font-size:12px; padding: 6px 0; border-bottom: 1px solid var(--border-color); display:flex; justify-content:space-between;">
                            <div>
                                <a href="{maps_url}" target="_blank" style="color: #00C6FF; text-decoration: none; font-weight: 600;">
                                    📌 {item['name']}
                                </a> 
                                <span style="color: var(--text-secondary);">({item['distance_km']:.2f} km)</span>
                            </div>
                            <div style="color:#00C6FF; font-weight:600;">Security: {item['safety_score']}/100</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # Typing simulator (calling backend /api/conversation-risk)
        if st.session_state.get("typing", False):
            # Format history for API payload
            history_data = []
            for msg in st.session_state["chat_messages"][:-1]: # exclude the latest user message which triggered typing
                history_data.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            latest_msg = st.session_state["chat_messages"][-1]["content"]
            
            payload = {
                "history": history_data,
                "user_message": latest_msg,
                "user_id": "priya_sharma"
            }
            
            with st.spinner("AI thinking..."):
                res = api_post("/conversation-risk", payload)
                
            if res:
                reply = res.get("reply", "")
                state = res.get("state", "Normal")
                next_action = res.get("next_action", "")
                is_emerg = res.get("is_emergency", False)
                
                st.session_state["chat_messages"].append({
                    "role": "assistant",
                    "content": reply,
                    "time": datetime.now().strftime("%I:%M %p")
                })
                
                # Check for state escalations
                st.session_state["active_safety_state"] = state
                st.session_state["active_next_action"] = next_action
                st.session_state["chat_threat_score"] = res.get("threat_score", 0)
                
                if is_emerg:
                    st.toast("🚨 Safety parser: Threat escalated. Switching system to Emergency Mode!", icon="🚨")
                    user_lat = st.session_state.get("current_lat", 26.8346)
                    user_lng = st.session_state.get("current_lng", 80.9249)
                    calc_loc_val = st.session_state.get("current_address", "Your Location")
                    
                    # Call backend /sos endpoint to register emergency incident and broadcast SMS
                    user_chats = " | ".join([m["content"] for m in history_data[-5:] if m["role"] == "user"])
                    payload_sos = {
                        "situation": f"AI safety conversation escalation. Chat summary: {user_chats}",
                        "location_name": calc_loc_val,
                        "latitude": user_lat,
                        "longitude": user_lng,
                        "battery_level": 85
                    }
                    res_sos = api_post("/sos", payload_sos)
                    
                    sms_body = ""
                    if res_sos and res_sos.get("success"):
                        sms_body = res_sos.get("sms_body", "")
                    else:
                        sms_body = f"Emergency Alert! AI Safety Conversation escalated. Location: {calc_loc_val} ({user_lat}, {user_lng}). Please send help!"
                        
                    st.session_state["sos_sms_body"] = sms_body
                    st.session_state["sos_sent"] = True
                    st.session_state["wa_opened"] = False
                    st.session_state["active_page"] = "Emergency"
                    st.rerun()
            else:
                # Backend offline or rate limited fallback
                st.session_state["chat_messages"].append({
                    "role": "assistant",
                    "content": "⚠️ **Offline Mode / Connection Timeout**: I am currently operating in offline mode. For safety guidelines, please consult the Safety Laws database. If you feel unsafe, please activate the SOS button or call emergency helpline 112 immediately.",
                    "time": datetime.now().strftime("%I:%M %p")
                })
                
            st.session_state["typing"] = False
            st.rerun()

        # Input elements row
        st.markdown('<div style="border-top: 1px solid var(--border-color); padding-top:15px; margin-top: auto;">', unsafe_allow_html=True)
        
        in_col1, in_col2, in_col3 = st.columns([0.15, 0.15, 0.7])
        with in_col1:
            voice_trigger = st.button("🎤", help="Voice Input", key="btn_voice_input", width="stretch")
            if voice_trigger:
                # Compile fake audio content, simulating speech translation in selected language
                # Shifting this trigger directly calls our speech-to-text API
                user_lat = st.session_state.get("current_lat", 28.6273)
                user_lng = st.session_state.get("current_lng", 77.3725)
                calc_loc_val = st.session_state.get("current_address", "Your Location")
                
                files = {
                    "file": ("panic_help.wav", b"fake audio content bytes")
                }
                data = {
                    "latitude": user_lat,
                    "longitude": user_lng,
                    "location_name": calc_loc_val
                }
                with st.spinner("Whisper transcribing..."):
                    res = api_post_file("/voice-panic", files=files, data=data)
                if res:
                    transcript = res.get("transcript", "")
                    submit_user_message(transcript)
                else:
                    st.error("Speech transcription offline.")

        with in_col2:
            img_trigger = st.button("📷", help="Upload safety photo", key="btn_img_input", width="stretch")
            if img_trigger:
                st.toast("Simulating Cam scan...")
                time.sleep(0.8)
                st.session_state["chat_messages"].append({
                    "role": "user",
                    "content": "[Uploaded Image] - Scanned street conditions.",
                    "time": datetime.now().strftime("%I:%M %p")
                })
                st.session_state["chat_messages"].append({
                    "role": "assistant",
                    "content": "📷 AI Image Parser: The image reveals zero illumination in the selected alley stretch. Route risk factor elevated.",
                    "time": datetime.now().strftime("%I:%M %p")
                })
                st.rerun()

        with in_col3:
            with st.form("chat_form", clear_on_submit=True):
                user_text = st.text_input("Type your message here...", placeholder=t_dict["placeholder"], label_visibility="collapsed")
                submit_button = st.form_submit_button(t_dict["send"], width="stretch")
                if submit_button and user_text:
                    submit_user_message(user_text)

        st.markdown('</div>', unsafe_allow_html=True)

