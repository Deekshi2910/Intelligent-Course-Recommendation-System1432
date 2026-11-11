# Intelligent Course Recommendation System (ICRS)
## Comprehensive User & Administrator Manual

---

# PART I: STUDENT USER GUIDE

## 1. Getting Started: Registration & Authentication

1. Open your web browser and navigate to the application URL:
   ```text
   http://127.0.0.1:5000/
   ```
2. Click **Get Started** or **Student Sign In**.
3. If you are a new student:
   - Click **Create an Account**.
   - Enter your **Username**, **University Email**, and a secure **Password** (minimum 8 characters, including letters, numbers, and symbols).
   - Enter your **Roll Number**, **Department** (e.g., Computer Science & Engineering), and **Current Semester**.
   - Click **Complete Registration**.
4. Log in using your email/username and password.

---

## 2. Setting Up Your Academic Profile

To provide optimal recommendations, the AI engine requires your academic metrics:

1. In the Student Dashboard sidebar, click **Academic Profile**.
2. Enter your current **Cumulative Grade Point Average (CGPA)** on a 4.00 scale (e.g., `3.65`).
   > **Note**: The system strictly validates that your CGPA is between $0.00$ and $4.00$.
3. Update your **Semester** or **Department** if changed.
4. Click **Save Academic Profile**.

---

## 3. Selecting Your Technical & Domain Interests

1. In the sidebar, navigate to **Domain Interests**.
2. You will see a catalog of technical specialization badges (e.g., *Artificial Intelligence*, *Cybersecurity*, *Cloud Computing*, *Web Development*, *Data Science*).
3. Click on the badges that reflect your academic curiosity and career aspirations. Selected items will highlight in blue with a checkmark.
4. Click **Update Interests**.

---

## 4. Defining Your Career Goal

1. In the sidebar, navigate to **Career Goal**.
2. Select your target professional trajectory from the available pathways (e.g., *Data Scientist*, *Cloud Solutions Architect*, *Full-Stack Software Engineer*, *Cybersecurity Analyst*).
3. Click **Set Career Goal**.

---

## 5. Generating Intelligent Course Recommendations

1. In your dashboard, click **Generate Course Recommendations**.
2. The AI Inference Engine will immediately:
   - Load knowledge facts and production rules from the Knowledge Base.
   - Run Default Reasoning if any profile elements are pending.
   - Execute Forward Chaining deduction.
   - Filter out courses where your CGPA or prerequisites do not meet requirements.
   - Compute multi-factor suitability scores.
   - Rank and categorize courses into pedagogical tiers.
3. Your recommendation page displays:
   - **Suitability Score Gauge** (e.g., $92\%$).
   - **Tier Badge**:
     - 🟢 **Highly Recommended** ($\ge 80\%$)
     - 🔵 **Recommended** ($60\% - 79\%$)
     - 🟡 **Alternative Option** ($< 60\%$)
   - **Course Metadata**: Code, Credits, Difficulty, Minimum CGPA cutoff.
   - **XAI Explanation Card**: Detailed natural-language breakdown showing which rules matched, interest overlap, career relevance, and any default assumptions applied.
   - **Prerequisite Status**: Confirmation of prerequisite clearance.

---

## 6. Using the Interactive AI Rule Testing Sandbox

The **AI Rule Testing Page** allows students and researchers to experiment with hypothetical academic scenarios:

1. In the sidebar, click **AI Rule Testing**.
2. Enter a hypothetical **CGPA** (e.g., `3.80`).
3. Select hypothetical **Domain Interests** (e.g., *Artificial Intelligence*, *Data Science*).
4. Select a hypothetical **Career Goal** (e.g., *Data Scientist*).
5. Click **Evaluate Rules**.
6. The test runner will immediately output:
   - **Matched Rules**: Production rules whose antecedent conditions were satisfied.
   - **Failed Rules**: Production rules that failed, with an explanation of which specific condition failed.
   - **Recommended Courses**: Candidate courses derived from matched rules.
   - **Rejected Courses**: Courses filtered due to CGPA or prerequisite restrictions.
   - **Step-by-Step Reasoning Log**: Timestamped inference trail showing the deduction sequence.

---

## 7. Viewing Recommendation History

