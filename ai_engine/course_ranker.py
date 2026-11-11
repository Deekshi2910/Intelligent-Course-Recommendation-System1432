"""
Course Ranker Module
Phase 9: AI Inference Engine

Provides multi-tier ranking, deduplication, threshold filtering,
and categorization for candidate course recommendations:
- Sorts primarily by recommendation score (Suitability Percentage DESC).
- Uses rule priority as secondary ranking factor (Priority DESC).
- Uses course code as deterministic tertiary tie-breaker.
- Avoids duplicate course entries by deduplicating on course_id.
- Categorizes courses into pedagogical recommendation tiers.
"""

from typing import List, Dict, Any, Optional


class CourseRanker:
    """Ranks, filters, and tiers candidate course recommendations."""

    @classmethod
    def rank_and_filter(
        cls,
        candidate_courses: List[Dict[str, Any]],
        min_score_threshold: float = 0.0,
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Deduplicates, scores, filters by minimum threshold, and sorts candidates.
        Sorting keys:
        1. Recommendation Suitability Score DESC (100.0 to 0.0).
        2. Rule Priority DESC (P-10 to P-1).
        3. Course Code ASC (consistent tie-breaker).
        """
        # Deduplicate courses by course_id while merging reasons and preserving max metrics
        dedup_map: Dict[int, Dict[str, Any]] = {}

        for item in candidate_courses:
            c_id = int(item.get("course_id", 0))
            if not c_id:
                continue

            score = float(item.get("suitability_score") or item.get("match_score") or item.get("final_score") or 0.0)
            priority = int(item.get("priority", 1))

            if c_id not in dedup_map:
                entry = dict(item)
                entry["match_score"] = score
                entry["suitability_score"] = score
                entry["reasons"] = list(item.get("reasons", []))
                entry["fired_rules"] = list(item.get("fired_rules", []))
                entry["matched_interests"] = list(item.get("matched_interests", []))
                dedup_map[c_id] = entry
            else:
                existing = dedup_map[c_id]
                existing["priority"] = max(existing["priority"], priority)
                existing["match_score"] = max(existing["match_score"], score)
                existing["suitability_score"] = max(existing["suitability_score"], score)

                # Merge unique reasons
                for r in item.get("reasons", []):
                    if r not in existing["reasons"]:
                        existing["reasons"].append(r)

                # Merge unique fired rules
                for rule_name in item.get("fired_rules", []):
                    if rule_name not in existing["fired_rules"]:
                        existing["fired_rules"].append(rule_name)

                # Merge unique matched interests
                for mi in item.get("matched_interests", []):
                    if mi not in existing["matched_interests"]:
                        existing["matched_interests"].append(mi)

        # Filter by minimum score threshold
        filtered = [
            c for c in dedup_map.values()
            if float(c.get("suitability_score", 0.0)) >= min_score_threshold
        ]

        # Multi-factor sort:
        # 1. Suitability Score DESC
        # 2. Rule Priority DESC
        # 3. Course Code ASC (deterministic tie-breaking)
        sorted_courses = sorted(
            filtered,
            key=lambda c: (
                float(c.get("suitability_score", 0.0)),
                int(c.get("priority", 1)),
                -ord(c.get("course_code", "A")[0]) if c.get("course_code") else 0
            ),
            reverse=True
        )

        # Assign pedagogical recommendation tiers
        for idx, course in enumerate(sorted_courses, 1):
            course["rank"] = idx
            score = float(course.get("suitability_score", 0.0))
            prio = int(course.get("priority", 1))

            if score >= 85.0 or (prio >= 8 and score >= 75.0):
                course["recommendation_tier"] = "Highly Recommended"
                course["tier_badge_class"] = "bg-success"
            elif score >= 65.0:
                course["recommendation_tier"] = "Strong Match"
                course["tier_badge_class"] = "bg-primary"
            elif course.get("is_general_recommendation"):
                course["recommendation_tier"] = "Foundational Breadth"
                course["tier_badge_class"] = "bg-secondary"
            else:
                course["recommendation_tier"] = "Elective Option"
                course["tier_badge_class"] = "bg-info"

        if top_n and top_n > 0:
            return sorted_courses[:top_n]
        return sorted_courses
