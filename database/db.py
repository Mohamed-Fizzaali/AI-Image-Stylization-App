import sqlite3
from pathlib import Path

# =========================
# DATABASE CONFIGURATION
# =========================

BASE_DIR = Path(__file__).parent.parent
DB_PATH = Path(__file__).parent / "app_database.db"
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"


# =========================
# CONNECTION HANDLING
# =========================

def get_connection():
    """
    Creates and returns a SQLite connection with
    foreign key enforcement enabled.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# =========================
# STORAGE INITIALIZATION
# =========================

def initialize_storage():
    """
    Ensures upload directory exists.
    Prevents runtime errors when saving images.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# TABLE CREATION
# =========================

def create_tables():
    """
    Creates all required database tables,
    constraints, and indexes.
    Safe to run multiple times.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------
    # USERS TABLE
    # -------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            failed_attempts INTEGER DEFAULT 0,
            account_locked INTEGER DEFAULT 0
        );
    """)

    # -------------------------
    # TRANSACTIONS TABLE
    # -------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_status TEXT NOT NULL 
                CHECK(payment_status IN ('Pending', 'Completed', 'Failed')),
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT NOT NULL,
            FOREIGN KEY(user_id) 
                REFERENCES Users(user_id) 
                ON DELETE CASCADE
        );
    """)

    # -------------------------
    # IMAGE HISTORY TABLE
    # -------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ImageHistory (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_image_path TEXT NOT NULL,
            processed_image_path TEXT NOT NULL,
            style_applied TEXT NOT NULL,
            processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) 
                REFERENCES Users(user_id) 
                ON DELETE CASCADE
        );
    """)

    # -------------------------
    # INDEXES (Performance)
    # -------------------------
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON Users(email);")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON Users(username);")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_user 
        ON Transactions(user_id);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_date 
        ON Transactions(transaction_date);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_imagehistory_user 
        ON ImageHistory(user_id);
    """)

    conn.commit()
    conn.close()

    # Ensure storage folder exists
    initialize_storage()
