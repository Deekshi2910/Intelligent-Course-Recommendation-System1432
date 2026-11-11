"""
Comprehensive Test Suite for Phase 8: Default Reasoning Engine
Validates:
Test A: Complete student information (pure rule-based reasoning, no default needed)
Test B: Missing career goal (DR01: interest-based fallback)
Test C: Missing interests (DR02: career-based fallback)
Test D: Missing interests and career goal (DR03: general foundational recommendations)
Test E: Missing CGPA (DR04: never assumed, requests academic info)
Test F: Unknown prerequisites (DR05: never assumed satisfied, marked unverified)
Test G: Newly provided career goal (overrides default assumptions)
Test H: Newly provided interests (overrides default assumptions)
Test I: Assumption withdrawal (retraction and non-monotonic belief revision)
Test J: Recommendation regeneration upon profile preference update
Test K: Inactive courses exclusion
Test L: Minimum CGPA eligibility enforcement in default modes
Test M: Admin default rule management & toggle activation
"""

import unittest
import json
from app import app
from database.db_connection import get_db_cursor
from ai_engine.default_rules import DefaultRule, DefaultRuleManager, CANONICAL_DEFAULT_RULES
from ai_engine.assumption_manager import AssumptionManager, Assumption
from ai_engine.default_reasoning import DefaultReasoningEngine, infer_with_defaults
from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact


