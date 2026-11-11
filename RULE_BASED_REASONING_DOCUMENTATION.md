# AI Rule-Based Reasoning Engine Documentation
**Project:** Intelligent Course Recommendation System  
**Phase 7:** Rule-Based Reasoning Architecture & Production Rules Implementation  
**Version:** 1.0.0 (Production Ready)  
**Safety Protocol:** Zero Dynamic Code Execution (Strictly no `eval()` or `exec()`)

---

## 1. Overview of Rule-Based Reasoning

Rule-Based Reasoning (RBR) is a foundational paradigm of Knowledge-Based Artificial Intelligence (KBAI) and Expert Systems. Rather than relying on black-box probabilistic heuristics, Rule-Based Reasoning utilizes domain expertise formalized as explicit, transparent, and declarative **production rules**.

In this university course recommendation system:
- **Domain Knowledge** is stored as declarative facts (courses, CGPA cutoffs, prerequisites, student profiles, domain interests, and career pathways).
- **Inference Engine** applies deductive reasoning by matching student profile facts against rule condition antecedents.
- **Auditability & Explainability** are central: every recommendation provides a transparent, human-interpretable rationale explaining *why* a particular course was suggested, which conditions were satisfied, and why rejected courses failed academic criteria.

---

## 2. Production Rule Representation (IF–THEN Architecture)

Each production rule represents an expert recommendation policy of the formal shape:
$$\text{IF } \langle \text{Antecedent Conditions} \rangle \text{ THEN } \langle \text{Consequent Action} \rangle$$

### 2.1 Structured JSON Format

Rules are stored in MySQL (`knowledge_rules` table) using structured JSON conditions and strict allowlists:

```json
{
  "rule_name": "Rule_Machine_Learning_Core",
  "conditions": {
    "all": [
      {
        "field": "interests",
        "operator": "contains",
        "value": "Machine Learning"
      },
      {
        "field": "cgpa",
        "operator": "greater_than_or_equal",
        "value": 2.50
      }
    ],
    "any": [
      {
        "field": "career_goal",
        "operator": "equals",
        "value": "Machine Learning Engineer"
      },
      {
        "field": "career_goal",
        "operator": "equals",
        "value": "Data Scientist"
      },
      {
        "field": "interests",
        "operator": "contains",
        "value": "Python Programming"
      }
    ],
    "rationale": "Intermediate student with predictive analytics interest strongly recommended for Machine Learning."
  },
  "action": {
    "type": "recommend_course",
    "course_id": 1
  },
  "priority": 8,
  "is_active": true
}
```

### 2.2 Security and Safety Constraints
- **Zero dynamic code execution**: No `eval()`, `exec()`, or runtime compilation.
- **Explicit Field Allowlist**: `ALLOWED_FIELDS = {"interests", "career_goal", "cgpa", "department", "semester", "completed_courses"}`.
- **Explicit Operator Allowlist**: `ALLOWED_OPERATORS = {"equals", "not_equals", "contains", "greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal"}`.
- **Parameterized SQL**: All database operations use `%s` query bindings.

---

## 3. Condition Evaluation & Operator Registry

Evaluation is handled deterministically via a dedicated registry of pure Python comparator functions (`OPERATOR_REGISTRY` in `ai_engine.rule_evaluator`):

| Operator | Evaluated Semantic | Type Handling | Example Condition |
| :--- | :--- | :--- | :--- |
| `equals` | Strict equality | Case-insensitive for strings, exact for numerics | `career_goal equals 'Data Scientist'` |
| `not_equals` | Negated equality | Case-insensitive for strings | `department not_equals 'Civil'` |
| `contains` | Collection membership / substring | Checks element in list or substring | `interests contains 'Python'` |
| `greater_than` | Strict inequality ($>$) | Numeric float comparison | `cgpa greater_than 3.0` |
| `greater_than_or_equal` | Boundary inequality ($\ge$) | Numeric float comparison | `cgpa greater_than_or_equal 2.5` |
| `less_than` | Strict inequality ($<$) | Numeric float comparison | `semester less_than 8` |
| `less_than_or_equal` | Boundary inequality ($\le$) | Numeric float comparison | `cgpa less_than_or_equal 4.0` |

