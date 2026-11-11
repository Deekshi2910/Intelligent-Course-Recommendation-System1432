"""
Database Schema Initialization Script
Executes schema.sql against the target MySQL instance to set up tables and seed data.
"""

import os
import sys
import mysql.connector
from mysql.connector import Error

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config


def initialize_database(schema_path=None):
    """
    Connects to MySQL server, creates the database if needed,
    and executes all statements in schema.sql.
    """
    if schema_path is None:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    cfg = Config.get_db_config()
    print("Initiating database connection...")

    try:
        # Step 1: Connect to server (without target database first, to ensure DB can be created)
        conn = mysql.connector.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            autocommit=True
        )
        cursor = conn.cursor()

        # Step 2: Parse and execute SQL statements from schema.sql
        print(f"Executing schema from: {schema_path}")
        
        # Split statements ignoring SQL comments
        statements = []
        current = []
        for line in sql_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("--") or not stripped:
                continue
            current.append(line)
            if stripped.endswith(";"):
                statements.append("\n".join(current))
                current = []

        statements_executed = 0
        for stmt in statements:
            cleaned = stmt.strip()
            if cleaned:
                cursor.execute(cleaned)
                statements_executed += 1

        print(f"Schema execution complete. Total statements executed: {statements_executed}")
        cursor.close()
        conn.close()
        return True
    except Error as err:
        print(f"Database initialization failed [Errno {err.errno}]: {err.msg}")
        return False


if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)
