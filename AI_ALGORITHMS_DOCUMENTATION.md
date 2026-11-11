# AI Algorithms & Knowledge-Based Reasoning Documentation

---

## 1. Introduction & Theoretical Overview

The **Intelligent Course Recommendation System (ICRS)** employs an advanced composite Artificial Intelligence architecture combining:
1. **Relational Knowledge Representation (KR)**
2. **First-Order Production Rules with Salience Ordering**
3. **Forward-Chaining Inference with Refraction**
4. **Non-Monotonic Default Reasoning with Epistemic Assumption Tracking**
5. **Multi-Factor Multi-Criteria Decision Scoring (MCDA)**
6. **Explainable AI (XAI) Natural Language Generation**

Unlike opaque black-box machine learning models (e.g., deep neural networks), this knowledge-based expert system delivers deterministic, mathematically auditable, and fully explainable course recommendations that comply with institutional academic regulations.

---

## 2. Knowledge Representation Architecture

### 2.1 Formalism
Knowledge in ICRS is represented as structured facts and relational graphs:

- **Entity-Attribute-Value (EAV)**:
  $$\text{Course}(c) \rightarrow \{\text{Code}, \text{Credits}, \text{MinCGPA}, \text{Difficulty}, \text{CareerScope}\}$$
- **Relational Domain Maps**:
  $$\mathcal{R}_{\text{Interest}}: \text{Course} \times \text{Interest} \rightarrow \{0, 1\}$$
  $$\mathcal{R}_{\text{Career}}: \text{Course} \times \text{CareerGoal} \rightarrow \{0, 1\}$$
- **Prerequisite Directed Acyclic Graph (DAG)**:
  $$G = (V, E), \quad (u, v) \in E \iff u \text{ is a strict prerequisite for } v$$

### 2.2 Knowledge Repository & Validator
- `KnowledgeRepository` extracts clean fact dictionaries from MySQL.
- `KnowledgeValidator` performs semantic consistency audits:
  - Detects orphan courses with zero interest mappings.
  - Identifies invalid CGPA thresholds ($< 0.0$ or $> 4.0$).
  - Detects self-referential or cyclic prerequisite loops.

---

## 3. Production Rule Engine & Condition Grammar

### 3.1 Rule Structure
Production rules are formalized as:
$$\text{Rule } R_i = \langle \text{ID}, \text{Name}, \text{Priority}, \text{Antecedent}(\mathcal{C}), \text{Consequent}(\mathcal{A}) \rangle$$

Where $\mathcal{C}$ is a condition tree and $\mathcal{A}$ is a recommended course identifier.

### 3.2 JSON Condition Grammar
Conditions support logical grouping and typed predicate comparisons:
```json
{
  "operator": "AND",
  "conditions": [
    {
      "field": "cgpa",
      "operator": ">=",
      "value": 3.0
    },
    {
      "field": "interests",
      "operator": "CONTAINS",
      "value": "Artificial Intelligence"
    },
    {
      "field": "career_goal",
      "operator": "==",
      "value": "Data Scientist"
    }
  ]
}
```

### 3.3 Supported Operators
- `==`, `!=`, `<`, `<=`, `>`, `>=`
- `IN`: Checks if a scalar attribute exists within an array.
- `CONTAINS`: Checks if an array attribute contains a target scalar.
- `INTERSECTS`: Checks if two sets share at least one element.

---

## 4. Forward-Chaining Inference Engine

### 4.1 Working Memory Model
Working memory $\mathcal{W}$ contains ground facts:
$$\mathcal{W} = \{\text{Fact}(\text{student\_cgpa}, 3.45), \text{Fact}(\text{interest}, \text{"AI"}), \dots\}$$

### 4.2 Match-Resolve-Act Cycle
1. **Match**: The engine matches all active production rules against $\mathcal{W}$ using `RuleEvaluator`. All satisfied rules form the **Conflict Set** $\mathcal{S}$.
2. **Resolve**: The conflict set is sorted by rule priority (salience) in descending order:
   $$\text{Priority}(R_1) \ge \text{Priority}(R_2) \ge \dots \ge \text{Priority}(R_k)$$
