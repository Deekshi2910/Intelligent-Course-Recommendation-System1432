"""
Comprehensive Test Suite for AI Inference Engine & Sub-modules
Tests:
1. Forward Chaining Cycle & Conflict Resolution
2. Recommendation Scorer Multi-factor Weighting
3. Course Ranker Deduplication, Thresholding & Tiers
4. Explanation Generator XAI Output
5. Unified Inference Engine End-to-End Execution
6. History Persistence into recommendation_history
"""

import unittest
from app import app
from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact
from ai_engine.rules import ProductionRule, ConditionGroup, RulePredicate, RuleAction
from ai_engine.forward_chaining import ForwardChainingEngine
from ai_engine.recommendation_scorer import RecommendationScorer
from ai_engine.course_ranker import CourseRanker
from ai_engine.explanation_generator import ExplanationGenerator
from ai_engine.inference_engine import InferenceEngine, recommend_courses
from database.db_connection import get_db_cursor


class TestInferenceEngineModules(unittest.TestCase):
    """Test individual components and unified inference orchestrator."""

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.kb = KnowledgeBase()

    def setUp(self):
        self.sample_fact = CourseKnowledgeFact(
            course_id=1,
            course_code="CS-401",
            course_name="Machine Learning Systems",
            description="Deep dive into production ML systems.",
            minimum_cgpa=7.50,
            difficulty_level="Advanced",
            prerequisites_text="CS-201 Data Structures",
            prerequisite_courses=[{"course_code": "CS-201"}],
            interests=["Machine Learning", "Python", "Data Science"],
            career_goals=["Data Scientist", "ML Engineer"],
            is_active=True
        )

    # -------------------------------------------------------------------------
    # 1. Forward Chaining Tests
    # -------------------------------------------------------------------------
    def test_forward_chaining_match_resolve_act(self):
        engine = ForwardChainingEngine(max_cycles=5)
        rule1 = ProductionRule(
            id=101,
            rule_name="ML Rule High",
            action=RuleAction(course_id=1),
            priority=8,
            conditions=ConditionGroup(
                all=[RulePredicate(field="interests", operator="contains", value="Machine Learning")],
                rationale="ML rule high"
            )
        )
        rule2 = ProductionRule(
            id=102,
            rule_name="ML Rule Low",
            action=RuleAction(course_id=1),
            priority=4,
            conditions=ConditionGroup(
                all=[RulePredicate(field="interests", operator="contains", value="Machine Learning")],
                rationale="ML rule low"
            )
        )

        working_memory = {"interests": ["Machine Learning"], "cgpa": 8.0}
        result = engine.run(working_memory, [rule1, rule2], knowledge_base=self.kb)

        candidates = result["candidate_courses"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["course_id"], 1)
        # Deduplication should preserve highest priority
        self.assertEqual(candidates[0]["priority"], 8)
        self.assertIn("ML Rule High", candidates[0]["fired_rules"])
        self.assertIn("qualified_for_course_1", result["final_working_memory"])

    # -------------------------------------------------------------------------
    # 2. Recommendation Scorer Tests
    # -------------------------------------------------------------------------
    def test_recommendation_scorer_breakdown(self):
        student_profile = {
            "cgpa": 8.50,
            "semester": 6,
            "interests": ["Machine Learning", "Python"],
            "career_goal": "Data Scientist"
        }
        res = RecommendationScorer.score_course(
            student_profile=student_profile,
            course_fact=self.sample_fact,
            rule_priority=9
        )

        self.assertIn("total_score", res)
        self.assertIn("breakdown", res)
        score = res["total_score"]
        self.assertGreaterEqual(score, 70.0)
        self.assertLessEqual(score, 100.0)
        self.assertGreater(res["breakdown"]["academic_fit"], 0.0)
        self.assertGreater(res["breakdown"]["interest_overlap"], 0.0)
        self.assertEqual(res["breakdown"]["career_alignment"], 100.0)

    # -------------------------------------------------------------------------
    # 3. Course Ranker Tests
    # -------------------------------------------------------------------------
    def test_course_ranker_deduplication_and_tiers(self):
        raw_candidates = [
            {"course_id": 1, "course_code": "CS-401", "course_name": "ML", "priority": 9, "match_score": 88.0},
            {"course_id": 2, "course_code": "CS-402", "course_name": "Cyber", "priority": 6, "match_score": 65.0},
            {"course_id": 1, "course_code": "CS-401", "course_name": "ML", "priority": 5, "match_score": 70.0},
            {"course_id": 3, "course_code": "CS-403", "course_name": "Intro", "priority": 2, "match_score": 25.0}
        ]

        ranked = CourseRanker.rank_and_filter(raw_candidates, min_score_threshold=30.0)
        # Course 3 is below 30.0 threshold and should be filtered out
        self.assertEqual(len(ranked), 2)
        # Course 1 should be ranked #1
        self.assertEqual(ranked[0]["course_id"], 1)
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertEqual(ranked[0]["priority"], 9)
        self.assertEqual(ranked[0]["match_score"], 88.0)
        self.assertEqual(ranked[0]["recommendation_tier"], "Highly Recommended")

        # Course 2 should be ranked #2
        self.assertEqual(ranked[1]["course_id"], 2)
        self.assertEqual(ranked[1]["recommendation_tier"], "Strong Match")

    # -------------------------------------------------------------------------
    # 4. Explanation Generator Tests
    # -------------------------------------------------------------------------
    def test_explanation_generator(self):
        course_data = {
            "course_code": "CS-401",
            "course_name": "Machine Learning Systems",
            "minimum_cgpa": 7.50,
            "difficulty_level": "Advanced",
            "matched_interests": ["Machine Learning"],
            "matched_career_goals": ["Data Scientist"],
            "fired_rules": ["Machine Learning Recommendation"],
            "match_score": 92.5,
            "recommendation_tier": "Highly Recommended",
            "prerequisites_verified": True
        }
        student = {"cgpa": 8.50, "career_goal": "Data Scientist"}

        explanation = ExplanationGenerator.generate_recommendation_explanation(course_data, student)
        self.assertIn("Machine Learning", explanation)
        self.assertIn("Data Scientist", explanation)
        self.assertIn("academic eligibility", explanation)

        # Test Rejection explanation
        rej_exp = ExplanationGenerator.generate_rejection_explanation(
            course_data={"course_code": "CS-405", "course_name": "Cloud Arch", "minimum_cgpa": 8.0},
            student_profile={"cgpa": 6.50}
        )
        self.assertIn("CGPA requirement not met", rej_exp)

        # Test Default Reasoning explanation
        def_exp = ExplanationGenerator.generate_default_reasoning_explanation(
            strategy="interest_fallback",
            assumptions=[]
        )
        self.assertIn("DR01", def_exp)

    # -------------------------------------------------------------------------
    # 5. Full End-to-End Inference Engine Tests
    # -------------------------------------------------------------------------
    def test_end_to_end_inference_complete_profile(self):
        engine = InferenceEngine(knowledge_base=self.kb)
        profile = {
            "cgpa": 8.80,
            "semester": 6,
            "department": "Computer Science",
            "interests": ["Machine Learning", "Python"],
            "career_goal": "Data Scientist"
        }
        result = engine.infer(profile, min_score_threshold=30.0)

        self.assertIn("recommendations", result)
        self.assertIn("summary", result)
        self.assertGreater(result["total_recommended"], 0)

        top_rec = result["recommendations"][0]
        self.assertIn("course_code", top_rec)
        self.assertIn("explanation", top_rec)
        self.assertIn("match_score", top_rec)
        self.assertIn("recommendation_tier", top_rec)

    def test_end_to_end_inference_incomplete_profile_dr01(self):
        """Test inference when career goal is missing (DR01 fallback)."""
        engine = InferenceEngine(knowledge_base=self.kb)
        profile = {
            "cgpa": 8.0,
            "semester": 4,
            "interests": ["Cybersecurity"],
            "career_goal": ""  # Missing
        }
        result = engine.infer(profile)

        self.assertIn("DR01", result["applied_default_rules"])
        self.assertGreater(result["total_recommended"], 0)
        self.assertTrue(result["is_default_reasoning_used"])

    def test_end_to_end_inference_missing_cgpa_dr04(self):
        """Test inference when CGPA is missing (DR04 academic info required)."""
        engine = InferenceEngine(knowledge_base=self.kb)
        profile = {
            "cgpa": None,
            "semester": 4,
            "interests": ["Artificial Intelligence"],
            "career_goal": "AI Researcher"
        }
        result = engine.infer(profile)

        self.assertIn("DR04", result["applied_default_rules"])
        self.assertTrue(result["academic_info_required"])

    def test_recommend_courses_helper_function(self):
        profile = {
            "cgpa": 7.8,
            "semester": 5,
            "interests": ["Cloud Computing"],
            "career_goal": "Cloud Architect"
        }
        res = recommend_courses(profile, knowledge_base=self.kb, top_n=3)
        self.assertIn("recommendations", res)
        self.assertLessEqual(len(res["recommendations"]), 3)

    def test_recommend_and_persist(self):
        """Test persisting recommendation into recommendation_history."""
        # Find a valid student_id from database
        student_id = None
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id FROM student_profiles LIMIT 1")
            row = cursor.fetchone()
            if row:
                student_id = row["id"]

        if not student_id:
            self.skipTest("No student profiles in database to test persistence.")

        engine = InferenceEngine(knowledge_base=self.kb)
        profile = {
            "cgpa": 8.5,
            "semester": 5,
            "interests": ["Machine Learning"],
            "career_goal": "Data Scientist"
        }
        result = engine.recommend_and_persist(student_id=student_id, student_profile=profile, top_n=1)
        self.assertIn("recommendations", result)
        self.assertNotIn("persistence_error", result)


if __name__ == "__main__":
    unittest.main()
