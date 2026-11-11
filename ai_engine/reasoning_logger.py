"""
Reasoning Logger Module
Phase 7: Rule-Based Reasoning Engine

Captures, logs, formats, and persists step-by-step reasoning deductions.
Provides human-interpretable audit trails explaining why courses were suggested or rejected,
and records recommendations to the MySQL recommendation_history table.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.db_connection import get_db_cursor


@dataclass
class ReasoningStep:
    """Individual inference step recorded during rule evaluation."""
    step_id: int
    rule_name: str
    course_id: int
    course_code: str
    course_name: str
    match_score: float
    status: str  # 'FIRED', 'REJECTED'
    explanation: str
    matched_conditions: List[str] = field(default_factory=list)
    failed_conditions: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        """Serializes reasoning step to a dictionary."""
        return {
            "step_id": self.step_id,
            "rule_name": self.rule_name,
            "course_id": self.course_id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "match_score": round(self.match_score, 2),
            "status": self.status,
            "explanation": self.explanation,
            "matched_conditions": self.matched_conditions,
            "failed_conditions": self.failed_conditions,
            "reasons": self.reasons,
            "timestamp": self.timestamp
        }


class ReasoningLogger:
    """Logs and maintains an audit trail of deductive reasoning steps."""

    def __init__(self):
        self._steps: List[ReasoningStep] = []
        self._counter: int = 1

    def log_evaluation(self, rule_name: str, course_id: int, course_code: str,
                       course_name: str, match_score: float, is_matched: bool,
                       matched_conditions: Optional[List[str]] = None,
                       failed_conditions: Optional[List[str]] = None,
                       reasons: Optional[List[str]] = None,
                       rationale: str = "") -> ReasoningStep:
        """Records a rule evaluation outcome into the reasoning log."""
        status = "FIRED" if is_matched else "REJECTED"
        m_conds = list(matched_conditions or [])
        f_conds = list(failed_conditions or [])
        r_list = list(reasons or [])

        explanation_parts = []
        if is_matched:
            explanation_parts.append(f"Rule '{rule_name}' fired with {match_score:.1f}% confidence for {course_name} ({course_code}).")
            if m_conds:
                explanation_parts.append("Matched conditions: " + "; ".join(m_conds) + ".")
        else:
            explanation_parts.append(f"Rule '{rule_name}' rejected for {course_name} ({course_code}).")
            if f_conds:
                explanation_parts.append("Failed conditions: " + "; ".join(f_conds) + ".")

        if rationale:
            explanation_parts.append(f"Rationale: {rationale}")

        full_explanation = " ".join(explanation_parts)

        step = ReasoningStep(
            step_id=self._counter,
            rule_name=rule_name,
            course_id=course_id,
            course_code=course_code,
            course_name=course_name,
            match_score=match_score,
            status=status,
            explanation=full_explanation,
            matched_conditions=m_conds,
            failed_conditions=f_conds,
            reasons=r_list
        )
        self._steps.append(step)
        self._counter += 1
        return step

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Returns the complete sequence of logged reasoning steps."""
        return [s.to_dict() for s in self._steps]

    def get_history(self) -> List[Dict[str, Any]]:
        """Alias for get_audit_trail for backward compatibility."""
        return self.get_audit_trail()

    def get_fired_steps(self) -> List[Dict[str, Any]]:
        """Returns only the steps where rules were successfully fired."""
        return [s.to_dict() for s in self._steps if s.status == "FIRED"]

    def get_rejected_steps(self) -> List[Dict[str, Any]]:
        """Returns only the steps where rules were rejected."""
        return [s.to_dict() for s in self._steps if s.status == "REJECTED"]

    def format_student_explanation(self, course_code: str) -> str:
        """Extracts and formats user-facing explanation for a recommended course."""
        matching_steps = [s for s in self._steps if s.course_code == course_code and s.status == "FIRED"]
        if not matching_steps:
            return f"Course {course_code} is recommended based on academic curriculum rules."

        best_step = max(matching_steps, key=lambda s: s.match_score)
        return best_step.explanation

    @staticmethod
    def persist_recommendation(student_id: int, course_id: int,
                               score: float, reasoning: str) -> int:
        """
        Persists a final recommendation record to MySQL recommendation_history.
        """
        query = """
            INSERT INTO recommendation_history (student_id, recommended_course_id, recommendation_score, reasoning)
            VALUES (%s, %s, %s, %s)
        """
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (student_id, course_id, round(float(score), 2), reasoning))
            return cursor.lastrowid

    def clear(self) -> None:
        """Resets the internal reasoning logger state."""
        self._steps.clear()
        self._counter = 1
