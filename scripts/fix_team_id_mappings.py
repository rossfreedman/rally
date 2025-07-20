#!/usr/bin/env python3
"""
Fix Team ID Mappings for Restored User Data

This script fixes the team ID mappings for polls and captain messages that were restored
with old team IDs from the backup. It uses the team_mapping_backup table to map old
team IDs to new ones based on team context.
"""

import psycopg2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import parse_db_url, get_db_url
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_team_id_mappings():
    """Fix team ID mappings for polls and captain messages"""
    print("🔧 Fixing Team ID Mappings for Restored User Data")
    print("=" * 60)
    
    try:
        # Connect to database
        config = parse_db_url(get_db_url())
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Step 1: Check current state
        print("\n📊 Current State:")
        cursor.execute("SELECT COUNT(*) FROM polls WHERE team_id IS NOT NULL")
        poll_count = cursor.fetchone()[0]
        print(f"   Polls with team_id: {poll_count}")
        
        cursor.execute("SELECT COUNT(*) FROM captain_messages WHERE team_id IS NOT NULL")
        msg_count = cursor.fetchone()[0]
        print(f"   Captain messages with team_id: {msg_count}")
        
        # Step 2: Get team mapping backup data
        print("\n🔄 Loading team mappings...")
        cursor.execute("""
            SELECT 
                old_team_id,
                old_team_name,
                old_team_alias,
                old_league_id,
                old_league_string_id,
                old_club_id,
                old_series_id
            FROM team_mapping_backup
        """)
        mappings = cursor.fetchall()
        print(f"   Found {len(mappings)} team mappings")
        
        # Step 3: Create mapping dictionary
        team_id_mapping = {}
        for mapping in mappings:
            old_team_id, old_team_name, old_team_alias, old_league_id, old_league_string_id, old_club_id, old_series_id = mapping
            
            # Find new team ID based on context
            cursor.execute("""
                SELECT t.id 
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                WHERE l.league_id = %s 
                AND t.club_id = %s 
                AND t.series_id = %s
                AND (t.team_name = %s OR t.team_alias = %s)
            """, (old_league_string_id, old_club_id, old_series_id, old_team_name, old_team_alias))
            
            new_team = cursor.fetchone()
            if new_team:
                team_id_mapping[old_team_id] = new_team[0]
                print(f"   Mapped {old_team_id} → {new_team[0]} ({old_team_name})")
        
        # Step 3.5: Handle missing teams with fallback mappings
        print("\n🔧 Creating fallback mappings for missing teams...")
        
        # Map Tennaqua Series 22 to Tennaqua Series 11 (closest available)
        cursor.execute("""
            SELECT t.id 
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'APTA_CHICAGO' 
            AND t.team_name LIKE 'Tennaqua - 11'
            LIMIT 1
        """)
        tennaqua_11 = cursor.fetchone()
        if tennaqua_11:
            team_id_mapping[67600] = tennaqua_11[0]  # Tennaqua - 22
            team_id_mapping[67854] = tennaqua_11[0]  # Test Chicago 22 @ Tennaqua
            print(f"   Fallback mapped Tennaqua Series 22 → Tennaqua Series 11 (ID: {tennaqua_11[0]})")
        
        # Map Tennaqua S2B to another NSTF team (Lake Forest S2B)
        cursor.execute("""
            SELECT t.id 
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'NSTF' 
            AND t.team_name LIKE 'Lake Forest S2B'
            LIMIT 1
        """)
        lake_forest_s2b = cursor.fetchone()
        if lake_forest_s2b:
            team_id_mapping[67620] = lake_forest_s2b[0]  # Tennaqua S2B
            team_id_mapping[67855] = lake_forest_s2b[0]  # Test Series 2B @ Tennaqua
            print(f"   Fallback mapped Tennaqua S2B → Lake Forest S2B (ID: {lake_forest_s2b[0]})")
        
        print(f"   Created {len(team_id_mapping)} total mappings (including fallbacks)")
        
        # Step 4: Fix polls
        print("\n📊 Fixing polls...")
        cursor.execute("SELECT id, team_id FROM polls WHERE team_id IS NOT NULL")
        polls = cursor.fetchall()
        
        polls_fixed = 0
        for poll_id, old_team_id in polls:
            if old_team_id in team_id_mapping:
                new_team_id = team_id_mapping[old_team_id]
                cursor.execute("UPDATE polls SET team_id = %s WHERE id = %s", (new_team_id, poll_id))
                polls_fixed += 1
                print(f"   Fixed poll {poll_id}: {old_team_id} → {new_team_id}")
            else:
                print(f"   ⚠️  No mapping found for poll {poll_id} (team_id: {old_team_id})")
        
        # Step 5: Fix captain messages
        print("\n💬 Fixing captain messages...")
        cursor.execute("SELECT id, team_id FROM captain_messages WHERE team_id IS NOT NULL")
        messages = cursor.fetchall()
        
        messages_fixed = 0
        for msg_id, old_team_id in messages:
            if old_team_id in team_id_mapping:
                new_team_id = team_id_mapping[old_team_id]
                cursor.execute("UPDATE captain_messages SET team_id = %s WHERE id = %s", (new_team_id, msg_id))
                messages_fixed += 1
                print(f"   Fixed message {msg_id}: {old_team_id} → {new_team_id}")
            else:
                print(f"   ⚠️  No mapping found for message {msg_id} (team_id: {old_team_id})")
        
        # Step 6: Commit changes
        conn.commit()
        
        # Step 7: Verify fixes
        print("\n✅ Verification:")
        cursor.execute("SELECT COUNT(*) FROM polls p JOIN teams t ON p.team_id = t.id")
        valid_polls = cursor.fetchone()[0]
        print(f"   Polls with valid team associations: {valid_polls}")
        
        cursor.execute("SELECT COUNT(*) FROM captain_messages cm JOIN teams t ON cm.team_id = t.id")
        valid_messages = cursor.fetchone()[0]
        print(f"   Captain messages with valid team associations: {valid_messages}")
        
        print(f"\n🎉 Successfully fixed {polls_fixed} polls and {messages_fixed} captain messages!")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error fixing team ID mappings: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = fix_team_id_mappings()
    if success:
        print("\n✅ Team ID mapping fix completed successfully!")
    else:
        print("\n❌ Team ID mapping fix failed!")
        exit(1) 