import os
import psycopg
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment or use default local database"""
    if os.getenv('DATABASE_URL'):
        # Railway provides DATABASE_URL in the format: postgres://user:pass@host:5432/dbname
        return os.getenv('DATABASE_URL')
    return "dbname=rally user=rossfreedman"

@contextmanager
def get_db():
    """Get database connection"""
    conn = psycopg.connect(get_database_url())
    try:
        yield conn
    finally:
        conn.close() 