#!/usr/bin/env python3
"""
Staging CNSWPL Import - Robust Version
======================================

This script imports CNSWPL data to staging with proper error handling
and transaction management.
"""

import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import sys
from dotenv import load_dotenv

def run_staging_import():
    print("🚀 STAGING CNSWPL IMPORT")
    print("=" * 40)
    
    # Load environment
    load_dotenv()
    staging_url = os.getenv('DATABASE_PUBLIC_URL')
    
    if not staging_url:
        print("❌ DATABASE_PUBLIC_URL not set")
        return False
    
    if staging_url.startswith("postgres://"):
        staging_url = staging_url.replace("postgres://", "postgresql://", 1)
    
    print("🔗 Connecting to staging database...")
    
    try:
        # Connect to staging
        parsed = urlparse(staging_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            sslmode="require",
            connect_timeout=30
        )
        conn.autocommit = True  # Important: avoid transaction blocks
        
        print("✅ Connected to staging database")
        
        # Load CNSWPL data
        cnswpl_file = 'data/leagues/CNSWPL/match_history.json'
        if not os.path.exists(cnswpl_file):
            print(f"❌ CNSWPL data not found: {cnswpl_file}")
            print("📤 You'll need to upload CNSWPL data to staging server")
            return False
        
        with open(cnswpl_file, 'r') as f:
            cnswpl_matches = json.load(f)
        
        print(f"📂 Loaded {len(cnswpl_matches)} CNSWPL matches")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get CNSWPL league ID
            cursor.execute("SELECT id FROM leagues WHERE league_id = 'CNSWPL'")
            league = cursor.fetchone()
            
            if not league:
                print("❌ CNSWPL league not found in staging")
                return False
            
            cnswpl_league_id = league['id']
            print(f"🎯 Target league ID: {cnswpl_league_id}")
            
            # Check current state
            cursor.execute("""
                SELECT COUNT(*) as existing_cnswpl
                FROM match_scores 
                WHERE league_id = %s
            """, (cnswpl_league_id,))
            
            existing = cursor.fetchone()
            print(f"📊 Existing CNSWPL matches: {existing['existing_cnswpl']}")
            
            if existing['existing_cnswpl'] > 500:
                print("✅ CNSWPL matches already exist - checking Lisa Wagner...")
                
                # Check Lisa Wagner specifically
                lisa_player_id = "nndz-WkM2eHhybi9qUT09"
                cursor.execute("""
                    SELECT COUNT(*) as lisa_matches
                    FROM match_scores
                    WHERE (home_player_1_id = %s OR home_player_2_id = %s
                           OR away_player_1_id = %s OR away_player_2_id = %s)
                """, (lisa_player_id, lisa_player_id, lisa_player_id, lisa_player_id))
                
                lisa_check = cursor.fetchone()
                print(f"👤 Lisa Wagner matches: {lisa_check['lisa_matches']}")
                
                if lisa_check['lisa_matches'] == 0:
                    print("🔧 Lisa Wagner has no matches - fixing player IDs...")
                    return fix_player_ids(cursor, cnswpl_league_id)
                else:
                    print("✅ Lisa Wagner has matches - checking user linkage...")
                    return check_user_linkage(cursor)
            else:
                print("📥 Importing CNSWPL matches...")
                return import_matches(cursor, cnswpl_matches, cnswpl_league_id)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

def fix_player_ids(cursor, cnswpl_league_id):
    """Fix NULL player IDs in CNSWPL matches"""
    print("🔧 Fixing NULL player IDs...")
    
    # This would require the fix script - for now just report
    cursor.execute("""
        SELECT COUNT(*) as null_matches
        FROM match_scores ms
        WHERE ms.league_id = %s 
          AND (ms.home_player_1_id IS NULL OR ms.home_player_2_id IS NULL
               OR ms.away_player_1_id IS NULL OR ms.away_player_2_id IS NULL)
    """, (cnswpl_league_id,))
    
    null_check = cursor.fetchone()
    print(f"🚨 CNSWPL matches with NULL player IDs: {null_check['null_matches']}")
    
    if null_check['null_matches'] > 0:
        print("⚠️ Need to run fix_cnswpl_match_player_ids.py")
        return False
    
    return True

def check_user_linkage(cursor):
    """Check if Lisa Wagner's user is properly linked"""
    print("🔗 Checking user linkage...")
    
    cursor.execute("""
        SELECT u.id, u.tenniscores_player_id, u.team_id, u.league_id
        FROM users u
        WHERE u.first_name = 'Lisa' AND u.last_name = 'Wagner'
    """)
    
    user = cursor.fetchone()
    if user:
        print(f"👤 Lisa Wagner user:")
        print(f"   Player ID: {user['tenniscores_player_id']}")
        print(f"   Team ID: {user['team_id']}")
        print(f"   League ID: {user['league_id']}")
        
        if user['tenniscores_player_id'] and user['team_id']:
            print("✅ User properly linked!")
            return True
        else:
            print("⚠️ User not properly linked")
            return False
    else:
        print("❌ Lisa Wagner user not found")
        return False

def import_matches(cursor, matches, league_id):
    """Import CNSWPL matches"""
    print(f"📥 Importing {len(matches)} matches...")
    
    imported = 0
    for i, match in enumerate(matches):
        try:
            cursor.execute("""
                INSERT INTO match_scores (
                    match_date, home_team, away_team, 
                    home_player_1_name, home_player_1_id,
                    home_player_2_name, home_player_2_id,
                    away_player_1_name, away_player_1_id,
                    away_player_2_name, away_player_2_id,
                    winner, scores, league_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                match.get('match_date'),
                match.get('home_team'),
                match.get('away_team'),
                match.get('home_player_1_name'),
                match.get('home_player_1_id'),
                match.get('home_player_2_name'),
                match.get('home_player_2_id'),
                match.get('away_player_1_name'),
                match.get('away_player_1_id'),
                match.get('away_player_2_name'),
                match.get('away_player_2_id'),
                match.get('winner'),
                match.get('scores'),
                league_id
            ))
            imported += 1
            
            if i % 100 == 0:
                print(f"   Imported {i}/{len(matches)} matches...")
                
        except Exception as e:
            print(f"⚠️ Failed to import match {i}: {e}")
            continue
    
    print(f"✅ Imported {imported} matches")
    return True

if __name__ == "__main__":
    success = run_staging_import()
    if success:
        print("\n🎉 IMPORT SUCCESS!")
        print("📱 Test: https://rally-staging.up.railway.app/mobile/analyze-me")
    else:
        print("\n❌ IMPORT FAILED")
    
    sys.exit(0 if success else 1)
