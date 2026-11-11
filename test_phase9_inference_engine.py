"""
Comprehensive Phase 9 Automated Test Suite: Complete AI Inference Engine
Intelligent Course Recommendation System

Validates all 15 Phase 9 Specifications (A through O) + Independent Forward Chaining:
Test A: Complete student information (rule-based reasoning + forward chaining)
Test B: Missing career goal (DR01 interest fallback)
Test C: Missing interests (DR02 career fallback)
Test D: Missing both (DR03 general foundational)
Test E: Missing CGPA (DR04 never assumed, requests academic info)
Test F: Low CGPA (hard eligibility exclusion + deficit recording)
Test G: Unknown prerequisites (DR05 unverified flag, never assumed satisfied)
Test H: Multiple matched rules (multi-rule agenda execution)
Test I: Conflicting rules (priority-based conflict resolution)
Test J: Duplicate course recommendations (deduplication & reason merging)
Test K: Equal recommendation scores (consistent multi-tier tie-breaking)
Test L: Inactive courses (strict exclusion from recommendation pool)
Test M: No eligible courses (graceful handling when no courses qualify)
Test N: Recommendation history storage (MySQL persistence & duplicate prevention)
Test O: Recommendation explanation accuracy (grounded Explainable AI validation)
Test P: Forward Chaining Independent Execution (Match-Resolve-Act cycle & refraction)
"""

import unittest
from app import app
from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact
from ai_engine.rules import ProductionRule, ConditionGroup, RulePredicate, RuleAction
from ai_engine.forward_chaining import ForwardChainingEngine
from ai_engine.recommendation_scorer import RecommendationScorer
from ai_engine.course_ranker import CourseRanker
from ai_engine.explanation_generator import ExplanationGenerator
from ai_engine.inference_engine import InferenceEngine, generate_recommendations
from database.db_connection import get_db_cursor


