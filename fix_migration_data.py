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

def format_timestamp(ts):
    """Format timestamp consistently"""
    if pd.isna(ts) or ts is None:
        return None
    if isinstance(ts, str):
        try:
            return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
    return ts

def fix_users_table(sqlite_cursor, pg_cursor):
    """Fix data in users table"""
    logger.info("Fixing users table...")
    
    # Get data from SQLite
    sqlite_cursor.execute("SELECT * FROM users")
    columns = [description[0] for description in sqlite_cursor.description]
    users = pd.DataFrame(sqlite_cursor.fetchall(), columns=columns)
    
    # Update each user in PostgreSQL
    for _, user in users.iterrows():
        pg_cursor.execute("""
            UPDATE users SET 
                created_at = %(created_at)s,
                last_login = %(last_login)s,
                club_automation_password = %(club_automation_password)s,
                club_id = %(club_id)s
            WHERE email = %(email)s
        """, {
            'created_at': format_timestamp(user['created_at']),
            'last_login': format_timestamp(user['last_login']),
            'club_automation_password': user['club_automation_password'],
            'club_id': user['club_id'] if pd.notna(user['club_id']) else None,
            'email': user['email']
        })
    
    logger.info("✅ Users table fixed")

def fix_user_instructions_table(sqlite_cursor, pg_cursor):
    """Fix data in user_instructions table"""
    logger.info("Fixing user_instructions table...")
    
    # Get data from SQLite
    sqlite_cursor.execute("SELECT * FROM user_instructions")
    columns = [description[0] for description in sqlite_cursor.description]
    instructions = pd.DataFrame(sqlite_cursor.fetchall(), columns=columns)
    
    # Clear existing data in PostgreSQL
    pg_cursor.execute("TRUNCATE TABLE user_instructions RESTART IDENTITY")
    
    # Insert correct data
    for _, instruction in instructions.iterrows():
        # Handle series_id/series_name correctly
        series_id = instruction['series_id']
        series_name = None
        if isinstance(series_id, str):  # If series_id contains a name
            series_name = series_id
            series_id = None
        
        # Handle team_id/team_name correctly
        team_id = instruction['team_id']
        team_name = None
        if isinstance(team_id, str):  # If team_id contains a string
            team_name = team_id
            team_id = None
        elif pd.isna(team_id):
            team_id = None
        
        pg_cursor.execute("""
            INSERT INTO user_instructions (
                user_email, instruction, created_at, is_active, team_id,
                series_id, series_name, team_name
            ) VALUES (
                %(user_email)s, %(instruction)s, %(created_at)s, %(is_active)s, %(team_id)s,
                %(series_id)s, %(series_name)s, %(team_name)s
            )
        """, {
            'user_email': instruction['user_email'],
            'instruction': instruction['instruction'],
            'created_at': format_timestamp(instruction['created_at']),
            'is_active': bool(instruction['is_active']),
            'team_id': team_id,
            'series_id': series_id,
            'series_name': series_name,
            'team_name': team_name
        })
    
    logger.info("✅ User instructions table fixed")

def fix_player_availability_table(sqlite_cursor, pg_cursor):
    """Fix data in player_availability table"""
    logger.info("Fixing player_availability table...")
    
    # Get data from SQLite
    sqlite_cursor.execute("SELECT * FROM player_availability")
    columns = [description[0] for description in sqlite_cursor.description]
    availability = pd.DataFrame(sqlite_cursor.fetchall(), columns=columns)
    
    # Update each record in PostgreSQL
    for _, record in availability.iterrows():
        pg_cursor.execute("""
            UPDATE player_availability SET 
                updated_at = %(updated_at)s,
                is_available = %(is_available)s
            WHERE player_name = %(player_name)s 
            AND match_date = %(match_date)s 
            AND series = %(series)s
        """, {
            'updated_at': format_timestamp(record['updated_at']),
            'is_available': bool(record['is_available']),
            'player_name': record['player_name'],
            'match_date': record['match_date'],
            'series': record['series']
        })
    
    logger.info("✅ Player availability table fixed")

def fix_user_activity_logs_table(sqlite_cursor, pg_cursor):
    """Fix data in user_activity_logs table"""
    logger.info("Fixing user_activity_logs table...")
    
    # Get data from SQLite
    sqlite_cursor.execute("SELECT * FROM user_activity_logs")
    columns = [description[0] for description in sqlite_cursor.description]
    logs = pd.DataFrame(sqlite_cursor.fetchall(), columns=columns)
    
    # Clear existing data in PostgreSQL
    pg_cursor.execute("TRUNCATE TABLE user_activity_logs RESTART IDENTITY")
    
    # Insert correct data
    for _, log in logs.iterrows():
        pg_cursor.execute("""
            INSERT INTO user_activity_logs (
                user_email, activity_type, page, action, details, 
                ip_address, timestamp
            ) VALUES (
                %(user_email)s, %(activity_type)s, %(page)s, %(action)s, 
                %(details)s, %(ip_address)s, %(timestamp)s
            )
        """, {
            'user_email': log['user_email'],
            'activity_type': log['activity_type'],
            'page': log['page'],
            'action': log['action'],
            'details': log['details'],
            'ip_address': log['ip_address'],
            'timestamp': format_timestamp(log['timestamp'])
        })
    
    logger.info("✅ User activity logs table fixed")

def fix_migration_data():
    """Fix all data inconsistencies between SQLite and PostgreSQL"""
    logger.info("Starting data fix process...")
    
    try:
        # Connect to both databases
        sqlite_conn = get_sqlite_connection()
        sqlite_cursor = sqlite_conn.cursor()
        
        with get_db() as pg_conn:
            pg_cursor = pg_conn.cursor(cursor_factory=RealDictCursor)
            
            # Fix each table
            fix_users_table(sqlite_cursor, pg_cursor)
            fix_user_instructions_table(sqlite_cursor, pg_cursor)
            fix_player_availability_table(sqlite_cursor, pg_cursor)
            fix_user_activity_logs_table(sqlite_cursor, pg_cursor)
            
            # Commit all changes
            pg_conn.commit()
            
            logger.info("✅ All data fixes completed successfully!")
    
    except Exception as e:
        logger.error(f"Error during data fix: {str(e)}")
        raise
    finally:
        sqlite_conn.close()

if __name__ == '__main__':
    fix_migration_data() 