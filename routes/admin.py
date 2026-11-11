"""
Admin Routes Module
Handles administrator authentication, system dashboard, student management,
course management (CRUD), domain interests, career goals, knowledge base ontologies,
AI knowledge rules (structured JSON), recommendation analytics reports, and admin profile security.

Strictly protected by @admin_required and @no_cache decorators.
Zero eval() / exec() usage.
"""

import json
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from werkzeug.security import check_password_hash, generate_password_hash
from database.db_connection import get_db_cursor
from routes.decorators import admin_required, no_cache
from ai_engine.rule_manager import RuleManager
from ai_engine.default_rules import DefaultRuleManager

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ============================================================================
# 1. Administrator Authentication
# ============================================================================

@admin_bp.route("/login", methods=["GET", "POST"])
@no_cache
def login():
    """Renders separate administrator login page and authenticates admin credentials."""
    if session.get("user_id") and session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        identifier = (
            request.form.get("identifier", "").strip()
            or request.form.get("username_or_email", "").strip()
            or request.form.get("email", "").strip()
            or request.form.get("username", "").strip()
        )
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Please enter both administrator identifier and password.", "danger")
            return render_template("admin_login.html")

        try:
            with get_db_cursor(dictionary=True) as (cursor, _):
                cursor.execute("""
                    SELECT id, username, email, password_hash, role, is_active
                    FROM users
                    WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s)
                """, (identifier, identifier))
                user = cursor.fetchone()

                if not user or not check_password_hash(user["password_hash"], password):
                    flash("Invalid administrator credentials.", "danger")
                    return render_template("admin_login.html")

                if user["role"] != "admin":
                    flash("Access denied. This account does not possess administrator privileges.", "danger")
                    return render_template("admin_login.html")

                if not user.get("is_active", True):
                    flash("This administrator account has been deactivated. Please contact root.", "danger")
                    return render_template("admin_login.html")

                # Establish administrator session
                session.clear()
                session.permanent = True
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["email"] = user["email"]
                session["role"] = "admin"

                flash(f"Welcome, Administrator {user['username']}.", "success")
                next_page = request.args.get("next")
                if next_page and next_page.startswith("/admin"):
                    return redirect(next_page)
                return redirect(url_for("admin.dashboard"))
        except Exception as exc:
            flash(f"Database error during administrator login: {exc}", "danger")

    return render_template("admin_login.html")


# ============================================================================
# 2. Administrator Overview Dashboard
# ============================================================================