class TestPhase9InferenceEngine(unittest.TestCase):
    """Exhaustive test suite for Phase 9 Complete AI Inference Engine."""

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.kb = KnowledgeBase()

    def setUp(self):
        self.engine = InferenceEngine(knowledge_base=self.kb)

    # -------------------------------------------------------------------------
    # Test A: Complete Student Information
    # -------------------------------------------------------------------------
    def test_A_complete_student_information(self):
        profile = {
            "cgpa": 8.50,
            "semester": 6,
            "department": "Computer Science",
            "interests": ["Machine Learning", "Python Programming"],
            "career_goal": "Data Scientist",
            "completed_courses": ["Python", "Linear Algebra", "CS-101"]
        }
        res = generate_recommendations(profile, knowledge_base=self.kb)
        
        self.assertGreater(res["total_recommended"], 0)
        self.assertIn("recommendations", res)
        top = res["recommendations"][0]
        self.assertGreaterEqual(top["suitability_score"], 60.0)
        self.assertIn("score_breakdown", top)
        # All 4 components calculated
        self.assertIn("interest_match", top["score_breakdown"])
        self.assertIn("career_match", top["score_breakdown"])
        self.assertIn("cgpa_readiness", top["score_breakdown"])
        self.assertIn("prerequisite_match", top["score_breakdown"])

    # -------------------------------------------------------------------------
    # Test B: Missing Career Goal (DR01 Fallback)
    # -------------------------------------------------------------------------
    def test_B_missing_career_goal(self):
        profile = {
            "cgpa": 8.00,
            "semester": 4,
            "interests": ["Python Programming", "Machine Learning"],
            "career_goal": ""  # Missing
        }
        res = self.engine.infer(profile)

        self.assertIn("DR01", res["applied_default_rules"])
        self.assertTrue(res["is_default_reasoning_used"])
        self.assertGreater(res["total_recommended"], 0)
        # Career score should be 0.0 because career goal was missing (not assumed)
        for r in res["recommendations"]:
            self.assertEqual(r["score_breakdown"]["career_match"], 0.0)

    # -------------------------------------------------------------------------
    # Test C: Missing Interests (DR02 Fallback)
    # -------------------------------------------------------------------------
    def test_C_missing_interests(self):
        profile = {
            "cgpa": 8.00,
            "semester": 4,
            "interests": [],  # Missing
            "career_goal": "Data Scientist"
        }
        res = self.engine.infer(profile)

        self.assertIn("DR02", res["applied_default_rules"])
        self.assertTrue(res["is_default_reasoning_used"])
        self.assertGreater(res["total_recommended"], 0)
        # Interest match should be 0.0 because interests were missing
        for r in res["recommendations"]:
            self.assertEqual(r["score_breakdown"]["interest_match"], 0.0)

    # -------------------------------------------------------------------------
    # Test D: Missing Both Interests & Career Goal (DR03 Fallback)
    # -------------------------------------------------------------------------
    def test_D_missing_both(self):
        profile = {
            "cgpa": 8.00,
            "semester": 4,
            "interests": [],
            "career_goal": ""
        }
        res = self.engine.infer(profile)

        self.assertIn("DR03", res["applied_default_rules"])
        self.assertTrue(res["is_default_reasoning_used"])
        self.assertGreater(res["total_recommended"], 0)
        # Should recommend foundational/breadth electives
        tiers = [r.get("recommendation_tier") for r in res["recommendations"]]
        self.assertTrue(any("Foundational" in t or "Elective" in t for t in tiers))

    # -------------------------------------------------------------------------
    # Test E: Missing CGPA (DR04 Fallback - Never Assumed)
    # -------------------------------------------------------------------------
    def test_E_missing_cgpa(self):
        profile = {
            "cgpa": None,  # Missing
            "semester": 4,
            "interests": ["Machine Learning"],
            "career_goal": "Data Scientist"
        }
        res = self.engine.infer(profile)

        self.assertIn("DR04", res["applied_default_rules"])
        self.assertTrue(res["academic_info_required"])
        # Courses requiring CGPA must NOT be recommended without academic data
        for r in res["recommendations"]:
            self.assertEqual(float(r.get("minimum_cgpa", 0.0)), 0.0)

    # -------------------------------------------------------------------------
    # Test F: Low CGPA (Hard Eligibility Constraint)
    # -------------------------------------------------------------------------
    def test_F_low_cgpa(self):
        # Student CGPA 2.10; course CS-406 requires 3.00, CS-408 requires 2.75
        profile = {
            "cgpa": 2.10,
            "semester": 6,
            "interests": ["Machine Learning", "Artificial Intelligence"],
            "career_goal": "Data Scientist"
        }
        res = self.engine.infer(profile)

        # Ineligible courses must not be in recommendations
        rec_ids = {r["course_id"] for r in res["recommendations"]}
        self.assertNotIn(6, rec_ids)  # CS-406 requires 3.00
        self.assertNotIn(8, rec_ids)  # CS-408 requires 2.75

        # Check rejected courses log
        rej_codes = [rej["course_code"] for rej in res["rejected_courses"]]
        self.assertIn("CS-406", rej_codes)

    # -------------------------------------------------------------------------
    # Test G: Unknown Prerequisites (DR05 Fallback)
    # -------------------------------------------------------------------------
    def test_G_unknown_prerequisites(self):
        profile = {
            "cgpa": 8.00,
            "semester": 5,
            "interests": ["Machine Learning"],
            "career_goal": "Data Scientist",
            "completed_courses": None  # Unknown/unspecified
        }
        res = self.engine.infer(profile)

        self.assertTrue(res["unverified_prerequisites_found"])
        # Verify unverified notes exist on courses requiring prerequisites
        unverified_found = False
        for r in res["recommendations"]:
            if not r.get("prerequisites_verified", True):
                unverified_found = True
                self.assertIn("Unverified", r.get("prerequisites_note", ""))
        self.assertTrue(unverified_found)

    # -------------------------------------------------------------------------
    # Test H: Multiple Matched Rules
    # -------------------------------------------------------------------------
    def test_H_multiple_matched_rules(self):
        # Matches multiple rules: ML, Python, AI
        profile = {
            "cgpa": 9.00,
            "semester": 6,
            "interests": ["Machine Learning", "Python Programming", "Artificial Intelligence"],
            "career_goal": "Data Scientist"
        }
        res = self.engine.infer(profile)

        self.assertGreater(len(res["fired_rules"]), 1)
        # Deduplication merges fired rules under candidate
        top_rec = res["recommendations"][0]
        self.assertGreaterEqual(len(top_rec.get("fired_rules", [])), 1)

    # -------------------------------------------------------------------------
    # Test I: Conflicting Rules (Priority Resolution)
    # -------------------------------------------------------------------------
    def test_I_conflicting_rules(self):
        fc = ForwardChainingEngine()
        rule_low = ProductionRule(
            id=201, rule_name="Rule Low", action=RuleAction(course_id=1), priority=3,
            conditions=ConditionGroup(all=[RulePredicate("interests", "contains", "Python")])
        )
        rule_high = ProductionRule(
            id=202, rule_name="Rule High", action=RuleAction(course_id=1), priority=9,
            conditions=ConditionGroup(all=[RulePredicate("interests", "contains", "Python")])
        )

        res = fc.run({"interests": ["Python"], "cgpa": 8.0}, [rule_low, rule_high], knowledge_base=self.kb)
        candidates = res["candidate_courses"]
        self.assertEqual(len(candidates), 1)
        # Priority resolution: should adopt priority 9
        self.assertEqual(candidates[0]["priority"], 9)

    # -------------------------------------------------------------------------
    # Test J: Duplicate Course Recommendations Deduplication
    # -------------------------------------------------------------------------
    def test_J_duplicate_course_recommendations(self):
        cand1 = {"course_id": 1, "course_code": "CS-401", "course_name": "ML", "priority": 5, "suitability_score": 80.0, "reasons": ["R1"]}
        cand2 = {"course_id": 1, "course_code": "CS-401", "course_name": "ML", "priority": 8, "suitability_score": 85.0, "reasons": ["R2"]}
        ranked = CourseRanker.rank_and_filter([cand1, cand2])

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["priority"], 8)
        self.assertEqual(ranked[0]["suitability_score"], 85.0)
        self.assertIn("R1", ranked[0]["reasons"])
        self.assertIn("R2", ranked[0]["reasons"])

    # -------------------------------------------------------------------------
    # Test K: Equal Recommendation Scores Tie-Breaking
    # -------------------------------------------------------------------------
    def test_K_equal_recommendation_scores(self):
        candA = {"course_id": 1, "course_code": "CS-401", "course_name": "ML", "priority": 6, "suitability_score": 80.0}
        candB = {"course_id": 2, "course_code": "CS-402", "course_name": "AI", "priority": 8, "suitability_score": 80.0}
        ranked = CourseRanker.rank_and_filter([candA, candB])

        self.assertEqual(len(ranked), 2)
        # Higher priority (8) breaks tie over lower priority (6)
        self.assertEqual(ranked[0]["course_id"], 2)
        self.assertEqual(ranked[1]["course_id"], 1)

    # -------------------------------------------------------------------------
    # Test L: Inactive Courses Exclusion
    # -------------------------------------------------------------------------
    def test_L_inactive_courses(self):
        inactive_fact = CourseKnowledgeFact(
            course_id=999,
            course_code="CS-999",
            course_name="Deprecated System",
            description="Inactive course",
            minimum_cgpa=0.0,
            difficulty_level="Beginner",
            prerequisites_text="",
            is_active=False
        )
        elig = self.engine.evaluate_course_eligibility(inactive_fact, {"cgpa": 9.0})
        self.assertFalse(elig["is_eligible"])
        self.assertIn("inactive", elig["reasons"][0].lower())

    # -------------------------------------------------------------------------
    # Test M: No Eligible Courses Handling
    # -------------------------------------------------------------------------
    def test_M_no_eligible_courses(self):
        # Student CGPA 1.00 is below all minimum CGPAs (all require >= 2.0)
        profile = {
            "cgpa": 1.00,
            "semester": 1,
            "interests": ["Python Programming"],
            "career_goal": "Software Engineer"
        }
        res = self.engine.infer(profile)

        self.assertEqual(res["total_recommended"], 0)
        self.assertEqual(len(res["recommendations"]), 0)
        self.assertGreater(res["total_rejected"], 0)

    # -------------------------------------------------------------------------
    # Test N: Recommendation History Storage
    # -------------------------------------------------------------------------
    def test_N_recommendation_history_storage(self):
        student_id = None
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM student_profiles LIMIT 1")
            row = cursor.fetchone()
            if row:
                student_id = row["id"]

        if not student_id:
            self.skipTest("No student profiles in database for persistence test.")

        profile = {
            "cgpa": 8.50,
            "semester": 6,
            "interests": ["Machine Learning"],
            "career_goal": "Data Scientist"
        }
        res = self.engine.recommend_and_persist(student_id=student_id, student_profile=profile, top_n=2)
        
        self.assertGreater(res.get("persisted_count", 0), 0)
        self.assertNotIn("persistence_error", res)

    # -------------------------------------------------------------------------
    # Test O: Recommendation Explanation Accuracy
    # -------------------------------------------------------------------------
    def test_O_recommendation_explanation_accuracy(self):
        course_data = {
            "course_code": "CS-401",
            "course_name": "Machine Learning",
            "minimum_cgpa": 7.50,
            "suitability_score": 90.0,
            "matched_interests": ["Python", "Mathematics"],
            "career_goal_matched": True,
            "score_breakdown": {
                "interest_match": 85.0,
                "career_match": 100.0,
                "cgpa_readiness": 90.0,
                "prerequisite_match": 100.0
            }
        }
        student_profile = {
            "cgpa": 8.50,
            "career_goal": "Data Scientist",
            "interests": ["Python", "Mathematics"]
        }
        exp = ExplanationGenerator.generate_recommendation_explanation(course_data, student_profile)

        self.assertIn("Machine Learning received a suitability score of 90", exp)
        self.assertIn("Python and Mathematics", exp)
        self.assertIn("Data Scientist", exp)
        self.assertIn("academic eligibility requirement", exp)

    # -------------------------------------------------------------------------
    # Test P: Forward Chaining Independent Execution
    # -------------------------------------------------------------------------
    def test_P_forward_chaining_independent(self):
        fc = ForwardChainingEngine(max_cycles=3)
        rule = ProductionRule(
            id=301,
            rule_name="Independent Rule",
            action=RuleAction(course_id=1),
            priority=7,
            conditions=ConditionGroup(all=[RulePredicate("interests", "contains", "Python")])
        )
        wm = {"interests": ["Python"], "cgpa": 8.0}
        res = fc.run(wm, [rule], knowledge_base=self.kb)

        self.assertEqual(len(res["fired_rules"]), 1)
        self.assertEqual(res["total_cycles"], 1)
        self.assertIn("qualified_for_course_1", res["final_working_memory"])


if __name__ == "__main__":
    unittest.main()
