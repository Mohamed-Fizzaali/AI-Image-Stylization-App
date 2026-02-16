import sys
from pathlib import Path
import streamlit as st

# =========================
# PATH CONFIG
# =========================

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.auth_login import login_user
from backend.auth import register_user
from database.db import create_tables

create_tables()


# Page config must be first Streamlit command

icon_path = Path(__file__).parent / "assets" / "artify_logo.png"

st.set_page_config(
    page_title="Artify AI",
    page_icon=str(icon_path),
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>

/* Completely remove Streamlit sidebar */
section[data-testid="stSidebar"] {
    display: none !important;
}

/* Remove collapse arrow button */
button[data-testid="collapsedControl"] {
    display: none !important;
}

/* Remove default top header spacing */
header {visibility: hidden;}
footer {visibility: hidden;}

</style>
""", unsafe_allow_html=True)



st.markdown("""
<style>

/* SaaS fixed top navbar - targets the block containing nav-logo */
div[data-testid="stHorizontalBlock"]:has(.nav-logo),
.block-container > div:has([data-testid="stHorizontalBlock"]:has(.nav-logo)) {
    position: sticky !important;
    top: 0 !important;
    z-index: 100 !important;
    background: #ffffff !important;
    padding: 0.75rem 0 !important;
    margin: 0 -1rem 1.5rem -1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    border-bottom: 1px solid #e5e7eb !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
}

.nav-logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.35rem;
    font-weight: 700;
    color: #1f2937;
    letter-spacing: -0.02em;
}

.nav-logo-icon {
    font-size: 1.5rem;
}
</style>
""", unsafe_allow_html=True)


# =========================
# SESSION INIT
# =========================

defaults = {
    "logged_in": False,
    "show_login": False,
    "show_register": False,
    "show_drawer": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =========================
# FLASH MESSAGE
# =========================

if "flash_message" in st.session_state:
    st.success(st.session_state.flash_message)
    del st.session_state.flash_message

# =========================
# MODAL CSS (SCROLL SAFE)
# =========================

st.markdown("""
<style>


/* Modal Styling */
.overlay {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.4);
    backdrop-filter: blur(6px);
    z-index: 999;
}

.st-key-login_box, .st-key-register_box {
    position: fixed !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    background-color: white !important;
    padding: 25px !important;
    border-radius: 16px !important;
    box-shadow: 0 15px 50px rgba(0,0,0,0.3) !important;
    z-index: 1300 !important;
    max-height: 85vh !important;
    overflow-y: auto !important;
}

.st-key-login_box { width: 420px !important; }
.st-key-register_box { width: 500px !important; }

</style>
""", unsafe_allow_html=True)



# =========================
# HEADER (ALWAYS FULL WIDTH)
# =========================


st.markdown("""
<style>
.custom-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0px;
}

.logo-container {
    width: 200px;
}

.logo-container svg {
    width: 100% !important;
    height: auto !important;
    display: block;
}
</style>
""", unsafe_allow_html=True)

logo_path = Path(__file__).resolve().parent / "assets" / "artify_logo.svg"

left_html = ""
if logo_path.exists():
    svg_code = logo_path.read_text(encoding="utf-8")
    left_html = f'<div class="logo-container">{svg_code}</div>'
else:
    left_html = "<div style='font-weight:600;'>Artify AI</div>"

col1, col2 = st.columns([9,1])

with col1:
    st.markdown(f'<div class="custom-header">{left_html}</div>', unsafe_allow_html=True)

with col2:
    if st.button("👤", key="profile_icon_btn"):
        st.session_state.show_drawer = not st.session_state.show_drawer
        st.rerun()

st.markdown(
    "<hr style='margin-top:5px; margin-bottom:25px; border: 1px solid #e5e7eb;'>",
    unsafe_allow_html=True
)




# =========================
# BODY LAYOUT (ONLY CONTENT SPLITS)
# =========================

if st.session_state.show_drawer:
    main_col, panel_col = st.columns([3, 1])
else:
    main_col = st.container()



# =========================
# MAIN CONTENT (HERO ONLY)
# =========================

with main_col:

    st.title("Transform Your Photos Into Art")
    st.write("AI-powered image stylization and cartoon transformation platform.")

    if st.button("Open AI Editor", key="hero_editor_btn"):
        if not st.session_state.logged_in:
            st.session_state.show_login = True
            st.rerun()
        else:
            st.switch_page("pages/dashboard.py")
            st.stop()


# =========================
# RIGHT PANEL CONTENT
# =========================

if st.session_state.show_drawer:
    with panel_col:

        st.markdown(
            """
            <style>
            .right-panel {
                border-left: 1px solid #e5e7eb;
                padding-left: 24px;
                height: 100%;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        with st.container():
            st.markdown('<div class="right-panel">', unsafe_allow_html=True)

            st.markdown("### 👤 Account")
            st.markdown("---")

            if st.session_state.logged_in:

                st.markdown("#### 👤 " + st.session_state.get("username"))

                if st.button("📊 Dashboard", key="drawer_dashboard_btn"):
                    st.session_state.show_drawer = False
                    st.switch_page("pages/dashboard.py")
                    st.stop()

                if st.button("🚪 Logout", key="drawer_logout_btn"):
                    st.session_state.clear()
                    st.rerun()

            else:

                st.info("Sign in to access your dashboard.")

                if st.button("🔐 Login", key="drawer_login_btn"):
                    st.session_state.show_login = True
                    st.session_state.show_drawer = False
                    st.rerun()

                if st.button("📝 Register", key="drawer_register_btn"):
                    st.session_state.show_register = True
                    st.session_state.show_drawer = False
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)



