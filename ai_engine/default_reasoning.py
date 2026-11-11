"""
Default Reasoning Module
Phase 8: Default Reasoning Engine

Implements non-monotonic Default Reasoning (Reiter's Default Logic: A : B / C).
Handles incomplete, partial, or undeclared student information using structured
fallback rules (DR01 - DR05) and assumption management.

Reasoning Priority Hierarchy:
1. Actual student interests.
2. Actual career goals.
3. Rule-based reasoning.
4. Default reasoning (DR01, DR02, DR05).
5. General recommendations (DR03).

Strict Guarantees:
- Never assumes missing CGPA (DR04).
- Never assumes unknown prerequisites are satisfied (DR05).
- Excludes inactive courses.
- Retracts assumptions when actual student information is observed.
- Zero eval() / exec() usage.
"""

from typing import Dict, Any, List, Optional, Tuple
from ai_engine.default_rules import DefaultRule, DefaultRuleManager, CANONICAL_DEFAULT_RULES
from ai_engine.assumption_manager import AssumptionManager, Assumption
from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact
from ai_engine.rule_evaluator import evaluate_rules
from ai_engine.reasoning_logger import ReasoningLogger


class DefaultReasoningEngine:
    """Non-monotonic Default Reasoning Engine for course recommendations."""

    def __init__(self, assumption_manager: Optional[AssumptionManager] = None):
        self.assumption_manager = assumption_manager or AssumptionManager()
        self.logger = ReasoningLogger()

    def evaluate(self, student_data: Dict[str, Any],
                 knowledge_base: Optional[KnowledgeBase] = None) -> Dict[str, Any]:
        """
        Executes default reasoning over incomplete student facts:
        1. Detects missing attributes (CGPA, interests, career goal, prerequisites).
        2. Applies canonical default rules (DR01 - DR05).
        3. Enforces academic constraints (never assumes CGPA or prerequisites).
        4. Reconciles with actual student data (actual data always overrides assumptions).
        5. Generates explainable recommendations and rejection logs.
        """
        if knowledge_base is None:
            try:
                knowledge_base = KnowledgeBase()
            except Exception:
                knowledge_base = None

        self.logger.clear()
        rules_map = {r.rule_code: r for r in DefaultRuleManager.get_all_rules(active_only=False)}

        # ---------------------------------------------------------------------
        # 1. Detect Missing Student Information
        # ---------------------------------------------------------------------
        # CGPA Check
        raw_cgpa = student_data.get("cgpa")
        has_cgpa = True
        student_cgpa: Optional[float] = None

        if raw_cgpa is None or raw_cgpa == "":
            has_cgpa = False
        else:
            try:
                student_cgpa = float(raw_cgpa)
                if student_cgpa <= 0.0 and "cgpa" not in student_data:
                    has_cgpa = False
            except (ValueError, TypeError):
                has_cgpa = False

        # Technical Interests Check
        raw_interests = student_data.get("interests")
        interests_list: List[str] = []
        if isinstance(raw_interests, (list, tuple, set)):
            interests_list = [str(i).strip() for i in raw_interests if str(i).strip()]
        elif isinstance(raw_interests, str) and raw_interests.strip():
            interests_list = [raw_interests.strip()]
        has_interests = len(interests_list) > 0

        # Career Goal Check
        raw_goal = student_data.get("career_goal")
        career_goal_str = ""
        if raw_goal and isinstance(raw_goal, str) and raw_goal.strip():
            career_goal_str = raw_goal.strip()
        has_career_goal = len(career_goal_str) > 0

        # Prerequisites Verification Check
        completed_courses = student_data.get("completed_courses")
        has_prereq_info = completed_courses is not None and isinstance(completed_courses, (list, tuple))

        # Semester Standing
        semester = int(student_data.get("semester") or 1)

        # ---------------------------------------------------------------------
        # 2. Reconcile Existing Assumptions with Incoming Actual Data
        # ---------------------------------------------------------------------
        withdrawal_logs = self.assumption_manager.reconcile_with_actual_data(student_data)

        applied_default_rules: List[str] = []
        clarification_messages: List[str] = []
        recommended_courses: List[Dict[str, Any]] = []
        rejected_courses: List[Dict[str, Any]] = []
        academic_info_required = False
        unverified_prerequisites_found = False

        # ---------------------------------------------------------------------
        # 3. Apply DR04 (Missing CGPA)
        # ---------------------------------------------------------------------
        dr04 = rules_map.get("DR04")
        if not has_cgpa and (dr04 is None or dr04.is_active):
            applied_default_rules.append("DR04")
            academic_info_required = True
            clarification_messages.append(
                "Your CGPA is missing. Please provide your CGPA before academic eligibility can be confirmed. "
                "The system will not assume or estimate your CGPA."
            )
            self.logger.log_evaluation(
                rule_name="DR04_Missing_CGPA",
                course_id=0,
                course_code="ACADEMIC",
                course_name="CGPA Verification",
                match_score=0.0,
                is_matched=False,
                failed_conditions=["CGPA is missing"],
                rationale="CGPA is required to confirm eligibility; never assumed."
            )

        # ---------------------------------------------------------------------
        # 4. Determine Reasoning Strategy (Normal Rule-Based vs DR01, DR02, DR03)
        # ---------------------------------------------------------------------
        dr01 = rules_map.get("DR01")
        dr02 = rules_map.get("DR02")
        dr03 = rules_map.get("DR03")
        dr05 = rules_map.get("DR05")

        # CASE A: Full Information (Rule-Based Reasoning)
        if has_interests and has_career_goal:
            if has_cgpa:
                # Complete student preferences available; run pure rule-based reasoning
                rule_eval = evaluate_rules(student_data, knowledge_base=knowledge_base)
                recommended_courses = list(rule_eval.get("recommended_courses", []))
                rejected_courses = list(rule_eval.get("rejected_evaluations", []))
            else:
                # CGPA is missing (DR04): Do not assume CGPA; candidate courses require CGPA verification
                rule_eval = evaluate_rules(dict(student_data, cgpa=10.0), knowledge_base=knowledge_base)
                candidates = list(rule_eval.get("recommended_courses", []))
                for c in candidates:
                    rejected_courses.append({
                        "course_id": c["course_id"],
                        "course_code": c["course_code"],
                        "course_name": c["course_name"],
                        "reason": "Academic eligibility unverified: CGPA is missing. Please provide your CGPA before eligibility can be confirmed.",
                        "priority": c.get("priority", 5)
                    })

        # CASE B: DR01 - Missing Career Goal (Interest-Based Fallback)
        elif has_interests and not has_career_goal and (dr01 is None or dr01.is_active):
            applied_default_rules.append("DR01")
            self.assumption_manager.record_assumption(
                field_name="career_goal",
                assumed_value="UNSPECIFIED",
                reason="Student did not provide a career goal; falling back to interest ontologies.",
                source_rule="DR01"
            )
            clarification_messages.append(
                "Your career goal was not provided. Therefore, the system used your selected interests to identify suitable courses."
            )

            # Retrieve active courses matching student's selected interests from Knowledge Base
            if knowledge_base:
                matched_courses = []
                for interest_name in interests_list:
                    matched_courses.extend(knowledge_base.get_courses_by_interest(interest_name))

                # Deduplicate by course_id
                seen_courses = set()
                for course_fact in matched_courses:
                    if not course_fact.is_active:
                        continue
                    if course_fact.course_id in seen_courses:
                        continue
                    seen_courses.add(course_fact.course_id)

                    # Check CGPA eligibility
                    is_eligible = True
                    cgpa_reason = ""
                    if has_cgpa and student_cgpa is not None:
                        if student_cgpa < course_fact.minimum_cgpa:
                            is_eligible = False
                            cgpa_reason = f"Student CGPA ({student_cgpa:.2f}) below required ({course_fact.minimum_cgpa:.2f})"
                    else:
                        is_eligible = False
                        cgpa_reason = "Academic eligibility unverified: CGPA is missing"

                    if is_eligible:
                        # Interest match score
                        overlap = [i for i in course_fact.interests if i.lower() in [x.lower() for x in interests_list]]
                        match_score = min(95.0, 50.0 + len(overlap) * 20.0)

                        explanation = (
                            f"{course_fact.course_name} ({course_fact.course_code}) was recommended because "
                            f"the student selected interest in {', '.join(overlap) if overlap else 'related domains'}."
                        )
                        recommended_courses.append({
                            "course_id": course_fact.course_id,
                            "course_code": course_fact.course_code,
                            "course_name": course_fact.course_name,
                            "priority": 7,
                            "match_score": round(match_score, 1),
                            "reasons": [
                                "Recommended via DR01 interest-based fallback.",
                                f"Matches interest(s): {', '.join(overlap)}."
                            ],
                            "explanation": explanation,
                            "fired_rules": ["DR01_Interest_Based_Fallback"],
                            "is_default_reasoning": True,
                            "fallback_strategy": "interest_based"
                        })
                    else:
                        rejected_courses.append({
                            "course_id": course_fact.course_id,
                            "course_code": course_fact.course_code,
                            "course_name": course_fact.course_name,
                            "reason": cgpa_reason,
                            "priority": 7
                        })

        # CASE C: DR02 - Missing Interests (Career-Based Fallback)
        elif not has_interests and has_career_goal and (dr02 is None or dr02.is_active):
            applied_default_rules.append("DR02")
            self.assumption_manager.record_assumption(
                field_name="interests",
                assumed_value=["UNSPECIFIED"],
                reason="Student did not provide technical interests; falling back to target career pathway.",
                source_rule="DR02"
            )
            clarification_messages.append(
                "Your interests were not provided. Therefore, the system used your selected career goal to identify suitable courses."
            )

            # Retrieve active courses matching career goal from Knowledge Base
            if knowledge_base:
                matched_courses = knowledge_base.get_courses_by_career_goal(career_goal_str)
                seen_courses = set()

                for course_fact in matched_courses:
                    if not course_fact.is_active:
                        continue
                    if course_fact.course_id in seen_courses:
                        continue
                    seen_courses.add(course_fact.course_id)

                    # Check CGPA eligibility
                    is_eligible = True
                    cgpa_reason = ""
                    if has_cgpa and student_cgpa is not None:
                        if student_cgpa < course_fact.minimum_cgpa:
                            is_eligible = False
                            cgpa_reason = f"Student CGPA ({student_cgpa:.2f}) below required ({course_fact.minimum_cgpa:.2f})"
                    else:
                        is_eligible = False
                        cgpa_reason = "Academic eligibility unverified: CGPA is missing"

                    if is_eligible:
                        match_score = 80.0
                        explanation = (
                            f"{course_fact.course_name} ({course_fact.course_code}) was recommended because "
                            f"it prepares students for the target career pathway '{career_goal_str}'."
                        )
                        recommended_courses.append({
                            "course_id": course_fact.course_id,
                            "course_code": course_fact.course_code,
                            "course_name": course_fact.course_name,
                            "priority": 6,
                            "match_score": match_score,
                            "reasons": [
                                "Recommended via DR02 career-based fallback.",
                                f"Directly aligned with target career: '{career_goal_str}'."
                            ],
                            "explanation": explanation,
                            "fired_rules": ["DR02_Career_Based_Fallback"],
                            "is_default_reasoning": True,
                            "fallback_strategy": "career_based"
                        })
                    else:
                        rejected_courses.append({
                            "course_id": course_fact.course_id,
                            "course_code": course_fact.course_code,
                            "course_name": course_fact.course_name,
                            "reason": cgpa_reason,
                            "priority": 6
                        })

        # CASE D: DR03 - Missing Both Interests & Career Goal (General Foundational Recommendations)
        else:
            if dr03 is None or dr03.is_active:
                applied_default_rules.append("DR03")
                self.assumption_manager.record_assumption(
                    field_name="general_profile",
                    assumed_value="FOUNDATIONAL",
                    reason="Student provided neither interests nor career goals; falling back to foundational electives.",
                    source_rule="DR03"
                )
                clarification_messages.append(
                    "Neither interests nor career goals were provided. These are general foundational recommendations and may not match your personal preferences."
                )

                if knowledge_base:
                    # Recommend introductory breadth courses: CS-402, CS-410, CS-404
                    foundational_codes = ["CS-402", "CS-410", "CS-404", "CS-407"]
                    for code in foundational_codes:
                        course_fact = knowledge_base.get_course_by_code(code)
                        if not course_fact or not course_fact.is_active:
                            continue

                        # Check CGPA eligibility
                        is_eligible = True
                        cgpa_reason = ""
                        if has_cgpa and student_cgpa is not None:
                            if student_cgpa < course_fact.minimum_cgpa:
                                is_eligible = False
                                cgpa_reason = f"Student CGPA ({student_cgpa:.2f}) below required ({course_fact.minimum_cgpa:.2f})"
                        else:
                            is_eligible = False
                            cgpa_reason = "Academic eligibility unverified: CGPA is missing"

                        if is_eligible:
                            explanation = (
                                f"{course_fact.course_name} ({course_fact.course_code}) was suggested as a general "
                                f"foundational breadth course because neither interests nor career goals were specified."
                            )
                            recommended_courses.append({
                                "course_id": course_fact.course_id,
                                "course_code": course_fact.course_code,
                                "course_name": course_fact.course_name,
                                "priority": 3,
                                "match_score": 50.0,
                                "reasons": [
                                    "Recommended via DR03 general foundational fallback.",
                                    "Serves as core breadth elective in computing curriculum."
                                ],
                                "explanation": explanation,
                                "fired_rules": ["DR03_General_Foundational_Fallback"],
                                "is_default_reasoning": True,
                                "is_general_recommendation": True,
                                "fallback_strategy": "general_foundational"
                            })
                        else:
                            rejected_courses.append({
                                "course_id": course_fact.course_id,
                                "course_code": course_fact.course_code,
                                "course_name": course_fact.course_name,
                                "reason": cgpa_reason,
                                "priority": 3
                            })

        # ---------------------------------------------------------------------
        # 5. Apply DR05 (Unknown Prerequisites Verification)
        # ---------------------------------------------------------------------
        if dr05 is None or dr05.is_active:
            for rec in recommended_courses:
                course_id = rec.get("course_id")
                course_fact = knowledge_base.get_course_by_id(course_id) if knowledge_base else None

                if course_fact and course_fact.prerequisites_text:
                    # If student completed courses is unprovided or None
                    if not has_prereq_info:
                        if "DR05" not in applied_default_rules:
                            applied_default_rules.append("DR05")
                            unverified_prerequisites_found = True
                            clarification_messages.append(
                                "Prerequisite information is unavailable. Eligibility is marked as unverified; prerequisites cannot be assumed satisfied."
                            )

                        rec["prerequisites_verified"] = False
                        rec["prerequisites_note"] = f"Unverified: Requires prerequisite ({course_fact.prerequisites_text})"
                        rec["explanation"] += f" (Note: Prerequisite '{course_fact.prerequisites_text}' is unverified)."
                    else:
                        # Verify completed courses against prerequisites
                        completed_norm = [str(c).lower().strip() for c in (completed_courses or [])]
                        prereq_parts = [p.strip().lower() for p in course_fact.prerequisites_text.replace(";", ",").split(",") if p.strip()]
                        
                        all_satisfied = all(any(req in c or c in req for c in completed_norm) for req in prereq_parts)
                        rec["prerequisites_verified"] = all_satisfied
                        if not all_satisfied:
                            rec["prerequisites_note"] = f"Missing prerequisite(s): {course_fact.prerequisites_text}"
                else:
                    rec["prerequisites_verified"] = True

        # Sort recommendations by priority descending, then match score descending
        sorted_recommendations = sorted(
            recommended_courses,
            key=lambda x: (x.get("priority", 1), x.get("match_score", 0.0)),
            reverse=True
        )

        is_default_reasoning_used = any(r in applied_default_rules for r in ["DR01", "DR02", "DR03", "DR04", "DR05"])

        return {
            "recommended_courses": sorted_recommendations,
            "rejected_courses": rejected_courses,
            "applied_default_rules": applied_default_rules,
            "clarification_messages": list(dict.fromkeys(clarification_messages)),
            "assumptions_made": [a.to_dict() for a in self.assumption_manager.get_active_assumptions()],
            "withdrawn_assumptions": withdrawal_logs,
            "is_default_reasoning_used": is_default_reasoning_used,
            "academic_info_required": academic_info_required,
            "unverified_prerequisites_found": unverified_prerequisites_found,
            "total_recommended": len(sorted_recommendations),
            "total_rejected": len(rejected_courses)
        }


def infer_with_defaults(student_data: Dict[str, Any],
                        knowledge_base: Optional[KnowledgeBase] = None) -> Dict[str, Any]:
    """Top-level helper executing Default Reasoning with DR01-DR05."""
    engine = DefaultReasoningEngine()
    return engine.evaluate(student_data, knowledge_base=knowledge_base)
