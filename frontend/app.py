import sys
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.auth import register_user
from backend.auth_login import login_user
from database.db import create_tables


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

        :root {
            --bg-top: #f8fcff;
            --bg-mid: #e9f6f1;
            --bg-bottom: #e2ebff;
            --ink-900: #0f172a;
            --ink-700: #334155;
            --ink-500: #64748b;
            --brand-800: #0d635d;
            --brand-700: #0f766e;
            --brand-500: #14b8a6;
            --accent-500: #ef7d2e;
            --card-bg: rgba(255, 255, 255, 0.84);
            --card-stroke: rgba(148, 163, 184, 0.24);
        }

        html, body, [class*="css"] {
            font-family: "Manrope", "Segoe UI", sans-serif;
        }

        html, body {
            background:
                radial-gradient(circle at -4% -12%, rgba(56, 189, 248, 0.38), transparent 44%),
                radial-gradient(circle at 102% -8%, rgba(249, 115, 22, 0.22), transparent 38%),
                radial-gradient(circle at 78% 108%, rgba(34, 197, 94, 0.22), transparent 40%),
                linear-gradient(122deg, #dbeafe 0%, #dcfce7 52%, #ffedd5 100%) fixed;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"] {
            background: transparent !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            background: transparent !important;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {
            max-width: 100%;
            overflow-x: hidden !important;
        }

        .stApp {
            background:
                radial-gradient(circle at -4% -12%, rgba(56, 189, 248, 0.38), transparent 44%),
                radial-gradient(circle at 102% -8%, rgba(249, 115, 22, 0.22), transparent 38%),
                radial-gradient(circle at 78% 108%, rgba(34, 197, 94, 0.22), transparent 40%),
                linear-gradient(122deg, #dbeafe 0%, #dcfce7 52%, #ffedd5 100%);
            background-attachment: fixed;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(148, 163, 184, 0.22);
            background: linear-gradient(180deg, rgba(246,250,255,0.97) 0%, rgba(231,240,255,0.92) 100%);
        }

        .block-container {
            padding-top: 2.35rem;
            padding-bottom: 2.35rem;
            max-width: 1180px;
        }

        .side-head {
            font-size: 1.1rem;
            font-weight: 800;
            margin-bottom: 0.3rem;
            color: var(--ink-900);
            letter-spacing: -0.01em;
        }

        .side-sub {
            margin-bottom: 0.75rem;
            color: var(--ink-500);
            font-size: 0.84rem;
        }

        form[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(148, 163, 184, 0.26);
            border-radius: 1rem;
            padding: 0.85rem 0.85rem 0.55rem 0.85rem;
        }

        [data-testid="stTextInput"] input {
            border-radius: 0.72rem;
            border: 1px solid rgba(148, 163, 184, 0.38);
            background: #ffffff;
        }

        [data-testid="stTextInput"] input:focus {
            border-color: rgba(20, 184, 166, 0.75);
            box-shadow: 0 0 0 1px rgba(20, 184, 166, 0.35);
        }

        .brand-kicker {
            display: inline-block;
            background: rgba(13, 99, 93, 0.10);
            color: var(--brand-700);
            border: 1px solid rgba(15, 118, 110, 0.24);
            border-radius: 999px;
            padding: 0.34rem 0.9rem;
            font-size: 0.72rem;
            letter-spacing: 0.095em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.7rem;
        }

        .hero-title {
            font-size: clamp(2.15rem, 3.8vw, 3.35rem);
            line-height: 1.02;
            font-weight: 800;
            color: var(--ink-900);
            letter-spacing: -0.03em;
            margin: 0 0 0.8rem 0;
        }

        .hero-sub {
            color: var(--ink-700);
            font-size: 1.04rem;
            line-height: 1.65;
            margin-bottom: 1rem;
            max-width: 60ch;
        }

        .stat-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-bottom: 1rem;
        }

        .stat-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.28rem 0.62rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.75);
            border: 1px solid rgba(148, 163, 184, 0.34);
            color: var(--ink-700);
            font-size: 0.77rem;
            font-weight: 650;
        }

        .spotlight-card {
            background: var(--card-bg);
            border: 1px solid var(--card-stroke);
            border-radius: 1.05rem;
            padding: 1.1rem 1.15rem;
            backdrop-filter: blur(4px);
            box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05);
            animation: fadeInUp 380ms ease both;
        }

        .spotlight-card h4 {
            margin: 0 0 0.35rem 0;
            color: var(--ink-900);
            font-size: 1.06rem;
        }

        .spotlight-card p {
            margin: 0;
            color: var(--ink-700);
            font-size: 0.92rem;
            line-height: 1.5;
        }

        .feature-card {
            background: var(--card-bg);
            border: 1px solid var(--card-stroke);
            border-radius: 1.05rem;
            padding: 1.02rem 1.08rem;
            min-height: 125px;
            transition: transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
            animation: fadeInUp 430ms ease both;
        }

        .feature-card:hover {
            transform: translateY(-3px);
            border-color: rgba(20, 184, 166, 0.45);
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
        }

        .feature-card h4 {
            color: var(--ink-900);
            margin: 0 0 0.28rem 0;
        }

        .feature-card p {
            color: var(--ink-700);
            margin: 0;
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .section-title {
            margin-top: 0.3rem;
            margin-bottom: 0.8rem;
            color: var(--ink-900);
            font-size: 1.22rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, var(--brand-800) 0%, var(--brand-500) 100%);
            border: none;
            color: #ffffff;
            font-weight: 700;
            border-radius: 0.72rem;
            box-shadow: 0 10px 22px rgba(15, 118, 110, 0.22);
        }

        button[data-testid="baseButton-primary"]:hover {
            filter: brightness(1.03);
            transform: translateY(-1px);
        }

        button[data-testid="baseButton-secondary"] {
            border-radius: 0.72rem;
            border: 1px solid rgba(148, 163, 184, 0.4);
            color: var(--ink-900);
        }

        .stAlert {
            border-radius: 0.8rem;
        }

        [data-testid="stLogo"] img,
        [data-testid="stLogo"] svg {
            max-height: 4.2rem !important;
            width: auto !important;
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @media (max-width: 900px) {
            .block-container {
                padding-top: 1.1rem;
                padding-bottom: 1.2rem;
                padding-left: 0.85rem;
                padding-right: 0.85rem;
                max-width: 100% !important;
            }
            .block-container [data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                gap: 0.75rem !important;
            }
            .block-container [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 0 !important;
            }
            .hero-sub {
                font-size: 0.95rem;
                overflow-wrap: anywhere;
            }
            .hero-title {
                font-size: clamp(1.72rem, 9vw, 2.2rem);
                line-height: 1.12;
                overflow-wrap: anywhere;
            }
            .feature-card {
                min-height: auto;
            }
            .spotlight-card,
            .feature-card {
                padding: 0.9rem 0.95rem;
            }
            .spotlight-card p,
            .feature-card p {
                overflow-wrap: anywhere;
            }
            .stat-row {
                gap: 0.4rem;
            }
            .stat-chip {
                font-size: 0.73rem;
            }
            button[data-testid="baseButton-primary"],
            button[data-testid="baseButton-secondary"] {
                min-height: 2.65rem;
            }
            [data-testid="stLogo"] img,
            [data-testid="stLogo"] svg {
                max-height: 3.1rem !important;
            }
            .section-title {
                font-size: 1.05rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


create_tables()

assets_dir = Path(__file__).resolve().parent / "assets"
icon_png = assets_dir / "artify_logo.png"
logo_svg = assets_dir / "artify_logo.svg"
logo_asset = logo_svg if logo_svg.exists() else icon_png

st.set_page_config(
    page_title="Artify AI",
    page_icon=str(icon_png) if icon_png.exists() else ":art:",
    layout="wide",
)

apply_styles()
if logo_asset.exists() and hasattr(st, "logo"):
    try:
        st.logo(str(logo_asset), size="large")
    except TypeError:
        st.logo(str(logo_asset))

defaults = {
    "logged_in": False,
    "username": None,
    "email": None,
    "user_id": None,
    "remember_me": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "flash_message" in st.session_state:
    st.success(st.session_state.flash_message)
    del st.session_state.flash_message

with st.sidebar:
    st.markdown('<div class="side-head">Account Center</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="side-sub">Secure sign-in and profile access</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if st.session_state.logged_in:
        st.success(f"Signed in as {st.session_state.username}")
        if st.session_state.email:
            st.caption(st.session_state.email)

        if st.button("Open Dashboard", use_container_width=True, type="primary"):
            st.switch_page("pages/dashboard.py")

        if st.button("Log out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.email = None
            st.session_state.user_id = None
            st.session_state.remember_me = False
            st.rerun()
    else:
        mode = st.radio(
            "Access",
            options=["Login", "Create account"],
            key="auth_mode",
            horizontal=True,
        )

        if mode == "Login":
            with st.form("login_form"):
                st.markdown("#### Welcome back")
                identifier = st.text_input("Email or username", key="login_identifier")
                password = st.text_input("Password", type="password", key="login_password")
                remember_me = st.checkbox("Remember Me", key="login_remember_me")
                login_submit = st.form_submit_button("Sign in", use_container_width=True)
            st.caption("Forgot Password? (Coming Soon)")

            if login_submit:
                result = login_user(identifier.strip(), password)
                if result.get("success"):
                    st.session_state.logged_in = True
                    st.session_state.username = result.get("username")
                    st.session_state.email = result.get("email")
                    st.session_state.user_id = result.get("user_id")
                    st.session_state.remember_me = bool(remember_me)
                    st.rerun()
                st.error(result.get("message", "Login failed."))

        else:
            with st.form("register_form"):
                st.markdown("#### Create your account")
                reg_user = st.text_input("Username", key="reg_username")
                reg_email = st.text_input("Email", key="reg_email")
                reg_pass = st.text_input("Password", type="password", key="reg_password")
                reg_confirm = st.text_input(
                    "Confirm password",
                    type="password",
                    key="reg_confirm",
                )
                

                agree_terms = st.checkbox("I agree to the Terms and Conditions", key="reg_terms")
                register_submit = st.form_submit_button("Create account", use_container_width=True)

            if register_submit:
                reg_user_clean = reg_user.strip()
                reg_email_clean = reg_email.strip()
                submit_errors = []

                if not (reg_user_clean and reg_email_clean and reg_pass and reg_confirm):
                    submit_errors.append("All fields are required.")
                if reg_pass and reg_confirm and reg_pass != reg_confirm:
                    submit_errors.append("Passwords do not match.")
                if not agree_terms:
                    submit_errors.append("You must agree to the Terms and Conditions.")

                if submit_errors:
                    st.error("Please fix the following:\n- " + "\n- ".join(submit_errors))
                else:
                    result = register_user(reg_user_clean, reg_email_clean, reg_pass)
                    if result.get("success"):
                        st.session_state.flash_message = "Account created. Please sign in."
                        st.session_state.auth_mode = "Login"
                        st.rerun()
                    else:
                        st.error(result.get("message", "Registration failed."))

left, right = st.columns([1.6, 1], gap="large")

with left:
    st.markdown('<div class="brand-kicker">AI CARTOONIZATION STUDIO</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="hero-title">Turn everyday photos into clean, publication-ready cartoon art.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-sub">Artify AI helps creators and teams convert portraits or product '
        'shots into polished cartoon visuals with a reliable, repeatable workflow.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="stat-row">
            <span class="stat-chip">High-resolution exports</span>
            <span class="stat-chip">Fast style presets</span>
            <span class="stat-chip">Secure account workflow</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        open_editor = st.button("Launch AI Editor", type="primary", use_container_width=True)
    with c2:
        open_dashboard = st.button("Open dashboard", use_container_width=True)

    if open_editor or open_dashboard:
        if st.session_state.logged_in:
            st.switch_page("pages/dashboard.py")
        else:
            st.warning("Please sign in from the sidebar to continue.")

    st.caption("Optimized for web-ready visuals and social media outputs.")

with right:
    st.markdown(
        """
        <div class="spotlight-card">
            <h4>What you can expect</h4>
            <p>Upload, apply style, compare output, and download in one flow. The dashboard keeps your account, uploads, and payments organized in one place.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")
    st.markdown(
        """
        <div class="spotlight-card">
            <h4>Core quality goals</h4>
            <p>Edge-preserving smoothing, vibrant but balanced tones, and high-resolution exports suitable for digital publishing.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">Why teams choose Artify AI</div>', unsafe_allow_html=True)
f1, f2, f3 = st.columns(3, gap="medium")
with f1:
    st.markdown(
        """
        <div class="feature-card">
            <h4>Consistent outputs</h4>
            <p>Keep visual quality stable across portraits, product shots, and campaign assets.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with f2:
    st.markdown(
        """
        <div class="feature-card">
            <h4>Faster creative cycles</h4>
            <p>Spend less time editing manually and more time testing style directions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with f3:
    st.markdown(
        """
        <div class="feature-card">
            <h4>Security in workspace</h4>
            <p>Your account workflow is tied to local storage and your own database setup.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
