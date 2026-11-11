# Intelligent Course Recommendation System (ICRS)

An enterprise-grade, explainable Knowledge-Based Expert System developed with **Python Flask**, **MySQL**, **HTML5**, **CSS3**, and **Bootstrap 5**.

The system applies classical and non-monotonic Artificial Intelligence techniques—including **Knowledge Representation**, **Knowledge Base**, **Rule-Based Production Systems**, **Default Reasoning**, **Forward Chaining (RETE-style Match-Resolve-Act cycle)**, and **Multi-Factor Weighted Scoring**—to deliver personalized, transparent, and academically sound course recommendations to university students.

---

## 🎯 Problem Statement

In modern higher education institutions, undergraduate students face an increasingly complex array of elective courses, technical specializations, and interdependent prerequisites. Academic advising typically encounters significant challenges:
1. **Curriculum Complexity & Prerequisite Violations**: Students frequently select advanced electives without satisfying foundational prerequisite courses, resulting in course drops or academic failure.
2. **Misalignment with Career Trajectories**: Students often enroll in electives that fail to develop the competencies demanded by their desired industry careers (e.g., Data Science, Cloud Architecture, Cybersecurity).
3. **Incomplete Student Information**: Traditional advisory systems halt or fail when students have not yet finalized their career plans or specific interests.
4. **Lack of Explainability**: Modern black-box recommendation algorithms (e.g., collaborative filtering or deep learning) cannot provide pedagogical justification or rule citations, eroding institutional trust.

The **Intelligent Course Recommendation System** solves this by formalizing academic regulations, domain ontologies, and career pathways into an explicit Knowledge Base. It employs rule-based and default reasoning to handle complete and incomplete student profiles while providing fully auditable, explainable advice.

---

## 🧠 Core AI Concepts & Techniques

1. **Knowledge Representation (KR)**: Structured modeling of university courses, domain interest taxonomies, career goal pathways, and directed acyclic graph (DAG) prerequisite dependencies.
2. **Knowledge Base (KB)**: Centralized fact repository with real-time MySQL synchronization and semantic consistency validation (detecting orphan nodes and invalid CGPA thresholds).
3. **Production Rule System**: Declarative condition-action rules ($IF \dots THEN \dots$) with typed comparison predicates, logical `AND`/`OR` grouping, and priority salience.
4. **Non-Monotonic Default Reasoning**: Heuristic fallback rules (DR01–DR05) that generate safe provisional advice in the face of missing career goals or interests, supported by epistemic assumption tracking and belief revision.
5. **Forward Chaining Inference**: Deductive working-memory inference executing the classical *Match-Resolve-Act* cycle with refraction mechanisms to prevent infinite execution loops.
6. **Multi-Factor Multi-Criteria Scoring (MCDA)**: Mathematical suitability scoring combining Interest Match ($40\%$), Career Alignment ($35\%$), Academic CGPA Clearance ($15\%$), and Prerequisite Completion ($10\%$).
7. **Explainable AI (XAI)**: Generation of transparent, human-readable explanations citing specific rule matches, percentage breakdowns, and explicit assumption warnings.

---

## 🌟 Key Features

### 1. Artificial Intelligence Core (`ai_engine/`)
- **Knowledge Representation & Base (`knowledge_base.py`, `knowledge_repository.py`)**: Models relational and graph facts: courses, domain interests, career pathways, hard prerequisites, and eligibility criteria.
- **Knowledge Validator (`knowledge_validator.py`)**: Performs automated semantic sanity checks, detecting isolated courses, broken prerequisites, missing mappings, and invalid CGPA bounds.
- **Production Rule Engine (`rules.py`, `rule_evaluator.py`, `rule_manager.py`)**: Dynamic antecedent-consequent rules with AND/OR logic, nested condition trees, priority ordering, and strict validation.
- **Default Reasoning Engine (`default_rules.py`, `default_reasoning.py`, `assumption_manager.py`)**: Non-monotonic AI reasoning addressing incomplete student profiles (DR01–DR05) using epistemic statuses (`VERIFIED`, `ASSUMED_DEFAULT`, `UNKNOWN`) and belief revision.
- **Forward Chaining Engine (`forward_chaining.py`)**: Classical forward inference working memory loop with refraction, salience priority resolution, and derivation lineage tracking.
- **Scorer & Ranker (`recommendation_scorer.py`, `course_ranker.py`)**: Multi-factor scoring (Interest Match 40%, Career Alignment 35%, CGPA Clearance 15%, Prerequisite Factor 10%) and tiered categorization (*Highly Recommended*, *Recommended*, *Alternative Option*).
- **Explainable AI (XAI) (`explanation_generator.py`, `reasoning_logger.py`)**: Full transparency with natural-language justifications, rule citations, assumption disclaimers, and audit trails.