class TestDefaultReasoningEngine(unittest.TestCase):
    """Exhaustive test suite for Non-Monotonic Default Reasoning."""

    @classmethod
    def setUpClass(cls):
        """Initializes test context and Knowledge Base."""
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.client = cls.app.test_client()

        cls.kb = KnowledgeBase()
        DefaultRuleManager.ensure_table_exists()

        # Ensure all default rules are active initially
        for r in DefaultRuleManager.get_all_rules(active_only=False):
            if not r.is_active:
                DefaultRuleManager.toggle_rule(r.rule_code)

    def setUp(self):
        self.engine = DefaultReasoningEngine()

    # =========================================================================
    # Test A: Complete Student Information
    # =========================================================================

    def test_A_complete_student_information(self):
        """When full profile information exists, pure rule-based reasoning is used without defaults."""
        full_profile = {
            "cgpa": 3.50,
            "semester": 5,
            "department": "Computer Science",
            "interests": ["Machine Learning", "Python Programming"],
            "career_goal": "Machine Learning Engineer",
            "completed_courses": ["Python", "Linear Algebra"]
        }
        res = self.engine.evaluate(full_profile, knowledge_base=self.kb)

        self.assertFalse(res["is_default_reasoning_used"])
        self.assertNotIn("DR01", res["applied_default_rules"])
        self.assertNotIn("DR02", res["applied_default_rules"])
        self.assertNotIn("DR03", res["applied_default_rules"])
        self.assertNotIn("DR04", res["applied_default_rules"])
        self.assertGreater(len(res["recommended_courses"]), 0)

        ml_rec = next((c for c in res["recommended_courses"] if "Machine Learning" in c["course_name"]), None)
        self.assertIsNotNone(ml_rec)
        print("[PASS] Test A: Complete student information uses pure rule-based reasoning.")

    # =========================================================================
    # Test B: Missing Career Goal (DR01)
    # =========================================================================

    def test_B_missing_career_goal(self):
        """DR01: When career goal is missing but interests exist, uses interest-based fallback."""
        profile = {
            "cgpa": 3.20,
            "semester": 4,
            "interests": ["Cloud Infrastructure & DevOps", "Cloud Technology"],
            "career_goal": ""  # Missing
        }
        res = self.engine.evaluate(profile, knowledge_base=self.kb)

        self.assertTrue(res["is_default_reasoning_used"])
        self.assertIn("DR01", res["applied_default_rules"])
        self.assertTrue(any("career goal was not provided" in m.lower() for m in res["clarification_messages"]))

        # Check recommended courses match interest
        cloud_rec = next((c for c in res["recommended_courses"] if "Cloud Computing" in c["course_name"]), None)
        self.assertIsNotNone(cloud_rec)
        self.assertTrue(cloud_rec.get("is_default_reasoning"))
        self.assertIn("interest", cloud_rec["explanation"].lower())
        print("[PASS] Test B: Missing career goal triggers DR01 interest-based fallback.")

    # =========================================================================
    # Test C: Missing Interests (DR02)
    # =========================================================================

    def test_C_missing_interests(self):
        """DR02: When interests are missing but career goal exists, uses career-based fallback."""
        profile = {
            "cgpa": 3.00,
            "semester": 4,
            "interests": [],  # Missing
            "career_goal": "Cybersecurity Analyst"
        }
        res = self.engine.evaluate(profile, knowledge_base=self.kb)

        self.assertTrue(res["is_default_reasoning_used"])
        self.assertIn("DR02", res["applied_default_rules"])
        self.assertTrue(any("interests were not provided" in m.lower() for m in res["clarification_messages"]))

        # Check recommended courses match career goal
        sec_rec = next((c for c in res["recommended_courses"] if "Cyber Security" in c["course_name"]), None)
        self.assertIsNotNone(sec_rec)
        self.assertTrue(sec_rec.get("is_default_reasoning"))
        self.assertIn("career pathway", sec_rec["explanation"].lower())
        print("[PASS] Test C: Missing interests triggers DR02 career-based fallback.")

    # =========================================================================
    # Test D: Missing Both Interests and Career Goal (DR03)
    # =========================================================================

    def test_D_missing_both_interests_and_career_goal(self):
        """DR03: When both are missing, generates general foundational breadth recommendations."""
        profile = {
            "cgpa": 3.00,
            "semester": 2,
            "interests": [],
            "career_goal": ""
        }
        res = self.engine.evaluate(profile, knowledge_base=self.kb)

        self.assertTrue(res["is_default_reasoning_used"])
        self.assertIn("DR03", res["applied_default_rules"])
        self.assertTrue(any("neither interests nor career goals" in m.lower() for m in res["clarification_messages"]))

        # Recommendations should be marked as general recommendations
        self.assertGreater(len(res["recommended_courses"]), 0)
        first_rec = res["recommended_courses"][0]
        self.assertTrue(first_rec.get("is_general_recommendation"))
        self.assertIn("general foundational", first_rec["explanation"].lower())
        print("[PASS] Test D: Missing both triggers DR03 general foundational recommendations.")

    # =========================================================================
    # Test E: Missing CGPA (DR04)
    # =========================================================================

    def test_E_missing_cgpa(self):
        """DR04: When CGPA is missing, requests academic info and never assumes a value."""
        profile = {
            "cgpa": None,  # Missing
            "interests": ["Machine Learning"],
            "career_goal": "Data Scientist"
        }
        res = self.engine.evaluate(profile, knowledge_base=self.kb)

        self.assertTrue(res["academic_info_required"])
        self.assertIn("DR04", res["applied_default_rules"])
        self.assertTrue(any("cgpa is missing" in m.lower() for m in res["clarification_messages"]))

        # Verified that no course is confirmed eligible without CGPA
        # In fact, courses requiring minimum CGPA are marked in rejected list with CGPA missing reason
        self.assertGreater(len(res["rejected_courses"]), 0)
        self.assertTrue(any("cgpa is missing" in r["reason"].lower() for r in res["rejected_courses"]))
        print("[PASS] Test E: Missing CGPA triggers DR04 request; CGPA is never assumed.")

    # =========================================================================
    # Test F: Unknown Prerequisites (DR05)
    # =========================================================================

    def test_F_unknown_prerequisites(self):
        """DR05: When completed course transcripts are absent, marks prerequisites unverified."""
        profile = {
            "cgpa": 3.50,
            "interests": ["Deep Learning & Neural Networks"],
            "career_goal": "AI Research Scientist",
            "completed_courses": None  # Prerequisite info unavailable
        }
        res = self.engine.evaluate(profile, knowledge_base=self.kb)

        self.assertIn("DR05", res["applied_default_rules"])
        self.assertTrue(res["unverified_prerequisites_found"])
        self.assertTrue(any("prerequisite information is unavailable" in m.lower() for m in res["clarification_messages"]))

        # Any recommended course that has prerequisites must be marked unverified
        dl_rec = next((c for c in res["recommended_courses"] if "Deep Learning" in c["course_name"]), None)
        if dl_rec:
            self.assertFalse(dl_rec.get("prerequisites_verified"))
            self.assertIn("unverified", dl_rec.get("prerequisites_note", "").lower())
        print("[PASS] Test F: Unknown prerequisites triggers DR05; never assumed satisfied.")

    # =========================================================================
    # Test G: Newly Provided Career Goal (Overrides Default)
    # =========================================================================

    def test_G_newly_provided_career_goal_overrides_default(self):
        """Actual career goal provided by student overrides any prior default assumption."""
        mgr = AssumptionManager()
        # Initial state: student omitted career goal, DR01 made assumption
        mgr.record_assumption("career_goal", "UNSPECIFIED", "Initial missing goal", "DR01")
        self.assertTrue(mgr.has_active_assumption("career_goal"))

        # Student subsequently submits profile with actual career goal
        new_data = {"career_goal": "Computer Vision Engineer"}
        retractions = mgr.reconcile_with_actual_data(new_data)

        self.assertFalse(mgr.has_active_assumption("career_goal"))
        self.assertEqual(len(retractions), 1)
        self.assertIn("Computer Vision Engineer", retractions[0])
        print("[PASS] Test G: Newly provided career goal overrides default assumption.")

    # =========================================================================
    # Test H: Newly Provided Interests (Overrides Default)
    # =========================================================================

    def test_H_newly_provided_interests_overrides_default(self):
        """Actual student interests override any prior default interest assumption."""
        mgr = AssumptionManager()
        mgr.record_assumption("interests", ["UNSPECIFIED"], "Initial missing interests", "DR02")
        self.assertTrue(mgr.has_active_assumption("interests"))

        # Student subsequently selects actual interests
        new_data = {"interests": ["Natural Language Processing", "Artificial Intelligence"]}
        retractions = mgr.reconcile_with_actual_data(new_data)

        self.assertFalse(mgr.has_active_assumption("interests"))
        self.assertEqual(len(retractions), 1)
        self.assertIn("Natural Language Processing", retractions[0])
        print("[PASS] Test H: Newly provided interests override default assumption.")

    # =========================================================================
    # Test I: Assumption Withdrawal
    # =========================================================================

    def test_I_assumption_withdrawal(self):
        """Verifies manual and programmatic assumption retraction."""
        mgr = AssumptionManager()
        a = mgr.record_assumption("career_goal", "Data Scientist", "Initial hypothesis", "DR01")
        self.assertEqual(a.status, "ACTIVE")
        self.assertTrue(a.is_temporary)

        withdrawn = mgr.withdraw_assumption("career_goal", "Student updated preference")
        self.assertIsNotNone(withdrawn)
        self.assertEqual(withdrawn.status, "WITHDRAWN")
        self.assertFalse(mgr.has_active_assumption("career_goal"))
        self.assertIsNotNone(withdrawn.withdrawn_at)
        self.assertEqual(withdrawn.withdrawal_reason, "Student updated preference")
        print("[PASS] Test I: Assumption withdrawal (retraction) verified.")

    # =========================================================================
    # Test J: Recommendation Regeneration Upon Update
    # =========================================================================

    def test_J_recommendation_regeneration(self):
        """Verifies that updating preferences from incomplete to complete regenerates recommendations."""
        # Phase 1: Incomplete profile (missing interests)
        incomplete_profile = {
            "cgpa": 3.50,
            "semester": 4,
            "interests": [],
            "career_goal": "Big Data Engineer"
        }
        res1 = self.engine.evaluate(incomplete_profile, knowledge_base=self.kb)
        self.assertTrue(res1["is_default_reasoning_used"])
        self.assertIn("DR02", res1["applied_default_rules"])

        # Phase 2: Student updates profile with exact interests
        updated_profile = {
            "cgpa": 3.50,
            "semester": 4,
            "interests": ["Big Data & Distributed Computing"],
            "career_goal": "Big Data Engineer",
            "completed_courses": ["Database Systems"]
        }
        res2 = self.engine.evaluate(updated_profile, knowledge_base=self.kb)
        # In updated profile, pure rule-based reasoning should be used
        self.assertFalse(res2["is_default_reasoning_used"])
        self.assertNotIn("DR02", res2["applied_default_rules"])

        bd_rec = next((c for c in res2["recommended_courses"] if "Big Data" in c["course_name"]), None)
        self.assertIsNotNone(bd_rec)
        print("[PASS] Test J: Recommendation regeneration upon preference update verified.")

    # =========================================================================
    # Test K: Inactive Courses Exclusion
    # =========================================================================

    def test_K_inactive_courses_exclusion(self):
        """Verifies that inactive courses are strictly excluded from all recommendations."""
        # Query an inactive course or check active flag
        all_courses = self.kb.get_all_courses(active_only=False)
        inactive = next((c for c in all_courses if not c.is_active), None)

        if inactive:
            profile = {"cgpa": 4.0, "interests": inactive.interests, "career_goal": "Data Scientist"}
            res = self.engine.evaluate(profile, knowledge_base=self.kb)
            rec_ids = [c["course_id"] for c in res["recommended_courses"]]
            self.assertNotIn(inactive.course_id, rec_ids)
        print("[PASS] Test K: Inactive courses strictly excluded from recommendations.")

    # =========================================================================
    # Test L: Minimum CGPA Eligibility
    # =========================================================================

    def test_L_minimum_cgpa_eligibility(self):
        """Verifies that academic CGPA constraints are strictly enforced in default reasoning."""
        # Deep Learning requires 3.00
        # Student with interests but CGPA 2.80 below requirement
        low_cgpa_profile = {
            "cgpa": 2.80,
            "interests": ["Deep Learning & Neural Networks"],
            "career_goal": ""  # DR01 triggers
        }
        res = self.engine.evaluate(low_cgpa_profile, knowledge_base=self.kb)

        # Deep Learning must NOT be recommended
        rec_names = [c["course_name"] for c in res["recommended_courses"]]
        self.assertNotIn("Deep Learning", rec_names)

        # Deep Learning must appear in rejected courses with CGPA reason
        rej_dl = next((r for r in res["rejected_courses"] if "Deep Learning" in r["course_name"]), None)
        self.assertIsNotNone(rej_dl)
        self.assertIn("below required", rej_dl["reason"].lower())
        print("[PASS] Test L: Minimum CGPA eligibility enforced in default reasoning.")

    # =========================================================================
    # Test M: Admin Default Rule Activation & Deactivation
    # =========================================================================

    def test_M_admin_default_rule_toggle(self):
        """Verifies that default rules can be deactivated by administrators."""
        # Toggle DR01 off
        DefaultRuleManager.toggle_rule("DR01")
        rule = DefaultRuleManager.get_rule_by_code("DR01")
        self.assertFalse(rule.is_active)

        # Evaluate profile missing career goal: DR01 should not be applied when inactive
        profile = {"cgpa": 3.0, "interests": ["Machine Learning"], "career_goal": ""}
        res = self.engine.evaluate(profile, knowledge_base=self.kb)
        self.assertNotIn("DR01", res["applied_default_rules"])

        # Toggle DR01 back on
        DefaultRuleManager.toggle_rule("DR01")
        rule_restored = DefaultRuleManager.get_rule_by_code("DR01")
        self.assertTrue(rule_restored.is_active)
        print("[PASS] Test M: Admin default rule activation/deactivation toggle verified.")


if __name__ == "__main__":
    unittest.main()
