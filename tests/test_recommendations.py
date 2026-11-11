"""
Phase 10: End-to-End Recommendations Workflow & Persistence Test Suite
Tests the complete 18-step student recommendation lifecycle:
Profile retrieval -> Inference -> Forward Chaining -> Default Reasoning ->
Eligibility -> Scoring -> Ranking -> XAI -> MySQL Persistence -> History view.
"""

import os
import sys
import unittest
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database.db_connection import get_db_cursor
from ai_engine.inference_engine import InferenceEngine


class TestRecommendationsWorkflow(unittest.TestCase):
    """End-to-end integration test suite for the full recommendation workflow."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        cls.email = "test_rec_workflow@university.edu"
        cls.username = "test_rec_workflow"
        cls.password = "StudentPass#2026"

        cls.cleanup_data()

        # Seed student in DB with profile and interests
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
            """, (cls.user_id, "End-to-End Student", "ROLL-E2E-101", "Computer Science", 6, 8.80))
            cls.profile_id = cursor.lastrowid

            # Add Machine Learning interest
            cursor.execute("SELECT id FROM interests WHERE interest_name = 'Machine Learning' LIMIT 1")
            i_row = cursor.fetchone()
            if i_row:
                cursor.execute("""
                    INSERT INTO student_interests (student_id, interest_id)
                    VALUES (%s, %s)
                """, (cls.profile_id, i_row["id"]))

            # Set Career Goal to Data Scientist
            cursor.execute("SELECT id FROM career_goals WHERE goal_name = 'Data Scientist' LIMIT 1")
            g_row = cursor.fetchone()
            if g_row:
                cursor.execute("""
                    UPDATE student_profiles SET career_goal_id = %s WHERE id = %s
                """, (g_row["id"], cls.profile_id))

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

    def test_complete_recommendation_lifecycle(self):
        """
        Executes and verifies steps 1 to 18 of the complete student workflow:
        1. Open AI recommendations interface (GET).
        2. Click 'Generate Recommendations' (POST).
        3. Inference engine derives conclusions, scores, ranks, and persists.
        4. Recommendations saved in MySQL recommendation_history.
        5. Student views recommendation history.
        """
        # Step 7: Open AI Recommendations
        res_get = self.client.get("/student/recommendations")
        self.assertEqual(res_get.status_code, 200)
        self.assertIn(b"Intelligent Course Recommendations", res_get.data)
        self.assertIn(b"Generate AI Recommendations", res_get.data)

        # Step 8: Click Generate Recommendations (POST)
        res_post = self.client.post("/student/recommendations", follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)

        # Steps 9-16: Display ranked recommendations, scores, and XAI justifications
        self.assertIn(b"Suitability Score", res_post.data)
        self.assertIn(b"AI Recommendation Rationale", res_post.data)

        # Step 17: Verify records saved in MySQL recommendation_history
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT rh.id, rh.recommendation_score, rh.reasoning, c.course_code
                FROM recommendation_history rh
                JOIN courses c ON rh.recommended_course_id = c.id
                WHERE rh.student_id = %s
            """, (self.profile_id,))
            saved_records = cursor.fetchall()

        self.assertGreater(len(saved_records), 0)
        first_rec = saved_records[0]
        self.assertGreater(float(first_rec["recommendation_score"]), 0.0)
        self.assertTrue(len(first_rec["reasoning"]) > 10)

        # Step 18: Student views recommendation history (/student/history)
        res_hist = self.client.get("/student/history")
        self.assertEqual(res_hist.status_code, 200)
        self.assertIn(first_rec["course_code"].encode("utf-8"), res_hist.data)


if __name__ == "__main__":
    unittest.main()
