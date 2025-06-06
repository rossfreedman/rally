import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def init_db():
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment variable
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable is not set")
    
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("Creating tables...")
    
    # Create clubs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clubs (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE
    )
    ''')
    
    # Create series table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS series (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE
    )
    ''')
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        club_id INTEGER REFERENCES clubs(id),
        series_id INTEGER REFERENCES series(id),
        club_automation_password VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    ''')
    
    # Create user_instructions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_instructions (
        id SERIAL PRIMARY KEY,
        user_email VARCHAR(255) NOT NULL,
        instruction TEXT NOT NULL,
        series_id INTEGER REFERENCES series(id),
        team_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    )
    ''')
    
    # Create player_availability table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_availability (
        id SERIAL PRIMARY KEY,
        player_name VARCHAR(255) NOT NULL,
        match_date DATE NOT NULL,
        availability_status INTEGER NOT NULL DEFAULT 3, -- 1: available, 2: unavailable, 3: not sure
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        series_id INTEGER NOT NULL REFERENCES series(id),
        UNIQUE(player_name, match_date, series_id),
        CONSTRAINT valid_availability_status CHECK (availability_status IN (1, 2, 3))
    )
    ''')
    
    # Create user_activity_logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_activity_logs (
        id SERIAL PRIMARY KEY,
        user_email VARCHAR(255) NOT NULL,
        activity_type VARCHAR(255) NOT NULL,
        page VARCHAR(255),
        action TEXT,
        details TEXT,
        ip_address VARCHAR(45),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Insert default clubs
    default_clubs = [
        'Germantown Cricket Club', 'Philadelphia Cricket Club', 'Merion Cricket Club',
        'Waynesborough Country Club', 'Aronimink Golf Club', 'Overbrook Golf Club',
        'Radnor Valley Country Club', 'White Manor Country Club'
    ]
    
    for club in default_clubs:
        cursor.execute('''
        INSERT INTO clubs (name) 
        VALUES (%s) 
        ON CONFLICT (name) DO NOTHING
        ''', (club,))
    
    # Insert default series
    default_series = [
        'Series 1', 'Series 2', 'Series 3', 'Series 4',
        'Series 5', 'Series 6', 'Series 7', 'Series 8'
    ]
    
    for series in default_series:
        cursor.execute('''
        INSERT INTO series (name) 
        VALUES (%s) 
        ON CONFLICT (name) DO NOTHING
        ''', (series,))
    
    print("Creating indexes...")
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_instructions_email ON user_instructions(user_email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_availability ON player_availability(player_name, match_date, series_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_logs_user_email ON user_activity_logs(user_email, timestamp)')
    
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db() 