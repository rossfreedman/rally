import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from database_config import get_db
import logging

logger = logging.getLogger(__name__)

@contextmanager
def get_db_cursor(commit=True):
    """
    Context manager that provides a database cursor and handles commits/rollbacks.
    
    Args:
        commit (bool): Whether to automatically commit the transaction on success.
                      Set to False if you want to handle transactions manually.
    
    Yields:
        cursor: A database cursor that returns results as dictionaries
    """
    with get_db() as conn:
        # Use RealDictCursor to return results as dictionaries
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            logger.error(f"Query failed: {getattr(cursor, 'query', 'No query available')}")
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"Non-database error: {str(e)}")
            raise
        finally:
            cursor.close()

def execute_query(query, params=None, commit=True):
    """
    Execute a query and return all results.
    
    Args:
        query (str): The SQL query to execute
        params (tuple|dict): Query parameters
        commit (bool): Whether to commit the transaction
    
    Returns:
        list: Query results as a list of dictionaries
    """
    try:
        with get_db_cursor(commit=commit) as cursor:
            cursor.execute(query, params)
            if cursor.description:  # If the query returns results
                return cursor.fetchall()
            return None
    except Exception as e:
        logger.error(f"Query execution failed: {query}")
        logger.error(f"Parameters: {params}")
        raise

def execute_query_one(query, params=None, commit=True):
    """
    Execute a query and return the first result.
    
    Args:
        query (str): The SQL query to execute
        params (tuple|dict): Query parameters
        commit (bool): Whether to commit the transaction
    
    Returns:
        dict|None: First row of results as a dictionary, or None if no results
    """
    try:
        with get_db_cursor(commit=commit) as cursor:
            cursor.execute(query, params)
            if cursor.description:  # If the query returns results
                return cursor.fetchone()
            return None
    except Exception as e:
        logger.error(f"Query execution failed: {query}")
        logger.error(f"Parameters: {params}")
        raise

def execute_update(query, params=None):
    """
    Execute an update/insert/delete query and return success status.
    
    Args:
        query (str): The SQL query to execute
        params (tuple|dict): Query parameters
    
    Returns:
        bool: True if the update was successful
    """
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, params)
            return True
    except Exception as e:
        logger.error(f"Update failed: {query}")
        logger.error(f"Parameters: {params}")
        raise

def execute_many(query, params_list, commit=True):
    """
    Execute the same query with different parameters for batch operations.
    
    Args:
        query (str): The SQL query to execute
        params_list (list): List of parameter tuples/dicts
        commit (bool): Whether to commit the transaction
    """
    try:
        with get_db_cursor(commit=commit) as cursor:
            cursor.executemany(query, params_list)
    except Exception as e:
        logger.error(f"Batch execution failed: {query}")
        logger.error(f"First set of parameters: {params_list[0] if params_list else None}")
        raise 