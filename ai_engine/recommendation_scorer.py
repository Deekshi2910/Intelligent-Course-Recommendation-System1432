"""
Recommendation Scorer Module
Phase 9: AI Inference Engine

Implements a transparent, multi-factor weighted scoring model:
1. Interest Match (40%): Overlap between student technical interests and course domains.
   - Strictly prevents double-counting duplicate interests via set deduplication.
2. Career Goal Match (35%): Direct alignment with target career pathways.
   - Unknown/missing goals evaluate to 0.0 (never treated as successful match).
3. CGPA Academic Margin (15%): Academic readiness exceeding the course threshold.
   - Normalized scaling based on margin above course minimum CGPA.
4. Prerequisite Match (10%): Completion of formal prerequisite dependencies.
   - 100% if no prerequisites required, or if all completed.
   - 0% if prerequisites are unverified or missing (never assumed satisfied).

Total Score = (Interest × 0.40) + (Career × 0.35) + (CGPA × 0.15) + (Prerequisite × 0.10)
Normalized and clamped strictly within [0.0, 100.0].

Configurable weights: May be customized via class attributes or per-call parameters.
"""

from typing import Dict, Any, List, Optional, Set
from ai_engine.knowledge_base import CourseKnowledgeFact


class RecommendationScorer:
    """Computes transparent, weighted multi-factor recommendation suitability scores."""

    # Default configurable component weights (sum = 1.00 / 100%)
    DEFAULT_WEIGHTS = {
        "interest": 0.40,
        "career": 0.35,
        "cgpa": 0.15,
        "prerequisite": 0.10
    }

    WEIGHT_INTEREST: float = 0.40
    WEIGHT_CAREER: float = 0.35
    WEIGHT_CGPA: float = 0.15
    WEIGHT_PREREQUISITE: float = 0.10

    @classmethod
    def get_configured_weights(cls, custom_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Validates and normalizes scoring weights."""
        if not custom_weights:
            return {
                "interest": cls.WEIGHT_INTEREST,
                "career": cls.WEIGHT_CAREER,
                "cgpa": cls.WEIGHT_CGPA,
                "prerequisite": cls.WEIGHT_PREREQUISITE
            }
        
        w_int = float(custom_weights.get("interest", cls.WEIGHT_INTEREST))
        w_car = float(custom_weights.get("career", cls.WEIGHT_CAREER))
        w_cgp = float(custom_weights.get("cgpa", cls.WEIGHT_CGPA))
        w_pre = float(custom_weights.get("prerequisite", cls.WEIGHT_PREREQUISITE))
        
        total = w_int + w_car + w_cgp + w_pre
        if total <= 0:
            return dict(cls.DEFAULT_WEIGHTS)
        
        # Normalize weights so they sum to 1.0
        return {
            "interest": w_int / total,
            "career": w_car / total,
            "cgpa": w_cgp / total,
            "prerequisite": w_pre / total
        }

    @classmethod
    def score_course(
        cls,
        student_profile: Dict[str, Any],
        course_fact: CourseKnowledgeFact,
        rule_priority: int = 5,
        matched_interests: Optional[List[str]] = None,
        matched_career_goals: Optional[List[str]] = None,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculates normalized suitability score [0.0 - 100.0] and component breakdown.
        """
        weights = cls.get_configured_weights(custom_weights)

        student_cgpa = float(student_profile.get("cgpa") or 0.0)
        student_goal = str(student_profile.get("career_goal") or "").strip().lower()
        raw_interests = student_profile.get("interests", [])
        completed_courses = student_profile.get("completed_courses")

        # ---------------------------------------------------------------------
        # 1. Interest Match Component (40% Weight)
        # Deduplicate student interests; avoid double-counting.
        # ---------------------------------------------------------------------
        # Normalize student interests to a unique set
        student_interests_set: Set[str] = {
            str(i).strip().lower() for i in raw_interests if str(i).strip()
        }
        course_interests_norm: List[str] = [i.strip().lower() for i in course_fact.interests]
        course_interests_set: Set[str] = set(course_interests_norm)

        matched_interest_names: List[str] = []
        if matched_interests:
            matched_interest_names = list(dict.fromkeys(matched_interests))
        else:
            for s_int in student_interests_set:
                for c_int in course_interests_norm:
                    if (s_int == c_int or s_int in c_int or c_int in s_int or
                            s_int.replace(" ", "") == c_int.replace(" ", "")):
                        if c_int not in matched_interest_names:
                            matched_interest_names.append(c_int)

        if course_interests_set and len(course_interests_set) > 0:
            overlap_count = len(matched_interest_names)
            # Proportion of course domain interests satisfied by student
            ratio = overlap_count / len(course_interests_set)
            # Base scaling with bonus for multiple distinct matches
            interest_sub = min(100.0, (ratio * 75.0) + (min(overlap_count, 3) * 8.33))
        elif matched_interest_names:
            interest_sub = min(100.0, len(matched_interest_names) * 35.0)
        else:
            # Missing or non-overlapping interests evaluate to 0.0
            interest_sub = 0.0

        # ---------------------------------------------------------------------
        # 2. Career Goal Match Component (35% Weight)
        # ---------------------------------------------------------------------
        career_sub = 0.0
        course_goals_norm = [g.strip().lower() for g in course_fact.career_goals]
        goal_matched = False

        if matched_career_goals and len(matched_career_goals) > 0:
            career_sub = 100.0
            goal_matched = True
        elif student_goal:
            student_goal_clean = student_goal.replace(" ", "").replace("-", "")
            for cg in course_goals_norm:
                cg_clean = cg.replace(" ", "").replace("-", "")
                if student_goal == cg or student_goal in cg or cg in student_goal or student_goal_clean == cg_clean:
                    career_sub = 100.0
                    goal_matched = True
                    break
        else:
            # Unknown / missing career goal evaluates to 0.0 (not a match)
            career_sub = 0.0

        # ---------------------------------------------------------------------
        # 3. CGPA Academic Readiness Component (15% Weight)
        # ---------------------------------------------------------------------
        min_cgpa = float(course_fact.minimum_cgpa or 0.0)
        if student_cgpa > 0 and student_cgpa >= min_cgpa:
            # Eligible: Baseline 70.0 + readiness margin above prerequisite
            margin = student_cgpa - min_cgpa
            cgpa_sub = min(100.0, 70.0 + (margin * 15.0))
        else:
            # Below prerequisite or missing
            cgpa_sub = 0.0

        # ---------------------------------------------------------------------
        # 4. Prerequisite Match Component (10% Weight)
        # ---------------------------------------------------------------------
        prereqs = course_fact.prerequisite_courses or []
        prereq_text = str(course_fact.prerequisites_text or "").strip()

        if not prereqs and (not prereq_text or prereq_text.lower() in ("none", "nil")):
            # No prerequisite required: full score
            prereq_sub = 100.0
            prereq_status = "satisfied_none_required"
        elif completed_courses is not None:
            # Check completed courses
            completed_set = {str(c).strip().lower() for c in completed_courses if str(c).strip()}
            required_codes = [
                p.get("course_code", "").strip().lower()
                for p in prereqs if isinstance(p, dict) and p.get("course_code")
            ]
            if not required_codes and prereq_text:
                required_codes = [
                    x.strip().lower() for x in prereq_text.replace(";", ",").split(",") if x.strip()
                ]

            if required_codes:
                satisfied_count = sum(
                    1 for req in required_codes
                    if any(req in comp or comp in req for comp in completed_set)
                )
                prereq_sub = (satisfied_count / len(required_codes)) * 100.0
                prereq_status = "verified_complete" if satisfied_count == len(required_codes) else "partial"
            else:
                prereq_sub = 100.0
                prereq_status = "satisfied"
        else:
            # Unknown / unverified prerequisite history: 0.0 (conservative safety)
            prereq_sub = 0.0
            prereq_status = "unverified"

        # ---------------------------------------------------------------------
        # Final Weighted Aggregation
        # ---------------------------------------------------------------------
        final_score = (
            (interest_sub * weights["interest"]) +
            (career_sub * weights["career"]) +
            (cgpa_sub * weights["cgpa"]) +
            (prereq_sub * weights["prerequisite"])
        )

        # Clamped strictly [0.0, 100.0]
        clamped_score = max(0.0, min(100.0, final_score))

        return {
            "final_score": round(clamped_score, 1),
            "total_score": round(clamped_score, 1),
            "suitability_score": round(clamped_score, 1),
            "weights_used": weights,
            "breakdown": {
                "interest_match": round(interest_sub, 1),
                "career_match": round(career_sub, 1),
                "cgpa_readiness": round(cgpa_sub, 1),
                "prerequisite_match": round(prereq_sub, 1),
                # Legacy keys for backward compatibility
                "academic_fit": round(cgpa_sub, 1),
                "interest_overlap": round(interest_sub, 1),
                "career_alignment": round(career_sub, 1),
                "priority_bonus": round(rule_priority * 10.0, 1),
                "difficulty_match": round(cgpa_sub, 1)
            },
            "matched_interests": matched_interest_names,
            "career_goal_matched": goal_matched,
            "prerequisite_status": prereq_status
        }