3. **Act**: The highest-priority rule fires, asserting a new recommendation fact into working memory.
4. **Refraction Loop Prevention**: To prevent infinite firing loops, the engine maintains an execution set $\mathcal{E}$ of previously fired `(rule_id, course_id)` tuples. A rule instance fires at most once per student inference session.

---

## 5. Non-Monotonic Default Reasoning

### 5.1 The Incomplete Information Problem
In educational advising, students frequently exhibit incomplete profiles:
- Missing career goals (undecided career trajectory).
- Unselected technical interests.
- Incomplete prerequisite course history.

Standard deductive logic halts when premises are missing. ICRS uses non-monotonic default reasoning to infer provisional recommendations while maintaining strict academic safety.

### 5.2 Default Rules Formulation
| Rule Code | Trigger Condition | Default Action / Fallback Strategy | Epistemic Status |
| :--- | :--- | :--- | :--- |
| **DR01** | Missing Career Goal, Interests Present | Infer courses aligned with student's verified interests. | `ASSUMED_DEFAULT` |
| **DR02** | Missing Interests, Career Goal Present | Infer foundational courses aligned with career goal pathway. | `ASSUMED_DEFAULT` |
| **DR03** | Missing Career Goal AND Interests | Recommend high-demand general core foundation electives. | `ASSUMED_DEFAULT` |
| **DR04** | Missing CGPA | **NEVER ASSUME CGPA**. Reject inference until student inputs verifiable academic record. | `UNKNOWN` (Halt) |
| **DR05** | Unknown Prerequisite Records | Mark prerequisite clearance as unverified. Recommend introductory courses without prerequisites. | `ASSUMED_DEFAULT` |

### 5.3 Assumption Management & Belief Revision
- Every default inference is logged with an epistemic marker: `VERIFIED` vs `ASSUMED_DEFAULT`.
- When a student later provides the missing information, `AssumptionManager` withdraws the default facts, restoring monotonic consistency.

---

## 6. Multi-Factor Suitability Scoring Algorithm

Once candidate courses are derived from rules and default logic, each eligible course $c$ is assigned a quantitative suitability score:

$$\text{SuitabilityScore}(c) = \sum_{i=1}^{4} w_i \cdot S_i(c)$$

### 6.1 Weight Allocation Rationale
1. **Domain Interest Match ($w_1 = 0.40$)**: Measures overlap between student interests and course topic mappings.
2. **Career Goal Alignment ($w_2 = 0.35$)**: Measures direct relevance to the student's declared or inferred vocational target.
3. **CGPA Academic Clearance ($w_3 = 0.15$)**: Scaled metric reflecting academic comfort above minimum cutoff:
   $$S_{\text{cgpa}} = \min\left(1.0, \frac{\text{Student CGPA} - \text{Course Min CGPA}}{1.0} + 0.5\right)$$
4. **Prerequisite Fulfillment ($w_4 = 0.10$)**: Evaluates completion of required preparatory courses.

$$\sum w_i = 0.40 + 0.35 + 0.15 + 0.10 = 1.00 \quad (100\%)$$

---

## 7. Course Ranking & Tier Assignment

Eligible courses are sorted by final suitability score in descending order and assigned to standardized academic tiers:

| Tier | Score Range | Pedagogical Meaning |
| :--- | :---: | :--- |
| **Highly Recommended** | $\ge 80.0\%$ | Prime match. High interest overlap, direct career alignment, strong academic clearance. |
| **Recommended** | $60.0\% - 79.9\%$ | Solid match. Meets either career goal or primary interests with sound eligibility. |
| **Alternative Option** | $< 60.0\%$ | Broadening or exploratory elective. Satisfies prerequisites and CGPA cutoffs. |

---

## 8. Explainable AI (XAI) Generation

Trust in automated advising requires comprehensive transparency. The `ExplanationGenerator` constructs a human-readable justification for every recommendation:

1. **Rule Citation**: Names the specific production rule that derived the candidate course.
2. **Factor Breakdown**: Explicitly presents the calculated component scores (e.g., Interest: $100\%$, Career: $100\%$, CGPA: $85\%$).
3. **Assumption Disclaimers**: If any default reasoning was applied (e.g., DR01 or DR02), an explicit notice warns the student of provisional assumptions.
4. **Prerequisite Assurance**: Confirms that required preparatory courses have been verified.
