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
            padding-top: 2.1rem;
            padding-bottom: 2.2rem;
            max-width: 1180px;
        }

        .dash-kicker {
            display: inline-block;
            background: rgba(13, 99, 93, 0.10);
            color: var(--brand-700);
            border: 1px solid rgba(15, 118, 110, 0.24);
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
            border: 1px solid rgba(148, 163, 184, 0.36);
            background: rgba(255,255,255,0.75);
        }

        .stDataFrame {
            border-radius: 0.8rem;
            overflow: hidden;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {
            border-radius: 0.72rem;
            border: 1px solid rgba(148, 163, 184, 0.38);
        }

        [data-testid="stFileUploader"] section {
            border-radius: 0.95rem;
            border: 1px dashed rgba(15, 118, 110, 0.45);
            background: rgba(255,255,255,0.68);
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
                padding-top: 1.2rem;
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
    if st.button("Image Processing", use_container_width=True):
        st.switch_page("pages/image_editor.py")
        st.stop()
    if st.button("Back to home", use_container_width=True):
        st.switch_page("app.py")
        st.stop()
    if st.button("Log out", use_container_width=True, type="primary"):
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
            Upload an image, set creative controls, and run processing from one clean flow.
            Your OpenCV cartoonization function can be connected directly to the generate action below.
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
                st.image(uploaded_file, caption="Source image preview", use_container_width=True)
            else:
                st.caption("Drop an image to start previewing your output setup.")

    with right:
        with st.container(border=True):
            style = st.selectbox(
                "Cartoon style",
                ["Classic", "Soft shading", "Bold outlines", "High contrast"],
            )
            intensity = st.slider("Effect intensity", min_value=0, max_value=100, value=65)
            preserve_skin = st.checkbox("Preserve skin tones", value=True)
            keep_background = st.checkbox("Keep background details", value=True)

            run_processing = st.button("Generate cartoon image", type="primary", use_container_width=True)
            if run_processing and not uploaded_file:
                st.warning("Upload an image before generating.")
            elif run_processing:
                st.info(
                    f"Pipeline placeholder: style={style}, intensity={intensity}, "
                    f"preserve_skin={preserve_skin}, keep_background={keep_background}"
                )

elif menu == "Payment History":
    st.subheader("Payment History")
    with st.container(border=True):
        if transactions:
            st.dataframe(transactions, use_container_width=True, hide_index=True)
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
