import os
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def get_db_url():
    """Get database URL from environment or use default"""
    url = os.getenv('DATABASE_URL', 'postgresql://localhost/rally')
    # Handle Railway's postgres:// URLs
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url

def parse_db_url(url):
    """Parse database URL into connection parameters"""
    parsed = urlparse(url)
    return {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'sslmode': 'require' if 'railway.app' in (parsed.hostname or '') else 'prefer'
    }

@contextmanager
def get_db():
    """Get database connection"""
    db_params = parse_db_url(get_db_url())
    try:
        conn = psycopg2.connect(**db_params)
        yield conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        print(f"Connection params (excluding password): {dict(dbname=db_params['dbname'], user=db_params['user'], host=db_params['host'], port=db_params['port'], sslmode=db_params['sslmode'])}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def execute_query(query, params=None):
    """Execute a query and return all results"""
    with get_db() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query, params or {})
            results = cursor.fetchall()
            return [dict(row) for row in results]

def execute_query_one(query, params=None):
    """Execute a query and return one result"""
    with get_db() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query, params or {})
            result = cursor.fetchone()
            return dict(result) if result else None

def execute_update(query, params=None):
    """Execute an update query and return success status"""
    with get_db() as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or {})
                conn.commit()
                return True
        except Exception as e:
            print(f"Error executing update: {str(e)}")
            conn.rollback()
            return False 