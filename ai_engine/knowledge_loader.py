"""
Knowledge Loader Module
Initializes, seeds, and synchronizes the canonical AI Knowledge Base in MySQL.
Ensures zero duplicates using transactional idempotency and safe foreign key resolution.
"""

from typing import Dict, Any, List
from database.db_connection import get_db_cursor
from mysql.connector import Error


# =============================================================================
# Canonical Domain Knowledge Definitions
# =============================================================================

CANONICAL_INTERESTS: List[str] = [
    "Python Programming",
    "Java Programming",
    "Mathematics",
    "Data Science",
    "Networking",
    "Artificial Intelligence",
    "Machine Learning",
    "Cloud Technology",
    "Cyber Security",
    "Web Development"
]

CANONICAL_CAREER_GOALS: List[Dict[str, str]] = [
    {
        "goal_name": "Data Scientist",
        "description": "Applies statistical modeling, exploratory data analysis, and predictive machine learning to uncover insights."
    },
    {
        "goal_name": "AI Engineer",
        "description": "Architects, trains, and operationalizes machine learning systems, cognitive models, and intelligent agents."
    },
    {
        "goal_name": "Machine Learning Engineer",
        "description": "Designs scalable predictive pipelines, feature engineering workflows, and high-performance neural model inference."
    },
    {
        "goal_name": "Software Developer",
        "description": "Builds robust, maintainable full-stack software applications, services, and backend system architectures."
    },
    {
        "goal_name": "Cloud Engineer",
        "description": "Provisions, deploys, scales, and monitors enterprise cloud infrastructure, microservices, and distributed pipelines."
    },
    {
        "goal_name": "Cyber Security Analyst",
        "description": "Monitors network vectors, implements cryptographic protocols, conducts vulnerability assessments, and defends systems."
    },
    {
        "goal_name": "Data Engineer",
        "description": "Constructs distributed data architectures, ETL/ELT streaming pipelines, data warehouses, and big data clusters."
    },
    {
        "goal_name": "Computer Vision Engineer",
        "description": "Develops image segmentation, object detection, facial recognition, and spatial perception algorithms."
    }
]

