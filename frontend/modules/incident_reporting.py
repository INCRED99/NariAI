import streamlit as st
import time

def render_incident_reporting():
    # Page Header
    st.markdown(
        """
        <div style='text-align: left; margin-bottom: 25px;'>
            <h1 style='margin: 0; font-size: 38px;'><span class='gradient-text'>Incident Reporter</span></h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                Report unsafe surroundings, harassment, street light outages, or safety violations. AI instantly categories details for dispatch.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Initialize states
    if "reporter_desc" not in st.session_state:
        st.session_state["reporter_desc"] = ""
    if "reporter_loc" not in st.session_state:
        st.session_state["reporter_loc"] = st.session_state.get("current_address", "Your Location")
    if "reporter_submitted" not in st.session_state:
        st.session_state["reporter_submitted"] = False
    if "mic_recording" not in st.session_state:
        st.session_state["mic_recording"] = False

    col1, col2 = st.columns([1.3, 0.9], gap="large")

    with col1:
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0; font-size:18px;'>Incident Details</h3>", unsafe_allow_html=True)
        
        # Location Form
        loc_val = st.text_input("Incident Location", value=st.session_state["reporter_loc"])
        if loc_val != st.session_state["reporter_loc"]:
            st.session_state["reporter_loc"] = loc_val
            
        # Description
        desc_val = st.text_area(
            "Describe the Situation", 
            value=st.session_state["reporter_desc"], 
            placeholder="Type incident description here... (or use the voice recorder below)"
        )
        if desc_val != st.session_state["reporter_desc"]:
            st.session_state["reporter_desc"] = desc_val

        # Voice recorder simulator
        st.markdown("<h4 style='margin-top:20px; margin-bottom: 10px;'>Simulate Voice Witness Report</h4>", unsafe_allow_html=True)
        
        # Audio widget simulator
        vc_col1, vc_col2 = st.columns([0.3, 0.7])
        with vc_col1:
            if st.session_state["mic_recording"]:
                # Pulsing state
                st.markdown(
                    """
                    <div style="display:flex; justify-content:center; align-items:center; padding: 5px 0;">
                        <span class="material-icons-outlined" style="font-size: 40px; color:#FF3B30; animation: pulse-sos 1s infinite;">mic</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    """
                    <div style="display:flex; justify-content:center; align-items:center; padding: 5px 0;">
                        <span class="material-icons-outlined" style="font-size: 40px; color:#7A5CFF;">mic_none</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        with vc_col2:
            if st.session_state["mic_recording"]:
                if st.button("🔴 STOP RECORDING", key="btn_stop_mic", width="stretch"):
                    st.session_state["mic_recording"] = False
                    st.session_state["reporter_desc"] = "A suspicious group of people gathered near the street corner. The lamps are broken here and there is no guard present."
                    st.toast("Voice recorded and parsed by AI!")
                    st.rerun()
            else:
                if st.button("🎤 RECORD TRANSCRIPT", key="btn_start_mic", width="stretch"):
                    st.session_state["mic_recording"] = True
                    st.toast("Recording simulator active. Speak for 2 seconds...")
                    st.rerun()
                    
        st.markdown('</div>', unsafe_allow_html=True)

        # Image Upload
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0; font-size:18px;'>Upload Evidence (Photo/Video)</h3>", unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Drag & drop files here", type=["png", "jpg", "jpeg", "mp4"])
        
        if uploaded_file is not None:
            st.markdown(
                """
                <div style="padding:10px; background:rgba(0, 198, 255, 0.08); border-radius:10px; border:1px dashed rgba(0, 198, 255, 0.3); font-size:13px; margin-top:10px;">
                    <strong>AI Image Parsing Completed:</strong><br>
                    • Bounding Box 1: <span style="color:#FF3B30; font-weight:600;">Zero Illumination Zone</span> (Detected)<br>
                    • Metadata tags: night_stretch, dark_corner, pedestrian_risk<br>
                    • Processing confidence: 96%
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # AI Parser Summary Card
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown(
            """
            <h3 style='margin-top:0; font-size:18px;' class='icon-text-align'>
                <span class='material-icons-outlined' style='color:#7A5CFF;'>smart_toy</span> AI Report Compiler
            </h3>
            <p style='font-size:13px; color: var(--text-secondary); margin-bottom:15px;'>
                Live parser processing details:
            </p>
            """,
            unsafe_allow_html=True
        )
        
        # Compute dynamic categories based on content
        desc = st.session_state["reporter_desc"]
        category = "General Threat"
        urgency = "Low"
        badge_style = "low"
        ai_summary = "Waiting for description inputs to parse..."
        
        if len(desc) > 5:
            ai_summary = f"Incident reported at '{st.session_state['reporter_loc']}'. Details highlight structural infrastructure failure and threat factors."
            if "broken" in desc.lower() or "lamps" in desc.lower() or "dark" in desc.lower():
                category = "Infrastructure (Streetlight Outage)"
                urgency = "Medium"
                badge_style = "medium"
            if "suspicious" in desc.lower() or "group" in desc.lower() or "harassment" in desc.lower():
                category = "Security Threat"
                urgency = "High"
                badge_style = "high"
                
        st.markdown(
            f"""
            <div style="margin-bottom:12px;">
                <span style="font-size:12px; color: var(--text-secondary); display:block; margin-bottom:3px;">PARSED CATEGORY</span>
                <strong style="font-size:15px; color: var(--text-primary);">{category}</strong>
            </div>
            <div style="margin-bottom:12px;">
                <span style="font-size:12px; color: var(--text-secondary); display:block; margin-bottom:3px;">URGENCY RATING</span>
                <span class="severity-badge {badge_style}">{urgency}</span>
            </div>
            <div style="margin-bottom:12px;">
                <span style="font-size:12px; color: var(--text-secondary); display:block; margin-bottom:3px;">AI SYNTHESIZED REPORT LOG</span>
                <p style="margin:0; font-size:13px; color: var(--text-primary); font-style:italic;">"{ai_summary}"</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit Button
        if st.session_state["reporter_submitted"]:
            raw_loc = st.session_state.get("reporter_loc", "Your Location")
            parts = [p.strip() for p in raw_loc.split(",")]
            city_name = "Local"
            if len(parts) > 1:
                city_name = parts[1]
            elif len(parts) > 0 and parts[0] != "Your Location" and parts[0] != "":
                city_name = parts[0]
            st.markdown(
                f"""
                <div class="safety-card" style="border: 2px solid #34C759; text-align:center; background: rgba(52, 199, 89, 0.08);">
                    <span class="material-icons-outlined" style="font-size:40px; color:#34C759;">check_circle</span>
                    <h4 style="margin:10px 0 5px 0; color:#34C759;">Report Dispatched</h4>
                    <p style="margin:0; font-size:12px; color: var(--text-secondary);">ID: #NARI-8849<br>Sent to {city_name} Municipal & Local Police</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("File New Report", key="btn_reset_report", width="stretch"):
                st.session_state["reporter_submitted"] = False
                st.session_state["reporter_desc"] = ""
                st.rerun()
        else:
            if st.button("🚀 SUBMIT REPORT", key="btn_submit_report", width="stretch", type="primary"):
                st.session_state["reporter_submitted"] = True
                st.toast("🎉 Incident submitted successfully!")
                st.rerun()
