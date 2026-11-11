"""
Knowledge Base Interface Module
Represents structured course knowledge facts, domain ontologies,
and provides declarative high-level access methods for the recommendation system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from ai_engine.knowledge_repository import KnowledgeRepository
from ai_engine.knowledge_validator import KnowledgeValidator


@dataclass
class CourseKnowledgeFact:
    """
    Formal knowledge representation of an elective course fact within the AI Knowledge Base.
    Encapsulates academic requirements, difficulty rating, domain interests, and career opportunities.
    """
    course_id: int
    course_code: str
    course_name: str
    description: str
    minimum_cgpa: float
    difficulty_level: str
    prerequisites_text: str
    prerequisite_courses: List[Dict[str, Any]] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    career_goals: List[str] = field(default_factory=list)
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the course knowledge fact to a dictionary representation."""
        return {
            "course_id": self.course_id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "description": self.description,
            "minimum_cgpa": float(self.minimum_cgpa),
            "difficulty_level": self.difficulty_level,
            "prerequisites_text": self.prerequisites_text,
            "prerequisite_courses": self.prerequisite_courses,
            "interests": self.interests,
            "career_goals": self.career_goals,
            "is_active": self.is_active
        }

    def matches_interest(self, interest_name: str) -> bool:
        """Checks if this course aligns with a given interest name (case-insensitive)."""
        target = interest_name.strip().lower()
        return any(target == i.strip().lower() for i in self.interests)

    def matches_career_goal(self, goal_name: str) -> bool:
        """Checks if this course aligns with a given career goal (case-insensitive)."""
        target = goal_name.strip().lower()
        return any(target == g.strip().lower() for g in self.career_goals)

    def is_eligible(self, student_cgpa: float) -> bool:
        """Determines if a student's CGPA satisfies the minimum threshold."""
        try:
            return float(student_cgpa) >= float(self.minimum_cgpa)
        except (ValueError, TypeError):
            return False

    @property
    def prerequisite_codes(self) -> List[str]:
        """Returns list of prerequisite course codes."""
        return [p.get("course_code", "") for p in self.prerequisite_courses if p.get("course_code")]


