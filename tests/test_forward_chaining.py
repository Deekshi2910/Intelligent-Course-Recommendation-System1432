"""
Phase 10: Forward Chaining Inference Test Suite
Validates the Match-Resolve-Act forward chaining cycle, working memory assertions,
priority conflict resolution, refraction (loop prevention), and quiescence termination.
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_engine.forward_chaining import ForwardChainingEngine, FiredRuleRecord
from ai_engine.rules import ProductionRule, ConditionGroup, RulePredicate, RuleAction
from ai_engine.knowledge_base import KnowledgeBase


class TestForwardChaining(unittest.TestCase):
    """Test suite for the Forward Chaining deductive inference cycle."""

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()

    def test_match_resolve_act_execution(self):
        """Forward chaining fires eligible rules and asserts derived facts."""
        fc = ForwardChainingEngine(max_cycles=5)
        rule = ProductionRule(
            id=501,
            rule_name="FC Test Rule",
            action=RuleAction(course_id=1),
            priority=8,
            conditions=ConditionGroup(
                all=[RulePredicate("interests", "contains", "Machine Learning")]
            )
        )
        wm = {"interests": ["Machine Learning"], "cgpa": 8.50}
        res = fc.run(wm, [rule], knowledge_base=self.kb)

        self.assertEqual(len(res["fired_rules"]), 1)
        self.assertEqual(res["total_cycles"], 1)
        self.assertIn("qualified_for_course_1", res["final_working_memory"])

    def test_priority_conflict_resolution(self):
        """Conflict resolution executes highest priority rules first."""
        fc = ForwardChainingEngine(max_cycles=5)
        rule_low = ProductionRule(
            id=502,
            rule_name="Low Priority Rule",
            action=RuleAction(course_id=1),
            priority=2,
            conditions=ConditionGroup(all=[RulePredicate("interests", "contains", "Python")])
        )
        rule_high = ProductionRule(
            id=503,
            rule_name="High Priority Rule",
            action=RuleAction(course_id=1),
            priority=9,
            conditions=ConditionGroup(all=[RulePredicate("interests", "contains", "Python")])
        )
        wm = {"interests": ["Python"], "cgpa": 8.0}
        res = fc.run(wm, [rule_low, rule_high], knowledge_base=self.kb)

        candidates = res["candidate_courses"]
        self.assertEqual(len(candidates), 1)
        # Preserves highest priority (9)
        self.assertEqual(candidates[0]["priority"], 9)

    def test_refraction_prevents_infinite_loops(self):
        """Refraction ensures rules fire at most once across cycles."""
        fc = ForwardChainingEngine(max_cycles=10)
        rule = ProductionRule(
            id=504,
            rule_name="Loop Prevention Rule",
            action=RuleAction(course_id=2),
            priority=5,
            conditions=ConditionGroup(all=[RulePredicate("interests", "contains", "AI")])
        )
        wm = {"interests": ["AI"], "cgpa": 8.0}
        res = fc.run(wm, [rule], knowledge_base=self.kb)

        # Should fire once and terminate in cycle 1
        self.assertEqual(len(res["fired_rules"]), 1)
        self.assertEqual(res["total_cycles"], 1)


if __name__ == "__main__":
    unittest.main()
