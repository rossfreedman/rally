import sqlite3
import os
import hashlib

def init_db():
    # Create database directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Use absolute path for database
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
    print(f"Initializing database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create clubs lookup table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')
    
    # Create series lookup table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS series (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        club_id INTEGER,
        series_id INTEGER,
        club_automation_password TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        FOREIGN KEY (club_id) REFERENCES clubs(id),
        FOREIGN KEY (series_id) REFERENCES series(id)
    )
    ''')
    
    # Create index on email for faster lookups
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_user_email 
    ON users(email)
    ''')
    
    # Create user_instructions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_instructions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        instruction TEXT NOT NULL,
        series_id INTEGER,
        team_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (series_id) REFERENCES series(id),
        FOREIGN KEY (team_id) REFERENCES teams(id)
    )
    ''')
    
    # Create index on user_email for faster lookups
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_user_instructions_email 
    ON user_instructions(user_email)
    ''')
    
    # Create player_availability table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT NOT NULL,
        match_date TEXT NOT NULL,
        is_available BOOLEAN DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        series TEXT NOT NULL,
        UNIQUE(player_name, match_date, series)
    )
    ''')
    
    # Create index on player_name and match_date for faster lookups
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_player_availability 
    ON player_availability(player_name, match_date, series)
    ''')
    
    # Create user_activity_logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        activity_type TEXT NOT NULL,
        page TEXT,
        action TEXT,
        details TEXT,
        ip_address TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_email) REFERENCES users(email)
    )
    ''')
    
    # Create index on user_email and timestamp for faster queries
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_user_activity_logs_user_email 
    ON user_activity_logs(user_email, timestamp)
    ''')
    
    # Insert default clubs if they don't exist
    default_clubs = [
        'Tennaqua', 'Wilmette PD', 'Sunset Ridge', 'Winnetka', 'Exmoor',
        'Hinsdale PC', 'Onwentsia', 'Salt Creek', 'Lakeshore S&F', 'Glen View',
        'Prairie Club', 'Lake Forest', 'Evanston', 'Midt-Bannockburn', 'Briarwood',
        'Birchwood', 'Hinsdale GC', 'Butterfield', 'Chicago Highlands', 'Glen Ellyn',
        'Skokie', 'Winter Club', 'Westmoreland', 'Valley Lo', 'South Barrington',
        'Saddle & Cycle', 'Ruth Lake', 'Northmoor', 'North Shore', 'Midtown - Chicago',
        'Michigan Shores', 'Lake Shore CC', 'Knollwood', 'Indian Hill', 'Glenbrook RC',
        'Hawthorn Woods', 'Lake Bluff', 'Barrington Hills CC', 'River Forest PD',
        'Edgewood Valley', 'Park Ridge CC', 'Medinah', 'LaGrange CC', 'Dunham Woods',
        'Bryn Mawr', 'Glen Oak', 'Inverness', 'White Eagle', 'Legends',
        'River Forest CC', 'Oak Park CC', 'Royal Melbourne'
    ]
    
    for club in default_clubs:
        cursor.execute('INSERT OR IGNORE INTO clubs (name) VALUES (?)', (club,))
    
    # Insert default series if they don't exist
    default_series = [
        'Chicago 1', 'Chicago 2', 'Chicago 3', 'Chicago 4', 'Chicago 5',
        'Chicago 6', 'Chicago 7', 'Chicago 8', 'Chicago 9', 'Chicago 10',
        'Chicago 11', 'Chicago 12', 'Chicago 13', 'Chicago 14', 'Chicago 15',
        'Chicago 16', 'Chicago 17', 'Chicago 18', 'Chicago 19', 'Chicago 20',
        'Chicago 21', 'Chicago 22', 'Chicago 23', 'Chicago 24', 'Chicago 25',
        'Chicago 26', 'Chicago 27', 'Chicago 28', 'Chicago 29', 'Chicago 30',
        'Chicago 31', 'Chicago 32', 'Chicago 33', 'Chicago 34', 'Chicago 35',
        'Chicago 36', 'Chicago 37', 'Chicago 38', 'Chicago 39', 'Chicago Legends',
        'Chicago 7 SW', 'Chicago 9 SW', 'Chicago 11 SW', 'Chicago 13 SW',
        'Chicago 15 SW', 'Chicago 17 SW', 'Chicago 19 SW', 'Chicago 21 SW',
        'Chicago 23 SW', 'Chicago 25 SW', 'Chicago 27 SW', 'Chicago 29 SW'
    ]
    
    for series in default_series:
        cursor.execute('INSERT OR IGNORE INTO series (name) VALUES (?)', (series,))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!") 