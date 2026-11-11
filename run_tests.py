"""
================================================================================
Intelligent Course Recommendation System - Automated Test Runner
================================================================================
Executes the comprehensive automated test suite across all subsystems:
- Authentication & RBAC (tests/test_auth.py)
- Student Profile & Academic Management (tests/test_student.py)
- Admin Dashboard & Rule Operations (tests/test_admin.py)
- AI Knowledge Base & Validation (tests/test_knowledge_base.py)
- Production Rule Engine (tests/test_rule_engine.py)
- Default Reasoning & Fallbacks (tests/test_default_reasoning.py)
- Forward Chaining & Conflict Resolution (tests/test_forward_chaining.py)
- AI Inference Engine & Scoring (tests/test_inference_engine.py)
- End-to-End Recommendations (tests/test_recommendations.py)
================================================================================
"""

import sys
import os
import time
import pytest

def run_suite():
    print("=" * 80)
    print(" INTELLIGENT COURSE RECOMMENDATION SYSTEM - AUTOMATED TEST SUITE")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Executable: {sys.executable}")
    print(f"Working Directory: {os.getcwd()}")
    print("-" * 80)

    test_dir = os.path.join(os.path.dirname(__file__), "tests")
    exit_code = pytest.main([
        "-v",
        "--tb=short",
        test_dir
    ])

    print("-" * 80)
    if exit_code == 0:
        print(">>> ALL TESTS COMPLETED SUCCESSFULLY (100% PASS RATE)")
    else:
        print(f">>> TEST SUITE COMPLETED WITH CODE: {exit_code}")
    print("=" * 80)
    return exit_code

if __name__ == "__main__":
    sys.exit(run_suite())
