"""
Rule Evaluator Module
Phase 7: Rule-Based Reasoning Engine

Evaluates student facts against declarative production rule antecedents.
STRICT SAFETY REQUIREMENT:
Strictly zero eval() / exec() usage. Controlled operator registry with explicit allowlist.
Deterministic condition evaluation, academic eligibility enforcement, priority handling,
duplicate recommendation merging, and comprehensive reasoning generation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Callable
from ai_engine.rules import (
    ProductionRule,
    ConditionGroup,
    RulePredicate,
    ALLOWED_FIELDS,
    ALLOWED_OPERATORS
)
from ai_engine.reasoning_logger import ReasoningLogger


# ============================================================================
# Controlled Operator Registry (Pure Deterministic Python Functions)
# ============================================================================

def _op_equals(student_val: Any, target_val: Any) -> bool:
    """Case-insensitive equality comparison for strings, exact for numerics."""
    if student_val is None or target_val is None:
        return student_val == target_val
    if isinstance(student_val, (int, float)) and isinstance(target_val, (int, float, str)):
        try:
            return float(student_val) == float(target_val)
        except (ValueError, TypeError):
            return False
    return str(student_val).strip().lower() == str(target_val).strip().lower()


def _op_not_equals(student_val: Any, target_val: Any) -> bool:
    """Inverse of equals."""
    return not _op_equals(student_val, target_val)


def _op_contains(student_val: Any, target_val: Any) -> bool:
    """
    Checks membership. If student_val is a collection (e.g. interests, courses),
    checks whether target_val matches or is contained in any element.
    If student_val is a string, performs substring check.
    """
    if student_val is None or target_val is None:
        return False
    target_str = str(target_val).strip().lower()

    if isinstance(student_val, (list, tuple, set)):
        for item in student_val:
            item_str = str(item).strip().lower()
            if target_str == item_str or target_str in item_str or item_str in target_str:
                return True
        return False

    return target_str in str(student_val).strip().lower()


def _op_greater_than(student_val: Any, target_val: Any) -> bool:
    """Numeric greater than comparison."""
    if student_val is None or target_val is None:
        return False
    try:
        return float(student_val) > float(target_val)
    except (ValueError, TypeError):
        return False


def _op_greater_than_or_equal(student_val: Any, target_val: Any) -> bool:
    """Numeric greater than or equal comparison."""
    if student_val is None or target_val is None:
        return False
    try:
        return float(student_val) >= float(target_val)
    except (ValueError, TypeError):
        return False


def _op_less_than(student_val: Any, target_val: Any) -> bool:
    """Numeric less than comparison."""
    if student_val is None or target_val is None:
        return False
    try:
        return float(student_val) < float(target_val)
    except (ValueError, TypeError):
        return False


def _op_less_than_or_equal(student_val: Any, target_val: Any) -> bool:
    """Numeric less than or equal comparison."""
    if student_val is None or target_val is None:
        return False
    try:
        return float(student_val) <= float(target_val)
    except (ValueError, TypeError):
        return False


OPERATOR_REGISTRY: Dict[str, Callable[[Any, Any], bool]] = {
    "equals": _op_equals,
    "not_equals": _op_not_equals,
    "contains": _op_contains,
    "greater_than": _op_greater_than,
    "greater_than_or_equal": _op_greater_than_or_equal,
    "less_than": _op_less_than,
    "less_than_or_equal": _op_less_than_or_equal
}


@dataclass
class RuleEvaluationResult:
    """Encapsulates the complete result of evaluating a rule against student facts."""
    rule: ProductionRule
    is_matched: bool
    match_score: float
    cgpa_satisfied: bool
    semester_satisfied: bool
    prerequisites_satisfied: bool
    matched_conditions: List[str] = field(default_factory=list)
    failed_conditions: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    matched_interests: List[str] = field(default_factory=list)
    matched_career_goals: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes evaluation outcome to a clean dictionary."""
        return {
            "rule_id": self.rule.id,
            "rule_name": self.rule.rule_name,
            "recommended_course_id": self.rule.recommended_course_id,
            "course_code": self.rule.course_code,
            "course_name": self.rule.course_name,
            "priority": self.rule.priority,
            "is_matched": self.is_matched,
            "match_score": round(self.match_score, 2),
            "cgpa_satisfied": self.cgpa_satisfied,
            "semester_satisfied": self.semester_satisfied,
            "prerequisites_satisfied": self.prerequisites_satisfied,
            "matched_conditions": self.matched_conditions,
            "failed_conditions": self.failed_conditions,
            "reasons": self.reasons,
            "matched_interests": self.matched_interests,
            "matched_career_goals": self.matched_career_goals,
            "rationale": self.rule.conditions.rationale
        }