@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
@no_cache
def dashboard():
    """Displays administrative metrics, active courses, and recent student activity."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            # Aggregated statistics
            cursor.execute("SELECT COUNT(*) AS total_students FROM student_profiles")
            total_students = cursor.fetchone()["total_students"]

            cursor.execute("SELECT COUNT(*) AS total_courses FROM courses WHERE is_active = TRUE")
            total_courses = cursor.fetchone()["total_courses"]

            cursor.execute("SELECT COUNT(*) AS total_interests FROM interests")
            total_interests = cursor.fetchone()["total_interests"]

            cursor.execute("SELECT COUNT(*) AS total_goals FROM career_goals")
            total_goals = cursor.fetchone()["total_goals"]

            cursor.execute("SELECT COUNT(*) AS total_rules FROM knowledge_rules WHERE is_active = TRUE")
            total_rules = cursor.fetchone()["total_rules"]

            cursor.execute("SELECT COUNT(*) AS total_recommendations FROM recommendation_history")
            total_recommendations = cursor.fetchone()["total_recommendations"]

            # Recent student registrations
            cursor.execute("""
                SELECT sp.id, sp.user_id, sp.full_name, sp.roll_number, sp.department,
                       sp.semester, sp.cgpa, u.is_active, u.created_at
                FROM student_profiles sp
                JOIN users u ON sp.user_id = u.id
                ORDER BY u.created_at DESC, sp.id DESC
                LIMIT 5
            """)
            recent_students = cursor.fetchall()

            # Course list summary
            cursor.execute("""
                SELECT c.*, GROUP_CONCAT(i.interest_name SEPARATOR ', ') AS tags
                FROM courses c
                LEFT JOIN course_interests ci ON c.id = ci.course_id
                LEFT JOIN interests i ON ci.interest_id = i.id
                GROUP BY c.id
                ORDER BY c.course_code ASC
            """)
            courses = cursor.fetchall()

            # Knowledge rules summary
            cursor.execute("""
                SELECT kr.*, c.course_code, c.course_name
                FROM knowledge_rules kr
                JOIN courses c ON kr.recommended_course_id = c.id
                ORDER BY kr.priority DESC
            """)
            rules = cursor.fetchall()

        return render_template(
            "admin_dashboard.html",
            total_students=total_students,
            total_courses=total_courses,
            total_interests=total_interests,
            total_goals=total_goals,
            total_rules=total_rules,
            total_recommendations=total_recommendations,
            recent_students=recent_students,
            courses=courses,
            rules=rules
        )
    except Exception as exc:
        flash(f"Failed to load administrator dashboard data: {exc}", "danger")
        return render_template(
            "admin_dashboard.html",
            total_students=0,
            total_courses=0,
            total_interests=0,
            total_goals=0,
            total_rules=0,
            total_recommendations=0,
            recent_students=[],
            courses=[],
            rules=[]
        )


# ============================================================================
# 3. Student Management
# ============================================================================

@admin_bp.route("/students", methods=["GET"])
@admin_required
@no_cache
def students():
    """Lists registered students with search by query (q) and department/semester filters."""
    search_query = request.args.get("q", "").strip()
    selected_dept = request.args.get("dept", "").strip()
    selected_sem = request.args.get("sem", "").strip()

    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            # Fetch distinct departments for filter dropdown
            cursor.execute("SELECT DISTINCT department FROM student_profiles WHERE department IS NOT NULL AND department != '' ORDER BY department ASC")
            departments = [row["department"] for row in cursor.fetchall()]

            # Build dynamic filtered query
            base_query = """
                SELECT sp.id, sp.user_id, sp.full_name, sp.roll_number, sp.department,
                       sp.semester, sp.cgpa, u.username, u.email, u.is_active, u.created_at
                FROM student_profiles sp
                JOIN users u ON sp.user_id = u.id
                WHERE 1=1
            """
            params = []

            if search_query:
                base_query += """
                    AND (
                        LOWER(sp.full_name) LIKE LOWER(%s) OR
                        LOWER(sp.roll_number) LIKE LOWER(%s) OR
                        LOWER(u.email) LIKE LOWER(%s) OR
                        LOWER(u.username) LIKE LOWER(%s)
                    )
                """
                like_pattern = f"%{search_query}%"
                params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

            if selected_dept:
                base_query += " AND sp.department = %s"
                params.append(selected_dept)

            if selected_sem:
                try:
                    sem_num = int(selected_sem)
                    base_query += " AND sp.semester = %s"
                    params.append(sem_num)
                except ValueError:
                    pass

            base_query += " ORDER BY sp.roll_number ASC"
            cursor.execute(base_query, tuple(params))
            student_list = cursor.fetchall()

        return render_template(
            "admin_students.html",
            students=student_list,
            departments=departments,
            search_query=search_query,
            selected_dept=selected_dept,
            selected_sem=selected_sem
        )
    except Exception as exc:
        flash(f"Error retrieving student records: {exc}", "danger")
        return render_template(
            "admin_students.html",
            students=[],
            departments=[],
            search_query=search_query,
            selected_dept=selected_dept,
            selected_sem=selected_sem
        )


@admin_bp.route("/students/<int:student_id>", methods=["GET"])
@admin_required
@no_cache
def student_detail(student_id):
    """Displays detailed dossier for a specific student, including academic profile, interests, and recommendations."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT sp.id, sp.user_id, sp.full_name, sp.roll_number, sp.department,
                       sp.semester, sp.cgpa, u.username, u.email, u.is_active, u.created_at,
                       cg.goal_name, cg.description AS goal_description
                FROM student_profiles sp
                JOIN users u ON sp.user_id = u.id
                LEFT JOIN career_goals cg ON sp.career_goal_id = cg.id
                WHERE sp.id = %s
            """, (student_id,))
            student = cursor.fetchone()

            if not student:
                flash("Student profile not found.", "danger")
                return redirect(url_for("admin.students"))

            # Fetch student's selected interests
            cursor.execute("""
                SELECT i.interest_name
                FROM student_interests si
                JOIN interests i ON si.interest_id = i.id
                WHERE si.student_id = %s
                ORDER BY i.interest_name ASC
            """, (student_id,))
            student_interests = cursor.fetchall()

            # Fetch recommendation history
            cursor.execute("""
                SELECT rh.id, rh.recommendation_score, rh.reasoning, rh.created_at,
                       c.course_code, c.course_name
                FROM recommendation_history rh
                JOIN courses c ON rh.recommended_course_id = c.id
                WHERE rh.student_id = %s
                ORDER BY rh.created_at DESC
            """, (student_id,))
            recommendations = cursor.fetchall()

        return render_template(
            "admin_student_detail.html",
            student=student,
            interests=student_interests,
            recommendation_history=recommendations
        )
    except Exception as exc:
        flash(f"Error fetching student details: {exc}", "danger")
        return redirect(url_for("admin.students"))


@admin_bp.route("/students/<int:student_id>/toggle-status", methods=["POST"])
@admin_required
@no_cache
def student_toggle_status(student_id):
    """Toggles student user account active/deactivated state."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("""
                SELECT sp.user_id, u.is_active, sp.full_name
                FROM student_profiles sp
                JOIN users u ON sp.user_id = u.id
                WHERE sp.id = %s
            """, (student_id,))
            record = cursor.fetchone()

            if not record:
                flash("Student record not found.", "danger")
                return redirect(url_for("admin.students"))

            new_status = not bool(record["is_active"])
            cursor.execute("UPDATE users SET is_active = %s WHERE id = %s", (new_status, record["user_id"]))
            conn.commit()

            status_str = "activated" if new_status else "deactivated"
            flash(f"Student account for {record['full_name']} successfully {status_str}.", "success")
    except Exception as exc:
        flash(f"Failed to update account status: {exc}", "danger")

    # Redirect to referer or student list
    referer = request.referrer
    if referer and "/admin/students" in referer:
        return redirect(referer)
    return redirect(url_for("admin.students"))


# ============================================================================
# 4. Course Management (CRUD)
# ============================================================================

@admin_bp.route("/courses", methods=["GET"])
@admin_required
@no_cache
def courses():
    """Renders the course catalog with associated domain interest tags."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT c.*, GROUP_CONCAT(i.interest_name SEPARATOR ', ') AS tags
                FROM courses c
                LEFT JOIN course_interests ci ON c.id = ci.course_id
                LEFT JOIN interests i ON ci.interest_id = i.id
                GROUP BY c.id
                ORDER BY c.course_code ASC
            """)
            course_list = cursor.fetchall()
        return render_template("admin_courses.html", courses=course_list)
    except Exception as exc:
        flash(f"Error loading course catalog: {exc}", "danger")
        return render_template("admin_courses.html", courses=[])


@admin_bp.route("/courses/add", methods=["GET", "POST"])
@admin_required
@no_cache
def courses_add():
    """Adds a new elective course with mapped domain interests."""
    if request.method == "POST":
        course_code = request.form.get("course_code", "").strip().upper()
        course_name = request.form.get("course_name", "").strip()
        description = request.form.get("description", "").strip()
        min_cgpa_raw = request.form.get("minimum_cgpa", "2.00").strip()
        difficulty_level = request.form.get("difficulty_level", "Intermediate").strip()
        prerequisites = request.form.get("prerequisites", "").strip()
        career_scope = request.form.get("career_scope", "").strip()
        is_active = bool(request.form.get("is_active"))
        selected_interest_ids = request.form.getlist("interest_ids")

        if not course_code or not course_name or not description:
            flash("Course Code, Course Name, and Description are mandatory.", "danger")
            return redirect(url_for("admin.courses_add"))

        try:
            min_cgpa = float(min_cgpa_raw)
            if not (0.0 <= min_cgpa <= 4.0):
                raise ValueError()
        except ValueError:
            flash("Minimum CGPA must be a valid number between 0.00 and 4.00.", "danger")
            return redirect(url_for("admin.courses_add"))

        if difficulty_level not in ["Beginner", "Intermediate", "Advanced"]:
            difficulty_level = "Intermediate"

        try:
            with get_db_cursor(dictionary=True) as (cursor, conn):
                # Verify unique course_code
                cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course_code,))
                if cursor.fetchone():
                    flash(f"Course code '{course_code}' already exists.", "danger")
                    return redirect(url_for("admin.courses_add"))

                # Insert course
                cursor.execute("""
                    INSERT INTO courses (course_code, course_name, description, minimum_cgpa, difficulty_level, career_scope, prerequisites, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (course_code, course_name, description, min_cgpa, difficulty_level, career_scope, prerequisites, is_active))
                new_course_id = cursor.lastrowid

                # Link selected domain interests
                for int_id in selected_interest_ids:
                    try:
                        cursor.execute("""
                            INSERT INTO course_interests (course_id, interest_id)
                            VALUES (%s, %s)
                        """, (new_course_id, int(int_id)))
                    except Exception:
                        pass

                # Link selected career goals
                selected_career_goal_ids = request.form.getlist("career_goal_ids")
                for goal_id in selected_career_goal_ids:
                    try:
                        cursor.execute("""
                            INSERT INTO course_career_goals (course_id, career_goal_id)
                            VALUES (%s, %s)
                        """, (new_course_id, int(goal_id)))
                    except Exception:
                        pass

                # Link selected prerequisite courses
                selected_prereq_ids = request.form.getlist("prerequisite_course_ids")
                for prereq_id in selected_prereq_ids:
                    try:
                        p_id = int(prereq_id)
                        if p_id != new_course_id:
                            cursor.execute("""
                                INSERT INTO course_prerequisites (course_id, prerequisite_course_id)
                                VALUES (%s, %s)
                            """, (new_course_id, p_id))
                    except Exception:
                        pass

                conn.commit()
                flash(f"Course '{course_code} - {course_name}' created successfully.", "success")
                return redirect(url_for("admin.courses"))
        except Exception as exc:
            flash(f"Database error creating course: {exc}", "danger")
            return redirect(url_for("admin.courses_add"))

    # GET request
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, interest_name FROM interests ORDER BY interest_name ASC")
            all_interests = cursor.fetchall()

            cursor.execute("SELECT id, goal_name FROM career_goals ORDER BY goal_name ASC")
            all_career_goals = cursor.fetchall()

            cursor.execute("SELECT id, course_code, course_name FROM courses ORDER BY course_code ASC")
            all_other_courses = cursor.fetchall()

        return render_template(
            "admin_course_form.html",
            course=None,
            all_interests=all_interests,
            selected_interest_ids=[],
            all_career_goals=all_career_goals,
            selected_career_goal_ids=[],
            all_other_courses=all_other_courses,
            selected_prereq_ids=[]
        )
    except Exception as exc:
        flash(f"Failed to load course creation form: {exc}", "danger")
        return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@admin_required
