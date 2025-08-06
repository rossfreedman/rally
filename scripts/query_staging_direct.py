#!/usr/bin/env python3
"""
Query Staging Database Directly from Local
==========================================

This script connects to the staging database directly from your local environment
using Railway's public database URL. No need to upload scripts to staging!

Usage:
1. Get Railway staging database URL: `railway variables --service "Rally STAGING App"`
2. Set environment variable: `export DATABASE_PUBLIC_URL="your_staging_url"`
3. Run this script: `python scripts/query_staging_direct.py`
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import json
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_database_config

def get_staging_connection():
    """Connect directly to staging database from local environment"""
    
    # Get staging database URL from environment
    staging_url = (
        os.getenv('DATABASE_PUBLIC_URL') or 
        os.getenv('DATABASE_URL') or
        os.getenv('STAGING_DATABASE_URL')
    )
    
    if not staging_url:
        print("❌ No staging database URL found!")
        print("Set one of these environment variables:")
        print("  - DATABASE_PUBLIC_URL (preferred for external access)")
        print("  - DATABASE_URL")  
        print("  - STAGING_DATABASE_URL")
        print()
        print("Get the URL with: railway variables --service \"Rally STAGING App\"")
        return None
    
    # Handle Railway's postgres:// URLs
    if staging_url.startswith("postgres://"):
        staging_url = staging_url.replace("postgres://", "postgresql://", 1)
    
    # Parse and connect
    parsed = urlparse(staging_url)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",  # Required for Railway
        "connect_timeout": 30,
        "application_name": "local_staging_query"
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        print(f"✅ Connected to staging database at {parsed.hostname}")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to staging database: {e}")
        return None

def run_query(conn, description, query, params=None):
    """Run a query and display results"""
    print(f"\n=== {description} ===")
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params or [])
        results = cursor.fetchall()
        
        if not results:
            print("No results found")
            return
        
        # Display results
        for i, row in enumerate(results):
            if i == 0:
                # Print headers
                headers = list(row.keys())
                print(" | ".join(f"{h:15}" for h in headers))
                print("-" * (len(headers) * 18))
            
            # Print row data
            values = [str(row[key]) if row[key] is not None else "NULL" for key in row.keys()]
            print(" | ".join(f"{v:15}" for v in values))
            
            # Limit output for readability
            if i >= 20:
                print(f"... and {len(results) - 21} more rows")
                break
    
    except Exception as e:
        print(f"❌ Error running query: {e}")

def investigate_series_issue(conn):
    """Investigate the series_id health issue"""
    
    # 1. Check leagues table
    run_query(conn, "LEAGUES TABLE", """
        SELECT id, league_id, league_name 
        FROM leagues 
        ORDER BY id
    """)
    
    # 2. Check series_stats league_id distribution
    run_query(conn, "SERIES_STATS LEAGUE_ID DISTRIBUTION", """
        SELECT league_id, COUNT(*) as count
        FROM series_stats 
        GROUP BY league_id 
        ORDER BY league_id
    """)
    
    # 3. Check for orphaned series_stats records
    run_query(conn, "ORPHANED SERIES_STATS (league_id not in leagues)", """
        SELECT DISTINCT ss.league_id, COUNT(*) as count
        FROM series_stats ss
        LEFT JOIN leagues l ON ss.league_id = l.id
        WHERE l.id IS NULL
        GROUP BY ss.league_id
        ORDER BY ss.league_id
    """)
    
    # 4. Check series_id health
    run_query(conn, "SERIES_ID HEALTH SUMMARY", """
        SELECT 
            COUNT(*) as total_records,
            COUNT(series_id) as with_series_id,
            COUNT(*) - COUNT(series_id) as missing_series_id,
            ROUND(COUNT(series_id)::float / COUNT(*) * 100, 1) as health_score_percent
        FROM series_stats
    """)
    
    # 5. Check specific problematic records
    run_query(conn, "PROBLEMATIC RECORDS (missing series_id)", """
        SELECT series, league_id, COUNT(*) as count
        FROM series_stats 
        WHERE series_id IS NULL
        GROUP BY series, league_id
        ORDER BY count DESC
        LIMIT 10
    """)

def fix_orphaned_records(conn):
    """Fix orphaned league_id references"""
    print("\n=== FIXING ORPHANED RECORDS ===")
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get current leagues for mapping
    cursor.execute("SELECT id, league_id FROM leagues")
    leagues = {row['league_id']: row['id'] for row in cursor.fetchall()}
    print(f"Available leagues: {leagues}")
    
    # Common orphaned ID mappings (based on previous experience)
    orphan_mappings = {}
    
    for league_id, db_id in leagues.items():
        if league_id == "APTA_CHICAGO":
            orphan_mappings[4815] = db_id


            orphan_mappings[4817] = db_id
        elif league_id == "NSTF":
            orphan_mappings[4818] = db_id
    
    print(f"Proposed orphan fixes: {orphan_mappings}")
    
    # Apply fixes
    fixed_count = 0
    for orphaned_id, correct_id in orphan_mappings.items():
        cursor.execute("""
            UPDATE series_stats 
            SET league_id = %s 
            WHERE league_id = %s
        """, (correct_id, orphaned_id))
        
        if cursor.rowcount > 0:
            print(f"✅ Fixed {cursor.rowcount} records: {orphaned_id} → {correct_id}")
            fixed_count += cursor.rowcount
    
    if fixed_count > 0:
        conn.commit()
        print(f"✅ Total fixed: {fixed_count} records")
        
        # Re-run health check
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(series_id) as with_series_id,
                ROUND(COUNT(series_id)::float / COUNT(*) * 100, 1) as health_score_percent
            FROM series_stats
        """)
        health = cursor.fetchone()
        print(f"📊 New health score: {health['health_score_percent']}%")
    else:
        print("ℹ️  No orphaned records found to fix")