class RuleEvaluator:
    """Evaluates student facts against production rules and knowledge base facts."""

    @classmethod
    def evaluate_predicate(cls, predicate: RulePredicate,
                           student_data: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Evaluates a single atomic condition predicate against student facts.
        Returns:
            (is_satisfied: bool, detail: str, field_desc: str)
        """
        field_name = predicate.field.strip().lower()
        operator_name = predicate.operator.strip().lower()
        target_value = predicate.value

        op_func = OPERATOR_REGISTRY.get(operator_name)
        if not op_func:
            return False, f"Unsupported operator '{operator_name}'", field_name

        student_value = student_data.get(field_name)

        # Handle missing student data gracefully
        if student_value is None and field_name not in ("completed_courses", "interests"):
            # Check if field is completely absent
            if operator_name == "not_equals":
                return True, f"Student {field_name} is not set (satisfies != {target_value})", field_name
            return False, f"Missing student information for '{field_name}'", field_name

        # For list fields like interests, ensure collection format
        if field_name == "interests":
            if student_value is None:
                student_value = []
            elif isinstance(student_value, str):
                student_value = [student_value]
        elif field_name == "completed_courses":
            if student_value is None:
                student_value = []
            elif isinstance(student_value, str):
                student_value = [student_value]

        is_satisfied = op_func(student_value, target_value)

        # Build readable explanation fragment
        op_symbols = {
            "equals": "==",
            "not_equals": "!=",
            "contains": "contains",
            "greater_than": ">",
            "greater_than_or_equal": ">=",
            "less_than": "<",
            "less_than_or_equal": "<="
        }
        op_sym = op_symbols.get(operator_name, operator_name)

        if is_satisfied:
            if field_name == "interests":
                detail = f"Student has interest in '{target_value}'"
            elif field_name == "career_goal":
                detail = f"Student selected career goal '{target_value}'"
            elif field_name == "cgpa":
                detail = f"Student CGPA ({float(student_value):.2f}) satisfies requirement ({op_sym} {target_value})"
            elif field_name == "semester":
                detail = f"Student semester ({student_value}) satisfies requirement ({op_sym} {target_value})"
            else:
                detail = f"Condition met: {field_name} {op_sym} {target_value}"
        else:
            if field_name == "interests":
                detail = f"Student does not have required interest '{target_value}'"
            elif field_name == "career_goal":
                current_goal = student_value or 'None'
                detail = f"Student career goal '{current_goal}' does not match '{target_value}'"
            elif field_name == "cgpa":
                curr_cgpa = float(student_value or 0.0)
                detail = f"Student CGPA ({curr_cgpa:.2f}) does not meet requirement ({op_sym} {target_value})"
            elif field_name == "semester":
                curr_sem = student_value or 'None'
                detail = f"Student semester ({curr_sem}) does not meet requirement ({op_sym} {target_value})"
            else:
                detail = f"Condition not met: {field_name} {op_sym} {target_value}"

        return is_satisfied, detail, field_name

    @classmethod
    def evaluate(cls, rule: ProductionRule, student_profile: Dict[str, Any],
                 course_fact: Optional[Any] = None) -> RuleEvaluationResult:
        """
        Evaluates a production rule against student profile facts and course metadata.
        
        Args:
            rule: ProductionRule to evaluate.
            student_profile: Dictionary containing student attributes (cgpa, semester, interests, etc.).
            course_fact: Optional CourseKnowledgeFact instance for intrinsic course requirement verification.
        """
        matched_conditions: List[str] = []
        failed_conditions: List[str] = []
        reasons: List[str] = []
        matched_interests: List[str] = []
        matched_career_goals: List[str] = []

        conditions = rule.conditions

        # ---------------------------------------------------------------------
        # 1. Evaluate 'all' (AND) predicates
        # ---------------------------------------------------------------------
        all_passed = True
        for pred in conditions.all:
            satisfied, detail, field_name = cls.evaluate_predicate(pred, student_profile)
            if satisfied:
                matched_conditions.append(detail)
                if field_name == "interests":
                    matched_interests.append(str(pred.value))
                elif field_name == "career_goal":
                    matched_career_goals.append(str(pred.value))
            else:
                failed_conditions.append(detail)
                all_passed = False

        # ---------------------------------------------------------------------
        # 2. Evaluate 'any' (OR) predicates
        # ---------------------------------------------------------------------
        any_passed = True
        any_matched_count = 0
        if conditions.any:
            any_passed = False
            for pred in conditions.any:
                satisfied, detail, field_name = cls.evaluate_predicate(pred, student_profile)
                if satisfied:
                    any_matched_count += 1
                    matched_conditions.append(detail)
                    if field_name == "interests":
                        matched_interests.append(str(pred.value))
                    elif field_name == "career_goal":
                        matched_career_goals.append(str(pred.value))
                    any_passed = True
                else:
                    failed_conditions.append(detail)

        # Base rule condition satisfaction: (all passed) AND (any passed)
        rule_logic_satisfied = all_passed and any_passed

        # Deduplicate matched collections
        matched_interests = list(dict.fromkeys(matched_interests))
        matched_career_goals = list(dict.fromkeys(matched_career_goals))

        # ---------------------------------------------------------------------
        # 3. Academic Eligibility Checks (CGPA & Semester Constraints)
        # ---------------------------------------------------------------------
        student_cgpa = float(student_profile.get("cgpa") or 0.0)
        student_sem = int(student_profile.get("semester") or 1)

        # Check course intrinsic minimum CGPA if course_fact is provided
        course_min_cgpa = 0.0
        if course_fact:
            course_min_cgpa = float(getattr(course_fact, "minimum_cgpa", 0.0) or 0.0)

        # Check rule minimum CGPA
        rule_min_cgpa = conditions.min_cgpa
        required_min_cgpa = max(course_min_cgpa, rule_min_cgpa)

        cgpa_satisfied = student_cgpa >= required_min_cgpa
        if not cgpa_satisfied:
            rejection_msg = (
                f"Student CGPA ({student_cgpa:.2f}) is below minimum requirement "
                f"({required_min_cgpa:.2f})."
            )
            failed_conditions.append(rejection_msg)
            reasons.append(rejection_msg)
        else:
            if required_min_cgpa > 0.0:
                reasons.append(
                    f"Student CGPA ({student_cgpa:.2f}) satisfies minimum requirement "
                    f"({required_min_cgpa:.2f})."
                )

        # Semester check
        req_sem = conditions.min_semester
        semester_satisfied = student_sem >= req_sem
        if not semester_satisfied:
            sem_msg = f"Student semester ({student_sem}) is below required semester ({req_sem})."
            failed_conditions.append(sem_msg)
            reasons.append(sem_msg)
        else:
            if req_sem > 1:
                reasons.append(f"Student semester ({student_sem}) meets required standing (>= {req_sem}).")

        # ---------------------------------------------------------------------
        # 4. Prerequisite Checking
        # ---------------------------------------------------------------------
        prerequisites_satisfied = True
        raw_completed = student_profile.get("completed_courses")
        completed_courses = [
            str(c).strip().lower()
            for c in (raw_completed if raw_completed is not None else [])
        ]

        prereq_raw = getattr(course_fact, "prerequisites_text", None) or getattr(course_fact, "prerequisites", None)
        if course_fact and prereq_raw:
            # Parse prerequisites if comma or semicolon separated
            if isinstance(prereq_raw, str):
                prereq_items = [p.strip() for p in prereq_raw.replace(";", ",").split(",") if p.strip()]
            elif isinstance(prereq_raw, (list, tuple)):
                prereq_items = [str(p).strip() for p in prereq_raw if str(p).strip()]
            else:
                prereq_items = []

            # If student profile provided an explicit completed courses list, verify satisfaction
            if student_profile.get("completed_courses") is not None and prereq_items:
                missing_prereqs = []
                for req in prereq_items:
                    req_norm = req.lower()
                    if not any(req_norm == c or req_norm in c for c in completed_courses):
                        missing_prereqs.append(req)

                if missing_prereqs:
                    prerequisites_satisfied = False
                    prereq_msg = f"Missing required prerequisite(s): {', '.join(missing_prereqs)}."
                    failed_conditions.append(prereq_msg)
                    reasons.append(prereq_msg)
                else:
                    reasons.append(f"Satisfies prerequisite(s): {', '.join(prereq_items)}.")

        # ---------------------------------------------------------------------
        # 5. Overall Match Determination
        # ---------------------------------------------------------------------
        is_matched = bool(
            rule_logic_satisfied and
            cgpa_satisfied and
            semester_satisfied and
            prerequisites_satisfied
        )

        # ---------------------------------------------------------------------
        # 6. Weighted Match Score [0.0 - 100.0]
        # ---------------------------------------------------------------------
        match_score = 0.0
        if is_matched:
            # Academic readiness base (30%)
            match_score += 30.0

            # Interest match contribution (35%)
            if matched_interests:
                match_score += min(35.0, len(matched_interests) * 20.0)
            elif not conditions.required_interests:
                match_score += 20.0

            # Career goal match contribution (25%)
            if matched_career_goals:
                match_score += 25.0
            elif not conditions.preferred_career_goals:
                match_score += 15.0

            # Priority normalization bonus (10%)
            match_score += min(10.0, float(rule.priority))

            # Add matched items into reasons summary
            if matched_interests:
                reasons.append(f"Matched interest(s): {', '.join(matched_interests)}.")
            if matched_career_goals:
                reasons.append(f"Aligned with career goal: '{matched_career_goals[0]}'.")

        match_score = max(0.0, min(100.0, match_score))

        return RuleEvaluationResult(
            rule=rule,
            is_matched=is_matched,
            match_score=match_score,
            cgpa_satisfied=cgpa_satisfied,
            semester_satisfied=semester_satisfied,
            prerequisites_satisfied=prerequisites_satisfied,
            matched_conditions=matched_conditions,
            failed_conditions=failed_conditions,
            reasons=reasons,
            matched_interests=matched_interests,
            matched_career_goals=matched_career_goals
        )


# ============================================================================
# Top-Level Rule Evaluation Orchestrator Function
# ============================================================================

def evaluate_rules(student_data: Dict[str, Any],
                   knowledge_base: Optional[Any] = None,
                   active_rules: Optional[List[ProductionRule]] = None) -> Dict[str, Any]:
    """
    Evaluates all active production rules against student profile facts.

    Responsibilities:
    - Retrieve active rules ordered by priority descending.
    - Evaluate rule conditions applying AND ('all') and OR ('any') logic.
    - Enforce academic eligibility (student CGPA >= course minimum CGPA).
    - Check course availability and prerequisites.
    - Merge duplicate recommendations across rules, preserving highest priority and match score.
    - Generate transparent, human-readable reasoning explanations for recommended and rejected courses.

    Args:
        student_data: Dict containing student facts (cgpa, semester, interests, career_goal, completed_courses).
        knowledge_base: Optional KnowledgeBase instance.
        active_rules: Optional pre-loaded list of ProductionRule instances.

    Returns:
        Structured dictionary:
        {
            "recommended_courses": List[Dict],
            "rejected_evaluations": List[Dict],
            "audit_trail": List[Dict],
            "total_rules_evaluated": int,
            "total_rules_fired": int
        }
    """
    from ai_engine.rule_manager import RuleManager
    from ai_engine.knowledge_base import KnowledgeBase

    # Initialize KnowledgeBase if not provided
    if knowledge_base is None:
        try:
            knowledge_base = KnowledgeBase()
        except Exception:
            knowledge_base = None

    # Retrieve rules
    if active_rules is None:
        rule_mgr = RuleManager()
        rules = rule_mgr.get_all_rules(active_only=True)
    else:
        rules = [r for r in active_rules if r.is_active]

    # Sort rules strictly by priority descending (higher priority evaluated first)
    rules = sorted(rules, key=lambda r: (r.priority, r.id or 0), reverse=True)

    logger = ReasoningLogger()
    recommendations_map: Dict[int, Dict[str, Any]] = {}
    rejected_evaluations: List[Dict[str, Any]] = []

    student_cgpa = float(student_data.get("cgpa") or 0.0)

    for rule in rules:
        course_id = rule.recommended_course_id
        course_fact = None
        if knowledge_base:
            course_fact = knowledge_base.get_course_by_id(course_id)

        course_code = rule.course_code or (course_fact.course_code if course_fact else f"COURSE-{course_id}")
        course_name = rule.course_name or (course_fact.course_name if course_fact else f"Course #{course_id}")

        # Check course availability
        if course_fact and hasattr(course_fact, "is_active") and not course_fact.is_active:
            rejected_evaluations.append({
                "rule_name": rule.rule_name,
                "course_id": course_id,
                "course_code": course_code,
                "course_name": course_name,
                "reason": "Course is currently inactive in the university curriculum.",
                "priority": rule.priority
            })
            continue

        # Evaluate rule
        eval_result = RuleEvaluator.evaluate(rule, student_data, course_fact=course_fact)

        # Log evaluation step
        logger.log_evaluation(
            rule_name=rule.rule_name,
            course_id=course_id,
            course_code=course_code,
            course_name=course_name,
            match_score=eval_result.match_score,
            is_matched=eval_result.is_matched,
            matched_conditions=eval_result.matched_conditions,
            failed_conditions=eval_result.failed_conditions,
            reasons=eval_result.reasons,
            rationale=rule.conditions.rationale
        )

        if eval_result.is_matched:
            # Format comprehensive explanation
            interests_str = ", ".join(eval_result.matched_interests) if eval_result.matched_interests else "related subjects"
            career_str = eval_result.matched_career_goals[0] if eval_result.matched_career_goals else str(student_data.get("career_goal") or "their career field")
            req_cgpa_val = float(course_fact.minimum_cgpa if course_fact else rule.conditions.min_cgpa)

            explanation = (
                f"{course_name} was recommended because the student has an interest in {interests_str}, "
                f"selected {career_str} as their career goal, "
                f"and meets the minimum CGPA requirement of {req_cgpa_val:.2f}."
            )

            # Avoid duplicate recommendations: merge reasons and keep highest priority
            if course_id in recommendations_map:
                existing = recommendations_map[course_id]
                existing["priority"] = max(existing["priority"], rule.priority)
                existing["match_score"] = max(existing["match_score"], eval_result.match_score)
                existing["fired_rules"].append(rule.rule_name)
                # Merge unique reasons
                for r_text in eval_result.reasons:
                    if r_text not in existing["reasons"]:
                        existing["reasons"].append(r_text)
            else:
                recommendations_map[course_id] = {
                    "course_id": course_id,
                    "course_code": course_code,
                    "course_name": course_name,
                    "priority": rule.priority,
                    "match_score": round(eval_result.match_score, 2),
                    "reasons": eval_result.reasons,
                    "explanation": explanation,
                    "fired_rules": [rule.rule_name]
                }
        else:
            # Build rejection reason summary
            fail_summary = "; ".join(eval_result.failed_conditions) if eval_result.failed_conditions else "Rule criteria not satisfied."
            rejected_evaluations.append({
                "rule_name": rule.rule_name,
                "course_id": course_id,
                "course_code": course_code,
                "course_name": course_name,
                "reason": fail_summary,
                "priority": rule.priority,
                "failed_conditions": eval_result.failed_conditions
            })

    # Sort recommended courses by priority descending, then match score descending
    sorted_recommendations = sorted(
        recommendations_map.values(),
        key=lambda x: (x["priority"], x["match_score"]),
        reverse=True
    )

    return {
        "recommended_courses": sorted_recommendations,
        "rejected_evaluations": rejected_evaluations,
        "audit_trail": logger.get_audit_trail(),
        "total_rules_evaluated": len(rules),
        "total_rules_fired": len(logger.get_fired_steps())
    }