# =========================
# LOGIN MODAL
# =========================

if st.session_state.show_login:
    st.markdown('<div class="overlay"></div>', unsafe_allow_html=True)

    with st.container(key="login_box"):
        st.subheader("🔐 Login")

        identifier = st.text_input("Email or Username", key="login_identifier_input")
        password = st.text_input("Password", type="password", key="login_password_input")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Sign In", use_container_width=True, key="login_submit_btn"):
                result = login_user(identifier, password)

                if result["success"]:
                    st.session_state.logged_in = True
                    st.session_state.username = result["username"]
                    st.session_state.email = result.get("email")
                    st.session_state.show_login = False
                    st.rerun()
                else:
                    st.error(result["message"])

        with col2:
            if st.button("Close", use_container_width=True, key="login_close_btn"):
                st.session_state.show_login = False
                st.rerun()

# =========================
# REGISTER MODAL
# =========================

if st.session_state.show_register:
    st.markdown('<div class="overlay"></div>', unsafe_allow_html=True)

    with st.container(key="register_box"):
        st.subheader("📝 Create Account")

        reg_user = st.text_input("Username", key="reg_username_input")
        reg_email = st.text_input("Email", key="reg_email_input")
        reg_pass = st.text_input("Password", type="password", key="reg_password_input")
        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm_input")

        len_v = len(reg_pass) >= 8 if reg_pass else False
        upper_v = any(c.isupper() for c in reg_pass) if reg_pass else False
        lower_v = any(c.islower() for c in reg_pass) if reg_pass else False
        digit_v = any(c.isdigit() for c in reg_pass) if reg_pass else False
        spec_v = any(not c.isalnum() for c in reg_pass) if reg_pass else False
        match_v = (reg_pass == reg_confirm) if (reg_pass and reg_confirm) else False

        st.markdown("#### Password Requirements")

        g1, g2 = st.columns(2)

        with g1:
            st.markdown(f"{'✅' if len_v else '❌'} 8+ Characters")
            st.markdown(f"{'✅' if upper_v else '❌'} Uppercase")
            st.markdown(f"{'✅' if lower_v else '❌'} Lowercase")

        with g2:
            st.markdown(f"{'✅' if digit_v else '❌'} Number")
            st.markdown(f"{'✅' if spec_v else '❌'} Special Char")
            st.markdown(f"{'✅' if match_v else '❌'} Match")

        st.markdown("---")

        agree_terms = st.checkbox("I agree to the Terms and Conditions", key="reg_terms_checkbox")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Register Now", use_container_width=True, key="register_submit_btn"):
                if not agree_terms:
                    st.error("You must agree to continue.")
                elif not (len_v and upper_v and lower_v and digit_v and spec_v and match_v):
                    st.error("Please meet all password requirements.")
                elif not (reg_user and reg_email):
                    st.error("Username and Email cannot be empty.")
                else:
                    result = register_user(reg_user.strip(), reg_email.strip(), reg_pass)
                    if result["success"]:
                        st.session_state.show_register = False
                        st.session_state.show_login = True
                        st.session_state.flash_message = "Account created! Please login."
                        st.rerun()
                    else:
                        st.error(result["message"])

        with col2:
            if st.button("Cancel", use_container_width=True, key="register_cancel_btn"):
                st.session_state.show_register = False
                st.rerun()
