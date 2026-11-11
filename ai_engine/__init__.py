"""
AI Engine Package
Intelligent Course Recommendation System

Comprehensive Knowledge-Based and Rule-Based AI Engine:
- knowledge_base: Course knowledge models and queries.
- knowledge_repository: MySQL persistence and relationship queries.
- knowledge_validator: Data sanity checks and structural validation.
- knowledge_loader: Seed data loader.
- rules: Structured JSON production rules representation.
- rule_evaluator: Deterministic condition evaluation and testing.
- rule_manager: Production rules database management and priorities.
- default_reasoning: Non-monotonic default reasoning engine (DR01 - DR05).
- default_rules: Canonical default rules.
- assumption_manager: Working assumptions and non-monotonic retractions.
- forward_chaining: Match-Resolve-Act forward chaining inference engine.
- recommendation_scorer: Multi-criteria confidence scoring.
- course_ranker: Deduplication, threshold filtering, and ranking tiers.
- explanation_generator: Explainable AI (XAI) rationale generation.
- inference_engine: Master recommendation orchestrator and history persistence.
- reasoning_logger: Audit trail logging.
"""

from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact
from ai_engine.knowledge_repository import KnowledgeRepository
from ai_engine.knowledge_validator import KnowledgeValidator
from ai_engine.knowledge_loader import KnowledgeLoader
from ai_engine.rules import (
    ProductionRule,
    ConditionGroup,
    RuleCondition,
    RulePredicate,
    RuleAction,
    ALLOWED_FIELDS,
    ALLOWED_OPERATORS
)
from ai_engine.rule_evaluator import (
    RuleEvaluator,
    RuleEvaluationResult,
    evaluate_rules,
    OPERATOR_REGISTRY
)
from ai_engine.rule_manager import RuleManager
from ai_engine.default_rules import DefaultRule, DefaultRuleManager, CANONICAL_DEFAULT_RULES, get_canonical_default_rules
from ai_engine.assumption_manager import Assumption, AssumptionManager
from ai_engine.default_reasoning import DefaultReasoningEngine, infer_with_defaults
from ai_engine.forward_chaining import ForwardChainingEngine, FiredRuleRecord
from ai_engine.recommendation_scorer import RecommendationScorer
from ai_engine.course_ranker import CourseRanker
from ai_engine.explanation_generator import ExplanationGenerator
from ai_engine.inference_engine import InferenceEngine, generate_recommendations, recommend_courses
from ai_engine.reasoning_logger import ReasoningLogger, ReasoningStep

__all__ = [
    # Knowledge Base
    "KnowledgeBase",
    "CourseKnowledgeFact",
    "KnowledgeRepository",
    "KnowledgeValidator",
    "KnowledgeLoader",
    # Rules & Operators
    "ProductionRule",
    "ConditionGroup",
    "RuleCondition",
    "RulePredicate",
    "RuleAction",
    "ALLOWED_FIELDS",
    "ALLOWED_OPERATORS",
    # Evaluation & Reasoning
    "RuleEvaluator",
    "RuleEvaluationResult",
    "evaluate_rules",
    "OPERATOR_REGISTRY",
    "RuleManager",
    # Default Reasoning
    "DefaultRule",
    "DefaultRuleManager",
    "CANONICAL_DEFAULT_RULES",
    "get_canonical_default_rules",
    "Assumption",
    "AssumptionManager",
    "DefaultReasoningEngine",
    "infer_with_defaults",
    # Forward Chaining & Inference
    "ForwardChainingEngine",
    "FiredRuleRecord",
    "RecommendationScorer",
    "CourseRanker",
    "ExplanationGenerator",
    "InferenceEngine",
    "generate_recommendations",
    "recommend_courses",
    # Audit Trail
    "ReasoningLogger",
    "ReasoningStep"
]
