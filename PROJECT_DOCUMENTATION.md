# Intelligent Course Recommendation System (ICRS)
## Comprehensive Technical Architecture & Engineering Documentation

---

## 1. Executive Summary & Project Purpose

The **Intelligent Course Recommendation System (ICRS)** is an AI-powered Knowledge-Based Expert System engineered to assist undergraduate university students in curating optimal, academically viable course trajectories aligned with their career ambitions, domain interests, and historical academic performance.

Higher education curricula often present complex prerequisite dependencies, diverse elective tracks, and variable minimum academic thresholds. Traditional academic advising relies on static handbooks or manual faculty counseling, which can lead to suboptimal elective selection, prerequisite violations, and credit delays. ICRS resolves this challenge by formalizing academic rules, domain relationships, and career pathways into an explicit **Knowledge Base** and orchestrating an **Inference Engine** that executes forward-chaining deduction, non-monotonic default reasoning, and multi-factor suitability scoring.

---

## 2. Academic & Theoretical Foundations

### 2.1 Knowledge Engineering in Higher Education
Knowledge Engineering is the discipline of capturing human domain expertise, formalizing it into explicit data structures, and reasoning over it programmatically. In ICRS, academic guidelines (e.g., "Advanced Machine Learning requires Data Structures and a minimum CGPA of 3.00") are modeled not as hardcoded conditional branches in procedural code, but as declarative production rules stored in a relational knowledge repository.

### 2.2 Classical Rule-Based Production Systems
Production systems operate on a tripartite architecture:
1. **Working Memory (Facts)**: The dynamic collection of verified ground truths representing the student's current state (CGPA, completed courses, active domain interests, declared career goals).
2. **Production Memory (Rules)**: Declarative condition-action pairs of the form:
   $$\text{IF } P_1 \wedge P_2 \wedge \dots \wedge P_n \implies \text{THEN } A$$
3. **Inference Engine**: The control mechanism that matches facts against rule conditions, resolves conflicts using rule salience (priority), and fires actions to assert new facts into working memory.

### 2.3 Non-Monotonic Default Reasoning
In classical monotonic logic, adding new information can never invalidate previously established conclusions. However, real-world academic advising frequently encounters incomplete student information (e.g., a first-year student who has not yet chosen a career goal or selected elective interests). 

ICRS implements default reasoning through non-monotonic rules (DR01–DR05), allowing the system to postulate provisional assumptions while explicitly tracking their epistemic status (`ASSUMED_DEFAULT`). If the student later provides verified facts, the system performs belief revision, withdrawing default assumptions and re-evaluating recommendations.

---

## 3. Technology Stack & Component Architecture

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Presentation Layer** | HTML5, CSS3, JavaScript, Bootstrap 5.3.3 | Responsive UI with custom dashboards, glassmorphism badges, and modal editors. |
| **Application Layer** | Python 3.10+ & Flask 3.1.3 | Modular MVC pattern utilizing Flask Blueprints (`auth_bp`, `student_bp`, `admin_bp`). |
| **Inference & AI Core** | Custom Python AI Engine (`ai_engine/`) | Decoupled knowledge repository, forward chaining engine, and multi-factor ranker. |
| **Data Persistence** | MySQL 8.0+ / `mysql-connector-python` | Relational 3NF database schema with foreign keys, cascading constraints, and index optimization. |
| **Security & Session** | Werkzeug Security, Flask-WTF | PBKDF2:SHA256 password hashing, CSRF protection, and role-based access decorators. |

---

## 4. Database Schema & Relational Modeling

The database schema `intelligent_course_recommendation` consists of 11 relational tables organized in Third Normal Form (3NF):

### 4.1 Core Entity Tables
1. **`users`**: Core authentication entity storing `id`, `username`, `email`, `password_hash`, `role` (`'student'` or `'admin'`), `is_active`, and audit timestamps.
2. **`student_profiles`**: One-to-one extension of `users` for students, recording `roll_number`, `department`, `semester`, `cgpa`, and foreign key reference to `career_goals(id)`.
3. **`courses`**: Catalog of university offerings containing `course_code`, `course_name`, `description`, `credits`, `minimum_cgpa`, `difficulty_level`, `career_scope`, `prerequisites`, and `is_active`.
4. **`interests`**: Standardized domain interest taxonomy (e.g., Artificial Intelligence, Cybersecurity, Web Development).
5. **`career_goals`**: Standardized vocational targets (e.g., Data Scientist, Cloud Architect, Security Analyst).

