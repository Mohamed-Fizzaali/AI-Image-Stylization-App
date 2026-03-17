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


def _ensure_column(cursor: sqlite3.Cursor, table_name: str, column_name: str, ddl: str) -> None:
    """Add a missing column in-place for older local databases."""
    cursor.execute(f"PRAGMA table_info({table_name});")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl};")


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
            profile_picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            failed_attempts INTEGER DEFAULT 0,
            account_locked INTEGER DEFAULT 0
        );
    """)

    _ensure_column(cursor, "Users", "profile_picture", "profile_picture TEXT")
    _ensure_column(cursor, "Users", "full_name", "full_name TEXT")
    _ensure_column(cursor, "Users", "active_plan", "active_plan TEXT DEFAULT 'Starter'")
    _ensure_column(cursor, "Users", "monthly_generations", "monthly_generations INTEGER DEFAULT 0")

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

    _ensure_column(cursor, "Transactions", "razorpay_order_id", "razorpay_order_id TEXT")
    _ensure_column(cursor, "Transactions", "razorpay_payment_id", "razorpay_payment_id TEXT")

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

    _ensure_column(cursor, "ImageHistory", "is_favorite", "is_favorite BOOLEAN DEFAULT 0")

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
