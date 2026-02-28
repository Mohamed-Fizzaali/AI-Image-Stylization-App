import re
import bcrypt
import sqlite3
from database.db import get_connection

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,32}$")


# =========================
# EMAIL VALIDATION
# =========================

def is_valid_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None


def is_valid_username(username: str) -> bool:
    return USERNAME_PATTERN.match(username) is not None


def normalize_username(username: str) -> str:
    return (username or "").strip()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


# =========================
# PASSWORD STRENGTH CHECK
# =========================

def is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True


# =========================
# PASSWORD HASHING
# =========================

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


# =========================
# USER REGISTRATION
# =========================

def register_user(username: str, email: str, password: str) -> dict:
    """
    Registers a new user with validation,
    secure password hashing, and atomic database insertion.
    """

    username_clean = normalize_username(username)
    email_clean = normalize_email(email)

    # Input validation
    if not username_clean or not email_clean or not password:
        return {"success": False, "message": "All fields are required."}

    if "@" in username_clean:
        return {"success": False, "message": "Username cannot contain @."}

    if not is_valid_username(username_clean):
        return {
            "success": False,
            "message": "Username must be 3-32 characters and can contain letters, numbers, dot, underscore, or hyphen.",
        }

    if not is_valid_email(email_clean):
        return {"success": False, "message": "Invalid email format."}

    if not is_strong_password(password):
        return {
            "success": False,
            "message": "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character."
        }

    try:
        password_hash = hash_password(password)

        # Atomic insert using UNIQUE constraint enforcement
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Users (username, email, password_hash)
                VALUES (?, ?, ?)
            """, (username_clean, email_clean, password_hash))

        return {"success": True, "message": "User registered successfully."}

    except sqlite3.IntegrityError:
        # Catches UNIQUE constraint violation
        return {"success": False, "message": "Username or email already exists."}

    except Exception:
        return {"success": False, "message": "Unable to register right now. Please try again later."}
