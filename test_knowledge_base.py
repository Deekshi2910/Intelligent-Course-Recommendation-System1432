"""
Phase 6 AI Knowledge Base Comprehensive Test Suite
Validates:
1. Knowledge Base initialization and CourseKnowledgeFact data modeling.
2. Course retrieval by ID, code, and active/inactive status.
3. Domain interest retrieval.
4. Career goal retrieval.
5. Course-interest mapping and interest-filtered queries.
6. Course-career goal mapping and career-filtered queries.
7. CGPA eligibility filtering.
8. Textual and structured prerequisite retrieval.
9. KnowledgeValidator anomaly, bounds, and missing field detection.
10. Duplicate relationship prevention and idempotency.
11. Self-referential prerequisite rejection.
12. Database connection failure resilience and error handling.
"""

import os
import sys
import unittest
from unittest.mock import patch
from mysql.connector import Error

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from ai_engine import (
    KnowledgeBase,
    CourseKnowledgeFact,
    KnowledgeRepository,
    KnowledgeValidator,
    KnowledgeLoader
)
from database.db_connection import get_db_cursor


class KnowledgeBaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        # Ensure canonical knowledge is loaded
        KnowledgeLoader.load_canonical_knowledge()

        cls.kb = KnowledgeBase()
        cls.repo = KnowledgeRepository()
        cls.validator = KnowledgeValidator()

    def setUp(self):
        self.kb.reload()

    # =========================================================================
    # 1. Knowledge Base Initialization
    # =========================================================================

    def test_1_kb_initialization(self):
        """Verifies Knowledge Base initializes and creates CourseKnowledgeFact instances."""
        courses = self.kb.get_all_courses(active_only=False)
        self.assertGreaterEqual(len(courses), 10)
        self.assertIsInstance(courses[0], CourseKnowledgeFact)

        sample = courses[0]
        self.assertTrue(hasattr(sample, "course_code"))
        self.assertTrue(hasattr(sample, "minimum_cgpa"))
        self.assertTrue(hasattr(sample, "interests"))
        self.assertTrue(hasattr(sample, "career_goals"))
        self.assertTrue(hasattr(sample, "prerequisite_courses"))

        d = sample.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["course_code"], sample.course_code)
        print("\n[PASS] Test 1: Knowledge Base initialized with structured CourseKnowledgeFacts.")

    # =========================================================================
    # 2. Course Retrieval (All, ID, Code)
    # =========================================================================

    def test_2_course_retrieval(self):
        """Tests course retrieval by ID, course code, and active filtering."""
        all_active = self.kb.get_all_courses(active_only=True)
        self.assertGreaterEqual(len(all_active), 10)

        # Retrieve by code
        ml_course = self.kb.get_course_by_code("CS-401")
        self.assertIsNotNone(ml_course)
        self.assertEqual(ml_course.course_name, "Machine Learning")

        # Retrieve by ID
        by_id = self.kb.get_course_by_id(ml_course.course_id)
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id.course_code, "CS-401")

        # Non-existent course
        none_course = self.kb.get_course_by_code("NONEXISTENT-999")
        self.assertIsNone(none_course)
        print("[PASS] Test 2: Course retrieval by ID, code, and active status verified.")

    # =========================================================================
    # 3. Domain Interest Retrieval
    # =========================================================================

    def test_3_interest_retrieval(self):
        """Verifies retrieval of all domain interests."""
        interests = self.kb.get_all_interests()
        self.assertGreaterEqual(len(interests), 10)

        names = [i["interest_name"] for i in interests]
        self.assertIn("Python Programming", names)
        self.assertIn("Machine Learning", names)
        self.assertIn("Cloud Technology", names)
        self.assertIn("Cyber Security", names)
        print("[PASS] Test 3: Domain interests retrieved successfully from Knowledge Base.")

    # =========================================================================
    # 4. Career Goal Retrieval
    # =========================================================================

    def test_4_career_goal_retrieval(self):
        """Verifies retrieval of all career opportunities and pathways."""
        goals = self.kb.get_all_career_goals()
        self.assertGreaterEqual(len(goals), 8)

        goal_names = [g["goal_name"] for g in goals]
        self.assertIn("Data Scientist", goal_names)
        self.assertIn("AI Engineer", goal_names)
        self.assertIn("Cloud Engineer", goal_names)
        self.assertIn("Cyber Security Analyst", goal_names)
        print("[PASS] Test 4: Career goals retrieved successfully from Knowledge Base.")

    # =========================================================================
    # 5. Course-Interest Mapping
    # =========================================================================

    def test_5_course_interest_mapping(self):
        """Tests filtering courses by domain interests."""
        ml_courses = self.kb.get_courses_by_interest("Machine Learning")
        self.assertGreater(len(ml_courses), 0)
        codes = [c.course_code for c in ml_courses]
        self.assertIn("CS-401", codes)

        py_courses = self.kb.get_courses_by_interest("Python Programming")
        self.assertGreater(len(py_courses), 0)
        py_codes = [c.course_code for c in py_courses]
        self.assertIn("CS-401", py_codes)
        self.assertIn("CS-402", py_codes)
        print("[PASS] Test 5: Course-interest ontological mappings verified.")

    # =========================================================================
    # 6. Course-Career Goal Mapping
    # =========================================================================

    def test_6_course_career_mapping(self):
        """Tests filtering courses by aligned career pathways."""
        ds_courses = self.kb.get_courses_by_career_goal("Data Scientist")
        self.assertGreater(len(ds_courses), 0)
        ds_codes = [c.course_code for c in ds_courses]
        self.assertIn("CS-401", ds_codes)  # Machine Learning aligns with Data Scientist

        sec_courses = self.kb.get_courses_by_career_goal("Cyber Security Analyst")
        self.assertGreater(len(sec_courses), 0)
        sec_codes = [c.course_code for c in sec_courses]
        self.assertIn("CS-405", sec_codes)  # Cyber Security aligns with Cyber Security Analyst
        print("[PASS] Test 6: Course-career pathway mappings verified.")

    # =========================================================================
    # 7. CGPA Eligibility Retrieval
    # =========================================================================

    def test_7_cgpa_eligibility_retrieval(self):
        """Tests course retrieval conditioned upon minimum CGPA requirements."""
        # Low CGPA should match fewer courses than high CGPA
        courses_low = self.kb.get_courses_by_cgpa(2.10)
        courses_high = self.kb.get_courses_by_cgpa(3.50)

        self.assertGreaterEqual(len(courses_high), len(courses_low))

        # Deep Learning requires min_cgpa 3.00
        dl = self.kb.get_course_by_code("CS-406")
        if dl:
            self.assertFalse(dl.is_eligible(2.10))
            self.assertTrue(dl.is_eligible(3.20))

        print("[PASS] Test 7: CGPA academic eligibility bounds verified.")

    # =========================================================================
    # 8. Prerequisite Retrieval
    # =========================================================================

    def test_8_prerequisite_retrieval(self):
        """Verifies textual and structured prerequisite course dependencies."""
        prereqs_dl = self.kb.get_course_prerequisites("CS-406")
        self.assertIsNotNone(prereqs_dl["course"])
        self.assertIn("Machine Learning", prereqs_dl["prerequisites_text"])

        # Structured prerequisite should link to CS-401
        prereq_codes = [p["course_code"] for p in prereqs_dl["prerequisite_courses"]]
        self.assertIn("CS-401", prereq_codes)

        # Computer Vision requires CS-401 and CS-402
        prereqs_cv = self.kb.get_course_prerequisites("CS-409")
        cv_codes = [p["course_code"] for p in prereqs_cv["prerequisite_courses"]]
        self.assertIn("CS-401", cv_codes)
        print("[PASS] Test 8: Structured and textual prerequisite resolution verified.")

    # =========================================================================
    # 9. Knowledge Validation & Anomaly Detection
    # =========================================================================

    def test_9_invalid_knowledge_detection(self):
        """Verifies KnowledgeValidator identifies missing fields and out-of-range values."""
        # 1. Missing Code & Name
        bad_course_1 = {
            "course_code": "",
            "course_name": "",
            "minimum_cgpa": 2.5,
            "difficulty_level": "Intermediate"
        }
        res1 = self.validator.validate_course_dict(bad_course_1)
        self.assertFalse(res1["is_valid"])
        self.assertTrue(any("code" in e.lower() for e in res1["errors"]))
        self.assertTrue(any("title" in e.lower() for e in res1["errors"]))

        # 2. Invalid CGPA (> 10.0 or < 0.0 or non-numeric)
        bad_course_2 = {
            "course_code": "TEST-ERR",
            "course_name": "Test Error Course",
            "minimum_cgpa": 12.5,  # Out of range
            "difficulty_level": "Intermediate"
        }
        res2 = self.validator.validate_course_dict(bad_course_2)
        self.assertFalse(res2["is_valid"])
        self.assertTrue(any("cgpa" in e.lower() for e in res2["errors"]))

        # 3. Invalid Difficulty Level
        bad_course_3 = {
            "course_code": "TEST-ERR-2",
            "course_name": "Test Error Course 2",
            "minimum_cgpa": 2.5,
            "difficulty_level": "ImpossibleLevel"
        }
        res3 = self.validator.validate_course_dict(bad_course_3)
        self.assertFalse(res3["is_valid"])
        self.assertTrue(any("difficulty" in e.lower() for e in res3["errors"]))

        # 4. Live Database Audit
        audit = self.kb.validate_knowledge_base()
        self.assertIn(audit["status"], ["HEALTHY", "WARNING"])
        self.assertEqual(audit["errors_count"], 0)
        print("[PASS] Test 9: Knowledge validation and anomaly detection verified.")

    # =========================================================================
    # 10. Duplicate Relationship Prevention
    # =========================================================================

    def test_10_duplicate_relationship_prevention(self):
        """Verifies that duplicate M:N relationships are prevented safely."""
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM courses LIMIT 1")
            course_id = cursor.fetchone()["id"]

            cursor.execute("SELECT id FROM interests LIMIT 1")
            interest_id = cursor.fetchone()["id"]

        # First addition (or existing)
        self.repo.add_course_interest(course_id, interest_id)

        # Duplicate addition attempt should be ignored safely (returns False for no new rows)
        is_new = self.repo.add_course_interest(course_id, interest_id)
        self.assertFalse(is_new)

        # Verify exactly one record in DB
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM course_interests
                WHERE course_id = %s AND interest_id = %s
            """, (course_id, interest_id))
            self.assertEqual(cursor.fetchone()["cnt"], 1)

        print("[PASS] Test 10: Duplicate relationship prevention and idempotency verified.")

    # =========================================================================
    # 11. Self-Prerequisite Prevention
    # =========================================================================

    def test_11_self_prerequisite_prevention(self):
        """Verifies rejection of self-referencing prerequisite dependencies."""
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM courses LIMIT 1")
            cid = cursor.fetchone()["id"]

        with self.assertRaises(ValueError):
            self.repo.add_course_prerequisite(cid, cid)

        print("[PASS] Test 11: Self-referential prerequisite constraint strictly enforced.")

    # =========================================================================
    # 12. Database Connection Resilience
    # =========================================================================

    def test_12_database_connection_resilience(self):
        """Verifies graceful exception handling when a database query fails."""
        with patch("ai_engine.knowledge_repository.get_db_cursor") as mock_cursor:
            mock_cursor.side_effect = Error("Simulated MySQL connection drop")

            # Repository should let error bubble or handle appropriately
            with self.assertRaises(Error):
                self.repo.get_all_courses()

        print("[PASS] Test 12: Database connection failure resilience verified.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
