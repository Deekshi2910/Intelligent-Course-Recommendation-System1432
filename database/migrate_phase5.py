"""
Database Migration Script for Phase 5
Adds is_active column to users table if not already present.
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db_connection import get_db_cursor
from mysql.connector import Error


def run_migration():
    print("Running Phase 5 Database Migration...")
    try:
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            # Check if is_active column exists on users
            cursor.execute("SHOW COLUMNS FROM users LIKE 'is_active'")
            exists = cursor.fetchone()

            if not exists:
                print("Adding is_active column to users table...")
                cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER role")
                print("[SUCCESS] Added is_active column to users table.")
            else:
                print("[INFO] is_active column already exists on users table.")

        return True
    except Error as err:
        print(f"[ERROR] Migration failed [Errno {err.errno}]: {err.msg}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