class KnowledgeBase:
    """
    AI Knowledge Base Manager.
    Acts as the single point of entry for knowledge retrieval, ontological queries,
    and validation audits.
    """

    def __init__(self, repository: Optional[KnowledgeRepository] = None):
        self.repository = repository or KnowledgeRepository()
        self.validator = KnowledgeValidator()
        self._cache: Optional[Dict[int, CourseKnowledgeFact]] = None

    def _convert_raw_to_fact(self, raw: Dict[str, Any]) -> CourseKnowledgeFact:
        """Converts raw repository dictionary into a strongly-typed CourseKnowledgeFact."""
        interest_names = [i["interest_name"] for i in raw.get("interests", []) if "interest_name" in i]
        career_names = [g["goal_name"] for g in raw.get("career_goals", []) if "goal_name" in g]

        return CourseKnowledgeFact(
            course_id=raw["course_id"],
            course_code=raw["course_code"],
            course_name=raw["course_name"],
            description=raw.get("description") or "",
            minimum_cgpa=float(raw.get("minimum_cgpa") or 0.0),
            difficulty_level=raw.get("difficulty_level") or "Intermediate",
            prerequisites_text=raw.get("prerequisites_text") or "",
            prerequisite_courses=raw.get("prerequisite_courses", []),
            interests=interest_names,
            career_goals=career_names,
            is_active=bool(raw.get("is_active", True))
        )

    def reload(self) -> None:
        """Flushes in-memory cache and reloads knowledge from MySQL."""
        raw_courses = self.repository.get_all_courses(active_only=False)
        cache_map = {}
        for rc in raw_courses:
            fact = self._convert_raw_to_fact(rc)
            cache_map[fact.course_id] = fact
        self._cache = cache_map

    def _ensure_loaded(self) -> None:
        """Lazy loads the knowledge base cache if not already populated."""
        if self._cache is None:
            self.reload()

    # =========================================================================
    # Course Retrieval Queries
    # =========================================================================

    def get_all_courses(self, active_only: bool = True) -> List[CourseKnowledgeFact]:
        """Retrieves all course knowledge facts."""
        self._ensure_loaded()
        courses = list(self._cache.values())
        if active_only:
            courses = [c for c in courses if c.is_active]
        return sorted(courses, key=lambda x: x.course_code)

    def get_course_by_id(self, course_id: int) -> Optional[CourseKnowledgeFact]:
        """Retrieves a course knowledge fact by primary key ID."""
        self._ensure_loaded()
        return self._cache.get(course_id)

    def get_course_by_code(self, course_code: str) -> Optional[CourseKnowledgeFact]:
        """Retrieves a course knowledge fact by course code (e.g., 'CS-401')."""
        self._ensure_loaded()
        code_norm = course_code.strip().lower()
        for course in self._cache.values():
            if course.course_code.strip().lower() == code_norm:
                return course
        return None

    def get_courses_by_interest(self, interest_name_or_id: Union[str, int], active_only: bool = True) -> List[CourseKnowledgeFact]:
        """Retrieves courses matching a specific domain interest."""
        self._ensure_loaded()
        courses = self.get_all_courses(active_only=active_only)

        if isinstance(interest_name_or_id, int):
            # Resolve interest ID from repository
            all_ints = self.repository.get_all_interests()
            matched_name = next((i["interest_name"] for i in all_ints if i["id"] == interest_name_or_id), None)
            if not matched_name:
                return []
            target = matched_name.strip().lower()
        else:
            target = str(interest_name_or_id).strip().lower()

        target_norm = target.replace(" ", "").replace("-", "").replace("_", "")
        return [
            c for c in courses
            if any(
                i.strip().lower() == target
                or i.strip().lower().replace(" ", "").replace("-", "").replace("_", "") == target_norm
                or target_norm in i.strip().lower().replace(" ", "")
                or i.strip().lower().replace(" ", "") in target_norm
                for i in c.interests
            )
        ]

    def get_courses_by_career_goal(self, goal_name_or_id: Union[str, int], active_only: bool = True) -> List[CourseKnowledgeFact]:
        """Retrieves courses aligned with a specific career goal."""
        self._ensure_loaded()
        courses = self.get_all_courses(active_only=active_only)

        if isinstance(goal_name_or_id, int):
            all_goals = self.repository.get_all_career_goals()
            matched_name = next((g["goal_name"] for g in all_goals if g["id"] == goal_name_or_id), None)
            if not matched_name:
                return []
            target = matched_name.strip().lower()
        else:
            target = str(goal_name_or_id).strip().lower()

        target_norm = target.replace(" ", "").replace("-", "").replace("_", "")
        return [
            c for c in courses
            if any(g.strip().lower() == target or g.strip().lower().replace(" ", "").replace("-", "").replace("_", "") == target_norm for g in c.career_goals)
        ]

    def get_courses_by_cgpa(self, student_cgpa: float, active_only: bool = True) -> List[CourseKnowledgeFact]:
        """Retrieves courses where student CGPA >= minimum course CGPA requirement."""
        courses = self.get_all_courses(active_only=active_only)
        return [c for c in courses if c.is_eligible(student_cgpa)]

    def get_course_prerequisites(self, course_id_or_code: Union[str, int]) -> Dict[str, Any]:
        """
        Retrieves textual and structured prerequisite course dependencies for a course.
        """
        if isinstance(course_id_or_code, int):
            course = self.get_course_by_id(course_id_or_code)
        else:
            course = self.get_course_by_code(str(course_id_or_code))

        if not course:
            return {"course": None, "prerequisites_text": "", "prerequisite_courses": []}

        return {
            "course": course.to_dict(),
            "prerequisites_text": course.prerequisites_text,
            "prerequisite_courses": course.prerequisite_courses
        }

    # =========================================================================
    # Interests & Career Goals Master List
    # =========================================================================

    def get_all_interests(self) -> List[Dict[str, Any]]:
        """Retrieves all registered domain interests."""
        return self.repository.get_all_interests()

    def get_all_career_goals(self) -> List[Dict[str, Any]]:
        """Retrieves all registered career goals."""
        return self.repository.get_all_career_goals()

    # =========================================================================
    # Complete Knowledge Base Export & Validation
    # =========================================================================

    def get_complete_knowledge_base(self, active_only: bool = False) -> Dict[str, Any]:
        """
        Exports the entire knowledge base state including courses, ontologies, and summary metrics.
        """
        courses = self.get_all_courses(active_only=active_only)
        interests = self.get_all_interests()
        career_goals = self.get_all_career_goals()

        return {
            "total_courses": len(courses),
            "total_interests": len(interests),
            "total_career_goals": len(career_goals),
            "courses": [c.to_dict() for c in courses],
            "interests": interests,
            "career_goals": career_goals
        }

    def validate_knowledge_base(self) -> Dict[str, Any]:
        """
        Runs an audit over the knowledge repository using KnowledgeValidator.
        """
        return self.validator.audit_database()
