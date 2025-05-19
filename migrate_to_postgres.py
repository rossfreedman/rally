import sqlite3
import psycopg2
import os
from database_config import get_db_url, parse_db_url
from datetime import datetime

def get_sqlite_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
    return sqlite3.connect(db_path)

def safe_timestamp(value):
    """Convert various timestamp formats to PostgreSQL compatible timestamp"""
    if not value:
        return None
    try:
        # Try parsing as datetime
        return datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            # Try parsing as date
            return datetime.strptime(str(value), '%Y-%m-%d')
        except ValueError:
            # If all parsing fails, return None
            return None

def safe_integer(value):
    """Convert value to integer safely"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_boolean(value):
    """Convert integer to boolean safely"""
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return None

def create_postgres_schema(pg_conn):
    with pg_conn.cursor() as cursor:
        # Create clubs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clubs (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        ''')

        # Create series table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS series (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        ''')

        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            club_id INTEGER REFERENCES clubs(id),
            series_id INTEGER REFERENCES series(id),
            club_automation_password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        ''')

        # Create user_instructions table with corrected schema
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_instructions (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            instruction TEXT NOT NULL,
            series_id INTEGER,
            team_id INTEGER,
            created_at TIMESTAMP,
            series_name TEXT
        )
        ''')

        # Create player_availability table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_availability (
            id SERIAL PRIMARY KEY,
            player_name TEXT NOT NULL,
            match_date TEXT NOT NULL,
            is_available BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            series TEXT NOT NULL,
            UNIQUE(player_name, match_date, series)
        )
        ''')

        # Create user_activity_logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity_logs (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            page TEXT,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_instructions_email ON user_instructions(user_email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_availability ON player_availability(player_name, match_date, series)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_logs_user_email ON user_activity_logs(user_email, timestamp)')

def migrate_data(sqlite_conn, pg_conn):
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    try:
        # Migrate clubs
        print("Migrating clubs...")
        sqlite_cursor.execute('SELECT * FROM clubs')
        clubs = sqlite_cursor.fetchall()
        for club in clubs:
            pg_cursor.execute('INSERT INTO clubs (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING', club)
        pg_conn.commit()

        # Migrate series
        print("Migrating series...")
        sqlite_cursor.execute('SELECT * FROM series')
        series = sqlite_cursor.fetchall()
        for s in series:
            pg_cursor.execute('INSERT INTO series (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING', s)
        pg_conn.commit()

        # Migrate users
        print("Migrating users...")
        sqlite_cursor.execute('SELECT * FROM users')
        users = sqlite_cursor.fetchall()
        for user in users:
            # Convert timestamps and ensure integers
            user_data = list(user)
            user_data[5] = safe_integer(user_data[5])  # club_id
            user_data[6] = safe_integer(user_data[6])  # series_id
            user_data[8] = safe_timestamp(user_data[8])  # created_at
            user_data[9] = safe_timestamp(user_data[9])  # last_login
            
            pg_cursor.execute('''
            INSERT INTO users (id, email, password_hash, first_name, last_name, club_id, series_id, 
                             club_automation_password, created_at, last_login)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            ''', tuple(user_data))
        pg_conn.commit()

        # Migrate user_instructions with corrected schema
        print("Migrating user instructions...")
        sqlite_cursor.execute('SELECT * FROM user_instructions')
        instructions = sqlite_cursor.fetchall()
        for instruction in instructions:
            # Convert data types appropriately
            instruction_data = list(instruction)
            instruction_data[3] = safe_integer(instruction_data[3])  # series_id
            instruction_data[4] = safe_integer(instruction_data[4])  # team_id
            instruction_data[5] = safe_timestamp(instruction_data[5])  # created_at
            # instruction_data[6] is already a string (series_name)
            
            try:
                pg_cursor.execute('''
                INSERT INTO user_instructions (id, user_email, instruction, series_id, team_id, created_at, series_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                ''', tuple(instruction_data))
                pg_conn.commit()  # Commit after each instruction
            except Exception as e:
                print(f"Error inserting instruction: {instruction_data}")
                print(f"Error details: {str(e)}")
                pg_conn.rollback()  # Rollback on error
                continue

        # Migrate player_availability with boolean conversion
        print("Migrating player availability...")
        sqlite_cursor.execute('SELECT * FROM player_availability')
        availability = sqlite_cursor.fetchall()
        for avail in availability:
            # Convert updated_at timestamp and boolean
            avail_data = list(avail)
            avail_data[3] = safe_boolean(avail_data[3])  # is_available
            avail_data[4] = safe_timestamp(avail_data[4])  # updated_at
            
            try:
                pg_cursor.execute('''
                INSERT INTO player_availability (id, player_name, match_date, is_available, updated_at, series)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (player_name, match_date, series) DO NOTHING
                ''', tuple(avail_data))
                pg_conn.commit()  # Commit after each record
            except Exception as e:
                print(f"Error inserting availability: {avail_data}")
                print(f"Error details: {str(e)}")
                pg_conn.rollback()  # Rollback on error
                continue

        # Migrate user_activity_logs
        print("Migrating user activity logs...")
        sqlite_cursor.execute('SELECT * FROM user_activity_logs')
        logs = sqlite_cursor.fetchall()
        for log in logs:
            # Convert timestamp
            log_data = list(log)
            log_data[7] = safe_timestamp(log_data[7])
            
            try:
                pg_cursor.execute('''
                INSERT INTO user_activity_logs (id, user_email, activity_type, page, action, details, ip_address, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                ''', tuple(log_data))
                pg_conn.commit()  # Commit after each log
            except Exception as e:
                print(f"Error inserting log: {log_data}")
                print(f"Error details: {str(e)}")
                pg_conn.rollback()  # Rollback on error
                continue

    except Exception as e:
        print(f"Error during migration: {str(e)}")
        pg_conn.rollback()
        raise

def main():
    # Get database connections
    sqlite_conn = get_sqlite_connection()
    db_params = parse_db_url(get_db_url())
    pg_conn = psycopg2.connect(**db_params)

    try:
        print("Creating PostgreSQL schema...")
        create_postgres_schema(pg_conn)
        
        print("Migrating data...")
        migrate_data(sqlite_conn, pg_conn)
        
        print("Migration completed successfully!")
    
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        pg_conn.rollback()
    
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    main() 