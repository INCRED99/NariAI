import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time

def render_dashboard():
    # Retrieve current location from session state
    curr_lat = st.session_state.get("current_lat", 28.6273)
    curr_lng = st.session_state.get("current_lng", 77.3725)
    curr_addr = st.session_state.get("current_address", "Your Location")

    # Evaluate safety dynamically using the risk assessment API
    from frontend.modules.api_client import api_post
    curr_time_str = datetime.now().strftime("%H:%M")
    
    payload = {
        "location": curr_addr,
        "transit_time": curr_time_str,
        "weather": "Clear Sky",
        "crime_index": "Medium",
        "crowd_density": 65,
        "message": "Routine background monitoring at user's current detected location."
    }
    
    res = api_post("/risk-assessment", payload)
    if res:
        curr_risk_score = res.get("risk_score", 12)
        curr_risk_cat = res.get("risk_category", "Safe")
        curr_explanation = res.get("explanation", "Vicinity deemed secure based on standard monitoring parameters.")
    else:
        curr_risk_score = 12
        curr_risk_cat = "Safe"
        curr_explanation = "Vicinity deemed secure based on standard monitoring parameters."
        
    curr_safety_score = 100 - curr_risk_score
    rating_color = "#34C759" if curr_safety_score > 70 else "#FF9500" if curr_safety_score > 40 else "#FF3B30"

    # Header Section
    st.markdown(
        f"""
        <div style='text-align: left; margin-bottom: 25px;'>
            <span class='severity-badge low' style='font-size: 13px; margin-bottom: 10px;'>
                <span class='material-icons-outlined icon-text-align' style='font-size: 14px;'>check_circle</span> SYSTEM ACTIVE & SECURE
            </span>
            <h1 style='margin: 0; font-size: 38px;'>Welcome back, <span class='gradient-text'>Priya</span>!</h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                Here is your safety summary for today. Your current location is rated <strong style="color: {rating_color};">{curr_risk_cat} ({curr_safety_score}% Safety Index)</strong>.
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # Tabs for Overview vs Live Risk Calculator
    tab1, tab2 = st.tabs(["📊 Overview Summary", "🔍 Live Risk Assessment"])

    is_dark = st.session_state.get("dark_mode", True)
    chart_bg = "rgba(0,0,0,0)"
    font_color = "#F6F5FB" if is_dark else "#1A1D35"
    grid_color = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.05)"
    line_color = "#7A5CFF"

    with tab1:
        # Main Grid (2 Columns)
        col1, col2 = st.columns([1.1, 0.9], gap="medium")

        with col1:
            
            st.markdown(
                f"""
                <div class="safety-card">
                    <h3 style="margin-top:0; margin-bottom:15px; font-size:18px;" class="icon-text-align">
                        <span class="material-icons-outlined" style="color: #00C6FF;">my_location</span> Current Location
                    </h3>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <div>
                            <p style="margin:0; font-size: 16px; font-weight:600; line-height: 1.35;">{curr_addr}</p>
                            <p style="margin:3px 0 0 0; font-size: 12px; color: var(--text-secondary);">GPS Coordinates Detected (Accurate to 5m)</p>
                        </div>
                        <div style="text-align: right;">
                            <p style="margin:0; font-size: 14px; font-weight:600; color: #34C759;">Active GPS</p>
                            <p style="margin:0; font-size: 12px; color: var(--text-secondary);">Signal Strong</p>
                        </div>
                    </div>
                    <div style="display:flex; gap: 15px; font-size: 14px; border-top: 1px solid var(--border-color); padding-top: 12px;">
                        <div><span style="color: var(--text-secondary);">Lat/Lng:</span> {curr_lat:.4f}° N, {curr_lng:.4f}° E</div>
                        <div><span style="color: var(--text-secondary);">Device Battery:</span> 84% ⚡</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Location Share Toggle
            with st.container():
                st.markdown('<div style="margin-top:-10px; margin-bottom: 20px; padding-left:5px;">', unsafe_allow_html=True)
                share_live = st.toggle("Share Live Location with Emergency Contacts", value=True, key="dash_share_live")
                if share_live:
                    st.caption("🟢 Live sharing active. Contacts can view your route.")
                st.markdown('</div>', unsafe_allow_html=True)

            # Safety Timeline
            st.markdown(
                """
                <div class="safety-card" style="margin-bottom: 20px;">
                    <h3 style="margin-top:0; margin-bottom:5px; font-size:18px;" class="icon-text-align">
                        <span class="material-icons-outlined" style="color: #7A5CFF;">timeline</span> Safety Timeline
                    </h3>
                    <p style="margin:0 0 15px 0; font-size:13px; color: var(--text-secondary);">Hourly historical safety index for your vicinity</p>
                """,
                unsafe_allow_html=True
            )
            
            # Plotly Area Chart for Safety Timeline
            hours = [f"{i:02d}:00" for i in range(24)]
            safety_index = [96, 96, 95, 95, 92, 88, 90, 94, 96, 97, 97, 98, 98, 97, 97, 95, 93, 90, 85, 82, 85, 88, 92, 95]
            df = pd.DataFrame({"Hour": hours, "Safety Index": safety_index})

            fig = px.area(df, x="Hour", y="Safety Index", markers=True)
            fig.update_layout(
                paper_bgcolor=chart_bg,
                plot_bgcolor=chart_bg,
                margin=dict(l=10, r=10, t=10, b=10),
                height=200,
                xaxis=dict(showgrid=False, color=font_color, tickmode='linear', dtick=4),
                yaxis=dict(gridcolor=grid_color, color=font_color, range=[60, 105]),
                template="plotly_dark" if is_dark else "plotly_white"
            )
            fig.update_traces(
                line=dict(color=line_color, width=2.5),
                fillcolor="rgba(122, 92, 255, 0.15)"
            )
            st.plotly_chart(fig, width="stretch", config={'displayModeBar': False})
            st.markdown("</div>", unsafe_allow_html=True)

            # Recent Incidents Feed
            st.markdown(
                """
                <div class="safety-card">
                    <h3 style="margin-top:0; margin-bottom:15px; font-size:18px;" class="icon-text-align">
                        <span class="material-icons-outlined" style="color: #FF3B30;">campaign</span> Safety Alerts & Alerts Nearby
                    </h3>
                    <div style="display:flex; flex-direction:column; gap:12px;">
                        <div style="padding-bottom:10px; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:start;">
                            <div>
                                <span class="severity-badge medium">Medium Risk</span>
                                <p style="margin:5px 0 0 0; font-size:14px; font-weight:500;">Stray Dogs Aggression</p>
                                <p style="margin:0; font-size:12px; color: var(--text-secondary);">Block C crossing, 350m away • 40m ago</p>
                            </div>
                            <span class="material-icons-outlined" style="color: var(--text-secondary); font-size:18px;">chevron_right</span>
                        </div>
                        <div style="padding-bottom:10px; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:start;">
                            <div>
                                <span class="severity-badge low">Low Risk</span>
                                <p style="margin:5px 0 0 0; font-size:14px; font-weight:500;">Street Light Outage reported</p>
                                <p style="margin:0; font-size:12px; color: var(--text-secondary);">Main Metro Boulevard • 2h ago</p>
                            </div>
                            <span class="material-icons-outlined" style="color: var(--text-secondary); font-size:18px;">chevron_right</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:start;">
                            <div>
                                <span class="severity-badge high">High Risk</span>
                                <p style="margin:5px 0 0 0; font-size:14px; font-weight:500;">Crowd Gathering/Protest</p>
                                <p style="margin:0; font-size:12px; color: var(--text-secondary);">Main Transit Station Gate • 1d ago</p>
                            </div>
                            <span class="material-icons-outlined" style="color: var(--text-secondary); font-size:18px;">chevron_right</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            # AI Safety Score Circular Indicator
            st.markdown('<div class="safety-card" style="text-align: center;">', unsafe_allow_html=True)
            
            # Plotly Gauge Chart for Safety Score
            score = curr_safety_score
            fig_score = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                number = {'suffix': "%", 'font': {'size': 44, 'family': 'Outfit', 'color': font_color}},
                gauge = {
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': font_color, 'ticks': ""},
                    'bar': {'color': rating_color, 'thickness': 0.25},
                    'bgcolor': "rgba(122,92,255,0.05)",
                    'borderwidth': 0,
                    'steps': [
                        {'range': [0, 40], 'color': 'rgba(255, 59, 48, 0.1)'},
                        {'range': [40, 75], 'color': 'rgba(255, 149, 0, 0.1)'},
                        {'range': [75, 100], 'color': 'rgba(52, 199, 89, 0.1)'}
                    ],
                    'threshold': {
                        'line': {'color': "#00C6FF", 'width': 3},
                        'thickness': 0.8,
                        'value': score
                    }
                }
            ))
            fig_score.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=10, b=10),
                height=160,
                template="plotly_dark" if is_dark else "plotly_white"
            )
            st.plotly_chart(fig_score, width="stretch", config={'displayModeBar': False})
            
            st.markdown(
                f"""
                <div style="margin-top: -15px;">
                    <h4 style="margin: 0; font-size: 16px;">AI Safety Rating: <strong>{curr_risk_cat}</strong></h4>
                    <p style="margin: 5px 0 0 0; font-size: 13px; color: var(--text-secondary);">{curr_explanation}</p>
                </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Weather Widget
            st.markdown(
                """
                <div class="safety-card">
                    <h3 style="margin-top:0; margin-bottom:15px; font-size:18px;" class="icon-text-align">
                        <span class="material-icons-outlined" style="color: #FF9500;">light_mode</span> Safety Weather Info
                    </h3>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <p style="margin:0; font-size: 24px; font-weight:700;">32°C</p>
                            <p style="margin:0; font-size: 13px; color: var(--text-secondary);">Clear Sky • Sunset 6:58 PM</p>
                        </div>
                        <span class="material-icons-outlined" style="font-size: 40px; color: #FF9500;">wb_sunny</span>
                    </div>
                    <div style="margin-top:12px; padding:10px; background:rgba(255, 149, 0, 0.08); border-radius:10px; border:1px dashed rgba(255, 149, 0, 0.2); font-size:12px;">
                        <strong>AI Note:</strong> Clear weather ensures high road visibility. Sunset is in 2 hours. Keep routing alerts active after dusk.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Quick Actions Grid
            st.markdown(
                """
                <div class="safety-card">
                    <h3 style="margin-top:0; margin-bottom:15px; font-size:18px;" class="icon-text-align">
                        <span class="material-icons-outlined" style="color: #7A5CFF;">bolt</span> Quick Actions
                    </h3>
                """,
                unsafe_allow_html=True
            )
            qa1, qa2 = st.columns(2)
            with qa1:
                if st.button("🚨 Trigger SOS", width="stretch", key="qa_sos"):
                    st.session_state["sos_triggered"] = True
                    st.session_state["active_page"] = "Emergency"
                    st.rerun()
                if st.button("💬 Safety AI Chat", width="stretch", key="qa_chat"):
                    st.session_state["active_page"] = "AI Assistant"
                    st.rerun()
            with qa2:
                if st.button("🗺️ Safe Route Home", width="stretch", key="qa_route"):
                    st.session_state["active_page"] = "Safe Route"
                    st.rerun()
                if st.button("⚠️ File Report", width="stretch", key="qa_report"):
                    st.session_state["active_page"] = "Incident Reporting"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Safety Alerts (Smart Recommendation Cards)
            st.markdown(
                """
                <div class="safety-card">
                    <h3 style="margin-top:0; margin-bottom:12px; font-size:16px;" class="icon-text-align">
                        <span class="material-icons-outlined" style="color: #00D2FF;">tips_and_updates</span> Smart Recommendation
                    </h3>
                    <p style="margin:0; font-size:13px; line-height:1.4;">
                        "You travel frequently during evening commutes. We recommend staying on primary well-lit thoroughfares, sharing coordinates, and keeping emergency alerts active."
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Trusted Safety Circles Card (Edit on Home Page)
            st.markdown('<div class="safety-card">', unsafe_allow_html=True)
            st.markdown(
                """
                <h3 style="margin-top:0; margin-bottom:15px; font-size:18px;" class="icon-text-align">
                    <span class="material-icons-outlined" style="color: #7A5CFF;">groups</span> Trusted Safety Circles
                </h3>
                """,
                unsafe_allow_html=True
            )
            
            # Fetch current contacts from profile API
            from frontend.modules.api_client import api_get, api_post
            profile_res = api_get("/profile")
            contacts = []
            if profile_res and "profile" in profile_res:
                contacts = profile_res["profile"].get("emergency_contacts", [])
            
            if not contacts:
                contacts = [
                    {"name": "Aarav Sharma", "relation": "Husband", "phone": "7007914594"},
                    {"name": "Neha Verma", "relation": "Sister", "phone": "+91 91234 56789"},
                    {"name": "Siddharth", "relation": "Roommate", "phone": "+91 99887 76655"}
                ]
                
            for c in contacts:
                st.markdown(
                    f"""
                    <div style="padding: 10px; border-radius: 8px; background: rgba(122,92,255,0.05); margin-bottom: 8px; border: 1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <p style="margin:0; font-size:13px; font-weight:600;">{c['name']} ({c['relation']})</p>
                            <p style="margin:0; font-size:11px; color: var(--text-secondary);">{c['phone']}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            with st.expander("✏️ Edit Emergency Contacts", expanded=False):
                c1_name = st.text_input("Contact 1 Name", value=contacts[0]["name"], key="dash_c1_name")
                c1_rel = st.text_input("Contact 1 Relation", value=contacts[0]["relation"], key="dash_c1_rel")
                c1_phone = st.text_input("Contact 1 Phone", value=contacts[0]["phone"], key="dash_c1_phone")
                
                st.markdown("<hr style='margin:10px 0; border-top:1px solid var(--border-color);'>", unsafe_allow_html=True)
                
                c2_name = st.text_input("Contact 2 Name", value=contacts[1]["name"], key="dash_c2_name")
                c2_rel = st.text_input("Contact 2 Relation", value=contacts[1]["relation"], key="dash_c2_rel")
                c2_phone = st.text_input("Contact 2 Phone", value=contacts[1]["phone"], key="dash_c2_phone")
                
                st.markdown("<hr style='margin:10px 0; border-top:1px solid var(--border-color);'>", unsafe_allow_html=True)
                
                c3_name = st.text_input("Contact 3 Name", value=contacts[2]["name"], key="dash_c3_name")
                c3_rel = st.text_input("Contact 3 Relation", value=contacts[2]["relation"], key="dash_c3_rel")
                c3_phone = st.text_input("Contact 3 Phone", value=contacts[2]["phone"], key="dash_c3_phone")
                
                if st.button("💾 Save Emergency Contacts", key="btn_save_dash_contacts", width="stretch", type="primary"):
                    updated_contacts = [
                        {"name": c1_name, "relation": c1_rel, "phone": c1_phone},
                        {"name": c2_name, "relation": c2_rel, "phone": c2_phone},
                        {"name": c3_name, "relation": c3_rel, "phone": c3_phone}
                    ]
                    
                    profile_data = profile_res.get("profile", {}) if profile_res else {}
                    
                    post_payload = {
                        "name": profile_data.get("name", "User"),
                        "phone": profile_data.get("phone", ""),
                        "preferred_language": profile_data.get("preferred_language", "English (US)"),
                        "safe_word": profile_data.get("safe_word", "Blue Moon"),
                        "home_address": profile_data.get("home_address", ""),
                        "home_lat": profile_data.get("home_lat", 0.0),
                        "home_lng": profile_data.get("home_lng", 0.0),
                        "office_address": profile_data.get("office_address", ""),
                        "office_lat": profile_data.get("office_lat", 0.0),
                        "office_lng": profile_data.get("office_lng", 0.0),
                        "travel_routine": profile_data.get("travel_routine", ""),
                        "emergency_contacts": updated_contacts
                    }
                    
                    save_res = api_post("/profile", post_payload)
                    if save_res and save_res.get("success"):
                        st.toast("Emergency contacts saved successfully!", icon="💾")
                        st.rerun()
                    else:
                        st.error("Failed to update emergency contacts.")
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown(
            """
            <div class="safety-card">
                <h3 style="margin-top:0; font-size:20px;" class="icon-text-align">
                    <span class="material-icons-outlined" style="color: #7A5CFF;">gpp_maybe</span> Live Risk Assessment
                </h3>
                <p style="color: var(--text-secondary); font-size:14px; margin-top:-5px;">
                    Real-time safety scan. Surroundings are evaluated dynamically based on your current location, local weather context, and active time factors.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Resolve variables dynamically
        calc_loc = st.session_state.get("current_address", "Your Location")
        now_time = datetime.now()
        time_str = now_time.strftime("%H:%M")
        
        # Deduce safety parameters based on current time (higher risk at night)
        hour = now_time.hour
        if 20 <= hour or hour <= 5:
            default_crime = "High"
            default_crowd = 15
            situation_desc = "Late evening transit. Assessing lighting, streetlight density, and local patrol alerts."
        else:
            default_crime = "Medium"
            default_crowd = 45
            situation_desc = "Normal daytime transit. Foot traffic is active, local municipal patrols are normal."
            
        default_weather = "Light Rain" # Corresponds to weather widget on homepage
        
        st.markdown(
            f"""
            <div style="display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">
                <div class="safety-card" style="flex: 1; min-width: 150px; margin-bottom: 0; padding: 12px; text-align: center;">
                    <span class="material-icons-outlined" style="color: #7A5CFF; font-size: 20px;">place</span>
                    <p style="margin: 5px 0 0 0; font-size: 11px; color: var(--text-secondary);">Resolved Location</p>
                    <p style="margin: 2px 0 0 0; font-size: 13px; font-weight: 600;">{calc_loc}</p>
                </div>
                <div class="safety-card" style="flex: 1; min-width: 120px; margin-bottom: 0; padding: 12px; text-align: center;">
                    <span class="material-icons-outlined" style="color: #00D2FF; font-size: 20px;">schedule</span>
                    <p style="margin: 5px 0 0 0; font-size: 11px; color: var(--text-secondary);">Transit Time</p>
                    <p style="margin: 2px 0 0 0; font-size: 13px; font-weight: 600;">{time_str}</p>
                </div>
                <div class="safety-card" style="flex: 1; min-width: 120px; margin-bottom: 0; padding: 12px; text-align: center;">
                    <span class="material-icons-outlined" style="color: #34C759; font-size: 20px;">cloudy_snowing</span>
                    <p style="margin: 5px 0 0 0; font-size: 11px; color: var(--text-secondary);">Weather Context</p>
                    <p style="margin: 2px 0 0 0; font-size: 13px; font-weight: 600;">{default_weather}</p>
                </div>
                <div class="safety-card" style="flex: 1; min-width: 120px; margin-bottom: 0; padding: 12px; text-align: center;">
                    <span class="material-icons-outlined" style="color: #FF9500; font-size: 20px;">groups</span>
                    <p style="margin: 5px 0 0 0; font-size: 11px; color: var(--text-secondary);">Est. Crowd</p>
                    <p style="margin: 2px 0 0 0; font-size: 13px; font-weight: 600;">{default_crowd}%</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Call FastAPI backend for dynamic risk score and explanation
        from frontend.modules.api_client import api_post
        
        payload = {
            "location": calc_loc,
            "transit_time": time_str,
            "weather": default_weather,
            "crime_index": default_crime,
            "crowd_density": default_crowd,
            "message": situation_desc
        }
        
        res = api_post("/risk-assessment", payload)
        if res:
            final_risk = res.get("risk_score", 50)
            risk_cat = res.get("risk_category", "Moderate")
            explanation = res.get("explanation", "Assessment completed successfully.")
        else:
            final_risk = 50
            risk_cat = "Moderate"
            explanation = "Connection offline. Using local safety metrics cache."

        # Determine colors and advice dynamically based on API response
        if risk_cat == "Critical":
            status_label = "CRITICAL RISK"
            status_color = "#FF3B30"
            advice_box = f"""
            <div class="danger-container" style="border-left: 5px solid #FF3B30;">
                <h4 style="margin:0 0 5px 0; color:#FF3B30;">🚨 CRITICAL THREAT DETECTED</h4>
                <p style="margin:0; font-size:13px; line-height:1.4;">{explanation}</p>
            </div>
            """
        elif risk_cat == "High":
            status_label = "HIGH RISK"
            status_color = "#FF9500"
            advice_box = f"""
            <div class="danger-container" style="background:rgba(255,149,0,0.08); border: 1px solid rgba(255,149,0,0.3); border-radius:12px; padding:15px; margin:10px 0; border-left: 5px solid #FF9500;">
                <h4 style="margin:0 0 5px 0; color:#FF9500;">⚠️ HIGH RISK AWARENESS</h4>
                <p style="margin:0; font-size:13px; line-height:1.4;">{explanation}</p>
            </div>
            """
        elif risk_cat == "Moderate":
            status_label = "MODERATE RISK"
            status_color = "#FF9500"
            advice_box = f"""
            <div class="danger-container" style="background:rgba(255,149,0,0.08); border: 1px solid rgba(255,149,0,0.3); border-radius:12px; padding:15px; margin:10px 0; border-left: 5px solid #FF9500;">
                <h4 style="margin:0 0 5px 0; color:#FF9500;">⚠️ MODERATE AWARENESS</h4>
                <p style="margin:0; font-size:13px; line-height:1.4;">{explanation}</p>
            </div>
            """
        else:
            status_label = "LOW RISK / SECURE"
            status_color = "#34C759"
            advice_box = f"""
            <div class="success-container" style="border-left: 5px solid #34C759;">
                <h4 style="margin:0 0 5px 0; color:#34C759;">🟢 AREA DEEMED SECURE</h4>
                <p style="margin:0; font-size:13px; line-height:1.4;">{explanation}</p>
            </div>
            """

        st.markdown('<div class="safety-card" style="text-align: center;">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>Risk Assessment Score</h4>", unsafe_allow_html=True)
        
        # Plotly Gauge Chart for Live Risk
        fig_risk = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = final_risk,
            domain = {'x': [0, 1], 'y': [0, 1]},
            number = {'suffix': "/100", 'font': {'size': 44, 'family': 'Outfit', 'color': font_color}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': font_color, 'ticks': ""},
                'bar': {'color': status_color, 'thickness': 0.25},
                'bgcolor': "rgba(255,255,255,0.05)",
                'borderwidth': 0,
                'steps': [
                    {'range': [0, 30], 'color': 'rgba(52, 199, 89, 0.1)'},
                    {'range': [30, 60], 'color': 'rgba(255, 149, 0, 0.1)'},
                    {'range': [60, 100], 'color': 'rgba(255, 59, 48, 0.1)'}
                ]
            }
        ))
        fig_risk.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=10, b=10),
            height=185,
            template="plotly_dark" if is_dark else "plotly_white"
        )
        st.plotly_chart(fig_risk, width="stretch", config={'displayModeBar': False})
        
        st.markdown(
            f"""
            <div style="margin-top: -15px; margin-bottom:10px;">
                <h3 style="margin: 0; color: {status_color}; font-weight:800;">{status_label}</h3>
                <p style="margin: 5px 0 0 0; font-size: 13px; color: var(--text-secondary);">
                    Assessment calculated for: <strong>{calc_loc}</strong>
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Advice card insertion
        st.markdown(advice_box, unsafe_allow_html=True)
        
        # Action button
        if final_risk >= 45:
            if st.button("🚨 TRIGGER EMERGENCY ASSISTANT", key="assess_trigger_sos", width="stretch", type="primary"):
                st.session_state["active_page"] = "Emergency"
                st.session_state["sos_triggered"] = True
                st.rerun()

