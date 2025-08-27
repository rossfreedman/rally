#!/usr/bin/env python3
"""
Shared utilities for Rally league data import scripts.
Provides database connection, league resolution, and upsert operations.
"""

import os
import psycopg2
import psycopg2.extras

# Use the existing database configuration that handles Railway properly
try:
    from database_config import get_db_url
except ImportError:
    # Fallback to local .env loading if database_config not available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # dotenv not available, continue without it
        pass

def get_conn():
    """Get database connection using the proper database configuration."""
    try:
        # Use the Railway-aware database configuration
        database_url = get_db_url()
    except (ImportError, NameError):
        # Fallback to direct environment variable
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
    
    conn = psycopg2.connect(database_url)
    return conn


def get_league_id(cur, league_key):
    """Get league ID from database using league_id or league_name."""
    cur.execute(
        "SELECT id FROM leagues WHERE league_id = %s OR league_name = %s LIMIT 1",
        (league_key, league_key)
    )
    result = cur.fetchone()
    if not result:
        raise ValueError(f"League '{league_key}' not found in database")
    return result[0]


def column_exists(cur, table, column):
    """Check if a column exists in a table."""
    cur.execute("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s LIMIT 1
    """, (table, column))
    return cur.fetchone() is not None


def check_tenniscores_player_id_column(cur):
    """Check if players table has tenniscores_player_id column."""
    return column_exists(cur, "players", "tenniscores_player_id")


def upsert_club(cur, name, league_id):
    """Upsert club and return ID."""
    if not name:
        return None
    
    # Check if clubs table has league_id column
    if column_exists(cur, "clubs", "league_id"):
        # Direct league_id column
        cur.execute("""
            INSERT INTO clubs (name, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM clubs WHERE name = %s AND league_id = %s", (name, league_id))
        return cur.fetchone()[0]
    else:
        # Use club_leagues junction table
        # First, try to insert the club
        cur.execute("INSERT INTO clubs (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id", (name,))
        result = cur.fetchone()
        
        if result:
            # New club was created
            club_id = result[0]
        else:
            # Club already exists, get its ID
            cur.execute("SELECT id FROM clubs WHERE name = %s", (name,))
            club_id = cur.fetchone()[0]
        
        # Check if club-league relationship already exists
        cur.execute("SELECT 1 FROM club_leagues WHERE club_id = %s AND league_id = %s", (club_id, league_id))
        if not cur.fetchone():
            # Create club-league relationship only if it doesn't exist
            cur.execute("INSERT INTO club_leagues (club_id, league_id) VALUES (%s, %s)", (club_id, league_id))
        
        return club_id


def upsert_series(cur, name, league_id):
    """Upsert series and return ID."""
    if not name:
        return None
    
    # Check if series table has display_name column
    if column_exists(cur, "series", "display_name"):
        cur.execute("""
            INSERT INTO series (name, display_name, league_id) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (name, name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (name, league_id))
        return cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO series (name, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (name, league_id))
        return cur.fetchone()[0]


def upsert_team(cur, league_id, team_name, club_name, series_name):
    """Upsert team and return ID. Requires club and series names."""
    if not all([team_name, club_name, series_name]):
        return None
    
    club_id = upsert_club(cur, club_name, league_id)
    series_id = upsert_series(cur, series_name, league_id)
    
    # Check if teams table has display_name column
    if column_exists(cur, "teams", "display_name"):
        cur.execute("""
            INSERT INTO teams (team_name, display_name, club_id, series_id, league_id) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (team_name, league_id) DO NOTHING 
            RETURNING id
        """, (team_name, team_name, club_id, series_id, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM teams WHERE team_name = %s AND league_id = %s", (team_name, league_id))
        return cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO teams (name, club_id, series_id, league_id) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (team_name, club_id, series_id, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM teams WHERE name = %s AND league_id = %s", (team_name, league_id))
        return cur.fetchone()[0]


def upsert_player(cur, league_id, player_name, external_id=None, club_name=None, series_name=None, team_name=None):
    """Upsert player and return ID."""
    if not player_name:
        return None
    
    # Determine which columns exist
    has_external_id = column_exists(cur, "players", "external_id")
    has_tenniscores_id = column_exists(cur, "players", "tenniscores_player_id")
    has_club_id = column_exists(cur, "players", "club_id")
    has_series_id = column_exists(cur, "players", "series_id")
    has_team_id = column_exists(cur, "players", "team_id")
    has_first_last = column_exists(cur, "players", "first_name") and column_exists(cur, "players", "last_name")
    
    # Parse player name if first_name/last_name columns exist
    if has_first_last and " " in player_name:
        first_name, last_name = player_name.split(" ", 1)
    else:
        first_name, last_name = player_name, ""
    
    # Get additional IDs if columns exist
    club_id = None
    series_id = None
    team_id = None
    
    if has_club_id and club_name:
        club_id = upsert_club(cur, league_id, club_name)
    
    if has_series_id and series_name:
        series_id = upsert_series(cur, league_id, series_name)
    
    if has_team_id and team_name:
        team_id = upsert_team(cur, league_id, team_name, club_name, series_name)
    
    # Try external_id path first if available
    if has_external_id and external_id:
        if has_first_last and has_club_id and has_series_id:
            cur.execute("""
                INSERT INTO players (first_name, last_name, league_id, club_id, series_id, external_id) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                ON CONFLICT (external_id) DO UPDATE SET 
                    first_name = EXCLUDED.first_name, 
                    last_name = EXCLUDED.last_name, 
                    league_id = EXCLUDED.league_id,
                    club_id = EXCLUDED.club_id,
                    series_id = EXCLUDED.series_id
                RETURNING id
            """, (first_name, last_name, league_id, club_id, series_id, external_id))
        elif has_first_last:
            cur.execute("""
                INSERT INTO players (first_name, last_name, league_id, external_id) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (external_id) DO UPDATE SET 
                    first_name = EXCLUDED.first_name, 
                    last_name = EXCLUDED.last_name, 
                    league_id = EXCLUDED.league_id
                RETURNING id
            """, (first_name, last_name, league_id, external_id))
        else:
            cur.execute("""
                INSERT INTO players (name, league_id, external_id) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (external_id) DO UPDATE SET 
                    name = EXCLUDED.name, 
                    league_id = EXCLUDED.league_id
                RETURNING id
            """, (player_name, league_id, external_id))
        
        result = cur.fetchone()
        if result:
            return result[0]
    
    # Try tenniscores_player_id path if available
    if has_tenniscores_id and external_id:
        if has_first_last and has_club_id and has_series_id:
            cur.execute("""
                INSERT INTO players (first_name, last_name, league_id, club_id, series_id, tenniscores_player_id) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id)
                DO UPDATE SET 
                    first_name = EXCLUDED.first_name, 
                    last_name = EXCLUDED.last_name
                RETURNING id
            """, (first_name, last_name, league_id, club_id, series_id, external_id))
        elif has_first_last:
            cur.execute("""
                INSERT INTO players (first_name, last_name, league_id, tenniscores_player_id) 
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id)
                DO UPDATE SET 
                    first_name = EXCLUDED.first_name, 
                    last_name = EXCLUDED.last_name
                RETURNING id
            """, (first_name, last_name, league_id, external_id))
        else:
            cur.execute("""
                INSERT INTO players (name, league_id, tenniscores_player_id) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id)
                DO UPDATE SET 
                    name = EXCLUDED.name
                RETURNING id
            """, (player_name, league_id, external_id))
        
        result = cur.fetchone()
        if result:
            return result[0]
    
    # Fallback to name + league_id path
    if has_first_last and has_club_id and has_series_id:
        cur.execute("""
            INSERT INTO players (first_name, last_name, league_id, club_id, series_id) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (first_name, last_name, league_id, club_id, series_id) DO NOTHING 
            RETURNING id
        """, (first_name, last_name, league_id, club_id, series_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("""
            SELECT id FROM players 
            WHERE first_name = %s AND last_name = %s AND league_id = %s AND club_id = %s AND series_id = %s
        """, (first_name, last_name, league_id, club_id, series_id))
        existing = cur.fetchone()
        if existing:
            return existing[0]
    elif has_first_last:
        cur.execute("""
            INSERT INTO players (first_name, last_name, league_id) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (first_name, last_name, league_id) DO NOTHING 
            RETURNING id
        """, (first_name, last_name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("""
            SELECT id FROM players 
            WHERE first_name = %s AND last_name = %s AND league_id = %s
        """, (first_name, last_name, league_id))
        existing = cur.fetchone()
        if existing:
            return existing[0]
    else:
        cur.execute("""
            INSERT INTO players (name, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (player_name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM players WHERE name = %s AND league_id = %s", (player_name, league_id))
        existing = cur.fetchone()
        if existing:
            return existing[0]
    
    return None


def lookup_team_id(cur, league_id, team_name):
    """Look up team ID by name and league. Do not create."""
    if not team_name:
        return None
    
    # Check if teams table has team_name column
    if column_exists(cur, "teams", "team_name"):
        cur.execute("SELECT id FROM teams WHERE team_name = %s AND league_id = %s", (team_name, league_id))
    else:
        cur.execute("SELECT id FROM teams WHERE name = %s AND league_id = %s", (team_name, league_id))
    
    result = cur.fetchone()
    return result[0] if result else None


def parse_datetime_safe(datetime_str):
    """Parse datetime string safely, return None if invalid."""
    if not datetime_str:
        return None
    
    try:
        from datetime import datetime
        # Try common formats including 12-hour time with AM/PM
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p"]:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        return None
    except ImportError:
        return None
