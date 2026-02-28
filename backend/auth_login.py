import bcrypt
from datetime import datetime

from database.db import get_connection

MAX_FAILED_ATTEMPTS = 5
GENERIC_AUTH_FAILURE = "Invalid email/username or password."


def normalize_identifier(identifier: str) -> str:
    return (identifier or "").strip()


def login_user(identifier: str, password: str):
    """
    Authenticate user using email OR username.
    Handles:
    - Account lockout (5 attempts)
    - Inactive accounts
    - Failed attempt tracking
    - last_login update
    """
    identifier_clean = normalize_identifier(identifier)

    if not identifier_clean or not password:
        return {"success": False, "message": "All fields are required."}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Avoid ambiguous OR lookups that can match different accounts.
            if "@" in identifier_clean:
                cursor.execute(
                    """
                    SELECT user_id, username, email, password_hash,
                           failed_attempts, account_locked, is_active
                    FROM Users
                    WHERE LOWER(email) = LOWER(?)
                    LIMIT 1
                    """,
                    (identifier_clean,),
                )
                user = cursor.fetchone()
                if not user:
                    # Backward compatibility for legacy usernames containing '@'.
                    cursor.execute(
                        """
                        SELECT user_id, username, email, password_hash,
                               failed_attempts, account_locked, is_active
                        FROM Users
                        WHERE username = ?
                        LIMIT 1
                        """,
                        (identifier_clean,),
                    )
                    user = cursor.fetchone()
            else:
                cursor.execute(
                    """
                    SELECT user_id, username, email, password_hash,
                           failed_attempts, account_locked, is_active
                    FROM Users
                    WHERE username = ?
                    LIMIT 1
                    """,
                    (identifier_clean,),
                )
                user = cursor.fetchone()

            if not user:
                return {"success": False, "message": GENERIC_AUTH_FAILURE}

            user_id, username, email, password_hash, failed_attempts, account_locked, is_active = user

            if not is_active or account_locked:
                return {"success": False, "message": GENERIC_AUTH_FAILURE}

            if bcrypt.checkpw(password.encode(), password_hash.encode()):
                cursor.execute(
                    """
                    UPDATE Users
                    SET failed_attempts = 0,
                        last_login = ?
                    WHERE user_id = ?
                    """,
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id),
                )
                conn.commit()

                return {
                    "success": True,
                    "message": "Login successful.",
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                }

            failed_attempts += 1

            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                cursor.execute(
                    """
                    UPDATE Users
                    SET failed_attempts = ?,
                        account_locked = 1
                    WHERE user_id = ?
                    """,
                    (failed_attempts, user_id),
                )
                conn.commit()
                return {"success": False, "message": GENERIC_AUTH_FAILURE}

            cursor.execute(
                """
                UPDATE Users
                SET failed_attempts = ?
                WHERE user_id = ?
                """,
                (failed_attempts, user_id),
            )
            conn.commit()
            return {"success": False, "message": GENERIC_AUTH_FAILURE}

    except Exception:
        # Do not expose internal error details.
        return {"success": False, "message": "Authentication error. Please try again later."}
