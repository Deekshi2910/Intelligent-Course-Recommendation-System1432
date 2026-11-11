"""
Application Configuration Module
Loads configuration settings from environment variables using python-dotenv.
"""

import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()


class Config:
    """Base Configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    
    # Security & Session Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Database Settings
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME", "intelligent_course_recommendation")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    @classmethod
    def get_db_config(cls):
        """Return database connection parameters dictionary."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "database": cls.DB_NAME,
        }


class DevelopmentConfig(Config):
    """Development Configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production Configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True



# Configuration mapping dictionary
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
