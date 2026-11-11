# Administrator Dashboard & Curriculum Control System
## Intelligent Course Recommendation System — Phase 5 Documentation

---

### 1. Executive Summary

Phase 5 introduces a comprehensive, enterprise-grade **Administrator Dashboard and Curriculum Control Portal** for the *Intelligent Course Recommendation System*. The portal empowers academic administrators to monitor system-wide recommendation metrics, inspect and manage student profiles, perform full CRUD operations on elective course offerings, curate domain interests and career goals, inspect the ontological knowledge matrix, and author declarative production rules for the upcoming Rule-Based AI Inference Engine.

All routes are strictly protected against unauthorized access, session hijacking, cache leakage, and injection vulnerabilities.

---

### 2. Architecture & Design Principles

```
                                  +---------------------------------------+
                                  |         Administrator Browser         |
                                  +---------------------------------------+
                                                      |
                                                      v
                                        +---------------------------+
                                        |  Flask-WTF CSRF & Auth    |
                                        +---------------------------+
                                                      |
                 +------------------------------------+-----------------------------------+
                 |                                    |                                   |
                 v                                    v                                   v
+---------------------------------+  +---------------------------------+  +---------------------------------+
|       Student Management        |  |        Curriculum Control       |  |     AI Knowledge Management     |
| - Registry Search & Filters     |  | - Course Catalog CRUD           |  | - Course-Interest Matrix        |
| - Dossier & Audit Inspection    |  | - Domain Interests Catalog      |  | - Declarative Production Rules  |
| - Account Activation Toggle     |  | - Career Pathways Catalog       |  | - Structured JSON Antecedents   |
| - Deactivation Login Enforcer   |  | - Safe Deletion / Soft Deact.   |  | - Audit Trail Reports & Logs    |
+---------------------------------+  +---------------------------------+  +---------------------------------+
                 |                                    |                                   |
                 +------------------------------------+-----------------------------------+
                                                      |
                                                      v
                                      +-------------------------------+
                                      |   MySQL 26.7 InnoDB Database   |
                                      +-------------------------------+
```

1. **Role-Based Authorization**: Every administrative view and action is wrapped in `@admin_required` and `@no_cache` decorators. Student accounts are rejected and redirected.
2. **Safe Deletion Policy**: Courses with existing student recommendation history cannot be hard deleted; they are automatically soft-deactivated (`is_active = FALSE`) to maintain database integrity and historical audit trails. Similarly, domain interests and career goals with active attachments are protected against accidental removal.
3. **Zero `eval()` / `exec()` Guarantee**: Administrative production rules are defined declaratively and serialized into structured JSON format in the `knowledge_rules.conditions` column. No dynamic code execution is permitted under any circumstances.
4. **Responsive UI/UX**: Built with Bootstrap 5, Bootstrap Icons, responsive navigation sidebar component (`templates/components/admin_sidebar.html`), KPI stat cards, and confirmation modal dialogs.

---

### 3. Endpoint Catalog

