"""
Phase 10: Authentication and Authorization Test Suite
Tests student registration, login, logout, admin auth, RBAC, and session security.
"""

import os
import sys
import unittest
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database.db_connection import get_db_cursor
from create_admin import create_admin_user


class TestAuthentication(unittest.TestCase):
    """Test suite for authentication, authorization, and route protection."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        cls.student_email = "test_auth_student@university.edu"
        cls.student_username = "test_auth_student"
        cls.student_password = "StudentPass#2026"

        cls.admin_email = "test_auth_admin@university.edu"
        cls.admin_username = "test_auth_admin"
        cls.admin_password = "AdminSuperSecret#2026"

        cls.reg_email = "test_reg_student@university.edu"
        cls.reg_username = "test_reg_student"
        cls.reg_password = "NewStudentPass@2026"

        cls.cleanup_all_test_data()

        # Seed persistent student in DB
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            pw_hash = generate_password_hash(cls.student_password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'student')
            """, (cls.student_username, cls.student_email, pw_hash))
            stu_user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (stu_user_id, "Test Student", "ROLL-AUTH-TEST", "Computer Science", 4, 3.80))

        # Seed persistent admin in DB
        create_admin_user(cls.admin_username, cls.admin_email, cls.admin_password)

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_all_test_data()

    @classmethod
    def cleanup_all_test_data(cls):
        """Cleans up all test users created in this suite."""
        with get_db_cursor(commit=True) as (cursor, _):
            cursor.execute("""
                DELETE FROM users 
                WHERE email IN (%s, %s, %s)
                   OR username IN (%s, %s, %s, 'temp_cli_admin')
            """, (
                cls.student_email, cls.admin_email, cls.reg_email,
                cls.student_username, cls.admin_username, cls.reg_username
            ))

    def setUp(self):
        self.client = app.test_client()

    def test_student_registration_success(self):
        """Test valid student registration with profile creation."""
        with get_db_cursor(commit=True) as (cursor, _):
            cursor.execute("DELETE FROM users WHERE email = %s", (self.reg_email,))

        res = self.client.post("/register", data={
            "username": self.reg_username,
            "email": self.reg_email,
            "password": self.reg_password,
            "confirm_password": self.reg_password,
            "full_name": "New Registered Student",
            "roll_number": "ROLL-REG-101",
            "department": "Computer Science",
            "semester": "3",
            "cgpa": "3.65"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Registration successful", res.data)

    def test_student_registration_duplicate_email(self):
        """Duplicate email registration is rejected."""
        res = self.client.post("/register", data={
            "username": "another_user",
            "email": self.student_email,
            "password": "ValidPass123!",
            "confirm_password": "ValidPass123!",
            "full_name": "Duplicate Student",
            "roll_number": "ROLL-DUP",
            "department": "Computer Science",
            "semester": "1",
            "cgpa": "3.0"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"already registered", res.data)

    def test_student_login_and_logout(self):
        """Test student login and logout."""
        res = self.client.post("/login", data={
            "identifier": self.student_username,
            "password": self.student_password
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome", res.data)

        # Logout
        res_out = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res_out.status_code, 200)
        self.assertIn(b"signed out", res_out.data)

    def test_admin_login(self):
        """Test admin login to admin portal."""
        res = self.client.post("/admin/login", data={
            "identifier": self.admin_username,
            "password": self.admin_password
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Admin Dashboard", res.data)

    def test_student_blocked_from_admin_dashboard(self):
        """Student cannot access admin routes."""
        self.client.post("/login", data={
            "identifier": self.student_username,
            "password": self.student_password
        }, follow_redirects=True)

        res = self.client.get("/admin/dashboard", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Unauthorized access", res.data)


if __name__ == "__main__":
    unittest.main()
