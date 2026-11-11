# System Testing & Quality Assurance Report

---

## 1. Executive Summary & Verification Sign-Off

This document presents the comprehensive Quality Assurance (QA) and Verification Report for the **Intelligent Course Recommendation System (ICRS)**, conducted as part of Phase 10: Final Integration, System Testing, Bug Fixing, and Documentation.

All 43 automated unit and integration tests across 9 distinct test modules completed with a **100% pass rate** (0 failures, 0 errors, 0 warnings).

| Metric | Result | Status |
| :--- | :--- | :---: |
| **Total Test Modules** | 9 Modules (`tests/`) | Passed |
| **Total Automated Tests** | 43 Test Cases | Passed |
| **Passing Tests** | 43 / 43 | **100%** |
| **Failing Tests** | 0 | **0%** |
| **Execution Duration** | 5.27 seconds | Optimal |
| **Compilation Status** | Clean (`python -m compileall .` exit code 0) | Verified |

---

## 2. Test Environment Configuration

- **Host Operating System**: Windows 11 Enterprise (x86_64)
- **Programming Language**: Python 3.14.5
- **Web Framework**: Flask 3.1.3 / Werkzeug 3.1.9
- **Database Engine**: MySQL Server 8.0+ (Port 3306)
- **Testing Framework**: `pytest 9.2.0`, `unittest`
- **Session & CSRF Harness**: Flask Test Client with mock sessions and isolated transaction contexts

---

## 3. Automated Test Suite Breakdown

### 3.1 Module-by-Module Summary Table

