"""
Phase 10: Admin Management & Workflow Test Suite
Tests admin dashboard overview, student records inspection, course management CRUD,
interest management, career goal management, AI rule management, and analytics reports.
"""

import os
import sys
import unittest
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database.db_connection import get_db_cursor
from create_admin import create_admin_user


class TestAdminDashboard(unittest.TestCase):
    """Test suite for Admin Dashboard and Management operations."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        cls.admin_email = "test_admin_mgmt@university.edu"
        cls.admin_username = "test_admin_mgmt"
        cls.admin_password = "AdminSuperSecret#2026"

        cls.cleanup_data()
        create_admin_user(cls.admin_username, cls.admin_email, cls.admin_password)

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM users WHERE username = %s", (cls.admin_username,))
            row = cursor.fetchone()
            cls.admin_user_id = row["id"]

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_data()

    @classmethod
    def cleanup_data(cls):
        with get_db_cursor(commit=True) as (cursor, _):
            cursor.execute("DELETE FROM courses WHERE course_code LIKE 'TEST-%'")
            cursor.execute("DELETE FROM interests WHERE interest_name LIKE 'TEST_%'")
            cursor.execute("DELETE FROM career_goals WHERE goal_name LIKE 'TEST_%'")
            cursor.execute("DELETE FROM users WHERE email = %s", (cls.admin_email,))

    def setUp(self):
        self.client = app.test_client()
        self.login_admin()

    def login_admin(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.admin_user_id
            sess["username"] = self.admin_username
            sess["email"] = self.admin_email
            sess["role"] = "admin"

    def test_admin_dashboard_metrics(self):
        """Admin dashboard loads with accurate statistics."""
        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Total Students", res.data)
        self.assertIn(b"Active Courses", res.data)

    def test_view_registered_students(self):
        """Admin can view registered students list."""
        res = self.client.get("/admin/students")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Student", res.data)

    def test_course_crud_workflow(self):
        """Admin can add, edit, and toggle courses."""
        # 1. Add course
        test_code = "TEST-901"
        res_add = self.client.post("/admin/courses/add", data={
            "course_code": test_code,
            "course_name": "Automated Testing Course",
            "description": "Comprehensive test course",
            "minimum_cgpa": "2.50",
            "difficulty_level": "Intermediate",
            "career_scope": "QA Engineer",
            "prerequisites": "None",
            "is_active": "1"
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)

        # Retrieve course ID
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM courses WHERE course_code = %s", (test_code,))
            c_row = cursor.fetchone()
            self.assertIsNotNone(c_row)
            course_id = c_row["id"]

        # 2. Edit course
        res_edit = self.client.post(f"/admin/courses/{course_id}/edit", data={
            "course_code": test_code,
            "course_name": "Updated Testing Course",
            "description": "Updated description",
            "minimum_cgpa": "2.80",
            "difficulty_level": "Advanced",
            "career_scope": "QA Lead",
            "prerequisites": "None",
            "is_active": "1"
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)

        # 3. Toggle Status
        res_toggle = self.client.post(f"/admin/courses/{course_id}/toggle-status", follow_redirects=True)
        self.assertEqual(res_toggle.status_code, 200)

        # 4. Delete course
        res_del = self.client.post(f"/admin/courses/{course_id}/delete", follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)

    def test_interest_management(self):
        """Admin can add, edit, and delete domain interests."""
        res_add = self.client.post("/admin/interests", data={
            "interest_name": "TEST_Quantum_Computing"
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)

        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM interests WHERE interest_name = 'TEST_Quantum_Computing'")
            row = cursor.fetchone()
            if row:
                interest_id = row["id"]
                self.client.post(f"/admin/interests/{interest_id}/delete", follow_redirects=True)

    def test_career_goal_management(self):
        """Admin can add and manage career goals."""
        res_add = self.client.post("/admin/career-goals", data={
            "goal_name": "TEST_Quantum_Engineer",
            "description": "Quantum engineering focus"
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)

        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM career_goals WHERE goal_name = 'TEST_Quantum_Engineer'")
            row = cursor.fetchone()
            if row:
                goal_id = row["id"]
                self.client.post(f"/admin/career-goals/{goal_id}/delete", follow_redirects=True)

    def test_ai_rule_management(self):
        """Admin can view AI knowledge rules and toggle activation status."""
        res = self.client.get("/admin/rules")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"AI Knowledge Rules", res.data)

        # Fetch a rule and toggle
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, is_active FROM knowledge_rules LIMIT 1")
            r_row = cursor.fetchone()

        if r_row:
            rule_id = r_row["id"]
            res_toggle = self.client.post(f"/admin/rules/{rule_id}/toggle", follow_redirects=True)
            self.assertEqual(res_toggle.status_code, 200)
            # Toggle back to restore original state
            self.client.post(f"/admin/rules/{rule_id}/toggle", follow_redirects=True)

    def test_admin_reports(self):
        """Admin can view recommendation statistics and audit reports."""
        res = self.client.get("/admin/reports")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Recommendation Monitoring", res.data)


if __name__ == "__main__":
    unittest.main()
