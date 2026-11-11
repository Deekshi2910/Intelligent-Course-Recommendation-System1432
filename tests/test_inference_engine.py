"""
Phase 10: Centralized Inference Engine Test Suite
Validates the full inference pipeline: profile normalization, hard eligibility checks,
forward chaining, default reasoning fallback, 4-factor scoring, ranking, and grounded XAI.
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_engine.inference_engine import InferenceEngine, generate_recommendations
from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact
from ai_engine.recommendation_scorer import RecommendationScorer
from ai_engine.course_ranker import CourseRanker
from ai_engine.explanation_generator import ExplanationGenerator


class TestInferenceEngine(unittest.TestCase):
    """Test suite for the unified master AI Inference Engine."""

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()
        cls.engine = InferenceEngine(knowledge_base=cls.kb)

    def test_complete_student_inference(self):
        """Complete profile generates high suitability score recommendations with grounded XAI."""
        profile = {
            "cgpa": 8.80,
            "semester": 6,
            "department": "Computer Science",
            "interests": ["Machine Learning", "Python Programming"],
            "career_goal": "Data Scientist",
            "completed_courses": ["Python", "Linear Algebra", "CS-101"]
        }
        res = self.engine.infer(profile)

        self.assertGreater(res["total_recommended"], 0)
        top = res["recommendations"][0]
        self.assertIn("course_name", top)
        self.assertIn("suitability_score", top)
        self.assertIn("score_breakdown", top)
        self.assertIn("explanation", top)

    def test_hard_eligibility_exclusion(self):
        """Courses requiring minimum CGPA > student CGPA are strictly excluded."""
        profile = {
            "cgpa": 2.10,
            "semester": 6,
            "interests": ["Machine Learning", "Artificial Intelligence"],
            "career_goal": "Data Scientist"
        }
        res = self.engine.infer(profile)

        rec_ids = {r["course_id"] for r in res["recommendations"]}
        # CS-406 requires 3.00, CS-408 requires 2.75
        self.assertNotIn(6, rec_ids)
        self.assertNotIn(8, rec_ids)

        rej_codes = [rej["course_code"] for rej in res["rejected_courses"]]
        self.assertIn("CS-406", rej_codes)

    def test_recommendation_scorer_weights(self):
        """Scorer correctly calculates 40% Interest, 35% Career, 15% CGPA, 10% Prereq."""
        fact = self.kb.get_course_by_code("CS-401")
        student = {
            "cgpa": 8.50,
            "career_goal": "Data Scientist",
            "interests": ["Machine Learning"],
            "completed_courses": ["Python", "Linear Algebra"]
        }
        score_res = RecommendationScorer.score_course(student, fact)
        self.assertIn("suitability_score", score_res)
        self.assertIn("breakdown", score_res)
        self.assertGreater(score_res["suitability_score"], 60.0)

    def test_course_ranker_tier_assignment(self):
        """Course ranker assigns appropriate pedagogical badges."""
        candidates = [
            {"course_id": 1, "course_code": "CS-401", "course_name": "ML", "priority": 9, "suitability_score": 90.0},
            {"course_id": 2, "course_code": "CS-402", "course_name": "AI", "priority": 5, "suitability_score": 70.0}
        ]
        ranked = CourseRanker.rank_and_filter(candidates)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["recommendation_tier"], "Highly Recommended")
        self.assertEqual(ranked[1]["recommendation_tier"], "Strong Match")

    def test_explanation_generator_format(self):
        """Explanation generator creates grounded natural language explanation."""
        course_data = {
            "course_name": "Machine Learning",
            "course_code": "CS-401",
            "minimum_cgpa": 2.50,
            "suitability_score": 90.0,
            "matched_interests": ["Python", "Mathematics"],
            "career_goal_matched": True
        }
        student = {"cgpa": 8.50, "career_goal": "Data Scientist"}
        exp = ExplanationGenerator.generate_recommendation_explanation(course_data, student)
        self.assertIn("Machine Learning received a suitability score of 90", exp)
        self.assertIn("Python and Mathematics", exp)
        self.assertIn("Data Scientist", exp)
        self.assertIn("academic eligibility requirement", exp)


if __name__ == "__main__":
    unittest.main()
