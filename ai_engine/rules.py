"""
Rule Definitions and Knowledge Representation Module
Phase 7: Rule-Based Reasoning Engine

Defines declarative production rules (IF antecedents -> THEN consequences)
supporting multi-condition evaluations, AND ('all') / OR ('any') logical operators,
and course recommendation actions.

STRICT SAFETY REQUIREMENT:
Zero dynamic code execution. No eval(), exec(), or arbitrary code.
All fields and operators are validated against explicit allowlists.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
import json

# Allowed fields in rule conditions
ALLOWED_FIELDS = (
    "interests",
    "career_goal",
    "cgpa",
    "department",
    "semester",
    "completed_courses"
)

# Allowed comparison operators in rule conditions
ALLOWED_OPERATORS = (
    "equals",
    "not_equals",
    "contains",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal"
)


@dataclass
class RulePredicate:
    """
    Individual atomic condition predicate in a production rule antecedent.
    Example:
        {"field": "interests", "operator": "contains", "value": "Python"}
        {"field": "career_goal", "operator": "equals", "value": "Data Scientist"}
        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 7.5}
    """
    field: str
    operator: str
    value: Any

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validates that field and operator belong to approved allowlists."""
        if not self.field or not isinstance(self.field, str):
            raise ValueError(f"Invalid condition field '{self.field}'. Must be a non-empty string.")
        
        field_norm = self.field.strip().lower()
        if field_norm not in ALLOWED_FIELDS:
            raise ValueError(
                f"Field '{self.field}' is not allowed. Allowed fields: {', '.join(ALLOWED_FIELDS)}"
            )

        if not self.operator or not isinstance(self.operator, str):
            raise ValueError(f"Invalid operator '{self.operator}'. Must be a non-empty string.")

        op_norm = self.operator.strip().lower()
        if op_norm not in ALLOWED_OPERATORS:
            raise ValueError(
                f"Operator '{self.operator}' is not supported. Allowed operators: {', '.join(ALLOWED_OPERATORS)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes predicate to dictionary."""
        return {
            "field": self.field.strip().lower(),
            "operator": self.operator.strip().lower(),
            "value": self.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RulePredicate":
        """Factory creating a RulePredicate from a raw dictionary."""
        if not isinstance(data, dict):
            raise ValueError(f"Predicate data must be a dictionary, got {type(data).__name__}")
        return cls(
            field=str(data.get("field", "")),
            operator=str(data.get("operator", "")),
            value=data.get("value")
        )


@dataclass
class ConditionGroup:
    """
    Represents structured compound conditions supporting AND ('all') and OR ('any') logical operators.
    Fully backwards-compatible with legacy dictionary structures.
    """
    all: List[RulePredicate] = field(default_factory=list)
    any: List[RulePredicate] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serializes compound conditions to dictionary."""
        res: Dict[str, Any] = {
            "all": [p.to_dict() for p in self.all],
            "any": [p.to_dict() for p in self.any]
        }
        if self.rationale:
            res["rationale"] = self.rationale

        # Preserve legacy fields for template and backward compatibility
        res["min_cgpa"] = self.min_cgpa
        res["min_semester"] = self.min_semester
        res["required_interests"] = self.required_interests
        res["preferred_career_goals"] = self.preferred_career_goals
        return res

    @property
    def min_cgpa(self) -> float:
        """Extracts minimum CGPA threshold from predicates."""
        for p in self.all + self.any:
            if p.field == "cgpa" and p.operator in ("greater_than_or_equal", "greater_than", "equals"):
                try:
                    return float(p.value)
                except (ValueError, TypeError):
                    pass
        return 0.0

    @property
    def min_semester(self) -> int:
        """Extracts minimum semester requirement from predicates."""
        for p in self.all + self.any:
            if p.field == "semester" and p.operator in ("greater_than_or_equal", "greater_than", "equals"):
                try:
                    return int(p.value)
                except (ValueError, TypeError):
                    pass
        return 1

    @property
    def required_interests(self) -> List[str]:
        """Extracts interest values required by conditions."""
        res = []
        for p in self.all + self.any:
            if p.field == "interests" and p.operator in ("contains", "equals"):
                if isinstance(p.value, (list, tuple)):
                    res.extend([str(x) for x in p.value])
                elif p.value is not None:
                    res.append(str(p.value))
        return list(dict.fromkeys(res))

    @property
    def preferred_career_goals(self) -> List[str]:
        """Extracts career goal values preferred by conditions."""
        res = []
        for p in self.all + self.any:
            if p.field == "career_goal" and p.operator in ("equals", "contains"):
                if isinstance(p.value, (list, tuple)):
                    res.extend([str(x) for x in p.value])
                elif p.value is not None:
                    res.append(str(p.value))
        return list(dict.fromkeys(res))

    @classmethod
    def from_dict(cls, data: Union[Dict[str, Any], str]) -> "ConditionGroup":
        """
        Parses condition specifications from a dictionary or JSON string.
        Handles both modern Phase 7 {'all': [...], 'any': [...]} structure
        and legacy Phase 6 {'min_cgpa': ..., 'required_interests': ...} format.
        """
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {}

        if not isinstance(data, dict):
            return cls()

        # If nested inside 'conditions': { ... }
        if "conditions" in data and isinstance(data["conditions"], dict):
            data = data["conditions"]

        all_preds: List[RulePredicate] = []
        any_preds: List[RulePredicate] = []
        rationale = str(data.get("rationale") or "")

        # 1. Parse 'all' (AND) predicates
        if "all" in data and isinstance(data["all"], list):
            for item in data["all"]:
                if isinstance(item, dict):
                    all_preds.append(RulePredicate.from_dict(item))

        # 2. Parse 'any' (OR) predicates
        if "any" in data and isinstance(data["any"], list):
            for item in data["any"]:
                if isinstance(item, dict):
                    any_preds.append(RulePredicate.from_dict(item))

        # 3. Legacy compatibility fallback: convert legacy fields if all/any were empty
        if not all_preds and not any_preds:
            if "min_cgpa" in data and float(data.get("min_cgpa") or 0.0) > 0.0:
                all_preds.append(RulePredicate("cgpa", "greater_than_or_equal", float(data["min_cgpa"])))

            if "min_semester" in data and int(data.get("min_semester") or 1) > 1:
                all_preds.append(RulePredicate("semester", "greater_than_or_equal", int(data["min_semester"])))

            req_ints = data.get("required_interests") or []
            if isinstance(req_ints, list) and req_ints:
                for item in req_ints:
                    any_preds.append(RulePredicate("interests", "contains", str(item)))

            pref_goals = data.get("preferred_career_goals") or []
            if isinstance(pref_goals, list) and pref_goals:
                for item in pref_goals:
                    any_preds.append(RulePredicate("career_goal", "equals", str(item)))

        return cls(all=all_preds, any=any_preds, rationale=rationale)


# Alias for backward compatibility
RuleCondition = ConditionGroup


@dataclass
class RuleAction:
    """
    Action consequent of a production rule.
    Example:
        {"type": "recommend_course", "course_id": 1}
    """
    type: str = "recommend_course"
    course_id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "course_id": int(self.course_id)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuleAction":
        if not isinstance(data, dict):
            return cls()
        return cls(
            type=str(data.get("type", "recommend_course")),
            course_id=int(data.get("course_id", 0))
        )


@dataclass
class ProductionRule:
    """
    Formal representation of a Production Rule in the Knowledge Base.
    IF antecedent conditions are satisfied THEN execute recommendation action.
    """
    id: Optional[int]
    rule_name: str
    conditions: ConditionGroup
    action: RuleAction
    priority: int = 5
    is_active: bool = True
    course_code: Optional[str] = None
    course_name: Optional[str] = None

    @property
    def recommended_course_id(self) -> int:
        """Helper mapping to action's recommended course ID."""
        return self.action.course_id

    @recommended_course_id.setter
    def recommended_course_id(self, val: int) -> None:
        self.action.course_id = int(val)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes rule into a clean JSON-ready dictionary."""
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "conditions": self.conditions.to_dict(),
            "action": self.action.to_dict(),
            "priority": self.priority,
            "is_active": self.is_active,
            "recommended_course_id": self.recommended_course_id,
            "course_code": self.course_code,
            "course_name": self.course_name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductionRule":
        """Instantiates ProductionRule from a structured dictionary."""
        course_id = 0
        if "action" in data and isinstance(data["action"], dict):
            action_obj = RuleAction.from_dict(data["action"])
        elif "recommended_course_id" in data:
            action_obj = RuleAction("recommend_course", int(data["recommended_course_id"]))
        else:
            action_obj = RuleAction("recommend_course", 0)

        cond_raw = data.get("conditions", {})
        cond_obj = ConditionGroup.from_dict(cond_raw)

        return cls(
            id=data.get("id"),
            rule_name=str(data.get("rule_name", "")),
            conditions=cond_obj,
            action=action_obj,
            priority=int(data.get("priority") or 5),
            is_active=bool(data.get("is_active", True)),
            course_code=data.get("course_code"),
            course_name=data.get("course_name")
        )

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "ProductionRule":
        """Factory method constructing a ProductionRule from a MySQL query row."""
        raw_conds = row.get("conditions")
        cond_obj = ConditionGroup.from_dict(raw_conds)

        course_id = int(row.get("recommended_course_id") or 0)
        action_obj = RuleAction(type="recommend_course", course_id=course_id)

        return cls(
            id=row.get("id"),
            rule_name=str(row.get("rule_name", "")),
            conditions=cond_obj,
            action=action_obj,
            priority=int(row.get("priority") or 5),
            is_active=bool(row.get("is_active", True)),
            course_code=row.get("course_code"),
            course_name=row.get("course_name")
        )
