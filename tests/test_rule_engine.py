"""
Phase 10: Rule-Based Reasoning Test Suite
Validates production rules representations, condition groups, comparison operators,
allowlists, rule priorities, and deterministic evaluation without eval().
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_engine.rules import (
    ProductionRule,
    ConditionGroup,
    RulePredicate,
    RuleAction,
    ALLOWED_FIELDS,
    ALLOWED_OPERATORS
)
from ai_engine.rule_evaluator import RuleEvaluator, evaluate_rules
from ai_engine.rule_manager import RuleManager
from ai_engine.knowledge_base import KnowledgeBase


class TestRuleEngine(unittest.TestCase):
    """Test suite for AI Production Rules and deterministic evaluation."""

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()
        cls.rm = RuleManager()

    def test_predicate_validation(self):
        """RulePredicate rejects invalid fields and operators."""
        # Valid
        pred = RulePredicate("cgpa", "greater_than_or_equal", 7.5)
        self.assertEqual(pred.field, "cgpa")

        # Invalid field
        with self.assertRaises(ValueError):
            RulePredicate("invalid_field", "equals", "val")

        # Invalid operator
        with self.assertRaises(ValueError):
            RulePredicate("cgpa", "invalid_op", 7.5)

    def test_rule_evaluator_and_conditions(self):
        """Rule requires all AND conditions to be satisfied."""
        rule = ProductionRule(
            id=101,
            rule_name="Test AND Rule",
            action=RuleAction(course_id=1),
            priority=8,
            conditions=ConditionGroup(
                all=[
                    RulePredicate("interests", "contains", "Python"),
                    RulePredicate("cgpa", "greater_than_or_equal", 7.0)
                ]
            )
        )
        # Satisifes both
        res1 = RuleEvaluator.evaluate(rule, {"interests": ["Python"], "cgpa": 8.0})
        self.assertTrue(res1.is_matched)

        # Fails CGPA
        res2 = RuleEvaluator.evaluate(rule, {"interests": ["Python"], "cgpa": 6.5})
        self.assertFalse(res2.is_matched)

    def test_rule_evaluator_or_conditions(self):
        """Rule requires at least one OR condition to be satisfied."""
        rule = ProductionRule(
            id=102,
            rule_name="Test OR Rule",
            action=RuleAction(course_id=1),
            priority=5,
            conditions=ConditionGroup(
                any=[
                    RulePredicate("career_goal", "equals", "Data Scientist"),
                    RulePredicate("career_goal", "equals", "ML Engineer")
                ]
            )
        )
        res1 = RuleEvaluator.evaluate(rule, {"career_goal": "Data Scientist", "cgpa": 8.0})
        self.assertTrue(res1.is_matched)

        res2 = RuleEvaluator.evaluate(rule, {"career_goal": "Web Developer", "cgpa": 8.0})
        self.assertFalse(res2.is_matched)

    def test_rule_manager_retrieval(self):
        """RuleManager retrieves active rules ordered by priority descending."""
        rules = self.rm.get_all_rules(active_only=True)
        self.assertGreater(len(rules), 0)
        # Check priority order
        priorities = [r.priority for r in rules]
        self.assertEqual(priorities, sorted(priorities, reverse=True))


if __name__ == "__main__":
    unittest.main()