---

## 4. Logical Operators: Conjunction (AND) and Disjunction (OR)

Complex reasoning policies require composing multiple atomic condition predicates.

### 4.1 Conjunction (`all` / AND)
Every predicate listed in `conditions.all` must evaluate to `True`. If any single condition is not satisfied, the conjunction fails.
$$\text{Satisfied}(\text{all}) \iff \bigwedge_{p \in \text{all}} \text{Eval}(p, \text{StudentProfile})$$

### 4.2 Disjunction (`any` / OR)
At least one predicate listed in `conditions.any` must evaluate to `True`. If `conditions.any` is non-empty, satisfaction requires at least one match.
$$\text{Satisfied}(\text{any}) \iff \bigvee_{p \in \text{any}} \text{Eval}(p, \text{StudentProfile})$$

### 4.3 Compound Evaluation
When both `all` and `any` are defined:
$$\text{RuleMatches} \iff \text{Satisfied}(\text{all}) \land \text{Satisfied}(\text{any}) \land \text{AcademicEligibility} \land \text{PrerequisitesMet}$$

---

## 5. Academic Eligibility & Boundary Enforcement

Academic criteria represent **hard non-negotiable constraints** that cannot be overridden by rule priority, career alignment, or interest overlap.

### 5.1 Minimum CGPA Constraint
If a student's CGPA is strictly below the course's intrinsic `minimum_cgpa` threshold (or the rule's minimum threshold), the recommendation is **immediately rejected**:
$$\text{StudentCGPA} < \text{CourseMinCGPA} \implies \text{REJECT}$$

**Exact Boundary Behavior:**
- $\text{Threshold} = 2.50$:
  - $\text{CGPA} = 2.49 \implies$ **REJECTED** (Rejection logged: *"Student CGPA (2.49) is below minimum requirement (2.50)."*)
  - $\text{CGPA} = 2.50 \implies$ **SATISFIED** (Boundary met)
  - $\text{CGPA} = 2.51 \implies$ **SATISFIED** (Eligible)

### 5.2 Course Prerequisite Enforcement
When student data includes completed coursework (`completed_courses`), prerequisites defined in the curriculum (e.g. *Python, Linear Algebra* for *Machine Learning*) are evaluated. Missing any prerequisite marks the candidate course as rejected and documents the exact missing prerequisite in the audit trail.

---

## 6. Rule Priority & Conflict Resolution

In expert systems, multiple rules may fire simultaneously. The system uses a multi-tier conflict resolution strategy:

1. **Precedence by Priority**:
   - Each rule carries an integer priority from `1` (lowest) to `10` (highest).
   - Higher priority rules are evaluated first.
   - Recommended courses are ranked primarily by priority descending, secondarily by match score descending.
2. **Duplicate Recommendation Merging**:
   - If Rule A (Priority 6) and Rule B (Priority 9) both recommend Course 1 (*Machine Learning*), the system outputs **exactly one recommendation**.
   - Preserves highest priority ($\max(6, 9) = 9$).
   - Preserves highest match confidence score.
   - Merges unique reasoning evidences and records both firing rules in `fired_rules: ["Rule_A", "Rule_B"]`.
3. **Priority Invariance against Academic Criteria**:
   - High priority never overrides failing CGPA or missing prerequisites.

---

## 7. Explainable AI (XAI) & Reasoning Logs

For every recommended course, the engine constructs a comprehensive, human-interpretable explanation.

### 7.1 Successful Recommendation Example
> **Machine Learning (CS-401)** was recommended because the student has an interest in *Machine Learning, Python Programming*, selected *Data Scientist* as their career goal, and meets the minimum CGPA requirement of 2.50.

### 7.2 Rejection Audit Example
> **Deep Learning (CS-406)** was rejected: Student CGPA (2.85) is below course minimum requirement (3.00); Missing required prerequisite(s): Machine Learning.

---

## 8. Sample AI Production Rules Deployed

All 10 sample production rules dynamically query their corresponding course records from MySQL:

| Priority | Rule Name | Target Course | Core Conditions (AND / OR) |
| :---: | :--- | :--- | :--- |
| **P-10** | `Rule_Deep_Learning_Eligibility` | CS-406 Deep Learning | **AND:** CGPA $\ge 3.00$, Interest: Deep Learning & Neural Networks<br>**OR:** Career: AI Research Scientist \| ML Engineer |
| **P-9** | `Rule_NLP_Specialization` | CS-408 Natural Language Processing | **AND:** CGPA $\ge 2.75$, Interest: Natural Language Processing<br>**OR:** Career: NLP Specialist \| AI Research Scientist |
| **P-9** | `Rule_Computer_Vision_Specialization` | CS-409 Computer Vision | **AND:** CGPA $\ge 2.80$, Interest: Computer Vision<br>**OR:** Career: Computer Vision Engineer \| AI Research Scientist |
| **P-8** | `Rule_Machine_Learning_Core` | CS-401 Machine Learning | **AND:** CGPA $\ge 2.50$, Interest: Machine Learning<br>**OR:** Career: ML Engineer \| Data Scientist \| Interest: Python |
| **P-7** | `Rule_Big_Data_Analytics` | CS-403 Big Data Analytics | **AND:** CGPA $\ge 2.50$, Interest: Big Data & Distributed Computing<br>**OR:** Career: Big Data Engineer \| Data Engineer |
| **P-7** | `Rule_General_AI_Foundations` | CS-402 Artificial Intelligence | **AND:** CGPA $\ge 2.00$, Interest: Artificial Intelligence<br>**OR:** Career: AI Engineer \| AI Research Scientist |
| **P-6** | `Rule_Cloud_Computing_DevOps` | CS-404 Cloud Computing | **AND:** CGPA $\ge 2.00$<br>**OR:** Interest: Cloud Infrastructure \| Cloud Tech \| Career: Cloud Architect |
| **P-6** | `Rule_Cyber_Security_Defense` | CS-405 Cyber Security | **AND:** CGPA $\ge 2.00$<br>**OR:** Interest: Network Security \| Cyber Security \| Career: Security Analyst |
| **P-5** | `Rule_Data_Mining_Foundation` | CS-407 Data Mining | **AND:** CGPA $\ge 2.20$<br>**OR:** Interest: Data Mining \| Data Science \| Career: Data Scientist |
| **P-5** | `Rule_Internet_of_Things_Foundations` | CS-410 Internet of Things | **AND:** CGPA $\ge 2.00$<br>**OR:** Interest: Networking \| Career: Software Developer |

---

## 9. Automated Verification & Test Results

The rule-based reasoning engine is backed by exhaustive unit and integration testing in `test_rule_engine.py`:

```text
Ran 13 tests in 0.916s
OK
[PASS] Test 1: Interest matching verified.
[PASS] Test 2: Career goal matching verified.
[PASS] Test 3: CGPA academic eligibility and boundaries verified.
[PASS] Test 4: Combined AND ('all') conditions verified.
[PASS] Test 5: OR ('any') conditions verified.
[PASS] Test 6: Invalid operators and allowlist validation verified.
[PASS] Test 7: Missing student information handled gracefully.
[PASS] Test 8: Inactive rules strictly ignored.
[PASS] Test 9: Rule priority ordering verified.
[PASS] Test 10: Duplicate recommendation merging verified.
[PASS] Test 11: Prerequisite checking verified.
[PASS] Test 12: Unauthorized rule modifications blocked.
[PASS] Test 13: All 10 sample AI rules successfully verified.
```

**Full System Test Suite Run:**
- `test_rule_engine.py`: 13 / 13 Passed (100%)
- `test_knowledge_base.py`: 12 / 12 Passed (100%)
- `test_admin_dashboard.py`: 13 / 13 Passed (100%)
- `test_student_dashboard.py`: 10 / 10 Passed (100%)
- `test_auth.py`: 14 / 14 Passed (100%)
- `database/test_db.py`: 6 / 6 Passed (100%)

**Total: 68 / 68 Passed (100%)** across all system subsystems.
