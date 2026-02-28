import hashlib
import sys
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.image_upload import get_image_metadata, save_uploaded_image, validate_image


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
            --brand-500: #14b8a6;
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

        .page-kicker {
            display: inline-block;
            background: rgba(13, 99, 93, 0.10);
            color: #0f766e;
            border: 1px solid rgba(15, 118, 110, 0.24);
            border-radius: 999px;
            padding: 0.34rem 0.84rem;
            font-size: 0.72rem;
            letter-spacing: 0.095em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.65rem;
        }

        .page-title {
            margin: 0.1rem 0 0.5rem 0;
            font-size: clamp(1.95rem, 3.1vw, 2.85rem);
            line-height: 1.05;
            letter-spacing: -0.025em;
            color: var(--ink-900);
            font-weight: 800;
        }

        .page-sub {
            color: var(--ink-700);
            font-size: 1rem;
            line-height: 1.55;
            margin-bottom: 0.9rem;
        }

        .meta-card {
            background: var(--card-bg);
            border: 1px solid var(--card-stroke);
            border-radius: 1rem;
            padding: 1rem 1.05rem;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
        }

        .meta-title {
            color: var(--ink-900);
            font-size: 1.02rem;
            font-weight: 750;
            margin-bottom: 0.7rem;
        }

        .meta-item {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.52rem 0;
            border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            color: var(--ink-700);
            font-size: 0.92rem;
        }

        .meta-item:last-child {
            border-bottom: none;
        }

        .meta-key {
            color: var(--ink-500);
            font-weight: 600;
        }

        .meta-value {
            color: var(--ink-900);
            font-weight: 700;
            text-align: right;
        }

        [data-testid="stFileUploader"] section {
            border-radius: 0.95rem;
            border: 1px dashed rgba(15, 118, 110, 0.45);
            background: rgba(255,255,255,0.68);
        }

        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, var(--brand-800) 0%, var(--brand-500) 100%);
            border: none;
            color: #ffffff;
            font-weight: 700;
            border-radius: 0.72rem;
            box-shadow: 0 10px 22px rgba(15, 118, 110, 0.22);
        }

        [data-testid="stLogo"] img,
        [data-testid="stLogo"] svg {
            max-height: 4.1rem !important;
            width: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


assets_dir = Path(__file__).resolve().parents[1] / "assets"
icon_png = assets_dir / "artify_logo.png"
logo_svg = assets_dir / "artify_logo.svg"
logo_asset = logo_svg if logo_svg.exists() else icon_png

st.set_page_config(
    page_title="Image Upload & Preview",
    page_icon=str(icon_png) if icon_png.exists() else ":art:",
    layout="wide",
)

apply_styles()

if logo_asset.exists() and hasattr(st, "logo"):
    try:
        st.logo(str(logo_asset), size="large")
    except TypeError:
        st.logo(str(logo_asset))

# Protect page: login required
if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.switch_page("app.py")
    st.stop()

if "current_image_path" not in st.session_state:
    st.session_state.current_image_path = None
if "current_image_hash" not in st.session_state:
    st.session_state.current_image_hash = None

with st.sidebar:
    st.markdown("### Image Tools")
    st.caption("Upload, review metadata, and replace current image.")
    st.markdown("---")
    if st.button("Back to dashboard", use_container_width=True):
        st.switch_page("pages/dashboard.py")
        st.stop()
    if st.button("Back to home", use_container_width=True):
        st.switch_page("app.py")
        st.stop()

st.markdown('<div class="page-kicker">IMAGE STUDIO</div>', unsafe_allow_html=True)
st.markdown('<h1 class="page-title">Image Upload & Preview</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="page-sub">Upload a supported file, validate it, and inspect image metadata before processing.</p>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload image",
    type=["jpg", "jpeg", "png", "bmp"],
    help="Supported formats: JPG, JPEG, PNG, BMP. Max size: 10 MB.",
)

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
        # Prevent duplicate saves while the same upload remains selected in Streamlit.
        file_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
        current_hash = st.session_state.get("current_image_hash")
        current_path = st.session_state.get("current_image_path")

        if (not current_path) or (file_hash != current_hash):
            try:
                saved_path = save_uploaded_image(uploaded_file)
            except Exception as exc:
                st.error(f"Failed to save image: {exc}")
            else:
                st.session_state.current_image_path = saved_path
                st.session_state.current_image_hash = file_hash
                st.success("Image validated and saved successfully.")

current_image_path = st.session_state.get("current_image_path")

if current_image_path:
    image_path_obj = Path(current_image_path)
    if not image_path_obj.exists():
        st.warning("Saved image path no longer exists. Please upload again.")
        st.session_state.current_image_path = None
        st.session_state.current_image_hash = None
        st.stop()

    try:
        metadata = get_image_metadata(current_image_path)
    except Exception as exc:
        st.error(f"Could not read image metadata: {exc}")
        st.stop()

    image_col, meta_col = st.columns([1.55, 1], gap="large")

    with image_col:
        with st.container(border=True):
            st.subheader("Preview")
            st.image(current_image_path, use_container_width=True)
            st.caption(str(image_path_obj))

    with meta_col:
        st.markdown(
            f"""
            <div class="meta-card">
                <div class="meta-title">Image Metadata</div>
                <div class="meta-item"><span class="meta-key">Width</span><span class="meta-value">{metadata['width']} px</span></div>
                <div class="meta-item"><span class="meta-key">Height</span><span class="meta-value">{metadata['height']} px</span></div>
                <div class="meta-item"><span class="meta-key">Size</span><span class="meta-value">{metadata['file_size_mb']:.4f} MB</span></div>
                <div class="meta-item"><span class="meta-key">Format</span><span class="meta-value">{metadata['format']}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")
        if st.button("Replace Image", type="primary", use_container_width=True):
            st.session_state.current_image_path = None
            st.session_state.current_image_hash = None
            st.rerun()
else:
    st.info("Upload an image to preview and view metadata.")
