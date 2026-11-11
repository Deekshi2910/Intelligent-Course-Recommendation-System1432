"""
Phase 10: Default Reasoning Test Suite
Validates non-monotonic default reasoning (DR01 - DR05), working hypotheses tracking,
and belief revision upon receiving updated student information.
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_engine.default_rules import DefaultRule, DefaultRuleManager, CANONICAL_DEFAULT_RULES
from ai_engine.assumption_manager import AssumptionManager
from ai_engine.default_reasoning import DefaultReasoningEngine, infer_with_defaults
from ai_engine.knowledge_base import KnowledgeBase


class TestDefaultReasoning(unittest.TestCase):
    """Test suite for Non-Monotonic Default Reasoning."""

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()
        cls.engine = DefaultReasoningEngine()

    def test_dr01_missing_career_goal(self):
        """DR01: Missing career goal triggers interest-based fallback."""
        data = {
            "cgpa": 8.00,
            "interests": ["Machine Learning"],
            "career_goal": ""
        }
        res = self.engine.evaluate(data, knowledge_base=self.kb)
        self.assertIn("DR01", res["applied_default_rules"])
        self.assertGreater(res["total_recommended"], 0)

    def test_dr02_missing_interests(self):
        """DR02: Missing interests triggers career-based fallback."""
        data = {
            "cgpa": 8.00,
            "interests": [],
            "career_goal": "Data Scientist"
        }
        res = self.engine.evaluate(data, knowledge_base=self.kb)
        self.assertIn("DR02", res["applied_default_rules"])
        self.assertGreater(res["total_recommended"], 0)

    def test_dr03_missing_both(self):
        """DR03: Missing both triggers general foundational breadth."""
        data = {
            "cgpa": 8.00,
            "interests": [],
            "career_goal": ""
        }
        res = self.engine.evaluate(data, knowledge_base=self.kb)
        self.assertIn("DR03", res["applied_default_rules"])
        self.assertGreater(res["total_recommended"], 0)

    def test_dr04_missing_cgpa_never_assumed(self):
        """DR04: Missing CGPA prompts for academic info; CGPA is never assumed."""
        data = {
            "cgpa": None,
            "interests": ["Machine Learning"],
            "career_goal": "Data Scientist"
        }
        res = self.engine.evaluate(data, knowledge_base=self.kb)
        self.assertIn("DR04", res["applied_default_rules"])
        self.assertTrue(res["academic_info_required"])

    def test_dr05_unknown_prerequisites_unverified(self):
        """DR05: Unknown prerequisites are never assumed satisfied; marked unverified."""
        data = {
            "cgpa": 8.00,
            "interests": ["Machine Learning"],
            "career_goal": "Data Scientist",
            "completed_courses": None
        }
        res = self.engine.evaluate(data, knowledge_base=self.kb)
        self.assertTrue(res["unverified_prerequisites_found"])

    def test_assumption_withdrawal(self):
        """Actual student data withdraws and overrides prior default assumptions."""
        mgr = AssumptionManager()
        mgr.record_assumption("career_goal", "Data Scientist", "DR01 fallback", "DR01")
        self.assertEqual(len(mgr.get_active_assumptions()), 1)

        # Actual career goal observed
        retracted = mgr.reconcile_with_actual_data({"career_goal": "Cybersecurity Analyst"})
        self.assertEqual(len(retracted), 1)
        self.assertEqual(len(mgr.get_active_assumptions()), 0)


if __name__ == "__main__":
    unittest.main()
