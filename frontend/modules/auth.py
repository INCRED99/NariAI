import streamlit as st
from frontend.modules.api_client import api_post

def render_auth_page():
    # Inject a gorgeous gradient background/header
    st.markdown(
        """
        <div style='text-align: center; margin-top: 30px; margin-bottom: 30px;'>
            <span class='material-icons-outlined' style='font-size: 55px; background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: pulse-sos 3s infinite;'>shield</span>
            <h1 style='margin: 10px 0 0 0; font-size: 40px;'><span class='gradient-text'>NARI SAFETY HUB</span></h1>
            <p style='color: var(--text-secondary); font-size: 16px; margin-top: 5px;'>
                Your AI-Powered Personal Safety & Security Assistant
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Center the login/registration form
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown("<div class='safety-card'>", unsafe_allow_html=True)
        
        # Use a radio widget styled nicely as a selector
        auth_mode = st.radio("Access Level", ["Sign In", "Sign Up"], horizontal=True, label_visibility="collapsed")
        
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        if auth_mode == "Sign In":
            st.markdown("<h3 style='margin-top:0; font-size:20px;'>Secure Login</h3>", unsafe_allow_html=True)
            email = st.text_input("Email Address", placeholder="name@example.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pwd")
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("🔓 ACCESS SAFETY HUB", width="stretch", type="primary", key="login_btn"):
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner("Authenticating with Firebase secure vault..."):
                        res = api_post("/auth/login", {"email": email, "password": password})
                    if res and res.get("success"):
                        st.session_state["authenticated"] = True
                        st.session_state["idToken"] = res.get("idToken")
                        st.session_state["uid"] = res.get("uid")
                        st.session_state["user_email"] = res.get("email")
                        st.session_state["user_name"] = res.get("name")
                        st.query_params["idToken"] = res.get("idToken")
                        st.query_params["uid"] = res.get("uid")
                        st.query_params["email"] = res.get("email", "")
                        st.query_params["name"] = res.get("name", "User")
                        st.toast(f"Welcome back, {res.get('name')}!", icon="🛡️")
                        st.rerun()
                    else:
                        st.error("Login failed. Please check your credentials.")
                        
        else:
            st.markdown("<h3 style='margin-top:0; font-size:20px;'>Create Secure Profile</h3>", unsafe_allow_html=True)
            name = st.text_input("Full Name", placeholder="e.g. Priya Sharma", key="reg_name")
            email = st.text_input("Email Address", placeholder="name@example.com", key="reg_email")
            phone = st.text_input("Phone Number", placeholder="e.g. 7007914594", key="reg_phone")
            password = st.text_input("Password", type="password", placeholder="Minimum 6 characters", key="reg_pwd")
            
            st.markdown(
                """
                <p style='color: var(--text-secondary); font-size: 11px; margin-top:-5px; line-height: 1.3;'>
                    * Phone number is required to send emergency notifications and live coordinates to your emergency contacts.
                </p>
                """,
                unsafe_allow_html=True
            )
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("🛡️ CREATE SECURE ACCOUNT", width="stretch", type="primary", key="reg_btn"):
                if not name or not email or not phone or not password:
                    st.error("All fields (Name, Email, Phone, Password) are required.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    with st.spinner("Registering secure profile..."):
                        reg_payload = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "password": password
                        }
                        res = api_post("/auth/register", reg_payload)
                    
                    if res and res.get("success"):
                        st.success("Registration successful! Initiating secure login...")
                        # Automatically sign the user in
                        with st.spinner("Logging in..."):
                            login_res = api_post("/auth/login", {"email": email, "password": password})
                        if login_res and login_res.get("success"):
                            st.session_state["authenticated"] = True
                            st.session_state["idToken"] = login_res.get("idToken")
                            st.session_state["uid"] = login_res.get("uid")
                            st.session_state["user_email"] = login_res.get("email")
                            st.session_state["user_name"] = login_res.get("name")
                            st.query_params["idToken"] = login_res.get("idToken")
                            st.query_params["uid"] = login_res.get("uid")
                            st.query_params["email"] = login_res.get("email", "")
                            st.query_params["name"] = login_res.get("name", "User")
                            st.toast(f"Account created and verified. Welcome, {name}!", icon="🛡️")
                            st.rerun()
                        else:
                            st.info("Registration successful. Please switch to Sign In and enter your credentials.")
                    else:
                        st.error("Registration failed. Email or phone might already be in use or format is invalid.")
                        
        st.markdown("</div>", unsafe_allow_html=True)
