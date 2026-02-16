import streamlit as st

# =========================
# PAGE CONFIGURATION
# =========================

st.set_page_config(
    page_title="Dashboard",
    page_icon="",
    layout="wide"
)

# =========================
# PROTECT PAGE (LOGIN REQUIRED)
# =========================

if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.switch_page("app.py")
    st.stop()

# Safe session access
username = st.session_state.get("username", "User")
email = st.session_state.get("email", "Not Available")

# =========================
# SIDEBAR NAVIGATION
# =========================

with st.sidebar:
    st.title("🎨 AI Platform")
    st.write(f"Logged in as: **{username}**")
    st.markdown("---")

    menu = st.radio(
        "Navigation",
        ["Image Processing", "Payment History", "Profile Settings"]
    )

    st.markdown("---")

    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("app.py")
        st.stop()

# =========================
# MAIN DASHBOARD CONTENT
# =========================

st.title("Artify AI Dashboard")
st.success(f"Welcome back, {username}!")
st.markdown("---")

# =========================
# PAGE SECTIONS
# =========================

if menu == "Image Processing":
    st.header("🎨 AI Image Processing")
    st.info("OpenCV cartoonization module will be integrated here.")

    uploaded_file = st.file_uploader(
        "Upload an image to cartoonize",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPG, JPEG, PNG"
    )

elif menu == "Payment History":
    st.header("💳 Payment History")
    st.info("Your transaction history will appear here after payment integration.")

elif menu == "Profile Settings":
    st.header("⚙️ Profile Settings")

    with st.container(border=True):
        st.subheader("Account Details")
        st.write(f"👤 **Username:** {username}")
        st.write(f"📧 **Email:** {email}")
