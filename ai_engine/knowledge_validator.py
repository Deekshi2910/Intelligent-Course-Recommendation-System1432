"""
Knowledge Validator Module
Audits, verifies, and validates course knowledge representations,
academic eligibility bounds, relational mappings, and ontological integrity.
Identifies anomalies, duplicates, missing properties, and invalid dependencies.
"""

from typing import Dict, List, Any, Optional
from database.db_connection import get_db_cursor


class KnowledgeValidator:
    """Provides methods to validate individual course facts and system-wide knowledge integrity."""

    VALID_DIFFICULTY_LEVELS = {"Beginner", "Intermediate", "Advanced"}

    @classmethod
    def validate_course_dict(cls, course: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates an individual course dictionary.
        Returns a dict with is_valid (bool), errors (list), and warnings (list).
        """
        errors = []
        warnings = []

        # 1. Course Code
        code = course.get("course_code")
        if not code or not str(code).strip():
            errors.append("Course code is missing or empty.")
        elif len(str(code).strip()) > 20:
            errors.append(f"Course code '{code}' exceeds maximum length of 20 characters.")

        # 2. Course Name
        name = course.get("course_name")
        if not name or not str(name).strip():
            errors.append("Course title is missing or empty.")
        elif len(str(name).strip()) > 150:
            errors.append(f"Course title '{name}' exceeds maximum length of 150 characters.")

        # 3. Minimum CGPA
        cgpa_val = course.get("minimum_cgpa")
        if cgpa_val is not None:
            try:
                cgpa_float = float(cgpa_val)
                if cgpa_float < 0.0 or cgpa_float > 10.0:
                    errors.append(f"Minimum CGPA ({cgpa_float}) out of valid range [0.00 - 10.00].")
            except (ValueError, TypeError):
                errors.append(f"Invalid non-numeric minimum CGPA value: {cgpa_val}.")
        else:
            warnings.append("Minimum CGPA is not explicitly defined (defaults to 0.00).")

        # 4. Difficulty Level
        diff = course.get("difficulty_level")
        if not diff or diff not in cls.VALID_DIFFICULTY_LEVELS:
            errors.append(f"Invalid difficulty level '{diff}'. Must be one of: {sorted(cls.VALID_DIFFICULTY_LEVELS)}.")

        # 5. Description
        desc = course.get("description")
        if not desc or not str(desc).strip():
            warnings.append("Course description is empty.")

        # 6. Interests Check
        interests = course.get("interests", [])
        if not interests:
            warnings.append("No technical domain interests mapped to this course.")

        # 7. Career Goals Check
        career_goals = course.get("career_goals", [])
        if not career_goals:
            warnings.append("No career pathway opportunities mapped to this course.")

        # 8. Inactive Status
        if not course.get("is_active", True):
            warnings.append("Course is marked as inactive and is excluded from active recommendations.")

        return {
            "course_code": code or "UNKNOWN",
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    @classmethod
    def audit_database(cls) -> Dict[str, Any]:
        """
        Executes a comprehensive structural and relational audit of the live MySQL Knowledge Base.
        Checks courses, domain interests, career goals, junction integrity, and prerequisites.
        """
        report = {
            "status": "HEALTHY",
            "total_courses_audited": 0,
            "valid_courses_count": 0,
            "invalid_courses_count": 0,
            "warnings_count": 0,
            "errors_count": 0,
            "course_diagnostics": [],
            "orphan_course_interests": 0,
            "orphan_course_career_goals": 0,
            "orphan_prerequisites": 0,
            "self_prerequisites": 0,
            "cyclic_prerequisites": [],
            "duplicate_interest_mappings": 0,
            "duplicate_career_mappings": 0,
            "recommendations": []
        }

        with get_db_cursor(dictionary=True) as (cursor, _):
            # 1. Audit All Courses
            cursor.execute("""
                SELECT
                    c.id, c.course_code, c.course_name, c.description,
                    c.minimum_cgpa, c.difficulty_level, c.prerequisites, c.is_active
                FROM courses c
            """)
            courses = cursor.fetchall()
            report["total_courses_audited"] = len(courses)

            for c in courses:
                cid = c["id"]

                # Fetch mapped interests
                cursor.execute("""
                    SELECT i.interest_name FROM course_interests ci
                    JOIN interests i ON ci.interest_id = i.id
                    WHERE ci.course_id = %s
                """, (cid,))
                c["interests"] = [row["interest_name"] for row in cursor.fetchall()]

                # Fetch mapped career goals
                cursor.execute("""
                    SELECT cg.goal_name FROM course_career_goals ccg
                    JOIN career_goals cg ON ccg.career_goal_id = cg.id
                    WHERE ccg.course_id = %s
                """, (cid,))
                c["career_goals"] = [row["goal_name"] for row in cursor.fetchall()]

                # Validate course
                diag = cls.validate_course_dict(c)
                report["course_diagnostics"].append(diag)
                if diag["is_valid"]:
                    report["valid_courses_count"] += 1
                else:
                    report["invalid_courses_count"] += 1
                    report["errors_count"] += len(diag["errors"])
                report["warnings_count"] += len(diag["warnings"])

            # 2. Check for Duplicate or Orphan Course Interests
            cursor.execute("""
                SELECT course_id, interest_id, COUNT(*) AS cnt
                FROM course_interests
                GROUP BY course_id, interest_id
                HAVING cnt > 1
            """)
            dupe_ci = cursor.fetchall()
            report["duplicate_interest_mappings"] = len(dupe_ci)

            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM course_interests ci
                LEFT JOIN courses c ON ci.course_id = c.id
                LEFT JOIN interests i ON ci.interest_id = i.id
                WHERE c.id IS NULL OR i.id IS NULL
            """)
            orphan_ci = cursor.fetchone()["cnt"]
            report["orphan_course_interests"] = orphan_ci

            # 3. Check for Duplicate or Orphan Course Career Goals
            cursor.execute("""
                SELECT course_id, career_goal_id, COUNT(*) AS cnt
                FROM course_career_goals
                GROUP BY course_id, career_goal_id
                HAVING cnt > 1
            """)
            dupe_ccg = cursor.fetchall()
            report["duplicate_career_mappings"] = len(dupe_ccg)

            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM course_career_goals ccg
                LEFT JOIN courses c ON ccg.course_id = c.id
                LEFT JOIN career_goals cg ON ccg.career_goal_id = cg.id
                WHERE c.id IS NULL OR cg.id IS NULL
            """)
            orphan_ccg = cursor.fetchone()["cnt"]
            report["orphan_course_career_goals"] = orphan_ccg

            # 4. Check for Self-Referential or Orphan Prerequisites
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM course_prerequisites
                WHERE course_id = prerequisite_course_id
            """)
            report["self_prerequisites"] = cursor.fetchone()["cnt"]

            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM course_prerequisites cp
                LEFT JOIN courses c1 ON cp.course_id = c1.id
                LEFT JOIN courses c2 ON cp.prerequisite_course_id = c2.id
                WHERE c1.id IS NULL OR c2.id IS NULL
            """)
            report["orphan_prerequisites"] = cursor.fetchone()["cnt"]

            # 5. Check for 2-node Cyclic Prerequisites (A requires B AND B requires A)
            cursor.execute("""
                SELECT cp1.course_id AS cA, cp1.prerequisite_course_id AS cB
                FROM course_prerequisites cp1
                JOIN course_prerequisites cp2
                  ON cp1.course_id = cp2.prerequisite_course_id
                 AND cp1.prerequisite_course_id = cp2.course_id
                WHERE cp1.course_id < cp1.prerequisite_course_id
            """)
            cycles = cursor.fetchall()
            report["cyclic_prerequisites"] = [f"Cycle detected between course #{row['cA']} and #{row['cB']}" for row in cycles]

        # Overall Status Assessment
        total_errs = (
            report["errors_count"]
            + report["orphan_course_interests"]
            + report["orphan_course_career_goals"]
            + report["orphan_prerequisites"]
            + report["self_prerequisites"]
            + len(report["cyclic_prerequisites"])
        )

        if total_errs > 0:
            report["status"] = "CRITICAL"
            report["recommendations"].append("Resolve invalid fields and broken relational keys to ensure valid inference.")
        elif report["warnings_count"] > 0:
            report["status"] = "WARNING"
            report["recommendations"].append("Assign missing domain interests or descriptions to unmapped courses.")
        else:
            report["status"] = "HEALTHY"
            report["recommendations"].append("Knowledge base ontologies are consistent and ready for inference reasoning.")

        return report

    @classmethod
    def validate_all(cls) -> Dict[str, Any]:
        """Alias for audit_database."""
        return cls.audit_database()
