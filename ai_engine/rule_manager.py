"""
Rule Manager Module
Phase 7: Rule-Based Reasoning Engine

Manages persistence, retrieval, prioritization, validation, and lifecycle
of AI production rules stored in MySQL knowledge_rules table.
STRICT SAFETY REQUIREMENT:
Zero dynamic code execution. Explicit allowlist validation on all fields and operators.
"""

from typing import List, Dict, Any, Optional, Union
import json
from database.db_connection import get_db_cursor
from ai_engine.rules import (
    ProductionRule,
    ConditionGroup,
    RulePredicate,
    RuleAction,
    ALLOWED_FIELDS,
    ALLOWED_OPERATORS
)


class RuleManager:
    """Manages persistence, retrieval, and prioritization of AI production rules."""

    def __init__(self):
        pass

    def get_all_rules(self, active_only: bool = True) -> List[ProductionRule]:
        """
        Retrieves all production rules from MySQL, joined with course metadata.
        Ordered by priority descending (highest priority rules evaluated first).
        """
        query = """
            SELECT
                kr.id,
                kr.rule_name,
                kr.conditions,
                kr.recommended_course_id,
                kr.priority,
                kr.is_active,
                c.course_code,
                c.course_name
            FROM knowledge_rules kr
            JOIN courses c ON kr.recommended_course_id = c.id
        """
        params = []
        if active_only:
            query += " WHERE kr.is_active = TRUE AND c.is_active = TRUE"

        query += " ORDER BY kr.priority DESC, kr.id ASC"

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        return [ProductionRule.from_db_row(r) for r in rows]

    def get_rule_by_id(self, rule_id: int) -> Optional[ProductionRule]:
        """Retrieves a single production rule by primary key ID."""
        query = """
            SELECT
                kr.id,
                kr.rule_name,
                kr.conditions,
                kr.recommended_course_id,
                kr.priority,
                kr.is_active,
                c.course_code,
                c.course_name
            FROM knowledge_rules kr
            JOIN courses c ON kr.recommended_course_id = c.id
            WHERE kr.id = %s
        """
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (rule_id,))
            row = cursor.fetchone()

        if row:
            return ProductionRule.from_db_row(row)
        return None

    def get_rules_for_course(self, course_id: int, active_only: bool = True) -> List[ProductionRule]:
        """Retrieves all rules recommending a specific course."""
        rules = self.get_all_rules(active_only=active_only)
        return [r for r in rules if r.recommended_course_id == course_id]

    @classmethod
    def validate_rule_structure(cls, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the structure of a rule before saving or updating.
        Checks:
        - rule_name is a non-empty string.
        - recommended_course_id exists in courses table.
        - priority is an integer between 1 and 10.
        - conditions conforms to structured JSON (all/any) with allowed fields and operators.
        - strictly forbids arbitrary code.
        """
        errors: List[str] = []

        # 1. Rule Name validation
        rule_name = str(rule_data.get("rule_name") or "").strip()
        if not rule_name:
            errors.append("Rule name / identifier cannot be empty.")
        elif len(rule_name) > 100:
            errors.append("Rule name exceeds maximum length of 100 characters.")

        # 2. Priority validation
        try:
            priority = int(rule_data.get("priority", 5))
            if priority < 1 or priority > 10:
                errors.append(f"Priority ({priority}) must be between 1 and 10.")
        except (ValueError, TypeError):
            errors.append("Priority must be a valid integer between 1 and 10.")

        # 3. Course existence validation
        course_id_raw = rule_data.get("recommended_course_id")
        if course_id_raw is None:
            # Check action dict
            action = rule_data.get("action")
            if isinstance(action, dict):
                course_id_raw = action.get("course_id")

        try:
            course_id = int(course_id_raw)
            with get_db_cursor(dictionary=True) as (cursor, _):
                cursor.execute("SELECT id FROM courses WHERE id = %s", (course_id,))
                if not cursor.fetchone():
                    errors.append(f"Recommended course ID {course_id} does not exist in the courses catalog.")
        except (ValueError, TypeError):
            errors.append("Recommended course ID must be a valid integer.")
        except Exception as exc:
            errors.append(f"Database error verifying course ID: {exc}")

        # 4. Conditions validation
        raw_conds = rule_data.get("conditions")
        if isinstance(raw_conds, str):
            try:
                raw_conds = json.loads(raw_conds)
            except Exception as exc:
                errors.append(f"Conditions must be valid JSON: {exc}")
                raw_conds = {}

        if not isinstance(raw_conds, dict):
            errors.append("Conditions must be a valid JSON dictionary.")
        else:
            # Check all / any predicates
            for group_key in ("all", "any"):
                if group_key in raw_conds:
                    items = raw_conds[group_key]
                    if not isinstance(items, list):
                        errors.append(f"Conditions '{group_key}' must be a list of condition predicates.")
                        continue
                    for idx, pred in enumerate(items):
                        if not isinstance(pred, dict):
                            errors.append(f"Condition #{idx + 1} in '{group_key}' must be a dictionary.")
                            continue
                        field_val = str(pred.get("field", "")).strip().lower()
                        if field_val not in ALLOWED_FIELDS:
                            errors.append(
                                f"Field '{pred.get('field')}' in '{group_key}' is not allowed. "
                                f"Allowed: {', '.join(ALLOWED_FIELDS)}"
                            )
                        op_val = str(pred.get("operator", "")).strip().lower()
                        if op_val not in ALLOWED_OPERATORS:
                            errors.append(
                                f"Operator '{pred.get('operator')}' in '{group_key}' is not allowed. "
                                f"Allowed: {', '.join(ALLOWED_OPERATORS)}"
                            )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    def add_rule(self, rule_name: str, recommended_course_id: int, conditions: Any,
                 priority: int = 5, is_active: bool = True) -> int:
        """
        Inserts a new production rule into MySQL knowledge_rules table after validation.
        """
        if isinstance(conditions, ConditionGroup):
            cond_dict = conditions.to_dict()
        elif isinstance(conditions, str):
            try:
                cond_dict = json.loads(conditions)
            except Exception:
                cond_dict = {}
        elif isinstance(conditions, dict):
            cond_dict = conditions
        else:
            cond_dict = {}

        # Validate
        val_res = self.validate_rule_structure({
            "rule_name": rule_name,
            "recommended_course_id": recommended_course_id,
            "conditions": cond_dict,
            "priority": priority
        })
        if not val_res["is_valid"]:
            raise ValueError(f"Rule validation failed: {'; '.join(val_res['errors'])}")

        cond_json = json.dumps(cond_dict, ensure_ascii=False)
        query = """
            INSERT INTO knowledge_rules (rule_name, conditions, recommended_course_id, priority, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (rule_name, cond_json, recommended_course_id, priority, is_active))
            return cursor.lastrowid

    def update_rule(self, rule_id: int, rule_name: str, recommended_course_id: int,
                    conditions: Any, priority: int = 5, is_active: bool = True) -> bool:
        """
        Updates an existing production rule after validation.
        """
        if isinstance(conditions, ConditionGroup):
            cond_dict = conditions.to_dict()
        elif isinstance(conditions, str):
            try:
                cond_dict = json.loads(conditions)
            except Exception:
                cond_dict = {}
        elif isinstance(conditions, dict):
            cond_dict = conditions
        else:
            cond_dict = {}

        val_res = self.validate_rule_structure({
            "rule_name": rule_name,
            "recommended_course_id": recommended_course_id,
            "conditions": cond_dict,
            "priority": priority
        })
        if not val_res["is_valid"]:
            raise ValueError(f"Rule validation failed: {'; '.join(val_res['errors'])}")

        cond_json = json.dumps(cond_dict, ensure_ascii=False)
        query = """
            UPDATE knowledge_rules
            SET rule_name = %s, conditions = %s, recommended_course_id = %s,
                priority = %s, is_active = %s
            WHERE id = %s
        """
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (rule_name, cond_json, recommended_course_id, priority, is_active, rule_id))
            return cursor.rowcount > 0

    def toggle_rule(self, rule_id: int) -> bool:
        """Toggles active/inactive state of a rule."""
        query_sel = "SELECT is_active FROM knowledge_rules WHERE id = %s"
        query_up = "UPDATE knowledge_rules SET is_active = %s WHERE id = %s"
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query_sel, (rule_id,))
            row = cursor.fetchone()
            if not row:
                return False
            new_status = not bool(row["is_active"])
            cursor.execute(query_up, (new_status, rule_id))
            return True

    def delete_rule(self, rule_id: int) -> bool:
        """Deletes a rule from knowledge_rules table."""
        query = "DELETE FROM knowledge_rules WHERE id = %s"
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (rule_id,))
            return cursor.rowcount > 0

    @staticmethod
    def sort_rules_by_priority(rules: List[ProductionRule]) -> List[ProductionRule]:
        """Utility to sort rules by priority descending."""
        return sorted(rules, key=lambda r: (r.priority, r.id or 0), reverse=True)

    def seed_sample_rules(self) -> Dict[str, int]:
        """
        Creates or updates meaningful sample AI rules for the 10 required courses:
        - Machine Learning
        - Artificial Intelligence
        - Deep Learning
        - Big Data Analytics
        - Cloud Computing
        - Cyber Security
        - Data Mining
        - Natural Language Processing
        - Computer Vision
        - Internet of Things

        Uses actual course IDs dynamically retrieved from MySQL rather than assuming fixed IDs.
        Uses structured JSON conditions supporting all (AND) and any (OR) operators.
        """
        # Fetch current courses mapping from MySQL
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute("SELECT id, course_code, course_name, minimum_cgpa FROM courses")
            courses_by_name = {c["course_name"].strip().lower(): c for c in cursor.fetchall()}

        sample_definitions = [
            {
                "rule_name": "Rule_Machine_Learning_Core",
                "course_lookup": "machine learning",
                "priority": 8,
                "conditions": {
                    "all": [
                        {"field": "interests", "operator": "contains", "value": "Machine Learning"},
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.50}
                    ],
                    "any": [
                        {"field": "career_goal", "operator": "equals", "value": "Machine Learning Engineer"},
                        {"field": "career_goal", "operator": "equals", "value": "Data Scientist"},
                        {"field": "interests", "operator": "contains", "value": "Python Programming"}
                    ],
                    "rationale": "Intermediate student with predictive analytics interest strongly recommended for Machine Learning."
                }
            },
            {
                "rule_name": "Rule_General_AI_Foundations",
                "course_lookup": "artificial intelligence",
                "priority": 7,
                "conditions": {
                    "all": [
                        {"field": "interests", "operator": "contains", "value": "Artificial Intelligence"},
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.00}
                    ],
                    "any": [
                        {"field": "career_goal", "operator": "equals", "value": "AI Engineer"},
                        {"field": "career_goal", "operator": "equals", "value": "AI Research Scientist"}
                    ],
                    "rationale": "Rule recommending Artificial Intelligence for core cognitive computing and intelligent systems."
                }
            },
            {
                "rule_name": "Rule_Deep_Learning_Eligibility",
                "course_lookup": "deep learning",
                "priority": 10,
                "conditions": {
                    "all": [
                        {"field": "interests", "operator": "contains", "value": "Deep Learning & Neural Networks"},
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 3.00}
                    ],
                    "any": [
                        {"field": "career_goal", "operator": "equals", "value": "AI Research Scientist"},
                        {"field": "career_goal", "operator": "equals", "value": "Machine Learning Engineer"}
                    ],
                    "rationale": "High CGPA student in advanced semesters with deep learning interest qualifies for Deep Learning."
                }
            },
            {
                "rule_name": "Rule_Big_Data_Analytics",
                "course_lookup": "big data analytics",
                "priority": 7,
                "conditions": {
                    "all": [
                        {"field": "interests", "operator": "contains", "value": "Big Data & Distributed Computing"},
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.50}
                    ],
                    "any": [
                        {"field": "career_goal", "operator": "equals", "value": "Big Data Engineer"},
                        {"field": "career_goal", "operator": "equals", "value": "Data Engineer"}
                    ],
                    "rationale": "Student keen on distributed data pipelines and large-scale data storage suited for Big Data Analytics."
                }
            },
            {
                "rule_name": "Rule_Cloud_Computing_DevOps",
                "course_lookup": "cloud computing",
                "priority": 6,
                "conditions": {
                    "all": [
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.00}
                    ],
                    "any": [
                        {"field": "interests", "operator": "contains", "value": "Cloud Infrastructure & DevOps"},
                        {"field": "interests", "operator": "contains", "value": "Cloud Technology"},
                        {"field": "career_goal", "operator": "equals", "value": "Cloud Solutions Architect"},
                        {"field": "career_goal", "operator": "equals", "value": "Cloud Engineer"}
                    ],
                    "rationale": "Student interested in cloud infrastructure, virtualization, and distributed systems matches Cloud Computing."
                }
            },
            {
                "rule_name": "Rule_Cyber_Security_Defense",
                "course_lookup": "cyber security",
                "priority": 6,
                "conditions": {
                    "all": [
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.00}
                    ],
                    "any": [
                        {"field": "interests", "operator": "contains", "value": "Network Security & Cryptography"},
                        {"field": "interests", "operator": "contains", "value": "Cyber Security"},
                        {"field": "career_goal", "operator": "equals", "value": "Cybersecurity Analyst"},
                        {"field": "career_goal", "operator": "equals", "value": "Cyber Security Analyst"}
                    ],
                    "rationale": "Student dedicated to security, network protection, and defense systems directed to Cyber Security."
                }
            },
            {
                "rule_name": "Rule_Data_Mining_Foundation",
                "course_lookup": "data mining",
                "priority": 5,
                "conditions": {
                    "all": [
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.20}
                    ],
                    "any": [
                        {"field": "interests", "operator": "contains", "value": "Data Mining & Predictive Modeling"},
                        {"field": "interests", "operator": "contains", "value": "Data Science"},
                        {"field": "career_goal", "operator": "equals", "value": "Data Scientist"}
                    ],
                    "rationale": "Students pursuing statistical pattern recognition steered toward Data Mining."
                }
            },
            {
                "rule_name": "Rule_NLP_Specialization",
                "course_lookup": "natural language processing",
                "priority": 9,
                "conditions": {
                    "all": [
                        {"field": "interests", "operator": "contains", "value": "Natural Language Processing"},
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.75}
                    ],
                    "any": [
                        {"field": "career_goal", "operator": "equals", "value": "NLP Specialist"},
                        {"field": "career_goal", "operator": "equals", "value": "AI Research Scientist"}
                    ],
                    "rationale": "Student targeting language modeling, computational linguistics, and conversational AI recommended for Natural Language Processing."
                }
            },
            {
                "rule_name": "Rule_Computer_Vision_Specialization",
                "course_lookup": "computer vision",
                "priority": 9,
                "conditions": {
                    "all": [
                        {"field": "interests", "operator": "contains", "value": "Computer Vision"},
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.80}
                    ],
                    "any": [
                        {"field": "career_goal", "operator": "equals", "value": "Computer Vision Engineer"},
                        {"field": "career_goal", "operator": "equals", "value": "AI Research Scientist"}
                    ],
                    "rationale": "Student focusing on image processing, visual object recognition, and robotics recommended for Computer Vision."
                }
            },
            {
                "rule_name": "Rule_Internet_of_Things_Foundations",
                "course_lookup": "internet of things",
                "priority": 5,
                "conditions": {
                    "all": [
                        {"field": "cgpa", "operator": "greater_than_or_equal", "value": 2.00}
                    ],
                    "any": [
                        {"field": "interests", "operator": "contains", "value": "Networking"},
                        {"field": "career_goal", "operator": "equals", "value": "Software Developer"}
                    ],
                    "rationale": "Student interested in embedded hardware, edge devices, and sensor networks recommended for Internet of Things."
                }
            }
        ]

        seeded_counts = {"inserted": 0, "updated": 0}

        for item in sample_definitions:
            course = courses_by_name.get(item["course_lookup"])
            if not course:
                continue

            course_id = course["id"]
            cond_dict = item["conditions"]
            # Add action metadata into condition or rule
            cond_json = json.dumps(cond_dict, ensure_ascii=False)

            with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
                # Check if rule exists
                cursor.execute("SELECT id FROM knowledge_rules WHERE rule_name = %s", (item["rule_name"],))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("""
                        UPDATE knowledge_rules
                        SET conditions = %s, recommended_course_id = %s, priority = %s, is_active = TRUE
                        WHERE id = %s
                    """, (cond_json, course_id, item["priority"], existing["id"]))
                    seeded_counts["updated"] += 1
                else:
                    cursor.execute("""
                        INSERT INTO knowledge_rules (rule_name, conditions, recommended_course_id, priority, is_active)
                        VALUES (%s, %s, %s, %s, TRUE)
                    """, (item["rule_name"], cond_json, course_id, item["priority"]))
                    seeded_counts["inserted"] += 1

        return seeded_counts
