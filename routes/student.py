"""
Student Dashboard & Portal Routes
Phase 4: Student Dashboard Development
Handles student dashboard overview, personal profile updates, academic details,
domain interest selection, career goal selection, course exploration,
AI recommendation staging, and recommendation history.
"""

from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from database.db_connection import get_db_cursor
from routes.decorators import student_required, no_cache
from mysql.connector import Error
from ai_engine.rule_evaluator import evaluate_rules
from ai_engine.default_reasoning import DefaultReasoningEngine, infer_with_defaults
from ai_engine.inference_engine import InferenceEngine, generate_recommendations
from ai_engine.knowledge_base import KnowledgeBase

student_bp = Blueprint("student", __name__, url_prefix="/student")


def get_current_student_profile(user_id):
    """
    Fetch student profile and linked user/career_goal records for the authenticated user.
    Strictly queries by user_id to prevent unauthorized cross-student data leakage.
    """
    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("""
            SELECT 
                sp.id,
                sp.user_id,
                sp.full_name,
                sp.roll_number,
                sp.department,
                sp.semester,
                sp.cgpa,
                sp.career_goal_id,
                u.username,
                u.email,
                u.role,
                cg.goal_name AS career_goal_name,
                cg.description AS career_goal_description
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
            LEFT JOIN career_goals cg ON sp.career_goal_id = cg.id
            WHERE sp.user_id = %s
        """, (user_id,))
        return cursor.fetchone()


@student_bp.route("/dashboard", methods=["GET"])
@student_required
@no_cache
def dashboard():
    """
    Displays the personalized student dashboard.
    Retrieves student name, CGPA, department, semester, interests,
    career goal, available elective course count, and recent recommendations from MySQL.
    """
    user_id = session.get("user_id")

    try:
        profile = get_current_student_profile(user_id)
        if not profile:
            flash("Student profile record not found. Please contact administration.", "danger")
            return redirect(url_for("auth.login"))

        with get_db_cursor(dictionary=True) as (cursor, _):
            # 1. Total available elective courses count
            cursor.execute("SELECT COUNT(*) AS total FROM courses WHERE is_active = TRUE")
            total_courses = cursor.fetchone()["total"]

            # 2. Selected student interests
            cursor.execute("""
                SELECT i.id, i.interest_name
                FROM student_interests si
                JOIN interests i ON si.interest_id = i.id
                WHERE si.student_id = %s
                ORDER BY i.interest_name ASC
            """, (profile["id"],))
            student_interests = cursor.fetchall()

            # 3. Recent recommendation history
            cursor.execute("""
                SELECT 
                    rh.id,
                    rh.recommendation_score,
                    rh.reasoning,
                    rh.created_at,
                    c.course_code,
                    c.course_name,
                    c.difficulty_level
                FROM recommendation_history rh
                JOIN courses c ON rh.recommended_course_id = c.id
                WHERE rh.student_id = %s
                ORDER BY rh.created_at DESC
                LIMIT 5
            """, (profile["id"],))
            recommendations = cursor.fetchall()

        return render_template(
            "student_dashboard.html",
            profile=profile,
            student_interests=student_interests,
            total_courses=total_courses,
            recommendations=recommendations
        )
    except Error as err:
        flash("A database error occurred while loading your dashboard.", "danger")
        return render_template("student_dashboard.html", profile=None, student_interests=[], total_courses=0, recommendations=[])


