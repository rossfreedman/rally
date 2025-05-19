import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from database_config import get_db
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_sqlite_connection():
    """Get SQLite database connection"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
    return sqlite3.connect(db_path)

def get_table_names(sqlite_cursor):
    """Get all table names from SQLite database"""
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    # Skip SQLite-specific tables
    return [table for table in tables if not table.startswith('sqlite_')]

def compare_row_counts(sqlite_cursor, pg_cursor, table_name):
    """Compare row counts between SQLite and PostgreSQL tables"""
    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    sqlite_count = sqlite_cursor.fetchone()[0]
    
    pg_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
    pg_count = pg_cursor.fetchone()['count']
    
    return sqlite_count, pg_count

def compare_table_data(sqlite_cursor, pg_cursor, table_name):
    """Compare actual data between SQLite and PostgreSQL tables"""
    # Get column names from SQLite
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in sqlite_cursor.fetchall()]
    
    # Add PostgreSQL-specific columns for user_instructions
    if table_name == 'user_instructions':
        columns.append('team_name')
    
    # Fetch all data from both databases
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    sqlite_data = pd.DataFrame(sqlite_cursor.fetchall(), columns=columns[:-1] if table_name == 'user_instructions' else columns)
    
    pg_cursor.execute(f"SELECT * FROM {table_name}")
    pg_data = pd.DataFrame(pg_cursor.fetchall(), columns=columns)
    
    # Convert boolean columns in SQLite data (0/1) to match PostgreSQL (True/False)
    bool_columns = sqlite_data.select_dtypes(include=['int64']).columns
    for col in bool_columns:
        if set(sqlite_data[col].unique()).issubset({0, 1}):
            sqlite_data[col] = sqlite_data[col].astype(bool)
    
    # Handle timestamp columns
    timestamp_columns = ['created_at', 'updated_at', 'last_login', 'timestamp']
    for col in timestamp_columns:
        if col in sqlite_data.columns:
            # Convert timestamps to datetime objects for consistent comparison
            sqlite_data[col] = pd.to_datetime(sqlite_data[col], utc=True)
            pg_data[col] = pd.to_datetime(pg_data[col], utc=True)
            # Round to seconds to avoid microsecond differences
            sqlite_data[col] = sqlite_data[col].dt.floor('s')
            pg_data[col] = pg_data[col].dt.floor('s')
    
    # Handle NULL values consistently
    for col in sqlite_data.columns:
        # Convert empty strings to None/NULL
        sqlite_data[col] = sqlite_data[col].replace('', None)
        pg_data[col] = pg_data[col].replace('', None)
        # Convert NaN to None/NULL
        sqlite_data[col] = sqlite_data[col].replace({pd.NA: None})
        pg_data[col] = pg_data[col].replace({pd.NA: None})
        # Convert string 'None' to None
        sqlite_data[col] = sqlite_data[col].replace('None', None)
        pg_data[col] = pg_data[col].replace('None', None)
    
    # Special handling for user_instructions table
    if table_name == 'user_instructions':
        # Copy team_id to team_name in SQLite data if it's a string
        sqlite_data['team_name'] = None
        for idx in sqlite_data.index:
            if isinstance(sqlite_data.loc[idx, 'team_id'], str):
                sqlite_data.loc[idx, 'team_name'] = sqlite_data.loc[idx, 'team_id']
                sqlite_data.loc[idx, 'team_id'] = None
    
    # Sort both dataframes by all columns except id
    sort_columns = [col for col in columns if col != 'id']
    if sort_columns:
        sqlite_data = sqlite_data.sort_values(by=sort_columns).reset_index(drop=True)
        pg_data = pg_data.sort_values(by=sort_columns).reset_index(drop=True)
    
    # Compare dataframes
    if sqlite_data.equals(pg_data):
        return True, None
    else:
        # Find differences
        differences = []
        for col in columns:
            if col == 'id':  # Skip id column comparison
                continue
            if col not in sqlite_data.columns:  # Skip columns that don't exist in SQLite
                continue
            if not sqlite_data[col].equals(pg_data[col]):
                mismatch_indices = (sqlite_data[col] != pg_data[col])
                samples = []
                for idx in mismatch_indices[mismatch_indices].index[:3]:  # Show up to 3 examples
                    if (pd.isna(sqlite_data.loc[idx, col]) and pd.isna(pg_data.loc[idx, col])):
                        continue  # Skip if both are NULL/NaN
                    samples.append({
                        'index': idx,
                        'sqlite_value': sqlite_data.loc[idx, col],
                        'pg_value': pg_data.loc[idx, col]
                    })
                if samples:  # Only add to differences if there are actual differences
                    differences.append({
                        'column': col,
                        'samples': samples
                    })
        return False, differences if differences else None

def verify_migration():
    """Verify data migration from SQLite to PostgreSQL"""
    logger.info("Starting migration verification...")
    
    verification_results = {
        'tables_checked': 0,
        'tables_matched': 0,
        'tables_mismatched': 0,
        'details': []
    }
    
    try:
        # Connect to both databases
        sqlite_conn = get_sqlite_connection()
        sqlite_cursor = sqlite_conn.cursor()
        
        with get_db() as pg_conn:
            pg_cursor = pg_conn.cursor(cursor_factory=RealDictCursor)
            
            # Get all tables from SQLite
            tables = get_table_names(sqlite_cursor)
            
            for table_name in tables:
                logger.info(f"Verifying table: {table_name}")
                verification_results['tables_checked'] += 1
                
                # Compare row counts
                sqlite_count, pg_count = compare_row_counts(sqlite_cursor, pg_cursor, table_name)
                
                table_result = {
                    'table_name': table_name,
                    'sqlite_count': sqlite_count,
                    'pg_count': pg_count,
                    'counts_match': sqlite_count == pg_count,
                    'data_matches': None,
                    'differences': None
                }
                
                if sqlite_count == pg_count:
                    # Compare actual data
                    data_matches, differences = compare_table_data(sqlite_cursor, pg_cursor, table_name)
                    table_result['data_matches'] = data_matches
                    table_result['differences'] = differences
                    
                    if data_matches:
                        verification_results['tables_matched'] += 1
                        logger.info(f"✅ Table {table_name} verified successfully")
                    else:
                        verification_results['tables_mismatched'] += 1
                        logger.warning(f"❌ Data mismatch in table {table_name}")
                        logger.warning(f"Differences: {differences}")
                else:
                    verification_results['tables_mismatched'] += 1
                    logger.warning(f"❌ Row count mismatch in table {table_name}")
                    logger.warning(f"SQLite: {sqlite_count}, PostgreSQL: {pg_count}")
                
                verification_results['details'].append(table_result)
    
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")
        raise
    finally:
        sqlite_conn.close()
    
    # Print summary
    logger.info("\n=== Verification Summary ===")
    logger.info(f"Tables checked: {verification_results['tables_checked']}")
    logger.info(f"Tables matched: {verification_results['tables_matched']}")
    logger.info(f"Tables mismatched: {verification_results['tables_mismatched']}")
    
    return verification_results

if __name__ == '__main__':
    verify_migration() 