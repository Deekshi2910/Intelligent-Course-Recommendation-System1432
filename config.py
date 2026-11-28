"""
Application Configuration Module
Loads configuration settings from environment variables using python-dotenv.
Supports local MySQL, TiDB Cloud Serverless, and cloud deployment platforms (Render, Heroku, etc.).
"""

import os
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()


def parse_database_url(url_str):
    """
    Parses a database URL (e.g. mysql://user:pass@host:port/database)
    and returns a normalized connection parameters dictionary.
    """
    if not url_str or not isinstance(url_str, str):
        return {}
    
    # Strip optional scheme prefix variations like mysql+pymysql://
    clean_url = url_str.strip()
    if clean_url.startswith("mysql+"):
        clean_url = "mysql" + clean_url[clean_url.find("://"):]
        
    parsed = urlparse(clean_url)
    if not parsed.hostname:
        return {}

    return {
        "host": parsed.hostname,
        "port": parsed.port or (4000 if parsed.hostname and "tidbcloud" in parsed.hostname.lower() else 3306),
        "user": unquote(parsed.username) if parsed.username else None,
        "password": unquote(parsed.password) if parsed.password else None,
        "database": parsed.path.lstrip("/"),
    }


class Config:
    """Base Configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    
    # Security & Session Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") in ("1", "true", "True")
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Database Settings (supports DATABASE_URL, TIDB_*, or DB_*)
    _url_params = parse_database_url(os.getenv("DATABASE_URL", ""))

    DB_HOST = _url_params.get("host") or os.getenv("TIDB_HOST") or os.getenv("DB_HOST", "localhost")
    DB_PORT = _url_params.get("port") or int(os.getenv("TIDB_PORT") or os.getenv("DB_PORT", 4000 if os.getenv("TIDB_HOST") else 3306))
    DB_NAME = _url_params.get("database") or os.getenv("TIDB_DB_NAME") or os.getenv("DB_NAME", "intelligent_course_recommendation")
    DB_USER = _url_params.get("user") or os.getenv("TIDB_USER") or os.getenv("DB_USER", "root")
    DB_PASSWORD = _url_params.get("password") or os.getenv("TIDB_PASSWORD") or os.getenv("DB_PASSWORD", "")

    # SSL / TLS Settings for TiDB Cloud & Cloud MySQL
    DB_SSL_MODE = os.getenv("DB_SSL_MODE", "AUTO").upper()  # AUTO, REQUIRED, DISABLED
    DB_SSL_CA = os.getenv("DB_SSL_CA", "")
    DB_SSL_VERIFY_CERT = os.getenv("DB_SSL_VERIFY_CERT", "1").lower() in ("1", "true", "yes")
    DB_SSL_VERIFY_IDENTITY = os.getenv("DB_SSL_VERIFY_IDENTITY", "1").lower() in ("1", "true", "yes")

    @classmethod
    def get_db_config(cls):
        """
        Return database connection parameters dictionary including resolved SSL settings.
        Dynamically evaluates environment variables so runtime/injected changes are respected.
        """
        url_params = parse_database_url(os.getenv("DATABASE_URL", ""))

        host = url_params.get("host") or os.getenv("TIDB_HOST") or os.getenv("DB_HOST", cls.DB_HOST)
        port = url_params.get("port") or int(os.getenv("TIDB_PORT") or os.getenv("DB_PORT", cls.DB_PORT))
        database = url_params.get("database") or os.getenv("TIDB_DB_NAME") or os.getenv("DB_NAME", cls.DB_NAME)
        user = url_params.get("user") or os.getenv("TIDB_USER") or os.getenv("DB_USER", cls.DB_USER)
        password = url_params.get("password") or os.getenv("TIDB_PASSWORD") or os.getenv("DB_PASSWORD", cls.DB_PASSWORD)

        ssl_mode = os.getenv("DB_SSL_MODE", cls.DB_SSL_MODE).upper()
        ssl_ca = os.getenv("DB_SSL_CA", cls.DB_SSL_CA)
        ssl_verify_cert = os.getenv("DB_SSL_VERIFY_CERT", str(cls.DB_SSL_VERIFY_CERT)).lower() in ("1", "true", "yes")
        ssl_verify_identity = os.getenv("DB_SSL_VERIFY_IDENTITY", str(cls.DB_SSL_VERIFY_IDENTITY)).lower() in ("1", "true", "yes")

        # Determine whether SSL is required
        ssl_required = False
        if ssl_mode in ("REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"):
            ssl_required = True
        elif ssl_mode == "DISABLED":
            ssl_required = False
        elif ssl_mode == "AUTO":
            # Auto-detect TiDB Cloud or non-local hosts
            is_local = str(host).lower() in ("localhost", "127.0.0.1", "::1", "none")
            is_tidb = "tidbcloud.com" in str(host).lower() or port == 4000 or bool(os.getenv("TIDB_HOST"))
            if is_tidb or (not is_local and bool(ssl_ca)):
                ssl_required = True
            else:
                ssl_required = False

        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "ssl_mode": ssl_mode,
            "ssl_required": ssl_required,
            "ssl_ca": ssl_ca,
            "ssl_verify_cert": ssl_verify_cert,
            "ssl_verify_identity": ssl_verify_identity,
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
