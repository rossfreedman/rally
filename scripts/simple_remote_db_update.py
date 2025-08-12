#!/usr/bin/env python3
"""
Simple Remote Database Update
============================

Updates staging and production databases with missing clubs and tests ETL readiness.
Uses direct psycopg2 connections for reliability.

Usage:
    # Set database URLs first:
    export STAGING_DB_URL="postgresql://user:pass@host:port/db"
    export PRODUCTION_DB_URL="postgresql://user:pass@host:port/db"
    
    # Then run:
    python scripts/simple_remote_db_update.py staging
    python scripts/simple_remote_db_update.py production
    python scripts/simple_remote_db_update.py both
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse
from datetime import datetime

def get_db_connection(environment):
    """Get database connection for specified environment"""
    if environment == 'staging':
        db_url = os.getenv('STAGING_DB_URL')
        if not db_url:
            # Try Railway staging URL format
            db_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    else:  # production
        db_url = os.getenv('PRODUCTION_DB_URL') 
        if not db_url:
            # Try Railway production URL format - get from Railway variables
            try:
                import subprocess
                result = subprocess.run(['railway', 'variables'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'DATABASE_URL' in line and 'postgresql://' in line:
                        # Extract the URL from the table format
                        parts = line.split('│')
                        if len(parts) >= 3:
                            db_url = parts[2].strip()
                            break
            except:
                pass
            
            if not db_url:
                # Fallback - try the script's database connection method
                raise ValueError("Could not get production database URL. Please set PRODUCTION_DB_URL environment variable.")
    
    if not db_url:
        raise ValueError(f"No database URL found for {environment}")
    
    return psycopg2.connect(db_url)

def execute_sql(conn, sql, description):
    """Execute SQL and return results"""
    print(f"🔄 {description}...")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql)
            
            # Handle different SQL types
            if cursor.description:
                results = cursor.fetchall()
                conn.commit()
                print(f"✅ {description} - Success")
                return results
            else:
                conn.commit()
                print(f"✅ {description} - Success")
                return []
                
    except Exception as e:
        conn.rollback()
        print(f"❌ {description} - Error: {str(e)}")
        return None

def add_missing_clubs(conn):
    """Add missing clubs that cause ETL failures"""
    # Check what columns exist in clubs table
    check_sql = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'clubs' 
    ORDER BY ordinal_position;
    """
    
    columns = execute_sql(conn, check_sql, "Checking clubs table columns")
    
    if columns:
        column_names = [col['column_name'] for col in columns]
        print(f"📋 Clubs table columns: {column_names}")
        
        # Use only the 'name' column if that's all that exists
        if 'name' in column_names:
            sql = """
            INSERT INTO clubs (name) 
            VALUES 
                ('PraIrie Club'),
                ('Glenbrook')
            ON CONFLICT (name) DO NOTHING;
            """
        else:
            print("❌ Clubs table doesn't have expected structure")
            return False
    else:
        print("❌ Could not check clubs table structure")
        return False
    
    result = execute_sql(conn, sql, "Adding missing clubs")
    
    # Verify clubs exist
    verify_sql = "SELECT name FROM clubs WHERE name IN ('PraIrie Club', 'Glenbrook') ORDER BY name;"
    clubs = execute_sql(conn, verify_sql, "Verifying clubs added")
    
    if clubs is not None:
        print(f"📋 Clubs found: {[club['name'] for club in clubs]}")
        return len(clubs) >= 2
    return False