### 2. Student Experience
- **Secure Authentication**: Registration, bcrypt hashing, password validation, role-based access.
- **Student Profile Management**: Real-time CGPA tracking, semester/department details, career goal selection.
- **Interactive Domain Interests**: Multi-select tag manager for technical and domain interests.
- **Personalized Recommendations**: One-click AI evaluation with suitability breakdown, tier badges, and explainability cards.
- **Interactive Rule Testing Sandbox**: Allows students to test hypothetical CGPA, interests, and career goals against production rules with step-by-step reasoning logs.
- **Recommendation History**: Audit trail of past recommendations with timestamped snapshot inspection.

### 3. Administrator Experience
- **Executive Analytics Dashboard**: Real-time metrics on students, active courses, interest distributions, and recommendation volumes.
- **Student Record Management**: View enrolled students, inspect academic profiles, and toggle account access.
- **Course Catalog Management**: Full CRUD operations with code validation, difficulty levels, CGPA cutoffs, and prerequisite links.
- **Taxonomy Management**: Add and maintain domain interests and career goal definitions with student usage counts.
- **AI Rule Management**: Create, edit, toggle, and prioritize dynamic production rules.
- **Default Rule Toggles**: Administer non-monotonic fallback heuristics (DR01–DR05).
- **Knowledge Base Health Audit**: Live diagnostic suite detecting orphan nodes and inconsistencies.
- **Monitoring & Audit Reports**: System-wide inference audit log inspection and statistical reports.

---

## 🏗️ System Architecture