### 4.2 Relational & Associative Tables
6. **`student_interests`**: Many-to-many junction mapping `student_id` to `interest_id`.
7. **`course_interests`**: Many-to-many junction associating courses with applicable interest domains.
8. **`course_career_goals`**: Many-to-many junction linking courses with career pathways.
9. **`course_prerequisites`**: Directed graph edges modeling prerequisite dependencies (`course_id` $\rightarrow$ `prerequisite_course_id`).

### 4.3 AI & Knowledge Tables
10. **`knowledge_rules`**: Declarative production rules with `rule_name`, `condition_json` (antecedent specification), `recommendation_course_id` (consequent course), `priority`, and `is_active`.
11. **`default_rules`**: Non-monotonic fallback heuristics (`DR01` through `DR05`) with configurable activation status.
12. **`recommendation_history`**: Audit trail capturing timestamped recommendation runs, recommended courses, suitability scores, ranking tiers, and explainability summaries.

---

## 5. AI Engine Architecture (`ai_engine/`)

The AI engine is structured into decoupled modules:

```text
ai_engine/
├── knowledge_base.py          # Unified knowledge base interface
├── knowledge_repository.py    # Raw data extraction from MySQL
├── knowledge_validator.py     # Structural & semantic sanity checks
├── rules.py                   # Rule class definitions & condition operators
├── rule_evaluator.py          # AST condition evaluation engine
├── rule_manager.py            # Rule lifecycle, DB sync, & priority ordering
├── default_rules.py           # Fallback heuristic definitions (DR01-DR05)
├── default_reasoning.py       # Incomplete information handler
├── assumption_manager.py      # Epistemic status tracking & belief revision
├── forward_chaining.py        # RETE-style Match-Resolve-Act cycle
├── recommendation_scorer.py   # Multi-factor mathematical scoring
├── course_ranker.py           # Categorization into ranking tiers
├── explanation_generator.py   # Natural-language XAI explanations
├── inference_engine.py        # Orchestration pipeline
└── reasoning_logger.py        # Structured reasoning logs & audit trail
```

---

## 6. End-to-End Recommendation Lifecycle

1. **Extraction**: `KnowledgeRepository` extracts active courses, domain mappings, prerequisites, and production rules from MySQL.
2. **Fact Assembly**: Student profile data (CGPA, interests, career goal, completed courses) is assembled into initial working memory.
3. **Default Reasoning Assessment**: If key attributes are missing, `DefaultReasoningEngine` evaluates applicable default rules (DR01–DR05). Safe fallbacks are asserted and recorded by `AssumptionManager`.
4. **Forward Chaining Execution**: `ForwardChainingEngine` matches active production rules against working memory facts. Conflicts are resolved via rule priority. Derived course recommendations are asserted.
5. **Hard Eligibility Filtering**: The engine strictly checks:
   - Does student CGPA meet or exceed `course.minimum_cgpa`?
   - Has student fulfilled all required prerequisites?
   Any ineligible courses are filtered to `rejected_courses` with explicit causal explanations.
6. **Multi-Factor Suitability Scoring**:
   $$\text{Score} = (w_1 \times S_{\text{interest}}) + (w_2 \times S_{\text{career}}) + (w_3 \times S_{\text{cgpa}}) + (w_4 \times S_{\text{prereq}})$$
   Weights: Interest Match ($40\%$), Career Alignment ($35\%$), CGPA Clearance ($15\%$), Prerequisite Completion ($10\%$).
7. **Tiered Ranking**: Courses are categorized into:
   - **Highly Recommended**: Suitability $\ge 80\%$
   - **Recommended**: Suitability $60\% - 79\%$
   - **Alternative Option**: Suitability $< 60\%$
8. **Explainable AI (XAI) Generation**: For each course, `ExplanationGenerator` creates human-readable justifications citing specific rule matches, interest overlaps, career alignment, and explicit assumptions.
9. **Persistence & Presentation**: Results are saved to `recommendation_history` and rendered in the student portal.

---

## 7. Security Architecture

1. **Role-Based Access Control (RBAC)**: Custom decorators `@student_required` and `@admin_required` enforce strict boundaries, preventing privilege escalation.
2. **SQL Injection Immunization**: All MySQL operations utilize parameterized query interfaces with `%s` placeholders. String formatting in queries is completely prohibited.
3. **Session & Cookie Hygiene**: Session state is decoupled from large payloads. Recommendation results and audit logs are persisted in database tables rather than overflowing client-side cookie limits.
4. **Input Sanitization & Validation**: Form fields, CGPA ranges ($0.00 - 4.00$), and rule JSON structures are strictly validated prior to processing.
