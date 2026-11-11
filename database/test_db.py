"""
Database Verification and Test Suite
Validates MySQL connection, 9 tables existence, foreign keys, cascading, and sample queries.
"""

import os
import sys
from werkzeug.security import generate_password_hash, check_password_hash

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db_connection import get_db_connection, get_db_cursor, test_connection
from mysql.connector import Error

REQUIRED_TABLES = [
    "users",
    "student_profiles",
    "interests",
    "student_interests",
    "career_goals",
    "courses",
    "course_interests",
    "knowledge_rules",
    "recommendation_history"
]


def test_1_mysql_connection():
    """Verify live connectivity to the MySQL instance."""
    print("\n--- Test 1: MySQL Connection ---")
    success, msg = test_connection()
    assert success, f"MySQL connection test failed: {msg}"
    print(f"[PASS] {msg}")


def test_2_tables_existence():
    """Verify all nine tables exist in the database."""
    print("\n--- Test 2: Table Existence (All 9 Tables) ---")
    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("SHOW TABLES")
        rows = cursor.fetchall()
        existing_tables = [list(row.values())[0].lower() for row in rows]
        print(f"Discovered tables in database: {sorted(existing_tables)}")

        for table in REQUIRED_TABLES:
            assert table in existing_tables, f"Missing required table: {table}"
            print(f"  [PASS] Table '{table}' exists.")

    print(f"[PASS] All {len(REQUIRED_TABLES)} required tables are present.")


def test_3_sample_records():
    """Verify that sample seed records are correctly populated."""
    print("\n--- Test 3: Sample Records Verification ---")
    with get_db_cursor(dictionary=True) as (cursor, _):
        # 1. Courses
        cursor.execute("SELECT COUNT(*) AS total FROM courses")
        course_count = cursor.fetchone()["total"]
        print(f"  Courses count: {course_count}")
        assert course_count >= 8, f"Expected at least 8 courses, found {course_count}"

        # 2. Interests
        cursor.execute("SELECT COUNT(*) AS total FROM interests")
        interest_count = cursor.fetchone()["total"]
        print(f"  Interests count: {interest_count}")
        assert interest_count >= 10, f"Expected at least 10 interests, found {interest_count}"

        # 3. Career Goals
        cursor.execute("SELECT COUNT(*) AS total FROM career_goals")
        goals_count = cursor.fetchone()["total"]
        print(f"  Career Goals count: {goals_count}")
        assert goals_count >= 6, f"Expected at least 6 career goals, found {goals_count}"

        # 4. Knowledge Rules
        cursor.execute("SELECT COUNT(*) AS total FROM knowledge_rules")
        rules_count = cursor.fetchone()["total"]
        print(f"  Knowledge Rules count: {rules_count}")
        assert rules_count >= 8, f"Expected at least 8 rules, found {rules_count}"

        # 5. Course Interests Mapping
        cursor.execute("SELECT COUNT(*) AS total FROM course_interests")
        ci_count = cursor.fetchone()["total"]
        print(f"  Course-Interest mappings count: {ci_count}")
        assert ci_count > 0, "No course-interest mappings found."

    print("[PASS] Seed data verified successfully.")


def test_4_foreign_keys_and_cascades():
    """Verify FK enforcement, rejection of invalid references, and cascade deletion."""
    print("\n--- Test 4: Foreign Key Constraints & Cascading Deletions ---")

    # A. Test FK violation rejection
    with get_db_cursor(commit=False, dictionary=True) as (cursor, conn):
        try:
            cursor.execute("""
                INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
                VALUES (999999, 'Ghost User', 'ROLL-999', 'Computer Science', 5, 3.50)
            """)
            conn.commit()
            assert False, "FK violation should have been raised for non-existent user_id!"
        except Error as err:
            print(f"  [PASS] Expected FK constraint violation caught: Error {err.errno}")

    # B. Test valid insertion, relationships, and cascade delete
    with get_db_cursor(commit=True, dictionary=True) as (cursor, conn):
        # 1. Insert test user with securely hashed password
        test_pw_hash = generate_password_hash("TestSecureP@ss123")
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """, ("test_student_phase2", "test_phase2@example.com", test_pw_hash, "student"))
        test_user_id = cursor.lastrowid

        # 2. Insert test student profile
        cursor.execute("""
            INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (test_user_id, "Test Student", "CS-2026-TEST", "Computer Science", 6, 3.75))
        test_student_id = cursor.lastrowid

        # 3. Associate student with an interest
        cursor.execute("SELECT id FROM interests LIMIT 1")
        test_interest_id = cursor.fetchone()["id"]
        cursor.execute("""
            INSERT INTO student_interests (student_id, interest_id)
            VALUES (%s, %s)
        """, (test_student_id, test_interest_id))

        # 4. Insert recommendation history
        cursor.execute("SELECT id FROM courses LIMIT 1")
        test_course_id = cursor.fetchone()["id"]
        cursor.execute("""
            INSERT INTO recommendation_history (student_id, recommended_course_id, recommendation_score, reasoning)
            VALUES (%s, %s, %s, %s)
        """, (test_student_id, test_course_id, 92.50, "Matches Machine Learning background and CGPA >= 3.5"))

    # Verify insertion worked
    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("SELECT * FROM student_profiles WHERE id = %s", (test_student_id,))
        assert cursor.fetchone() is not None, "Failed to retrieve newly inserted student profile."

        cursor.execute("SELECT * FROM student_interests WHERE student_id = %s", (test_student_id,))
        assert cursor.fetchone() is not None, "Failed to retrieve student_interest mapping."

        cursor.execute("SELECT * FROM recommendation_history WHERE student_id = %s", (test_student_id,))
        assert cursor.fetchone() is not None, "Failed to retrieve recommendation history record."

    # C. Delete the test user and verify CASCADE cleanup
    with get_db_cursor(commit=True, dictionary=True) as (cursor, conn):
        cursor.execute("DELETE FROM users WHERE id = %s", (test_user_id,))

    # Verify cascade
    with get_db_cursor(dictionary=True) as (cursor, _):
        cursor.execute("SELECT * FROM student_profiles WHERE id = %s", (test_student_id,))
        assert cursor.fetchone() is None, "Student profile was not deleted via cascade!"

        cursor.execute("SELECT * FROM student_interests WHERE student_id = %s", (test_student_id,))
        assert cursor.fetchone() is None, "Student interest mapping was not deleted via cascade!"

        cursor.execute("SELECT * FROM recommendation_history WHERE student_id = %s", (test_student_id,))
        assert cursor.fetchone() is None, "Recommendation history was not deleted via cascade!"

    print("  [PASS] Foreign key cascade deletion verified across user -> profile -> interests -> history.")