```text
Intelligent-Course-Recommendation/
├── ai_engine/                         # AI & Inference Subsystem
│   ├── __init__.py
│   ├── knowledge_base.py              # Knowledge Base interface & fact querying
│   ├── knowledge_repository.py        # MySQL knowledge extraction layer
│   ├── knowledge_validator.py         # Knowledge integrity and semantic audit
│   ├── rules.py                       # Production Rule definitions & operators
│   ├── rule_evaluator.py              # Predicate evaluator with logic trees
│   ├── rule_manager.py                # Database rule retrieval & priority sorting
│   ├── default_rules.py               # Fallback heuristics (DR01-DR05)
│   ├── default_reasoning.py           # Non-monotonic reasoning engine
│   ├── assumption_manager.py          # Epistemic tracker & belief revision
│   ├── forward_chaining.py            # Forward inference engine & refraction
│   ├── recommendation_scorer.py       # Multi-factor mathematical scoring
│   ├── course_ranker.py               # Tiered categorization & sorting
│   ├── explanation_generator.py       # Transparent natural-language XAI
│   ├── inference_engine.py            # Central orchestration pipeline
│   └── reasoning_logger.py            # Audit trail & structured logging
├── database/                          # Database connection & schema scripts
│   ├── db_connection.py               # Parameterized connection pool with retry
│   ├── schema.sql                     # Complete DDL tables & indexes
│   └── seed_data.sql                  # Comprehensive seed curriculum data
├── routes/                            # Modular Flask Blueprints
│   ├── __init__.py
│   ├── auth.py                        # Authentication & registration routes
│   ├── student.py                     # Student portal & recommendation routes
│   └── admin.py                       # Admin management & rule routes
├── static/                            # Static assets
│   ├── css/
│   │   ├── style.css                  # Custom styling & glassmorphism
│   │   └── dashboard.css              # Dashboard layout styling
│   └── js/
│       ├── main.js                    # Client-side UI enhancements
│       └── student_interests.js       # Dynamic interest management
├── templates/                         # Jinja2 Templates (Bootstrap 5)
│   ├── base.html                      # Root layout with responsive navbar
│   ├── student_dashboard.html         # Student portal overview
│   ├── student_recommendations.html   # Detailed recommendation display
│   ├── student_rule_testing.html      # AI Rule Testing sandbox
│   ├── student_interests.html         # Student interest selector
│   ├── student_academic_profile.html  # Student CGPA & profile form
│   ├── student_career_goal.html       # Career path selector
│   ├── student_history.html           # Historical recommendation log
│   ├── admin_dashboard.html           # Admin analytics dashboard
│   ├── admin_students.html            # Student records & status toggles
│   ├── admin_courses.html             # Course catalog & management
│   ├── admin_interests.html           # Interest taxonomy manager
│   ├── admin_career_goals.html        # Career goal taxonomy manager
│   ├── admin_rules.html               # Production rule management
│   ├── admin_default_rules.html       # Default rule administration
│   ├── admin_kb_audit.html            # Knowledge Base audit dashboard
│   ├── admin_reports.html             # Analytics & recommendation reports
│   └── ...                            # Auth, error, and profile templates
├── tests/                             # Comprehensive Automated Test Suite
│   ├── __init__.py
│   ├── conftest.py                    # Pytest configuration & fixtures
│   ├── test_auth.py                   # Authentication & RBAC tests
│   ├── test_student.py                # Student workflows & profile tests
│   ├── test_admin.py                  # Admin dashboard & management tests
│   ├── test_knowledge_base.py         # KB query & integrity tests
│   ├── test_rule_engine.py            # Rule condition & evaluator tests
│   ├── test_default_reasoning.py      # Non-monotonic DR01-DR05 tests
│   ├── test_forward_chaining.py       # Forward chaining & refraction tests
│   ├── test_inference_engine.py       # Complete inference pipeline tests
│   └── test_recommendations.py        # End-to-end recommendation tests
├── app.py                             # Flask Application Entry Point
├── config.py                          # App & Database Configuration
├── create_admin.py                    # CLI Utility to bootstrap admin account
├── run_tests.py                       # Automated test runner script
├── requirements.txt                   # Production dependencies
├── .env.example                       # Environment template
└── README.md                          # Project documentation
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.10+ / Flask 3.1.3 |
| **Database** | MySQL Server 8.0+ / `mysql-connector-python` |
| **Authentication & Security** | Werkzeug Security (pbkdf2:sha256), Flask Session, CSRF Protection |
| **AI & Inference Engine** | Knowledge Representation, Forward Chaining, Default Reasoning, Multi-Factor Scorer |
| **Frontend Framework** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3.3, Bootstrap Icons |
| **Testing & Quality Assurance** | `pytest 9.2.0`, `unittest` |

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- MySQL Server 8.0+ running locally or remotely
- Git

### 2. Clone Repository
```bash
git clone https://github.com/your-username/Intelligent-Course-Recommendation.git
cd Intelligent-Course-Recommendation
```

### 3. Create & Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Database Configuration
1. Open MySQL Command Line or MySQL Workbench.
2. Create the database:
   ```sql
   CREATE DATABASE IF NOT EXISTS intelligent_course_recommendation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Import the database schema and knowledge base seeds:
   ```bash
   mysql -u root -p intelligent_course_recommendation < database/schema.sql
   ```
4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
5. Edit `.env` with your MySQL database credentials:
   ```ini
   FLASK_APP=app.py
   FLASK_ENV=development
   FLASK_DEBUG=1
   SECRET_KEY=super-secret-development-key-change-in-production

   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=intelligent_course_recommendation
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   ```

### 6. Create Administrator User
Bootstrap the initial administrator account via the CLI tool:
```bash
python create_admin.py --username admin --email admin@university.edu --password "Admin@12345"
```

---

## 🚀 Running the Application

Start the local Flask development server:
```bash
python app.py
```
Open your web browser and navigate to:
```text
http://127.0.0.1:5000/
```

### Default Credentials
- **Admin Portal**:
  - URL: `http://127.0.0.1:5000/admin/login`
  - Email / Username: `admin@university.edu` or `admin`
  - Password: `Admin@12345` (or whichever password you configured in Step 6)
