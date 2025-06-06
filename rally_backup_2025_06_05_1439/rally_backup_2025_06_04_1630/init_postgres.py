from utils.db import execute_update, execute_query

def init_postgres():
    """Initialize PostgreSQL database with default data"""
    print("Initializing PostgreSQL database...")
    
    # Create clubs table
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS clubs (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    
    # Create series table
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS series (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    
    # Create users table
    execute_update(
        """
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
        """
    )
    
    # Create index on email for faster lookups
    execute_update(
        """
        CREATE INDEX IF NOT EXISTS idx_user_email 
        ON users(email)
        """
    )
    
    # Create user_instructions table
    execute_update(
        """
        CREATE TABLE IF NOT EXISTS user_instructions (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            instruction TEXT NOT NULL,
            series_id INTEGER REFERENCES series(id),
            team_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
        """
    )
    
    # Insert default clubs
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
        execute_update(
            """
            INSERT INTO clubs (name)
            VALUES (%(name)s)
            ON CONFLICT (name) DO NOTHING
            """,
            {'name': club}
        )
    
    # Insert default series
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
        execute_update(
            """
            INSERT INTO series (name)
            VALUES (%(name)s)
            ON CONFLICT (name) DO NOTHING
            """,
            {'name': series}
        )
    
    print("PostgreSQL database initialization complete.")

if __name__ == '__main__':
    init_postgres() 