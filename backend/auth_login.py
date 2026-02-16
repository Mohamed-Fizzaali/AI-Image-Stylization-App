import bcrypt
from datetime import datetime
from database.db import get_connection

MAX_FAILED_ATTEMPTS = 5


def login_user(identifier: str, password: str):
    """
    Authenticate user using email OR username.
    Handles:
    - Account lockout (5 attempts)
    - Inactive accounts
    - Failed attempt tracking
    - last_login update
    """

    if not identifier or not password:
        return {"success": False, "message": "All fields are required."}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id, username, email, password_hash,
                       failed_attempts, account_locked, is_active
                FROM Users
                WHERE email = ? OR username = ?
            """, (identifier, identifier))

            user = cursor.fetchone()

            # 🔐 Do NOT reveal if user exists or not
            if not user:
                return {"success": False, "message": "Invalid credentials."}

            user_id, username, email, password_hash, failed_attempts, account_locked, is_active = user

            # Inactive account
            if not is_active:
                return {"success": False, "message": "Account is inactive. Contact support."}

            # Locked account
            if account_locked:
                return {"success": False, "message": "Account locked due to multiple failed attempts."}

            # Verify password
            if bcrypt.checkpw(password.encode(), password_hash.encode()):

                cursor.execute("""
                    UPDATE Users
                    SET failed_attempts = 0,
                        last_login = ?
                    WHERE user_id = ?
                """, (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    user_id
                ))

                conn.commit()

                return {
                    "success": True,
                    "message": "Login successful.",
                    "user_id": user_id,
                    "username": username,
                    "email": email
                }

            else:
                failed_attempts += 1

                if failed_attempts >= MAX_FAILED_ATTEMPTS:
                    cursor.execute("""
                        UPDATE Users
                        SET failed_attempts = ?,
                            account_locked = 1
                        WHERE user_id = ?
                    """, (failed_attempts, user_id))

                    conn.commit()

                    return {
                        "success": False,
                        "message": "Account locked due to multiple failed attempts."
                    }

                else:
                    cursor.execute("""
                        UPDATE Users
                        SET failed_attempts = ?
                        WHERE user_id = ?
                    """, (failed_attempts, user_id))

                    conn.commit()

                    remaining = MAX_FAILED_ATTEMPTS - failed_attempts

                    return {
                        "success": False,
                        "message": f"Invalid credentials. {remaining} attempt(s) remaining."
                    }

    except Exception:
        # Do not expose internal error details
        return {"success": False, "message": "Authentication error. Please try again later."}
