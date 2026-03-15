import os
import json
import secrets
from pathlib import Path
from urllib.parse import urlencode
from authlib.integrations.requests_client import OAuth2Session

from backend.auth import hash_password
from database.db import get_connection
from datetime import datetime


REDIRECT_URI = "http://localhost:8501"

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def load_google_credentials() -> dict:
    """
    Loads Google OAuth credentials using one of two strategies (in order):
      1. backend/auth/google_credentials.json  (downloaded from Google Cloud Console)
      2. Environment variables: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (.env file)

    Neither the JSON file nor the .env file should ever be committed to the repository.
    See .env.example for a template.
    """
    # ── Strategy 1: JSON file ─────────────────────────────────────────────────
    # Search in common locations: backend/auth/ and root auth/
    possible_paths = [
        Path(__file__).resolve().parent / "auth" / "google_credentials.json",
        Path(__file__).resolve().parent.parent / "auth" / "google_credentials.json",
        Path.cwd() / "auth" / "google_credentials.json",
        Path.cwd() / "backend" / "auth" / "google_credentials.json"
    ]

    for creds_path in possible_paths:
        if creds_path.exists():
            with open(creds_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Google's downloaded JSON nests values under "web" or "installed"
            creds = data.get("web") or data.get("installed")
            if creds and creds.get("client_id") and creds.get("client_secret"):
                return creds
            
    # If file was found but invalid, or not found at all, we proceed to env vars

    # ── Strategy 2: Environment variables (.env or system env) ────────────────
    from dotenv import load_dotenv
    load_dotenv()

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if client_id and client_secret:
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": AUTHORIZE_URL,
            "token_uri": TOKEN_URL,
        }

    # ── Neither strategy worked ───────────────────────────────────────────────
    raise FileNotFoundError(
        "\n\n"
        "⚠️  Google OAuth credentials not found.\n\n"
        "Choose ONE of the following options:\n\n"
        "  Option A — JSON file (recommended):\n"
        "    1. Go to https://console.cloud.google.com → APIs & Services → Credentials\n"
        "    2. Download your OAuth 2.0 Client JSON\n"
        "    3. Save it to:  backend/auth/google_credentials.json\n\n"
        "  Option B — Environment variables:\n"
        "    1. Copy .env.example  →  .env\n"
        "    2. Fill in GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET\n\n"
        "⚠️  DO NOT commit either file to the repository.\n"
    )


def get_google_auth_url(redirect_uri: str) -> tuple[str, str]:
    """
    Generates the Google OAuth 2.0 authorization URL and state.
    """
    creds = load_google_credentials()
    
    # Create an OAuth2 session using authlib
    session = OAuth2Session(
        client_id=creds.get("client_id"),
        client_secret=creds.get("client_secret"),
        scope="openid email profile",
        redirect_uri=redirect_uri
    )
    
    # Use standard URIs from the file if they exist, fallback to hardcoded
    auth_uri = creds.get("auth_uri", AUTHORIZE_URL)
    
    uri, state = session.create_authorization_url(auth_uri)
    return uri, state


def process_google_callback(auth_code: str, state: str, redirect_uri: str) -> dict:
    """
    Exchanges the authorization code for an access token,
    retrieves the user's profile info from Google,
    and returns a standardized user dictionary.
    """
    try:
        creds = load_google_credentials()
        
        # Pass the state to the session for verification
        session = OAuth2Session(
            client_id=creds.get("client_id"),
            client_secret=creds.get("client_secret"),
            redirect_uri=redirect_uri,
            state=state
        )

        # 1. Exchange auth_code for token
        token_uri = creds.get("token_uri", TOKEN_URL)
        
        # Build the authorization response URL for internal verification
        authorization_response = f"{redirect_uri}?code={auth_code}&state={state}"
        
        token = session.fetch_token(
            token_uri,
            authorization_response=authorization_response,
            grant_type="authorization_code"
        )

        # 2. Use access token to fetch user info
        resp = session.get(USERINFO_URL)
        resp.raise_for_status()
        user_info = resp.json()

        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")
        
        if not email:
            return {"success": False, "message": "Google did not return an email address."}

        # 3. Handle database logic
        with get_connection() as conn:
            cursor = conn.cursor()

            # Check if user already exists
            cursor.execute(
                "SELECT user_id, username, email, account_locked, is_active FROM Users WHERE LOWER(email) = LOWER(?) LIMIT 1",
                (email,)
            )
            existing_user = cursor.fetchone()

            if existing_user:
                user_id, username, db_email, account_locked, is_active = existing_user

                if not is_active or account_locked:
                    return {"success": False, "message": "Account is locked or inactive."}

                # Update login timestamp & reset failures
                cursor.execute(
                    "UPDATE Users SET failed_attempts = 0, last_login = ?, profile_picture = ? WHERE user_id = ?",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), picture, user_id)
                )
                conn.commit()

                return {
                    "success": True,
                    "message": "Login successful.",
                    "user_id": user_id,
                    "username": username,
                    "email": db_email,
                    "profile_picture": picture
                }

            # User doesn't exist -> Create new account
            else:
                # Generate a secure random password since they used Google Auth
                random_password = secrets.token_urlsafe(20)
                password_hash = hash_password(random_password)

                # Use their Google name or fallback to a split of their email
                username = name if name else email.split("@")[0]

                # Ensure username is unique
                cursor.execute("SELECT 1 FROM Users WHERE username = ?", (username,))
                if cursor.fetchone():
                    # Handle duplicate usernames by appending random hex string
                    username = f"{username}_{secrets.token_hex(4)}"

                cursor.execute("""
                    INSERT INTO Users (username, email, password_hash, profile_picture, last_login)
                    VALUES (?, ?, ?, ?, ?)
                """, (username, email.lower(), password_hash, picture, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                
                # Fetch the new generated user_id
                cursor.execute("SELECT user_id FROM Users WHERE email = ?", (email.lower(),))
                new_user_id = cursor.fetchone()[0]

                return {
                    "success": True,
                    "message": "Account created and logged in via Google.",
                    "user_id": new_user_id,
                    "username": username,
                    "email": email.lower(),
                    "profile_picture": picture
                }

    except Exception as e:
        print(f"OAuth Error: {e}")
        return {"success": False, "message": "Google authentication failed."}
