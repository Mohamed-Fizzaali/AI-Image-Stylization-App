import sys
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from database.db import get_connection


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

        :root {
            --bg-top: #050d1e;
            --bg-mid: #09182d;
            --bg-bottom: #0f1f3a;
            --ink-900: #eaf2ff;
            --ink-700: #c0cfe8;
            --ink-500: #8ea3c3;
            --brand-800: #0d4f63;
            --brand-700: #0e7490;
            --brand-500: #22d3ee;
            --accent-500: #fb923c;
            --card-bg: rgba(12, 24, 44, 0.78);
            --card-stroke: rgba(125, 162, 206, 0.24);
        }

        html, body, [class*="css"] {
            font-family: "Manrope", "Segoe UI", sans-serif;
            color: var(--ink-700);
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--ink-900);
        }

        p, label, li, [data-testid="stMarkdownContainer"] {
            color: var(--ink-700);
        }

        html, body {
            background:
                radial-gradient(circle at -2% -8%, rgba(34, 211, 238, 0.22), transparent 34%),
                radial-gradient(circle at 103% 0%, rgba(251, 146, 60, 0.20), transparent 34%),
                radial-gradient(circle at 70% 105%, rgba(59, 130, 246, 0.18), transparent 40%),
                linear-gradient(160deg, var(--bg-top) 0%, var(--bg-mid) 46%, var(--bg-bottom) 100%) fixed;
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
                radial-gradient(circle at -2% -8%, rgba(34, 211, 238, 0.22), transparent 34%),
                radial-gradient(circle at 103% 0%, rgba(251, 146, 60, 0.20), transparent 34%),
                radial-gradient(circle at 70% 105%, rgba(59, 130, 246, 0.18), transparent 40%),
                linear-gradient(160deg, var(--bg-top) 0%, var(--bg-mid) 46%, var(--bg-bottom) 100%);
            background-attachment: fixed;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(125, 162, 206, 0.24);
            background: linear-gradient(180deg, rgba(5, 13, 31, 0.98) 0%, rgba(12, 28, 52, 0.96) 100%);
            color: var(--ink-700);
            backdrop-filter: blur(10px);
        }

        [data-testid="stSidebar"] * {
            color: var(--ink-700);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6 {
            color: var(--ink-900);
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label p,
        [data-testid="stSidebar"] .stCaptionContainer {
            color: var(--ink-700) !important;
        }

        button[data-testid="collapsedControl"] {
            background: rgba(7, 16, 32, 0.85) !important;
            border: 1px solid rgba(125, 162, 206, 0.4) !important;
            border-radius: 0.6rem !important;
            min-width: 2.3rem !important;
            min-height: 2.3rem !important;
        }

        button[data-testid="collapsedControl"] svg,
        [data-testid="stSidebarNav"] svg {
            fill: var(--ink-900) !important;
            color: var(--ink-900) !important;
        }

        [data-testid="stSidebarNav"] a {
            color: var(--ink-700) !important;
        }

        .block-container {
            padding-top: 2.1rem;
            padding-bottom: 2.2rem;
            max-width: 1180px;
        }

        .dash-kicker {
            display: inline-block;
            background: rgba(14, 116, 144, 0.22);
            color: #8de9ff;
            border: 1px solid rgba(34, 211, 238, 0.35);
            border-radius: 999px;
            padding: 0.34rem 0.84rem;
            font-size: 0.72rem;
            letter-spacing: 0.095em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.65rem;
        }

        .dash-title {
            margin: 0.1rem 0 0.55rem 0;
            font-size: clamp(1.95rem, 3.1vw, 2.85rem);
            line-height: 1.05;
            letter-spacing: -0.025em;
            color: var(--ink-900);
            font-weight: 800;
            white-space: normal !important;
            word-break: break-word;
        }

        .dash-sub {
            color: var(--ink-700);
            font-size: 1rem;
            line-height: 1.5;
            margin-bottom: 0.75rem;
        }

        .spot-card {
            background: var(--card-bg);
            border: 1px solid var(--card-stroke);
            border-radius: 1.05rem;
            padding: 1.05rem 1.12rem;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
            animation: fadeInUp 360ms ease both;
        }

        .sidebar-head {
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--ink-900);
            margin-bottom: 0.25rem;
            letter-spacing: -0.01em;
        }

        .side-sub {
            margin-bottom: 0.75rem;
            color: var(--ink-500);
            font-size: 0.84rem;
        }

        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #0e7490 0%, #22d3ee 100%);
            border: none;
            color: #03101f;
            font-weight: 700;
            border-radius: 0.72rem;
            box-shadow: 0 10px 22px rgba(34, 211, 238, 0.20);
        }

        button[data-testid="baseButton-primary"]:hover {
            filter: brightness(1.03);
            transform: translateY(-1px);
        }

        button[data-testid="baseButton-secondary"] {
            border-radius: 0.72rem;
            border: 1px solid rgba(125, 162, 206, 0.45);
            color: var(--ink-900);
            background: rgba(8, 20, 38, 0.66);
        }

        [data-testid="stMetric"] {
            background: var(--card-bg);
            border: 1px solid var(--card-stroke);
            border-radius: 1rem;
            padding: 0.66rem 0.78rem;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
        }

        .mini-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-bottom: 0.7rem;
        }

        .mini-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.29rem 0.64rem;
            font-size: 0.77rem;
            font-weight: 650;
            color: var(--ink-700);
            border: 1px solid rgba(125, 162, 206, 0.36);
            background: rgba(8, 20, 38, 0.74);
        }

        .stDataFrame {
            border-radius: 0.8rem;
            overflow: hidden;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {
            border-radius: 0.72rem;
            border: 1px solid rgba(125, 162, 206, 0.32);
            background: rgba(5, 13, 31, 0.74);
            color: var(--ink-900);
        }

        [data-testid="stFileUploader"] section {
            border-radius: 0.95rem;
            border: 1px dashed rgba(34, 211, 238, 0.42);
            background: rgba(8, 20, 38, 0.62);
        }

        [data-testid="stSelectbox"] > div {
            border-radius: 0.72rem;
        }

        [data-testid="stLogo"] img,
        [data-testid="stLogo"] svg {
            max-height: 4.1rem !important;
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
                padding-top: 0.85rem;
                padding-bottom: 1rem;
                padding-left: 0.7rem;
                padding-right: 0.7rem;
                max-width: 100% !important;
            }
            .block-container [data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                gap: 0.65rem !important;
            }
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
            }
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 0 !important;
            }
            .block-container [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 0 !important;
            }
            .dash-title {
                font-size: clamp(1.35rem, 7.4vw, 1.72rem);
                line-height: 1.12;
                overflow-wrap: anywhere;
            }
            .dash-sub {
                font-size: 0.88rem;
                overflow-wrap: anywhere;
            }
            .spot-card {
                padding: 0.78rem 0.82rem;
                overflow-wrap: anywhere;
            }
            [data-testid="stMetric"] {
                padding: 0.52rem 0.58rem;
            }
            .mini-pill {
                font-size: 0.69rem;
            }
            [data-testid="stLogo"] img,
            [data-testid="stLogo"] svg {
                max-height: 3rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def fetch_dashboard_data(user_id: int | None) -> tuple[dict, list[dict], dict]:
    metrics = {
        "images_processed": 0,
        "completed_payments": 0,
        "total_spent": 0.0,
    }
    transactions: list[dict] = []
    profile = {
        "created_at": "N/A",
        "last_login": "N/A",
        "is_active": True,
        "account_locked": False,
        "failed_attempts": 0,
    }

    if not user_id:
        return metrics, transactions, profile

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM ImageHistory WHERE user_id = ?",
                (user_id,),
            )
            metrics["images_processed"] = cursor.fetchone()[0] or 0

            cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0), COUNT(*)
                FROM Transactions
                WHERE user_id = ? AND payment_status = 'Completed'
                """,
                (user_id,),
            )
            total_spent, completed_count = cursor.fetchone()
            metrics["total_spent"] = float(total_spent or 0)
            metrics["completed_payments"] = completed_count or 0

            cursor.execute(
                """
                SELECT transaction_date, amount, payment_status, payment_method
                FROM Transactions
                WHERE user_id = ?
                ORDER BY transaction_date DESC
                LIMIT 12
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            transactions = [
                {
                    "Date": row[0],
                    "Amount (USD)": f"{float(row[1]):.2f}",
                    "Status": row[2],
                    "Method": row[3],
                }
                for row in rows
            ]

            cursor.execute(
                """
                SELECT created_at, last_login, is_active, account_locked, failed_attempts
                FROM Users
                WHERE user_id = ?
                """,
                (user_id,),
            )
            user_row = cursor.fetchone()
            if user_row:
                profile = {
                    "created_at": user_row[0] or "N/A",
                    "last_login": user_row[1] or "N/A",
                    "is_active": bool(user_row[2]),
                    "account_locked": bool(user_row[3]),
                    "failed_attempts": user_row[4] or 0,
                }

    except Exception:
        return metrics, transactions, profile

    return metrics, transactions, profile