@no_cache
def courses_edit(course_id):
    """Edits an existing elective course and synchronizes domain interests, career goals, and prerequisites."""
    if request.method == "POST":
        course_code = request.form.get("course_code", "").strip().upper()
        course_name = request.form.get("course_name", "").strip()
        description = request.form.get("description", "").strip()
        min_cgpa_raw = request.form.get("minimum_cgpa", "2.00").strip()
        difficulty_level = request.form.get("difficulty_level", "Intermediate").strip()
        prerequisites = request.form.get("prerequisites", "").strip()
        career_scope = request.form.get("career_scope", "").strip()
        is_active = bool(request.form.get("is_active"))
        selected_interest_ids = request.form.getlist("interest_ids")
        selected_career_goal_ids = request.form.getlist("career_goal_ids")
        selected_prereq_ids = request.form.getlist("prerequisite_course_ids")

        if not course_code or not course_name or not description:
            flash("Course Code, Course Name, and Description are mandatory.", "danger")
            return redirect(url_for("admin.courses_edit", course_id=course_id))

        try:
            min_cgpa = float(min_cgpa_raw)
            if not (0.0 <= min_cgpa <= 4.0):
                raise ValueError()
        except ValueError:
            flash("Minimum CGPA must be a valid number between 0.00 and 4.00.", "danger")
            return redirect(url_for("admin.courses_edit", course_id=course_id))

        if difficulty_level not in ["Beginner", "Intermediate", "Advanced"]:
            difficulty_level = "Intermediate"

        try:
            with get_db_cursor(dictionary=True) as (cursor, conn):
                # Verify unique course_code on other courses
                cursor.execute("SELECT id FROM courses WHERE course_code = %s AND id != %s", (course_code, course_id))
                if cursor.fetchone():
                    flash(f"Course code '{course_code}' is already used by another course.", "danger")
                    return redirect(url_for("admin.courses_edit", course_id=course_id))

                # Update course
                cursor.execute("""
                    UPDATE courses
                    SET course_code = %s, course_name = %s, description = %s,
                        minimum_cgpa = %s, difficulty_level = %s, career_scope = %s,
                        prerequisites = %s, is_active = %s
                    WHERE id = %s
                """, (course_code, course_name, description, min_cgpa, difficulty_level, career_scope, prerequisites, is_active, course_id))

                # Sync course interests
                cursor.execute("DELETE FROM course_interests WHERE course_id = %s", (course_id,))
                for int_id in selected_interest_ids:
                    try:
                        cursor.execute("""
                            INSERT INTO course_interests (course_id, interest_id)
                            VALUES (%s, %s)
                        """, (course_id, int(int_id)))
                    except Exception:
                        pass

                # Sync course career goals
                cursor.execute("DELETE FROM course_career_goals WHERE course_id = %s", (course_id,))
                for goal_id in selected_career_goal_ids:
                    try:
                        cursor.execute("""
                            INSERT INTO course_career_goals (course_id, career_goal_id)
                            VALUES (%s, %s)
                        """, (course_id, int(goal_id)))
                    except Exception:
                        pass

                # Sync course prerequisites
                cursor.execute("DELETE FROM course_prerequisites WHERE course_id = %s", (course_id,))
                for prereq_id in selected_prereq_ids:
                    try:
                        p_id = int(prereq_id)
                        if p_id != course_id:
                            cursor.execute("""
                                INSERT INTO course_prerequisites (course_id, prerequisite_course_id)
                                VALUES (%s, %s)
                            """, (course_id, p_id))
                    except Exception:
                        pass

                conn.commit()
                flash(f"Course '{course_code}' updated successfully.", "success")
                return redirect(url_for("admin.courses"))
        except Exception as exc:
            flash(f"Database error updating course: {exc}", "danger")
            return redirect(url_for("admin.courses_edit", course_id=course_id))

    # GET request
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT * FROM courses WHERE id = %s", (course_id,))
            course = cursor.fetchone()
            if not course:
                flash("Course not found.", "danger")
                return redirect(url_for("admin.courses"))

            cursor.execute("SELECT id, interest_name FROM interests ORDER BY interest_name ASC")
            all_interests = cursor.fetchall()

            cursor.execute("SELECT id, goal_name FROM career_goals ORDER BY goal_name ASC")
            all_career_goals = cursor.fetchall()

            cursor.execute("SELECT id, course_code, course_name FROM courses WHERE id != %s ORDER BY course_code ASC", (course_id,))
            all_other_courses = cursor.fetchall()

            cursor.execute("SELECT interest_id FROM course_interests WHERE course_id = %s", (course_id,))
            selected_ids = [row["interest_id"] for row in cursor.fetchall()]

            cursor.execute("SELECT career_goal_id FROM course_career_goals WHERE course_id = %s", (course_id,))
            selected_goal_ids = [row["career_goal_id"] for row in cursor.fetchall()]

            cursor.execute("SELECT prerequisite_course_id FROM course_prerequisites WHERE course_id = %s", (course_id,))
            selected_prereq_ids = [row["prerequisite_course_id"] for row in cursor.fetchall()]

        return render_template(
            "admin_course_form.html",
            course=course,
            all_interests=all_interests,
            selected_interest_ids=selected_ids,
            all_career_goals=all_career_goals,
            selected_career_goal_ids=selected_goal_ids,
            all_other_courses=all_other_courses,
            selected_prereq_ids=selected_prereq_ids
        )
    except Exception as exc:
        flash(f"Failed to load course: {exc}", "danger")
        return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<int:course_id>/toggle-status", methods=["POST"])
