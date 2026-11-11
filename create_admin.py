"""
Administrative Account Setup Utility
Intelligent Course Recommendation System
Provides a secure CLI tool to create administrator accounts.
Never hardcodes credentials or exposes plain-text passwords.
"""

import sys
import os
import getpass
import re
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database.db_connection import get_db_cursor
from mysql.connector import Error

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"


def create_admin_user(username, email, password):
    """
    Creates an administrator account in the users table.
    Validates inputs and stores hashed credentials.
    """
    # Validation
    username = username.strip()
    email = email.strip().lower()

    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")

    if not re.match(EMAIL_REGEX, email):
        raise ValueError("Invalid email format.")

    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    pw_hash = generate_password_hash(password)

    try:
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            # Check for collision
            cursor.execute("SELECT id, role FROM users WHERE username = %s OR email = %s", (username, email))
            existing = cursor.fetchone()
            if existing:
                raise ValueError(f"An account with this username or email already exists (Role: {existing['role']}).")

            # Insert admin
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'admin')
            """, (username, email, pw_hash))
            admin_id = cursor.lastrowid

            print(f"[SUCCESS] Admin account created successfully! (User ID: {admin_id}, Username: {username})")
            return admin_id
    except Error as err:
        print(f"[ERROR] Database error during admin creation: {err.msg}")
        raise


def reset_admin_password(identifier, new_password):
    """
    Resets the password for an existing administrator account.
    Validates the account existence and updates the hashed password.
    """
    identifier = identifier.strip()
    if not identifier:
        raise ValueError("Admin identifier (username or email) is required.")

    if not new_password or len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters long.")

    pw_hash = generate_password_hash(new_password)

    try:
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT id, username, email, role FROM users
                WHERE (LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s)) AND role = 'admin'
            """, (identifier, identifier))
            admin = cursor.fetchone()

            if not admin:
                raise ValueError(f"No administrator account found matching identifier '{identifier}'.")

            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (pw_hash, admin["id"]))
            print(f"[SUCCESS] Password for administrator '{admin['username']}' ({admin['email']}) successfully reset!")
            return True
    except Error as err:
        print(f"[ERROR] Database error during password reset: {err.msg}")
        raise


def interactive_cli():
    """Interactively prompts the user for admin credentials securely without echoing."""
    is_reset_mode = len(sys.argv) > 1 and sys.argv[1] in ("--reset", "-r")

    print("=" * 60)
    print("Administrator Password Reset CLI" if is_reset_mode else "Administrator Account Creation CLI")
    print("Intelligent Course Recommendation System")
    print("=" * 60)

    try:
        if is_reset_mode:
            identifier = input("Enter admin username or email: ").strip()
            password = getpass.getpass("Enter new admin password (hidden): ")
            confirm_password = getpass.getpass("Confirm new admin password (hidden): ")

            if password != confirm_password:
                print("[ERROR] Passwords do not match. Aborting.")
                sys.exit(1)

            reset_admin_password(identifier, password)
        else:
            username = input("Enter admin username: ").strip()
            email = input("Enter admin email: ").strip()
            password = getpass.getpass("Enter admin password (hidden): ")
            confirm_password = getpass.getpass("Confirm admin password (hidden): ")

            if password != confirm_password:
                print("[ERROR] Passwords do not match. Aborting.")
                sys.exit(1)

            create_admin_user(username, email, password)
    except KeyboardInterrupt:
        print("\n[INFO] Operation cancelled by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] {str(exc)}")
        sys.exit(1)


if __name__ == "__main__":
    interactive_cli()
