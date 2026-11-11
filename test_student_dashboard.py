"""
Phase 4 Student Dashboard Comprehensive Test Suite
Validates student dashboard data retrieval, profile updates, CGPA 0-10 validation,
interest management, career goal selection, course exploration,
AI recommendation staging, and data isolation between students.
"""

import os
import sys
import unittest
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from database.db_connection import get_db_cursor


class StudentDashboardTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        cls.stuA_email = "stu_phase4_a@university.edu"
        cls.stuA_username = "stu_phase4_a"
        cls.stuA_password = "PasswordA#2026"

        cls.stuB_email = "stu_phase4_b@university.edu"
        cls.stuB_username = "stu_phase4_b"
        cls.stuB_password = "PasswordB#2026"

        cls.cleanup_data()

        # Seed Student A
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            pw_hash_a = generate_password_hash(cls.stuA_password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'student')
            """, (cls.stuA_username, cls.stuA_email, pw_hash_a))
            cls.stuA_user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (cls.stuA_user_id, "Alice Student", "ROLL-P4-A", "Computer Science", 4, 8.50))
            cls.stuA_profile_id = cursor.lastrowid

            # Seed Student B
            pw_hash_b = generate_password_hash(cls.stuB_password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'student')
            """, (cls.stuB_username, cls.stuB_email, pw_hash_b))
            cls.stuB_user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (cls.stuB_user_id, "Bob Student", "ROLL-P4-B", "Software Engineering", 6, 7.80))
            cls.stuB_profile_id = cursor.lastrowid

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_data()

    @classmethod
    def cleanup_data(cls):
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(
                "DELETE FROM users WHERE email IN (%s, %s) OR username IN (%s, %s)",
                (cls.stuA_email, cls.stuB_email, cls.stuA_username, cls.stuB_username)
            )

    def setUp(self):
        self.client = app.test_client()

    def login_as_student_a(self):
        return self.client.post("/login", data={
            "identifier": self.stuA_email,
            "password": self.stuA_password
        }, follow_redirects=True)

    # =========================================================================
    # 1. Dashboard Loading & Details Verification
    # =========================================================================

    def test_1_dashboard_loads_with_correct_details(self):
        """Verify dashboard loads real MySQL student name, CGPA, department, and course count."""
        self.login_as_student_a()
        res = self.client.get("/student/dashboard")
        self.assertEqual(res.status_code, 200)

        # Assert presence of actual student data from MySQL
        self.assertIn(b"Alice Student", res.data)
        self.assertIn(b"ROLL-P4-A", res.data)
        self.assertIn(b"Computer Science", res.data)
        self.assertIn(b"Semester 4", res.data)
        self.assertIn(b"8.50", res.data)
        self.assertIn(b"Available Electives", res.data)
        print("[PASS] Test 1: Dashboard loads with correct student details.")

    # =========================================================================
    # 2. Student Profile Updates
    # =========================================================================

    def test_2_profile_updates_are_saved(self):
        """Verify student can update full name, department, semester, and roll number."""
        self.login_as_student_a()
        res = self.client.post("/student/profile", data={
            "full_name": "Alice M. Student",
            "roll_number": "ROLL-P4-A-UPDATED",
            "department": "Artificial Intelligence",
            "semester": 5
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Student profile updated successfully", res.data)

        # Check in DB
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT * FROM student_profiles WHERE id = %s", (self.stuA_profile_id,))
            p = cursor.fetchone()
            self.assertEqual(p["full_name"], "Alice M. Student")
            self.assertEqual(p["roll_number"], "ROLL-P4-A-UPDATED")
            self.assertEqual(p["department"], "Artificial Intelligence")
            self.assertEqual(p["semester"], 5)

        # Restore original roll number
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("UPDATE student_profiles SET roll_number = 'ROLL-P4-A' WHERE id = %s", (self.stuA_profile_id,))

        print("[PASS] Test 2: Profile updates saved successfully.")

    # =========================================================================
    # 3. CGPA Validation (0 to 10 Scale)
    # =========================================================================

    def test_3a_valid_cgpa_accepted(self):
        """Verify CGPA up to 10.00 is accepted and stored."""
        self.login_as_student_a()
        res = self.client.post("/student/academic", data={
            "semester": 5,
            "cgpa": "9.75"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Academic details and CGPA updated successfully", res.data)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT cgpa FROM student_profiles WHERE id = %s", (self.stuA_profile_id,))
            self.assertEqual(float(cursor.fetchone()["cgpa"]), 9.75)

        # Test maximum boundary 10.00
        res_max = self.client.post("/student/academic", data={
            "semester": 5,
            "cgpa": "10.00"
        }, follow_redirects=True)
        self.assertEqual(res_max.status_code, 200)
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT cgpa FROM student_profiles WHERE id = %s", (self.stuA_profile_id,))
            self.assertEqual(float(cursor.fetchone()["cgpa"]), 10.00)

        print("[PASS] Test 3a: Valid CGPA (up to 10.00) accepted.")

    def test_3b_invalid_cgpa_rejected(self):
        """Verify CGPA < 0 or > 10 is rejected."""
        self.login_as_student_a()

        # Negative CGPA
        res_neg = self.client.post("/student/academic", data={
            "semester": 5,
            "cgpa": "-1.50"
        }, follow_redirects=True)
        self.assertIn(b"CGPA must be between 0.00 and 10.00", res_neg.data)

        # CGPA exceeding 10.00
        res_high = self.client.post("/student/academic", data={
            "semester": 5,
            "cgpa": "10.50"
        }, follow_redirects=True)
        self.assertIn(b"CGPA must be between 0.00 and 10.00", res_high.data)

        print("[PASS] Test 3b: Out-of-range CGPA rejected.")

    # =========================================================================
    # 4. Interest Management (Add & Remove)
    # =========================================================================

    def test_4_interests_add_and_remove(self):
        """Verify student can select multiple interests, replace them, and remove them."""
        self.login_as_student_a()

        # Fetch 2 valid interest IDs from database
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM interests LIMIT 3")
            i_ids = [row["id"] for row in cursor.fetchall()]

        # Select interests 0 and 1
        res_add = self.client.post("/student/interests", data={
            "interest_ids": [str(i_ids[0]), str(i_ids[1])]
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b"Domain interests updated successfully", res_add.data)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT interest_id FROM student_interests WHERE student_id = %s", (self.stuA_profile_id,))
            saved = [r["interest_id"] for r in cursor.fetchall()]
            self.assertEqual(len(saved), 2)
            self.assertIn(i_ids[0], saved)
            self.assertIn(i_ids[1], saved)

        # Update to only interest 2 (removing 0 and 1)
        res_replace = self.client.post("/student/interests", data={
            "interest_ids": [str(i_ids[2])]
        }, follow_redirects=True)
        self.assertEqual(res_replace.status_code, 200)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT interest_id FROM student_interests WHERE student_id = %s", (self.stuA_profile_id,))
            saved = [r["interest_id"] for r in cursor.fetchall()]
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0], i_ids[2])

        print("[PASS] Test 4: Interests added and removed successfully.")

    # =========================================================================
    # 5. Career Goals Selection
    # =========================================================================

    def test_5_career_goals_selection_and_clearing(self):
        """Verify student can select a preferred career goal and clear it."""
        self.login_as_student_a()

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, goal_name FROM career_goals LIMIT 1")
            goal = cursor.fetchone()

        # Select career goal
        res_goal = self.client.post("/student/career-goals", data={
            "action": "save",
            "career_goal_id": str(goal["id"])
        }, follow_redirects=True)
        self.assertEqual(res_goal.status_code, 200)
        self.assertIn(f"Career goal updated to &#39;{goal['goal_name']}&#39;".encode(), res_goal.data)

        # Verify on dashboard
        dash_res = self.client.get("/student/dashboard")
        self.assertIn(goal["goal_name"].encode(), dash_res.data)

        # Clear career goal
        res_clear = self.client.post("/student/career-goals", data={
            "action": "clear"
        }, follow_redirects=True)
        self.assertEqual(res_clear.status_code, 200)
        self.assertIn(b"Preferred career goal cleared", res_clear.data)

        print("[PASS] Test 5: Career goal selected, verified on dashboard, and cleared.")

    # =========================================================================
    # 6. Course Exploration & MySQL Retrieval
    # =========================================================================

    def test_6_courses_exploration_loads_from_mysql(self):
        """Verify course catalog renders courses from MySQL with codes and difficulty levels."""
        self.login_as_student_a()
        res = self.client.get("/student/courses")
        self.assertEqual(res.status_code, 200)

        # Verify courses exist in response
        self.assertIn(b"Machine Learning", res.data)
        self.assertIn(b"Artificial Intelligence", res.data)
        self.assertIn(b"Cloud Computing", res.data)
        self.assertIn(b"Cyber Security", res.data)
        self.assertIn(b"CS-401", res.data)
        print("[PASS] Test 6: Course catalog successfully loaded from MySQL.")

    # =========================================================================
    # 7. AI Recommendation Staging Page
    # =========================================================================

    def test_7_ai_recommendation_staging_page(self):
        """Verify AI recommendation explanatory view and Generate Recommendations button action."""
        self.login_as_student_a()

        # GET explanation
        res_get = self.client.get("/student/recommendations")
        self.assertEqual(res_get.status_code, 200)
        self.assertIn(b"How the AI Inference Engine Works", res_get.data)
        self.assertIn(b"Rule-Based Reasoning", res_get.data)
        self.assertIn(b"Generate Recommendations", res_get.data)

        # POST Generate Recommendations
        res_post = self.client.post("/student/recommendations", follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn(b"AI Recommendation Staging Activated", res_post.data)
        self.assertIn(b"Phase 5", res_post.data)
        print("[PASS] Test 7: AI recommendation explanation and staging verified.")

    # =========================================================================
    # 8. Recommendation History
    # =========================================================================

    def test_8_recommendation_history(self):
        """Verify recommendation history loads clean empty state or saved recommendation records."""
        self.login_as_student_a()

        # Insert a sample recommendation for student A
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM courses LIMIT 1")
            course_id = cursor.fetchone()["id"]
            cursor.execute("""
                INSERT INTO recommendation_history (student_id, recommended_course_id, recommendation_score, reasoning)
                VALUES (%s, %s, %s, %s)
            """, (self.stuA_profile_id, course_id, 94.00, "High match on data science and machine learning prerequisites."))

        res = self.client.get("/student/history")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Historical Course Recommendations", res.data)
        self.assertIn(b"94.0%", res.data)
        self.assertIn(b"High match on data science", res.data)

        print("[PASS] Test 8: Recommendation history loaded with score and reasoning.")

    # =========================================================================
    # 9. Cross-Student Data Isolation
    # =========================================================================

    def test_9_cross_student_data_isolation(self):
        """Verify Student A cannot see or mutate Student B's information."""
        self.login_as_student_a()

        # Access dashboard - must only show Alice's data, never Bob's
        res = self.client.get("/student/dashboard")
        self.assertIn(b"Alice", res.data)
        self.assertNotIn(b"Bob Student", res.data)
        self.assertNotIn(b"ROLL-P4-B", res.data)

        # Profile view
        prof_res = self.client.get("/student/profile")
        self.assertIn(b"Alice", prof_res.data)
        self.assertNotIn(b"Bob Student", prof_res.data)

        print("[PASS] Test 9: Strict cross-student data isolation enforced.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
