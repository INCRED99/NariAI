import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from frontend.modules.api_client import api_post

def render_route_safety():
    # Page Header
    st.markdown(
        """
        <div style='text-align: left; margin-bottom: 25px;'>
            <h1 style='margin: 0; font-size: 38px;'><span class='gradient-text'>Route Safety Analyzer</span></h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                Compare route alternatives based on lighting density, active police coverage, and community safety logs.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Fetch profile for coordinates if needed
    from frontend.modules.api_client import api_get
    profile_res = api_get("/profile")
    profile_db = profile_res.get("profile", {}) if profile_res else {}

    # Search inputs container
    st.markdown('<div class="safety-card">', unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns([1.2, 1.2, 0.8])
    with sc1:
        default_origin = st.session_state.get("current_address", "Your Location")
        origin = st.text_input("Origin", value=default_origin, placeholder="Enter starting point...")
    with sc2:
        default_dest = profile_db.get("office_address", "Office Address")
        destination = st.text_input("Destination", value=default_dest, placeholder="Enter destination...")
    with sc3:
        from datetime import datetime
        sel_time = st.time_input("Departure Time", value=datetime.now().time(), key="route_transit_time")
    st.markdown('</div>', unsafe_allow_html=True)

    # Resolve coordinates for origin
    origin_lat = None
    origin_lng = None
    current_addr = st.session_state.get("current_address", "Your Location")
    if origin == current_addr or origin == "Your Location":
        origin_lat = st.session_state.get("current_lat", 28.6273)
        origin_lng = st.session_state.get("current_lng", 77.3725)
    elif "home" in origin.lower():
        origin_lat = profile_db.get("home_lat", 28.6273)
        origin_lng = profile_db.get("home_lng", 77.3725)

    # Resolve coordinates for destination
    dest_lat = None
    dest_lng = None
    if "office" in destination.lower():
        dest_lat = profile_db.get("office_lat", 28.5730)
        dest_lng = profile_db.get("office_lng", 77.3220)
    elif "home" in destination.lower():
        dest_lat = profile_db.get("home_lat", 28.6273)
        dest_lng = profile_db.get("home_lng", 77.3725)

    # Call backend API
    payload = {
        "origin": origin,
        "destination": destination,
        "time_of_day": sel_time.strftime("%H:%M") if hasattr(sel_time, "strftime") else str(sel_time),
        "origin_lat": origin_lat,
        "origin_lng": origin_lng,
        "dest_lat": dest_lat,
        "dest_lng": dest_lng
    }
    
    with st.spinner("Analyzing routes via AI Safety Core..."):
        res = api_post("/safe-routes", payload)

    if not res or "routes" not in res:
        st.error("Could not fetch route safety recommendations from the backend.")
        return

    routes = res.get("routes", [])
    
    # Render routes choice
    routes_mapping = {r["description"]: r for r in routes}
    
    # Main columns
    col_map, col_details = st.columns([1.5, 1.3], gap="medium")

    with col_details:
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>Select Route</h4>", unsafe_allow_html=True)
        
        # Route select toggle
        route_choice = st.radio(
            "Route Type",
            list(routes_mapping.keys()),
            index=0,
            label_visibility="collapsed"
        )
        
        selected_route = routes_mapping[route_choice]
        metrics = selected_route["metrics"]
        risk_score = metrics["safety_score"]
        
        # Risk gauge chart
        is_dark = st.session_state.get("dark_mode", True)
        font_color = "#F6F5FB" if is_dark else "#1A1D35"
        risk_color = "#34C759" if risk_score > 70 else "#FF9500" if risk_score > 40 else "#FF3B30"
        
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = risk_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            number = {'suffix': "/100 Safety", 'font': {'size': 24, 'family': 'Outfit', 'color': font_color}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': font_color, 'ticks': ""},
                'bar': {'color': risk_color, 'thickness': 0.3},
                'bgcolor': "rgba(255,255,255,0.05)",
                'borderwidth': 0,
                'steps': [
                    {"range": [0, 45], "color": "rgba(255, 59, 48, 0.1)"},
                    {"range": [45, 75], "color": "rgba(255, 149, 0, 0.1)"},
                    {"range": [75, 100], "color": "rgba(52, 199, 89, 0.1)"}
                ]
            }
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            height=110,
            template="plotly_dark" if is_dark else "plotly_white"
        )
        st.plotly_chart(fig, width="stretch", config={'displayModeBar': False})
        
        # Explain why
        color_header = "#34C759" if risk_score > 60 else "#FF3B30"
        prefix_header = "🟢 Why recommended:" if risk_score > 60 else "⚠️ Safe Alerts & Warnings:"
        
        st.markdown(
            f"""
            <div style="padding:15px; background:rgba(122,92,255,0.05); border-radius:10px; border:1px solid var(--border-color); font-size:13px; margin-bottom: 15px; line-height:1.45;">
                <strong style="color:{color_header}; font-size:14px;">{prefix_header}</strong><br>
                {selected_route['explanation_html']}
            </div>
            """,
            unsafe_allow_html=True
        )
            
        st.markdown("</div>", unsafe_allow_html=True)

        # Route Comparison Table
        st.markdown(
            f"""
            <div class="safety-card">
                <h4 style="margin-top:0; margin-bottom:10px;">Route Comparison Parameters</h4>
                <table class="route-compare-table">
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>{routes[1]["category"]} (Short)</th>
                            <th>{routes[0]["category"]} (Safe)</th>
                            <th>{routes[2]["category"]} (Balanced)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Duration</strong></td>
                            <td>{routes[1]["metrics"]["duration_mins"]} mins</td>
                            <td>{routes[0]["metrics"]["duration_mins"]} mins</td>
                            <td>{routes[2]["metrics"]["duration_mins"]} mins</td>
                        </tr>
                        <tr>
                            <td><strong>Illumination Index</strong></td>
                            <td>{routes[1]["metrics"]["streetlight_density"]}%</td>
                            <td>{routes[0]["metrics"]["streetlight_density"]}%</td>
                            <td>{routes[2]["metrics"]["streetlight_density"]}%</td>
                        </tr>
                        <tr>
                            <td><strong>PCR Police Stand</strong></td>
                            <td>{routes[1]["metrics"]["police_booths"]}</td>
                            <td>{routes[0]["metrics"]["police_booths"]}</td>
                            <td>{routes[2]["metrics"]["police_booths"]}</td>
                        </tr>
                        <tr>
                            <td><strong>CCTV Zones</strong></td>
                            <td>{routes[1]["metrics"]["cctv_zones"]}</td>
                            <td>{routes[0]["metrics"]["cctv_zones"]}</td>
                            <td>{routes[2]["metrics"]["cctv_zones"]}</td>
                        </tr>
                        <tr>
                            <td><strong>Foot Density</strong></td>
                            <td>{routes[1]["metrics"]["foot_traffic"]}</td>
                            <td>{routes[0]["metrics"]["foot_traffic"]}</td>
                            <td>{routes[2]["metrics"]["foot_traffic"]}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_map:
        # Offline POI Definitions
        police_stations = [
            {"name": "Sector 62 Police Post", "lat": 28.6250, "lng": 77.3650},
            {"name": "Sector 58 Police Station", "lat": 28.6050, "lng": 77.3520},
            {"name": "Sector 20 District HQ", "lat": 28.5780, "lng": 77.3200}
        ]
        
        hospitals = [
            {"name": "Fortis Hospital Emergency", "lat": 28.6210, "lng": 77.3700},
            {"name": "Kailash Hospital Emergency", "lat": 28.5800, "lng": 77.3280}
        ]

        gmaps_key = st.session_state.get("gmaps_key", "").strip()
        if gmaps_key:
            map_url = f"https://www.google.com/maps/embed/v1/directions?key={gmaps_key}&origin={origin}&destination={destination}"
            st.markdown('<div class="safety-card" style="padding: 10px; margin-bottom: 20px;">', unsafe_allow_html=True)
            st.markdown(
                f"""
                <iframe
                    width="100%"
                    height="480"
                    style="border:0; border-radius:12px;"
                    loading="lazy"
                    allowfullscreen
                    src="{map_url}">
                </iframe>
                """,
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            # Create Folium Map
            tileset = "CartoDB dark_matter" if is_dark else "CartoDB positron"
            
            # Initialize map centered on starting origin coordinate
            path_coords = selected_route["path"]
            m = folium.Map(location=path_coords[0], zoom_start=13, tiles=tileset, zoom_control=False)
            
            # Origin Marker
            folium.Marker(
                location=path_coords[0],
                popup=f"Origin: {origin}",
                icon=folium.Icon(color="green", icon="play", prefix="fa")
            ).add_to(m)

            # Destination Marker
            folium.Marker(
                location=path_coords[-1],
                popup=f"Destination: {destination}",
                icon=folium.Icon(color="blue", icon="stop", prefix="fa")
            ).add_to(m)

            # Draw paths based on selection
            # Highlight active route and draw alternative dotted line
            path_color = "#34C759" if risk_score > 60 else "#FF3B30"
            folium.PolyLine(
                locations=path_coords,
                color=path_color,
                weight=6,
                opacity=0.9,
                tooltip=f"{selected_route['category']} Route Path"
            ).add_to(m)
            
            # Draw dotted lines for the other two routes
            for r_name, r in routes_mapping.items():
                if r_name != route_choice:
                    folium.PolyLine(
                        locations=r["path"],
                        color="#9E9EAF",
                        weight=3,
                        opacity=0.4,
                        dash_array="5, 10"
                    ).add_to(m)

            # Draw POIs on the map
            for ps in police_stations:
                folium.Marker(
                    location=[ps["lat"], ps["lng"]],
                    popup=f"Police: {ps['name']}",
                    icon=folium.Icon(color="cadetblue", icon="shield", prefix="fa")
                ).add_to(m)

            for hosp in hospitals:
                folium.Marker(
                    location=[hosp["lat"], hosp["lng"]],
                    popup=f"Hospital: {hosp['name']}",
                    icon=folium.Icon(color="red", icon="plus")
                ).add_to(m)

            # Render Map in glassmorphic container
            st.markdown('<div class="safety-card" style="padding: 10px; margin-bottom: 20px;">', unsafe_allow_html=True)
            st_folium(m, height=480, width=700, returned_objects=[])
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Support POIs list below the map
        st.markdown('<div class="safety-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0; margin-bottom:10px;'>Active Emergency Safeguards</h4>", unsafe_allow_html=True)
        
        poi_type = st.segmented_control("Filter Stations", ["Police Booths", "Medical Centers"], default="Police Booths", key="route_poi_filter")
        
        if poi_type == "Police Booths":
            for ps in police_stations:
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-color);">
                        <div>
                            <p style="margin:0; font-size:13px; font-weight:600;">{ps['name']}</p>
                            <p style="margin:0; font-size:11px; color: var(--text-secondary);">PCR Patrolling Cover Active</p>
                        </div>
                        <span class="severity-badge low" style="font-size:10px; background:rgba(0,198,255,0.1); color:#00C6FF; border:1px solid rgba(0,198,255,0.2);">Patrolling Active</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            for hosp in hospitals:
                st.markdown(
                    f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-color);">
                        <div>
                            <p style="margin:0; font-size:13px; font-weight:600;">{hosp['name']}</p>
                            <p style="margin:0; font-size:11px; color: var(--text-secondary);">Trauma ER and ambulance ready</p>
                        </div>
                        <span class="severity-badge low" style="font-size:10px; background:rgba(52,199,89,0.1); color:#34C759; border:1px solid rgba(52,199,89,0.2);">24/7 Open</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.markdown("</div>", unsafe_allow_html=True)
