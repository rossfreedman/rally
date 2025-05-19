import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from database_config import get_db

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
        except Exception:
            conn.rollback()
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
    with get_db_cursor(commit=commit) as cursor:
        cursor.execute(query, params)
        if cursor.description:  # If the query returns results
            return cursor.fetchall()
        return None

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
    with get_db_cursor(commit=commit) as cursor:
        cursor.execute(query, params)
        if cursor.description:  # If the query returns results
            return cursor.fetchone()
        return None

def execute_many(query, params_list, commit=True):
    """
    Execute the same query with different parameters for batch operations.
    
    Args:
        query (str): The SQL query to execute
        params_list (list): List of parameter tuples/dicts
        commit (bool): Whether to commit the transaction
    """
    with get_db_cursor(commit=commit) as cursor:
        cursor.executemany(query, params_list) 