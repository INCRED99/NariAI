import streamlit as st
import folium
from streamlit_folium import st_folium
from frontend.modules.api_client import api_get

def render_nearby_places():
    # Page Header
    st.markdown(
        """
        <div style='text-align: left; margin-bottom: 25px;'>
            <h1 style='margin: 0; font-size: 38px;'><span class='gradient-text'>Nearby Safe Havens</span></h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                Instantly track local police booths, emergency centers, 24h pharmacies, and safe public spots ranked by security rating.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Categories
    categories = ["Police Station", "Hospital", "Pharmacy", "Metro", "Public Places"]
    
    # Initialize states
    if "selected_category" not in st.session_state:
        st.session_state["selected_category"] = "Police Station"
    if "active_nav_place" not in st.session_state:
        st.session_state["active_nav_place"] = None

    # Segmented navigation menu
    sel_cat = st.segmented_control("Select Category", categories, default=st.session_state["selected_category"])
    if sel_cat and sel_cat != st.session_state["selected_category"]:
        st.session_state["selected_category"] = sel_cat
        st.session_state["active_nav_place"] = None
        st.rerun()

    # User coordinate location (from Geolocation or default Noida)
    user_lat = st.session_state.get("current_lat", 28.6273)
    user_lng = st.session_state.get("current_lng", 77.3725)

    # Check settings for custom GPS override (e.g. Connaught Place CP)
    calc_loc_val = st.session_state.get("current_address", "Your Location")
    if "connaught" in calc_loc_val.lower() or "cp" in calc_loc_val.lower():
        user_lat = 28.6304
        user_lng = 77.2177

    # Fetch safe spots from backend API
    params = {
        "latitude": user_lat,
        "longitude": user_lng,
        "category": st.session_state["selected_category"]
    }
    
    with st.spinner("Finding safe havens nearby..."):
        processed_places = api_get("/nearby-places", params)

    if processed_places is None:
        st.error("Failed to fetch nearby safe places from backend.")
        return

    # Grid layout: Map on left, ranked list on right
    col_map, col_list = st.columns([1.5, 1.3], gap="medium")

    with col_list:
        st.markdown(
            f"""
            <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                <span class='severity-badge low' style='font-size: 12px; background: rgba(52,199,89,0.1); color:#34C759; border: 1px solid rgba(52,199,89,0.2);'>
                    {len(processed_places)} Safe Havens Found
                </span>
                <span style="font-size:12px; color: var(--text-secondary);">Ranked by proximity & security</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        for idx, place in enumerate(processed_places):
            rank_label = f"#{idx+1} Safe Haven"
            if idx == 0:
                rank_badge = f"<span class='severity-badge low' style='font-size: 10px; background: rgba(52,199,89,0.15); color: #34C759; border: 1px solid #34C759;'>🏆 {rank_label} (Best Choice)</span>"
            elif idx == 1:
                rank_badge = f"<span class='severity-badge low' style='font-size: 10px; background: rgba(0,198,255,0.1); color: #00C6FF; border: 1px solid #00C6FF;'>🥈 {rank_label}</span>"
            else:
                rank_badge = f"<span class='severity-badge low' style='font-size: 10px;'>🥉 {rank_label}</span>"

            st.markdown(
                f"""
                <div class="safety-card" style="margin-bottom: 15px; border-top: 3px solid #7A5CFF;">
                    <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom: 6px;">
                        <div>
                            <h4 style="margin:0 0 3px 0; font-size:16px; font-weight:700;">{place['name']}</h4>
                            {rank_badge}
                        </div>
                        <div style="text-align:right;">
                            <span class="severity-badge low" style="white-space:nowrap; background:rgba(122,92,255,0.08); border-color:transparent;">{place['distance_km']:.2f} km away</span>
                            <div style="font-size:13px; font-weight:700; color:#7A5CFF; margin-top:5px;">Security: {place['safety_score']}/100</div>
                        </div>
                    </div>
                    <p style="margin:0 0 10px 0; font-size:12px; color:var(--text-secondary); line-height:1.4;">{place['desc']}</p>
                    <div style="font-size:12px; margin-bottom:12px; color: var(--text-secondary);" class="icon-text-align">
                        <span class="material-icons-outlined" style="font-size:14px; color:#34C759;">phone</span>
                        <span>Contact: <strong>{place['phone']}</strong></span>
                    </div>
                """,
                unsafe_allow_html=True
            )
            
            # Navigation trigger
            btn_key = f"hav_nav_{st.session_state['selected_category'].replace(' ', '')}_{idx}"
            is_active = (st.session_state["active_nav_place"] == place["name"])
            btn_label = "📍 Safe Path Active" if is_active else "🧭 Render Route Path"
            
            if st.button(btn_label, key=btn_key, use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state["active_nav_place"] = place["name"]
                st.toast(f"Plotting safe path to {place['name']}", icon="🧭")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with col_map:
        gmaps_key = st.session_state.get("gmaps_key", "").strip()
        
        # Check active nav place
        active_place_obj = None
        for place in processed_places:
            if st.session_state["active_nav_place"] == place["name"]:
                active_place_obj = place
                break

        if gmaps_key:
            # Build Google Maps Embed iframe URL
            if active_place_obj:
                # Directions map from user to selected safe haven
                map_url = f"https://www.google.com/maps/embed/v1/directions?key={gmaps_key}&origin={user_lat},{user_lng}&destination={active_place_obj['lat']},{active_place_obj['lng']}&mode=walking"
            else:
                # Search map showing safe havens of selected category
                search_q = f"{st.session_state['selected_category']}"
                map_url = f"https://www.google.com/maps/embed/v1/search?key={gmaps_key}&q={search_q}+near+{user_lat},{user_lng}&zoom=15"
                
            st.markdown('<div class="safety-card" style="padding: 10px; margin-bottom: 0;">', unsafe_allow_html=True)
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
            # Folium fallback
            is_dark = st.session_state.get("dark_mode", True)
            tileset = "CartoDB dark_matter" if is_dark else "CartoDB positron"
            
            m = folium.Map(location=[user_lat, user_lng], zoom_start=15, tiles=tileset, zoom_control=False)
            
            # User Marker
            folium.Marker(
                location=[user_lat, user_lng],
                popup="Priya (My Location)",
                icon=folium.Icon(color="purple", icon="user", prefix="fa")
            ).add_to(m)

            # Place Markers
            for place in processed_places:
                marker_color = "red"
                icon_name = "question"
                cat = st.session_state["selected_category"]
                if cat == "Police Station":
                    marker_color = "cadetblue"
                    icon_name = "shield"
                elif cat == "Hospital":
                    marker_color = "red"
                    icon_name = "plus-sign"
                elif cat == "Pharmacy":
                    marker_color = "green"
                    icon_name = "leaf"
                elif cat == "Metro":
                    marker_color = "blue"
                    icon_name = "road"
                elif cat == "Public Places":
                    marker_color = "orange"
                    icon_name = "star"
                    
                folium.Marker(
                    location=[place["lat"], place["lng"]],
                    popup=place["name"],
                    icon=folium.Icon(color=marker_color, icon=icon_name)
                ).add_to(m)

            # Draw path if active
            if active_place_obj:
                folium.PolyLine(
                    locations=active_place_obj["path"],
                    color="#00C6FF",
                    weight=6,
                    opacity=0.85,
                    tooltip=f"Safe Path to {active_place_obj['name']}"
                ).add_to(m)
                
                # Focus map halfway
                mid_lat = (user_lat + active_place_obj["lat"]) / 2
                mid_lng = (user_lng + active_place_obj["lng"]) / 2
                m.location = [mid_lat, mid_lng]

            st.markdown('<div class="safety-card" style="padding: 10px; margin-bottom: 0;">', unsafe_allow_html=True)
            st_folium(m, height=480, width=700, returned_objects=[])
            st.markdown("</div>", unsafe_allow_html=True)
