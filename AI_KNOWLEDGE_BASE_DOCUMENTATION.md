# AI Knowledge Base Architecture & Specification
## Intelligent Course Recommendation System — Phase 6 Documentation

---

### 1. What a Knowledge Base Is

In Knowledge-Based Artificial Intelligence (KBAI) and Expert Systems, a **Knowledge Base (KB)** is an organized collection of facts, domain ontologies, constraints, and relationships that capture expert human knowledge in a structured, machine-interpretable format. 

Unlike raw unstructured databases or statistical models that infer patterns implicitly from numerical weights, a Knowledge Base provides:
1. **Explicit Declarative Representation**: Domain concepts (e.g., courses, technical interests, career pathways, prerequisites) are represented explicitly as formal entities with well-defined attributes.
2. **Deterministic Ground Truth**: Represents the verified curriculum prerequisites, minimum academic standing thresholds, and career competencies without probabilistic hallucinations.
3. **Decoupled Architecture**: Completely decouples domain knowledge from the reasoning algorithms (the Inference Engine implemented in later phases), allowing curriculum architects and administrators to update course offerings and requirements dynamically without rewriting procedural logic.

---

### 2. Knowledge Representation

The AI Knowledge Base models domain knowledge as **Structured Course Facts** using the `CourseKnowledgeFact` data structure in [`ai_engine/knowledge_base.py`](file:///z:/Intelligent-Course-Recommendation/ai_engine/knowledge_base.py).

#### Formal Fact Specification
Each course fact represents a grounded ontological node:
```json
{
    "course_id": 1,
    "course_code": "CS-401",
    "course_name": "Machine Learning",
    "description": "Fundamentals of supervised, unsupervised, and reinforcement learning with regression, classification, clustering, and model validation.",
    "minimum_cgpa": 2.50,
    "difficulty_level": "Advanced",
    "prerequisites_text": "Python, Linear Algebra",
    "prerequisite_courses": [],
    "interests": [
        "Python Programming",
        "Mathematics",
        "Data Science",
        "Machine Learning",
        "Artificial Intelligence"
    ],
    "career_goals": [
        "Machine Learning Engineer",
        "Data Scientist",
        "AI Engineer"
    ],
    "is_active": true
}
```

```
+-----------------------------------------------------------------------------------+
|                            CourseKnowledgeFact Node                               |
+-----------------------------------------------------------------------------------+
|  - course_id: int                                                                 |
|  - course_code: str (e.g., 'CS-401')                                               |
|  - course_name: str                                                               |
|  - minimum_cgpa: float (academic eligibility bound)                               |
|  - difficulty_level: {'Beginner', 'Intermediate', 'Advanced'}                    |
|  - prerequisites_text: str (human-readable prerequisite statement)                |
|  - is_active: bool                                                                |
+------------------------------------+----------------------------------------------+
                                     |
         +---------------------------+---------------------------+
         |                           |                           |
         v                           v                           v
+------------------+       +-------------------+       +--------------------+
|  Interests [M:N] |       | Career Goals [M:N]|       | Prereq Course [M:N]|
| - Machine Learn. |       | - ML Engineer     |       | - CS-401 (for DL)  |
| - Python Prog.   |       | - Data Scientist  |       | - CS-402 (for CV)  |
| - Data Science   |       | - AI Engineer     |       |                    |
+------------------+       +-------------------+       +--------------------+
```

---

### 3. Knowledge Repository Architecture

The `ai_engine` package is organized into four modular components adhering to the Single Responsibility Principle:

```
ai_engine/
│
├── __init__.py                # Package interface exposing KB classes
├── knowledge_base.py          # High-level declarative API & CourseKnowledgeFact model
├── knowledge_repository.py    # Low-level parameterized MySQL data access layer
├── knowledge_validator.py     # Structural anomaly detection & DB integrity auditor
└── knowledge_loader.py        # Canonical knowledge seeder & idempotent synchronizer
```

- **`KnowledgeRepository`**: Handles low-level database communication using parameterized SQL queries (`%s`). Retrieves raw tuples, executes relational queries for courses, interests, career goals, and prerequisites, and manages relationship mutations.
- **`KnowledgeBase`**: Serves as the primary public interface. Employs lazy in-memory caching (`reload()` / cache invalidation), transforms raw records into `CourseKnowledgeFact` models, and provides semantic query methods (by interest, career goal, CGPA, or prerequisite).
- **`KnowledgeValidator`**: Audits course facts and database integrity. Detects missing fields, invalid CGPA values, cyclic prerequisites, self-referential dependencies, and orphan junction records.
- **`KnowledgeLoader`**: Idempotently seeds the 10 canonical elective courses, 10 core domain interests, 8 career goals, and their relational mappings into MySQL without creating duplicate rows.

---

### 4. Database Schema & Relational Design

The Knowledge Base leverages two relational junction tables to establish structured dependencies:

```
                +---------------------+
                |       courses       |
                +---------------------+
                | id (PK)             |
                | course_code (UQ)    |
                | course_name         |
                | minimum_cgpa        |
                | difficulty_level    |
                +----------+----------+
                           |
        +------------------+------------------+------------------+
        |                                     |                  |
        v                                     v                  v
+-----------------------+           +--------------------+     +-----------------------+
|   course_interests    |           |course_career_goals |     | course_prerequisites  |
+-----------------------+           +--------------------+     +-----------------------+
| id (PK)               |           | id (PK)            |     | id (PK)               |
| course_id (FK)        |           | course_id (FK)     |     | course_id (FK)        |
| interest_id (FK)      |           | career_goal_id (FK)|     | prereq_course_id (FK) |
| UNIQUE(course,interest|           | UNIQUE(course,goal)|     | UNIQUE(course,prereq) |
+-----------+-----------+           +---------+----------+     +-----------+-----------+
            |                                 |                            |
            v                                 v                            |
+-----------------------+           +--------------------+                 |
|       interests       |           |    career_goals    |                 |
+-----------------------+           +--------------------+                 |
| id (PK)               |           | id (PK)            |                 |
| interest_name (UQ)    |           | goal_name (UQ)     |                 |
+-----------------------+           +--------------------+                 |
            ^                                                              v
            +--------------------------------------------------------------+
```

1. **`course_career_goals`**:
   - `id`: `INT AUTO_INCREMENT PRIMARY KEY`
   - `course_id`: `INT NOT NULL, FOREIGN KEY REFERENCES courses(id) ON DELETE CASCADE`
   - `career_goal_id`: `INT NOT NULL, FOREIGN KEY REFERENCES career_goals(id) ON DELETE CASCADE`
   - `UNIQUE KEY uq_course_career_goal (course_id, career_goal_id)`
   - Indexes on `course_id` and `career_goal_id`.
2. **`course_prerequisites`**:
   - `id`: `INT AUTO_INCREMENT PRIMARY KEY`
   - `course_id`: `INT NOT NULL, FOREIGN KEY REFERENCES courses(id) ON DELETE CASCADE`
   - `prerequisite_course_id`: `INT NOT NULL, FOREIGN KEY REFERENCES courses(id) ON DELETE CASCADE`
   - `UNIQUE KEY uq_course_prerequisite (course_id, prerequisite_course_id)`
   - Indexes on `course_id` and `prerequisite_course_id`.

---

### 5. Canonical Knowledge Facts

The Knowledge Base defines 10 core elective subjects with precise prerequisite and career alignments:

| Code | Course Title | Difficulty | Min CGPA | Core Prerequisites | Target Career Pathways | Mapped Domain Interests |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **CS-401** | Machine Learning | Advanced | 2.50 | Python, Linear Algebra | Machine Learning Engineer, Data Scientist, AI Engineer | Python Programming, Mathematics, Data Science, Machine Learning, Artificial Intelligence |
| **CS-402** | Artificial Intelligence | Intermediate | 2.00 | Discrete Math, Data Structures | AI Engineer, Machine Learning Engineer, Software Developer | Python Programming, Mathematics, Artificial Intelligence, Machine Learning |
| **CS-403** | Big Data Analytics | Advanced | 2.50 | Database Systems | Data Engineer, Data Scientist, Cloud Engineer | Java Programming, Python Programming, Data Science, Cloud Technology |
| **CS-404** | Cloud Computing | Intermediate | 2.00 | OS, Computer Networks | Cloud Engineer, Software Developer | Cloud Technology, Networking, Web Development |
| **CS-405** | Cyber Security | Intermediate | 2.00 | Computer Networks | Cyber Security Analyst, Software Developer | Cyber Security, Networking |
| **CS-406** | Deep Learning | Advanced | 3.00 | CS-401 (Machine Learning) | AI Engineer, ML Engineer, Computer Vision Engineer | Python Programming, Mathematics, Machine Learning, Artificial Intelligence |
| **CS-407** | Data Mining | Intermediate | 2.20 | Database Systems | Data Scientist, Data Engineer | Data Science, Python Programming, Mathematics |
| **CS-408** | Natural Language Processing | Advanced | 2.75 | CS-401 (Machine Learning) | AI Engineer, ML Engineer, Data Scientist | Python Programming, Machine Learning, Artificial Intelligence, Data Science |
| **CS-409** | Computer Vision | Advanced | 2.80 | CS-401, CS-402 | Computer Vision Engineer, AI Engineer, ML Engineer | Python Programming, Mathematics, Artificial Intelligence, Machine Learning |
| **CS-410** | Internet of Things | Beginner | 2.00 | CS-404 (Cloud Computing) | Cloud Engineer, Software Developer | Networking, Cloud Technology, Python Programming |

---

### 6. Retrieval Functions API

The `KnowledgeBase` class provides high-level query methods for the application:

```python
from ai_engine import KnowledgeBase

kb = KnowledgeBase()

# 1. Retrieve all active courses
active_courses = kb.get_all_courses(active_only=True)

# 2. Retrieve course by unique code or ID
course = kb.get_course_by_code("CS-401")
print(course.course_name, course.minimum_cgpa, course.interests)

# 3. Retrieve courses matching a student's domain interest
ml_courses = kb.get_courses_by_interest("Machine Learning")

# 4. Retrieve courses aligned with a career goal
ds_courses = kb.get_courses_by_career_goal("Data Scientist")

# 5. Retrieve courses where student satisfies minimum CGPA
eligible_courses = kb.get_courses_by_cgpa(student_cgpa=3.25)

# 6. Retrieve prerequisite dependencies (structured and text)
prereqs = kb.get_course_prerequisites("CS-406")
# Output: {'course': {...}, 'prerequisites_text': 'Machine Learning', 'prerequisite_courses': [{'course_code': 'CS-401', ...}]}

# 7. Complete Knowledge Base export
complete_kb = kb.get_complete_knowledge_base()

# 8. Run structural and ontological validation audit
audit_report = kb.validate_knowledge_base()
```

---

### 7. Knowledge Validation Engine

The `KnowledgeValidator` verifies the integrity of course facts and relational mappings:
- **Bounds Checking**: Validates that minimum CGPA lies within $[0.00, 10.00]$ and difficulty level is one of `{'Beginner', 'Intermediate', 'Advanced'}`.
- **Relational Integrity**: Detects orphan rows in `course_interests`, `course_career_goals`, or `course_prerequisites` where parent records do not exist.
- **Dependency Anomaly Checks**:
  - Rejects self-referencing prerequisites (`course_id == prerequisite_course_id`).
  - Detects 2-node cyclic prerequisites ($A \to B$ and $B \to A$).
- **Audit Reporting**: Returns a structured report with overall status (`HEALTHY`, `WARNING`, `CRITICAL`), valid courses count, error diagnostics, and administrative recommendations.

---

### 8. Admin & Student Integration

1. **Admin Portal Integration**:
   - [`/admin/knowledge-base`](http://127.0.0.1:5000/admin/knowledge-base): Displays the unified knowledge matrix including course codes, titles, minimum CGPAs, difficulty ratings, prerequisites, domain interests, and career pathways.
   - **Audit Knowledge Base Button**: Administrators can trigger real-time validation audits (`/admin/knowledge-base/audit`) to inspect system health and verify consistency.
   - **Course Form**: Enables administrators to assign technical interests, target career goals, and structured course prerequisite dependencies directly from the UI.
2. **Student Portal Integration**:
   - [`/student/courses`](http://127.0.0.1:5000/student/courses): Uses `KnowledgeBase.get_all_courses(active_only=True)` to present elective course offerings, displaying prerequisite courses, academic requirements, and aligned career pathways with responsive badge controls.

---

### 9. Test Verification Results

All 12 automated tests in [`test_knowledge_base.py`](file:///z:/Intelligent-Course-Recommendation/test_knowledge_base.py) passed:

```
test_1_kb_initialization ................................................. PASS
test_2_course_retrieval .................................................. PASS
test_3_interest_retrieval ................................................ PASS
test_4_career_goal_retrieval ............................................. PASS
test_5_course_interest_mapping ........................................... PASS
test_6_course_career_mapping ............................................. PASS
test_7_cgpa_eligibility_retrieval ........................................ PASS
test_8_prerequisite_retrieval ............................................ PASS
test_9_invalid_knowledge_detection ....................................... PASS
test_10_duplicate_relationship_prevention ................................ PASS
test_11_self_prerequisite_prevention ..................................... PASS
test_12_database_connection_resilience ................................... PASS

Overall Test Status: 12 / 12 PASSED (100% SUCCESS)
```

#### Regression Testing Status:
- `test_admin_dashboard.py`: **13 / 13 PASSED** (100%)
- `test_student_dashboard.py`: **10 / 10 PASSED** (100%)
- `test_auth.py`: **14 / 14 PASSED** (100%)
- `database/test_db.py`: **6 / 6 PASSED** (100%)
