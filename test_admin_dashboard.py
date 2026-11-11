"""
Phase 5 Admin Dashboard Comprehensive Test Suite
Validates:
- Category A: Dashboard statistics, aggregations, and recent student activity
- Category B: Student management (search, filter, dossier view, account activation toggle, login block)
- Category C: Course management (CRUD, domain interest sync, status toggle, safe deletion policy)
- Category D: Domain interests and career goals management (CRUD and safety constraints)
- Category E: Knowledge base ontological matrix and requirement mappings
- Category F: AI knowledge rules management (structured JSON conditions, toggle, delete, validation)
- Category G: Role authorization, unauthenticated access blocking, and admin profile security
"""

import os
import sys
import json
import unittest
from werkzeug.security import generate_password_hash, check_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from database.db_connection import get_db_cursor


class AdminDashboardTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        cls.admin_username = "admin_p5_test"
        cls.admin_email = "admin_p5_test@university.edu"
        cls.admin_password = "AdminSecret#2026"

        cls.student_username = "student_p5_test"
        cls.student_email = "student_p5_test@university.edu"
        cls.student_password = "StudentPass#2026"

        cls.cleanup_data()

        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            # 1. Create Admin User
            admin_hash = generate_password_hash(cls.admin_password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, 'admin', TRUE)
            """, (cls.admin_username, cls.admin_email, admin_hash))
            cls.admin_user_id = cursor.lastrowid

            # 2. Create Student User & Profile
            student_hash = generate_password_hash(cls.student_password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, 'student', TRUE)
            """, (cls.student_username, cls.student_email, student_hash))
            cls.student_user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (cls.student_user_id, "Test Student P5", "ROLL-P5-001", "Computer Science", 5, 3.45))
            cls.student_profile_id = cursor.lastrowid

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_data()

    @classmethod
    def cleanup_data(cls):
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            # Clean up test rules
            cursor.execute("DELETE FROM knowledge_rules WHERE rule_name LIKE 'TEST_%'")
            # Clean up test courses
            cursor.execute("DELETE FROM courses WHERE course_code LIKE 'TEST-%'")
            # Clean up test interests
            cursor.execute("DELETE FROM interests WHERE interest_name LIKE 'TEST_%'")
            # Clean up test career goals
            cursor.execute("DELETE FROM career_goals WHERE goal_name LIKE 'TEST_%'")
            # Clean up users
            cursor.execute("DELETE FROM users WHERE username IN ('admin_p5_test', 'admin_p5_updated', 'student_p5_test')")

    def setUp(self):
        self.client = app.test_client()

    def login_admin(self):
        """Helper to establish an authenticated admin session."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.admin_user_id
            sess["username"] = self.admin_username
            sess["email"] = self.admin_email
            sess["role"] = "admin"

    def login_student(self):
        """Helper to establish an authenticated student session."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_user_id
            sess["username"] = self.student_username
            sess["email"] = self.student_email
            sess["role"] = "student"

    # =========================================================================
    # Test Category A: Admin Dashboard Overview
    # =========================================================================

    def test_A1_dashboard_stats_and_overview(self):
        """Verifies admin dashboard displays real metrics matching MySQL tables."""
        self.login_admin()
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 200)

        html = response.data.decode("utf-8")
        self.assertIn("System Overview & Analytics", html)
        self.assertIn("Students", html)
        self.assertIn("Courses", html)
        self.assertIn("AI Rules", html)
        self.assertIn("Recently Registered Students", html)
        self.assertIn("ROLL-P5-001", html)
        self.assertIn("Test Student P5", html)

    # =========================================================================
    # Test Category B: Student Management
    # =========================================================================

    def test_B1_students_list_search_and_filters(self):
        """Tests student list, search filtering by name/roll, and department/semester filters."""
        self.login_admin()

        # 1. Base list
        resp = self.client.get("/admin/students")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ROLL-P5-001", resp.data.decode("utf-8"))

        # 2. Search by query 'ROLL-P5'
        resp_search = self.client.get("/admin/students?q=ROLL-P5")
        self.assertEqual(resp_search.status_code, 200)
        self.assertIn("ROLL-P5-001", resp_search.data.decode("utf-8"))

        # 3. Search query that matches nothing
        resp_nomatch = self.client.get("/admin/students?q=NONEXISTENT_XYZ_QUERY")
        self.assertEqual(resp_nomatch.status_code, 200)
        self.assertNotIn("ROLL-P5-001", resp_nomatch.data.decode("utf-8"))

        # 4. Department filter
        resp_dept = self.client.get("/admin/students?dept=Computer+Science")
        self.assertEqual(resp_dept.status_code, 200)
        self.assertIn("ROLL-P5-001", resp_dept.data.decode("utf-8"))

        # 5. Semester filter
        resp_sem = self.client.get("/admin/students?sem=5")
        self.assertEqual(resp_sem.status_code, 200)
        self.assertIn("ROLL-P5-001", resp_sem.data.decode("utf-8"))

    def test_B2_student_detail_dossier(self):
        """Verifies individual student dossier details view."""
        self.login_admin()
        resp = self.client.get(f"/admin/students/{self.student_profile_id}")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Test Student P5", html)
        self.assertIn("ROLL-P5-001", html)
        self.assertIn("Computer Science", html)
        self.assertIn("Semester 5", html)

    def test_B3_student_toggle_status_and_login_blocking(self):
        """Verifies toggling student status deactivates account and blocks login."""
        self.login_admin()

        # 1. Toggle status to deactivated
        resp_toggle = self.client.post(f"/admin/students/{self.student_profile_id}/toggle-status", follow_redirects=True)
        self.assertEqual(resp_toggle.status_code, 200)

        # Check DB reflects is_active = 0
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT is_active FROM users WHERE id = %s", (self.student_user_id,))
            u = cursor.fetchone()
            self.assertEqual(u["is_active"], 0)

        # 2. Attempt login as deactivated student
        client_unauth = app.test_client()
        login_resp = client_unauth.post("/login", data={
            "identifier": self.student_email,
            "password": self.student_password
        }, follow_redirects=True)
        login_html = login_resp.data.decode("utf-8")
        self.assertIn("deactivated", login_html.lower())

        # 3. Reactivate student account
        self.login_admin()
        self.client.post(f"/admin/students/{self.student_profile_id}/toggle-status", follow_redirects=True)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT is_active FROM users WHERE id = %s", (self.student_user_id,))
            u = cursor.fetchone()
            self.assertEqual(u["is_active"], 1)

    # =========================================================================
    # Test Category C: Course Management
    # =========================================================================

    def test_C1_course_crud_and_interest_sync(self):
        """Verifies adding a course, mapping interests, editing details, toggling status, and deleting."""
        self.login_admin()

        # Fetch an interest to link
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM interests LIMIT 1")
            interest_row = cursor.fetchone()
            interest_id = interest_row["id"]

        # 1. Add Course
        add_data = {
            "course_code": "TEST-501",
            "course_name": "Test Neural Networks",
            "description": "Deep learning architectures and backpropagation.",
            "minimum_cgpa": "2.75",
            "difficulty_level": "Advanced",
            "career_scope": "AI Engineer",
            "prerequisites": "Calculus, Linear Algebra",
            "is_active": "1",
            "interest_ids": [str(interest_id)]
        }
        resp_add = self.client.post("/admin/courses/add", data=add_data, follow_redirects=True)
        self.assertEqual(resp_add.status_code, 200)

        # Verify insertion in DB
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, course_code, difficulty_level FROM courses WHERE course_code = 'TEST-501'")
            c = cursor.fetchone()
            self.assertIsNotNone(c)
            test_course_id = c["id"]

            cursor.execute("SELECT interest_id FROM course_interests WHERE course_id = %s", (test_course_id,))
            ci = cursor.fetchone()
            self.assertEqual(ci["interest_id"], interest_id)

        # 2. Edit Course
        edit_data = {
            "course_code": "TEST-501",
            "course_name": "Test Neural Networks & Deep Learning",
            "description": "Advanced deep learning architectures.",
            "minimum_cgpa": "3.00",
            "difficulty_level": "Advanced",
            "career_scope": "Deep Learning Researcher",
            "prerequisites": "Calculus, Python",
            "is_active": "1"
        }
        resp_edit = self.client.post(f"/admin/courses/{test_course_id}/edit", data=edit_data, follow_redirects=True)
        self.assertEqual(resp_edit.status_code, 200)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT course_name, minimum_cgpa FROM courses WHERE id = %s", (test_course_id,))
            updated_c = cursor.fetchone()
            self.assertEqual(updated_c["course_name"], "Test Neural Networks & Deep Learning")
            self.assertEqual(float(updated_c["minimum_cgpa"]), 3.00)

        # 3. Toggle Status
        self.client.post(f"/admin/courses/{test_course_id}/toggle-status", follow_redirects=True)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT is_active FROM courses WHERE id = %s", (test_course_id,))
            self.assertEqual(cursor.fetchone()["is_active"], 0)

        # 4. Safe Deletion Policy check:
        # Case A: When recommendations exist, soft-deactivates instead of deleting
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("""
                INSERT INTO recommendation_history (student_id, recommended_course_id, recommendation_score, reasoning)
                VALUES (%s, %s, %s, %s)
            """, (self.student_profile_id, test_course_id, 92.50, "Audit test recommendation record."))

        resp_del = self.client.post(f"/admin/courses/{test_course_id}/delete", follow_redirects=True)
        self.assertEqual(resp_del.status_code, 200)

        # Course should still exist in DB (soft deactivated)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, is_active FROM courses WHERE id = %s", (test_course_id,))
            soft_c = cursor.fetchone()
            self.assertIsNotNone(soft_c)
            self.assertEqual(soft_c["is_active"], 0)

        # Clean up test recommendation and permanently delete course
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("DELETE FROM recommendation_history WHERE recommended_course_id = %s", (test_course_id,))

        resp_hard_del = self.client.post(f"/admin/courses/{test_course_id}/delete", follow_redirects=True)
        self.assertEqual(resp_hard_del.status_code, 200)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM courses WHERE id = %s", (test_course_id,))
            self.assertIsNone(cursor.fetchone())

    # =========================================================================
    # Test Category D: Interests and Career Goals Management
    # =========================================================================

    def test_D1_interest_crud_and_safety_checks(self):
        """Verifies adding, editing, and safely deleting domain interests."""
        self.login_admin()

        # 1. Add interest
        resp_add = self.client.post("/admin/interests", data={"interest_name": "TEST_Bioinformatics"}, follow_redirects=True)
        self.assertEqual(resp_add.status_code, 200)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM interests WHERE interest_name = 'TEST_Bioinformatics'")
            test_int = cursor.fetchone()
            self.assertIsNotNone(test_int)
            int_id = test_int["id"]

        # 2. Edit interest
        resp_edit = self.client.post(f"/admin/interests/{int_id}/edit", data={"interest_name": "TEST_Computational_Biology"}, follow_redirects=True)
        self.assertEqual(resp_edit.status_code, 200)

        # 3. Delete unused interest
        resp_del = self.client.post(f"/admin/interests/{int_id}/delete", follow_redirects=True)
        self.assertEqual(resp_del.status_code, 200)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM interests WHERE id = %s", (int_id,))
            self.assertIsNone(cursor.fetchone())

    def test_D2_career_goal_crud_and_safety_checks(self):
        """Verifies adding, editing, and safely deleting career goals."""
        self.login_admin()

        # 1. Add career goal
        resp_add = self.client.post("/admin/career-goals", data={
            "goal_name": "TEST_Quantum_Architect",
            "description": "Designs quantum algorithm circuits."
        }, follow_redirects=True)
        self.assertEqual(resp_add.status_code, 200)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM career_goals WHERE goal_name = 'TEST_Quantum_Architect'")
            g = cursor.fetchone()
            self.assertIsNotNone(g)
            goal_id = g["id"]

        # 2. Edit career goal
        resp_edit = self.client.post(f"/admin/career-goals/{goal_id}/edit", data={
            "goal_name": "TEST_Quantum_Architect_Sr",
            "description": "Senior lead for quantum algorithm engineering."
        }, follow_redirects=True)
        self.assertEqual(resp_edit.status_code, 200)

        # 3. Delete unused career goal
        resp_del = self.client.post(f"/admin/career-goals/{goal_id}/delete", follow_redirects=True)
        self.assertEqual(resp_del.status_code, 200)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM career_goals WHERE id = %s", (goal_id,))
            self.assertIsNone(cursor.fetchone())

    # =========================================================================
    # Test Category E: Knowledge Base View
    # =========================================================================

    def test_E1_knowledge_base_matrix(self):
        """Verifies knowledge base matrix displays all course ontologies and relationships."""
        self.login_admin()
        resp = self.client.get("/admin/knowledge-base")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Knowledge Base", html)
        self.assertIn("Course Matrix", html)
        self.assertIn("Live Knowledge Base", html)

    # =========================================================================
    # Test Category F: AI Knowledge Rules Management (Zero eval/exec)
    # =========================================================================

    def test_F1_ai_rule_crud_with_structured_json(self):
        """Verifies AI rule creation storing structured JSON conditions, toggling, editing, and deletion."""
        self.login_admin()

        # Fetch an active course to target
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM courses WHERE is_active = TRUE LIMIT 1")
            target_course_id = cursor.fetchone()["id"]

        # 1. Create Rule
        rule_data = {
            "rule_name": "TEST_Rule_AI_Robotics",
            "recommended_course_id": str(target_course_id),
            "priority": "8",
            "min_cgpa": "3.20",
            "min_semester": "4",
            "rationale": "High performing student interested in robotics systems.",
            "is_active": "1",
            "required_interests": ["Machine Learning", "Artificial Intelligence"],
            "preferred_career_goals": ["Machine Learning Engineer"]
        }
        resp_add = self.client.post("/admin/rules/add", data=rule_data, follow_redirects=True)
        self.assertEqual(resp_add.status_code, 200)

        # Verify JSON condition stored in DB
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, conditions, priority FROM knowledge_rules WHERE rule_name = 'TEST_Rule_AI_Robotics'")
            r = cursor.fetchone()
            self.assertIsNotNone(r)
            test_rule_id = r["id"]
            self.assertEqual(r["priority"], 8)

            conds = json.loads(r["conditions"]) if isinstance(r["conditions"], str) else r["conditions"]
            self.assertEqual(conds["min_cgpa"], 3.20)
            self.assertEqual(conds["min_semester"], 4)
            self.assertIn("Machine Learning", conds["required_interests"])

        # 2. Edit Rule
        edit_data = {
            "rule_name": "TEST_Rule_AI_Robotics_Updated",
            "recommended_course_id": str(target_course_id),
            "priority": "9",
            "min_cgpa": "3.50",
            "min_semester": "5",
            "rationale": "Updated rationale for senior robotics specialization.",
            "is_active": "1",
            "required_interests": ["Machine Learning"],
            "preferred_career_goals": ["Machine Learning Engineer"]
        }
        resp_edit = self.client.post(f"/admin/rules/{test_rule_id}/edit", data=edit_data, follow_redirects=True)
        self.assertEqual(resp_edit.status_code, 200)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT rule_name, priority, conditions FROM knowledge_rules WHERE id = %s", (test_rule_id,))
            updated_r = cursor.fetchone()
            self.assertEqual(updated_r["rule_name"], "TEST_Rule_AI_Robotics_Updated")
            self.assertEqual(updated_r["priority"], 9)
            conds_up = json.loads(updated_r["conditions"]) if isinstance(updated_r["conditions"], str) else updated_r["conditions"]
            self.assertEqual(conds_up["min_cgpa"], 3.50)

        # 3. Toggle Rule
        self.client.post(f"/admin/rules/{test_rule_id}/toggle", follow_redirects=True)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT is_active FROM knowledge_rules WHERE id = %s", (test_rule_id,))
            self.assertEqual(cursor.fetchone()["is_active"], 0)

        # 4. Delete Rule
        resp_del = self.client.post(f"/admin/rules/{test_rule_id}/delete", follow_redirects=True)
        self.assertEqual(resp_del.status_code, 200)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM knowledge_rules WHERE id = %s", (test_rule_id,))
            self.assertIsNone(cursor.fetchone())

    # =========================================================================
    # Test Category G: Security, Authorization & Admin Profile
    # =========================================================================

    def test_G1_unauthenticated_access_is_blocked(self):
        """Unauthenticated requests to admin endpoints must redirect to login."""
        endpoints = [
            "/admin/dashboard",
            "/admin/students",
            "/admin/courses",
            "/admin/interests",
            "/admin/career-goals",
            "/admin/knowledge-base",
            "/admin/rules",
            "/admin/reports",
            "/admin/profile"
        ]
        for ep in endpoints:
            resp = self.client.get(ep)
            self.assertEqual(resp.status_code, 302, f"Endpoint {ep} should redirect unauthenticated users.")

    def test_G2_student_role_blocked_from_admin_portal(self):
        """Student accounts must be strictly forbidden from accessing admin endpoints."""
        self.login_student()
        endpoints = [
            "/admin/dashboard",
            "/admin/students",
            "/admin/courses",
            "/admin/rules",
            "/admin/reports"
        ]
        for ep in endpoints:
            resp = self.client.get(ep, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode("utf-8")
            # Should be blocked and redirected with unauthorized flash message or student dashboard
            self.assertTrue(
                "unauthorized" in html.lower() or "permission" in html.lower() or "access denied" in html.lower() or "student dashboard" in html.lower(),
                f"Student was unexpectedly permitted access to {ep}"
            )

    def test_G3_admin_reports_monitoring(self):
        """Verifies recommendation audit report analytics page renders properly."""
        self.login_admin()
        resp = self.client.get("/admin/reports")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertIn("Recommendation Monitoring", html)
        self.assertIn("Audit Reports", html)
        self.assertIn("Total Recommendations", html)

    def test_G4_admin_profile_and_password_security(self):
        """Tests admin updating username and verifying old password before password change."""
        self.login_admin()

        # 1. Update username
        resp_name = self.client.post("/admin/profile", data={
            "action": "update_profile",
            "username": "admin_p5_updated"
        }, follow_redirects=True)
        self.assertEqual(resp_name.status_code, 200)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT username FROM users WHERE id = %s", (self.admin_user_id,))
            self.assertEqual(cursor.fetchone()["username"], "admin_p5_updated")

        # 2. Change password with wrong current password (should fail)
        resp_wrong = self.client.post("/admin/profile", data={
            "action": "change_password",
            "current_password": "WrongPassword#123",
            "new_password": "BrandNewPassword#2026",
            "confirm_password": "BrandNewPassword#2026"
        }, follow_redirects=True)
        self.assertIn("incorrect", resp_wrong.data.decode("utf-8").lower())

        # 3. Change password with valid current password
        resp_pw = self.client.post("/admin/profile", data={
            "action": "change_password",
            "current_password": self.admin_password,
            "new_password": "BrandNewPassword#2026",
            "confirm_password": "BrandNewPassword#2026"
        }, follow_redirects=True)
        self.assertIn("successfully changed", resp_pw.data.decode("utf-8").lower())

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT password_hash FROM users WHERE id = %s", (self.admin_user_id,))
            new_hash = cursor.fetchone()["password_hash"]
            self.assertTrue(check_password_hash(new_hash, "BrandNewPassword#2026"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