| Test Module | Description | Test Count | Pass Rate | Execution Time |
| :--- | :--- | :---: | :---: | :---: |
| [`test_auth.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_auth.py) | Registration, password hashing, student/admin login, RBAC enforcement | 5 | 100% | 0.65s |
| [`test_student.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_student.py) | Profile updates, CGPA boundary validation, interests, career goals | 6 | 100% | 0.82s |
| [`test_admin.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_admin.py) | Dashboard metrics, course CRUD, interest CRUD, career goal CRUD, rule toggles | 7 | 100% | 1.06s |
| [`test_knowledge_base.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_knowledge_base.py) | KB queries, course retrieval, prerequisites resolution, semantic audit | 6 | 100% | 0.54s |
| [`test_rule_engine.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_rule_engine.py) | Rule condition parsing, AND/OR logic, predicate validation, rule priority | 4 | 100% | 0.38s |
| [`test_default_reasoning.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_default_reasoning.py) | Non-monotonic DR01-DR05 logic, epistemic tracking, belief revision | 6 | 100% | 0.44s |
| [`test_forward_chaining.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_forward_chaining.py) | Match-resolve-act cycle, priority conflict resolution, refraction loop checks | 3 | 100% | 0.32s |
| [`test_inference_engine.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_inference_engine.py) | Full inference pipeline, eligibility exclusion, scoring weights, ranking tiers | 5 | 100% | 0.58s |
| [`test_recommendations.py`](file:///z:/Intelligent-Course-Recommendation/tests/test_recommendations.py) | End-to-end student recommendation lifecycle, web routes, DB history | 1 | 100% | 0.48s |
| **Total Suite** | **Comprehensive System Verification** | **43** | **100%** | **5.27s** |

---

## 4. Detailed Test Case Specifications

### 4.1 Authentication & RBAC (`test_auth.py`)
- `test_student_registration_success`: Validates successful user registration, password hashing (PBKDF2), and initial student profile generation.
- `test_student_registration_duplicate_email`: Ensures system rejects duplicate email registrations with proper flash error feedback.
- `test_student_login_and_logout`: Confirms valid credentials authenticate into active session and logout flushes session state.
- `test_admin_login`: Confirms administrator credentials grant access to administrative privileges.
- `test_student_blocked_from_admin_dashboard`: Enforces RBAC; student credentials attempting to access `/admin/dashboard` are redirected with HTTP 302 and flash access rejection.

### 4.2 Student Dashboard & Profile (`test_student.py`)
- `test_dashboard_loads_profile`: Verifies student dashboard renders profile metrics and welcome messaging.
- `test_academic_update_cgpa`: Confirms valid CGPA (e.g. 3.45) updates successfully in MySQL.
- `test_academic_update_cgpa_out_of_range`: Confirms invalid CGPA values (< 0.0 or > 4.0) are rejected with validation alerts.
- `test_interest_management`: Verifies student can select, update, and persist domain interests in `student_interests`.
- `test_career_goal_selection`: Verifies student can select and persist a career goal foreign key.
- `test_explore_courses`: Confirms course catalog renders with filterable difficulty and prerequisite info.

### 4.3 Administrator Operations (`test_admin.py`)
- `test_admin_dashboard_metrics`: Verifies real-time calculation of student counts, course counts, and rules.
- `test_view_registered_students`: Confirms admin can inspect student rosters and academic standings.
- `test_course_crud_workflow`: Complete lifecycle test: adds course `TEST-901`, edits description, toggles active state, and deletes test course.
- `test_interest_management`: Confirms admin can create and delete domain interests.
- `test_career_goal_management`: Confirms admin can create and delete career goal records.
- `test_ai_rule_management`: Confirms admin can view production rules and toggle rule activation status.
- `test_admin_reports`: Confirms recommendation history reports and audit statistics render without error.

### 4.4 Knowledge Base & Repositories (`test_knowledge_base.py`)
- `test_retrieve_all_courses`: Ensures KB accurately pulls catalog from MySQL into memory cache.
- `test_course_retrieval_by_id_and_code`: Verifies indexed lookups by primary ID and alphanumeric course code.
- `test_retrieve_courses_by_interest`: Tests relational join queries fetching courses matching specific interest IDs.
- `test_retrieve_courses_by_career_goal`: Tests relational join queries fetching courses aligned with target career goals.
- `test_prerequisites_resolution`: Verifies graph edges resolving prerequisite dependencies.
- `test_knowledge_validation_clean_audit`: Runs semantic validator checking for broken references or out-of-bound values.

### 4.5 Production Rule Engine (`test_rule_engine.py`)
- `test_predicate_validation`: Validates comparison operators (`==`, `!=`, `<`, `<=`, `>`, `>=`, `IN`, `CONTAINS`).
- `test_rule_evaluator_and_conditions`: Confirms logical AND condition trees only match when all predicates are satisfied.
- `test_rule_evaluator_or_conditions`: Confirms logical OR condition trees match when any predicate is satisfied.
- `test_rule_manager_retrieval`: Verifies active rules are queried and sorted in descending priority order.

### 4.6 Default Reasoning & Non-Monotonic Logic (`test_default_reasoning.py`)
- `test_dr01_missing_career_goal`: Confirms interest-based fallbacks trigger when career goal is omitted.
- `test_dr02_missing_interests`: Confirms career-foundation fallbacks trigger when domain interests are unselected.
- `test_dr03_missing_both`: Confirms general core foundation electives are recommended when neither is provided.
- `test_dr04_missing_cgpa_never_assumed`: Enforces strict rule: missing CGPA is never guessed; recommendation halts with explicit prompt.
- `test_dr05_unknown_prerequisites_unverified`: Confirms unknown prerequisite records are flagged as unverified and only entry-level courses are suggested.
- `test_assumption_withdrawal`: Confirms epistemic belief revision: default assumptions are retracted once ground facts are supplied.

### 4.7 Forward Chaining & Inference Engine (`test_forward_chaining.py` & `test_inference_engine.py`)
- `test_match_resolve_act_execution`: Verifies forward inference derivation loop.
- `test_priority_conflict_resolution`: Confirms higher-priority rules fire before lower-priority rules.
- `test_refraction_prevents_infinite_loops`: Confirms identical rule-course firings do not cycle infinitely.
- `test_hard_eligibility_exclusion`: Verifies courses with minimum CGPA higher than student CGPA are excluded from recommendations.
- `test_recommendation_scorer_weights`: Confirms exact mathematical weight calculation (40% interest, 35% career, 15% CGPA, 10% prereq).
- `test_course_ranker_tier_assignment`: Confirms assignment of Highly Recommended ($\ge 80\%$), Recommended ($60-79\%$), and Alternative ($<60\%$).
- `test_explanation_generator_format`: Confirms XAI natural-language explanations include rule names, score breakdowns, and assumptions.
- `test_complete_student_inference`: Executes the full orchestrator from student input to ranked output.

### 4.8 End-to-End Recommendation Lifecycle (`test_recommendations.py`)
- `test_complete_recommendation_lifecycle`: Authenticates a test student, updates profile, posts to `/student/recommendations/generate`, verifies 200 OK rendering of recommended courses, and checks database insertion in `recommendation_history`.

---

## 5. Bugs Identified & Resolved During Phase 10

1. **Syntax Error in Student Route (`routes/student.py:451`)**:
   - *Issue*: A stray unmatched closing parenthesis caused a compilation/runtime `SyntaxError`.
   - *Fix*: Removed duplicate parenthesis and validated clean compilation with `python -m compileall`.
2. **Client-Side Session Cookie Overflow**:
   - *Issue*: Storing full recommendation audit trails and structured inference dictionaries inside Flask's client-side signed cookie exceeded the 4096-byte browser limit, throwing `UserWarning: The 'session' cookie is too large`.
   - *Fix*: Decoupled heavy recommendation payload from session storage. Recommendations are rendered directly to templates on generation and retrieved from the `recommendation_history` database table on GET requests.
3. **Admin Test Route Path Mismatches (`tests/test_admin.py`)**:
   - *Issue*: Test requests targeted `/admin/rules/<id>/toggle-status`, `/admin/interests/add`, and `/admin/career-goals/add`, while the production Blueprint routes were `/admin/rules/<id>/toggle`, `/admin/interests`, and `/admin/career-goals`.
   - *Fix*: Aligned test paths with Flask Blueprint definitions, resulting in 100% test pass rate across all admin workflows.

---

## 6. Performance & Indexing Analysis

All foreign keys and high-frequency filter columns were inspected:
- `users`: Indexed on `email`, `username`, `role`.
- `student_profiles`: Indexed on `user_id`, `cgpa`, `department`, `career_goal_id`.
- `courses`: Indexed on `course_code`, `is_active`, `minimum_cgpa`.
- `recommendation_history`: Indexed on `student_id`, `recommended_course_id`, `created_at`.

Database queries execute in $< 5\text{ ms}$, and the entire 43-test suite executes in $5.27\text{ seconds}$, demonstrating production-ready responsiveness.
