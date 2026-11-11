"""
Knowledge Repository Module
Low-level data access layer interfacing with MySQL.
Retrieves and persists structured course facts, domain interests,
career goals, prerequisite dependencies, and M:N relationships.
Utilizes parameterized SQL queries exclusively.
"""

from typing import List, Dict, Any, Optional
from database.db_connection import get_db_cursor
from mysql.connector import Error


class KnowledgeRepository:
    """Encapsulates all database interactions for the AI Knowledge Base."""

    def __init__(self):
        pass

    # =========================================================================
    # Courses Retrieval
    # =========================================================================

    def get_all_courses(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves all courses with joined interests, career goals, and prerequisite course codes.
        """
        query = """
            SELECT
                c.id AS course_id,
                c.course_code,
                c.course_name,
                c.description,
                c.minimum_cgpa,
                c.difficulty_level,
                c.career_scope,
                c.prerequisites AS prerequisites_text,
                c.is_active
            FROM courses c
        """
        params = []
        if active_only:
            query += " WHERE c.is_active = TRUE"
        query += " ORDER BY c.course_code ASC"

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, tuple(params))
            courses = cursor.fetchall()

        # Augment with relationships
        for course in courses:
            c_id = course["course_id"]
            course["interests"] = self.get_course_interests(c_id)
            course["career_goals"] = self.get_course_career_goals(c_id)
            course["prerequisite_courses"] = self.get_course_prerequisites(c_id)

        return courses

    def get_course_by_id(self, course_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single course by its primary key ID."""
        query = """
            SELECT
                c.id AS course_id,
                c.course_code,
                c.course_name,
                c.description,
                c.minimum_cgpa,
                c.difficulty_level,
                c.career_scope,
                c.prerequisites AS prerequisites_text,
                c.is_active
            FROM courses c
            WHERE c.id = %s
        """
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id,))
            course = cursor.fetchone()

        if course:
            course["interests"] = self.get_course_interests(course_id)
            course["career_goals"] = self.get_course_career_goals(course_id)
            course["prerequisite_courses"] = self.get_course_prerequisites(course_id)

        return course

    def get_course_by_code(self, course_code: str) -> Optional[Dict[str, Any]]:
        """Retrieves a course by unique course code (e.g., 'CS-401')."""
        query = """
            SELECT
                c.id AS course_id,
                c.course_code,
                c.course_name,
                c.description,
                c.minimum_cgpa,
                c.difficulty_level,
                c.career_scope,
                c.prerequisites AS prerequisites_text,
                c.is_active
            FROM courses c
            WHERE LOWER(c.course_code) = LOWER(%s)
        """
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (course_code.strip(),))
            course = cursor.fetchone()

        if course:
            c_id = course["course_id"]
            course["interests"] = self.get_course_interests(c_id)
            course["career_goals"] = self.get_course_career_goals(c_id)
            course["prerequisite_courses"] = self.get_course_prerequisites(c_id)

        return course

    # =========================================================================
    # Interests & Career Goals Retrieval
    # =========================================================================

    def get_all_interests(self) -> List[Dict[str, Any]]:
        """Retrieves all registered domain interests."""
        query = "SELECT id, interest_name FROM interests ORDER BY interest_name ASC"
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query)
            return cursor.fetchall()

    def get_all_career_goals(self) -> List[Dict[str, Any]]:
        """Retrieves all registered career pathways."""
        query = "SELECT id, goal_name, description FROM career_goals ORDER BY goal_name ASC"
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query)
            return cursor.fetchall()

    # =========================================================================
    # Relationship Retrieval
    # =========================================================================

    def get_course_interests(self, course_id: int) -> List[Dict[str, Any]]:
        """Retrieves domain interests linked to a course."""
        query = """
            SELECT i.id, i.interest_name
            FROM course_interests ci
            JOIN interests i ON ci.interest_id = i.id
            WHERE ci.course_id = %s
            ORDER BY i.interest_name ASC
        """
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id,))
            return cursor.fetchall()

    def get_course_career_goals(self, course_id: int) -> List[Dict[str, Any]]:
        """Retrieves career goals aligned with a course."""
        query = """
            SELECT cg.id, cg.goal_name, cg.description
            FROM course_career_goals ccg
            JOIN career_goals cg ON ccg.career_goal_id = cg.id
            WHERE ccg.course_id = %s
            ORDER BY cg.goal_name ASC
        """
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id,))
            return cursor.fetchall()

    def get_course_prerequisites(self, course_id: int) -> List[Dict[str, Any]]:
        """Retrieves structured prerequisite courses for a given course."""
        query = """
            SELECT
                cp.id AS prerequisite_id,
                c.id AS course_id,
                c.course_code,
                c.course_name,
                c.difficulty_level,
                c.minimum_cgpa
            FROM course_prerequisites cp
            JOIN courses c ON cp.prerequisite_course_id = c.id
            WHERE cp.course_id = %s
            ORDER BY c.course_code ASC
        """
        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id,))
            return cursor.fetchall()

    # =========================================================================
    # Filtered Knowledge Queries
    # =========================================================================

    def get_courses_by_interest(self, interest_identifier: Any, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves courses matching an interest by interest ID or interest name.
        """
        if isinstance(interest_identifier, int) or (isinstance(interest_identifier, str) and interest_identifier.isdigit()):
            int_id = int(interest_identifier)
            query = """
                SELECT DISTINCT c.id
                FROM courses c
                JOIN course_interests ci ON c.id = ci.course_id
                WHERE ci.interest_id = %s
            """
            params = [int_id]
        else:
            query = """
                SELECT DISTINCT c.id
                FROM courses c
                JOIN course_interests ci ON c.id = ci.course_id
                JOIN interests i ON ci.interest_id = i.id
                WHERE LOWER(i.interest_name) = LOWER(%s)
            """
            params = [str(interest_identifier).strip()]

        if active_only:
            query += " AND c.is_active = TRUE"

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, tuple(params))
            course_ids = [row["id"] for row in cursor.fetchall()]

        return [self.get_course_by_id(cid) for cid in course_ids if cid]

    def get_courses_by_career_goal(self, goal_identifier: Any, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves courses associated with a specific career goal.
        """
        if isinstance(goal_identifier, int) or (isinstance(goal_identifier, str) and goal_identifier.isdigit()):
            gid = int(goal_identifier)
            query = """
                SELECT DISTINCT c.id
                FROM courses c
                JOIN course_career_goals ccg ON c.id = ccg.course_id
                WHERE ccg.career_goal_id = %s
            """
            params = [gid]
        else:
            query = """
                SELECT DISTINCT c.id
                FROM courses c
                JOIN course_career_goals ccg ON c.id = ccg.course_id
                JOIN career_goals cg ON ccg.career_goal_id = cg.id
                WHERE LOWER(cg.goal_name) = LOWER(%s)
            """
            params = [str(goal_identifier).strip()]

        if active_only:
            query += " AND c.is_active = TRUE"

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, tuple(params))
            course_ids = [row["id"] for row in cursor.fetchall()]

        return [self.get_course_by_id(cid) for cid in course_ids if cid]

    def get_courses_by_cgpa(self, student_cgpa: float, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieves courses where student CGPA >= course minimum CGPA requirement.
        """
        query = """
            SELECT id
            FROM courses
            WHERE minimum_cgpa <= %s
        """
        params = [student_cgpa]
        if active_only:
            query += " AND is_active = TRUE"
        query += " ORDER BY minimum_cgpa DESC, course_code ASC"

        with get_db_cursor(dictionary=True) as (cursor, _):
            cursor.execute(query, tuple(params))
            course_ids = [row["id"] for row in cursor.fetchall()]

        return [self.get_course_by_id(cid) for cid in course_ids if cid]

    # =========================================================================
    # Knowledge Relationship Mutations (Transactional)
    # =========================================================================

    def add_course_interest(self, course_id: int, interest_id: int) -> bool:
        """Associates an interest with a course. Avoids duplicates."""
        query = """
            INSERT IGNORE INTO course_interests (course_id, interest_id)
            VALUES (%s, %s)
        """
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id, interest_id))
            return cursor.rowcount > 0

    def remove_course_interest(self, course_id: int, interest_id: int) -> bool:
        """Removes an interest mapping from a course."""
        query = "DELETE FROM course_interests WHERE course_id = %s AND interest_id = %s"
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id, interest_id))
            return cursor.rowcount > 0

    def add_course_career_goal(self, course_id: int, career_goal_id: int) -> bool:
        """Associates a career goal with a course. Avoids duplicates."""
        query = """
            INSERT IGNORE INTO course_career_goals (course_id, career_goal_id)
            VALUES (%s, %s)
        """
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id, career_goal_id))
            return cursor.rowcount > 0

    def remove_course_career_goal(self, course_id: int, career_goal_id: int) -> bool:
        """Removes a career goal mapping from a course."""
        query = "DELETE FROM course_career_goals WHERE course_id = %s AND career_goal_id = %s"
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id, career_goal_id))
            return cursor.rowcount > 0

    def add_course_prerequisite(self, course_id: int, prerequisite_course_id: int) -> bool:
        """Adds a structured course prerequisite dependency. Rejects self-dependency."""
        if course_id == prerequisite_course_id:
            raise ValueError("A course cannot be a prerequisite of itself.")

        query = """
            INSERT IGNORE INTO course_prerequisites (course_id, prerequisite_course_id)
            VALUES (%s, %s)
        """
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id, prerequisite_course_id))
            return cursor.rowcount > 0

    def remove_course_prerequisite(self, course_id: int, prerequisite_course_id: int) -> bool:
        """Removes a structured course prerequisite dependency."""
        query = "DELETE FROM course_prerequisites WHERE course_id = %s AND prerequisite_course_id = %s"
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute(query, (course_id, prerequisite_course_id))
            return cursor.rowcount > 0