CANONICAL_COURSES: List[Dict[str, Any]] = [
    {
        "course_code": "CS-401",
        "course_name": "Machine Learning",
        "description": "Fundamentals of supervised, unsupervised, and reinforcement learning with regression, classification, clustering, and model validation.",
        "minimum_cgpa": 2.50,
        "difficulty_level": "Advanced",
        "prerequisites": "Python, Linear Algebra",
        "career_scope": "Machine Learning Engineer, Data Scientist, AI Engineer",
        "is_active": True,
        "interests": ["Python Programming", "Mathematics", "Data Science", "Machine Learning", "Artificial Intelligence"],
        "career_goals": ["Machine Learning Engineer", "Data Scientist", "AI Engineer"],
        "prerequisite_codes": []
    },
    {
        "course_code": "CS-402",
        "course_name": "Artificial Intelligence",
        "description": "Introduction to cognitive systems, knowledge representation, heuristic search, logic inference, and expert systems.",
        "minimum_cgpa": 2.00,
        "difficulty_level": "Intermediate",
        "prerequisites": "Discrete Mathematics, Data Structures",
        "career_scope": "AI Engineer, Machine Learning Engineer, Software Developer",
        "is_active": True,
        "interests": ["Python Programming", "Mathematics", "Artificial Intelligence", "Machine Learning"],
        "career_goals": ["AI Engineer", "Machine Learning Engineer", "Software Developer"],
        "prerequisite_codes": []
    },
    {
        "course_code": "CS-403",
        "course_name": "Big Data Analytics",
        "description": "Distributed computing with Apache Spark, Hadoop MapReduce, scalable stream processing, and distributed NoSQL databases.",
        "minimum_cgpa": 2.50,
        "difficulty_level": "Advanced",
        "prerequisites": "Database Systems",
        "career_scope": "Data Engineer, Data Scientist, Cloud Engineer",
        "is_active": True,
        "interests": ["Java Programming", "Python Programming", "Data Science", "Cloud Technology"],
        "career_goals": ["Data Engineer", "Data Scientist", "Cloud Engineer"],
        "prerequisite_codes": []
    },
    {
        "course_code": "CS-404",
        "course_name": "Cloud Computing",
        "description": "Cloud service models (IaaS, PaaS, SaaS), virtualization, serverless compute, containerization with Docker/Kubernetes, and DevOps.",
        "minimum_cgpa": 2.00,
        "difficulty_level": "Intermediate",
        "prerequisites": "Operating Systems, Computer Networks",
        "career_scope": "Cloud Engineer, Software Developer",
        "is_active": True,
        "interests": ["Cloud Technology", "Networking", "Web Development"],
        "career_goals": ["Cloud Engineer", "Software Developer"],
        "prerequisite_codes": []
    },
    {
        "course_code": "CS-405",
        "course_name": "Cyber Security",
        "description": "Network defense principles, symmetric/asymmetric cryptography, threat analysis, authentication mechanisms, and penetration testing.",
        "minimum_cgpa": 2.00,
        "difficulty_level": "Intermediate",
        "prerequisites": "Computer Networks",
        "career_scope": "Cyber Security Analyst, Software Developer",
        "is_active": True,
        "interests": ["Cyber Security", "Networking"],
        "career_goals": ["Cyber Security Analyst", "Software Developer"],
        "prerequisite_codes": []
    },
    {
        "course_code": "CS-406",
        "course_name": "Deep Learning",
        "description": "Deep neural networks, backpropagation, convolutional networks (CNNs), recurrent networks (RNNs/LSTMs), transformers, and GANs.",
        "minimum_cgpa": 3.00,
        "difficulty_level": "Advanced",
        "prerequisites": "Machine Learning",
        "career_scope": "AI Engineer, Machine Learning Engineer, Computer Vision Engineer",
        "is_active": True,
        "interests": ["Python Programming", "Mathematics", "Machine Learning", "Artificial Intelligence"],
        "career_goals": ["AI Engineer", "Machine Learning Engineer", "Computer Vision Engineer"],
        "prerequisite_codes": ["CS-401"]
    },
    {
        "course_code": "CS-407",
        "course_name": "Data Mining",
        "description": "Techniques for discovering hidden patterns, frequent itemset mining, association rules, anomaly detection, and data warehouse modeling.",
        "minimum_cgpa": 2.20,
        "difficulty_level": "Intermediate",
        "prerequisites": "Database Systems",
        "career_scope": "Data Scientist, Data Engineer",
        "is_active": True,
        "interests": ["Data Science", "Python Programming", "Mathematics"],
        "career_goals": ["Data Scientist", "Data Engineer"],
        "prerequisite_codes": []
    },
    {
        "course_code": "CS-408",
        "course_name": "Natural Language Processing",
        "description": "Computational linguistics, text tokenization, n-grams, word embeddings, sequence-to-sequence architectures, and large language models.",
        "minimum_cgpa": 2.75,
        "difficulty_level": "Advanced",
        "prerequisites": "Machine Learning",
        "career_scope": "AI Engineer, Machine Learning Engineer, Data Scientist",
        "is_active": True,
        "interests": ["Python Programming", "Machine Learning", "Artificial Intelligence", "Data Science"],
        "career_goals": ["AI Engineer", "Machine Learning Engineer", "Data Scientist"],
        "prerequisite_codes": ["CS-401"]
    },
    {
        "course_code": "CS-409",
        "course_name": "Computer Vision",
        "description": "Digital image representation, edge detection, feature extraction, object localization, image segmentation, and visual transformers.",
        "minimum_cgpa": 2.80,
        "difficulty_level": "Advanced",
        "prerequisites": "Machine Learning, Artificial Intelligence",
        "career_scope": "Computer Vision Engineer, AI Engineer, Machine Learning Engineer",
        "is_active": True,
        "interests": ["Python Programming", "Mathematics", "Artificial Intelligence", "Machine Learning"],
        "career_goals": ["Computer Vision Engineer", "AI Engineer", "Machine Learning Engineer"],
        "prerequisite_codes": ["CS-401", "CS-402"]
    },
    {
        "course_code": "CS-410",
        "course_name": "Internet of Things",
        "description": "Microcontroller programming, sensor telemetry, edge computing gateways, wireless protocols (MQTT, CoAP), and cloud IoT platforms.",
        "minimum_cgpa": 2.00,
        "difficulty_level": "Beginner",
        "prerequisites": "Computer Networks",
        "career_scope": "Cloud Engineer, Software Developer",
        "is_active": True,
        "interests": ["Networking", "Cloud Technology", "Python Programming"],
        "career_goals": ["Cloud Engineer", "Software Developer"],
        "prerequisite_codes": ["CS-404"]
    }
]