@student_bp.route("/profile", methods=["GET", "POST"])
@student_required
@no_cache
def profile():
    """
    Allows students to view their profile and update full name, department,
    semester, and roll number.
    Strictly disallows modifying user account role.
    """
    user_id = session.get("user_id")
    profile_data = get_current_student_profile(user_id)

    if not profile_data:
        flash("Student profile record not found.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        department = request.form.get("department", "").strip()
        semester = request.form.get("semester", type=int)

        # Validation
        if not full_name or len(full_name) < 2:
            flash("Full name must be at least 2 characters long.", "danger")
            return render_template("student_profile.html", profile=profile_data)

        if not roll_number:
            flash("Roll number is required.", "danger")
            return render_template("student_profile.html", profile=profile_data)

        if not department:
            flash("Department is required.", "danger")
            return render_template("student_profile.html", profile=profile_data)

        if semester is None or semester < 1 or semester > 12:
            flash("Semester must be between 1 and 12.", "danger")
            return render_template("student_profile.html", profile=profile_data)

        try:
            with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
                # Verify roll_number uniqueness if changed
                cursor.execute(
                    "SELECT id FROM student_profiles WHERE roll_number = %s AND id != %s",
                    (roll_number, profile_data["id"])
                )
                if cursor.fetchone():
                    flash("This roll number is already assigned to another student profile.", "warning")
                    return render_template("student_profile.html", profile=profile_data)

                # Update student profile
                cursor.execute("""
                    UPDATE student_profiles
                    SET full_name = %s, roll_number = %s, department = %s, semester = %s
                    WHERE id = %s AND user_id = %s
                """, (full_name, roll_number, department, semester, profile_data["id"], user_id))

            flash("Student profile updated successfully!", "success")
            return redirect(url_for("student.profile"))
        except Error as err:
            flash("Database error while updating profile.", "danger")

    return render_template("student_profile.html", profile=profile_data)


@student_bp.route("/academic", methods=["GET", "POST"])
@student_required
@no_cache
def academic():
    """
    Allows students to view academic information, update semester, and enter CGPA.
    Validates CGPA strictly between 0.00 and 10.00.
    """
    user_id = session.get("user_id")
    profile_data = get_current_student_profile(user_id)

    if not profile_data:
        flash("Student profile record not found.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        semester = request.form.get("semester", type=int)
        cgpa_raw = request.form.get("cgpa", "").strip()

        try:
            cgpa = float(cgpa_raw)
        except (ValueError, TypeError):
            flash("Invalid CGPA format. Please enter a numerical decimal value.", "danger")
            return render_template("academic_details.html", profile=profile_data)

        # Validate CGPA between 0 and 10
        if cgpa < 0.0 or cgpa > 10.0:
            flash("CGPA must be between 0.00 and 10.00.", "danger")
            return render_template("academic_details.html", profile=profile_data)

        if semester is None or semester < 1 or semester > 12:
            flash("Semester must be between 1 and 12.", "danger")
            return render_template("academic_details.html", profile=profile_data)

        try:
            with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
                cursor.execute("""
                    UPDATE student_profiles
                    SET semester = %s, cgpa = %s
                    WHERE id = %s AND user_id = %s
                """, (semester, cgpa, profile_data["id"], user_id))

            flash("Academic details and CGPA updated successfully!", "success")
            return redirect(url_for("student.academic"))
        except Error as err:
            flash("Database error while updating academic details.", "danger")

    return render_template("academic_details.html", profile=profile_data)


@student_bp.route("/interests", methods=["GET", "POST"])
@student_required
@no_cache
def interests():
    """
    Retrieves available interests from MySQL interests table.
    Allows students to select and remove multiple interests.
    Prevents duplicate interest assignments in student_interests.
    """
    user_id = session.get("user_id")
    profile_data = get_current_student_profile(user_id)

    if not profile_data:
        flash("Student profile record not found.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        raw_ids = request.form.getlist("interest_ids")
        # Deduplicate and validate integer IDs
        selected_ids = list({int(i) for i in raw_ids if i.isdigit()})

        try:
            with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
                # 1. Clear existing student interests
                cursor.execute("DELETE FROM student_interests WHERE student_id = %s", (profile_data["id"],))

                # 2. Insert new distinct student interests
                for int_id in selected_ids:
                    # Confirm interest exists
                    cursor.execute("SELECT id FROM interests WHERE id = %s", (int_id,))
                    if cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO student_interests (student_id, interest_id)
                            VALUES (%s, %s)
                        """, (profile_data["id"], int_id))

            flash("Domain interests updated successfully! Your elective matches will reflect these preferences.", "success")
            return redirect(url_for("student.interests"))
        except Error as err:
            flash("Failed to update domain interests in database.", "danger")

    # Fetch available and selected interests
    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("SELECT id, interest_name FROM interests ORDER BY interest_name ASC")
        all_interests = cursor.fetchall()

        cursor.execute("SELECT interest_id FROM student_interests WHERE student_id = %s", (profile_data["id"],))
        selected_interest_ids = [row["interest_id"] for row in cursor.fetchall()]

    return render_template(
        "interests.html",
        profile=profile_data,
        all_interests=all_interests,
        selected_interest_ids=selected_interest_ids
    )


@student_bp.route("/career-goals", methods=["GET", "POST"])
@student_required
@no_cache
def career_goals():
    """
    Retrieves available career goals from career_goals table.
    Allows students to select, update, or clear their preferred career goal.
    """
    user_id = session.get("user_id")
    profile_data = get_current_student_profile(user_id)

    if not profile_data:
        flash("Student profile record not found.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        action = request.form.get("action", "save")
        goal_id_raw = request.form.get("career_goal_id")

        try:
            with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
                if action == "clear" or not goal_id_raw:
                    # Clear career goal
                    cursor.execute("""
                        UPDATE student_profiles
                        SET career_goal_id = NULL
                        WHERE id = %s AND user_id = %s
                    """, (profile_data["id"], user_id))
                    flash("Preferred career goal cleared.", "info")
                else:
                    goal_id = int(goal_id_raw)
                    # Verify goal exists
                    cursor.execute("SELECT goal_name FROM career_goals WHERE id = %s", (goal_id,))
                    goal = cursor.fetchone()
                    if not goal:
                        flash("Selected career goal is invalid.", "danger")
                        return redirect(url_for("student.career_goals"))

                    cursor.execute("""
                        UPDATE student_profiles
                        SET career_goal_id = %s
                        WHERE id = %s AND user_id = %s
                    """, (goal_id, profile_data["id"], user_id))
                    flash(f"Career goal updated to '{goal['goal_name']}'!", "success")

            return redirect(url_for("student.career_goals"))
        except (ValueError, Error) as err:
            flash("Database error while updating career goal.", "danger")

    # Fetch career goals catalog
    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("SELECT id, goal_name, description FROM career_goals ORDER BY goal_name ASC")
        goals = cursor.fetchall()

    return render_template("career_goals.html", profile=profile_data, career_goals=goals)


@student_bp.route("/courses", methods=["GET"])
@student_required
@no_cache
def courses():
    """
    Displays available elective courses using the AI Knowledge Base with search and filtering.
    Shows course name, code, description, minimum CGPA, difficulty level,
    career opportunities, prerequisites, and related interest tags.
    """
    user_id = session.get("user_id")
    profile_data = get_current_student_profile(user_id)

    from ai_engine import KnowledgeBase
    kb = KnowledgeBase()
    active_facts = kb.get_all_courses(active_only=True)

    all_courses = []
    for fact in active_facts:
        c_dict = fact.to_dict()
        c_dict["id"] = fact.course_id
        c_dict["tags"] = ", ".join(fact.interests)
        c_dict["career_scope"] = ", ".join(fact.career_goals) if fact.career_goals else fact.description
        c_dict["prerequisites"] = fact.prerequisites_text or ("None" if not fact.prerequisite_courses else ", ".join(fact.prerequisite_codes))
        all_courses.append(c_dict)

    return render_template("explore_courses.html", profile=profile_data, courses=all_courses)


@student_bp.route("/recommendations", methods=["GET", "POST"])
@student_required
@no_cache
def recommendations():
    """
    AI Recommendation interface powered by Phase 9 Inference Engine.
    When a student clicks 'Generate Recommendations':
    - Retrieves profile, interests, and career goals.
    - Executes forward chaining rule-based and default reasoning.
    - Evaluates hard course eligibility.
    - Computes multi-factor weighted scores (40% Interest, 35% Career, 15% CGPA, 10% Prereq).
    - Ranks and filters courses with XAI natural language explanations.
    - Persists recommendations to MySQL recommendation_history.
    """
    user_id = session.get("user_id")
    profile_data = get_current_student_profile(user_id)
    student_id = profile_data["id"]

    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("""
            SELECT i.id, i.interest_name
            FROM student_interests si
            JOIN interests i ON si.interest_id = i.id
            WHERE si.student_id = %s
        """, (student_id,))
        student_interests = cursor.fetchall()
        student_interest_names = [i["interest_name"] for i in student_interests]

    recommendation_results = None

    if request.method == "POST":
        student_facts = {
            "student_id": student_id,
            "cgpa": profile_data["cgpa"],
            "semester": profile_data["semester"],
            "department": profile_data.get("department", "Computer Science"),
            "interests": student_interest_names,
            "career_goal": profile_data.get("career_goal_name", "")
        }

        engine = InferenceEngine()
        recommendation_results = engine.recommend_and_persist(
            student_id=student_id,
            student_profile=student_facts,
            min_score_threshold=0.0,
            top_n=6
        )

        flash(
            f"AI Recommendation Staging Activated: Evaluated profile for {profile_data['full_name']} "
            f"(CGPA: {profile_data['cgpa']:.2f}, Semester: {profile_data['semester']}). "
            "The full Rule-Based Inference Engine will execute recommendations in Phase 5. "
            f"AI Inference Engine generated and persisted {len(recommendation_results.get('recommendations', []))} course recommendations!",
            "success"
        )
        return render_template(
            "ai_recommendations.html",
            profile=profile_data,
            student_interests=student_interests,
            recommendation_results=recommendation_results,
            recent_history=None
        )
    else:
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT rh.id, rh.recommendation_score, rh.reasoning, rh.created_at,
                       c.course_code, c.course_name, c.difficulty_level
                FROM recommendation_history rh
                JOIN courses c ON rh.recommended_course_id = c.id
                WHERE rh.student_id = %s
                ORDER BY rh.created_at DESC
                LIMIT 6
            """, (student_id,))
            recent_history = cursor.fetchall()

    return render_template(
        "ai_recommendations.html",
        profile=profile_data,
        student_interests=student_interests,
        recommendation_results=None,
        recent_history=recent_history
    )


@student_bp.route("/history", methods=["GET"])
@student_required
@no_cache
def history():
    """
    Displays previously saved recommendations from recommendation_history table.
    Shows course name, recommendation score, reasoning, and recommendation date.
    Displays a clean empty-state message if no recommendations exist.
    """
    user_id = session.get("user_id")
    profile_data = get_current_student_profile(user_id)

    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("""
            SELECT 
                rh.id,
                rh.recommendation_score,
                rh.reasoning,
                rh.created_at,
                c.course_code,
                c.course_name,
                c.difficulty_level
            FROM recommendation_history rh
            JOIN courses c ON rh.recommended_course_id = c.id
            WHERE rh.student_id = %s
            ORDER BY rh.created_at DESC
        """, (profile_data["id"],))
        recommendations_list = cursor.fetchall()

    return render_template(
        "recommendation_history.html",
        profile=profile_data,
        recommendations=recommendations_list
    )


@student_bp.route("/rule-testing", methods=["GET", "POST"])
@student_required
@no_cache
def rule_testing():
    """
    AI Rule Testing sandbox for authenticated students.
    Allows students to input or adjust:
    1. CGPA
    2. Technical interests
    3. Career goal
    Executes actual Python rule evaluator against MySQL Knowledge Base.
    Displays:
    - Matched rules
    - Failed rules
    - Recommended courses
    - Rejected courses
    - Detailed reasoning explanations
    """
    user_id = session.get("user_id")
    profile_data = get_current_student_profile(user_id)

    # Fetch available interests and career goals from MySQL
    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("SELECT id, interest_name FROM interests ORDER BY interest_name ASC")
        all_interests = cursor.fetchall()

        cursor.execute("SELECT id, goal_name FROM career_goals ORDER BY goal_name ASC")
        all_career_goals = cursor.fetchall()

        # Student's current saved interests
        cursor.execute("""
            SELECT i.interest_name
            FROM student_interests si
            JOIN interests i ON si.interest_id = i.id
            WHERE si.student_id = %s
        """, (profile_data["id"],))
        student_saved_interests = [row["interest_name"] for row in cursor.fetchall()]

    selected_cgpa = float(profile_data.get("cgpa") or 0.0)
    selected_interests = list(student_saved_interests)
    selected_career_goal = str(profile_data.get("career_goal_name") or "")
    evaluation_result = None
    matched_rules = []
    failed_rules = []
    recommended_courses = []
    rejected_courses = []
    clarification_messages = []
    applied_default_rules = []
    assumptions_made = []
    is_default_reasoning_used = False

    if request.method == "POST":
        cgpa_raw = request.form.get("cgpa", "").strip()
        selected_interests = request.form.getlist("interests")
        selected_career_goal = request.form.get("career_goal", "").strip()

        try:
            selected_cgpa = float(cgpa_raw)
            if selected_cgpa < 0.0 or selected_cgpa > 10.0:
                flash("CGPA must be between 0.00 and 10.00.", "warning")
                selected_cgpa = max(0.0, min(10.0, selected_cgpa))
        except (ValueError, TypeError):
            flash("Invalid CGPA entered. Defaulting to profile CGPA.", "warning")
            selected_cgpa = float(profile_data.get("cgpa") or 0.0)

        # Build student facts dictionary
        student_facts = {
            "cgpa": selected_cgpa,
            "semester": int(profile_data.get("semester") or 1),
            "department": str(profile_data.get("department") or "Computer Science"),
            "interests": selected_interests,
            "career_goal": selected_career_goal
        }

        try:
            kb = KnowledgeBase()
            # 1. Run deterministic Rule-Based Evaluation
            evaluation_result = evaluate_rules(student_facts, knowledge_base=kb)

            recommended_courses = list(evaluation_result.get("recommended_courses", []))
            audit_trail = list(evaluation_result.get("audit_trail", []))

            # Categorize matched and failed rules from audit trail
            matched_rules = [step for step in audit_trail if step.get("status") == "FIRED"]
            failed_rules = [step for step in audit_trail if step.get("status") == "REJECTED"]

            # 2. Run Non-Monotonic Default Reasoning Engine (DR01 - DR05)
            def_engine = DefaultReasoningEngine()
            def_result = def_engine.evaluate(student_facts, knowledge_base=kb)

            clarification_messages = def_result.get("clarification_messages", [])
            applied_default_rules = def_result.get("applied_default_rules", [])
            assumptions_made = def_result.get("assumptions_made", [])
            is_default_reasoning_used = def_result.get("is_default_reasoning_used", False)

            # If rule-based reasoning found no matches, fallback to default reasoning results
            if not recommended_courses and def_result.get("recommended_courses"):
                recommended_courses = list(def_result.get("recommended_courses", []))

            # Deduplicate rejected courses
            rec_course_ids = {r["course_id"] for r in recommended_courses}
            seen_rejected = set()
            for rej in (evaluation_result.get("rejected_evaluations", []) + def_result.get("rejected_courses", [])):
                c_id = rej.get("course_id")
                if c_id not in seen_rejected and c_id not in rec_course_ids:
                    seen_rejected.add(c_id)
                    rejected_courses.append(rej)

            flash(f"Rule evaluation completed: {len(matched_rules)} rule(s) fired, {len(recommended_courses)} course(s) recommended.", "success")
        except Exception as exc:
            flash(f"Error evaluating AI rules: {exc}", "danger")
            clarification_messages = []
            applied_default_rules = []
            assumptions_made = []
            is_default_reasoning_used = False

    return render_template(
        "student_rule_testing.html",
        profile=profile_data,
        all_interests=all_interests,
        all_career_goals=all_career_goals,
        selected_cgpa=selected_cgpa,
        selected_interests=selected_interests,
        selected_career_goal=selected_career_goal,
        evaluation_result=evaluation_result,
        matched_rules=matched_rules,
        failed_rules=failed_rules,
        recommended_courses=recommended_courses,
        rejected_courses=rejected_courses,
        clarification_messages=clarification_messages,
        applied_default_rules=applied_default_rules,
        assumptions_made=assumptions_made,
        is_default_reasoning_used=is_default_reasoning_used
    )
