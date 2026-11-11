"""
Assumption Manager Module
Phase 8: Default Reasoning Engine

Tracks hypothetical beliefs, assumptions, justifications, and belief revisions
in non-monotonic Default Reasoning.

Key Guarantees:
- Distinguishes actual student preferences from temporary default assumptions.
- Stores assumption reasons and timestamps.
- Marks all assumptions as temporary.
- Enables assumption withdrawal (retraction) when new student facts become available.
- Never permanently overwrites actual student preferences in MySQL or memory.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


@dataclass
class Assumption:
    """
    Represents an individual hypothetical belief adopted during default reasoning.
    """
    assumption_id: str
    field: str
    assumed_value: Any
    reason: str
    source_rule: str  # e.g., 'DR01', 'DR02', 'DR03', 'DR05'
    is_temporary: bool = True
    status: str = "ACTIVE"  # 'ACTIVE' or 'WITHDRAWN'
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    withdrawn_at: Optional[str] = None
    withdrawal_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes assumption to dictionary."""
        return {
            "assumption_id": self.assumption_id,
            "field": self.field,
            "assumed_value": self.assumed_value,
            "reason": self.reason,
            "source_rule": self.source_rule,
            "is_temporary": self.is_temporary,
            "status": self.status,
            "created_at": self.created_at,
            "withdrawn_at": self.withdrawn_at,
            "withdrawal_reason": self.withdrawal_reason
        }


class AssumptionManager:
    """
    Maintains an active set of hypothetical assumptions and coordinates
    belief revision when new actual student information is observed.
    """

    def __init__(self):
        self._assumptions: Dict[str, Assumption] = {}
        self._history: List[Assumption] = []
        self._counter: int = 1

    def record_assumption(self, field_name: str, assumed_value: Any,
                          reason: str, source_rule: str) -> Assumption:
        """
        Adopts a temporary default assumption when actual student information is absent.
        """
        assump_id = f"ASM-{self._counter:03d}"
        self._counter += 1

        assumption = Assumption(
            assumption_id=assump_id,
            field=field_name,
            assumed_value=assumed_value,
            reason=reason,
            source_rule=source_rule,
            is_temporary=True,
            status="ACTIVE"
        )
        self._assumptions[field_name] = assumption
        self._history.append(assumption)
        return assumption

    def withdraw_assumption(self, field_name: str, reason: str) -> Optional[Assumption]:
        """
        Withdraws (retracts) a previously held assumption.
        Triggered when actual student preferences become available.
        """
        if field_name in self._assumptions:
            assumption = self._assumptions[field_name]
            if assumption.status == "ACTIVE":
                assumption.status = "WITHDRAWN"
                assumption.withdrawn_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                assumption.withdrawal_reason = reason
                del self._assumptions[field_name]
                return assumption
        return None

    def reconcile_with_actual_data(self, actual_data: Dict[str, Any]) -> List[str]:
        """
        Compares incoming actual student facts against active assumptions.
        If actual data is provided for an assumed field, withdraws the assumption.
        Returns a list of withdrawal audit logs.
        """
        withdrawal_logs: List[str] = []

        # Check career_goal
        if "career_goal" in self._assumptions and actual_data.get("career_goal"):
            val = str(actual_data.get("career_goal") or "").strip()
            if val:
                withdrawn = self.withdraw_assumption(
                    "career_goal",
                    f"Student explicitly provided actual career goal: '{val}'"
                )
                if withdrawn:
                    withdrawal_logs.append(
                        f"Withdrew default assumption on career goal '{withdrawn.assumed_value}' "
                        f"because actual goal '{val}' was provided."
                    )

        # Check interests
        if "interests" in self._assumptions and actual_data.get("interests"):
            interests = actual_data.get("interests")
            if isinstance(interests, (list, tuple, set)) and len(interests) > 0:
                withdrawn = self.withdraw_assumption(
                    "interests",
                    f"Student explicitly provided actual interests: {list(interests)}"
                )
                if withdrawn:
                    withdrawal_logs.append(
                        f"Withdrew default assumption on interests "
                        f"because actual interests were provided: {list(interests)}"
                    )

        # Check CGPA
        if "cgpa" in self._assumptions and actual_data.get("cgpa") is not None:
            withdrawn = self.withdraw_assumption(
                "cgpa",
                f"Student provided actual CGPA: {actual_data.get('cgpa')}"
            )
            if withdrawn:
                withdrawal_logs.append("Withdrew default assumption on CGPA.")

        return withdrawal_logs

    def build_working_profile(self, actual_student_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, bool]]:
        """
        Builds a combined working profile while strictly preserving the distinction
        between actual student facts and assumed fallback facts.

        Actual student information ALWAYS overrides assumptions.
        Never permanently modifies the original student profile dictionary.

        Returns:
            (working_profile, is_assumed_map)
        """
        working = dict(actual_student_profile)
        is_assumed_map: Dict[str, bool] = {
            "cgpa": False,
            "interests": False,
            "career_goal": False,
            "prerequisites": False
        }

        # For each active assumption, apply to working profile only if missing in actual
        for field_name, assumption in self._assumptions.items():
            actual_val = actual_student_profile.get(field_name)

            is_missing = False
            if actual_val is None:
                is_missing = True
            elif isinstance(actual_val, (list, tuple, set)) and len(actual_val) == 0:
                is_missing = True
            elif isinstance(actual_val, str) and actual_val.strip() == "":
                is_missing = True

            if is_missing:
                working[field_name] = assumption.assumed_value
                is_assumed_map[field_name] = True

        return working, is_assumed_map

    def has_active_assumption(self, field_name: str) -> bool:
        """Returns True if there is currently an active assumption for the field."""
        return field_name in self._assumptions and self._assumptions[field_name].status == "ACTIVE"

    def get_active_assumptions(self) -> List[Assumption]:
        """Returns all currently active assumptions."""
        return list(self._assumptions.values())

    def get_assumption_history(self) -> List[Dict[str, Any]]:
        """Returns full audit trail of all assumptions created and withdrawn."""
        return [a.to_dict() for a in self._history]

    def clear(self) -> None:
        """Resets active assumptions while preserving counter."""
        self._assumptions.clear()
        self._history.clear()
        self._counter = 1