1. In the sidebar, click **Recommendation History**.
2. View your past recommendation sessions with timestamps.
3. Click **View Snapshot** to inspect the courses and scores generated during previous advising sessions.

---

# PART II: ADMINISTRATOR USER GUIDE

## 1. Accessing the Admin Portal

1. Navigate to:
   ```text
   http://127.0.0.1:5000/admin/login
   ```
2. Log in with administrator credentials:
   - **Username / Email**: `admin@university.edu`
   - **Password**: `Admin@12345` (or configured password)
3. Upon authentication, you will be redirected to the **Admin Executive Dashboard**.

---

## 2. Admin Dashboard & Executive Overview

The dashboard displays real-time operational metrics:
- **Total Students**: Number of registered students.
- **Active Courses**: Number of courses in the active catalog.
- **AI Production Rules**: Number of active declarative rules.
- **Recommendation Inferences**: Total recommendation runs generated.
- **Distribution Charts**: Student interest distributions and career goal choices.

---

## 3. Student Record Management

1. In the admin sidebar, click **Students**.
2. View the student roster with roll numbers, departments, semesters, and CGPA standings.
3. Click **Inspect** to review a student's profile and recommendation history.
4. Use the **Toggle Status** button to activate or suspend student access.

---

## 4. Course Catalog Management

1. In the sidebar, click **Courses**.
2. To add a new course:
   - Click **+ Add Course**.
   - Enter **Course Code** (e.g., `CS-405`), **Course Name**, **Credits**, **Minimum CGPA** (e.g., `3.00`), **Difficulty Level**, and **Career Scope**.
   - Select domain interest tags and career pathways linked to this course.
   - Specify prerequisites.
   - Click **Create Course**.
3. To edit an existing course:
   - Click **Edit** next to any course in the table.
   - Update parameters and click **Save Changes**.
4. To toggle or delete:
   - Click **Deactivate / Activate** to change availability.
   - Click **Delete** to remove obsolete courses.

---

## 5. Domain Interests & Career Goals Taxonomy

1. **Interests**:
   - Navigate to **Domain Interests**.
   - Add new specialization areas (e.g., *Quantum Computing*, *Bioinformatics*).
   - View how many active courses and students are associated with each interest.
2. **Career Goals**:
   - Navigate to **Career Goals**.
   - Add new target occupations and vocational scopes.

---

## 6. AI Production Rules Management

1. In the sidebar, click **AI Knowledge Rules**.
2. Review active production rules with their conditions, targets, and priority numbers.
3. Click **+ Create New Rule**:
   - Define **Rule Name** (e.g., *AI_High_CGPA_FastTrack*).
   - Set **Priority** (integer; higher numbers fire first in conflict resolution).
   - Select target **Recommended Course**.
   - Build condition logic using the condition builder (supports `AND`, `OR`, `cgpa >=`, `interests CONTAINS`, etc.).
   - Click **Save Rule**.
4. Toggle or edit existing rules dynamically without restarting the application.

---

## 7. Default Reasoning Administration

1. In the sidebar, click **Default Rules**.
2. View the status of non-monotonic fallback heuristics:
   - **DR01**: Missing Career Goal (Interest fallback).
   - **DR02**: Missing Interests (Career fallback).
   - **DR03**: Missing Both (General foundation fallback).
   - **DR04**: Missing CGPA (Strict rejection; never assumed).
   - **DR05**: Unknown Prerequisites (Unverified restriction).
3. Toggle individual heuristics on or off as institutional academic policies evolve.

---

## 8. Knowledge Base Health & Semantic Audit

1. In the sidebar, click **Knowledge Base Audit**.
2. Click **Run Diagnostic Audit**.
3. The system scans the relational database graph and reports:
   - Any courses with zero interest tags.
   - Any courses with missing career mappings.
   - Any broken prerequisite foreign keys.
   - Any out-of-range CGPA thresholds.
4. Green indicators signify a 100% clean, consistent knowledge base.

---

## 9. Analytics & Audit Reports

1. In the sidebar, click **Analytics & Reports**.
2. Inspect system-wide recommendation metrics:
   - Most frequently recommended courses.
   - Popular student interest domains.
   - Incomplete profile frequencies and default rule trigger rates.
   - Detailed audit logs of all past recommendation inferences.
