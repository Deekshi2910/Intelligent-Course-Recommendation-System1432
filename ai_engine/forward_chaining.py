"""
Forward Chaining Inference Engine Module
Intelligent Course Recommendation System

Implements the data-driven Forward Chaining algorithm (Match -> Resolve -> Act cycle):
- Working Memory: Holds initial student facts, derived facts, and candidate course recommendations.
- Rule Agenda: Active production rules from MySQL Knowledge Base.
- Match Phase: Identifies rules whose condition antecedents match current working memory.
- Conflict Resolution: Prioritizes rules by Priority descending, specificity, and refractory prevention.
- Act Phase: Executes recommendation actions, updates working memory, and logs deductions.
- Cycles until quiescence (fixed point).

Strict Safety: Strictly zero eval() / exec() usage.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple
from ai_engine.rules import ProductionRule
from ai_engine.rule_evaluator import RuleEvaluator, RuleEvaluationResult
from ai_engine.reasoning_logger import ReasoningLogger, ReasoningStep


@dataclass
class FiredRuleRecord:
    """Audit record for a production rule that successfully fired during forward chaining."""
    rule_id: Optional[int]
    rule_name: str
    course_id: int
    course_code: str
    course_name: str
    priority: int
    match_score: float
    matched_conditions: List[str]
    reasons: List[str]
    cycle: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "course_id": self.course_id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "priority": self.priority,
            "match_score": round(self.match_score, 2),
            "matched_conditions": self.matched_conditions,
            "reasons": self.reasons,
            "cycle": self.cycle
        }


class ForwardChainingEngine:
    """
    Executes forward-chaining deductive inference over production rules.
    Operates via Match-Resolve-Act iterations until fixed-point quiescence.
    """

    def __init__(self, max_cycles: int = 10):
        self.max_cycles = max_cycles

    def run(self, working_memory: Dict[str, Any],
            rules: List[ProductionRule],
            knowledge_base: Optional[Any] = None,
            logger: Optional[ReasoningLogger] = None) -> Dict[str, Any]:
        """
        Executes the forward chaining cycle:
        1. Initialize working memory with student profile facts.
        2. Match rules against working memory facts.
        3. Resolve conflicts via priority ordering.
        4. Fire eligible rules, asserting recommendations and derived facts.
        5. Terminate when no new rules can fire (quiescence) or max cycles reached.
        """
        facts = dict(working_memory)
        fired_rules: List[FiredRuleRecord] = []
        already_fired_rule_ids: Set[Any] = set()
        candidate_courses_map: Dict[int, Dict[str, Any]] = {}
        cycle = 1

        while cycle <= self.max_cycles:
            # 1. Match Phase: Find all rules whose antecedents are satisfied
            match_candidates: List[Tuple[ProductionRule, RuleEvaluationResult, Any]] = []

            for rule in rules:
                if not rule.is_active:
                    continue
                rule_key = rule.id or rule.rule_name
                # Refraction: Prevent re-firing the exact same rule in subsequent cycles
                if rule_key in already_fired_rule_ids:
                    continue

                course_id = rule.recommended_course_id
                course_fact = knowledge_base.get_course_by_id(course_id) if knowledge_base else None

                eval_result = RuleEvaluator.evaluate(rule, facts, course_fact=course_fact)

                if eval_result.is_matched:
                    match_candidates.append((rule, eval_result, course_fact))
                else:
                    if logger and cycle == 1:
                        # Log non-matching rules during initial pass
                        c_code = rule.course_code or (course_fact.course_code if course_fact else f"C-{course_id}")
                        c_name = rule.course_name or (course_fact.course_name if course_fact else f"Course #{course_id}")
                        logger.log_evaluation(
                            rule_name=rule.rule_name,
                            course_id=course_id,
                            course_code=c_code,
                            course_name=c_name,
                            match_score=eval_result.match_score,
                            is_matched=False,
                            matched_conditions=eval_result.matched_conditions,
                            failed_conditions=eval_result.failed_conditions,
                            reasons=eval_result.reasons,
                            rationale=rule.conditions.rationale
                        )

            # Quiescence check: No new rules can fire
            if not match_candidates:
                break

            # 2. Conflict Resolution Phase:
            # Sort candidate rules by priority descending, then match score descending
            match_candidates.sort(
                key=lambda item: (item[0].priority, item[1].match_score),
                reverse=True
            )

            # 3. Act Phase: Fire rules in priority order
            new_firings_in_cycle = 0
            for rule, eval_res, course_fact in match_candidates:
                rule_key = rule.id or rule.rule_name
                already_fired_rule_ids.add(rule_key)
                new_firings_in_cycle += 1

                course_id = rule.recommended_course_id
                c_code = rule.course_code or (course_fact.course_code if course_fact else f"CS-{course_id}")
                c_name = rule.course_name or (course_fact.course_name if course_fact else f"Course #{course_id}")

                record = FiredRuleRecord(
                    rule_id=rule.id,
                    rule_name=rule.rule_name,
                    course_id=course_id,
                    course_code=c_code,
                    course_name=c_name,
                    priority=rule.priority,
                    match_score=eval_res.match_score,
                    matched_conditions=eval_res.matched_conditions,
                    reasons=eval_res.reasons,
                    cycle=cycle
                )
                fired_rules.append(record)

                if logger:
                    logger.log_evaluation(
                        rule_name=rule.rule_name,
                        course_id=course_id,
                        course_code=c_code,
                        course_name=c_name,
                        match_score=eval_res.match_score,
                        is_matched=True,
                        matched_conditions=eval_res.matched_conditions,
                        failed_conditions=eval_res.failed_conditions,
                        reasons=eval_res.reasons,
                        rationale=rule.conditions.rationale
                    )

                # Deduplicate course recommendations in working memory
                if course_id in candidate_courses_map:
                    cand = candidate_courses_map[course_id]
                    cand["priority"] = max(cand["priority"], rule.priority)
                    cand["match_score"] = max(cand["match_score"], eval_res.match_score)
                    cand["fired_rules"].append(rule.rule_name)
                    for r_text in eval_res.reasons:
                        if r_text not in cand["reasons"]:
                            cand["reasons"].append(r_text)
                else:
                    candidate_courses_map[course_id] = {
                        "course_id": course_id,
                        "course_code": c_code,
                        "course_name": c_name,
                        "priority": rule.priority,
                        "match_score": round(eval_res.match_score, 2),
                        "reasons": list(eval_res.reasons),
                        "fired_rules": [rule.rule_name],
                        "matched_interests": list(eval_res.matched_interests),
                        "matched_career_goals": list(eval_res.matched_career_goals)
                    }

                # Assert new intermediate derived facts into working memory
                # E.g., student qualifies for course_id
                facts[f"qualified_for_course_{course_id}"] = True

            if new_firings_in_cycle == 0:
                break
            cycle += 1

        return {
            "candidate_courses": list(candidate_courses_map.values()),
            "fired_rules": [r.to_dict() for r in fired_rules],
            "total_cycles": cycle - 1,
            "final_working_memory": facts
        }
