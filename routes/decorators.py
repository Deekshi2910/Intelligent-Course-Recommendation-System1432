"""
Authentication and Role-Based Authorization Decorators
Provides reusable decorators for route protection and access control.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request, make_response


def login_required(f):
    """
    Requires the user to have an active authenticated session.
    Redirects unauthenticated users to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access this page.", "warning")
            # If attempting to access an admin route, redirect to admin login
            if request.path.startswith("/admin"):
                return redirect(url_for("admin.login", next=request.path))
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """
    Requires the authenticated user to hold one of the specified roles.
    Rejects unauthorized roles with a descriptive flash warning.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please sign in to access this page.", "warning")
                if "admin" in allowed_roles:
                    return redirect(url_for("admin.login", next=request.path))
                return redirect(url_for("auth.login", next=request.path))

            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash(f"Unauthorized access. You do not have permission to view this resource.", "danger")
                if user_role == "admin":
                    return redirect(url_for("admin.dashboard"))
                return redirect(url_for("student.dashboard"))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def student_required(f):
    """Convenience decorator for student-only views."""
    return role_required("student")(f)


def admin_required(f):
    """Convenience decorator for administrator-only views."""
    return role_required("admin")(f)


def no_cache(f):
    """
    Ensures protected pages are never cached by browsers or intermediate proxies.
    Prevents logged-out users from viewing sensitive dashboard information via the 'Back' button.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return decorated_function
