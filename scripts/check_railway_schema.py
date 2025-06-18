#!/usr/bin/env python3
"""Check Railway database schema"""

import psycopg2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db_url
import re

def check_railway_schema():
    """Check Railway database schema"""
    os.environ['SYNC_RAILWAY'] = 'true'
    
    # Get Railway connection details  
    url = get_db_url()
    pattern = r'postgresql://([^:]+):([^@]+)@([^/]+)/(.+)'
    match = re.match(pattern, url)
    user, password, host_port, database = match.groups()
    host, port = host_port.split(':')

    conn = psycopg2.connect(
        host=host, port=port, database=database, 
        user=user, password=password, sslmode='prefer'
    )

    cursor = conn.cursor()

    print("🔍 Checking Railway Database Schema")
    print("=" * 50)

    # Check if the constraint exists
    cursor.execute("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'club_leagues' 
        AND constraint_name = 'club_leagues_club_id_league_id_key'
    """)

    constraint_exists = cursor.fetchone()
    print(f'❓ club_leagues_club_id_league_id_key constraint exists: {constraint_exists is not None}')

    # Check current club_leagues table structure
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'club_leagues'
        ORDER BY ordinal_position
    """)

    columns = cursor.fetchall()
    print(f'📊 club_leagues columns: {columns}')

    # Check all constraints on club_leagues
    cursor.execute("""
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints 
        WHERE table_name = 'club_leagues'
    """)

    constraints = cursor.fetchall()
    print(f'🔗 club_leagues constraints: {constraints}')

    # Check current Alembic version
    cursor.execute("SELECT version_num FROM alembic_version")
    version = cursor.fetchone()
    print(f'📋 Current Alembic version: {version[0] if version else "None"}')

    conn.close()

if __name__ == "__main__":
    check_railway_schema() 