"""
Comprehensive Test Suite for Phase 7: Rule-Based Reasoning Engine
Validates:
1. Interest matching (contains operator)
2. Career goal matching (equals operator, case-insensitivity)
3. CGPA academic eligibility and exact boundary tests
4. Combined AND ('all') conditions
5. OR ('any') conditions
6. Invalid operators and fields (strict allowlist validation, zero eval/exec)
7. Missing student information (graceful fault tolerance)
8. Inactive rules handling (filtering and isolation)
9. Rule priority ordering (higher priority precedence)
10. Duplicate recommendations merging and reason consolidation
11. Prerequisite verification and missing prerequisite rejection
12. Unauthorized rule modifications security (admin-only enforcement)
13. All 10 sample AI rules verified in MySQL
"""

import unittest
import json
from werkzeug.security import generate_password_hash
from app import app
from database.db_connection import get_db_cursor
from ai_engine.rules import (
    ProductionRule,
    ConditionGroup,
    RulePredicate,
    RuleAction,
    ALLOWED_FIELDS,
    ALLOWED_OPERATORS
)
from ai_engine.rule_evaluator import (
    RuleEvaluator,
    RuleEvaluationResult,
    evaluate_rules,
    OPERATOR_REGISTRY
)
from ai_engine.rule_manager import RuleManager
from ai_engine.knowledge_base import KnowledgeBase, CourseKnowledgeFact


