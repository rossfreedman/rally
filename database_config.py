import os
from dotenv import load_dotenv
import psycopg2
from contextlib import contextmanager
from urllib.parse import urlparse

load_dotenv()

def get_db_url():
    """Get database URL from environment or use default"""
    return os.getenv('DATABASE_URL', 'postgresql://localhost/rally')

def parse_db_url(url):
    """Parse database URL into connection parameters"""
    parsed = urlparse(url)
    return {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432
    }

@contextmanager
def get_db():
    """Get database connection"""
    db_params = parse_db_url(get_db_url())
    conn = psycopg2.connect(**db_params)
    try:
        yield conn
    finally:
        conn.close() 