@admin_required
@no_cache
def course_toggle_status(course_id):
    """Toggles active status of an elective course."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("SELECT course_code, is_active FROM courses WHERE id = %s", (course_id,))
            c = cursor.fetchone()
            if not c:
                flash("Course not found.", "danger")
                return redirect(url_for("admin.courses"))

            new_status = not bool(c["is_active"])
            cursor.execute("UPDATE courses SET is_active = %s WHERE id = %s", (new_status, course_id))
            conn.commit()

            status_label = "activated" if new_status else "deactivated"
            flash(f"Course {c['course_code']} has been {status_label}.", "success")
    except Exception as exc:
        flash(f"Failed to toggle course status: {exc}", "danger")

    return redirect(url_for("admin.courses"))


@admin_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@admin_required
@no_cache
def course_delete(course_id):
    """
    Deletes course if no recommendation history references it;
    deactivates otherwise to preserve historical audit integrity.
    """
    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("SELECT course_code, course_name FROM courses WHERE id = %s", (course_id,))
            c = cursor.fetchone()
            if not c:
                flash("Course not found.", "danger")
                return redirect(url_for("admin.courses"))

            # Check recommendation history
            cursor.execute("SELECT COUNT(*) AS rec_count FROM recommendation_history WHERE recommended_course_id = %s", (course_id,))
            rec_count = cursor.fetchone()["rec_count"]

            if rec_count > 0:
                # Safe deactivation policy
                cursor.execute("UPDATE courses SET is_active = FALSE WHERE id = %s", (course_id,))
                conn.commit()
                flash(f"Course '{c['course_code']}' has {rec_count} historical recommendations. It was deactivated instead of deleted to protect audit logs.", "warning")
            else:
                cursor.execute("DELETE FROM courses WHERE id = %s", (course_id,))
                conn.commit()
                flash(f"Course '{c['course_code']}' permanently deleted.", "success")
    except Exception as exc:
        flash(f"Error during course deletion: {exc}", "danger")

    return redirect(url_for("admin.courses"))


# ============================================================================
# 5. Domain Interests Management
# ============================================================================

@admin_bp.route("/interests", methods=["GET", "POST"])
@admin_required
@no_cache
def interests():
    """Lists interests with usage counts and allows adding new interests."""
    if request.method == "POST":
        interest_name = request.form.get("interest_name", "").strip()
        if not interest_name:
            flash("Interest name cannot be empty.", "danger")
            return redirect(url_for("admin.interests"))

        try:
            with get_db_cursor(dictionary=True) as (cursor, conn):
                cursor.execute("SELECT id FROM interests WHERE LOWER(interest_name) = LOWER(%s)", (interest_name,))
                if cursor.fetchone():
                    flash(f"Interest '{interest_name}' already exists.", "danger")
                    return redirect(url_for("admin.interests"))

                cursor.execute("INSERT INTO interests (interest_name) VALUES (%s)", (interest_name,))
                conn.commit()
                flash(f"Interest '{interest_name}' added successfully.", "success")
                return redirect(url_for("admin.interests"))
        except Exception as exc:
            flash(f"Database error adding interest: {exc}", "danger")
            return redirect(url_for("admin.interests"))

    # GET request
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT i.id, i.interest_name,
                       COUNT(DISTINCT ci.course_id) AS course_count,
                       COUNT(DISTINCT si.student_id) AS student_count
                FROM interests i
                LEFT JOIN course_interests ci ON i.id = ci.interest_id
                LEFT JOIN student_interests si ON i.id = si.interest_id
                GROUP BY i.id
                ORDER BY i.interest_name ASC
            """)
            interest_list = cursor.fetchall()
        return render_template("admin_interests.html", interests=interest_list)
    except Exception as exc:
        flash(f"Failed to load interests: {exc}", "danger")
        return render_template("admin_interests.html", interests=[])


@admin_bp.route("/interests/<int:interest_id>/edit", methods=["POST"])
@admin_required
@no_cache
def interest_edit(interest_id):
    """Updates the name of an existing interest."""
    new_name = request.form.get("interest_name", "").strip()
    if not new_name:
        flash("Interest name cannot be blank.", "danger")
        return redirect(url_for("admin.interests"))

    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("SELECT id FROM interests WHERE LOWER(interest_name) = LOWER(%s) AND id != %s", (new_name, interest_id))
            if cursor.fetchone():
                flash(f"Another interest with name '{new_name}' already exists.", "danger")
                return redirect(url_for("admin.interests"))

            cursor.execute("UPDATE interests SET interest_name = %s WHERE id = %s", (new_name, interest_id))
            conn.commit()
            flash("Interest updated successfully.", "success")
    except Exception as exc:
        flash(f"Error updating interest: {exc}", "danger")

    return redirect(url_for("admin.interests"))


@admin_bp.route("/interests/<int:interest_id>/delete", methods=["POST"])
@admin_required
@no_cache
def interest_delete(interest_id):
    """Safely deletes an interest if not used by courses or students."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM course_interests WHERE interest_id = %s) AS c_count,
                    (SELECT COUNT(*) FROM student_interests WHERE interest_id = %s) AS s_count,
                    (SELECT interest_name FROM interests WHERE id = %s) AS interest_name
            """, (interest_id, interest_id, interest_id))
            check = cursor.fetchone()

            if not check or not check["interest_name"]:
                flash("Interest not found.", "danger")
                return redirect(url_for("admin.interests"))

            if check["c_count"] > 0 or check["s_count"] > 0:
                flash(f"Cannot delete interest '{check['interest_name']}' because it is associated with {check['c_count']} courses and {check['s_count']} students.", "danger")
                return redirect(url_for("admin.interests"))

            cursor.execute("DELETE FROM interests WHERE id = %s", (interest_id,))
            conn.commit()
            flash(f"Interest '{check['interest_name']}' deleted.", "success")
    except Exception as exc:
        flash(f"Error deleting interest: {exc}", "danger")

    return redirect(url_for("admin.interests"))


# ============================================================================
# 6. Career Goals Management
# ============================================================================