def query_staging_database():
    """Query the staging database directly"""
    try:
        config = get_database_config()
        
        # Connect to staging database
        conn = psycopg2.connect(
            host=config['host'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            port=config['port']
        )
        
        cur = conn.cursor()
        
        # Investigate player ID: nndz-WkMrK3didjlnUT09
        player_id = "nndz-WkMrK3didjlnUT09"
        
        print(f"🔍 Investigating player ID: {player_id}")
        print("=" * 60)
        
        # Query 1: Check if this player exists in the players table
        print("\n1️⃣ Player Record:")
        cur.execute("""
            SELECT p.id, p.first_name, p.last_name, p.club, p.series, 
                   p.league_id, l.league_name, l.league_id as league_string_id,
                   p.team_id, t.team_name, p.is_active
            FROM players p
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = %s
        """, [player_id])
        
        player_records = cur.fetchall()
        if player_records:
            for record in player_records:
                print(f"   ID: {record[0]}")
                print(f"   Name: {record[1]} {record[2]}")
                print(f"   Club: {record[3]}")
                print(f"   Series: {record[4]}")
                print(f"   League ID: {record[5]} ({record[6]} - {record[7]})")
                print(f"   Team ID: {record[8]} ({record[9]})")
                print(f"   Active: {record[10]}")
                print()
        else:
            print("   ❌ No player records found")
        
        # Query 2: Check user associations
        print("\n2️⃣ User Associations:")
        cur.execute("""
            SELECT upa.user_id, upa.tenniscores_player_id, u.first_name, u.last_name, u.email,
                   u.league_context, l.league_name
            FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE upa.tenniscores_player_id = %s
        """, [player_id])
        
        associations = cur.fetchall()
        if associations:
            for assoc in associations:
                print(f"   User ID: {assoc[0]}")
                print(f"   Player ID: {assoc[1]}")
                print(f"   User: {assoc[2]} {assoc[3]} ({assoc[4]})")
                print(f"   League Context: {assoc[5]} ({assoc[6]})")
                print()
        else:
            print("   ❌ No user associations found")
        
        # Query 3: Check if user has multiple leagues
        if associations:
            user_id = associations[0][0]
            print(f"\n3️⃣ All Leagues for User ID {user_id}:")
            cur.execute("""
                SELECT DISTINCT l.id, l.league_id, l.league_name
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                WHERE u.id = %s AND p.is_active = true
                ORDER BY l.league_name
            """, [user_id])
            
            leagues = cur.fetchall()
            if leagues:
                for league in leagues:
                    print(f"   League: {league[1]} ({league[2]})")
                print(f"\n   🎯 Total leagues: {len(leagues)}")
                if len(leagues) > 1:
                    print("   ✅ Multiple leagues - League selector should show")
                else:
                    print("   ❌ Single league - League selector won't show")
            else:
                print("   ❌ No leagues found")
        
        # Query 4: Check all teams for this user
        if associations:
            user_id = associations[0][0]
            print(f"\n4️⃣ All Teams for User ID {user_id}:")
            cur.execute("""
                SELECT DISTINCT
                    t.id as team_id,
                    t.team_name,
                    c.name as club_name,
                    s.name as series_name,
                    l.id as league_db_id,
                    l.league_id as league_string_id,
                    l.league_name
                FROM teams t
                JOIN players p ON t.id = p.team_id
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                JOIN clubs c ON t.club_id = c.id
                JOIN series s ON t.series_id = s.id
                JOIN leagues l ON t.league_id = l.id
                WHERE upa.user_id = %s 
                    AND p.is_active = TRUE 
                    AND t.is_active = TRUE
                ORDER BY l.league_name, t.team_name
            """, [user_id])
            
            teams = cur.fetchall()
            if teams:
                for team in teams:
                    print(f"   Team: {team[1]} ({team[2]}, {team[3]})")
                    print(f"         League: {team[5]} ({team[6]})")
                    print()
                print(f"   🎯 Total teams: {len(teams)}")
                
                # Check unique leagues
                unique_leagues = set(team[4] for team in teams)
                print(f"   🎯 Unique leagues: {len(unique_leagues)}")
                if len(unique_leagues) > 1:
                    print("   ✅ Multiple leagues - League selector should show")
                else:
                    print("   ❌ Single league - League selector won't show")
            else:
                print("   ❌ No teams found")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error querying database: {e}")
        return False

def main():
    """Main function"""
    print("🔍 STAGING DATABASE DIRECT QUERY TOOL")
    print("=" * 50)
    
    # Connect to staging
    conn = get_staging_connection()
    if not conn:
        return
    
    try:
        # Investigate the series issue
        investigate_series_issue(conn)
        
        # Ask if user wants to fix orphaned records
        print("\n" + "=" * 50)
        response = input("🔧 Do you want to fix orphaned records? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            fix_orphaned_records(conn)
        else:
            print("ℹ️  Skipping fixes. Run again with 'y' to apply fixes.")
            
        # Query the staging database directly
        query_staging_database()
        
    finally:
        conn.close()
        print("\n🔒 Database connection closed")

if __name__ == '__main__':
    main() 