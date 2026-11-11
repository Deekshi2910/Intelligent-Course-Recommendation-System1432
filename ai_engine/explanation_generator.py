"""
Explanation Generator Module
Phase 9: AI Inference Engine

Implements Explainable AI (XAI) rationale generation:
For every recommended course, constructs a grounded natural language explanation detailing:
- Which student interests matched.
- Whether the career goal matched.
- Whether the CGPA requirement was satisfied.
- Whether prerequisites were verified.
- Which AI production rules fired.
- Whether default reasoning was used.
- How the final suitability score was calculated.

Strict Safety: Zero eval() / exec() usage. Real evaluation facts only.
"""

from typing import Dict, Any, List, Optional


class ExplanationGenerator:
    """Generates transparent, grounded explanations for course recommendations and rejections."""

    @classmethod
    def generate_recommendation_explanation(
        cls,
        course_data: Dict[str, Any],
        student_profile: Dict[str, Any]
    ) -> str:
        """
        Synthesizes a grounded natural language explanation justifying why a course was recommended.
        
        Example format:
        "Machine Learning received a suitability score of 90 because it matches your interests in 
         Python and Mathematics, aligns with your Data Scientist career goal, and satisfies the 
         academic eligibility requirement."
        """
        course_name = course_data.get("course_name", "This course")
        course_code = course_data.get("course_code", "")
        min_cgpa = float(course_data.get("minimum_cgpa", 0.0) or 0.0)
        score = float(course_data.get("suitability_score") or course_data.get("match_score") or 0.0)
        
        student_cgpa = float(student_profile.get("cgpa", 0.0) or 0.0)
        student_goal = str(student_profile.get("career_goal", "")).strip()

        matched_interests = course_data.get("matched_interests", [])
        matched_career_goals = course_data.get("matched_career_goals", [])
        career_matched = course_data.get("career_goal_matched") or bool(matched_career_goals)
        fired_rules = course_data.get("fired_rules", [])
        is_default = course_data.get("is_default_reasoning", False) or course_data.get("is_general_recommendation", False)
        
        prereqs_verified = course_data.get("prerequisites_verified", True)
        prereq_note = course_data.get("prerequisites_note", "")

        # Build causal clause components
        causal_reasons: List[str] = []

        # 1. Interests Match
        if matched_interests:
            unique_ints = list(dict.fromkeys(matched_interests))
            if len(unique_ints) == 1:
                causal_reasons.append(f"matches your interest in {unique_ints[0]}")
            elif len(unique_ints) == 2:
                causal_reasons.append(f"matches your interests in {unique_ints[0]} and {unique_ints[1]}")
            else:
                causal_reasons.append(f"matches your interests in {', '.join(unique_ints[:-1])}, and {unique_ints[-1]}")
        elif not student_profile.get("interests"):
            if is_default:
                causal_reasons.append("provides foundational knowledge (default breadth)")

        # 2. Career Goal Alignment
        if career_matched or (student_goal and any(student_goal.lower() in str(g).lower() for g in course_data.get("career_goals", []))):
            target_goal = student_goal or (matched_career_goals[0] if matched_career_goals else "your target field")
            causal_reasons.append(f"aligns with your {target_goal} career goal")
        elif not student_goal and is_default:
            pass  # handled in default logic note

        # 3. CGPA Academic Requirement
        if student_cgpa > 0 and min_cgpa > 0:
            if student_cgpa >= min_cgpa:
                causal_reasons.append("satisfies the academic eligibility requirement")
        elif min_cgpa == 0:
            causal_reasons.append("has open academic eligibility")

        # 4. Prerequisites Verification
        if not prereqs_verified and prereq_note:
            causal_reasons.append(f"carries prerequisite advisory ({prereq_note})")
        elif prereqs_verified and course_data.get("prerequisites_text") and course_data.get("prerequisites_text").lower() not in ("none", "nil"):
            causal_reasons.append("prerequisites are verified")

        # Combine into cohesive explanation sentence
        score_int = int(round(score))
        if causal_reasons:
            reasons_joined = ", ".join(causal_reasons[:-1]) + (f", and {causal_reasons[-1]}" if len(causal_reasons) > 1 else causal_reasons[0])
            main_sentence = f"{course_name} received a suitability score of {score_int} because it {reasons_joined}."
        else:
            main_sentence = f"{course_name} received a suitability score of {score_int} based on curriculum fit."

        # Add rule or default reasoning attribution
        attributions: List[str] = []
        if fired_rules:
            clean_rules = [r for r in fired_rules if not r.startswith("DR0")]
            if clean_rules:
                attributions.append(f"AI Rule(s) Fired: {', '.join(clean_rules)}.")

        if is_default or any(str(r).startswith("DR0") for r in fired_rules):
            strategy = course_data.get("fallback_strategy", "default reasoning")
            attributions.append(f"Default Reasoning: Applied fallback strategy ({strategy}).")

        # Add score calculation formula breakdown if present
        breakdown = course_data.get("score_breakdown")
        if breakdown:
            calc_text = (
                f"Score Calculation: Interest={breakdown.get('interest_match', 0)}% (×40%) + "
                f"Career={breakdown.get('career_match', 0)}% (×35%) + "
                f"CGPA={breakdown.get('cgpa_readiness', 0)}% (×15%) + "
                f"Prerequisite={breakdown.get('prerequisite_match', 0)}% (×10%)."
            )
            attributions.append(calc_text)

        if attributions:
            return f"{main_sentence} {' '.join(attributions)}"
        return main_sentence

    @classmethod
    def generate_rejection_explanation(
        cls,
        course_data: Dict[str, Any],
        student_profile: Dict[str, Any],
        reasons: Optional[List[str]] = None
    ) -> str:
        """Constructs a factual, constructive explanation for course ineligibility or rejection."""
        course_code = course_data.get("course_code", "Course")
        course_name = course_data.get("course_name", "")
        min_cgpa = float(course_data.get("minimum_cgpa", 0.0) or 0.0)
        student_cgpa = float(student_profile.get("cgpa", 0.0) or 0.0)

        parts: List[str] = []

        if reasons:
            parts.extend(reasons)
        else:
            if not course_data.get("is_active", True):
                parts.append("Course is currently inactive in the curriculum catalog.")
            
            if min_cgpa > 0 and (student_cgpa == 0 or student_cgpa < min_cgpa):
                deficit = min_cgpa - student_cgpa
                parts.append(f"CGPA requirement not met (Required: {min_cgpa:.2f}, Current: {student_cgpa:.2f}, Deficit: {deficit:.2f}).")

            prereqs = course_data.get("prerequisites_text") or course_data.get("prerequisite_courses")
            if prereqs and str(prereqs).lower() not in ("none", "nil", "[]"):
                completed = student_profile.get("completed_courses")
                if completed is not None:
                    parts.append(f"Required prerequisites not completed: {prereqs}.")

            if not parts:
                parts.append("Did not meet composite eligibility threshold for student profile.")

        return f"{course_code} ({course_name}) was excluded: {' '.join(parts)}"

    @classmethod
    def generate_default_reasoning_explanation(
        cls,
        strategy: str,
        assumptions: List[Dict[str, Any]],
        rule_code: Optional[str] = None
    ) -> str:
        """Explains default fallback strategy and working hypotheses."""
        explanations = {
            "interest_fallback": (
                "Career goal was not specified. Default Rule DR01 was applied: "
                "Recommendations were derived purely from your selected technical interests."
            ),
            "career_fallback": (
                "Technical interests were not specified. Default Rule DR02 was applied: "
                "Recommendations were mapped directly from your target career goal."
            ),
            "general_foundational": (
                "Neither technical interests nor career goals were provided. Default Rule DR03 was applied: "
                "Generating foundational, high-demand core elective recommendations."
            ),
            "academic_info_required": (
                "Academic CGPA is missing. Default Rule DR04 was applied: "
                "No CGPA was assumed. Please update your profile with your current CGPA for personalized recommendations."
            ),
            "prerequisites_unverified": (
                "Course completion history was not provided. Default Rule DR05 was applied: "
                "Courses with prerequisites are flagged as unverified to preserve academic integrity."
            )
        }

        base = explanations.get(
            strategy,
            f"Default reasoning strategy '{strategy}' was applied to handle incomplete profile information."
        )

        if assumptions:
            details = [
                f"assumed {a.get('field_name')}='{a.get('assumed_value')}' ({a.get('reason')})"
                for a in assumptions
            ]
            return f"{base} Working hypotheses: {'; '.join(details)}."
        return base

    @classmethod
    def generate_comparative_summary(
        cls,
        ranked_courses: List[Dict[str, Any]],
        student_profile: Dict[str, Any]
    ) -> str:
        """Executive summary of the recommendation batch."""
        total = len(ranked_courses)
        if total == 0:
            return "No courses matched your current criteria. Consider adjusting your interests or updating your profile."

        top = ranked_courses[0]
        top_name = top.get("course_name", "Top Match")
        top_code = top.get("course_code", "")
        top_score = float(top.get("suitability_score") or top.get("match_score") or 0.0)

        high_matches = sum(1 for c in ranked_courses if c.get("recommendation_tier") == "Highly Recommended")
        strong_matches = sum(1 for c in ranked_courses if c.get("recommendation_tier") == "Strong Match")

        summary_parts = [
            f"AI Inference Engine evaluated active curriculum courses and identified {total} recommended option{'s' if total != 1 else ''}.",
            f"Top recommendation is {top_code}: {top_name} with an overall suitability score of {top_score:.1f}%."
        ]

        if high_matches > 0:
            summary_parts.append(f"{high_matches} course{'s' if high_matches != 1 else ''} rated as Highly Recommended.")
        if strong_matches > 0:
            summary_parts.append(f"{strong_matches} course{'s' if strong_matches != 1 else ''} rated as Strong Match.")

        return " ".join(summary_parts)
