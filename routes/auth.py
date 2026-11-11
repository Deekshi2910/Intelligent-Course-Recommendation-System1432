"""
Authentication Routes
Handles student registration, student login, and session logout.
Enforces input validation, password hashing, and role security.
"""

import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db_connection import get_db_cursor
from routes.decorators import no_cache

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"
USERNAME_REGEX = r"^[a-zA-Z0-9_]{3,30}$"


@auth_bp.route("/login", methods=["GET", "POST"])
@no_cache
def login():
    """Renders student login page and handles credential verification."""
    # If already logged in, redirect to respective dashboard
    if session.get("user_id"):
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        identifier = (
            request.form.get("identifier", "").strip()
            or request.form.get("username_or_email", "").strip()
            or request.form.get("email", "").strip()
            or request.form.get("username", "").strip()
        )
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Please enter both your email/username and password.", "danger")
            return render_template("login.html")

        try:
            with get_db_cursor(dictionary=True) as (cursor, _):
                # Search by username or email
                cursor.execute("""
                    SELECT id, username, email, password_hash, role, is_active
                    FROM users
                    WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s)
                """, (identifier, identifier))
                user = cursor.fetchone()

                if not user or not check_password_hash(user["password_hash"], password):
                    flash("Invalid email/username or password.", "danger")
                    return render_template("login.html")

                # Check account active status
                if user.get("is_active") is not None and not user["is_active"]:
                    flash("Your student account has been deactivated. Please contact an administrator.", "danger")
                    return render_template("login.html")

                # Block admin accounts from logging into student portal
                if user["role"] == "admin":
                    flash("Administrator account detected. Please use the Admin Login portal.", "info")
                    return redirect(url_for("admin.login"))

                # Create secure student session
                session.clear()
                session.permanent = True
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["email"] = user["email"]
                session["role"] = user["role"]

                flash(f"Welcome back, {user['username']}!", "success")
                next_page = request.args.get("next")
                if next_page and next_page.startswith("/"):
                    return redirect(next_page)
                return redirect(url_for("student.dashboard"))
        except Exception as exc:
            flash("A database error occurred during sign in. Please try again.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
@no_cache
def register():
    """Renders student registration page and creates account with student profile."""
    # If already logged in, redirect
    if session.get("user_id"):
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Optional academic fields from form or sensible defaults
        roll_number = request.form.get("roll_number", "").strip()
        department = request.form.get("department", "").strip() or "Computer Science"
        semester = request.form.get("semester", type=int) or 1
        cgpa = request.form.get("cgpa", type=float)
        if cgpa is None:
            cgpa = 0.00

        # Input Validation
        if not full_name or len(full_name) < 2:
            flash("Full name must be at least 2 characters long.", "danger")
            return render_template("register.html")

        if not username or not re.match(USERNAME_REGEX, username):
            flash("Username must be 3-30 characters long and contain only letters, numbers, and underscores.", "danger")
            return render_template("register.html")

        if not email or not re.match(EMAIL_REGEX, email):
            flash("Please provide a valid email address.", "danger")
            return render_template("register.html")

        if not password or len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if semester < 1 or semester > 12:
            flash("Semester must be between 1 and 12.", "danger")
            return render_template("register.html")

        if cgpa < 0.0 or cgpa > 4.0:
            flash("CGPA must be between 0.00 and 4.00.", "danger")
            return render_template("register.html")

        try:
            with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
                # 1. Uniqueness check for username
                cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s)", (username,))
                if cursor.fetchone():
                    flash("Username is already taken. Please choose another.", "warning")
                    return render_template("register.html")

                # 2. Uniqueness check for email
                cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
                if cursor.fetchone():
                    flash("Email is already registered. Please sign in or use another email.", "warning")
                    return render_template("register.html")

                # 3. Insert into users table - explicitly enforcing role='student'
                pw_hash = generate_password_hash(password)
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, 'student')
                """, (username, email, pw_hash))
                user_id = cursor.lastrowid

                # Generate roll_number if not provided
                if not roll_number:
                    roll_number = f"STU-{user_id:04d}"

                # Ensure roll_number uniqueness
                cursor.execute("SELECT id FROM student_profiles WHERE roll_number = %s", (roll_number,))
                if cursor.fetchone():
                    roll_number = f"STU-{user_id:04d}-{username[:4].upper()}"

                # 4. Insert into student_profiles table
                cursor.execute("""
                    INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, full_name, roll_number, department, semester, cgpa))

            flash("Registration successful! You can now sign in with your credentials.", "success")
            return redirect(url_for("auth.login"))
        except Exception as exc:
            flash(f"Registration failed due to a database error. Please try again.", "danger")

    return render_template("register.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
@no_cache
def logout():
    """Clears user session completely and redirects to login."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))