All administrative routes are prefixed with `/admin` and implemented in [`routes/admin.py`](file:///z:/Intelligent-Course-Recommendation/routes/admin.py):

| HTTP Method | Route Endpoint | Purpose & Functionality | Access Decorators |
| :--- | :--- | :--- | :--- |
| `GET`, `POST` | `/admin/login` | Administrator authentication entry point. | `@no_cache` |
| `GET` | `/admin/dashboard` | Central executive dashboard displaying 6 KPI stat metrics, recent registrations, and quick shortcuts. | `@admin_required`, `@no_cache` |
| `GET` | `/admin/students` | Student registry with real-time text query (`q`), department (`dept`), and semester (`sem`) filters. | `@admin_required`, `@no_cache` |
| `GET` | `/admin/students/<id>` | Comprehensive student dossier displaying academic profile, selected interests, and recommendation logs. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/students/<id>/toggle-status` | Inverts `users.is_active` status. Deactivated students are prevented from logging in. | `@admin_required`, `@no_cache` |
| `GET` | `/admin/courses` | Elective course catalog displaying codes, difficulty ratings, minimum CGPA, and interest tags. | `@admin_required`, `@no_cache` |
| `GET`, `POST` | `/admin/courses/add` | Form to create a new elective course and link domain interest mappings. | `@admin_required`, `@no_cache` |
| `GET`, `POST` | `/admin/courses/<id>/edit` | Form to edit course information and synchronize `course_interests` junction records. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/courses/<id>/toggle-status` | Toggle course availability between active and inactive in student offerings. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/courses/<id>/delete` | Deletes unreferenced courses or soft-deactivates courses with existing recommendation history. | `@admin_required`, `@no_cache` |
| `GET`, `POST` | `/admin/interests` | Lists domain interests with course and student usage counts; adds new interests. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/interests/<id>/edit` | Renames an existing domain interest. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/interests/<id>/delete` | Safely deletes an interest if not currently attached to any course or student. | `@admin_required`, `@no_cache` |
| `GET`, `POST` | `/admin/career-goals` | Lists career goals with student counts; adds new career pathways. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/career-goals/<id>/edit` | Updates career goal title and industry scope description. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/career-goals/<id>/delete` | Safely deletes an unused career goal. | `@admin_required`, `@no_cache` |
| `GET` | `/admin/knowledge-base` | Ontological matrix view displaying prerequisite chains, career scopes, and mapped interest domains. | `@admin_required`, `@no_cache` |
| `GET` | `/admin/rules` | Configured production rules view with parsed JSON conditions, priority badges, and toggle switches. | `@admin_required`, `@no_cache` |
| `GET`, `POST` | `/admin/rules/add` | Creates a new declarative AI production rule with antecedents and consequent rationale. | `@admin_required`, `@no_cache` |
| `GET`, `POST` | `/admin/rules/<id>/edit` | Updates rule priorities, academic conditions, domain interest matching, and explanations. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/rules/<id>/toggle` | Activates or deactivates an AI rule without deletion. | `@admin_required`, `@no_cache` |
| `POST` | `/admin/rules/<id>/delete` | Deletes an AI knowledge rule from the database. | `@admin_required`, `@no_cache` |
| `GET` | `/admin/reports` | Analytics and monitoring view for recommendation frequency, confidence distributions, and audit trails. | `@admin_required`, `@no_cache` |
| `GET`, `POST` | `/admin/profile` | Displays admin user profile; updates username and enables secure password change with verification. | `@admin_required`, `@no_cache` |

---

### 4. Database Schema & Data Integrity

The administrative features interact seamlessly with all 9 core database tables in `intelligent_course_recommendation`:

1. **`users` (`is_active` Boolean)**: Supports account lifecycle management. When an administrator deactivates a student, `users.is_active = FALSE`. The student login pipeline in [`routes/auth.py`](file:///z:/Intelligent-Course-Recommendation/routes/auth.py) immediately denies authentication with a descriptive warning.
2. **`courses`**: Stores elective course offerings (`course_code`, `course_name`, `description`, `minimum_cgpa`, `difficulty_level`, `career_scope`, `prerequisites`, `is_active`).
3. **`course_interests`**: M:N junction table between `courses` and `interests`. Dynamically synchronized upon course creation and updates.
4. **`knowledge_rules`**: Stores production rules with priority weighting (`1-10`), recommended course foreign key, and structured JSON antecedent conditions:
   ```json
   {
       "min_cgpa": 2.50,
       "min_semester": 4,
       "required_interests": ["Machine Learning", "Data Science & Analytics"],
       "preferred_career_goals": ["Machine Learning Engineer", "Data Scientist"],
       "rationale": "Student with predictive analytics interest strongly recommended for CS-401."
   }
   ```
5. **`recommendation_history`**: Audit logs of all suggestions generated for students, joined for analytics and individual student dossier reporting.

---

### 5. Security & Verification Architecture

- **CSRF Token Validation**: Every form includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` validated automatically by `Flask-WTF`.
- **Cache Invalidation**: `@no_cache` sets `Cache-Control: no-cache, no-store, must-revalidate` and `Pragma: no-cache` preventing sensitive student dossiers or administrative metrics from persisting in browser back-forward caches.
- **Password Integrity**: Admin password updates require verification of the existing password via `check_password_hash`, enforcement of minimum length constraints (≥ 8 characters), and secure salted hashing with Werkzeug.
- **SQL Injection Prevention**: 100% of SQL statements utilize parameterized `%s` placeholders.

---

### 6. Automated Test Verification Results

All 13 comprehensive tests in [`test_admin_dashboard.py`](file:///z:/Intelligent-Course-Recommendation/test_admin_dashboard.py) and all regression tests passed:

```
test_A1_dashboard_stats_and_overview ...................................... PASS
test_B1_students_list_search_and_filters .................................. PASS
test_B2_student_detail_dossier ............................................ PASS
test_B3_student_toggle_status_and_login_blocking .......................... PASS
test_C1_course_crud_and_interest_sync ..................................... PASS
test_D1_interest_crud_and_safety_checks ................................... PASS
test_D2_career_goal_crud_and_safety_checks ................................ PASS
test_E1_knowledge_base_matrix ............................................. PASS
test_F1_ai_rule_crud_with_structured_json ................................. PASS
test_G1_unauthenticated_access_is_blocked ................................. PASS
test_G2_student_role_blocked_from_admin_portal ............................ PASS
test_G3_admin_reports_monitoring .......................................... PASS
test_G4_admin_profile_and_password_security ............................... PASS

Overall Test Status: 13 / 13 PASSED (100% SUCCESS)
Regression Suites:
  - test_student_dashboard.py: 10 / 10 PASSED (100% SUCCESS)
  - test_auth.py:             14 / 14 PASSED (100% SUCCESS)
  - database/test_db.py:       6 / 6  PASSED (100% SUCCESS)
```
