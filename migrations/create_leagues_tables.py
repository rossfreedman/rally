#!/usr/bin/env python3
"""
Migration script to create leagues tables and establish many-to-many relationship between leagues and clubs.

This adds:
1. leagues table (league_id, league_name, league_url)
2. club_leagues junction table for many-to-many relationship
3. league_id column to users table
4. Updates init_db.py compatibility
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def run_migration():
    """Run the leagues migration"""
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment variable
    DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DATABASE_PUBLIC_URL')
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable is not set")
    
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("Creating leagues tables...")
    
    # Create leagues table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leagues (
        id SERIAL PRIMARY KEY,
        league_id VARCHAR(255) NOT NULL UNIQUE,
        league_name VARCHAR(255) NOT NULL,
        league_url VARCHAR(512),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create club_leagues junction table for many-to-many relationship
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS club_leagues (
        id SERIAL PRIMARY KEY,
        club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
        league_id INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(club_id, league_id)
    )
    ''')
    
    # Add league_id column to users table if it doesn't exist
    cursor.execute('''
    ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS league_id INTEGER REFERENCES leagues(id)
    ''')
    
    print("Inserting default leagues...")
    
    # Insert default leagues
    default_leagues = [
        ('APTA_CHICAGO', 'APTA Chicago', 'https://aptachicago.tenniscores.com/'),
        ('APTA_NATIONAL', 'APTA National', 'https://apta.tenniscores.com/'),
        ('NSTF', 'North Shore Tennis Foundation', 'https://nstf.org/'),
    ]
    
    for league_id, league_name, league_url in default_leagues:
        cursor.execute('''
        INSERT INTO leagues (league_id, league_name, league_url) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (league_id) DO NOTHING
        ''', (league_id, league_name, league_url))
    
    print("Setting up default club-league relationships...")
    
    # Get all clubs and assign them to APTA_CHICAGO league by default
    cursor.execute("SELECT id FROM clubs")
    clubs = cursor.fetchall()
    
    cursor.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
    apta_chicago_league = cursor.fetchone()
    
    if apta_chicago_league and clubs:
        apta_chicago_id = apta_chicago_league[0]
        for club in clubs:
            club_id = club[0]
            cursor.execute('''
            INSERT INTO club_leagues (club_id, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (club_id, league_id) DO NOTHING
            ''', (club_id, apta_chicago_id))
    
    # Update existing users to have APTA_CHICAGO as default league
    if apta_chicago_league:
        cursor.execute('''
        UPDATE users 
        SET league_id = %s 
        WHERE league_id IS NULL
        ''', (apta_chicago_league[0],))
    
    print("Creating indexes...")
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leagues_league_id ON leagues(league_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_leagues_club_id ON club_leagues(club_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_club_leagues_league_id ON club_leagues(league_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_league_id ON users(league_id)')
    
    conn.close()
    print("Leagues migration completed successfully!")

if __name__ == '__main__':
    run_migration() 