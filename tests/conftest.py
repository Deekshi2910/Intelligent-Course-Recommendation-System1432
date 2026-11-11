"""
Pytest Configuration and Fixtures
Ensures project root is added to sys.path and provides test client fixtures.
"""

import os
import sys

# Add project root directory to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from app import app
from database.db_connection import get_db_cursor
from ai_engine.knowledge_base import KnowledgeBase


@pytest.fixture(scope="session")
def flask_app():
    """Provides test Flask application."""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture(scope="function")
def client(flask_app):
    """Provides test client."""
    return flask_app.test_client()


@pytest.fixture(scope="session")
def shared_kb():
    """Provides a singleton KnowledgeBase for testing."""
    return KnowledgeBase()
