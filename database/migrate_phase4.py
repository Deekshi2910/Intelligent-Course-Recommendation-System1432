"""
Database Migration Script for Phase 4
Adds career_goal_id to student_profiles and modifies cgpa to DECIMAL(4, 2)
to support CGPA scales up to 10.00.
"""

import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db_connection import get_db_cursor
from mysql.connector import Error


def run_migration():
    print("Running Phase 4 Database Migration...")
    try:
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            # 1. Check if career_goal_id column exists
            cursor.execute("SHOW COLUMNS FROM student_profiles LIKE 'career_goal_id'")
            exists = cursor.fetchone()

            if not exists:
                print("Adding career_goal_id column and foreign key to student_profiles...")
                cursor.execute("""
                    ALTER TABLE student_profiles
                    ADD COLUMN career_goal_id INT NULL AFTER cgpa,
                    ADD CONSTRAINT fk_student_career_goal
                        FOREIGN KEY (career_goal_id) REFERENCES career_goals (id)
                        ON DELETE SET NULL
                        ON UPDATE CASCADE
                """)
                print("[SUCCESS] Added career_goal_id column with foreign key to career_goals.")
            else:
                print("[INFO] career_goal_id column already exists.")

            # 2. Modify cgpa to DECIMAL(4, 2)
            print("Upgrading cgpa column precision to DECIMAL(4, 2)...")
            cursor.execute("ALTER TABLE student_profiles MODIFY COLUMN cgpa DECIMAL(4, 2) NOT NULL DEFAULT 0.00")
            print("[SUCCESS] Modified student_profiles.cgpa to DECIMAL(4, 2).")

        return True
    except Error as err:
        print(f"[ERROR] Migration failed [Errno {err.errno}]: {err.msg}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