assets_dir = Path(__file__).resolve().parents[1] / "assets"
icon_png = assets_dir / "artify_logo.png"
logo_svg = assets_dir / "artify_logo.svg"
logo_asset = logo_svg if logo_svg.exists() else icon_png

st.set_page_config(
    page_title="Artify Dashboard",
    page_icon=str(icon_png) if icon_png.exists() else ":art:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_styles()
if logo_asset.exists() and hasattr(st, "logo"):
    try:
        st.logo(str(logo_asset), size="large")
    except TypeError:
        st.logo(str(logo_asset))

if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.switch_page("app.py")
    st.stop()

username = st.session_state.get("username", "User")
email = st.session_state.get("email", "Not available")
user_id = st.session_state.get("user_id")

metrics, transactions, profile = fetch_dashboard_data(user_id)

with st.sidebar:
    st.markdown('<div class="sidebar-head">Artify Workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-sub">Manage studio, billing, and profile</div>', unsafe_allow_html=True)
    st.caption(f"Signed in as {username}")
    st.markdown("---")

    menu = st.radio(
        "Sections",
        ["Image Studio", "Payment History", "Profile Settings"],
    )

    st.markdown("---")
    if st.button("Image Processing", width="stretch"):
        st.switch_page("pages/image_editor.py")
        st.stop()
    if st.button("Back to home", width="stretch"):
        st.switch_page("app.py")
        st.stop()
    if st.button("Log out", width="stretch", type="primary"):
        st.session_state.clear()
        st.switch_page("app.py")
        st.stop()

st.markdown('<div class="dash-kicker">USER DASHBOARD</div>', unsafe_allow_html=True)
st.markdown(f'<h1 class="dash-title">Welcome back, {username}</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="dash-sub">Track your generated content, review transactions, and manage account security.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="mini-pills">
        <span class="mini-pill">Live account stats</span>
        <span class="mini-pill">Centralized workflow</span>
        <span class="mini-pill">Secure session controls</span>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Images processed", metrics["images_processed"])
with m2:
    st.metric("Completed payments", metrics["completed_payments"])
with m3:
    st.metric("Total spent (USD)", f"{metrics['total_spent']:.2f}")

st.markdown("")

if menu == "Image Studio":
    st.subheader("Image Studio")
    st.markdown(
        """
        <div class="spot-card">
            Upload and preview here, then continue to the dedicated Image Editor
            page where the actual processing pipeline runs.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")

    left, right = st.columns([1.1, 1], gap="large")
    with left:
        with st.container(border=True):
            uploaded_file = st.file_uploader(
                "Upload image",
                type=["jpg", "jpeg", "png"],
                help="Supported formats: JPG, JPEG, PNG",
            )
            if uploaded_file:
                st.image(uploaded_file, caption="Source image preview", width="stretch")
            else:
                st.caption("Drop an image to start previewing your output setup.")

    with right:
        with st.container(border=True):
            style = st.selectbox(
                "Quick style preset",
                ["Classic Cartoon", "Sketch", "Pencil Color"],
            )

            run_processing = st.button("Continue in Image Editor", type="primary", width="stretch")
            if run_processing and not uploaded_file:
                st.warning("Upload an image before generating.")
            elif run_processing:
                uploaded_bytes = uploaded_file.getvalue()
                max_bytes = 10 * 1024 * 1024
                if len(uploaded_bytes) > max_bytes:
                    st.warning("File is larger than 10 MB. Please upload a smaller image.")
                else:
                    st.session_state.dashboard_image_prefill = {
                        "name": uploaded_file.name,
                        "bytes": uploaded_bytes,
                        "style": style,
                    }
                    st.switch_page("pages/image_editor.py")
                    st.stop()

elif menu == "Payment History":
    st.subheader("Payment History")
    with st.container(border=True):
        if transactions:
            st.dataframe(transactions, width="stretch", hide_index=True)
        else:
            st.info("No transactions found yet. Completed payments will appear here.")

elif menu == "Profile Settings":
    st.subheader("Profile Settings")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("#### Account details")
            st.write(f"Username: {username}")
            st.write(f"Email: {email}")
            st.write(f"Member since: {profile['created_at']}")
            st.write(f"Last login: {profile['last_login']}")

    with c2:
        with st.container(border=True):
            st.markdown("#### Security status")
            st.write(f"Active account: {'Yes' if profile['is_active'] else 'No'}")
            st.write(f"Account locked: {'Yes' if profile['account_locked'] else 'No'}")
            st.write(f"Failed login attempts: {profile['failed_attempts']}")
