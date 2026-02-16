from backend.auth import register_user
from database.db import create_tables

create_tables()

# Valid registration
print(register_user("JohnDoe", "john@example.com", "StrongPass1!"))

# Weak password
print(register_user("User2", "user2@example.com", "weak"))

# Invalid email
print(register_user("User3", "invalidemail", "StrongPass1!"))

# Duplicate user
print(register_user("JohnDoe", "john@example.com", "StrongPass1!"))

