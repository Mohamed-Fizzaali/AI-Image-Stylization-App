import base64
import sys
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import cast

import cv2
import numpy as np
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from database.db import get_connection
from frontend.user_profile import sync_user_profile_state, render_sidebar_profile
from backend.image_upload import get_image_metadata, save_uploaded_image, validate_image
from backend.image_processing import (
    apply_watermark,
    bgr_to_rgb,
    classic_cartoon,
    encode_image_to_png,
    grayscale_noir,
    invert_neon,
    pencil_color_effect,
    read_image,
    sepia_effect,
    sketch_effect,
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _img_to_b64(path: str) -> str | None:
    try:
        p = Path(path)
        if not p.is_file():
            return None
        ext = p.suffix.lstrip(".").lower()
        mime = "image/png" if ext == "png" else f"image/{ext}"
        return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    except Exception:
        return None


def _fmt_date(raw: str) -> str:
    try:
        dt = datetime.strptime(str(raw), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(raw)


def reset_editor() -> None:
    keys_to_clear = ["current_image_path", "processed_image", "current_image_hash", "selected_style", "image_paid"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

# ── Subscription tier defaults (safe to call on every run) ──
if "active_plan" not in st.session_state:
    st.session_state["active_plan"] = "Starter"
if "monthly_generations" not in st.session_state:
    st.session_state["monthly_generations"] = 0
if "favorites" not in st.session_state:
    st.session_state["favorites"] = []

def toggle_favorite(img_path: str) -> None:
    if img_path in st.session_state["favorites"]:
        st.session_state["favorites"].remove(img_path)
    else:
        st.session_state["favorites"].append(img_path)


def check_transaction(user_id: int | None) -> bool:
    """Return True if the current user has at least one Completed transaction."""
    if not user_id:
        return False
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT 1 FROM Transactions WHERE user_id=? AND payment_status='Completed' LIMIT 1",
                (user_id,)
            )
            return c.fetchone() is not None
    except Exception:
        return False


def record_mock_payment(user_id: int | None) -> None:
    """Insert a Completed mock transaction for the current user."""
    if not user_id:
        return
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO Transactions (user_id, amount, payment_status, payment_method) VALUES (?, ?, 'Completed', 'Mock')",
                (user_id, 0.0)
            )
            conn.commit()
    except Exception:
        pass


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

def fetch_dashboard_data(user_id: int | None) -> tuple[dict, list[dict], dict]:
    metrics = {"images_processed": 0, "completed_payments": 0, "total_spent": 0.0}
    transactions: list[dict] = []
    profile = {
        "created_at": "N/A", "last_login": "N/A",
        "is_active": True, "account_locked": False, "failed_attempts": 0,
    }
    if not user_id:
        return metrics, transactions, profile
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM ImageHistory WHERE user_id=?", (user_id,))
            metrics["images_processed"] = c.fetchone()[0] or 0

            c.execute(
                "SELECT COALESCE(SUM(amount),0), COUNT(*) FROM Transactions "
                "WHERE user_id=? AND payment_status='Completed'", (user_id,)
            )
            total_spent, completed_count = c.fetchone()
            metrics["total_spent"] = float(total_spent or 0)
            metrics["completed_payments"] = completed_count or 0

            c.execute(
                "SELECT transaction_date, amount, payment_status, payment_method "
                "FROM Transactions WHERE user_id=? ORDER BY transaction_date DESC LIMIT 12",
                (user_id,)
            )
            transactions = [
                {"Date": r[0], "Amount (USD)": f"{float(r[1]):.2f}", "Status": r[2], "Method": r[3]}
                for r in c.fetchall()
            ]

            c.execute(
                "SELECT created_at, last_login, is_active, account_locked, failed_attempts "
                "FROM Users WHERE user_id=?", (user_id,)
            )
            row = c.fetchone()
            if row:
                profile = {
                    "created_at": row[0] or "N/A", "last_login": row[1] or "N/A",
                    "is_active": bool(row[2]), "account_locked": bool(row[3]),
                    "failed_attempts": row[4] or 0,
                }
    except Exception:
        pass
    return metrics, transactions, profile


def fetch_recent_creations(user_id: int | None, limit: int = 8) -> list[dict]:
    if not user_id:
        return []
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT processed_image_path, style_applied, processing_date "
                "FROM ImageHistory WHERE user_id=? ORDER BY processing_date DESC LIMIT ?",
                (user_id, limit)
            )
            return [
                {"processed_image_path": r[0], "style_applied": r[1], "processing_date": r[2]}
                for r in c.fetchall()
            ]
    except Exception:
        return []


# ─────────────────────────────────────────────
# STYLES  — aligned with homepage design language
# ─────────────────────────────────────────────

