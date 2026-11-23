"""
Intelligent Course Recommendation System - Flask Application Entry Point
Phase 3: Complete Student and Admin Authentication System
"""

import os
from datetime import timedelta
import click
from flask import Flask, jsonify, render_template
from flask_wtf.csrf import CSRFProtect
from config import config_by_name

# Determine environment and load configuration
env_name = (
    os.getenv("FLASK_ENV")
    or os.getenv("ENVIRONMENT")
    or ("production" if os.getenv("RENDER") else "development")
).lower()
config_class = config_by_name.get(env_name, config_by_name["default"])

# Initialize Flask with explicit templates and static folder paths
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
app.config.from_object(config_class)
app.permanent_session_lifetime = timedelta(hours=2)

# Enable CSRF Protection
csrf = CSRFProtect(app)

# Register Route Blueprints
from routes import auth_bp, student_bp, admin_bp
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)


# ----------------------------------------------------------------------------
# Global Jinja2 Context Processors
# ----------------------------------------------------------------------------
@app.context_processor
def inject_avatar_helper():
    """Provides a global student_avatar_url helper across all templates."""
    def student_avatar_url(profile_or_gender=None, photo_path=None):
        gender = "Prefer not to say"
        photo = None

        if isinstance(profile_or_gender, dict):
            gender = profile_or_gender.get("gender") or "Prefer not to say"
            photo = profile_or_gender.get("profile_photo")
        elif isinstance(profile_or_gender, str):
            if profile_or_gender in ("Male", "Female", "Prefer not to say"):
                gender = profile_or_gender
            else:
                photo = profile_or_gender
            if photo_path:
                photo = photo_path

        if photo:
            clean_photo = photo.lstrip("/\\")
            full_path = os.path.join(app.root_path, "static", clean_photo)
            if os.path.isfile(full_path):
                from flask import url_for
                return url_for("static", filename=clean_photo)

        from flask import url_for
        if gender == "Male":
            return url_for("static", filename="images/avatars/avatar-male.svg")
        elif gender == "Female":
            return url_for("static", filename="images/avatars/avatar-female.svg")
        else:
            return url_for("static", filename="images/avatars/avatar-neutral.svg")

    return dict(student_avatar_url=student_avatar_url)


@app.route("/", methods=["GET"])
def home():
    """Home route displaying the application title."""
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health_check():
    """Health-check endpoint for system and database verification."""
    from database import test_connection
    db_ok, db_msg = test_connection()
    status_code = 200 if db_ok else 503
    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "service": "Intelligent Course Recommendation System",
        "brand": "CourseRecommender AI",
        "environment": env_name,
        "database": "connected" if db_ok else "disconnected",
        "database_message": db_msg if not db_ok else "Database connection operational"
    }), status_code


# ----------------------------------------------------------------------------
# CLI Command: flask create-admin
# ----------------------------------------------------------------------------
@app.cli.command("create-admin")
@click.option("--username", prompt="Admin username", help="Admin username")
@click.option("--email", prompt="Admin email", help="Admin email address")
@click.password_option(prompt="Admin password", confirmation_prompt=True, help="Admin password (hidden)")
def create_admin_cli(username, email, password):
    """Secure CLI command to create an administrator account."""
    from create_admin import create_admin_user
    try:
        create_admin_user(username, email, password)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)


# ----------------------------------------------------------------------------
# CLI Command: flask reset-admin-password
# ----------------------------------------------------------------------------
@app.cli.command("reset-admin-password")
@click.option("--identifier", prompt="Admin username or email", help="Admin username or email")
@click.password_option(prompt="New admin password", confirmation_prompt=True, help="New admin password (hidden)")
def reset_admin_password_cli(identifier, password):
    """Secure CLI command to reset an administrator account password."""
    from create_admin import reset_admin_password
    try:
        reset_admin_password(identifier, password)
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    debug = app.config.get("DEBUG", False)
    app.run(host=host, port=port, debug=debug)