@admin_bp.route("/career-goals", methods=["GET", "POST"])
@admin_required
@no_cache
def career_goals():
    """Lists career goals with student count and enables creating new career goals."""
    if request.method == "POST":
        goal_name = request.form.get("goal_name", "").strip()
        description = request.form.get("description", "").strip()

        if not goal_name:
            flash("Career goal title is required.", "danger")
            return redirect(url_for("admin.career_goals"))

        try:
            with get_db_cursor(dictionary=True) as (cursor, conn):
                cursor.execute("SELECT id FROM career_goals WHERE LOWER(goal_name) = LOWER(%s)", (goal_name,))
                if cursor.fetchone():
                    flash(f"Career goal '{goal_name}' already exists.", "danger")
                    return redirect(url_for("admin.career_goals"))

                cursor.execute("INSERT INTO career_goals (goal_name, description) VALUES (%s, %s)", (goal_name, description))
                conn.commit()
                flash(f"Career goal '{goal_name}' created successfully.", "success")
                return redirect(url_for("admin.career_goals"))
        except Exception as exc:
            flash(f"Database error creating career goal: {exc}", "danger")
            return redirect(url_for("admin.career_goals"))

    # GET request
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT cg.id, cg.goal_name, cg.description,
                       COUNT(sp.id) AS student_count
                FROM career_goals cg
                LEFT JOIN student_profiles sp ON cg.id = sp.career_goal_id
                GROUP BY cg.id
                ORDER BY cg.goal_name ASC
            """)
            goal_list = cursor.fetchall()
        return render_template("admin_career_goals.html", career_goals=goal_list)
    except Exception as exc:
        flash(f"Failed to load career goals: {exc}", "danger")
        return render_template("admin_career_goals.html", career_goals=[])


@admin_bp.route("/career-goals/<int:goal_id>/edit", methods=["POST"])
@admin_required
@no_cache
def career_goal_edit(goal_id):
    """Updates an existing career goal title and description."""
    goal_name = request.form.get("goal_name", "").strip()
    description = request.form.get("description", "").strip()

    if not goal_name:
        flash("Goal name cannot be empty.", "danger")
        return redirect(url_for("admin.career_goals"))

    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("SELECT id FROM career_goals WHERE LOWER(goal_name) = LOWER(%s) AND id != %s", (goal_name, goal_id))
            if cursor.fetchone():
                flash(f"Another career goal with title '{goal_name}' already exists.", "danger")
                return redirect(url_for("admin.career_goals"))

            cursor.execute("UPDATE career_goals SET goal_name = %s, description = %s WHERE id = %s", (goal_name, description, goal_id))
            conn.commit()
            flash("Career goal updated successfully.", "success")
    except Exception as exc:
        flash(f"Error updating career goal: {exc}", "danger")

    return redirect(url_for("admin.career_goals"))


@admin_bp.route("/career-goals/<int:goal_id>/delete", methods=["POST"])
@admin_required
@no_cache
def career_goal_delete(goal_id):
    """Safely deletes an unused career goal."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("""
                SELECT cg.goal_name, COUNT(sp.id) AS student_count
                FROM career_goals cg
                LEFT JOIN student_profiles sp ON cg.id = sp.career_goal_id
                WHERE cg.id = %s
                GROUP BY cg.id
            """, (goal_id,))
            check = cursor.fetchone()

            if not check:
                flash("Career goal not found.", "danger")
                return redirect(url_for("admin.career_goals"))

            if check["student_count"] > 0:
                flash(f"Cannot delete career goal '{check['goal_name']}' because {check['student_count']} student(s) currently select it.", "danger")
                return redirect(url_for("admin.career_goals"))

            cursor.execute("DELETE FROM career_goals WHERE id = %s", (goal_id,))
            conn.commit()
            flash(f"Career goal '{check['goal_name']}' deleted.", "success")
    except Exception as exc:
        flash(f"Error deleting career goal: {exc}", "danger")

    return redirect(url_for("admin.career_goals"))


# ============================================================================
# 7. Knowledge Base Matrix
# ============================================================================

@admin_bp.route("/knowledge-base", methods=["GET"])
@admin_required
@no_cache
def knowledge_base():
    """Displays comprehensive course knowledge ontologies, prerequisites, and interest relationships."""
    try:
        from ai_engine import KnowledgeBase
        kb = KnowledgeBase()
        kb.reload()
        all_facts = kb.get_all_courses(active_only=False)

        courses_list = []
        for fact in all_facts:
            f_dict = fact.to_dict()
            f_dict["tags"] = ", ".join(f_dict["interests"])
            f_dict["career_tags"] = ", ".join(f_dict["career_goals"])
            f_dict["prereq_tags"] = ", ".join([p["course_code"] for p in f_dict.get("prerequisite_courses", []) if p.get("course_code")])
            courses_list.append(f_dict)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT COUNT(*) AS total_rules FROM knowledge_rules WHERE is_active = TRUE")
            total_rules = cursor.fetchone()["total_rules"]

            cursor.execute("SELECT COUNT(*) AS total_mappings FROM course_interests")
            total_mappings = cursor.fetchone()["total_mappings"]

            cursor.execute("SELECT COUNT(*) AS total_career_mappings FROM course_career_goals")
            total_career_mappings = cursor.fetchone()["total_career_mappings"]

        audit_report = kb.validate_knowledge_base()

        return render_template(
            "admin_knowledge_base.html",
            courses=courses_list,
            total_rules=total_rules,
            total_mappings=total_mappings,
            total_career_mappings=total_career_mappings,
            audit_report=audit_report
        )
    except Exception as exc:
        flash(f"Failed to load knowledge base matrix: {exc}", "danger")
        return render_template("admin_knowledge_base.html", courses=[], total_rules=0, total_mappings=0, total_career_mappings=0, audit_report=None)


@admin_bp.route("/knowledge-base/audit", methods=["GET", "POST"])
@admin_required
@no_cache
def knowledge_base_audit():
    """Executes on-demand audit and validation across the live AI Knowledge Base."""
    try:
        from ai_engine import KnowledgeBase
        kb = KnowledgeBase()
        audit_report = kb.validate_knowledge_base()

        status = audit_report.get("status", "UNKNOWN")
        err_count = audit_report.get("errors_count", 0)
        warn_count = audit_report.get("warnings_count", 0)
        valid_cnt = audit_report.get("valid_courses_count", 0)
        total_cnt = audit_report.get("total_courses_audited", 0)

        status_type = "success" if status == "HEALTHY" else ("warning" if status == "WARNING" else "danger")
        flash(
            f"Knowledge Base Audit [{status}]: {valid_cnt}/{total_cnt} courses fully valid. "
            f"Errors: {err_count}, Warnings: {warn_count}.",
            status_type
        )
    except Exception as exc:
        flash(f"Error executing knowledge base validation: {exc}", "danger")

    return redirect(url_for("admin.knowledge_base"))


# ============================================================================
# 8. AI Inference Knowledge Rules Management (Zero eval/exec, Structured JSON)
# ============================================================================

@admin_bp.route("/rules", methods=["GET"])
@admin_required
@no_cache
def rules():
    """Renders configured production rules with parsed JSON conditions."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT kr.*, c.course_code, c.course_name
                FROM knowledge_rules kr
                JOIN courses c ON kr.recommended_course_id = c.id
                ORDER BY kr.priority DESC, kr.id ASC
            """)
            rules_raw = cursor.fetchall()

        # Safely parse JSON conditions for template rendering
        for r in rules_raw:
            raw_cond = r.get("conditions")
            if isinstance(raw_cond, str):
                try:
                    r["parsed_conditions"] = json.loads(raw_cond)
                except Exception:
                    r["parsed_conditions"] = {}
            elif isinstance(raw_cond, dict):
                r["parsed_conditions"] = raw_cond
            else:
                r["parsed_conditions"] = {}

        return render_template("admin_rules.html", rules=rules_raw)
    except Exception as exc:
        flash(f"Error loading AI rules: {exc}", "danger")
        return render_template("admin_rules.html", rules=[])


@admin_bp.route("/rules/add", methods=["GET", "POST"])
@admin_required
@no_cache
def rules_add():
    """Adds a new AI knowledge rule using structured JSON antecedents."""
    if request.method == "POST":
        rule_name = request.form.get("rule_name", "").strip()
        course_id_raw = request.form.get("recommended_course_id", "").strip()
        priority_raw = request.form.get("priority", "5").strip()
        min_cgpa_raw = request.form.get("min_cgpa", "2.00").strip()
        min_semester_raw = request.form.get("min_semester", "1").strip()
        rationale = request.form.get("rationale", "").strip()
        is_active = bool(request.form.get("is_active"))
        required_interests = request.form.getlist("required_interests")
        preferred_career_goals = request.form.getlist("preferred_career_goals")

        if not rule_name or not course_id_raw or not rationale:
            flash("Rule Identifier, Recommended Course, and Rationale are required.", "danger")
            return redirect(url_for("admin.rules_add"))

        try:
            course_id = int(course_id_raw)
            priority = max(1, min(10, int(priority_raw)))
            min_cgpa = float(min_cgpa_raw)
            min_semester = max(1, min(12, int(min_semester_raw)))
        except ValueError:
            flash("Invalid numeric value for Priority, Min CGPA, or Min Semester.", "danger")
            return redirect(url_for("admin.rules_add"))

        # Build clean JSON condition structure supporting all (AND) and any (OR)
        all_predicates = [
            {"field": "cgpa", "operator": "greater_than_or_equal", "value": round(min_cgpa, 2)}
        ]
        if min_semester > 1:
            all_predicates.append({"field": "semester", "operator": "greater_than_or_equal", "value": min_semester})

        any_predicates = []
        for interest in required_interests:
            any_predicates.append({"field": "interests", "operator": "contains", "value": interest})
        for goal in preferred_career_goals:
            any_predicates.append({"field": "career_goal", "operator": "equals", "value": goal})

        conditions_dict = {
            "all": all_predicates,
            "any": any_predicates,
            "min_cgpa": round(min_cgpa, 2),
            "min_semester": min_semester,
            "required_interests": required_interests,
            "preferred_career_goals": preferred_career_goals,
            "rationale": rationale
        }

        # Validate rule structure through RuleManager (strictly zero eval/exec)
        val_res = RuleManager.validate_rule_structure({
            "rule_name": rule_name,
            "recommended_course_id": course_id,
            "priority": priority,
            "conditions": conditions_dict
        })
        if not val_res["is_valid"]:
            flash(f"Rule validation error: {'; '.join(val_res['errors'])}", "danger")
            return redirect(url_for("admin.rules_add"))

        conditions_json = json.dumps(conditions_dict, ensure_ascii=False)

        try:
            with get_db_cursor(dictionary=True) as (cursor, conn):
                cursor.execute("""
                    INSERT INTO knowledge_rules (rule_name, conditions, recommended_course_id, priority, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """, (rule_name, conditions_json, course_id, priority, is_active))
                conn.commit()
                flash(f"AI Knowledge Rule '{rule_name}' created successfully.", "success")
                return redirect(url_for("admin.rules"))
        except Exception as exc:
            flash(f"Database error creating rule: {exc}", "danger")
            return redirect(url_for("admin.rules_add"))

    # GET request
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, course_code, course_name FROM courses WHERE is_active = TRUE ORDER BY course_code ASC")
            all_courses = cursor.fetchall()

            cursor.execute("SELECT id, interest_name FROM interests ORDER BY interest_name ASC")
            all_interests = cursor.fetchall()

            cursor.execute("SELECT id, goal_name FROM career_goals ORDER BY goal_name ASC")
            all_career_goals = cursor.fetchall()

        return render_template(
            "admin_rule_form.html",
            rule=None,
            conditions={},
            all_courses=all_courses,
            all_interests=all_interests,
            all_career_goals=all_career_goals
        )
    except Exception as exc:
        flash(f"Failed to load rule form: {exc}", "danger")
        return redirect(url_for("admin.rules"))


@admin_bp.route("/rules/<int:rule_id>/edit", methods=["GET", "POST"])
@admin_required
@no_cache
def rules_edit(rule_id):
    """Edits an existing AI knowledge rule and updates JSON conditions."""
    if request.method == "POST":
        rule_name = request.form.get("rule_name", "").strip()
        course_id_raw = request.form.get("recommended_course_id", "").strip()
        priority_raw = request.form.get("priority", "5").strip()
        min_cgpa_raw = request.form.get("min_cgpa", "2.00").strip()
        min_semester_raw = request.form.get("min_semester", "1").strip()
        rationale = request.form.get("rationale", "").strip()
        is_active = bool(request.form.get("is_active"))
        required_interests = request.form.getlist("required_interests")
        preferred_career_goals = request.form.getlist("preferred_career_goals")

        if not rule_name or not course_id_raw or not rationale:
            flash("Rule Identifier, Recommended Course, and Rationale are required.", "danger")
            return redirect(url_for("admin.rules_edit", rule_id=rule_id))

        try:
            course_id = int(course_id_raw)
            priority = max(1, min(10, int(priority_raw)))
            min_cgpa = float(min_cgpa_raw)
            min_semester = max(1, min(12, int(min_semester_raw)))
        except ValueError:
            flash("Invalid numeric value for Priority, Min CGPA, or Min Semester.", "danger")
            return redirect(url_for("admin.rules_edit", rule_id=rule_id))

        # Build clean JSON condition structure supporting all (AND) and any (OR)
        all_predicates = [
            {"field": "cgpa", "operator": "greater_than_or_equal", "value": round(min_cgpa, 2)}
        ]
        if min_semester > 1:
            all_predicates.append({"field": "semester", "operator": "greater_than_or_equal", "value": min_semester})

        any_predicates = []
        for interest in required_interests:
            any_predicates.append({"field": "interests", "operator": "contains", "value": interest})
        for goal in preferred_career_goals:
            any_predicates.append({"field": "career_goal", "operator": "equals", "value": goal})

        conditions_dict = {
            "all": all_predicates,
            "any": any_predicates,
            "min_cgpa": round(min_cgpa, 2),
            "min_semester": min_semester,
            "required_interests": required_interests,
            "preferred_career_goals": preferred_career_goals,
            "rationale": rationale
        }

        # Validate rule structure through RuleManager (strictly zero eval/exec)
        val_res = RuleManager.validate_rule_structure({
            "rule_name": rule_name,
            "recommended_course_id": course_id,
            "priority": priority,
            "conditions": conditions_dict
        })
        if not val_res["is_valid"]:
            flash(f"Rule validation error: {'; '.join(val_res['errors'])}", "danger")
            return redirect(url_for("admin.rules_edit", rule_id=rule_id))

        conditions_json = json.dumps(conditions_dict, ensure_ascii=False)

        try:
            with get_db_cursor(dictionary=True) as (cursor, conn):
                cursor.execute("""
                    UPDATE knowledge_rules
                    SET rule_name = %s, conditions = %s, recommended_course_id = %s,
                        priority = %s, is_active = %s
                    WHERE id = %s
                """, (rule_name, conditions_json, course_id, priority, is_active, rule_id))
                conn.commit()
                flash(f"Rule '{rule_name}' updated successfully.", "success")
                return redirect(url_for("admin.rules"))
        except Exception as exc:
            flash(f"Database error updating rule: {exc}", "danger")
            return redirect(url_for("admin.rules_edit", rule_id=rule_id))

    # GET request
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT * FROM knowledge_rules WHERE id = %s", (rule_id,))
            rule = cursor.fetchone()
            if not rule:
                flash("Rule not found.", "danger")
                return redirect(url_for("admin.rules"))

            cursor.execute("SELECT id, course_code, course_name FROM courses WHERE is_active = TRUE ORDER BY course_code ASC")
            all_courses = cursor.fetchall()

            cursor.execute("SELECT id, interest_name FROM interests ORDER BY interest_name ASC")
            all_interests = cursor.fetchall()

            cursor.execute("SELECT id, goal_name FROM career_goals ORDER BY goal_name ASC")
            all_career_goals = cursor.fetchall()

        # Parse conditions
        raw_cond = rule.get("conditions")
        if isinstance(raw_cond, str):
            try:
                parsed_cond = json.loads(raw_cond)
            except Exception:
                parsed_cond = {}
        elif isinstance(raw_cond, dict):
            parsed_cond = raw_cond
        else:
            parsed_cond = {}

        return render_template(
            "admin_rule_form.html",
            rule=rule,
            conditions=parsed_cond,
            all_courses=all_courses,
            all_interests=all_interests,
            all_career_goals=all_career_goals
        )
    except Exception as exc:
        flash(f"Failed to load rule: {exc}", "danger")
        return redirect(url_for("admin.rules"))


@admin_bp.route("/rules/<int:rule_id>/toggle", methods=["POST"])
@admin_required
@no_cache
def rule_toggle(rule_id):
    """Toggles active status of an AI rule."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("SELECT rule_name, is_active FROM knowledge_rules WHERE id = %s", (rule_id,))
            r = cursor.fetchone()
            if not r:
                flash("Rule not found.", "danger")
                return redirect(url_for("admin.rules"))

            new_status = not bool(r["is_active"])
            cursor.execute("UPDATE knowledge_rules SET is_active = %s WHERE id = %s", (new_status, rule_id))
            conn.commit()

            status_str = "activated" if new_status else "deactivated"
            flash(f"Rule '{r['rule_name']}' has been {status_str}.", "success")
    except Exception as exc:
        flash(f"Failed to toggle rule status: {exc}", "danger")

    return redirect(url_for("admin.rules"))


@admin_bp.route("/rules/<int:rule_id>/delete", methods=["POST"])
@admin_required
@no_cache
def rule_delete(rule_id):
    """Permanently deletes an AI rule from the knowledge base."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, conn):
            cursor.execute("SELECT rule_name FROM knowledge_rules WHERE id = %s", (rule_id,))
            r = cursor.fetchone()
            if not r:
                flash("Rule not found.", "danger")
                return redirect(url_for("admin.rules"))

            cursor.execute("DELETE FROM knowledge_rules WHERE id = %s", (rule_id,))
            conn.commit()
            flash(f"Rule '{r['rule_name']}' permanently deleted.", "success")
    except Exception as exc:
        flash(f"Failed to delete rule: {exc}", "danger")

    return redirect(url_for("admin.rules"))


@admin_bp.route("/default-rules", methods=["GET"])
@admin_required
@no_cache
def default_rules_view():
    """Renders canonical Non-Monotonic Default Rules (DR01 - DR05)."""
    try:
        rules = DefaultRuleManager.get_all_rules(active_only=False)
        return render_template("admin_default_rules.html", default_rules=rules)
    except Exception as exc:
        flash(f"Error loading default rules: {exc}", "danger")
        return render_template("admin_default_rules.html", default_rules=[])


@admin_bp.route("/default-rules/<rule_code>/toggle", methods=["POST"])
@admin_required
@no_cache
def default_rule_toggle(rule_code):
    """Toggles active status of a non-monotonic default rule (DR01 - DR05)."""
    try:
        success = DefaultRuleManager.toggle_rule(rule_code)
        if success:
            rule = DefaultRuleManager.get_rule_by_code(rule_code)
            status_str = "activated" if (rule and rule.is_active) else "deactivated"
            flash(f"Default rule {rule_code.upper()} has been {status_str}.", "success")
        else:
            flash(f"Default rule {rule_code} not found.", "warning")
    except Exception as exc:
        flash(f"Failed to toggle default rule: {exc}", "danger")

    return redirect(url_for("admin.default_rules_view"))


# ============================================================================
# 9. Recommendation Monitoring & Audit Reports
# ============================================================================

@admin_bp.route("/reports", methods=["GET"])
@admin_required
@no_cache
def reports():
    """Generates analytical reports on recommendation engine activity and distributions."""
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            # Total recommendation logs
            cursor.execute("SELECT COUNT(*) AS total_recommendations FROM recommendation_history")
            total_recommendations = cursor.fetchone()["total_recommendations"]

            # Distinct students advised
            cursor.execute("SELECT COUNT(DISTINCT student_id) AS total_students_advised FROM recommendation_history")
            total_students_advised = cursor.fetchone()["total_students_advised"]

            # Average recommendation match score
            cursor.execute("SELECT ROUND(AVG(recommendation_score), 1) AS avg_score FROM recommendation_history")
            avg_row = cursor.fetchone()
            avg_score = avg_row["avg_score"] if avg_row and avg_row["avg_score"] is not None else 0.0

            # Unique courses recommended
            cursor.execute("SELECT COUNT(DISTINCT recommended_course_id) AS unique_courses FROM recommendation_history")
            unique_courses_recommended = cursor.fetchone()["unique_courses"]

            # Most frequently recommended courses
            cursor.execute("""
                SELECT c.course_code, c.course_name, COUNT(rh.id) AS rec_count
                FROM recommendation_history rh
                JOIN courses c ON rh.recommended_course_id = c.id
                GROUP BY c.id
                ORDER BY rec_count DESC
                LIMIT 6
            """)
            top_courses = cursor.fetchall()
            for c in top_courses:
                c["percentage"] = round((c["rec_count"] / total_recommendations) * 100, 1) if total_recommendations > 0 else 0

            # Recent recommendation audit logs
            cursor.execute("""
                SELECT rh.id, rh.recommendation_score, rh.reasoning, rh.created_at,
                       rh.student_id, sp.full_name, sp.roll_number,
                       c.course_code, c.course_name
                FROM recommendation_history rh
                JOIN student_profiles sp ON rh.student_id = sp.id
                JOIN courses c ON rh.recommended_course_id = c.id
                ORDER BY rh.created_at DESC
                LIMIT 20
            """)
            recent_recommendations = cursor.fetchall()

            # Recommendation score distribution buckets
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN recommendation_score >= 90 THEN 1 ELSE 0 END) AS bucket_90_100,
                    SUM(CASE WHEN recommendation_score >= 80 AND recommendation_score < 90 THEN 1 ELSE 0 END) AS bucket_80_89,
                    SUM(CASE WHEN recommendation_score >= 70 AND recommendation_score < 80 THEN 1 ELSE 0 END) AS bucket_70_79,
                    SUM(CASE WHEN recommendation_score >= 60 AND recommendation_score < 70 THEN 1 ELSE 0 END) AS bucket_60_69,
                    SUM(CASE WHEN recommendation_score < 60 THEN 1 ELSE 0 END) AS bucket_below_60
                FROM recommendation_history
            """)
            score_dist = cursor.fetchone() or {
                "bucket_90_100": 0, "bucket_80_89": 0, "bucket_70_79": 0, "bucket_60_69": 0, "bucket_below_60": 0
            }

            # Frequently matched knowledge rules
            cursor.execute("""
                SELECT kr.id, kr.rule_name, kr.priority, c.course_code, c.course_name,
                       COUNT(rh.id) AS match_count
                FROM knowledge_rules kr
                JOIN courses c ON kr.recommended_course_id = c.id
                LEFT JOIN recommendation_history rh ON rh.recommended_course_id = kr.recommended_course_id
                WHERE kr.is_active = TRUE
                GROUP BY kr.id
                ORDER BY match_count DESC, kr.priority DESC
                LIMIT 5
            """)
            frequent_rules = cursor.fetchall()

        return render_template(
            "admin_reports.html",
            total_recommendations=total_recommendations,
            total_students_advised=total_students_advised,
            avg_score=avg_score,
            unique_courses_recommended=unique_courses_recommended,
            top_courses=top_courses,
            recent_recommendations=recent_recommendations,
            score_distribution=score_dist,
            frequent_rules=frequent_rules
        )
    except Exception as exc:
        flash(f"Failed to load recommendation audit reports: {exc}", "danger")
        return render_template(
            "admin_reports.html",
            total_recommendations=0,
            total_students_advised=0,
            avg_score=0.0,
            unique_courses_recommended=0,
            top_courses=[],
            recent_recommendations=[],
            score_distribution={"bucket_90_100": 0, "bucket_80_89": 0, "bucket_70_79": 0, "bucket_60_69": 0, "bucket_below_60": 0},
            frequent_rules=[]
        )


