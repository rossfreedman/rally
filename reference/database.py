import os
import sqlite3
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_path():
    """Get database path"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')

@contextmanager
def get_db():
    """Get database connection"""
    conn = sqlite3.connect(get_database_path())
    try:
        yield conn
    finally:
        conn.close() 