# Artify AI — AI Image Stylization App

A Python Streamlit application that lets you upload images and convert them into cartoon, sketch, and pencil styles using OpenCV. Includes email/password authentication and **Google OAuth login**.

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/artify-ai.git
cd artify-ai
```

### 2. Create & activate a virtual environment
```bash
py -3.11 -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS / Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up Google OAuth credentials *(required for Google login)*

We recommend setting up OAuth 2.0 to access Google login. Credentials are **never committed** to this repo.
Here is the 3-step process for providing local credentials:

**Step 1. Copy the environment file**
```bash
cp .env.example .env
```
> ⚠️ `.env` is in `.gitignore` — it will **never** be committed.

**Step 2. Add Google Cloud Keys**
Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services → Credentials**. Generate OAuth 2.0 Client IDs, and add them to your new `.env` file:
```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```
*(Alternatively, you can securely configure Streamlit cloud secrets via `st.secrets`, or download the credentials.json and save it to `backend/auth/google_credentials.json`)*

**Step 3. Set the Redirect URI**
In Google Cloud Console, ensure you set your Authorized Redirect URIs to exactly:
`http://localhost:8501`

### 5. Run the application
```bash
streamlit run frontend/app.py
```

The app will be available at **http://localhost:8501**

---

## 📁 Project Structure
```
artify-ai/
├── frontend/           # Streamlit UI
│   └── app.py
├── backend/            # Auth & processing logic
│   ├── auth.py
│   ├── auth_login.py
│   ├── auth_google.py
│   └── auth/           # ← Place google_credentials.json here (not committed)
├── database/           # SQLite database helpers
├── utils/              # Image utilities
├── .env.example        # Template for environment variables
└── requirements.txt
```

---

## 🔐 Security Notes
- `backend/auth/google_credentials.json` is listed in `.gitignore` — **never commit credentials**
- `.env` is listed in `.gitignore` — **never commit your `.env` file**
- Use `.env.example` as a template and share only that in the repository

---

## 🛠 Technologies
- Python 3.11 · Streamlit · OpenCV · Pillow · SQLite · Authlib · Google OAuth 2.0
