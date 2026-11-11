"""
Inference Engine Module
Phase 9: AI Inference Engine

The central AI orchestrator that unites all knowledge and reasoning modules:
1. Working Memory & Profile Normalization: Standardizes student facts.
2. Knowledge Base Integration: Retrieves course facts, prerequisites, and taxonomy.
3. Hard Eligibility Enforcement:
   - Verifies active course status.
   - Strictly enforces minimum CGPA (never recommends courses above student CGPA).
   - Verifies mandatory prerequisites against completed courses.
   - Excludes ineligible courses before scoring and records explicit rejection reasons.
4. Forward Chaining Deductive Inference: Runs production rules agenda (Match-Resolve-Act).
5. Non-Monotonic Default Reasoning: Resolves missing attributes via DR01 - DR05 and hypotheses.
6. Multi-Criteria Recommendation Scoring: Calculates 4-factor weighted confidence metrics:
   - Interest Match (40%)
   - Career Goal Match (35%)
   - CGPA Readiness (15%)
   - Prerequisite Verification (10%)
7. Course Ranking & Tier Assignment: Deduplicates, threshold-filters, and sorts courses.
8. Explainable AI (XAI) Generation: Creates transparent natural language justifications.
9. Reasoning Audit Logging: Tracks chronological steps for inspection and transparency.
10. Database Persistence: Saves recommendation runs to MySQL recommendation_history.

Strict Safety: Zero eval() / exec() usage. Parameterized queries only.
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact
from ai_engine.rule_manager import RuleManager
from ai_engine.forward_chaining import ForwardChainingEngine
from ai_engine.default_reasoning import DefaultReasoningEngine
from ai_engine.recommendation_scorer import RecommendationScorer
from ai_engine.course_ranker import CourseRanker
from ai_engine.explanation_generator import ExplanationGenerator
from ai_engine.reasoning_logger import ReasoningLogger
from database.db_connection import get_db_cursor


class InferenceEngine:
    """Master AI Inference Engine orchestrating forward chaining and default reasoning."""

    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        self.kb = knowledge_base or KnowledgeBase()
        self.rule_manager = RuleManager()
        self.forward_chaining = ForwardChainingEngine()
        self.default_reasoning = DefaultReasoningEngine()
        self.logger = ReasoningLogger()

    def _normalize_student_facts(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes and sanitizes student facts for working memory."""
        # Student ID
        student_id = student_profile.get("student_id") or student_profile.get("id") or 0
        try:
            student_id = int(student_id)
        except (ValueError, TypeError):
            student_id = 0

        # CGPA
        raw_cgpa = student_profile.get("cgpa")
        cgpa_val: Optional[float] = None
        if raw_cgpa is not None and raw_cgpa != "":
            try:
                cgpa_val = float(raw_cgpa)
            except (ValueError, TypeError):
                cgpa_val = None

        # Interests
        raw_interests = student_profile.get("interests", [])
        if isinstance(raw_interests, str):
            interests = [i.strip() for i in raw_interests.split(",") if i.strip()]
        elif isinstance(raw_interests, (list, tuple, set)):
            interests = [str(i).strip() for i in raw_interests if str(i).strip()]
        else:
            interests = []

        # Deduplicate student interests preserving order
        unique_interests = list(dict.fromkeys(interests))

        # Career Goal
        career_goal = str(student_profile.get("career_goal", "")).strip()

        # Semester
        try:
            semester = int(student_profile.get("semester", 1) or 1)
        except (ValueError, TypeError):
            semester = 1

        # Completed Courses
        completed = student_profile.get("completed_courses")
        if completed is not None:
            if isinstance(completed, str):
                completed = [c.strip() for c in completed.split(",") if c.strip()]
            else:
                completed = [str(c).strip() for c in completed if str(c).strip()]

        return {
            "student_id": student_id,
            "cgpa": cgpa_val,
            "semester": semester,
            "department": str(student_profile.get("department", "Computer Science")),
            "interests": unique_interests,
            "career_goal": career_goal,
            "completed_courses": completed
        }

    def evaluate_course_eligibility(
        self,
        course_fact: CourseKnowledgeFact,
        student_facts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enforces mandatory course eligibility as a hard constraint.
        Checks:
        1. Active course status.
        2. Minimum CGPA threshold (student CGPA >= course minimum CGPA).
        3. Prerequisite course requirements.
        Returns eligibility verdict and explicit rejection reasons.
        """
        rejection_reasons: List[str] = []

        # 1. Course Active Status
        if not course_fact.is_active:
            rejection_reasons.append("Course is currently inactive in the university curriculum.")

        # 2. Minimum CGPA Verification
        student_cgpa = student_facts.get("cgpa")
        min_cgpa = float(course_fact.minimum_cgpa or 0.0)

        if min_cgpa > 0.0:
            if student_cgpa is None:
                rejection_reasons.append(
                    f"Academic eligibility unverified: Requires minimum CGPA {min_cgpa:.2f}, but student CGPA is not provided."
                )
            elif student_cgpa < min_cgpa:
                deficit = min_cgpa - student_cgpa
                rejection_reasons.append(
                    f"CGPA requirement not met (Required: {min_cgpa:.2f}, Current: {student_cgpa:.2f}, Deficit: {deficit:.2f})."
                )

        # 3. Prerequisite Verification (Hard Constraint for Formal Prerequisites)
        completed = student_facts.get("completed_courses")
        prereqs = course_fact.prerequisite_courses or []
        prereq_text = str(course_fact.prerequisites_text or "").strip()

        if completed is not None and len(completed) > 0:
            completed_norm = {str(c).strip().lower() for c in completed if str(c).strip()}
            required_codes = [
                p.get("course_code", "").strip().lower()
                for p in prereqs if isinstance(p, dict) and p.get("course_code")
            ]
            if required_codes:
                missing = [
                    req for req in required_codes
                    if not any(req in comp or comp in req for comp in completed_norm)
                ]
                if missing:
                    rejection_reasons.append(f"Prerequisite course(s) not completed: {', '.join(missing)}.")
            elif prereq_text and prereq_text.lower() not in ("none", "nil"):
                prereq_parts = [x.strip().lower() for x in prereq_text.replace(";", ",").split(",") if x.strip()]
                # If specific course codes are specified in the text (e.g. CS-401)
                course_code_prereqs = [p for p in prereq_parts if "cs-" in p]
                if course_code_prereqs:
                    missing_codes = [
                        p for p in course_code_prereqs
                        if not any(p in comp or comp in p for comp in completed_norm)
                    ]
                    if missing_codes:
                        rejection_reasons.append(f"Prerequisite course(s) not completed: {', '.join(missing_codes)}.")

        is_eligible = len(rejection_reasons) == 0
        return {
            "is_eligible": is_eligible,
            "reasons": rejection_reasons
        }

    def infer(
        self,
        student_profile: Dict[str, Any],
        min_score_threshold: float = 0.0,
        top_n: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes full inference cycle:
        1. Normalizes student profile facts.
        2. Evaluates hard eligibility constraints for all active courses.
        3. Executes forward-chaining over active production rules.
        4. Identifies missing information and applies default reasoning (DR01 - DR05).
        5. Calculates multi-criteria confidence scores.
        6. Ranks, filters, and assigns recommendation tiers.
        7. Generates XAI explanations and executive summary.
        8. Logs reasoning steps to audit trail.
        """
        self.logger.clear()
        student_facts = self._normalize_student_facts(student_profile)
        execution_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        all_courses = self.kb.get_all_courses(active_only=False)
        eligible_course_ids: Set[int] = set()
        rejected_courses: List[Dict[str, Any]] = []

        # ---------------------------------------------------------------------
        # 1. Hard Course Eligibility Evaluation
        # ---------------------------------------------------------------------
        for course_fact in all_courses:
            elig_res = self.evaluate_course_eligibility(course_fact, student_facts)
            if elig_res["is_eligible"]:
                eligible_course_ids.add(course_fact.course_id)
            else:
                rej_explanation = ExplanationGenerator.generate_rejection_explanation(
                    course_data=course_fact.to_dict(),
                    student_profile=student_facts,
                    reasons=elig_res["reasons"]
                )
                rejected_courses.append({
                    "course_id": course_fact.course_id,
                    "course_code": course_fact.course_code,
                    "course_name": course_fact.course_name,
                    "reasons": elig_res["reasons"],
                    "explanation": rej_explanation
                })

        # ---------------------------------------------------------------------
        # 2. Forward-Chaining Deduction Pass
        # ---------------------------------------------------------------------
        active_rules = self.rule_manager.get_all_rules(active_only=True)
        fc_results = self.forward_chaining.run(
            working_memory=student_facts,
            rules=active_rules,
            knowledge_base=self.kb,
            logger=self.logger
        )
        fc_candidates = fc_results.get("candidate_courses", [])
        fired_rules = fc_results.get("fired_rules", [])

        # ---------------------------------------------------------------------
        # 3. Non-Monotonic Default Reasoning Pass
        # ---------------------------------------------------------------------
        def_results = self.default_reasoning.evaluate(student_facts, knowledge_base=self.kb)
        def_candidates = def_results.get("recommended_courses", [])
        applied_default_rules = def_results.get("applied_default_rules", [])
        assumptions_made = def_results.get("assumptions_made", [])
        clarifications = def_results.get("clarification_messages", [])

        # ---------------------------------------------------------------------
        # 4. Merge Eligible Candidate Courses
        # ---------------------------------------------------------------------
        candidate_pool: Dict[int, Dict[str, Any]] = {}

        # Add forward chaining candidates (only if eligible)
        for cand in fc_candidates:
            c_id = int(cand["course_id"])
            if c_id in eligible_course_ids:
                candidate_pool[c_id] = dict(cand)

        # Merge default reasoning candidates if eligible and not already covered
        for def_cand in def_candidates:
            c_id = int(def_cand["course_id"])
            if c_id in eligible_course_ids:
                if c_id not in candidate_pool:
                    candidate_pool[c_id] = {
                        "course_id": c_id,
                        "course_code": def_cand.get("course_code", f"CS-{c_id}"),
                        "course_name": def_cand.get("course_name", f"Course #{c_id}"),
                        "priority": def_cand.get("priority", 5),
                        "match_score": def_cand.get("match_score", 50.0),
                        "reasons": [def_cand.get("explanation", "Recommended via default fallback logic")],
                        "fired_rules": [def_cand.get("rule_applied", "Default Rule")],
                        "matched_interests": def_cand.get("matched_interests", []),
                        "matched_career_goals": def_cand.get("matched_career_goals", []),
                        "prerequisites_verified": def_cand.get("prerequisites_verified", True),
                        "prerequisites_note": def_cand.get("prerequisites_note", ""),
                        "is_general_recommendation": def_cand.get("is_general_recommendation", False),
                        "is_default_reasoning": True,
                        "fallback_strategy": def_cand.get("fallback_strategy", "")
                    }
                else:
                    if not def_cand.get("prerequisites_verified", True):
                        candidate_pool[c_id]["prerequisites_verified"] = False
                        candidate_pool[c_id]["prerequisites_note"] = def_cand.get("prerequisites_note", "")

        # ---------------------------------------------------------------------
        # 5. Multi-Factor Recommendation Scoring
        # ---------------------------------------------------------------------
        scored_candidates: List[Dict[str, Any]] = []

        for c_id, cand in candidate_pool.items():
            course_fact = self.kb.get_course_by_id(c_id)
            if not course_fact or not course_fact.is_active:
                continue

            scoring_result = RecommendationScorer.score_course(
                student_profile=student_facts,
                course_fact=course_fact,
                rule_priority=cand.get("priority", 5),
                matched_interests=cand.get("matched_interests"),
                matched_career_goals=cand.get("matched_career_goals")
            )

            cand_updated = dict(cand)
            cand_updated["minimum_cgpa"] = course_fact.minimum_cgpa
            cand_updated["difficulty_level"] = course_fact.difficulty_level
            cand_updated["prerequisites_text"] = course_fact.prerequisites_text
            cand_updated["career_goals"] = course_fact.career_goals
            cand_updated["course_interests"] = course_fact.interests

            # Normalized suitability score and component breakdown
            cand_updated["suitability_score"] = scoring_result["suitability_score"]
            cand_updated["match_score"] = scoring_result["suitability_score"]
            cand_updated["score_breakdown"] = scoring_result["breakdown"]
            cand_updated["career_goal_matched"] = scoring_result["career_goal_matched"]
            cand_updated["matched_interests"] = scoring_result["matched_interests"]

            # Generate natural language XAI explanation
            cand_updated["explanation"] = ExplanationGenerator.generate_recommendation_explanation(
                cand_updated,
                student_facts
            )

            scored_candidates.append(cand_updated)

        # ---------------------------------------------------------------------
        # 6. Multi-Factor Course Ranking & Threshold Filtering
        # ---------------------------------------------------------------------
        ranked_courses = CourseRanker.rank_and_filter(
            candidate_courses=scored_candidates,
            min_score_threshold=min_score_threshold,
            top_n=top_n
        )

        # ---------------------------------------------------------------------
        # 7. Executive Summary & Audit Output
        # ---------------------------------------------------------------------
        summary = ExplanationGenerator.generate_comparative_summary(
            ranked_courses=ranked_courses,
            student_profile=student_facts
        )

        return {
            "student_profile": student_facts,
            "student_id": student_facts["student_id"],
            "timestamp": execution_timestamp,
            "recommendations": ranked_courses,
            "rejected_courses": rejected_courses,
            "fired_rules": fired_rules,
            "applied_default_rules": applied_default_rules,
            "assumptions_made": assumptions_made,
            "clarification_messages": clarifications,
            "is_default_reasoning_used": def_results.get("is_default_reasoning_used", False),
            "academic_info_required": def_results.get("academic_info_required", False),
            "unverified_prerequisites_found": def_results.get("unverified_prerequisites_found", False),
            "summary": summary,
            "total_candidates": len(scored_candidates),
            "total_recommended": len(ranked_courses),
            "total_rejected": len(rejected_courses),
            "audit_trail": self.logger.get_history()
        }

    def recommend_and_persist(
        self,
        student_id: int,
        student_profile: Dict[str, Any],
        min_score_threshold: float = 0.0,
        top_n: Optional[int] = 5
    ) -> Dict[str, Any]:
        """
        Executes inference and persists the top recommendations into MySQL recommendation_history.
        Uses safe, parameterized transactions with run-level duplicate prevention.
        """
        profile = dict(student_profile)
        profile["student_id"] = student_id

        inference_result = self.infer(
            student_profile=profile,
            min_score_threshold=min_score_threshold,
            top_n=top_n
        )
        recommendations = inference_result.get("recommendations", [])

        if recommendations and student_id > 0:
            inserted_course_ids: Set[int] = set()
            try:
                with get_db_cursor(commit=True) as (cursor, _):
                    for rec in recommendations:
                        c_id = int(rec.get("course_id", 0))
                        # Prevent duplicate records within the same recommendation run
                        if not c_id or c_id in inserted_course_ids:
                            continue

                        inserted_course_ids.add(c_id)
                        score = rec.get("suitability_score") or rec.get("match_score", 0.0)
                        reasoning_text = rec.get("explanation", "")

                        cursor.execute("""
                            INSERT INTO recommendation_history
                                (student_id, recommended_course_id, recommendation_score, reasoning, created_at)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            student_id,
                            c_id,
                            round(float(score), 2),
                            reasoning_text,
                            datetime.now()
                        ))
                inference_result["persisted_count"] = len(inserted_course_ids)
            except Exception as e:
                inference_result["persistence_error"] = str(e)

        return inference_result


def generate_recommendations(
    student_data: Dict[str, Any],
    knowledge_base: Optional[KnowledgeBase] = None,
    min_score_threshold: float = 0.0,
    top_n: Optional[int] = None
) -> Dict[str, Any]:
    """
    Primary reusable API function to generate explainable course recommendations.
    Accepts student profile facts and returns structured recommendation results.
    """
    engine = InferenceEngine(knowledge_base=knowledge_base)
    return engine.infer(
        student_profile=student_data,
        min_score_threshold=min_score_threshold,
        top_n=top_n
    )


# Alias for backward compatibility
recommend_courses = generate_recommendations
