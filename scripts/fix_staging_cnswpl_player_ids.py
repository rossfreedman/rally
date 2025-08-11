#!/usr/bin/env python3
"""
Fix CNSWPL Player IDs on Staging
================================

This script connects directly to staging database and fixes NULL player IDs
in CNSWPL match_scores by linking player names to their database player IDs.
"""

import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import sys

def get_staging_connection():
    """Get connection to staging database"""
    # Hardcode staging URL or use environment variable
    staging_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
    
    if not staging_url:
        print("❌ DATABASE_URL not found. Run this script on staging server.")
        return None
    
    if staging_url.startswith("postgres://"):
        staging_url = staging_url.replace("postgres://", "postgresql://", 1)
    
    try:
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
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def fix_cnswpl_player_ids():
    """Fix NULL player IDs in CNSWPL matches"""
    print("🔧 FIXING CNSWPL PLAYER IDs ON STAGING")
    print("=" * 50)
    
    conn = get_staging_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get CNSWPL league ID
            cursor.execute("SELECT id FROM leagues WHERE league_id = 'CNSWPL'")
            league = cursor.fetchone()
            if not league:
                print("❌ CNSWPL league not found")
                return False
            
            cnswpl_league_id = league['id']
            print(f"🎯 CNSWPL league ID: {cnswpl_league_id}")
            
            # Check current state
            cursor.execute("""
                SELECT COUNT(*) as total_matches,
                       COUNT(CASE WHEN home_player_1_id IS NULL THEN 1 END) as null_home_1,
                       COUNT(CASE WHEN home_player_2_id IS NULL THEN 1 END) as null_home_2,
                       COUNT(CASE WHEN away_player_1_id IS NULL THEN 1 END) as null_away_1,
                       COUNT(CASE WHEN away_player_2_id IS NULL THEN 1 END) as null_away_2
                FROM match_scores 
                WHERE league_id = %s
            """, (cnswpl_league_id,))
            
            stats = cursor.fetchone()
            print(f"📊 CNSWPL Match Stats:")
            print(f"   Total matches: {stats['total_matches']}")
            print(f"   NULL home_player_1_id: {stats['null_home_1']}")
            print(f"   NULL home_player_2_id: {stats['null_home_2']}")
            print(f"   NULL away_player_1_id: {stats['null_away_1']}")
            print(f"   NULL away_player_2_id: {stats['null_away_2']}")
            
            if stats['total_matches'] == 0:
                print("❌ No CNSWPL matches found!")
                return False
            
            # Build player name to ID mapping
            print(f"\n🔗 Building player name → ID mapping...")
            cursor.execute("""
                SELECT tenniscores_player_id, first_name, last_name,
                       LOWER(TRIM(first_name || ' ' || last_name)) as full_name_lower
                FROM players p
                JOIN leagues l ON p.league_id = l.id
                WHERE l.league_id = 'CNSWPL'
            """)
            
            players = cursor.fetchall()
            player_mapping = {}
            for player in players:
                full_name = player['full_name_lower']
                player_mapping[full_name] = player['tenniscores_player_id']
            
            print(f"✅ Built mapping for {len(player_mapping)} CNSWPL players")
            
            # Check for Lisa Wagner specifically
            lisa_key = 'lisa wagner'
            if lisa_key in player_mapping:
                print(f"👤 Found Lisa Wagner: {player_mapping[lisa_key]}")
            else:
                print(f"⚠️ Lisa Wagner not found in player mapping!")
                print(f"   Available players: {list(player_mapping.keys())[:10]}...")
            
            # Fix NULL player IDs
            print(f"\n🔧 Fixing NULL player IDs...")
            fixed_count = 0
            
            # Get matches with NULL IDs
            cursor.execute("""
                SELECT id, home_player_1_name, home_player_2_name, 
                       away_player_1_name, away_player_2_name,
                       home_player_1_id, home_player_2_id,
                       away_player_1_id, away_player_2_id
                FROM match_scores 
                WHERE league_id = %s
                  AND (home_player_1_id IS NULL OR home_player_2_id IS NULL
                       OR away_player_1_id IS NULL OR away_player_2_id IS NULL)
            """, (cnswpl_league_id,))
            
            null_matches = cursor.fetchall()
            print(f"🔍 Found {len(null_matches)} matches with NULL player IDs")
            
            for match in null_matches:
                match_id = match['id']
                updates = []
                params = []
                
                # Check each player position
                positions = [
                    ('home_player_1_name', 'home_player_1_id'),
                    ('home_player_2_name', 'home_player_2_id'),
                    ('away_player_1_name', 'away_player_1_id'),
                    ('away_player_2_name', 'away_player_2_id')
                ]
                
                for name_field, id_field in positions:
                    player_name = match[name_field]
                    player_id = match[id_field]
                    
                    if player_name and not player_id:
                        # Try to find player ID
                        normalized_name = player_name.lower().strip()
                        if normalized_name in player_mapping:
                            found_id = player_mapping[normalized_name]
                            updates.append(f"{id_field} = %s")
                            params.append(found_id)
                            
                            if 'lisa wagner' in normalized_name:
                                print(f"✅ Found Lisa Wagner match! Setting {id_field} = {found_id}")
                
                # Apply updates if any found
                if updates:
                    update_query = f"""
                        UPDATE match_scores 
                        SET {', '.join(updates)}
                        WHERE id = %s
                    """
                    params.append(match_id)
                    
                    cursor.execute(update_query, params)
                    fixed_count += 1
            
            print(f"\n✅ Fixed {fixed_count} match records!")
            
            # Verify Lisa Wagner now has matches
            lisa_player_id = player_mapping.get('lisa wagner')
            if lisa_player_id:
                cursor.execute("""
                    SELECT COUNT(*) as lisa_matches
                    FROM match_scores
                    WHERE league_id = %s
                      AND (home_player_1_id = %s OR home_player_2_id = %s
                           OR away_player_1_id = %s OR away_player_2_id = %s)
                """, (cnswpl_league_id, lisa_player_id, lisa_player_id, lisa_player_id, lisa_player_id))
                
                lisa_check = cursor.fetchone()
                print(f"👤 Lisa Wagner now has {lisa_check['lisa_matches']} matches!")
                
                if lisa_check['lisa_matches'] > 0:
                    print(f"🎉 SUCCESS! Lisa Wagner's analyze-me page should now show data!")
                else:
                    print(f"⚠️ Lisa Wagner still has no matches - check name variations")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = fix_cnswpl_player_ids()
    if success:
        print(f"\n🎉 CNSWPL PLAYER ID FIX COMPLETE!")
        print(f"📱 Test: https://rally-staging.up.railway.app/mobile/analyze-me")
    else:
        print(f"\n❌ FIX FAILED")
    
    sys.exit(0 if success else 1)
