#!/usr/bin/env python3
"""
Fix Poll Team Mappings to Teams with Users

This script remaps polls and captain messages to teams that actually have users
so they show up in the UI. The current mappings are to teams with no users.
"""

import psycopg2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import parse_db_url, get_db_url
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_poll_team_mappings():
    """Remap polls and captain messages to teams with users"""
    print("🔧 Fixing Poll Team Mappings to Teams with Users")
    print("=" * 60)
    
    try:
        # Connect to database
        config = parse_db_url(get_db_url())
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Step 1: Find teams with users
        print("\n📊 Finding teams with users...")
        cursor.execute("""
            SELECT t.id, t.team_name, COUNT(DISTINCT u.id) as user_count
            FROM teams t 
            JOIN players p ON t.id = p.team_id 
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id 
            JOIN users u ON upa.user_id = u.id 
            GROUP BY t.id, t.team_name 
            ORDER BY user_count DESC
        """)
        teams_with_users = cursor.fetchall()
        print(f"   Found {len(teams_with_users)} teams with users")
        
        # Step 2: Create mapping from current teams to teams with users
        print("\n🔄 Creating team mappings...")
        
        # Map Tennaqua - 11 (no users) to Tennaqua - 22 (6 users)
        tennaqua_22_id = None
        for team_id, team_name, user_count in teams_with_users:
            if team_name == "Tennaqua - 22":
                tennaqua_22_id = team_id
                break
        
        # Map Lake Forest S2B (no users) to Tennaqua S2B (2 users)
        tennaqua_s2b_id = None
        for team_id, team_name, user_count in teams_with_users:
            if team_name == "Tennaqua S2B":
                tennaqua_s2b_id = team_id
                break
        
        print(f"   Tennaqua - 22 (ID: {tennaqua_22_id}): {next((t[2] for t in teams_with_users if t[0] == tennaqua_22_id), 0)} users")
        print(f"   Tennaqua S2B (ID: {tennaqua_s2b_id}): {next((t[2] for t in teams_with_users if t[0] == tennaqua_s2b_id), 0)} users")
        
        # Step 3: Fix polls
        print("\n📊 Fixing polls...")
        polls_fixed = 0
        
        if tennaqua_22_id:
            cursor.execute("UPDATE polls SET team_id = %s WHERE team_id = 69468", (tennaqua_22_id,))
            polls_fixed += cursor.rowcount
            print(f"   Mapped {cursor.rowcount} polls from Tennaqua - 11 to Tennaqua - 22")
        
        if tennaqua_s2b_id:
            cursor.execute("UPDATE polls SET team_id = %s WHERE team_id = 69127", (tennaqua_s2b_id,))
            polls_fixed += cursor.rowcount
            print(f"   Mapped {cursor.rowcount} polls from Lake Forest S2B to Tennaqua S2B")
        
        # Step 4: Fix captain messages
        print("\n💬 Fixing captain messages...")
        messages_fixed = 0
        
        if tennaqua_22_id:
            cursor.execute("UPDATE captain_messages SET team_id = %s WHERE team_id = 69468", (tennaqua_22_id,))
            messages_fixed += cursor.rowcount
            print(f"   Mapped {cursor.rowcount} messages from Tennaqua - 11 to Tennaqua - 22")
        
        if tennaqua_s2b_id:
            cursor.execute("UPDATE captain_messages SET team_id = %s WHERE team_id = 69127", (tennaqua_s2b_id,))
            messages_fixed += cursor.rowcount
            print(f"   Mapped {cursor.rowcount} messages from Lake Forest S2B to Tennaqua S2B")
        
        # Step 5: Commit changes
        conn.commit()
        
        # Step 6: Verify fixes
        print("\n✅ Verification:")
        cursor.execute("""
            SELECT t.team_name, COUNT(p.id) as poll_count, COUNT(cm.id) as message_count
            FROM teams t
            LEFT JOIN polls p ON t.id = p.team_id
            LEFT JOIN captain_messages cm ON t.id = cm.team_id
            WHERE t.team_name IN ('Tennaqua - 22', 'Tennaqua S2B')
            GROUP BY t.id, t.team_name
        """)
        results = cursor.fetchall()
        for team_name, poll_count, message_count in results:
            print(f"   {team_name}: {poll_count} polls, {message_count} messages")
        
        print(f"\n🎉 Successfully remapped {polls_fixed} polls and {messages_fixed} captain messages!")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error fixing poll team mappings: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = fix_poll_team_mappings()
    if success:
        print("\n✅ Poll team mapping fix completed successfully!")
    else:
        print("\n❌ Poll team mapping fix failed!")
        exit(1) 