- **Student Portal**:
  - URL: `http://127.0.0.1:5000/login`
  - Register a new account or log in with an existing student account.

---

## 🧪 Automated Testing

The project includes an end-to-end automated test suite spanning 43 unit and integration tests across 9 test modules with a 100% pass rate.

### Run All Tests via Runner Script:
```bash
python run_tests.py
```

### Run Tests via Pytest Directly:
```bash
pytest -v tests/
```

### Test Coverage Breakdown:
| Test Module | Coverage Scope | Tests |
| :--- | :--- | :---: |
| `tests/test_auth.py` | Student & Admin login, registration, password hashing, RBAC | 5 / 5 |
| `tests/test_student.py` | Profile updates, CGPA validation, interests, career goals | 6 / 6 |
| `tests/test_admin.py` | Metrics, course CRUD, interest CRUD, career goal CRUD, rule toggles | 7 / 7 |
| `tests/test_knowledge_base.py` | Knowledge Base queries, prerequisites, semantic audit | 6 / 6 |
| `tests/test_rule_engine.py` | Condition parsing, AND/OR logic, predicate validation, rule prioritization | 4 / 4 |
| `tests/test_default_reasoning.py` | DR01-DR05 non-monotonic reasoning, epistemic tracking, retraction | 6 / 6 |
| `tests/test_forward_chaining.py` | Working memory, match-resolve-act cycle, salience, refraction loops | 3 / 3 |
| `tests/test_inference_engine.py` | Complete orchestration, scoring weights, ranking tiers, XAI explanations | 5 / 5 |
| `tests/test_recommendations.py` | End-to-end student recommendation lifecycle & DB persistence | 1 / 1 |
| **Total** | **Comprehensive System Validation** | **43 / 43 (100%)** |

---

## 🧠 AI Recommendation Workflow

```text
[ Student Profile ]
        │
        ├── CGPA, Department, Completed Courses
        ├── Domain Interests (e.g., AI, Web, Cyber)
        └── Career Goal (e.g., Data Scientist)
        │
        ▼
[ Knowledge Base Extraction ] ─── (Validates against MySQL Schema)
        │
        ▼
[ Completeness Check & Default Reasoning ]
        │
        ├─ Incomplete? ──► [ Default Rules DR01-DR05 ] ──► (Assumptions Logged)
        │
        ▼
[ Forward Chaining Inference Engine ]
        │
        ├── Evaluates Active Production Rules (Salience Priority)
        ├── Applies Refraction (Prevents Cycles)
        └── Asserts Derived Recommendation Facts
        │
        ▼
[ Hard Eligibility Filter ] ─── (Rejects CGPA < minimum_cgpa or Missing Prereqs)
        │
        ▼
[ Multi-Factor Suitability Scorer ]
        ├── Interest Match: 40%
        ├── Career Goal Alignment: 35%
        ├── Academic CGPA Clearance: 15%
        └── Prerequisite Completion: 10%
        │
        ▼
[ Course Ranker & Categorizer ]
        ├── Tier 1: Highly Recommended (Score ≥ 80%)
        ├── Tier 2: Recommended (Score 60% - 79%)
        └── Tier 3: Alternative Option (Score < 60%)
        │
        ▼
[ Explanation Generator (XAI) ] ─── (Cites matched rules, interest overlap, assumptions)
        │
        ▼
[ Presentation & Historical Persistence ]
```

---

## 🔒 Security Best Practices
- **Password Protection**: Passwords securely hashed with `werkzeug.security` (PBKDF2 with SHA-256 and salted hashes).
- **SQL Injection Prevention**: 100% of database interactions use parameterized queries (`%s`). Zero string concatenation or formatting in SQL.
- **Cross-Site Request Forgery (CSRF)**: Forms protected using Flask-WTF tokens.
- **Role-Based Access Control (RBAC)**: Strict decorators `@student_required` and `@admin_required` prevent horizontal and vertical privilege escalation.
- **Cookie & Session Security**: Sensitive payloads are decoupled from client session cookies and persisted directly in MySQL tables.

---

## 📄 License
This project is licensed under the MIT License.