# ============================================================================
# 10. Administrator Profile & Security
# ============================================================================

@admin_bp.route("/profile", methods=["GET", "POST"])
@admin_required
@no_cache
def profile():
    """Allows viewing admin account details, updating username, and changing master password."""
    admin_id = session.get("user_id")

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "update_profile":
            new_username = request.form.get("username", "").strip()
            if not new_username:
                flash("Username cannot be empty.", "danger")
                return redirect(url_for("admin.profile"))

            try:
                with get_db_cursor(dictionary=True) as (cursor, conn):
                    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s) AND id != %s", (new_username, admin_id))
                    if cursor.fetchone():
                        flash(f"Username '{new_username}' is already taken.", "danger")
                        return redirect(url_for("admin.profile"))

                    cursor.execute("UPDATE users SET username = %s WHERE id = %s", (new_username, admin_id))
                    conn.commit()
                    session["username"] = new_username
                    flash("Administrator username updated successfully.", "success")
            except Exception as exc:
                flash(f"Failed to update profile: {exc}", "danger")

            return redirect(url_for("admin.profile"))

        elif action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not current_password or not new_password or not confirm_password:
                flash("All password fields are required.", "danger")
                return redirect(url_for("admin.profile"))

            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "danger")
                return redirect(url_for("admin.profile"))

            if new_password != confirm_password:
                flash("New password and confirmation do not match.", "danger")
                return redirect(url_for("admin.profile"))

            try:
                with get_db_cursor(dictionary=True) as (cursor, conn):
                    cursor.execute("SELECT password_hash FROM users WHERE id = %s", (admin_id,))
                    user = cursor.fetchone()
                    if not user or not check_password_hash(user["password_hash"], current_password):
                        flash("Current password entered is incorrect.", "danger")
                        return redirect(url_for("admin.profile"))

                    new_hash = generate_password_hash(new_password)
                    cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, admin_id))
                    conn.commit()
                    flash("Password successfully changed.", "success")
            except Exception as exc:
                flash(f"Failed to update password: {exc}", "danger")

            return redirect(url_for("admin.profile"))

    # GET request
    try:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, username, email, role, is_active, created_at FROM users WHERE id = %s", (admin_id,))
            admin_user = cursor.fetchone()
            if not admin_user:
                flash("Administrator user record not found.", "danger")
                return redirect(url_for("auth.logout"))
        return render_template("admin_profile.html", admin_user=admin_user)
    except Exception as exc:
        flash(f"Failed to load profile: {exc}", "danger")
        return redirect(url_for("admin.dashboard"))
