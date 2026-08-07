import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import time, datetime
from frontend.modules.api_client import api_get, api_post

def render_profile():
    # Page Header
    st.markdown(
        """
        <div style='text-align: left; margin-bottom: 25px;'>
            <h1 style='margin: 0; font-size: 38px;'><span class='gradient-text'>Personal Safety Profile</span></h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                Build your safety fingerprint. AI adjusts monitoring thresholds, warning levels, and geofencing buffers based on your commutes and trust circles.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Fetch Profile Data from Backend
    backend_data = api_get("/profile")
    
    if backend_data:
        profile_db = backend_data.get("profile", {})
        memories = backend_data.get("memories", [])
        memories_text = backend_data.get("memories_text", [])
    else:
        profile_db = {}
        memories = []
        memories_text = []

    # Get default values from database or session state
    p_name = profile_db.get("name", "Priya Sharma")
    p_phone = profile_db.get("phone", "7007914594")
    p_lang = profile_db.get("preferred_language", "English (US)")
    p_safe_word = profile_db.get("safe_word", "Blue Moon")
    p_home_addr = profile_db.get("home_address", "Home Address")
    p_home_lat = profile_db.get("home_lat", 28.6273)
    p_home_lng = profile_db.get("home_lng", 77.3725)
    p_office_addr = profile_db.get("office_address", "Office Address")
    p_office_lat = profile_db.get("office_lat", 28.5730)
    p_office_lng = profile_db.get("office_lng", 77.3220)
    p_routine = profile_db.get("travel_routine", "Daily Commute Route")
    
    db_contacts = profile_db.get("emergency_contacts", [])
    
    c_parents = db_contacts[0]["name"] + " (" + db_contacts[0]["relation"] + ") - " + db_contacts[0]["phone"] if len(db_contacts) > 0 else "Aarav Sharma (Husband) - 7007914594"
    c_friends = db_contacts[1]["name"] + " (" + db_contacts[1]["relation"] + ") - " + db_contacts[1]["phone"] if len(db_contacts) > 1 else "Neha Verma (Sister) - +91 91234 56789"
    c_roommate = db_contacts[2]["name"] + " (" + db_contacts[2]["relation"] + ") - " + db_contacts[2]["phone"] if len(db_contacts) > 2 else "Siddharth (Roommate) - +91 99887 76655"

    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
        # Profile details card
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0; font-size:18px;'>Primary Parameters</h3>", unsafe_allow_html=True)
        
        name = st.text_input("Full Name", value=p_name)
        phone = st.text_input("Phone Number", value=p_phone)
        
        lang_opts = ["English (US)", "Hindi (हिंदी)", "Marathi (मराठी)", "Bengali (বাংলা)", "Tamil (தமிழ்)"]
        sel_lang = st.selectbox("Preferred System Language", lang_opts, index=lang_opts.index(p_lang) if p_lang in lang_opts else 0)
        st.session_state["language"] = sel_lang
            
        custom_sw = st.text_input("Custom Safe Word (Emergency Trigger)", value=p_safe_word)
        st.session_state["safe_word"] = custom_sw
            
        st.markdown("</div>", unsafe_allow_html=True)

        # Commute profile card
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0; font-size:18px;'>Commute & Travel Profiles</h3>", unsafe_allow_html=True)
        st.caption("AI updates travel routine memory logs automatically.")
        
        home_addr = st.text_input("Home Location Address", value=p_home_addr)
        office_addr = st.text_input("Office Location Address", value=p_office_addr)
        reg_route = st.text_area("Daily Travel Route / Description", value=p_routine)
        
        st.markdown("</div>", unsafe_allow_html=True)

        # Emergency contacts configuration
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0; font-size:18px;'>Trusted Safety Circles</h3>", unsafe_allow_html=True)
        st.caption("Enter contact details in format: Name (Relation) - Number")
        
        parents_val = st.text_input("Family Contact Detail", value=c_parents)
        friends_val = st.text_input("Friends Contact Detail", value=c_friends)
        roommate_val = st.text_input("Roommate Contact Detail", value=c_roommate)

        if st.button("💾 SAVE PROFILE AND SYNC AI MEMORY", key="btn_save_full_profile", width="stretch", type="primary"):
            # Parse contact strings back to structured items
            def parse_contact_str(val, default_name, default_rel, default_phone):
                try:
                    parts = val.split(" - ")
                    ph = parts[1].strip()
                    name_rel = parts[0].split("(")
                    nm = name_rel[0].strip()
                    rel = name_rel[1].replace(")", "").strip()
                    return {"name": nm, "relation": rel, "phone": ph}
                except Exception:
                    return {"name": default_name, "relation": default_rel, "phone": default_phone}

            contacts_data = [
                parse_contact_str(parents_val, "Aarav Sharma", "Husband", "7007914594"),
                parse_contact_str(friends_val, "Neha Verma", "Sister", "+91 91234 56789"),
                parse_contact_str(roommate_val, "Siddharth", "Roommate", "+91 99887 76655")
            ]
            
            post_data = {
                "name": name,
                "phone": phone,
                "preferred_language": sel_lang,
                "safe_word": custom_sw,
                "home_address": home_addr,
                "home_lat": p_home_lat,
                "home_lng": p_home_lng,
                "office_address": office_addr,
                "office_lat": p_office_lat,
                "office_lng": p_office_lng,
                "travel_routine": reg_route,
                "emergency_contacts": contacts_data
            }
            
            res = api_post("/profile", post_data)
            if res and res.get("success"):
                st.toast("Personal Safety Profile updated & AI Safety Memories updated!", icon="💾")
                st.rerun()
            else:
                st.error("Failed to update profile on backend.")
            
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # AI Learnings Summary Card
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown(
            """
            <h3 style='margin-top:0; font-size:18px;' class='icon-text-align'>
                <span class='material-icons-outlined' style='color:#7A5CFF;'>psychology</span> AI Safety Memory (Mem0)
            </h3>
            <p style='font-size:13px; color: var(--text-secondary); margin-bottom:15px;'>
                Persistent safety insights extracted from your commutes, routines, and statements:
            </p>
            """,
            unsafe_allow_html=True
        )
        
        if memories_text:
            for text in memories_text:
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:start; gap:8px; font-size:13px; margin-bottom:10px;">
                        <span class="material-icons-outlined" style="font-size:16px; color:#00C6FF; margin-top:2px;">insights</span>
                        <div>{text}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                """
                <div style="text-align:center; padding:15px; color:var(--text-secondary); font-size:13px;">
                    No memory insights extracted yet. Save your profile to trigger safety fact extraction!
                </div>
                """,
                unsafe_allow_html=True
            )
            
        # Add a reset button for memories
        st.markdown("<hr style='margin: 15px 0; border-top: 1px solid var(--border-color);'>", unsafe_allow_html=True)
        if st.button("Clear AI Safety Memories", width="stretch", key="clear_mem_btn"):
            res = api_post("/profile/clear-memories")
            if res and res.get("success"):
                st.toast("Safety memories cleared successfully.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Travel Habits Widget
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown(
            """
            <h3 style='margin-top:0; font-size:18px;' class='icon-text-align'>
                <span class='material-icons-outlined' style='color:#00C6FF;'>directions_run</span> Travel Habits Safety
            </h3>
            <p style='font-size:13px; color: var(--text-secondary); margin-bottom:15px;'>
                Safety index of your historical destinations:
            </p>
            """,
            unsafe_allow_html=True
        )
        
        destinations = ["Office", "Gym / Fitness", "Market Place", "Family Res.", "Downtown Center"]
        scores = [94, 91, 85, 96, 78]
        df_habits = pd.DataFrame({"Destination": destinations, "Safety Index (%)": scores})
        
        is_dark = st.session_state.get("dark_mode", True)
        font_color = "#F6F5FB" if is_dark else "#1A1D35"
        
        fig = px.bar(
            df_habits, 
            x="Safety Index (%)", 
            y="Destination", 
            orientation="h",
            text="Safety Index (%)",
            color="Safety Index (%)",
            color_continuous_scale=[[0, '#FF3B30'], [0.5, '#FF9500'], [1, '#34C759']]
        )
        
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            height=200,
            xaxis=dict(showgrid=False, range=[0, 110], color=font_color),
            yaxis=dict(color=font_color),
            coloraxis_showscale=False,
            template="plotly_dark" if is_dark else "plotly_white"
        )
        fig.update_traces(
            textposition="outside",
            textfont=dict(color=font_color, size=11),
            marker=dict(line=dict(width=0))
        )
        st.plotly_chart(fig, width="stretch", config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)
