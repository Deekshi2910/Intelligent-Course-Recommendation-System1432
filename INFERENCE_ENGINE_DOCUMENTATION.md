# Intelligent Course Recommendation System: AI Inference Engine Documentation

## Phase 9: Complete AI Inference Engine & Explainable Recommendation Architecture

---

### Executive Overview

An **Inference Engine** is the processing brain of an Artificial Intelligence Knowledge-Based Expert System. While the **Knowledge Base** stores structured facts (course catalog, prerequisites, domain ontologies, career goal mappings) and the **Rule Base** encodes expert production rules (IF-THEN heuristics), the **Inference Engine** dynamically infers new knowledge and reaches actionable decisions by applying logical reasoning over student working memory.

In the **Intelligent Course Recommendation System**, the Inference Engine is architected as a hybrid expert system that synthesizes:
1. **Data-Driven Forward Chaining Deduction**: Evaluates production rules from MySQL to deduce course candidates.
2. **Non-Monotonic Default Reasoning (Reiter's Default Logic)**: Formulates defeasible working hypotheses when student attributes are missing or incomplete (DR01–DR05).
3. **Hard Academic Eligibility Enforcement**: Strictly validates course activity, minimum CGPA prerequisites, and completed course dependencies as non-negotiable boundaries before scoring.
4. **Multi-Factor Weighted Suitability Scoring**: Computes transparent, normalized metrics across four configurable dimensions:
   $$\text{Suitability Score} = (\text{Interest} \times 0.40) + (\text{Career} \times 0.35) + (\text{CGPA} \times 0.15) + (\text{Prerequisite} \times 0.10)$$
5. **Multi-Tier Course Ranking & Tier Assignment**: Eliminates duplicate recommendations, breaks score ties deterministically, and categorizes electives into pedagogical badges.
6. **Explainable AI (XAI) Justifications**: Generates grounded, human-interpretable natural language rationales detailing matched interests, career pathways, eligibility thresholds, and fired rules.
7. **Transactional Audit Logging**: Persists final recommendation runs into MySQL `recommendation_history` while guaranteeing run-level deduplication.

---

### Architecture & System Data Flow

```text
                               +-------------------------------------+
                               |       Student Profile Facts         |
                               | (CGPA, Semester, Interests, Career) |
                               +------------------+------------------+
                                                  |
                                                  v
                               +-------------------------------------+
                               |     Fact Normalization & Sanitizer  |
                               +------------------+------------------+
                                                  |
                                                  v
                               +-------------------------------------+
                               |    Hard Course Eligibility Check    |
                               |   (Active Status, CGPA, Prereqs)    |
                               +--------+-------------------+--------+
                                        |                   |
                        [Fails Criteria]|                   |[Meets Criteria]
                                        v                   v
                     +--------------------+       +--------------------+
                     |  Rejected Courses  |       |  Eligible Courses  |
                     |  (Audit Log Trail) |       |  (Working Memory)  |
                     +--------------------+       +---------+----------+
                                                            |
                                        +-------------------+-------------------+
                                        |                                       |
                                        v                                       v
                     +------------------------------------+  +------------------------------------+
                     |     Forward Chaining Deduction     |  |       Default Fallback Engine      |
                     | (Production Rules Agenda: P10->P1) |  |   (Reiter's Logic: DR01 -> DR05)   |
                     +------------------+-----------------+  +------------------+-----------------+
                                        |                                       |
                                        +-------------------+-------------------+
                                                            |
                                                            v
                                           +----------------------------------+
                                           |  Candidate Pool Deduplication    |
                                           +----------------+-----------------+
                                                            |
                                                            v
                                           +----------------------------------+
                                           | Transparent Multi-Factor Scorer  |
                                           |  (40% Int, 35% Car, 15% CGPA,    |
                                           |         10% Prerequisite)        |
                                           +----------------+-----------------+
                                                            |
                                                            v
                                           +----------------------------------+
                                           |    Multi-Tier Course Ranker      |
                                           | (Score DESC, Priority DESC, Code)|
                                           +----------------+-----------------+
                                                            |
                                                            v
                                           +----------------------------------+
                                           |   Explainable AI (XAI) Engine    |
                                           |   (Grounded Rationale Synthesis) |
                                           +----------------+-----------------+
                                                            |
                                           +----------------+-----------------+
                                           |                                  |
                                           v                                  v
                        +----------------------+           +----------------------+
                        | Flask Student UI /   |           | MySQL Persistence    |
                        | Admin Monitoring     |           | (recommendation_hist)|
                        +----------------------+           +----------------------+
```

---

### Core Components & Engineering Specifications

#### 1. Forward Chaining Deduction (`ai_engine/forward_chaining.py`)
- **Paradigm**: Data-driven forward deduction operating via the canonical **Match $\rightarrow$ Resolve $\rightarrow$ Act** inference loop.
- **Working Memory**: Holds normalized student facts, active course facts, and intermediate assertions (e.g. `qualified_for_course_<id>`).
- **Conflict Resolution**: Sorts eligible candidate rules by `Priority DESC` ($10 \rightarrow 1$), followed by condition match confidence score descending.
- **Cycle Quiescence**: Fires eligible rules in priority order and asserts intermediate facts until fixed-point quiescence (no new rules can fire) or maximum cycles reached.
- **Infinite Loop Prevention (Refraction)**: Tracks `already_fired_rule_ids` to guarantee no production rule fires more than once per inference run.

#### 2. Default Reasoning Integration (`ai_engine/default_reasoning.py`)
- **Paradigm**: Non-monotonic Default Logic based on Reiter's inference framework:
  $$\frac{\alpha : \beta}{\gamma}$$
  *(If prerequisite $\alpha$ is known, and hypothesis $\beta$ is consistent with current knowledge, infer default conclusion $\gamma$.)*
- **Canonical Rules**:
  - **DR01 (Missing Career Goal)**: Triggers interest-based fallback; career match evaluates to $0.0\%$.
  - **DR02 (Missing Interests)**: Triggers career-based fallback; interest match evaluates to $0.0\%$.
  - **DR03 (Missing Both)**: Generates foundational core elective recommendations (breadth).
  - **DR04 (Missing CGPA)**: Enforces academic constraint; **never invents or assumes CGPA**. Courses requiring CGPA are excluded until student provides verified academic record.
  - **DR05 (Unknown Prerequisites)**: Flags prerequisite status as unverified; **never assumes prerequisites are satisfied**.
- **Non-Monotonic Retraction**: Hypotheses recorded in `AssumptionManager` are retracted when actual student data is observed.

#### 3. Course Eligibility as a Hard Constraint (`ai_engine/inference_engine.py`)
Course eligibility is strictly a **hard constraint** rather than a mere penalty. A course is immediately excluded from the candidate pool and recorded in `rejected_courses` with explicit rationale if:
1. **Course Inactive**: `is_active == False` in the curriculum catalog.
2. **CGPA Deficit**: Student CGPA is lower than `minimum_cgpa`.
3. **Missing Formal Prerequisites**: Student has not completed mandatory prerequisite courses registered in `course_prerequisites`.

#### 4. Transparent Recommendation Scorer (`ai_engine/recommendation_scorer.py`)
Computes normalized suitability scores $[0.0, 100.0]$ using configurable weights:

$$\text{Suitability Score} = (S_{\text{int}} \times W_{\text{int}}) + (S_{\text{car}} \times W_{\text{car}}) + (S_{\text{cgp}} \times W_{\text{cgp}}) + (S_{\text{pre}} \times W_{\text{pre}})$$

- **Default Component Weights**:
  - **Interest Match ($W_{\text{int}} = 0.40$)**: Set deduplication eliminates double-counting of interests. Evaluates proportion of course domain tags matched:
    $$S_{\text{int}} = \min\left(100.0, \frac{|\text{Matched}|}{|\text{Course Interests}|} \times 75.0 + \min(|\text{Matched}|, 3) \times 8.33\right)$$
  - **Career Goal Match ($W_{\text{car}} = 0.35$)**: $100.0\%$ for direct or whitespace/hyphen-normalized match; $0.0\%$ for undeclared or unaligned goals.
  - **CGPA Readiness ($W_{\text{cgp}} = 0.15$)**: Baseline $70.0\%$ for meeting prerequisite + $15.0\%$ per grade point margin above minimum requirement.
  - **Prerequisite Fulfillment ($W_{\text{pre}} = 0.10$)**: $100.0\%$ if no prerequisites are required or all completed; $0.0\%$ if unverified (DR05).

#### 5. Course Ranker & Tier Categorization (`ai_engine/course_ranker.py`)
- **Deduplication**: Merges duplicate rule firings by `course_id`, retaining the maximum priority and combining reasoning audit trails.
- **Multi-Factor Sorting Keys**:
  1. Suitability Score descending ($100.0 \rightarrow 0.0$).
  2. Production Rule Priority descending ($10 \rightarrow 1$).
  3. Course Code ascending (deterministic tie-breaking).
- **Pedagogical Tiers**:
  - **Highly Recommended (`bg-success`)**: Score $\ge 85.0\%$ or (Priority $\ge 8$ and Score $\ge 75.0\%$).
  - **Strong Match (`bg-primary`)**: Score $\ge 65.0\%$.
  - **Foundational Breadth (`bg-secondary`)**: Assigned under default reasoning (DR03).
  - **Elective Option (`bg-info`)**: Eligible elective courses.

#### 6. Grounded Explainable AI (XAI) (`ai_engine/explanation_generator.py`)
Synthesizes natural language justifications derived purely from actual evaluation facts:

> *"Machine Learning received a suitability score of 90 because it matches your interests in Python and Mathematics, aligns with your Data Scientist career goal, and satisfies the academic eligibility requirement. AI Rule(s) Fired: Rule_Machine_Learning_Core. Score Calculation: Interest=85.0% (×40%) + Career=100.0% (×35%) + CGPA=90.0% (×15%) + Prerequisite=100.0% (×10%)."*

#### 7. Database Integration & Persistence
- **Table**: `recommendation_history`
- **Fields Stored**: `student_id`, `recommended_course_id`, `recommendation_score`, `reasoning`, `created_at`.
- **Run-Level Deduplication**: Tracks inserted course IDs in working memory to prevent duplicate records within the same recommendation batch.
- **Integrity**: Parameterized SQL statements executed inside transactional `with get_db_cursor(commit=True)` contexts.

---

### Automated Test Suite Results

The complete test suite was executed using `unittest discover`:

```text
Ran 103 tests in 16.821s
OK (All 103 tests passed with 100% success rate)
```

#### Phase 9 Automated Test Verification (`test_phase9_inference_engine.py`)

| Test Code | Specification | Test Description | Status |
| :---: | :--- | :--- | :---: |
| **Test A** | Complete Student Information | Full profile with CGPA, interests, career goal, and completed courses triggers forward chaining rule evaluation and multi-factor scoring | **PASS** |
| **Test B** | Missing Career Goal | Undeclared career goal triggers DR01 interest fallback; career score is $0.0\%$ (not assumed) | **PASS** |
| **Test C** | Missing Interests | Empty interest list triggers DR02 career fallback; interest score is $0.0\%$ | **PASS** |
| **Test D** | Missing Both | Missing interests and career goal triggers DR03 foundational breadth recommendations | **PASS** |
| **Test E** | Missing CGPA | Missing CGPA triggers DR04 request; CGPA is never invented; courses requiring CGPA are excluded | **PASS** |
| **Test F** | Low CGPA | Hard eligibility exclusion; courses failing minimum CGPA excluded and recorded in `rejected_courses` | **PASS** |
| **Test G** | Unknown Prerequisites | Unspecified course history triggers DR05 unverified flags; prerequisites never assumed satisfied | **PASS** |
| **Test H** | Multiple Matched Rules | Profile matching several active rules triggers forward chaining agenda and deduplication merging | **PASS** |
| **Test I** | Conflicting Rules | Forward chaining resolves conflicting rule candidates via priority descending ($9 > 3$) | **PASS** |
| **Test J** | Duplicate Recommendations | Course recommended by multiple rules deduplicated into a single entry with merged reasons | **PASS** |
| **Test K** | Equal Recommendation Scores | Equal scores broken deterministically by rule priority descending and course code | **PASS** |
| **Test L** | Inactive Courses | Inactive courses (`is_active = False`) strictly excluded from candidate pool | **PASS** |
| **Test M** | No Eligible Courses | Student with CGPA below all curriculum minimums yields 0 recommendations and logs all rejections | **PASS** |
| **Test N** | History Storage | Persists top recommendations to MySQL `recommendation_history` with run-level duplicate prevention | **PASS** |
| **Test O** | Explanation Accuracy | Validates grounded natural language XAI rationale against evaluation facts | **PASS** |
| **Test P** | Independent Forward Chaining | Evaluates Match-Resolve-Act loop, refraction tracking, and working memory assertion | **PASS** |

---

### Security & Safety Adherence

1. **Strictly Zero Dynamic Code Execution**: Prohibited `eval()`, `exec()`, or dynamic AST code generation across all modules.
2. **Explicit Operator & Field Allowlists**: Rule conditions validate fields and comparison operators against strict tuples.
3. **SQL Injection Defense**: All MySQL queries utilize parameterized placeholders (`%s`) exclusively.
4. **RBAC & Cross-Student Isolation**: The recommendation route `/student/recommendations` verifies authenticated session user ID and ensures students can only generate and view their own personal recommendations.
5. **Audit Trail Immutability**: Historical recommendation records in `recommendation_history` are never deleted during normal recommendation runs.
