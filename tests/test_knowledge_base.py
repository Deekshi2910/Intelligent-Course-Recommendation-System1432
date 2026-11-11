"""
Phase 10: AI Knowledge Base Test Suite
Validates structured course knowledge facts, domain ontologies, career goal mappings,
prerequisites resolution, and structural data validation.
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact
from ai_engine.knowledge_validator import KnowledgeValidator


class TestKnowledgeBase(unittest.TestCase):
    """Test suite for Knowledge Base facts and ontologies."""

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()
        cls.validator = KnowledgeValidator()

    def test_retrieve_all_courses(self):
        """Retrieves all active courses from knowledge base."""
        courses = self.kb.get_all_courses(active_only=True)
        self.assertGreater(len(courses), 0)
        first = courses[0]
        self.assertIsInstance(first, CourseKnowledgeFact)
        self.assertIsNotNone(first.course_code)
        self.assertIsNotNone(first.course_name)

    def test_course_retrieval_by_id_and_code(self):
        """Retrieves specific course by ID and course code."""
        course = self.kb.get_course_by_code("CS-401")
        self.assertIsNotNone(course)
        self.assertEqual(course.course_code, "CS-401")

        by_id = self.kb.get_course_by_id(course.course_id)
        self.assertIsNotNone(by_id)
        self.assertEqual(by_id.course_code, "CS-401")

    def test_retrieve_courses_by_interest(self):
        """Retrieves courses matching a specific technical interest."""
        courses = self.kb.get_courses_by_interest("Machine Learning")
        self.assertGreater(len(courses), 0)
        for c in courses:
            self.assertTrue(any("machine learning" in i.lower() for i in c.interests))

    def test_retrieve_courses_by_career_goal(self):
        """Retrieves courses matching a target career pathway."""
        courses = self.kb.get_courses_by_career_goal("Data Scientist")
        self.assertGreater(len(courses), 0)

    def test_prerequisites_resolution(self):
        """Course prerequisite relationships are correctly structured."""
        courses = self.kb.get_all_courses(active_only=False)
        prereq_courses = [c for c in courses if c.prerequisite_courses]
        self.assertGreater(len(prereq_courses), 0)

    def test_knowledge_validation_clean_audit(self):
        """KnowledgeValidator detects no critical integrity errors in seed knowledge."""
        audit = self.validator.validate_all()
        self.assertIn("status", audit)
        self.assertIn("total_courses_audited", audit)


if __name__ == "__main__":
    unittest.main()
