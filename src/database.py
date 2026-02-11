# Database connection utilities
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import logging
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

logger = logging.getLogger(__name__)

# Connection pool
_connection_pool = None

def get_connection_pool():
    """Get or create the connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    return _connection_pool

@contextmanager
def get_db_connection():
    """
    Context manager for database connections
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scenario")
            results = cursor.fetchall()
    """
    pool = get_connection_pool()
    conn = pool.getconn()
    
    try:
        yield conn
    finally:
        pool.putconn(conn)

@contextmanager
def get_db_cursor(commit=False):
    """
    Context manager for database cursor with automatic commit/rollback
    
    Args:
        commit: If True, commits on success. If False, rolls back (for read-only)
    
    Usage:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("INSERT INTO scenario (...) VALUES (...)")
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
            else:
                conn.rollback()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()

def execute_query(query, params=None, fetch=True):
    """
    Execute a query and return results
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch: If True, returns fetchall() results
    
    Returns:
        List of tuples (if fetch=True) or cursor.rowcount
    """
    with get_db_cursor(commit=False) as cursor:
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        return cursor.rowcount

def execute_insert(query, params=None, return_id=True):
    """
    Execute an INSERT query and optionally return the generated ID
    
    Args:
        query: SQL INSERT query
        params: Query parameters
        return_id: If True, returns the generated ID (assumes RETURNING id clause)
    
    Returns:
        Generated ID or None
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(query, params)
        if return_id:
            result = cursor.fetchone()
            return result[0] if result else None
        return cursor.rowcount

def execute_update(query, params=None):
    """
    Execute an UPDATE/DELETE query
    
    Returns:
        Number of affected rows
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(query, params)
        return cursor.rowcount

def execute_many(query, params_list):
    """
    Execute a query multiple times with different parameters
    
    Args:
        query: SQL query
        params_list: List of parameter tuples
    
    Returns:
        Number of affected rows
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.executemany(query, params_list)
        return cursor.rowcount

def test_connection():
    """Test database connection and return status"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            return True, version
    except Exception as e:
        return False, str(e)

def close_pool():
    """Close all connections in the pool"""
    global _connection_pool
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Database connection pool closed")