def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

        /* ── Base ── */
        :root {
            --ink-900: #111111;
            --ink-700: #374151;
            --ink-500: #64748b;
            --border:  #e5e7eb;
            --radius:  1rem;
            --blue:    #4f7df2;
        }

        html, body, [class*="css"],
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stMain"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        .stApp {
            font-family: "Manrope", "Segoe UI", sans-serif !important;
            background: #ffffff !important;
            background-color: #ffffff !important;
            color: var(--ink-700);
        }

        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 1140px !important;
        }

        /* ── Sidebar — minimal, like homepage ── */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid var(--border) !important;
        }
        [data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebarContent"] {
            background: #ffffff !important;
        }

        /* Hide Streamlit's auto-generated page navigation list */
        [data-testid="stSidebarNav"] { display: none !important; }

        /* Sidebar nav links (Streamlit's built-in pages nav) */
        [data-testid="stSidebarNav"] {
            background: transparent !important;
            padding-top: 0.5rem !important;
        }
        [data-testid="stSidebarNavItems"] {
            gap: 0.15rem !important;
        }
        [data-testid="stSidebarNavLink"] {
            border-radius: 0.8rem !important;
            color: #374151 !important;
            padding: 0.52rem 0.75rem !important;
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            background: transparent !important;
        }
        [data-testid="stSidebarNavLink"]:hover {
            background: #f1f5f9 !important;
            color: #0f172a !important;
        }
        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background: #f1f5f9 !important;
            color: #0f172a !important;
        }

        /* Sidebar collapse button */
        button[data-testid="collapsedControl"] {
            background: #ffffff !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 0.6rem !important;
            color: #374151 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        }
        button[data-testid="collapsedControl"] svg { fill: #374151 !important; }

        /* Sidebar custom nav buttons */
        [data-testid="stSidebar"] .stButton button {
            border: none !important;
            background: transparent !important;
            color: #374151 !important;
            font-weight: 600 !important;
            border-radius: 0.8rem !important;
            padding: 0.55rem 0.75rem !important;
            display: flex !important;
            justify-content: flex-start !important;
            box-shadow: none !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
        }
        [data-testid="stSidebar"] .stButton button p {
            font-size: 0.95rem !important;
            color: inherit !important;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background: #f1f5f9 !important;
            color: #0f172a !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
            transform: translateY(-1px) !important;
        }
        /* Active Streamlit Button (primary) */
        [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 14px rgba(79,125,242,.22) !important;
        }
        [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] p {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 18px rgba(79,125,242,.28) !important;
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            color: #ffffff !important;
        }
        .sb-divider {
            height: 1px;
            background: var(--border);
            margin: 0.65rem 0.5rem;
        }
        /* Sidebar Profile */
        .sidebar-profile {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-top: 0.5rem;
            margin-bottom: 2rem;
        }
        .profile-avatar {
            width: 72px;
            height: 72px;
            border-radius: 50%;
            background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
            color: #4f46e5;
            font-size: 2rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.8rem;
            box-shadow: 0 4px 14px rgba(0,0,0,0.05);
        }
        .profile-name {
            font-size: 1.05rem;
            font-weight: 700;
            color: #0f172a;
        }
        /* ── Page header ── */
        .dash-kicker {
            display: inline-block;
            background: #f4f4f5; color: #71717a;
            border: 1px solid #e4e4e7;
            border-radius: 999px;
            padding: 0.28rem 0.8rem;
            font-size: 0.68rem; letter-spacing: 0.1em;
            text-transform: uppercase; font-weight: 700;
            margin-bottom: 0.45rem;
        }
        .dash-title {
            margin: 0 0 0.35rem 0;
            font-size: clamp(1.85rem, 3vw, 2.55rem);
            font-weight: 800; color: #0f172a;
            letter-spacing: -0.03em; line-height: 1.05;
        }
        .dash-sub {
            color: var(--ink-500);
            font-size: 0.97rem; line-height: 1.55;
            margin-bottom: 1.6rem;
        }

        /* ── Stat cards ── */
        .stat-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 2.6rem;
        }
        .stat-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.2rem 1.35rem 1.05rem 1.35rem;
            box-shadow: 0 1px 6px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
        }
        .stat-card-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .stat-icon {
            width: 2.5rem; height: 2.5rem;
            border-radius: 0.65rem;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.05rem; flex-shrink: 0;
        }
        .stat-icon-blue   { background: linear-gradient(135deg, #4361ee, #3a0ca3); }
        .stat-icon-purple { background: linear-gradient(135deg, #7209b7, #560bad); }
        .stat-icon-pink   { background: linear-gradient(135deg, #f72585, #b5179e); }
        .stat-badge {
            font-size: 0.73rem; font-weight: 700;
            border-radius: 999px; padding: 0.17rem 0.52rem;
        }
        .stat-badge-green { color: #15803d; background: #dcfce7; }
        .stat-badge-blue  { color: #1d4ed8; background: #dbeafe; }
        .stat-value {
            font-size: 1.95rem; font-weight: 800;
            color: #0f172a; line-height: 1;
            letter-spacing: -0.035em;
        }
        .stat-label {
            font-size: 0.85rem; color: var(--ink-500); font-weight: 500;
        }

        /* ── Recent Creations ── */
        .rc-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            margin-bottom: 1.35rem;
        }
        .rc-title {
            font-size: 1.65rem; font-weight: 800;
            color: #0f172a; letter-spacing: -0.025em; line-height: 1.1;
            margin: 0 0 0.18rem 0;
        }
        .rc-sub  { color: var(--ink-500); font-size: 0.9rem; margin: 0; }
        .rc-view-all {
            font-size: 0.9rem; font-weight: 700;
            color: var(--blue) !important; text-decoration: none;
            padding-bottom: 0.2rem; white-space: nowrap;
        }
        .rc-view-all:hover { text-decoration: underline; }

        /* Card grid */
        .rc-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 0.6rem;
        }
        .rc-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
            box-shadow: 0 1px 6px rgba(0,0,0,0.06);
            transition: box-shadow .18s ease, transform .18s ease;
            animation: fadeInUp .35s ease both;
        }
        .rc-card:hover {
            box-shadow: 0 6px 22px rgba(0,0,0,0.1);
            transform: translateY(-3px);
        }
        .rc-card-img {
            width: 100%; height: 200px;
            object-fit: cover; display: block;
        }
        .rc-card-img-fallback {
            width: 100%; height: 200px;
            background: linear-gradient(135deg, #f0f3f9, #e2e8f0);
            display: flex; align-items: center; justify-content: center;
            font-size: 2rem; color: #94a3b8;
        }
        .rc-card-body { padding: 0.8rem 0.95rem 0.65rem 0.95rem; }
        .rc-card-style {
            font-size: 0.95rem; font-weight: 700;
            color: #0f172a; margin: 0 0 0.14rem 0;
        }
        .rc-card-date { font-size: 0.78rem; color: var(--ink-500); margin: 0; }

        /* Empty state */
        .rc-empty {
            border: 2px dashed #e2e8f0;
            border-radius: 1.2rem;
            padding: 3.5rem 2rem;
            text-align: center;
            background: #fafbfd;
            margin-bottom: 1.2rem;
        }
        .rc-empty-icon  { font-size: 2.8rem; margin-bottom: 0.9rem; display: block; }
        .rc-empty-title { font-size: 1.15rem; font-weight: 800; color: #0f172a; margin: 0 0 0.45rem 0; }
        .rc-empty-text  { color: var(--ink-500); font-size: 0.9rem; line-height: 1.55; max-width: 340px; margin: 0 auto; }

        /* Divider */
        .dash-hr { border: none; border-top: 1px solid var(--border); margin: 1.8rem 0 1.5rem 0; }

        /* Panel sections */
        .panel-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.1rem 1.2rem;
            box-shadow: 0 1px 5px rgba(0,0,0,0.04);
        }

        /* Buttons — primary */
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            border: none !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border-radius: 0.75rem !important;
            box-shadow: 0 4px 14px rgba(79,125,242,.22) !important;
            transition: transform .15s, box-shadow .15s !important;
        }
        button[data-testid="baseButton-primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 18px rgba(79,125,242,.28) !important;
        }

        /* Streamlit metric — hide (we use custom HTML) */
        [data-testid="stMetric"] { display: none !important; }

        /* ─────────────────────────────────────
           AI IMAGE STUDIO (Editor) — FIGMA UI
           Scoped + single .custom-card
           ───────────────────────────────────── */

        .custom-card {
            background: #ffffff;
            border-radius: 15px;
            border: 1px solid rgba(226, 232, 240, 0.95);
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
            padding: 16px 16px 14px 16px;
        }

        .studio-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .studio-title {
            font-size: 1.35rem;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.03em;
            margin: 0;
        }

        .studio-subtitle {
            margin: 0.15rem 0 0 0;
            font-size: 0.9rem;
            color: #64748b;
        }

        .studio-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: linear-gradient(135deg, rgba(79, 125, 242, 0.16), rgba(24, 184, 223, 0.14));
            border: 1px solid rgba(79, 125, 242, 0.22);
            color: #1d4ed8;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }

        .card-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }

        .card-head-left {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        .card-title {
            font-size: 0.9rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }

        .card-desc {
            font-size: 0.78rem;
            color: #64748b;
            margin: 0;
        }

        /* Uploader look */
        .st-key-studio_uploader_card [data-testid="stFileUploader"] section {
            border-radius: 14px;
            border: 1.5px dashed rgba(148, 163, 184, 0.6);
            background: #fbfdff;
        }

        /* Center images inside cards (fix use_container_width deprecation warning) */
        .studio-img-center [data-testid="stImage"] {
            display: flex;
            justify-content: center;
        }
        .studio-img-center img {
            max-width: 100%;
            height: auto;
            border-radius: 12px;
        }

        /* Style selector scroll area */
        .style-scroll {
            height: 520px;
            overflow-y: auto;
            padding-right: 6px;
        }
        .style-scroll::-webkit-scrollbar { width: 10px; }
        .style-scroll::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.55);
            border-radius: 999px;
            border: 3px solid rgba(255,255,255,0.9);
        }

        .style-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }

        .style-card-wrap {
            position: relative;
        }

        /* Each style card is a Streamlit button (click target) */
        .st-key-style_grid .style-card-wrap button {
            width: 100% !important;
            border-radius: 14px !important;
            border: 1px solid rgba(226, 232, 240, 0.95) !important;
            background: #ffffff !important;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08) !important;
            padding: 0 !important;
            overflow: hidden !important;
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease !important;
            min-height: 240px !important;
        }
        .st-key-style_grid .style-card-wrap button:hover {
            transform: translateY(-2px) !important;
            border-color: rgba(79, 125, 242, 0.5) !important;
            box-shadow: 0 22px 50px rgba(15, 23, 42, 0.14) !important;
        }

        .style-card-overlay {
            pointer-events: none;
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
        }

        .style-card-inner {
            padding: 12px 12px 11px 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            text-align: left;
        }

        .style-thumb {
            width: 100%;
            aspect-ratio: 16 / 10;
            border-radius: 12px;
            border: 1px solid rgba(226, 232, 240, 0.9);
            background: linear-gradient(135deg, #eef2ff, #f8fafc);
            overflow: hidden;
            position: relative;
        }
        .style-thumb img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .popular-badge {
            position: absolute;
            left: 10px;
            top: 10px;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #ffffff;
            background: linear-gradient(135deg, #f97316, #ec4899);
            padding: 0.18rem 0.5rem;
            border-radius: 999px;
            box-shadow: 0 10px 22px rgba(236, 72, 153, 0.35);
        }

        .style-name {
            font-size: 0.92rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }
        .style-text {
            font-size: 0.78rem;
            color: #64748b;
            margin: 0;
            line-height: 1.45;
            min-height: 2.2em;
        }

        /* Selected state */
        .is-selected-style button {
            border-color: rgba(79, 125, 242, 0.9) !important;
            box-shadow: 0 22px 60px rgba(79, 125, 242, 0.22) !important;
        }

        /* Metric cards row under uploader */
        .metric-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 12px;
        }
        .metric-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #94a3b8;
            margin: 0;
        }
        .metric-value {
            font-size: 1.05rem;
            font-weight: 900;
            color: #0f172a;
            letter-spacing: -0.03em;
            margin: 0.25rem 0 0 0;
        }

        /* Transform button */
        .st-key-transform_ai_btn button {
            border: none !important;
            border-radius: 14px !important;
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            color: #ffffff !important;
            font-weight: 900 !important;
            min-height: 54px !important;
            box-shadow: 0 18px 44px rgba(79, 125, 242, 0.22) !important;
            transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease !important;
        }
        .st-key-transform_ai_btn button:hover:enabled {
            transform: translateY(-1px) !important;
            box-shadow: 0 22px 52px rgba(79, 125, 242, 0.3) !important;
            filter: saturate(1.06) !important;
        }
        .st-key-transform_ai_btn button:disabled {
            background: #e5e7eb !important;
            color: #94a3b8 !important;
            box-shadow: none !important;
        }

        @keyframes fadeInUp {
            from { opacity:0; transform:translateY(8px); }
            to   { opacity:1; transform:translateY(0);   }
        }

        /* Responsive */
        @media(max-width: 900px) {
            .stat-row  { grid-template-columns: 1fr; }
            .rc-grid   { grid-template-columns: repeat(2, 1fr); }
            .style-grid { grid-template-columns: 1fr; }
            .metric-row { grid-template-columns: 1fr; }
            .rc-title  { font-size: 1.3rem; }
        }
        @media(max-width: 540px) {
            .rc-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Artify Dashboard",
    page_icon=":art:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_styles()

# Auth guard
if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.switch_page("app.py")
    st.stop()

sync_user_profile_state()

username = st.session_state.get("user_name") or st.session_state.get("username", "User")
email    = st.session_state.get("email", "Not available")
user_id  = st.session_state.get("user_id")

metrics, transactions, profile = fetch_dashboard_data(user_id)
recent_creations = fetch_recent_creations(user_id, limit=8)

# Initialize editor-related session state so it persists across sections
st.session_state.setdefault("current_image_path", None)
st.session_state.setdefault("current_image_hash", None)
st.session_state.setdefault("processed_image", None)
st.session_state.setdefault("processed_style", None)
st.session_state.setdefault("processing_time", None)
st.session_state.setdefault("current_style", None)
st.session_state.setdefault("selected_style", "classic_cartoon")
st.session_state.setdefault("output_quality", None)

# ─────────────────────────────────────────────
# AI IMAGE STUDIO — render_editor()
# (visual layer only; backend logic untouched)
# ─────────────────────────────────────────────

def render_editor() -> None:
    st.session_state.setdefault("last_time", None)

    st.markdown(
        """
        <style>
          /* Single block: studio cards + scroll grid */
          .custom-card{
            background:#fff;border-radius:15px;border:1px solid rgba(226,232,240,.95);
            box-shadow:0 18px 44px rgba(15,23,42,.08);padding:16px 16px 14px;
          }
          .studio-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;align-items:start;}
          .card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
          .card-title{font-size:.9rem;font-weight:800;color:#0f172a;margin:0;}
          .card-desc{font-size:.78rem;color:#64748b;margin:0;}
          .pill{display:inline-flex;align-items:center;gap:.45rem;padding:.35rem .7rem;border-radius:999px;
            background:linear-gradient(135deg,rgba(79,125,242,.16),rgba(24,184,223,.14));
            border:1px solid rgba(79,125,242,.22);color:#1d4ed8;font-size:.78rem;font-weight:800;white-space:nowrap;}
          .studio-img-center [data-testid="stImage"]{display:flex;justify-content:center;}
          .studio-img-center img{max-width:100%;height:auto;border-radius:12px;}
          .style-scroll{height:520px;overflow-y:auto;padding-right:6px;}
          .style-scroll::-webkit-scrollbar{width:10px;}
          .style-scroll::-webkit-scrollbar-thumb{background:rgba(148,163,184,.55);border-radius:999px;border:3px solid rgba(255,255,255,.9);}
          .style-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
          .style-card{border-radius:14px;padding:12px;border:1px solid rgba(226,232,240,.95);
            box-shadow:0 16px 40px rgba(15,23,42,.06);transition:transform 160ms ease,box-shadow 160ms ease,border-color 160ms ease;}
          .style-card:hover{transform:translateY(-2px);border-color:rgba(79,125,242,.45);box-shadow:0 22px 52px rgba(15,23,42,.12);}
          .style-card.selected{border:2px solid #4f7df2;}
          .style-name{font-size:.92rem;font-weight:900;color:#0f172a;margin:.35rem 0 .15rem 0;}
          .style-text{font-size:.78rem;color:#64748b;margin:0;line-height:1.45;min-height:2.2em;}
          .popular{display:inline-flex;align-items:center;gap:.35rem;font-size:.7rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase;
            color:#fff;background:linear-gradient(135deg,#f97316,#ec4899);padding:.18rem .5rem;border-radius:999px;
            box-shadow:0 10px 22px rgba(236,72,153,.25);}
          .metric-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:12px;}
          .metric-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:#94a3b8;margin:0;}
          .metric-value{font-size:1.05rem;font-weight:900;color:#0f172a;letter-spacing:-.03em;margin:.25rem 0 0 0;}
          .st-key-transform_ai_btn button{
            border:none!important;border-radius:14px!important;background:linear-gradient(135deg,#4f7df2 0%,#18b8df 100%)!important;
            color:#fff!important;font-weight:900!important;min-height:54px!important;box-shadow:0 18px 44px rgba(79,125,242,.22)!important;
            transition:transform 160ms ease,box-shadow 160ms ease,filter 160ms ease!important;
          }
          .st-key-transform_ai_btn button:hover:enabled{transform:translateY(-1px)!important;box-shadow:0 22px 52px rgba(79,125,242,.3)!important;filter:saturate(1.06)!important;}
          .st-key-transform_ai_btn button:disabled{background:#e5e7eb!important;color:#94a3b8!important;box-shadow:none!important;}

          /* Selected border based on key prefix (Streamlit adds .st-key-<key>) */
          [class*="st-key-style_card__selected__"] .custom-card{border:2px solid #4f7df2;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    STYLE_CONFIG = {
        "classic_cartoon": {
            "label": "Classic Cartoon",
            "description": "Bold outlines with vibrant colors.",
            "icon_url": "put image url",
            "popular": True,
            "is_premium": False,
        },
        "sketch": {
            "label": "Sketch Art",
            "description": "Hand-drawn pencil technique.",
            "icon_url": "put image url",
            "popular": False,
            "is_premium": False,
        },
        "pencil_color": {
            "label": "Pencil Color",
            "description": "Soft color pencil texture blend.",
            "icon_url": "put image url",
            "popular": False,
            "is_premium": False,
        },
        "sepia": {
            "label": "Retro Sepia",
            "description": "Vintage warm tones.",
            "icon_url": "https://placehold.co/150x150?text=Sepia",
            "popular": False,
            "is_premium": True,
        },
        "neon": {
            "label": "Inverted Neon",
            "description": "Cyberpunk glow.",
            "icon_url": "https://placehold.co/150x150?text=Neon",
            "popular": False,
            "is_premium": True,
        },
        "noir": {
            "label": "Cinematic Noir",
            "description": "Dramatic grayscale.",
            "icon_url": "https://placehold.co/150x150?text=Noir",
            "popular": False,
            "is_premium": True,
        },
    }

    selected_style_key = cast(str, st.session_state.get("selected_style") or next(iter(STYLE_CONFIG.keys())))
    st.session_state.selected_style = selected_style_key
    style_items = list(STYLE_CONFIG.items())

    current_image_path = st.session_state.get("current_image_path")
    processed_image = st.session_state.get("processed_image")

    st.markdown(
        """
        <div class="studio-header">
          <div>
            <p class="studio-title">AI Image Studio</p>
            <p class="studio-subtitle">Transform photos into art instantly</p>
          </div>
          <div class="pill">⚡ Fast Processing</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        # Left workspace: 2 states (no upload -> uploader card; uploaded -> preview/result)
        st.markdown(
            """
            <div class="custom-card">
              <div class="card-head">
                <div>
                  <p class="card-title">Upload Image</p>
                  <p class="card-desc">Drag & drop your image (or browse)</p>
                </div>
              </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file = None
        if not current_image_path:
            uploaded_file = st.file_uploader(
                "Upload image",
                type=["jpg", "jpeg", "png", "bmp"],
                help="Supported formats: JPG, JPEG, PNG, BMP. Max size: 10 MB.",
                key="studio_uploader",
            )
        else:
            if st.button("➕ Start New Project", width="stretch"):
                reset_editor()
                st.session_state["dash_section"] = "editor"
                st.rerun()

        if uploaded_file is not None:
            try:
                is_valid, validation_message = validate_image(uploaded_file, max_size_mb=10)
            except Exception as exc:
                st.error(f"Could not validate file: {exc}")
                is_valid = False
                validation_message = ""

            if not is_valid:
                if validation_message:
                    st.error(validation_message)
            else:
                file_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
                current_hash = st.session_state.get("current_image_hash")
                if (not current_image_path) or (file_hash != current_hash):
                    try:
                        saved_path = save_uploaded_image(uploaded_file)
                    except Exception as exc:
                        st.error(f"Failed to save image: {exc}")
                    else:
                        st.session_state.current_image_path = saved_path
                        st.session_state.current_image_hash = file_hash
                        st.session_state.processed_image = None
                        st.session_state.processed_style = None
                        st.session_state.last_time = None
                        current_image_path = saved_path
                        processed_image = None
                        st.rerun()

        # State 2: uploaded -> show workspace preview (result or side-by-side)
        if current_image_path:
            # Side-by-side when result exists, otherwise single original preview
            if processed_image is not None:
                try:
                    if processed_image.ndim == 2:
                        result_display = processed_image
                    else:
                        result_display = bgr_to_rgb(processed_image)
                except Exception:
                    result_display = None

                a, b = st.columns(2, gap="small")
                with a:
                    st.markdown('<div class="studio-img-center">', unsafe_allow_html=True)
                    st.image(current_image_path, width="stretch")
                    st.markdown("</div>", unsafe_allow_html=True)
                with b:
                    st.markdown('<div class="studio-img-center">', unsafe_allow_html=True)
                    if result_display is not None:
                        # Show watermarked preview until paid
                        if st.session_state.get("image_paid"):
                            st.image(result_display, width="stretch")
                        else:
                            wm = apply_watermark(processed_image)
                            st.image(bgr_to_rgb(wm) if wm.ndim == 3 else wm, width="stretch")
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="studio-img-center">', unsafe_allow_html=True)
                st.image(current_image_path, width="stretch")
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # end custom-card

        # Bottom metrics (functional backend)
        last_time = st.session_state.get("last_time")
        processing_text = f"{float(last_time):.2f}s" if last_time is not None else "~—"

        quality_text = "—"
        if processed_image is not None:
            try:
                h, w = processed_image.shape[:2]
                png_bytes = encode_image_to_png(processed_image)
                kb = len(png_bytes) / 1024.0
                tier = "HD" if (w >= 1280 or h >= 720) else "SD"
                quality_text = f"{tier} • {w}x{h}px • {kb:.0f}KB"
            except Exception:
                quality_text = "—"

        styles_count = len(STYLE_CONFIG)  # style_dict keys count

        st.markdown(
            f"""
            <div class="metric-row">
              <div class="custom-card" style="padding:12px 14px;">
                <p class="metric-label">Processing Time</p>
                <p class="metric-value">{processing_text}</p>
              </div>
              <div class="custom-card" style="padding:12px 14px;">
                <p class="metric-label">Output Quality</p>
                <p class="metric-value">{quality_text}</p>
              </div>
              <div class="custom-card" style="padding:12px 14px;">
                <p class="metric-label">Style Options</p>
                <p class="metric-value">{styles_count}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Payment gate: show after a style has been applied ──
        if processed_image is not None:
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            if st.session_state.get("image_paid"):
                # Clean (no-watermark) download
                try:
                    clean_bytes = encode_image_to_png(processed_image)
                    style_label_dl = st.session_state.get("processed_style", "artify")
                    fname = f"artify_{style_label_dl.lower().replace(' ', '_')}.png"
                    st.download_button(
                        "⬇  Download HD Image",
                        data=clean_bytes,
                        file_name=fname,
                        mime="image/png",
                        width="stretch",
                        key="download_clean_img",
                    )
                except Exception:
                    st.error("Could not prepare download.")
            else:
                st.info("🔒 Your result has a watermark. Simulate a payment to unlock the HD download.", icon="🔒")
                if st.button("💳  Simulate Payment", width="stretch", type="primary", key="sim_payment_btn"):
                    record_mock_payment(user_id)
                    st.session_state["image_paid"] = True
                    st.rerun()
            
            # Editor Favorite Toggle
            img_path_for_fav = st.session_state.get("current_image_path")
            if img_path_for_fav:
                is_fav = img_path_for_fav in st.session_state["favorites"]
                if st.button("❤️ Favorited" if is_fav else "🤍 Favorite", key="editor_fav_btn", width="stretch"):
                    toggle_favorite(img_path_for_fav)
                    st.rerun()

    with right_col:


        # ─── CSS ────────────────────────────────────────────────────────────
        st.markdown(
            """
            <style>
            /* ── Panel wrapper ── */
            .rp-card {
                background: #fff;
                border-radius: 15px;
                border: 1px solid rgba(226,232,240,0.95);
                box-shadow: 0 18px 44px rgba(15,23,42,0.08);
                padding: 16px 16px 12px;
                box-sizing: border-box;
            }
            .rp-title { font-size:.9rem; font-weight:800; color:#0f172a; margin:0; }
            .rp-desc  { font-size:.78rem; color:#64748b; margin:0 0 14px; }

            /* ── Scroll area (fixed height) ── */
            .rp-scroll {
                height: 550px;
                overflow-y: auto;
                overflow-x: hidden;
                box-sizing: border-box;
            }
            .rp-scroll::-webkit-scrollbar { width: 5px; }
            .rp-scroll::-webkit-scrollbar-track { background: transparent; }
            .rp-scroll::-webkit-scrollbar-thumb {
                background: rgba(148,163,184,0.45);
                border-radius: 999px;
            }

            /* ── Card body (pure HTML, no click needed here) ── */
            .sc-body {
                background: #fff;
                border-radius: 12px 12px 0 0;
                border: 1.5px solid rgba(226,232,240,0.95);
                border-bottom: none;
                box-shadow: 0 4px 14px rgba(15,23,42,0.07);
                padding: 12px 12px 8px;
                box-sizing: border-box;
                position: relative;
                transition: border-color 160ms ease, box-shadow 160ms ease;
            }
            .sc-body.sc-selected {
                border-color: #4f7df2 !important;
                border-width: 2px !important;
                box-shadow: 0 6px 24px rgba(79,125,242,0.22) !important;
            }
            .sc-img {
                width: 100%; height: 85px;
                object-fit: cover; border-radius: 8px;
                display: block; margin-bottom: 8px;
                border: 1px solid rgba(226,232,240,0.8);
            }
            .sc-name { font-size:.88rem; font-weight:800; color:#0f172a; margin:0 0 3px; }
            .sc-desc { font-size:.73rem; color:#64748b; margin:0; line-height:1.44; }

            /* ── ✓ Badge ── */
            .sc-check {
                position: absolute; top:8px; left:8px;
                width:19px; height:19px; border-radius:50%;
                background:#4f7df2; color:#fff;
                font-size:.65rem; font-weight:900;
                display:flex; align-items:center; justify-content:center;
                box-shadow:0 2px 7px rgba(79,125,242,0.45);
            }
            /* ── POPULAR badge ── */
            .sc-popular {
                position: absolute; top:8px; right:8px;
                font-size:.6rem; font-weight:800;
                letter-spacing:.09em; text-transform:uppercase;
                color:#fff;
                background: linear-gradient(135deg,#f97316,#ec4899);
                padding:.16rem .44rem; border-radius:999px;
                box-shadow:0 3px 10px rgba(236,72,153,.35);
            }

            /* ── Select button — attached to bottom of card body ── */
            /* Target each named container for the overall selected border */
            [class*="st-key-card_slot_"] .stButton button {
                border-radius: 0 0 12px 12px !important;
                border: 1.5px solid rgba(226,232,240,0.95) !important;
                border-top: none !important;
                width: 100% !important;
                font-size: 0.78rem !important;
                font-weight: 700 !important;
                padding: 0.4rem 0 !important;
                cursor: pointer !important;
                transition: background 160ms ease, color 160ms ease !important;
                background: #f8fafc !important;
                color: #64748b !important;
                box-shadow: none !important;
            }
            [class*="st-key-card_slot_"] .stButton button:hover {
                background: #eef2ff !important;
                color: #4f7df2 !important;
                border-color: rgba(79,125,242,0.35) !important;
            }
            /* Selected: primary button override */
            [class*="st-key-card_slot_selected_"] .stButton button {
                background: linear-gradient(135deg,#4f7df2,#18b8df) !important;
                color: #fff !important;
                border-color: #4f7df2 !important;
                box-shadow: 0 4px 14px rgba(79,125,242,0.25) !important;
            }
            /* Selected card body border matches */
            [class*="st-key-card_slot_selected_"] .sc-body {
                border-color: #4f7df2 !important;
                border-width: 2px !important;
                box-shadow: 0 6px 24px rgba(79,125,242,0.2) !important;
            }

            /* Remove Streamlit's extra margin on buttons inside cards */
            [class*="st-key-card_slot_"] .stButton { margin: 0 !important; }
            [class*="st-key-card_slot_"] > div { margin-bottom: 0 !important; }

            /* Gap row between card rows */
            .rp-row-gap { height: 14px; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ─── style the container so it looks like the panel card ─────────────
        st.markdown(
            """
            <style>
            /* ── Make the rp_panel container the visual panel card ── */
            [class*="st-key-rp_panel"] {
                background: #fff !important;
                border-radius: 15px !important;
                border: 1px solid rgba(226,232,240,0.95) !important;
                box-shadow: 0 18px 44px rgba(15,23,42,0.08) !important;
                padding: 16px 16px 12px !important;
                box-sizing: border-box !important;
            }
            .rp-title { font-size:.9rem; font-weight:800; color:#0f172a; margin:0 0 2px; }
            .rp-desc  { font-size:.78rem; color:#64748b; margin:0 0 14px; }

            /* ── Card body ── */
            .sc-body {
                background: #fff;
                border-radius: 12px 12px 0 0;
                border: 1.5px solid rgba(226,232,240,0.95);
                border-bottom: none;
                box-shadow: 0 4px 14px rgba(15,23,42,0.07);
                padding: 12px 12px 8px;
                box-sizing: border-box;
                position: relative;
                transition: border-color 160ms ease, box-shadow 160ms ease;
            }
            .sc-body.sc-selected {
                border-color: #4f7df2 !important;
                border-width: 2px !important;
                box-shadow: 0 6px 24px rgba(79,125,242,0.22) !important;
            }
            .sc-img {
                width:100%; height:85px; object-fit:cover;
                border-radius:8px; display:block; margin-bottom:8px;
                border:1px solid rgba(226,232,240,0.8);
            }
            .sc-name { font-size:.88rem; font-weight:800; color:#0f172a; margin:0 0 3px; }
            .sc-desc { font-size:.73rem; color:#64748b; margin:0; line-height:1.44; }

            /* ── ✓ badge ── */
            .sc-check {
                position:absolute; top:8px; left:8px;
                width:19px; height:19px; border-radius:50%;
                background:#4f7df2; color:#fff;
                font-size:.65rem; font-weight:900;
                display:flex; align-items:center; justify-content:center;
                box-shadow:0 2px 7px rgba(79,125,242,0.45);
            }
            /* ── POPULAR badge ── */
            .sc-popular {
                position:absolute; top:8px; right:8px;
                font-size:.6rem; font-weight:800;
                letter-spacing:.09em; text-transform:uppercase; color:#fff;
                background:linear-gradient(135deg,#f97316,#ec4899);
                padding:.16rem .44rem; border-radius:999px;
                box-shadow:0 3px 10px rgba(236,72,153,.35);
            }

            /* ── Select button fused to card bottom ── */
            [class*="st-key-card_slot_"] .stButton button {
                border-radius: 0 0 12px 12px !important;
                border: 1.5px solid rgba(226,232,240,0.95) !important;
                border-top: none !important;
                width: 100% !important;
                font-size: 0.78rem !important; font-weight: 700 !important;
                padding: 0.4rem 0 !important;
                background: #f8fafc !important; color: #64748b !important;
                box-shadow: none !important;
                transition: background 160ms ease, color 160ms ease !important;
            }
            [class*="st-key-card_slot_"] .stButton button:hover {
                background: #eef2ff !important;
                color: #4f7df2 !important;
                border-color: rgba(79,125,242,0.35) !important;
            }
            [class*="st-key-card_slot_selected_"] .stButton button {
                background: linear-gradient(135deg,#4f7df2,#18b8df) !important;
                color: #fff !important;
                border-color: #4f7df2 !important;
                box-shadow: 0 4px 14px rgba(79,125,242,0.25) !important;
            }
            [class*="st-key-card_slot_selected_"] .sc-body {
                border-color: #4f7df2 !important;
                border-width: 2px !important;
                box-shadow: 0 6px 24px rgba(79,125,242,0.2) !important;
            }
            [class*="st-key-card_slot_"] .stButton { margin:0 !important; }
            [class*="st-key-card_slot_"] > div { margin-bottom:0 !important; }
            .rp-row-gap { height:14px; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ─── Everything inside this container IS visually inside the panel ────
        with st.container(key="rp_panel"):

            # Header
            st.markdown(
                """
                <p class="rp-title">Choose Art Style</p>
                <p class="rp-desc">Select how you want to transform your image</p>
                """,
                unsafe_allow_html=True,
            )

            # ── Cards: st.columns(2) — true 2-column grid ────────────────────
            n = len(style_items)
            for row_start in range(0, n, 2):
                row_items = style_items[row_start: row_start + 2]
                grid_cols = st.columns(2, gap="small")

                for gcol, (style_key, cfg) in zip(grid_cols, row_items):
                    is_selected  = (style_key == selected_style_key)
                    is_premium   = cfg.get("is_premium", False)
                    is_locked    = is_premium and st.session_state.get("active_plan", "Starter") == "Starter"
                    selected_cls = "sc-body sc-selected" if is_selected else "sc-body"
                    slot_key     = (
                        f"card_slot_selected_{style_key}"
                        if is_selected else f"card_slot_{style_key}"
                    )
                    check_html   = '<span class="sc-check">✓</span>' if is_selected else ""
                    popular_html = (
                        '<span class="sc-popular">POPULAR</span>'
                        if cfg.get("popular") else ""
                    )

                    with gcol:
                        with st.container(key=slot_key):
                            st.markdown(
                                f"""
                                <div class="{selected_cls}">
                                  {check_html}{popular_html}
                                  <img src="https://placehold.co/150x150?text=Style"
                                       alt="{cfg['label']}" class="sc-img"/>
                                  <p class="sc-name">{cfg['label']}{' 🔒' if is_locked else ''}</p>
                                  <p class="sc-desc">{cfg['description']}</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            if is_locked:
                                st.button(
                                    "🔒 Pro Only",
                                    key=f"select_style_{style_key}",
                                    width="stretch",
                                    disabled=True,
                                )
                            else:
                                btn_label = "✓  Selected" if is_selected else "Select"
                                if st.button(
                                    btn_label,
                                    key=f"select_style_{style_key}",
                                    width="stretch",
                                ):
                                    st.session_state.selected_style = style_key
                                    st.rerun()

                if row_start + 2 < n:
                    st.markdown('<div class="rp-row-gap"></div>', unsafe_allow_html=True)

    ready = bool(st.session_state.get("current_image_path")) and bool(st.session_state.get("selected_style"))
    transform_clicked = st.button(
        "🪄  Transform with AI  →",
        type="primary",
        width="stretch",
        key="transform_ai_btn",
        disabled=not ready,
    )

    if transform_clicked:
        active_plan = st.session_state.get("active_plan", "Starter")
        monthly_gen = st.session_state.get("monthly_generations", 0)

        # Generation limit gate for Starter
        if active_plan == "Starter" and monthly_gen >= 10:
            st.error("⚠️ Monthly limit reached! You've used all 10 free generations. Upgrade to **Pro** for unlimited images.")
            st.stop()

        image_path = st.session_state.get("current_image_path")
        style_key = cast(str, st.session_state.get("selected_style"))

        with st.spinner("Transforming..."):
            t_start = time.time()
            try:
                if style_key == "classic_cartoon":
                    processed = classic_cartoon(image_path)
                    style_label = STYLE_CONFIG[style_key]["label"]
                elif style_key == "sketch":
                    processed = sketch_effect(image_path)
                    style_label = STYLE_CONFIG[style_key]["label"]
                elif style_key == "sepia":
                    processed = sepia_effect(image_path)
                    style_label = STYLE_CONFIG[style_key]["label"]
                elif style_key == "neon":
                    processed = invert_neon(image_path)
                    style_label = STYLE_CONFIG[style_key]["label"]
                elif style_key == "noir":
                    processed = grayscale_noir(image_path)
                    style_label = STYLE_CONFIG[style_key]["label"]
                else:
                    processed = pencil_color_effect(image_path)
                    style_label = STYLE_CONFIG[style_key]["label"]
            except Exception as exc:
                st.error(f"Failed to process image: {exc}")
                st.session_state.processed_image = None
                st.session_state.processed_style = None
                st.session_state.processing_time = None
                st.session_state.output_quality = None
            else:
                t_end = time.time()
                st.session_state.last_time = round(t_end - t_start, 2)
                st.session_state.processed_image = processed
                st.session_state.processed_style = style_label
                # Increment generation counter
                st.session_state["monthly_generations"] = monthly_gen + 1

                st.rerun()

# Determine active section from session BEFORE sidebar render
section = st.session_state.get("dash_section", "dashboard")

# ─────────────────────────────────────────────
# SIDEBAR — minimal, no logo, no workspace labels
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <style>
        /* Sidebar-only navigation styling (scoped) */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
        }

        /* Make sidebar content a flex column so footer can stick bottom */
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            display: flex !important;
            flex-direction: column !important;
            min-height: 100vh !important;
        }

        /* Navigation buttons base */
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 0.95rem !important;
            border: 1px solid #e6edf7 !important;
            background: #ffffff !important;
            box-shadow: 0 10px 22px rgba(148, 163, 184, 0.16) !important;
            color: #24324a !important;
            font-weight: 750 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            gap: 0.65rem !important;
            padding: 0.72rem 0.85rem !important;
            min-height: 3.1rem !important;
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease !important;
        }

        [data-testid="stSidebar"] .stButton > button:hover {
            transform: translateY(-1px) !important;
            border-color: #cfe0ff !important;
            box-shadow: 0 14px 26px rgba(148, 163, 184, 0.20) !important;
        }

        /* Active state (Streamlit primary buttons) */
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            border: none !important;
            background: linear-gradient(135deg, #4d7ff5 0%, #18b5df 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 16px 34px rgba(77, 127, 245, 0.28) !important;
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"] * {
            color: #ffffff !important;
        }

        /* Ensure button label text aligns left */
        [data-testid="stSidebar"] .stButton > button div,
        [data-testid="stSidebar"] .stButton > button p,
        [data-testid="stSidebar"] .stButton > button span {
            text-align: left !important;
        }

        /* Footer */
        [data-testid="stSidebar"] .st-key-sb_footer {
            margin-top: auto !important;
            padding-top: 0.75rem !important;
            padding-bottom: 0.75rem !important;
        }

        [data-testid="stSidebar"] hr.sb-hr {
            border: none !important;
            border-top: 1px solid #e6edf7 !important;
            margin: 0.75rem 0 0.9rem 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_sidebar_profile()

    # Navigation — SPA style, sections within dashboard
    nav = st.container(key="sb_nav")
    with nav:
        if st.button(
            "📊  Dashboard",
            width="stretch",
            type="primary" if section == "dashboard" else "secondary",
            key="sb_nav_dashboard",
        ):
            st.session_state["dash_section"] = "dashboard"
            st.rerun()

        if st.button(
            "🪄  Image Editor",
            width="stretch",
            type="primary" if section == "editor" else "secondary",
            key="sb_nav_editor",
        ):
            st.session_state["dash_section"] = "editor"
            st.rerun()

        if st.button(
            "🕒  My Images",
            width="stretch",
            type="primary" if section == "my_images" else "secondary",
            key="sb_nav_my_images",
        ):
            st.session_state["dash_section"] = "my_images"
            st.rerun()

        if st.button(
            "💳  Payments",
            width="stretch",
            type="primary" if section == "payments" else "secondary",
            key="sb_nav_payments",
        ):
            st.session_state["dash_section"] = "payments"
            st.rerun()

        if st.button(
            "👤  Profile",
            width="stretch",
            type="primary" if section == "profile" else "secondary",
            key="sb_nav_profile",
        ):
            st.session_state["dash_section"] = "profile"
            st.rerun()

    footer = st.container(key="sb_footer")
    with footer:
        st.markdown('<hr class="sb-hr" />', unsafe_allow_html=True)

        # Logout remains neutral and separated at the bottom
        if st.button("🚪  Log out", width="stretch", type="secondary", key="sb_logout"):
            st.session_state.clear()
            st.switch_page("app.py")
            st.stop()

# ─────────────────────────────────────────────
# MAIN — section-based view switching (Dashboard, Editor, My Images, Payments, Profile)
# ─────────────────────────────────────────────

if section == "dashboard":
    # Header
    
    st.markdown(f'<h1 class="dash-title">Welcome back, {username} 👋</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="dash-sub">Here\'s an overview of your AI artwork activity.</p>',
        unsafe_allow_html=True,
    )

    # ── Stat cards ──
    images_count = metrics["images_processed"]
    st.markdown(
        f"""
        <div class="stat-row">
          <div class="stat-card">
            <div class="stat-card-top">
              <div class="stat-icon stat-icon-blue">⚡</div>
              <span class="stat-badge stat-badge-green">↑ +12%</span>
            </div>
            <div class="stat-value">{images_count}</div>
            <div class="stat-label">Images Processed</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-top">
              <div class="stat-icon stat-icon-purple">🎨</div>
              <span class="stat-badge stat-badge-blue">New</span>
            </div>
            <div class="stat-value">3</div>
            <div class="stat-label">Available Styles</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-top">
              <div class="stat-icon stat-icon-pink">⬇</div>
              <span class="stat-badge stat-badge-green">↑ +8%</span>
            </div>
            <div class="stat-value">{images_count}</div>
            <div class="stat-label">Total Downloads</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── My Favorites header ──
    st.markdown(
        """
        <div class="rc-header">
          <div>
            <p class="rc-title">My Favorites</p>
            <p class="rc-sub">Your hand-picked AI-generated artwork</p>
          </div>
          <a class="rc-view-all" href="#">View All →</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Cards or empty state ──
    fav_creations = [item for item in recent_creations if item["processed_image_path"] in st.session_state.get("favorites", [])]
    if fav_creations:
        cards_html = '<div class="rc-grid">'
        download_data = []

        for idx, item in enumerate(fav_creations[:8]):
            img_path = item["processed_image_path"]
            style    = item["style_applied"]
            date_str = _fmt_date(item["processing_date"])
            b64      = _img_to_b64(img_path)

            if b64:
                img_html = f'<img class="rc-card-img" src="{b64}" alt="{style}">'
            else:
                img_html = '<div class="rc-card-img-fallback">🖼</div>'

            cards_html += f"""
            <div class="rc-card">
                {img_html}
                <div class="rc-card-body">
                    <p class="rc-card-style">{style}</p>
                    <p class="rc-card-date">{date_str}</p>
                </div>
            </div>
            """
            try:
                _active_plan_dl = st.session_state.get("active_plan", "Starter")
                raw_img = read_image(img_path)
                if raw_img is not None and _active_plan_dl == "Starter":
                    h_raw, w_raw = raw_img.shape[:2]
                    if w_raw > 1280:
                        scale = 1280 / w_raw
                        raw_img = cv2.resize(raw_img, (1280, int(h_raw * scale)), interpolation=cv2.INTER_AREA)
                    raw_img = apply_watermark(raw_img)
                    img_bytes = encode_image_to_png(raw_img)
                else:
                    img_bytes = Path(img_path).read_bytes()
                fname = f"artify_{style.lower().replace(' ','_')}.png"
                download_data.append((img_bytes, fname, f"dl_fav_{idx}"))
            except Exception:
                continue

        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

        # Download buttons aligned to cards
        COLS = 4
        for row_start in range(0, len(fav_creations[:8]), COLS):
            chunk = download_data[row_start: row_start + COLS]
            cols  = st.columns(len(chunk))
            for col, (data, fname, key) in zip(cols, chunk):
                with col:
                    if data and fname and key:
                        st.download_button(
                            "⬇  Download", data=data,
                            file_name=fname, mime="image/png",
                            key=key, width="stretch",
                        )
    else:
        st.markdown(
            """
            <div class="rc-empty">
                <span class="rc-empty-icon">❤️</span>
                <p class="rc-empty-title">No favorites yet</p>
                <p class="rc-empty-text">
                    No favorites yet. Heart an image in 'My Images' to see it here!
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# IMAGE EDITOR PANEL (in-dashboard workspace)
# ─────────────────────────────────────────────

elif section == "editor":
    render_editor()

# ─────────────────────────────────────────────
# MY IMAGES PANEL
# ─────────────────────────────────────────────

elif section == "my_images":
    st.markdown('<h1 class="dash-title">My Images</h1>', unsafe_allow_html=True)
    st.markdown('<p class="dash-sub">All your AI-generated artwork.</p>', unsafe_allow_html=True)

    if recent_creations:
        cards_html = '<div class="rc-grid">'
        from typing import List, Tuple, Any
        download_data: List[Tuple[Any, str, str, str]] = []  # list of (img_bytes, filename, key, path)
        for idx, item in enumerate(recent_creations):
            img_path = item["processed_image_path"]
            style    = item["style_applied"]
            date_str = _fmt_date(item["processing_date"])
            b64      = _img_to_b64(img_path)

            if b64:
                img_html = f'<img class="rc-card-img" src="{b64}" alt="{style}">'
            else:
                img_html = '<div class="rc-card-img-fallback">🖼</div>'

            cards_html += f"""
            <div class="rc-card">
                {img_html}
                <div class="rc-card-body">
                    <p class="rc-card-style">{style}</p>
                    <p class="rc-card-date">{date_str}</p>
                </div>
            </div>
            """
            try:
                _active_plan_dl = st.session_state.get("active_plan", "Starter")
                raw_img = read_image(img_path)
                if raw_img is not None and _active_plan_dl == "Starter":
                    # 720p cap + watermark for Starter
                    h_raw, w_raw = raw_img.shape[:2]
                    if w_raw > 1280:
                        scale = 1280 / w_raw
                        raw_img = cv2.resize(raw_img, (1280, int(h_raw * scale)), interpolation=cv2.INTER_AREA)
                    raw_img = apply_watermark(raw_img)
                    img_bytes = encode_image_to_png(raw_img)
                else:
                    img_bytes = Path(img_path).read_bytes()
                fname = f"artify_{style.lower().replace(' ','_')}.png"
                download_data.append((img_bytes, fname, f"dl_idx_myimg_{idx}", img_path))
            except Exception:
                continue

        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

        COLS = 4
        for row_start in range(0, len(recent_creations), COLS):
            chunk = download_data[row_start: row_start + COLS]
            cols  = st.columns(len(chunk))
            for col, (data, fname, key, img_path) in zip(cols, chunk):
                with col:
                    if data and fname and key:
                        st.download_button(
                            "⬇  Download", data=data,
                            file_name=fname, mime="image/png",
                            key=key, width="stretch",
                        )
                        is_fav = img_path in st.session_state["favorites"]
                        if st.button("❤️ Favorited" if is_fav else "🤍 Favorite", key=f"fav_{key}", width="stretch"):
                            toggle_favorite(img_path)
                            st.rerun()
    else:
        st.markdown(
            """
            <div class="rc-empty">
                <span class="rc-empty-icon">✨</span>
                <p class="rc-empty-title">No creations yet</p>
                <p class="rc-empty-text">You haven't processed any images yet.</p>
            </div>
            """, unsafe_allow_html=True
        )

# ─────────────────────────────────────────────
# PAYMENTS PANEL
# ─────────────────────────────────────────────

elif section == "payments":

    # ── Initialise subscription state ──────────────────────────────────────
    sub_defaults = {
        "plan_name": "Starter",
        "purchase_date": "N/A",
        "expiry_date": "Never",
    }
    for k, v in sub_defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    from datetime import timedelta

    def _activate_plan(plan: str) -> None:
        now = datetime.now()
        existing = st.session_state.get("plan_name", "Starter")
        try:
            exp = datetime.strptime(st.session_state.get("expiry_date", "Never"), "%Y-%m-%d")
        except ValueError:
            exp = now

        if existing == plan and st.session_state.get("expiry_date") not in ("Never", "N/A"):
            # Stack: extend by 30 days from current expiry
            new_exp = exp + timedelta(days=30)
        else:
            # New plan or switch: reset window from today
            new_exp = now + timedelta(days=30)

        st.session_state["plan_name"] = plan
        st.session_state["purchase_date"] = now.strftime("%Y-%m-%d")
        st.session_state["expiry_date"] = new_exp.strftime("%Y-%m-%d")

    plan_name     = st.session_state.get("plan_name", "Starter")
    purchase_date = st.session_state.get("purchase_date", "N/A")
    expiry_date   = st.session_state.get("expiry_date", "Never")

    # ── Pricing-page CSS ───────────────────────────────────────────────────
    st.markdown("""
    <style>
    .pricing-header { text-align:center; padding: 1.5rem 0 0.5rem; }
    .pricing-header .pill-badge {
        display:inline-block; background:#eef2ff; color:#4f46e5;
        font-size:.75rem; font-weight:700; padding:.3rem .9rem;
        border-radius:999px; margin-bottom:.9rem; letter-spacing:.04em;
    }
    .pricing-header h1 {
        font-size:2.1rem; font-weight:800; margin:0 0 .4rem; color:#0f172a;
    }
    .pricing-header p { color:#6c7a93; font-size:1rem; margin:0; }

    .sub-banner {
        background:#f8fafc; border:1.5px solid #e2e8f0;
        border-radius:12px; padding:1rem 1.4rem;
        display:flex; gap:2.5rem; align-items:center;
        margin-bottom:1.6rem; flex-wrap:wrap;
    }
    .sub-banner .sb-item { display:flex; flex-direction:column; gap:.15rem; }
    .sub-banner .sb-label { font-size:.7rem; font-weight:700; text-transform:uppercase;
        letter-spacing:.08em; color:#94a3b8; }
    .sub-banner .sb-value { font-size:.97rem; font-weight:700; color:#1e293b; }
    .sub-banner .sb-badge {
        background:#dcfce7; color:#16a34a; border-radius:999px;
        font-size:.72rem; font-weight:700; padding:.2rem .7rem;
    }

    .pc-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1.25rem;
        margin-top:1rem; }

    .pc-card {
        background:#fff; border-radius:18px;
        border:1.5px solid #e2e8f0;
        box-shadow:0 6px 22px rgba(15,23,42,.06);
        padding:1.6rem 1.4rem 1.4rem;
        position:relative; display:flex; flex-direction:column; gap:.7rem;
        transition:transform .2s, box-shadow .2s;
    }
    .pc-card:hover { transform:translateY(-3px); box-shadow:0 14px 36px rgba(15,23,42,.10); }
    .pc-card.popular {
        border-color:#6366f1;
        box-shadow:0 10px 40px rgba(99,102,241,.18);
    }

    .pc-badge-popular {
        position:absolute; top:-14px; left:50%; transform:translateX(-50%);
        background:linear-gradient(90deg,#6366f1,#8b5cf6);
        color:#fff; font-size:.73rem; font-weight:700; padding:.3rem 1.1rem;
        border-radius:999px; white-space:nowrap; letter-spacing:.04em;
    }
    .pc-badge-current {
        position:absolute; top:-14px; left:50%; transform:translateX(-50%);
        background:#22c55e; color:#fff; font-size:.73rem; font-weight:700;
        padding:.3rem 1.1rem; border-radius:999px; white-space:nowrap;
    }

    .pc-icon { font-size:2rem; margin-bottom:.2rem; }
    .pc-name { font-size:1.15rem; font-weight:700; color:#1e293b; margin:0; }
    .pc-price { display:flex; align-items:flex-end; gap:.25rem; margin:.1rem 0 .3rem; }
    .pc-price .amt { font-size:2.1rem; font-weight:800; color:#1e293b; line-height:1; }
    .pc-price .per { font-size:.85rem; color:#64748b; padding-bottom:.2rem; }
    .pc-features { list-style:none; padding:0; margin:0; flex:1;
        display:flex; flex-direction:column; gap:.45rem; }
    .pc-features li { font-size:.88rem; color:#334155; display:flex; gap:.5rem; align-items:flex-start; }
    .pc-features li span.fi { color:#6366f1; flex-shrink:0; }

    .pc-btn {
        width:100%; padding:.72rem 0; border-radius:10px; border:none;
        font-size:.95rem; font-weight:700; cursor:pointer; margin-top:.4rem;
        transition:opacity .18s;
    }
    .pc-btn-disabled {
        background:#f1f5f9; color:#94a3b8; cursor:not-allowed;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Page header ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="pricing-header">
        <div class="pill-badge">🏷 Pricing Plans</div>
        <h1>Choose Your Creative Power</h1>
        <p>Select the perfect plan to unlock unlimited AI creativity</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Current subscription banner ────────────────────────────────────────
    st.markdown(f"""
    <div class="sub-banner">
        <div class="sb-item">
            <span class="sb-label">Current Plan</span>
            <span class="sb-value">{plan_name} Plan</span>
        </div>
        <div class="sb-item">
            <span class="sb-label">Status</span>
            <span class="sb-badge">Active</span>
        </div>
        <div class="sb-item">
            <span class="sb-label">Purchase Date</span>
            <span class="sb-value">{purchase_date}</span>
        </div>
        <div class="sb-item">
            <span class="sb-label">Expiry Date</span>
            <span class="sb-value">{expiry_date}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Pricing cards ──────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3, gap="medium")

    # STARTER
    with c1:
        is_current = plan_name == "Starter"
        badge = '<span class="pc-badge-current">Current Plan</span>' if is_current else ""
        st.html(f"""
        <div class="pc-card">
            {badge}
            <div class="pc-icon">⚡</div>
            <p class="pc-name">Starter</p>
            <div class="pc-price">
                <span class="amt">$0</span>
                <span class="per">/forever</span>
            </div>
            <ul class="pc-features">
                <li><span class="fi">✅</span> 10 images per month</li>
                <li><span class="fi">✅</span> 3 basic styles</li>
                <li><span class="fi">✅</span> Standard quality (720p)</li>
                <li><span class="fi">✅</span> Email support</li>
                <li><span class="fi">✅</span> Watermark on images</li>
            </ul>
        </div>
        """)
        if is_current:
            st.button("Current Plan", key="btn_starter", disabled=True, width="stretch")
        else:
            if st.button("Get Started", key="btn_starter_go", width="stretch"):
                _activate_plan("Starter")
                st.rerun()

    # PRO
    with c2:
        is_current = plan_name == "Pro"
        badge = '<span class="pc-badge-current">Current Plan</span>' if is_current else '<span class="pc-badge-popular">⭐ Most Popular</span>'
        st.html(f"""
        <div class="pc-card popular">
            {badge}
            <div class="pc-icon">👑</div>
            <p class="pc-name">Pro</p>
            <div class="pc-price">
                <span class="amt">$9.99</span>
                <span class="per">/per month</span>
            </div>
            <ul class="pc-features">
                <li><span class="fi">✅</span> Unlimited images</li>
                <li><span class="fi">✅</span> All 6+ premium styles</li>
                <li><span class="fi">✅</span> High quality (1080p)</li>
                <li><span class="fi">✅</span> Priority support</li>
                <li><span class="fi">✅</span> No watermark</li>
            </ul>
        </div>
        """)
        if is_current:
            if st.button("Extend 30 Days", key="btn_pro_extend", type="primary", width="stretch"):
                _activate_plan("Pro")
                st.session_state["active_plan"] = "Pro"
                st.session_state["monthly_generations"] = 0
                st.rerun()
        else:
            if st.button("Get Started", key="btn_pro_go", type="primary", width="stretch"):
                _activate_plan("Pro")
                st.session_state["active_plan"] = "Pro"
                st.session_state["monthly_generations"] = 0
                st.rerun()

    # ENTERPRISE
    with c3:
        is_current = plan_name == "Enterprise"
        badge = '<span class="pc-badge-current">Current Plan</span>' if is_current else ""
        st.html(f"""
        <div class="pc-card">
            {badge}
            <div class="pc-icon">💎</div>
            <p class="pc-name">Enterprise</p>
            <div class="pc-price">
                <span class="amt">$29.99</span>
                <span class="per">/per month</span>
            </div>
            <ul class="pc-features">
                <li><span class="fi">✅</span> Unlimited images</li>
                <li><span class="fi">✅</span> Custom style creation</li>
                <li><span class="fi">✅</span> Ultra quality (4K)</li>
                <li><span class="fi">✅</span> 24/7 dedicated support</li>
                <li><span class="fi">✅</span> White-label option</li>
            </ul>
        </div>
        """)
        if is_current:
            if st.button("Extend 30 Days", key="btn_ent_extend", width="stretch"):
                _activate_plan("Enterprise")
                st.session_state["active_plan"] = "Enterprise"
                st.session_state["monthly_generations"] = 0
                st.rerun()
        else:
            if st.button("Get Started", key="btn_ent_go", width="stretch"):
                _activate_plan("Enterprise")
                st.session_state["active_plan"] = "Enterprise"
                st.session_state["monthly_generations"] = 0
                st.rerun()



# ─────────────────────────────────────────────
# PROFILE PANEL
# ─────────────────────────────────────────────

elif section == "profile":

    # Fallbacks in case user data is missing
    display_name = username if username else "John Doe"
    display_email = email if email else "john.doe@example.com"
    initials = display_name[:2].upper() if display_name else "JD"
    since_date = "Jan 2026"
    if profile.get("created_at") and profile["created_at"] != "N/A":
        try:
            since_dt = datetime.strptime(str(profile["created_at"]).split()[0], "%Y-%m-%d")
            since_date = since_dt.strftime("%b %Y")
        except Exception:
            since_date = str(profile["created_at"])

    # 1. Page Header
    st.markdown("""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom: 2rem;">
            <div style="width:40px; height:40px; border-radius:10px; background:linear-gradient(135deg, #7c3aed, #4f46e5); display:flex; align-items:center; justify-content:center; color:white; font-size:20px;">
                👤
            </div>
            <h1 style="color:#0f172a; font-size:1.8rem; font-weight:800; margin:0; padding:0; line-height:1;">Profile Settings</h1>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. Add full CSS block for the Profile page
    st.markdown("""
        <style>
        /* Card Containers */
        .pf-card {
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(15, 23, 42, 0.04);
            border: 1px solid rgba(226, 232, 240, 0.8);
            padding: 24px;
            margin-bottom: 24px;
        }
        
        /* Main Header Area inside the first card */
        .pf-header-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 16px;
        }
        .pf-user-info {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .pf-avatar {
            width: 88px;
            height: 88px;
            border-radius: 20px;
            background: linear-gradient(135deg, #4f46e5 0%, #d946ef 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 32px;
            font-weight: 800;
            position: relative;
            box-shadow: 0 12px 24px rgba(79, 70, 229, 0.25);
        }
        .pf-avatar-cam {
            position: absolute;
            bottom: -6px;
            right: -6px;
            background: #ffffff;
            border-radius: 50%;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            font-size: 14px;
            color: #64748b;
        }
        .pf-name {
            font-size: 1.5rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 4px 0;
            line-height:1;
        }
        .pf-email {
            font-size: 0.95rem;
            color: #64748b;
            margin: 0;
            font-weight: 500;
        }
        
        /* Grid Area inside the first card */
        .pf-stats-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 16px;
        }
        @media (max-width: 800px) {
            .pf-stats-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        .pf-stat {
            background: rgba(248, 250, 252, 0.5);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 14px;
            border: 1px solid rgba(226, 232, 240, 0.6);
            transition: transform 150ms ease;
        }
        .pf-stat:hover {
            transform: translateY(-2px);
        }
        .pf-stat-icon {
            width: 44px;
            height: 44px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        .pf-stat-blue { background: #eff6ff; color: #3b82f6; }
        .pf-stat-purp { background: #faf5ff; color: #a855f7; }
        .pf-stat-pink { background: #fdf2f8; color: #ec4899; }
        .pf-stat-green{ background: #f0fdf4; color: #22c55e; }
        
        .pf-stat-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin: 0 0 2px 0;
            font-weight: 700;
        }
        .pf-stat-val {
            font-size: 0.95rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* Account Info Section */
        .pf-section-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 20px 0;
        }
        .pf-form-group {
            margin-bottom: 20px;
        }
        .pf-label {
            display: block;
            font-size: 0.85rem;
            font-weight: 700;
            color: #334155;
            margin-bottom: 8px;
        }
        .pf-input {
            width: 100%;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px 16px;
            font-size: 0.95rem;
            color: #475569;
            font-weight: 500;
            font-family: inherit;
            box-sizing: border-box;
            outline: none;
            cursor: not-allowed;
            transition: border-color 200ms ease;
        }
        .pf-input:hover {
            border-color: #cbd5e1;
        }
        
        /* Button styling for Edit Profile HTML */
        .pf-edit-btn {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            color: white !important;
            border: none;
            border-radius: 999px;
            padding: 10px 24px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: transform 150ms ease, box-shadow 150ms ease;
        }
        .pf-edit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 24px rgba(99, 102, 241, 0.4);
        }
        </style>
    """, unsafe_allow_html=True)

    # 3. Main Profile Card (Header + Stats Grid)
    # Using a st.container to house the card so Streamlit widgets can be injected
    st.markdown('<div class="pf-card" style="padding-bottom: 0;">', unsafe_allow_html=True)
    
    # Header Row with Avatar and Edit Button
    st.markdown(f"""
        <div class="pf-header-row">
            <div class="pf-user-info">
                <div class="pf-avatar">
                    {initials}
                    <div class="pf-avatar-cam">📷</div>
                </div>
                <div>
                    <p class="pf-name">{display_name}</p>
                    <p class="pf-email">{display_email}</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Inject Edit Button precisely via negative margin
    st.markdown("<div style='display:flex; justify-content:flex-end; margin-top:-95px'>", unsafe_allow_html=True)
    if st.button("⚙️ Edit Profile", key="btn_edit_profile"):
        st.session_state["edit_profile_mode"] = not st.session_state.get("edit_profile_mode", False)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f"""
            <div class="pf-stats-grid" style="margin-top: 10px;">
                <!-- Username -->
                <div class="pf-stat pf-stat-blue" style="background:#f0f7ff; border-color:#dbeafe;">
                    <div class="pf-stat-icon" style="background:#3b82f6; color:#fff;">👤</div>
                    <div>
                        <p class="pf-stat-label" style="color:#2563eb;">Username</p>
                        <p class="pf-stat-val">{username}</p>
                    </div>
                </div>
                <!-- Email -->
                <div class="pf-stat pf-stat-purp" style="background:#faf5ff; border-color:#f3e8ff;">
                    <div class="pf-stat-icon" style="background:#a855f7; color:#fff;">✉️</div>
                    <div>
                        <p class="pf-stat-label" style="color:#9333ea;">Email</p>
                        <p class="pf-stat-val" title="{display_email}">{display_email[:12]}...</p>
                    </div>
                </div>
                <!-- Member Since -->
                <div class="pf-stat pf-stat-pink" style="background:#fdf2f8; border-color:#fce7f3;">
                    <div class="pf-stat-icon" style="background:#ec4899; color:#fff;">📅</div>
                    <div>
                        <p class="pf-stat-label" style="color:#db2777;">Member Since</p>
                        <p class="pf-stat-val">{since_date}</p>
                    </div>
                </div>
                <!-- Status -->
                <div class="pf-stat pf-stat-green" style="background:#f0fdf4; border-color:#dcfce7;">
                    <div class="pf-stat-icon" style="background:#22c55e; color:#fff;">🛡️</div>
                    <div>
                        <p class="pf-stat-label" style="color:#16a34a;">Status</p>
                        <p class="pf-stat-val">Active</p>
                    </div>
                </div>
            </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. Account Information Section (Bottom Card)
    st.markdown('<div class="pf-card">', unsafe_allow_html=True)
    st.markdown('<h2 class="pf-section-title">Account Information</h2>', unsafe_allow_html=True)
    
    if st.session_state.get("edit_profile_mode"):
        with st.form("edit_profile_form"):
            new_name = st.text_input("Full Name", value=display_name)
            new_email = st.text_input("Email Address", value=display_email)
            if st.form_submit_button("Save Changes", type="primary"):
                st.toast("Profile updated successfully! (Mock)", icon="✅")
                st.session_state["edit_profile_mode"] = False
                st.rerun()
    else:
        st.markdown(f"""
            <div class="pf-form-group">
                <label class="pf-label">Full Name</label>
                <div class="pf-input">{display_name}</div>
            </div>
            
            <div class="pf-form-group">
                <label class="pf-label">Email Address</label>
                <div class="pf-input">{display_email}</div>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
