import sqlite3
import psycopg
import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_sqlite_connection():
    """Get SQLite database connection"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
    return sqlite3.connect(db_path)

def get_postgres_connection():
    """Get PostgreSQL database connection"""
    return psycopg.connect("dbname=rally user=rossfreedman")

def convert_to_bool(value):
    """Convert SQLite integer to PostgreSQL boolean"""
    if isinstance(value, bool):
        return value
    return bool(value) if value is not None else None

def convert_to_int(value):
    """Convert string to integer, handling NULL values"""
    try:
        return int(value) if value not in (None, '', 'None') else None
    except (ValueError, TypeError):
        return None

def create_postgres_tables(pg_conn):
    """Create tables in PostgreSQL"""
    with pg_conn.cursor() as cur:
        # Create clubs table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS clubs (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        
        # Create series table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS series (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        
        # Create users table
        cur.execute('''
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
                last_login TIMESTAMP,
                FOREIGN KEY (club_id) REFERENCES clubs(id),
                FOREIGN KEY (series_id) REFERENCES series(id)
            )
        ''')
        
        # Create user_instructions table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_instructions (
                id SERIAL PRIMARY KEY,
                user_email TEXT NOT NULL,
                instruction TEXT NOT NULL,
                series_id INTEGER,
                team_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (series_id) REFERENCES series(id)
            )
        ''')
        
        # Create player_availability table
        cur.execute('''
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
        
        # Create user_activity_logs table without foreign key initially
        cur.execute('''
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
        cur.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_user_instructions_email ON user_instructions(user_email)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_player_availability ON player_availability(player_name, match_date, series)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_logs_user_email ON user_activity_logs(user_email, timestamp)')
        
        pg_conn.commit()

def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()
    
    try:
        # Create PostgreSQL tables
        create_postgres_tables(pg_conn)
        
        # Migrate clubs
        df = pd.read_sql_query("SELECT * FROM clubs", sqlite_conn)
        with pg_conn.cursor() as cur:
            for _, row in df.iterrows():
                cur.execute(
                    "INSERT INTO clubs (id, name) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                    (row['id'], row['name'])
                )
        
        # Migrate series
        df = pd.read_sql_query("SELECT * FROM series", sqlite_conn)
        with pg_conn.cursor() as cur:
            for _, row in df.iterrows():
                cur.execute(
                    "INSERT INTO series (id, name) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                    (row['id'], row['name'])
                )
        
        # Migrate users
        df = pd.read_sql_query("SELECT * FROM users", sqlite_conn)
        with pg_conn.cursor() as cur:
            for _, row in df.iterrows():
                cur.execute("""
                    INSERT INTO users (
                        id, email, password_hash, first_name, last_name,
                        club_id, series_id, club_automation_password,
                        created_at, last_login
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO UPDATE SET
                        password_hash = EXCLUDED.password_hash,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        club_id = EXCLUDED.club_id,
                        series_id = EXCLUDED.series_id,
                        club_automation_password = EXCLUDED.club_automation_password,
                        last_login = EXCLUDED.last_login
                """, (
                    row['id'], row['email'], row['password_hash'],
                    row['first_name'], row['last_name'],
                    convert_to_int(row['club_id']),
                    convert_to_int(row['series_id']),
                    row['club_automation_password'],
                    row['created_at'], row['last_login']
                ))
        
        # Migrate user_instructions
        df = pd.read_sql_query("SELECT * FROM user_instructions", sqlite_conn)
        with pg_conn.cursor() as cur:
            for _, row in df.iterrows():
                cur.execute("""
                    INSERT INTO user_instructions (
                        id, user_email, instruction, series_id,
                        team_id, created_at, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    row['id'], row['user_email'], row['instruction'],
                    convert_to_int(row['series_id']),
                    convert_to_int(row['team_id']),
                    row['created_at'],
                    convert_to_bool(row['is_active'])
                ))
        
        # Migrate player_availability
        df = pd.read_sql_query("SELECT * FROM player_availability", sqlite_conn)
        with pg_conn.cursor() as cur:
            for _, row in df.iterrows():
                cur.execute("""
                    INSERT INTO player_availability (
                        id, player_name, match_date, is_available,
                        updated_at, series
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (player_name, match_date, series) DO UPDATE SET
                        is_available = EXCLUDED.is_available,
                        updated_at = EXCLUDED.updated_at
                """, (
                    row['id'], row['player_name'], row['match_date'],
                    convert_to_bool(row['is_available']),
                    row['updated_at'], row['series']
                ))
        
        # Migrate user_activity_logs
        df = pd.read_sql_query("SELECT * FROM user_activity_logs", sqlite_conn)
        with pg_conn.cursor() as cur:
            for _, row in df.iterrows():
                # Only insert logs for existing users
                cur.execute("""
                    INSERT INTO user_activity_logs (
                        id, user_email, activity_type, page,
                        action, details, ip_address, timestamp
                    )
                    SELECT %s, %s, %s, %s, %s, %s, %s, %s
                    WHERE EXISTS (
                        SELECT 1 FROM users WHERE email = %s
                    )
                """, (
                    row['id'], row['user_email'], row['activity_type'],
                    row['page'], row['action'], row['details'],
                    row['ip_address'], row['timestamp'],
                    row['user_email']  # For the WHERE EXISTS clause
                ))
        
        # Add foreign key constraint to user_activity_logs after data migration
        with pg_conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE user_activity_logs
                ADD CONSTRAINT user_activity_logs_user_email_fkey
                FOREIGN KEY (user_email) REFERENCES users(email)
            """)
        
        pg_conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"Error during migration: {str(e)}")
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    migrate_data() 