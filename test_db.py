import sqlite3
from database.db import DB_PATH, create_tables

create_tables()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(Users)")
print("Users:", [row[1] for row in cursor.fetchall()])

cursor.execute("PRAGMA table_info(ImageHistory)")
print("ImageHistory:", [row[1] for row in cursor.fetchall()])

conn.close()
