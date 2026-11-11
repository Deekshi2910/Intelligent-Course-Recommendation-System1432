"""
Default Rules Module
Phase 8: Default Reasoning Engine

Defines canonical default rules (DR01 - DR05) based on non-monotonic Default Logic.
Handles partial, missing, or unstated student profile facts:
- DR01: Missing Career Goal (Interest-based fallback)
- DR02: Missing Interests (Career-based fallback)
- DR03: Missing Both Interests & Career Goal (General foundational recommendations)
- DR04: Missing CGPA (Request academic info, never assume CGPA)
- DR05: Unknown Prerequisites (Mark unverified, never assume satisfied)

Includes database persistence and lifecycle management for administrative activation/deactivation.
STRICT SAFETY REQUIREMENT: Zero eval() / exec() usage.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import json
from database.db_connection import get_db_cursor


@dataclass
class DefaultRule:
    """
    Formal representation of a Default Rule in Non-Monotonic Logic.
    Identified by a canonical rule code (e.g. DR01, DR02, DR03, DR04, DR05).
    """
    rule_code: str
    rule_name: str
    fallback_strategy: str  # 'interest_based', 'career_based', 'general_foundational', 'request_academic_info', 'unverified_prerequisites'
    description: str
    priority: int = 1
    is_active: bool = True
    rationale: str = ""
    explanation_template: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serializes default rule to dictionary."""
        return {
            "rule_code": self.rule_code,
            "rule_name": self.rule_name,
            "fallback_strategy": self.fallback_strategy,
            "description": self.description,
            "priority": self.priority,
            "is_active": self.is_active,
            "rationale": self.rationale,
            "explanation_template": self.explanation_template
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DefaultRule":
        """Instantiates DefaultRule from dictionary."""
        return cls(
            rule_code=str(data.get("rule_code", "")),
            rule_name=str(data.get("rule_name", "")),
            fallback_strategy=str(data.get("fallback_strategy", "")),
            description=str(data.get("description", "")),
            priority=int(data.get("priority") or 1),
            is_active=bool(data.get("is_active", True)),
            rationale=str(data.get("rationale", "")),
            explanation_template=str(data.get("explanation_template", ""))
        )


CANONICAL_DEFAULT_RULES: List[DefaultRule] = [
    DefaultRule(
        rule_code="DR01",
        rule_name="Missing Career Goal Fallback",
        fallback_strategy="interest_based",
        description="IF career goal is missing AND student interests are available, THEN generate interest-based recommendations.",
        priority=4,
        is_active=True,
        rationale="When career aspirations are undeclared, domain interest ontologies provide the strongest personal signal.",
        explanation_template="Your career goal was not provided. Therefore, the system used your selected interests to identify suitable courses."
    ),
    DefaultRule(
        rule_code="DR02",
        rule_name="Missing Interests Fallback",
        fallback_strategy="career_based",
        description="IF student interests are missing AND career goal is available, THEN generate career-based recommendations.",
        priority=3,
        is_active=True,
        rationale="When specific technical topics are undeclared, target career pathways define the required curriculum competencies.",
        explanation_template="Your interests were not provided. Therefore, the system used your selected career goal to identify suitable courses."
    ),
    DefaultRule(
        rule_code="DR03",
        rule_name="Missing Interests and Career Goal",
        fallback_strategy="general_foundational",
        description="IF interests and career goal are both missing, THEN generate general foundational course recommendations.",
        priority=2,
        is_active=True,
        rationale="When neither interests nor career goals are declared, recommend introductory breadth electives.",
        explanation_template="Neither interests nor career goals were provided. These are general foundational recommendations and may not match your personal preferences."
    ),
    DefaultRule(
        rule_code="DR04",
        rule_name="Missing CGPA Academic Request",
        fallback_strategy="request_academic_info",
        description="IF CGPA is missing, THEN request academic information. Do not assume a CGPA value.",
        priority=5,
        is_active=True,
        rationale="Academic eligibility requires explicit verification; never hallucinate or assume student GPA.",
        explanation_template="Your CGPA is missing. Please provide your CGPA before eligibility can be confirmed."
    ),
    DefaultRule(
        rule_code="DR05",
        rule_name="Unknown Prerequisites Verification",
        fallback_strategy="unverified_prerequisites",
        description="IF prerequisite information is unavailable or unverified, THEN mark eligibility as unverified. Do not assume prerequisites are satisfied.",
        priority=1,
        is_active=True,
        rationale="Course prerequisites represent hard academic dependencies and cannot be assumed without evidence.",
        explanation_template="Prerequisite completion status is unverified. Prerequisites cannot be assumed to be satisfied."
    )
]


class DefaultRuleManager:
    """Manages storage, retrieval, synchronization, and toggling of Default Rules."""

    @classmethod
    def ensure_table_exists(cls) -> None:
        """Ensures the default_rules table exists in MySQL and is populated."""
        create_sql = """
            CREATE TABLE IF NOT EXISTS default_rules (
                rule_code VARCHAR(20) PRIMARY KEY,
                rule_name VARCHAR(100) NOT NULL,
                fallback_strategy VARCHAR(100) NOT NULL,
                description TEXT,
                priority INT DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                rationale TEXT,
                explanation_template TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        try:
            with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
                cursor.execute(create_sql)
                # Seed canonical rules if table is empty
                cursor.execute("SELECT COUNT(*) AS total FROM default_rules")
                row = cursor.fetchone()
                if row and row["total"] == 0:
                    for r in CANONICAL_DEFAULT_RULES:
                        cursor.execute("""
                            INSERT INTO default_rules (rule_code, rule_name, fallback_strategy, description, priority, is_active, rationale, explanation_template)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (r.rule_code, r.rule_name, r.fallback_strategy, r.description, r.priority, r.is_active, r.rationale, r.explanation_template))
        except Exception:
            # Fall back safely if MySQL table creation is restricted
            pass

    @classmethod
    def get_all_rules(cls, active_only: bool = False) -> List[DefaultRule]:
        """Retrieves default rules from MySQL, falling back to canonical in-memory rules."""
        cls.ensure_table_exists()
        try:
            with get_db_cursor(dictionary=True) as (cursor, _):
                query = "SELECT * FROM default_rules"
                if active_only:
                    query += " WHERE is_active = TRUE"
                query += " ORDER BY priority DESC, rule_code ASC"
                cursor.execute(query)
                rows = cursor.fetchall()
                if rows:
                    return [DefaultRule.from_dict(r) for r in rows]
        except Exception:
            pass

        # Fallback to in-memory canonical list
        if active_only:
            return [r for r in CANONICAL_DEFAULT_RULES if r.is_active]
        return list(CANONICAL_DEFAULT_RULES)

    @classmethod
    def get_rule_by_code(cls, rule_code: str) -> Optional[DefaultRule]:
        """Retrieves a single default rule by rule code."""
        rules = cls.get_all_rules(active_only=False)
        for r in rules:
            if r.rule_code.upper() == rule_code.upper():
                return r
        return None

    @classmethod
    def toggle_rule(cls, rule_code: str) -> bool:
        """Toggles active/inactive state of a default rule in MySQL."""
        cls.ensure_table_exists()
        try:
            with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
                cursor.execute("SELECT is_active FROM default_rules WHERE rule_code = %s", (rule_code,))
                row = cursor.fetchone()
                if not row:
                    return False
                new_status = not bool(row["is_active"])
                cursor.execute("UPDATE default_rules SET is_active = %s WHERE rule_code = %s", (new_status, rule_code))
                return True
        except Exception:
            # In-memory toggle fallback
            for r in CANONICAL_DEFAULT_RULES:
                if r.rule_code.upper() == rule_code.upper():
                    r.is_active = not r.is_active
                    return True
        return False


def get_canonical_default_rules() -> List[DefaultRule]:
    """Helper returning active default rules."""
    return DefaultRuleManager.get_all_rules(active_only=True)
