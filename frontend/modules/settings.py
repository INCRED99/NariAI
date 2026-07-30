import streamlit as st
from frontend.modules.api_client import api_get, api_post

def render_settings():
    st.markdown(
        """
        <div style='text-align: left; margin-bottom: 25px;'>
            <h1 style='margin: 0; font-size: 38px;'><span class='gradient-text'>Settings</span></h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                Configure safety buffers, custom countdown durations, and siren parameters.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Main Config Grid (2 Columns)
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown('<div class="safety-card" style="min-height: 400px;">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0; font-size:18px;'>SOS Settings</h3>", unsafe_allow_html=True)
        
        countdown_secs = st.slider("SOS Countdown Duration (seconds)", min_value=3, max_value=15, value=5)
        st.caption("Lowering this duration speeds up emergency SMS dispatch but reduces time to cancel accidental triggers.")
        
        st.markdown("<h4 style='margin-top:20px; margin-bottom:5px;'>Pre-Incident Audio Loop</h4>", unsafe_allow_html=True)
        st.checkbox("Record ambient audio loop (1 min)", value=True)
        st.caption("Encrypts and caches a rolling 1-minute audio recording locally, uploaded only upon SOS activation.")
        
        st.markdown("<h4 style='margin-top:20px; margin-bottom:5px;'>Safe Word Trigger</h4>", unsafe_allow_html=True)
        
        # Sync safe word with MongoDB
        profile_res = api_get("/profile")
        current_safe_word = "Blue Moon"
        profile_data = {}
        if profile_res and "profile" in profile_res:
            profile_data = profile_res["profile"]
            current_safe_word = profile_data.get("safe_word", "Blue Moon")
            
        safe_word_val = st.text_input("Designated Safe Word", value=current_safe_word)
        if safe_word_val != current_safe_word and profile_data:
            profile_data["safe_word"] = safe_word_val
            res = api_post("/profile", profile_data)
            if res and res.get("success"):
                st.session_state["safe_word"] = safe_word_val
                st.toast("Safe Word updated and synchronized to MongoDB!", icon="💾")
                st.rerun()
                
        st.caption("Typing this word in the AI Assistant instantly activates SOS and broadcasts GPS coordinates.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="safety-card" style="min-height: 400px;">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0; font-size:18px;'>Sound & Alerts</h3>", unsafe_allow_html=True)
        
        siren_vol = st.slider("Alarm/Siren Volume", min_value=0, max_value=100, value=80)
        
        st.markdown("<h4 style='margin-top:25px; margin-bottom:10px;'>Alert Sound Test</h4>", unsafe_allow_html=True)
        if st.button("🔊 Test High-Pitch Siren", use_container_width=True):
            st.toast("🚨 Playing emergency siren test!")
            st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", start_time=0)
            
        st.markdown("<h4 style='margin-top:25px; margin-bottom:5px;'>Geofencing Buffer</h4>", unsafe_allow_html=True)
        st.number_input("Safe boundary radius (meters)", min_value=100, max_value=5000, value=1000, step=100)
        st.markdown('</div>', unsafe_allow_html=True)

    # Theme Settings Card (Full Width)
    st.markdown('<div class="safety-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top:0; font-size:18px;'>System Themes</h3>", unsafe_allow_html=True)
    
    current_theme = "Dark Mode" if st.session_state.get("dark_mode", True) else "Light Mode"
    st.write(f"System theme is currently: **{current_theme}**")
    
    dark_mode_toggle = st.toggle("Enable Dark Theme Toggle", value=st.session_state.get("dark_mode", True))
    if dark_mode_toggle != st.session_state.get("dark_mode", True):
        st.session_state["dark_mode"] = dark_mode_toggle
        st.toast(f"Theme switched to {'Dark' if dark_mode_toggle else 'Light'} mode!")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