class KnowledgeLoader:
    """Manages transactional loading, updating, and seeding of AI domain knowledge."""

    @classmethod
    def load_canonical_knowledge(cls, force_refresh_mappings: bool = False) -> Dict[str, int]:
        """
        Idempotently inserts or updates canonical courses, interests, career goals,
        and their interrelationships into MySQL.
        """
        stats = {
            "interests_added": 0,
            "career_goals_added": 0,
            "courses_added": 0,
            "courses_updated": 0,
            "interests_linked": 0,
            "career_goals_linked": 0,
            "prerequisites_linked": 0
        }

        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            # 1. Load Domain Interests
            for interest_name in CANONICAL_INTERESTS:
                cursor.execute("SELECT id FROM interests WHERE LOWER(interest_name) = LOWER(%s)", (interest_name,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO interests (interest_name) VALUES (%s)", (interest_name,))
                    stats["interests_added"] += 1

            # 2. Load Career Goals
            for goal in CANONICAL_CAREER_GOALS:
                cursor.execute("SELECT id FROM career_goals WHERE LOWER(goal_name) = LOWER(%s)", (goal["goal_name"],))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO career_goals (goal_name, description)
                        VALUES (%s, %s)
                    """, (goal["goal_name"], goal["description"]))
                    stats["career_goals_added"] += 1

            # 3. Load Courses
            for course in CANONICAL_COURSES:
                cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course["course_code"],))
                existing = cursor.fetchone()

                if existing:
                    # Update properties
                    cursor.execute("""
                        UPDATE courses
                        SET course_name = %s, description = %s, minimum_cgpa = %s,
                            difficulty_level = %s, career_scope = %s,
                            prerequisites = %s, is_active = %s
                        WHERE id = %s
                    """, (
                        course["course_name"],
                        course["description"],
                        course["minimum_cgpa"],
                        course["difficulty_level"],
                        course["career_scope"],
                        course["prerequisites"],
                        course["is_active"],
                        existing["id"]
                    ))
                    stats["courses_updated"] += 1
                else:
                    cursor.execute("""
                        INSERT INTO courses (
                            course_code, course_name, description, minimum_cgpa,
                            difficulty_level, career_scope, prerequisites, is_active
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        course["course_code"],
                        course["course_name"],
                        course["description"],
                        course["minimum_cgpa"],
                        course["difficulty_level"],
                        course["career_scope"],
                        course["prerequisites"],
                        course["is_active"]
                    ))
                    stats["courses_added"] += 1

            # 4. Link Course Interests
            for course in CANONICAL_COURSES:
                cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course["course_code"],))
                course_row = cursor.fetchone()
                if not course_row:
                    continue
                cid = course_row["id"]

                for int_name in course["interests"]:
                    cursor.execute("SELECT id FROM interests WHERE LOWER(interest_name) = LOWER(%s)", (int_name,))
                    i_row = cursor.fetchone()
                    if i_row:
                        cursor.execute("""
                            INSERT IGNORE INTO course_interests (course_id, interest_id)
                            VALUES (%s, %s)
                        """, (cid, i_row["id"]))
                        if cursor.rowcount > 0:
                            stats["interests_linked"] += 1

            # 5. Link Course Career Goals
            for course in CANONICAL_COURSES:
                cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course["course_code"],))
                course_row = cursor.fetchone()
                if not course_row:
                    continue
                cid = course_row["id"]

                for goal_name in course["career_goals"]:
                    cursor.execute("SELECT id FROM career_goals WHERE LOWER(goal_name) = LOWER(%s)", (goal_name,))
                    g_row = cursor.fetchone()
                    if g_row:
                        cursor.execute("""
                            INSERT IGNORE INTO course_career_goals (course_id, career_goal_id)
                            VALUES (%s, %s)
                        """, (cid, g_row["id"]))
                        if cursor.rowcount > 0:
                            stats["career_goals_linked"] += 1

            # 6. Link Structured Course Prerequisites
            for course in CANONICAL_COURSES:
                cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course["course_code"],))
                course_row = cursor.fetchone()
                if not course_row:
                    continue
                cid = course_row["id"]

                for prereq_code in course["prerequisite_codes"]:
                    cursor.execute("SELECT id FROM courses WHERE course_code = %s", (prereq_code,))
                    p_row = cursor.fetchone()
                    if p_row and p_row["id"] != cid:
                        cursor.execute("""
                            INSERT IGNORE INTO course_prerequisites (course_id, prerequisite_course_id)
                            VALUES (%s, %s)
                        """, (cid, p_row["id"]))
                        if cursor.rowcount > 0:
                            stats["prerequisites_linked"] += 1

        return stats