class TestRuleBasedReasoningEngine(unittest.TestCase):
    """Unit and Integration tests for AI Rule-Based Reasoning."""

    stu_email = "test_rule_student@university.edu"
    stu_username = "rule_tester"
    stu_password = "TestPassword@123"

    @classmethod
    def setUpClass(cls):
        """Initializes Flask test application and database fixtures."""
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.client = cls.app.test_client()

        # Seed sample rules ensuring 10 rules exist
        cls.rule_mgr = RuleManager()
        cls.rule_mgr.seed_sample_rules()
        cls.kb = KnowledgeBase()

        # Clean up any residual test student
        cls.cleanup_student()

        # Seed test student
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            pw_hash = generate_password_hash(cls.stu_password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'student')
            """, (cls.stu_username, cls.stu_email, pw_hash))
            cls.stu_user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO student_profiles (user_id, full_name, roll_number, department, semester, cgpa)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (cls.stu_user_id, "Test Rule Student", "ROLL-RULE-01", "Computer Science", 5, 8.20))
            cls.stu_profile_id = cursor.lastrowid

    @classmethod
    def tearDownClass(cls):
        """Removes test student records."""
        cls.cleanup_student()

    @classmethod
    def cleanup_student(cls):
        with get_db_cursor(commit=True, dictionary=True) as (cursor, _):
            cursor.execute("DELETE FROM users WHERE email = %s OR username = %s", (cls.stu_email, cls.stu_username))

    def login_student(self):
        """Logs in the test student."""
        return self.client.post("/login", data={
            "identifier": self.stu_email,
            "password": self.stu_password
        }, follow_redirects=True)

    # =========================================================================
    # 1. Interest Matching
    # =========================================================================

    def test_1_interest_matching(self):
        """Verifies that 'contains' operator correctly matches student interest."""
        pred = RulePredicate(field="interests", operator="contains", value="Machine Learning")
        
        # Positive case: exact match in list
        matched, detail, _ = RuleEvaluator.evaluate_predicate(
            pred, {"interests": ["Machine Learning", "Python Programming"]}
        )
        self.assertTrue(matched)
        self.assertIn("Machine Learning", detail)

        # Positive case: case-insensitive match
        matched_case, _, _ = RuleEvaluator.evaluate_predicate(
            pred, {"interests": ["machine learning"]}
        )
        self.assertTrue(matched_case)

        # Negative case: interest absent
        unmatched, detail_fail, _ = RuleEvaluator.evaluate_predicate(
            pred, {"interests": ["Web Development", "Java Programming"]}
        )
        self.assertFalse(unmatched)
        self.assertIn("does not have required interest", detail_fail)
        print("[PASS] Test 1: Interest matching verified.")

    # =========================================================================
    # 2. Career Goal Matching
    # =========================================================================

    def test_2_career_goal_matching(self):
        """Verifies that 'equals' operator matches career goals with case-insensitivity."""
        pred = RulePredicate(field="career_goal", operator="equals", value="Data Scientist")

        # Positive match
        matched, _, _ = RuleEvaluator.evaluate_predicate(
            pred, {"career_goal": "Data Scientist"}
        )
        self.assertTrue(matched)

        # Positive match (different case and spacing)
        matched_ci, _, _ = RuleEvaluator.evaluate_predicate(
            pred, {"career_goal": "  data scientist  "}
        )
        self.assertTrue(matched_ci)

        # Negative match
        unmatched, _, _ = RuleEvaluator.evaluate_predicate(
            pred, {"career_goal": "Cloud Solutions Architect"}
        )
        self.assertFalse(unmatched)
        print("[PASS] Test 2: Career goal matching verified.")

    # =========================================================================
    # 3. CGPA Academic Eligibility & Boundary Testing
    # =========================================================================

    def test_3_cgpa_eligibility_and_boundaries(self):
        """Verifies that academic CGPA requirement is strictly enforced with boundary tests."""
        # Course requiring min_cgpa 2.50
        course_mock = CourseKnowledgeFact(
            course_id=1,
            course_code="CS-401",
            course_name="Machine Learning",
            description="Machine learning fundamentals",
            minimum_cgpa=2.50,
            difficulty_level="Advanced",
            prerequisites_text="Python"
        )

        rule = ProductionRule(
            id=991,
            rule_name="Test_Rule_ML",
            conditions=ConditionGroup(
                all=[RulePredicate("cgpa", "greater_than_or_equal", 2.50)],
                any=[]
            ),
            action=RuleAction("recommend_course", 1),
            priority=5
        )

        # 1. Below boundary: 2.49 -> REJECTED
        res_below = RuleEvaluator.evaluate(rule, {"cgpa": 2.49}, course_fact=course_mock)
        self.assertFalse(res_below.is_matched)
        self.assertFalse(res_below.cgpa_satisfied)
        self.assertTrue(any("below minimum requirement" in r.lower() for r in res_below.failed_conditions))

        # 2. Exact boundary: 2.50 -> SATISFIED
        res_exact = RuleEvaluator.evaluate(rule, {"cgpa": 2.50}, course_fact=course_mock)
        self.assertTrue(res_exact.is_matched)
        self.assertTrue(res_exact.cgpa_satisfied)

        # 3. Above boundary: 2.51 -> SATISFIED
        res_above = RuleEvaluator.evaluate(rule, {"cgpa": 2.51}, course_fact=course_mock)
        self.assertTrue(res_above.is_matched)
        self.assertTrue(res_above.cgpa_satisfied)

        # 4. Course with high CGPA requirement (e.g. 7.50 on 10-scale)
        high_course = CourseKnowledgeFact(
            course_id=99,
            course_code="CS-HONORS",
            course_name="Honors Research",
            description="Honors track",
            minimum_cgpa=7.50,
            difficulty_level="Advanced",
            prerequisites_text=""
        )
        high_rule = ProductionRule(
            id=992,
            rule_name="Test_Rule_Honors",
            conditions=ConditionGroup(
                all=[RulePredicate("cgpa", "greater_than_or_equal", 7.50)]
            ),
            action=RuleAction("recommend_course", 99),
            priority=10
        )
        # Student CGPA = 7.00 -> Rejected
        res_70 = RuleEvaluator.evaluate(high_rule, {"cgpa": 7.00}, course_fact=high_course)
        self.assertFalse(res_70.is_matched)
        self.assertFalse(res_70.cgpa_satisfied)

        # Student CGPA = 7.50 -> Eligible
        res_75 = RuleEvaluator.evaluate(high_rule, {"cgpa": 7.50}, course_fact=high_course)
        self.assertTrue(res_75.is_matched)
        self.assertTrue(res_75.cgpa_satisfied)

        print("[PASS] Test 3: CGPA academic eligibility and boundaries verified.")

    # =========================================================================
    # 4. Combined AND ('all') Conditions
    # =========================================================================

    def test_4_combined_and_conditions(self):
        """Verifies that all conditions in 'all' must hold for the rule to fire."""
        rule = ProductionRule(
            id=993,
            rule_name="Test_AND_Rule",
            conditions=ConditionGroup(
                all=[
                    RulePredicate("interests", "contains", "Python Programming"),
                    RulePredicate("career_goal", "equals", "Data Scientist"),
                    RulePredicate("cgpa", "greater_than_or_equal", 7.50)
                ]
            ),
            action=RuleAction("recommend_course", 1),
            priority=8
        )

        # All satisfied
        student_perfect = {
            "interests": ["Python Programming", "Machine Learning"],
            "career_goal": "Data Scientist",
            "cgpa": 8.00
        }
        res_ok = RuleEvaluator.evaluate(rule, student_perfect)
        self.assertTrue(res_ok.is_matched)
        self.assertEqual(len(res_ok.matched_conditions), 3)

        # One condition fails (CGPA 7.20 < 7.50)
        student_low_cgpa = {
            "interests": ["Python Programming"],
            "career_goal": "Data Scientist",
            "cgpa": 7.20
        }
        res_low_cgpa = RuleEvaluator.evaluate(rule, student_low_cgpa)
        self.assertFalse(res_low_cgpa.is_matched)
        self.assertTrue(any("cgpa" in f.lower() for f in res_low_cgpa.failed_conditions))

        # Another condition fails (wrong career goal)
        student_wrong_goal = {
            "interests": ["Python Programming"],
            "career_goal": "Web Developer",
            "cgpa": 8.50
        }
        res_wrong_goal = RuleEvaluator.evaluate(rule, student_wrong_goal)
        self.assertFalse(res_wrong_goal.is_matched)
        print("[PASS] Test 4: Combined AND ('all') conditions verified.")

    # =========================================================================
    # 5. OR ('any') Conditions
    # =========================================================================

    def test_5_or_conditions(self):
        """Verifies that satisfying any one condition in 'any' enables rule satisfaction."""
        rule = ProductionRule(
            id=994,
            rule_name="Test_OR_Rule",
            conditions=ConditionGroup(
                all=[
                    RulePredicate("cgpa", "greater_than_or_equal", 2.00)
                ],
                any=[
                    RulePredicate("interests", "contains", "Cloud Infrastructure & DevOps"),
                    RulePredicate("career_goal", "equals", "Cloud Solutions Architect")
                ]
            ),
            action=RuleAction("recommend_course", 4),
            priority=6
        )

        # Matches via interest only
        stu_int = {"cgpa": 3.0, "interests": ["Cloud Infrastructure & DevOps"], "career_goal": "General"}
        self.assertTrue(RuleEvaluator.evaluate(rule, stu_int).is_matched)

        # Matches via career goal only
        stu_goal = {"cgpa": 3.0, "interests": ["General"], "career_goal": "Cloud Solutions Architect"}
        self.assertTrue(RuleEvaluator.evaluate(rule, stu_goal).is_matched)

        # Matches neither -> Rule fails
        stu_neither = {"cgpa": 3.0, "interests": ["Chemistry"], "career_goal": "Doctor"}
        self.assertFalse(RuleEvaluator.evaluate(rule, stu_neither).is_matched)
        print("[PASS] Test 5: OR ('any') conditions verified.")

    # =========================================================================
    # 6. Invalid Operators & Strict Allowlist Validation
    # =========================================================================

    def test_6_invalid_operators_and_fields(self):
        """Verifies that arbitrary operators or unapproved fields are strictly rejected."""
        # Disallowed operator (e.g. eval, regex, exec)
        with self.assertRaises(ValueError) as ctx_op:
            RulePredicate(field="interests", operator="eval", value="__import__('os').system('dir')")
        self.assertIn("not supported", str(ctx_op.exception).lower())

        # Disallowed field
        with self.assertRaises(ValueError) as ctx_field:
            RulePredicate(field="system_password", operator="equals", value="secret")
        self.assertIn("not allowed", str(ctx_field.exception).lower())

        # Validate RuleManager structure audit
        bad_rule = {
            "rule_name": "Exploit_Rule",
            "recommended_course_id": 1,
            "priority": 5,
            "conditions": {
                "all": [{"field": "malicious_field", "operator": "equals", "value": 1}]
            }
        }
        val = RuleManager.validate_rule_structure(bad_rule)
        self.assertFalse(val["is_valid"])
        self.assertTrue(any("not allowed" in e for e in val["errors"]))
        print("[PASS] Test 6: Invalid operators and allowlist validation verified.")

    # =========================================================================
    # 7. Missing Student Information
    # =========================================================================

    def test_7_missing_student_information(self):
        """Verifies that evaluate_rules handles missing/None attributes without exceptions."""
        empty_profile = {}
        res = evaluate_rules(empty_profile, knowledge_base=self.kb)
        self.assertIsInstance(res, dict)
        self.assertIn("recommended_courses", res)
        self.assertIn("rejected_evaluations", res)
        # Should cleanly reject rules requiring CGPA or interests rather than throwing KeyErrors
        self.assertGreater(len(res["rejected_evaluations"]), 0)
        print("[PASS] Test 7: Missing student information handled gracefully.")

    # =========================================================================
    # 8. Inactive Rules
    # =========================================================================

    def test_8_inactive_rules(self):
        """Verifies that inactive rules are filtered out and not evaluated."""
        # Create an inactive rule
        inactive_rule = ProductionRule(
            id=995,
            rule_name="Inactive_Test_Rule",
            conditions=ConditionGroup(
                all=[RulePredicate("cgpa", "greater_than_or_equal", 1.0)]
            ),
            action=RuleAction("recommend_course", 1),
            priority=10,
            is_active=False
        )

        student = {"cgpa": 3.8, "interests": ["Machine Learning"], "career_goal": "Data Scientist"}
        res = evaluate_rules(student, knowledge_base=self.kb, active_rules=[inactive_rule])
        # Inactive rule must not produce recommendations
        self.assertEqual(len(res["recommended_courses"]), 0)
        print("[PASS] Test 8: Inactive rules strictly ignored.")

    # =========================================================================
    # 9. Rule Priority
    # =========================================================================

    def test_9_rule_priority(self):
        """Verifies that rules are evaluated and sorted by priority descending."""
        rule_low = ProductionRule(
            id=901,
            rule_name="Low_Priority_Rule",
            conditions=ConditionGroup(all=[RulePredicate("cgpa", "greater_than_or_equal", 2.0)]),
            action=RuleAction("recommend_course", 4),
            priority=2
        )
        rule_high = ProductionRule(
            id=902,
            rule_name="High_Priority_Rule",
            conditions=ConditionGroup(all=[RulePredicate("cgpa", "greater_than_or_equal", 2.0)]),
            action=RuleAction("recommend_course", 5),
            priority=9
        )

        student = {"cgpa": 3.5, "interests": ["Cloud Infrastructure & DevOps", "Cyber Security"]}
        res = evaluate_rules(student, knowledge_base=self.kb, active_rules=[rule_low, rule_high])

        # High priority course must be listed before low priority
        self.assertGreaterEqual(len(res["recommended_courses"]), 2)
        first_course = res["recommended_courses"][0]
        second_course = res["recommended_courses"][1]
        self.assertGreaterEqual(first_course["priority"], second_course["priority"])
        print("[PASS] Test 9: Rule priority ordering verified.")

    # =========================================================================
    # 10. Duplicate Recommendation Merging
    # =========================================================================

    def test_10_duplicate_recommendation_merging(self):
        """Verifies that multiple rules for the same course are merged without duplication."""
        rule_a = ProductionRule(
            id=910,
            rule_name="Rule_A_ML",
            conditions=ConditionGroup(
                all=[RulePredicate("interests", "contains", "Machine Learning")],
                rationale="Matches machine learning interest."
            ),
            action=RuleAction("recommend_course", 1),
            priority=6
        )
        rule_b = ProductionRule(
            id=911,
            rule_name="Rule_B_ML",
            conditions=ConditionGroup(
                all=[RulePredicate("career_goal", "equals", "Data Scientist")],
                rationale="Aligned with Data Scientist goal."
            ),
            action=RuleAction("recommend_course", 1),
            priority=9
        )

        student = {
            "cgpa": 3.5,
            "interests": ["Machine Learning"],
            "career_goal": "Data Scientist"
        }
        res = evaluate_rules(student, knowledge_base=self.kb, active_rules=[rule_a, rule_b])

        # Must recommend Course 1 exactly once
        ml_recs = [r for r in res["recommended_courses"] if r["course_id"] == 1]
        self.assertEqual(len(ml_recs), 1)

        # Must preserve highest priority (9)
        self.assertEqual(ml_recs[0]["priority"], 9)
        # Must list both fired rules
        self.assertIn("Rule_A_ML", ml_recs[0]["fired_rules"])
        self.assertIn("Rule_B_ML", ml_recs[0]["fired_rules"])
        print("[PASS] Test 10: Duplicate recommendation merging verified.")

    # =========================================================================
    # 11. Prerequisite Checking
    # =========================================================================

    def test_11_prerequisite_checking(self):
        """Verifies course prerequisite verification against student completed courses."""
        course = CourseKnowledgeFact(
            course_id=6,
            course_code="CS-406",
            course_name="Deep Learning",
            description="Deep Learning",
            minimum_cgpa=3.00,
            difficulty_level="Advanced",
            prerequisites_text="Machine Learning"
        )
        rule = ProductionRule(
            id=920,
            rule_name="Rule_DL",
            conditions=ConditionGroup(
                all=[RulePredicate("cgpa", "greater_than_or_equal", 3.00)]
            ),
            action=RuleAction("recommend_course", 6),
            priority=10
        )

        # 1. Student without Machine Learning -> Rejected due to missing prerequisite
        student_missing_prereq = {
            "cgpa": 3.8,
            "completed_courses": ["Database Systems", "Operating Systems"]
        }
        res_fail = RuleEvaluator.evaluate(rule, student_missing_prereq, course_fact=course)
        self.assertFalse(res_fail.is_matched)
        self.assertFalse(res_fail.prerequisites_satisfied)
        self.assertTrue(any("prerequisite" in r.lower() for r in res_fail.reasons))

        # 2. Student with Machine Learning completed -> Passed
        student_with_prereq = {
            "cgpa": 3.8,
            "completed_courses": ["Database Systems", "Machine Learning"]
        }
        res_pass = RuleEvaluator.evaluate(rule, student_with_prereq, course_fact=course)
        self.assertTrue(res_pass.is_matched)
        self.assertTrue(res_pass.prerequisites_satisfied)
        print("[PASS] Test 11: Prerequisite checking verified.")

    # =========================================================================
    # 12. Unauthorized Rule Modifications
    # =========================================================================

    def test_12_unauthorized_rule_modifications(self):
        """Verifies that non-admin and unauthenticated requests cannot add or modify rules."""
        # Unauthenticated POST to /admin/rules/add
        res_add = self.client.post("/admin/rules/add", data={
            "rule_name": "Unauthorized_Rule",
            "recommended_course_id": 1,
            "priority": 5,
            "min_cgpa": "2.00",
            "min_semester": "1",
            "rationale": "Unauthorized injection attempt."
        }, follow_redirects=False)
        # Should redirect to admin login
        self.assertEqual(res_add.status_code, 302)
        self.assertIn("/admin/login", res_add.location)

        # Unauthenticated toggle
        res_toggle = self.client.post("/admin/rules/1/toggle", follow_redirects=False)
        self.assertEqual(res_toggle.status_code, 302)
        self.assertIn("/admin/login", res_toggle.location)
        print("[PASS] Test 12: Unauthorized rule modifications blocked.")

    # =========================================================================
    # 13. All 10 Sample AI Rules Verification
    # =========================================================================

    def test_13_all_sample_rules_verified(self):
        """Verifies all 10 required courses have active production rules in MySQL."""
        required_courses = [
            "Machine Learning",
            "Artificial Intelligence",
            "Deep Learning",
            "Big Data Analytics",
            "Cloud Computing",
            "Cyber Security",
            "Data Mining",
            "Natural Language Processing",
            "Computer Vision",
            "Internet of Things"
        ]

        active_rules = self.rule_mgr.get_all_rules(active_only=True)
        rule_course_names = [r.course_name.strip().lower() for r in active_rules if r.course_name]

        for course in required_courses:
            self.assertIn(
                course.strip().lower(),
                rule_course_names,
                f"Missing production rule for course: {course}"
            )

        # Test evaluation of a sample high-achiever student
        high_achiever = {
            "cgpa": 3.85,
            "semester": 6,
            "interests": ["Deep Learning & Neural Networks", "Machine Learning", "Natural Language Processing"],
            "career_goal": "AI Research Scientist",
            "completed_courses": ["Machine Learning", "Linear Algebra", "Python"]
        }
        eval_res = evaluate_rules(high_achiever, knowledge_base=self.kb)
        self.assertGreater(len(eval_res["recommended_courses"]), 0)

        # High priority Deep Learning should be recommended with explanation
        dl_rec = next((r for r in eval_res["recommended_courses"] if "Deep Learning" in r["course_name"]), None)
        self.assertIsNotNone(dl_rec)
        self.assertIn("was recommended because", dl_rec["explanation"])
        self.assertIn("Deep Learning & Neural Networks", dl_rec["explanation"])
        print("[PASS] Test 13: All 10 sample AI rules successfully verified.")

    # =========================================================================
    # 14. AI Rule Testing Page: Authentication Protection
    # =========================================================================

    def test_14_rule_testing_page_auth_protection(self):
        """Verifies that /student/rule-testing strictly redirects unauthenticated visitors to login."""
        # Clean session
        with self.client.session_transaction() as sess:
            sess.clear()

        res = self.client.get("/student/rule-testing", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.location)
        print("[PASS] Test 14: Rule testing page unauthenticated access blocked.")

    # =========================================================================
    # 15. AI Rule Testing Page: GET Interface Loading
    # =========================================================================

    def test_15_rule_testing_page_get(self):
        """Verifies that authenticated student can load AI Rule Testing page with inputs and button."""
        self.login_student()

        res = self.client.get("/student/rule-testing")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"AI Rule Testing", res.data)
        self.assertIn(b"Cumulative GPA", res.data)
        self.assertIn(b"Technical Domain Interests", res.data)
        self.assertIn(b"Target Career Goal", res.data)
        self.assertIn(b"Evaluate Rules", res.data)
        print("[PASS] Test 15: Rule testing GET interface loaded with form inputs.")

    # =========================================================================
    # 16. AI Rule Testing Page: POST Evaluation Execution
    # =========================================================================

    def test_16_rule_testing_page_post_evaluation(self):
        """Verifies rule evaluation execution via POST form submission and results display."""
        self.login_student()

        payload = {
            "cgpa": "3.50",
            "interests": ["Machine Learning", "Python Programming"],
            "career_goal": "Data Scientist"
        }

        res = self.client.post("/student/rule-testing", data=payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify presence of all required result sections
        self.assertIn(b"Matched Rules", res.data)
        self.assertIn(b"Failed Rules", res.data)
        self.assertIn(b"Recommended Courses", res.data)
        self.assertIn(b"Rejected Courses", res.data)
        self.assertIn(b"Reasoning Explanation", res.data)

        # Verify actual content from firing Rule_Machine_Learning_Core
        self.assertIn(b"Machine Learning", res.data)
        self.assertIn(b"CS-401", res.data)
        self.assertIn(b"was recommended because", res.data)
        print("[PASS] Test 16: Rule testing POST evaluation displays matched/failed rules and reasoning.")


if __name__ == "__main__":
    unittest.main()
