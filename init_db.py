import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def init_db():
    # Load environment variables
    load_dotenv()

    # Get database URL from environment variable
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable is not set")

    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    print("Creating tables...")

    # Create clubs table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS clubs (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE
    )
    """
    )

    # Create series table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS series (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE
    )
    """
    )

    # Create leagues table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS leagues (
        id SERIAL PRIMARY KEY,
        league_id VARCHAR(255) NOT NULL UNIQUE,
        league_name VARCHAR(255) NOT NULL,
        league_url VARCHAR(512),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # Create club_leagues junction table for many-to-many relationship
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS club_leagues (
        id SERIAL PRIMARY KEY,
        club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
        league_id INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(club_id, league_id)
    )
    """
    )

    # Create series_leagues junction table for many-to-many relationship
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS series_leagues (
        id SERIAL PRIMARY KEY,
        series_id INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
        league_id INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(series_id, league_id)
    )
    """
    )

    # Create users table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        club_id INTEGER REFERENCES clubs(id),
        series_id INTEGER REFERENCES series(id),
        league_id INTEGER REFERENCES leagues(id),
        club_automation_password VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    """
    )

    # Create user_instructions table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS user_instructions (
        id SERIAL PRIMARY KEY,
        user_email VARCHAR(255) NOT NULL,
        instruction TEXT NOT NULL,
        series_id INTEGER REFERENCES series(id),
        team_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE
    )
    """
    )

    # Create player_availability table
    cursor.execute(
        """
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
    """
    )

    # Create user_activity_logs table
    cursor.execute(
        """
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
    """
    )

    # Insert default clubs
    default_clubs = [
        "Germantown Cricket Club",
        "Philadelphia Cricket Club",
        "Merion Cricket Club",
        "Waynesborough Country Club",
        "Aronimink Golf Club",
        "Overbrook Golf Club",
        "Radnor Valley Country Club",
        "White Manor Country Club",
    ]

    for club in default_clubs:
        cursor.execute(
            """
        INSERT INTO clubs (name) 
        VALUES (%s) 
        ON CONFLICT (name) DO NOTHING
        """,
            (club,),
        )

    # Insert default series
    default_series = [
        "Series 1",
        "Series 2",
        "Series 3",
        "Series 4",
        "Series 5",
        "Series 6",
        "Series 7",
        "Series 8",
    ]

    for series in default_series:
        cursor.execute(
            """
        INSERT INTO series (name) 
        VALUES (%s) 
        ON CONFLICT (name) DO NOTHING
        """,
            (series,),
        )

    # Insert default leagues
    default_leagues = [
        ("APTA_CHICAGO", "APTA Chicago", "https://aptachicago.tenniscores.com/"),
        ("APTA_NATIONAL", "APTA National", "https://apta.tenniscores.com/"),
        ("NSTF", "North Shore Tennis Foundation", "https://nstf.org/"),
    ]

    for league_id, league_name, league_url in default_leagues:
        cursor.execute(
            """
        INSERT INTO leagues (league_id, league_name, league_url) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (league_id) DO NOTHING
        """,
            (league_id, league_name, league_url),
        )

    # Set up default club-league relationships (all clubs to APTA_CHICAGO)
    cursor.execute("SELECT id FROM clubs")
    clubs = cursor.fetchall()

    cursor.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
    apta_chicago_league = cursor.fetchone()

    if apta_chicago_league and clubs:
        apta_chicago_id = apta_chicago_league[0]
        for club in clubs:
            club_id = club[0]
            cursor.execute(
                """
            INSERT INTO club_leagues (club_id, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (club_id, league_id) DO NOTHING
            """,
                (club_id, apta_chicago_id),
            )

    # Set up default series-league relationships
    if apta_chicago_league:
        # Link Chicago series to APTA_CHICAGO league
        cursor.execute("SELECT id, name FROM series WHERE name LIKE 'Chicago%'")
        chicago_series = cursor.fetchall()

        for series_id, series_name in chicago_series:
            cursor.execute(
                """
            INSERT INTO series_leagues (series_id, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (series_id, league_id) DO NOTHING
            """,
                (series_id, apta_chicago_id),
            )

        # Link remaining series to APTA_CHICAGO as default
        cursor.execute(
            """
        SELECT s.id FROM series s 
        LEFT JOIN series_leagues sl ON s.id = sl.series_id 
        WHERE sl.series_id IS NULL
        """
        )
        unlinked_series = cursor.fetchall()

        for (series_id,) in unlinked_series:
            cursor.execute(
                """
            INSERT INTO series_leagues (series_id, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (series_id, league_id) DO NOTHING
            """,
                (series_id, apta_chicago_id),
            )

    print("Creating indexes...")
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_instructions_email ON user_instructions(user_email)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_player_availability ON player_availability(player_name, match_date, series_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_activity_logs_user_email ON user_activity_logs(user_email, timestamp)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_leagues_league_id ON leagues(league_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_club_leagues_club_id ON club_leagues(club_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_club_leagues_league_id ON club_leagues(league_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_series_leagues_series_id ON series_leagues(series_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_series_leagues_league_id ON series_leagues(league_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_league_id ON users(league_id)")

    conn.close()
    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