def check_anne_mooney(conn):
    """Check Anne Mooney's status in database"""
    # Check if she exists
    player_sql = """
    SELECT first_name, last_name, tenniscores_player_id, club_id, team_id
    FROM players 
    WHERE first_name = 'Anne' AND last_name = 'Mooney' AND tenniscores_player_id = 'cnswpl_0c3891cfa456bc03';
    """
    
    players = execute_sql(conn, player_sql, "Checking Anne Mooney player record")
    
    # Check her matches
    match_sql = """
    SELECT COUNT(*) as match_count
    FROM match_scores 
    WHERE (
        home_player_1_id = 'cnswpl_0c3891cfa456bc03' OR 
        home_player_2_id = 'cnswpl_0c3891cfa456bc03' OR 
        away_player_1_id = 'cnswpl_0c3891cfa456bc03' OR 
        away_player_2_id = 'cnswpl_0c3891cfa456bc03'
    );
    """
    
    matches = execute_sql(conn, match_sql, "Checking Anne Mooney match data")
    
    if players is not None and matches is not None:
        player_exists = len(players) > 0
        match_count = matches[0]['match_count'] if matches else 0
        
        print(f"📊 Anne Mooney Status:")
        print(f"   Player Record: {'✅ EXISTS' if player_exists else '❌ MISSING'}")
        print(f"   Match Data: {match_count} matches found")
        
        return player_exists
    return False

def validate_etl_dependencies(conn):
    """Validate all dependencies needed for successful ETL"""
    sql = """
    -- Check required clubs exist
    SELECT 'Tennaqua club' as item, 
           CASE WHEN COUNT(*) > 0 THEN 'EXISTS' ELSE 'MISSING' END as status
    FROM clubs WHERE name = 'Tennaqua'
    
    UNION ALL
    
    -- Check required teams exist  
    SELECT 'Tennaqua B team' as item,
           CASE WHEN COUNT(*) > 0 THEN 'EXISTS' ELSE 'MISSING' END as status
    FROM teams WHERE team_name = 'Tennaqua B' AND league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
    
    UNION ALL
    
    -- Check required series exist
    SELECT 'Series B' as item,
           CASE WHEN COUNT(*) > 0 THEN 'EXISTS' ELSE 'MISSING' END as status
    FROM series WHERE name = 'Series B'
    
    UNION ALL
    
    -- Check missing clubs issue is fixed
    SELECT 'Missing clubs fixed' as item,
           CASE WHEN COUNT(*) >= 2 THEN 'FIXED' ELSE 'PENDING' END as status
    FROM clubs WHERE name IN ('PraIrie Club', 'Glenbrook');
    """
    
    results = execute_sql(conn, sql, "Validating ETL dependencies")
    
    if results is not None:
        print("📋 ETL Dependency Check:")
        all_good = True
        for row in results:
            status_icon = "✅" if row['status'] in ['EXISTS', 'FIXED'] else "❌"
            print(f"   {status_icon} {row['item']}: {row['status']}")
            if row['status'] not in ['EXISTS', 'FIXED']:
                all_good = False
        
        return all_good
    return False

def update_database(environment):
    """Update database for specified environment"""
    print(f"\n🎯 UPDATING {environment.upper()} DATABASE")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        conn = get_db_connection(environment)
        print(f"✅ Connected to {environment} database")
        
        steps_passed = 0
        total_steps = 3
        
        # Step 1: Add missing clubs
        if add_missing_clubs(conn):
            steps_passed += 1
        
        # Step 2: Check Anne Mooney
        if check_anne_mooney(conn):
            steps_passed += 1
        
        # Step 3: Validate ETL dependencies
        if validate_etl_dependencies(conn):
            steps_passed += 1
        
        conn.close()
        
        print(f"\n📊 {environment.upper()} SUMMARY: {steps_passed}/{total_steps} checks passed")
        
        if steps_passed == total_steps:
            print(f"🎉 {environment.upper()} database is ready for enhanced ETL!")
        else:
            print(f"⚠️ {environment.upper()} database needs attention")
        
        return steps_passed == total_steps
        
    except Exception as e:
        print(f"❌ Failed to update {environment} database: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Update remote databases')
    parser.add_argument('environment', choices=['staging', 'production', 'both'])
    args = parser.parse_args()
    
    print("🚀 REMOTE DATABASE UPDATE SCRIPT")
    print("================================")
    
    success = True
    
    if args.environment in ['staging', 'both']:
        success &= update_database('staging')
    
    if args.environment in ['production', 'both']:
        success &= update_database('production')
    
    print(f"\n🏁 FINAL RESULT: {'SUCCESS' if success else 'PARTIAL FAILURE'}")
    
    if success:
        print("✅ All database updates completed successfully!")
        print("🔧 Enhanced ETL import process is ready to run")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
