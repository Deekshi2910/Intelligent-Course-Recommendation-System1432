"""
Phase 10: Student Workflow & Dashboard Test Suite
Tests student dashboard loading, profile updating, CGPA bounds validation,
interest management, career goal selection, and course exploration.
"""

import os
import sys
import unittest
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database.db_connection import get_db_cursor


class TestStudentDashboard(unittest.TestCase):
    """Test suite for Student Dashboard functionality."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        cls.email = "test_student_flow@university.edu"
        cls.username = "test_student_flow"
        cls.password = "StudentPass#2026"

        cls.cleanup_data()

        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            pw_hash = generate_password_hash(cls.password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'student')
            """, (cls.username, cls.email, pw_hash))
            cls.user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (cls.user_id, "Workflow Student", "ROLL-WF-101", "Computer Science", 4, 8.50))
            cls.profile_id = cursor.lastrowid

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_data()

    @classmethod
    def cleanup_data(cls):
        with get_db_cursor(commit=True) as (cursor, _):
            cursor.execute("DELETE FROM users WHERE email = %s", (cls.email,))

    def setUp(self):
        self.client = app.test_client()
        self.login_student()

    def login_student(self):
        self.client.post("/login", data={
            "identifier": self.username,
            "password": self.password
        }, follow_redirects=True)

    def test_dashboard_loads_profile(self):
        """Dashboard displays student details correctly."""
        res = self.client.get("/student/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Workflow Student", res.data)
        self.assertIn(b"ROLL-WF-101", res.data)

    def test_academic_update_cgpa(self):
        """Updating CGPA within valid range 0.00-10.00 succeeds."""
        res = self.client.post("/student/academic", data={
            "semester": "5",
            "cgpa": "9.20"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Academic details and CGPA updated successfully", res.data)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT cgpa, semester FROM student_profiles WHERE id = %s", (self.profile_id,))
            row = cursor.fetchone()
            self.assertEqual(float(row["cgpa"]), 9.20)
            self.assertEqual(row["semester"], 5)

    def test_academic_update_cgpa_out_of_range(self):
        """Out of range CGPA (> 10.00 or < 0.00) is rejected."""
        res = self.client.post("/student/academic", data={
            "semester": "5",
            "cgpa": "11.50"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"CGPA must be between 0.00 and 10.00", res.data)

    def test_interest_management(self):
        """Student can select and update technical interests."""
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM interests LIMIT 2")
            rows = cursor.fetchall()
            interest_ids = [str(r["id"]) for r in rows]

        res_update = self.client.post("/student/interests", data={
            "interest_ids": interest_ids
        }, follow_redirects=True)
        self.assertEqual(res_update.status_code, 200)
        self.assertIn(b"Domain interests updated successfully", res_update.data)

    def test_career_goal_selection(self):
        """Student can select and clear target career goal."""
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, goal_name FROM career_goals LIMIT 1")
            goal = cursor.fetchone()

        # Set goal
        res_set = self.client.post("/student/career-goals", data={
            "action": "save",
            "career_goal_id": goal["id"]
        }, follow_redirects=True)
        self.assertEqual(res_set.status_code, 200)
        self.assertIn(b"Career goal updated", res_set.data)

        # Clear goal
        res_clear = self.client.post("/student/career-goals", data={
            "action": "clear"
        }, follow_redirects=True)
        self.assertEqual(res_clear.status_code, 200)
        self.assertIn(b"Preferred career goal cleared", res_clear.data)

    def test_explore_courses(self):
        """Student can explore active courses."""
        res = self.client.get("/student/courses")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Explore Elective Courses", res.data)


if __name__ == "__main__":
    unittest.main()
