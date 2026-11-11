"""
Comprehensive Phase 3 Authentication & Authorization Test Suite
Validates student registration, student login, admin creation, admin login,
session protection, role authorization, and cache-control headers.
"""

import os
import sys
import unittest
from werkzeug.security import generate_password_hash, check_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from database.db_connection import get_db_cursor
from create_admin import create_admin_user


class AuthenticationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment and persistent test accounts."""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        # Persistent credentials for login & authorization tests
        cls.student_email = "perm_student_p3@university.edu"
        cls.student_username = "perm_student_p3"
        cls.student_password = "StudentPass#2026"

        cls.admin_email = "perm_admin_p3@university.edu"
        cls.admin_username = "perm_admin_p3"
        cls.admin_password = "AdminSuperSecret#2026"

        # Dedicated credentials for registration tests
        cls.reg_email = "new_registered_student@university.edu"
        cls.reg_username = "new_reg_student"
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
            """, (stu_user_id, "Persistent Student", "ROLL-PERM-P3", "Computer Science", 4, 3.80))

        # Seed persistent admin in DB
        create_admin_user(cls.admin_username, cls.admin_email, cls.admin_password)

    @classmethod
    def tearDownClass(cls):
        """Purge all test records upon suite completion."""
        cls.cleanup_all_test_data()

    @classmethod
    def cleanup_all_test_data(cls):
        """Remove all test accounts from database."""
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("""
                DELETE FROM users 
                WHERE email IN (%s, %s, %s) OR username IN (%s, %s, %s)
            """, (
                cls.student_email, cls.admin_email, cls.reg_email,
                cls.student_username, cls.admin_username, cls.reg_username
            ))

    def setUp(self):
        """Ensure every individual test gets a fresh test client and session."""
        self.client = app.test_client()

    # =========================================================================
    # A. STUDENT TESTS
    # =========================================================================

    def test_A1_student_registration_success(self):
        """Verify student registers successfully and profile is created."""
        response = self.client.post("/register", data={
            "full_name": "New Enrolled Student",
            "username": self.reg_username,
            "email": self.reg_email,
            "password": self.reg_password,
            "confirm_password": self.reg_password,
            "roll_number": "ROLL-REG-101",
            "department": "Computer Science",
            "semester": 3,
            "cgpa": 3.70
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Registration successful", response.data)

        # Verify DB records
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, username, email, password_hash, role FROM users WHERE username = %s", (self.reg_username,))
            user = cursor.fetchone()
            self.assertIsNotNone(user)
            self.assertEqual(user["role"], "student")
            self.assertTrue(check_password_hash(user["password_hash"], self.reg_password))

            cursor.execute("SELECT * FROM student_profiles WHERE user_id = %s", (user["id"],))
            profile = cursor.fetchone()
            self.assertIsNotNone(profile)
            self.assertEqual(profile["full_name"], "New Enrolled Student")
            self.assertEqual(profile["roll_number"], "ROLL-REG-101")
            self.assertEqual(float(profile["cgpa"]), 3.70)
        print("[PASS] Test A1: Student registered successfully with profile.")

    def test_A2_student_registration_duplicate_email_rejected(self):
        """Verify rejection of registration when email already exists."""
        response = self.client.post("/register", data={
            "full_name": "Duplicate Student",
            "username": "unique_username_999",
            "email": self.student_email,  # Existing email
            "password": "Password123",
            "confirm_password": "Password123",
            "department": "Computer Science",
            "semester": 2,
            "cgpa": 3.00
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Email is already registered", response.data)
        print("[PASS] Test A2: Duplicate email correctly rejected.")

    def test_A3_student_registration_password_mismatch_rejected(self):
        """Verify rejection when confirm password does not match."""
        response = self.client.post("/register", data={
            "full_name": "Mismatch Student",
            "username": "mismatch_user_888",
            "email": "mismatch@example.com",
            "password": "Password123",
            "confirm_password": "DifferentPassword456",
            "department": "Computer Science",
            "semester": 1,
            "cgpa": 3.00
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Passwords do not match", response.data)
        print("[PASS] Test A3: Password mismatch correctly rejected.")

    def test_A4_student_login_invalid_credentials_rejected(self):
        """Verify login rejection with incorrect password."""
        response = self.client.post("/login", data={
            "identifier": self.student_email,
            "password": "WrongPassword999"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email/username or password", response.data)
        print("[PASS] Test A4: Invalid credentials rejected.")

    def test_A5_student_login_and_dashboard_success(self):
        """Verify student logs in successfully and accesses student dashboard."""
        response = self.client.post("/login", data={
            "identifier": self.student_email,
            "password": self.student_password
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back", response.data)
        self.assertIn(b"Student Dashboard", response.data)
        self.assertIn(b"Persistent Student", response.data)

        # Subsequent direct access to dashboard within same session
        dash_res = self.client.get("/student/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Academic Profile", dash_res.data)
        self.assertIn(b"ROLL-PERM-P3", dash_res.data)
        print("[PASS] Test A5: Student logged in and accessed student dashboard.")

    def test_A6_student_logout_success(self):
        """Verify logout clears session and subsequent protected access redirects."""
        # Sign in
        self.client.post("/login", data={
            "identifier": self.student_email,
            "password": self.student_password
        }, follow_redirects=True)

        # Log out
        logout_res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b"You have been signed out successfully", logout_res.data)

        # Revisit protected page after logout
        protected_res = self.client.get("/student/dashboard")
        self.assertEqual(protected_res.status_code, 302)
        self.assertIn("/login", protected_res.headers.get("Location", ""))
        print("[PASS] Test A6: Logout successful and post-logout access blocked.")

    # =========================================================================
    # B. ADMIN TESTS
    # =========================================================================

    def test_B1_admin_account_creation_via_utility(self):
        """Verify admin account can be created via utility script."""
        temp_admin = "temp_cli_admin"
        temp_email = "temp_cli_admin@university.edu"
        temp_pw = "TempAdminPass#2026"

        admin_id = create_admin_user(temp_admin, temp_email, temp_pw)
        self.assertIsNotNone(admin_id)

        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("SELECT role, password_hash FROM users WHERE id = %s", (admin_id,))
            admin = cursor.fetchone()
            self.assertEqual(admin["role"], "admin")
            self.assertTrue(check_password_hash(admin["password_hash"], temp_pw))
            # Cleanup temp admin
            cursor.execute("DELETE FROM users WHERE id = %s", (admin_id,))

        print("[PASS] Test B1: Admin account created successfully via utility.")

    def test_B2_admin_login_invalid_credentials_rejected(self):
        """Verify rejection of incorrect admin credentials."""
        response = self.client.post("/admin/login", data={
            "identifier": self.admin_username,
            "password": "IncorrectAdminPassword"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid administrator credentials", response.data)
        print("[PASS] Test B2: Incorrect admin credentials rejected.")

    def test_B3_admin_login_and_dashboard_success(self):
        """Verify admin logs in and accesses admin dashboard."""
        response = self.client.post("/admin/login", data={
            "identifier": self.admin_username,
            "password": self.admin_password
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome, Administrator", response.data)
        self.assertIn(b"Admin Dashboard", response.data)
        self.assertIn(b"Total Students", response.data)
        self.assertIn(b"Active Courses", response.data)

        # Subsequent direct access to admin dashboard
        dash_res = self.client.get("/admin/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Elective Courses Catalog", dash_res.data)
        self.assertIn(b"Inference Engine Knowledge Rules", dash_res.data)
        print("[PASS] Test B3: Admin login and dashboard access successful.")

    # =========================================================================
    # C. AUTHORIZATION & ACCESS CONTROL TESTS
    # =========================================================================

    def test_C1_student_cannot_access_admin_dashboard(self):
        """Verify student is forbidden from accessing admin dashboard."""
        # Login as student
        self.client.post("/login", data={
            "identifier": self.student_email,
            "password": self.student_password
        }, follow_redirects=True)

        # Attempt to access admin dashboard
        res = self.client.get("/admin/dashboard", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Unauthorized access", res.data)
        self.assertNotIn(b"Inference Engine Knowledge Rules", res.data)
        print("[PASS] Test C1: Student blocked from admin dashboard.")

    def test_C2_admin_cannot_access_student_dashboard(self):
        """Verify administrator cannot access student-only dashboard."""
        # Login as admin
        self.client.post("/admin/login", data={
            "identifier": self.admin_username,
            "password": self.admin_password
        }, follow_redirects=True)

        # Attempt to access student dashboard
        res = self.client.get("/student/dashboard", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Unauthorized access", res.data)
        self.assertNotIn(b"Academic Profile", res.data)
        print("[PASS] Test C2: Admin blocked from student-only dashboard.")

    def test_C3_student_cannot_login_through_admin_portal(self):
        """Verify student cannot authenticate through /admin/login."""
        response = self.client.post("/admin/login", data={
            "identifier": self.student_email,
            "password": self.student_password
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Access denied. This account does not possess administrator privileges", response.data)
        print("[PASS] Test C3: Student blocked from authenticating via admin portal.")

    def test_C4_unauthenticated_cannot_access_protected_pages(self):
        """Verify unauthenticated requests are redirected."""
        res_stu = self.client.get("/student/dashboard")
        self.assertEqual(res_stu.status_code, 302)
        self.assertIn("/login", res_stu.headers.get("Location", ""))

        res_adm = self.client.get("/admin/dashboard")
        self.assertEqual(res_adm.status_code, 302)
        self.assertIn("/admin/login", res_adm.headers.get("Location", ""))
        print("[PASS] Test C4: Unauthenticated access redirected to respective login pages.")

    def test_C5_cache_control_headers_on_protected_pages(self):
        """Verify no-cache headers are set on protected responses to prevent browser back-button caching."""
        self.client.post("/login", data={
            "identifier": self.student_email,
            "password": self.student_password
        }, follow_redirects=True)

        res = self.client.get("/student/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn("no-store", res.headers.get("Cache-Control", ""))
        self.assertIn("no-cache", res.headers.get("Cache-Control", ""))
        print("[PASS] Test C5: Security Cache-Control headers verified on protected responses.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