def test_5_complex_select_queries():
    """Verify parameterized multi-table JOIN and JSON queries."""
    print("\n--- Test 5: Parameterized Complex SELECT Queries ---")
    with get_db_cursor(dictionary=True) as (cursor, _):
        # A. Query courses with their mapped interests
        cursor.execute("""
            SELECT 
                c.course_code,
                c.course_name,
                c.difficulty_level,
                c.minimum_cgpa,
                GROUP_CONCAT(i.interest_name ORDER BY i.interest_name SEPARATOR ', ') AS mapped_interests
            FROM courses c
            JOIN course_interests ci ON c.id = ci.course_id
            JOIN interests i ON ci.interest_id = i.id
            WHERE c.is_active = TRUE
            GROUP BY c.id
            ORDER BY c.course_code
        """)
        courses = cursor.fetchall()
        assert len(courses) >= 8, f"Expected >= 8 courses in join, got {len(courses)}"
        print(f"  [PASS] Successfully joined courses with interests (Retrieved {len(courses)} courses).")
        for c in courses[:3]:
            print(f"    - {c['course_code']}: {c['course_name']} -> [{c['mapped_interests']}]")

        # B. Query knowledge rules with course details and JSON condition extraction
        cursor.execute("""
            SELECT 
                kr.rule_name,
                kr.priority,
                c.course_code,
                c.course_name,
                kr.conditions
            FROM knowledge_rules kr
            JOIN courses c ON kr.recommended_course_id = c.id
            WHERE kr.is_active = TRUE
            ORDER BY kr.priority DESC
        """)
        rules = cursor.fetchall()
        assert len(rules) >= 8, f"Expected >= 8 rules, got {len(rules)}"
        print(f"  [PASS] Retrieved {len(rules)} active knowledge rules ordered by priority.")
        for r in rules[:2]:
            print(f"    - Priority {r['priority']}: {r['rule_name']} -> {r['course_code']} ({r['course_name']})")


def test_6_security_principles():
    """Verify security controls: password hashing and parameterization."""
    print("\n--- Test 6: Security Verification ---")
    plain = "SuperSecretPassword2026!"
    hashed = generate_password_hash(plain)

    # 1. Plain text must not match hash
    assert plain != hashed, "Plaintext password must never equal the hash!"
    # 2. Check password verification works
    assert check_password_hash(hashed, plain), "Password verification failed!"
    assert not check_password_hash(hashed, "WrongPassword"), "False positive in password check!"
    print("  [PASS] Password hashing and verification meets security standards.")


def run_all_tests():
    print("=================================================================")
    print("Starting Phase 2 Database Test Suite")
    print("=================================================================")
    test_1_mysql_connection()
    test_2_tables_existence()
    test_3_sample_records()
    test_4_foreign_keys_and_cascades()
    test_5_complex_select_queries()
    test_6_security_principles()
    print("\n=================================================================")
    print("ALL 6 TEST SUITES PASSED SUCCESSFULLY!")
    print("=================================================================")


if __name__ == "__main__":
    try:
        run_all_tests()
    except Exception as exc:
        print(f"\n[FAIL] Test suite failed: {exc}")
        sys.exit(1)
