"""
Database Connection Manager
Intelligent Course Recommendation System
Provides reusable, robust, and secure MySQL connections via mysql-connector-python.
Supports local MySQL and cloud databases (TiDB Cloud Serverless, PlanetScale, etc.).
"""

import os
import logging
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error, errorcode
from config import Config

logger = logging.getLogger(__name__)


def _resolve_ca_bundle(custom_ca=None):
    """
    Locates the system or Python CA certificates bundle for TLS verification.
    Checks user-specified path, standard Linux paths, or falls back to certifi.
    """
    if custom_ca and os.path.isfile(custom_ca):
        return custom_ca

    # Standard Linux CA bundle paths (e.g., Render Debian/Ubuntu base images)
    common_linux_paths = [
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/etc/ssl/ca-bundle.pem",
    ]
    for p in common_linux_paths:
        if os.path.isfile(p):
            return p

    try:
        import certifi
        return certifi.where()
    except ImportError:
        pass

    return None


def get_connection_config(database_name=None):
    """
    Build connection configuration dictionary from Config.
    Never exposes or logs the password.
    """
    cfg = Config.get_db_config()
    if database_name is not None:
        cfg["database"] = database_name
    return cfg


def get_db_connection(database_name=None):
    """
    Establish and return a MySQL database connection.
    Handles SSL/TLS encryption for TiDB Cloud Serverless and cloud providers.
    Handles common connection errors gracefully without printing passwords.
    
    :param database_name: Optional override for the target database.
    :return: mysql.connector.connection.MySQLConnection object or None.
    """
    config = get_connection_config(database_name)
    try:
        conn_params = {
            "host": config["host"],
            "port": config["port"],
            "user": config["user"],
            "password": config["password"],
            "database": config.get("database"),
            "autocommit": False,
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
        }

        # Configure SSL / TLS settings for TiDB Cloud or remote hosts
        if config.get("ssl_required"):
            conn_params["ssl_disabled"] = False
            conn_params["ssl_verify_cert"] = config.get("ssl_verify_cert", True)
            conn_params["ssl_verify_identity"] = config.get("ssl_verify_identity", True)
            ca_bundle = _resolve_ca_bundle(config.get("ssl_ca"))
            if ca_bundle:
                conn_params["ssl_ca"] = ca_bundle
        else:
            conn_params["ssl_disabled"] = True

        connection = mysql.connector.connect(**conn_params)
        return connection
    except Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logger.error("Database connection failed: Invalid username or password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            logger.error(f"Database connection failed: Database '{config.get('database')}' does not exist.")
        elif err.errno == errorcode.CR_CONN_HOST_ERROR:
            logger.error(f"Database connection failed: Could not connect to host '{config['host']}:{config['port']}'.")
        else:
            logger.error(f"Database connection error [{err.errno}]: {err.msg}")
        raise


@contextmanager
def get_db_cursor(commit=False, dictionary=True, database_name=None):
    """
    Context manager for safe database cursor handling.
    Automatically handles transaction commit, rollback on error, and resource cleanup.
    
    Usage:
        with get_db_cursor(commit=True) as (cursor, conn):
            cursor.execute("INSERT INTO users ...", (val1, val2))
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection(database_name)
        cursor = connection.cursor(dictionary=dictionary)
        yield cursor, connection
        if commit:
            connection.commit()
    except Exception as exc:
        if connection and connection.is_connected():
            connection.rollback()
        logger.error(f"Database transaction error: {str(exc)}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def test_connection(database_name=None):
    """
    Test connectivity to the MySQL server and optionally the specific database.
    Returns (success: bool, message: str).
    """
    try:
        conn = get_db_connection(database_name)
        if conn.is_connected():
            server_info = conn.server_info if hasattr(conn, "server_info") else conn.get_server_info()
            conn.close()
            return True, f"Connected successfully to MySQL server (Version: {server_info})."
        return False, "Connection object created but not active."
    except Error as err:
        return False, f"Connection failed (Errno {err.errno}): {err.msg}"
