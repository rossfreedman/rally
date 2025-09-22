#!/usr/bin/env python3
"""
Clean staging database to match local JSON exactly.
Remove all APTA players that are not in the current JSON file.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def clean_staging_database():
    print("🧹 CLEANING STAGING DATABASE")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load local players data
    with open("data/leagues/APTA_CHICAGO/players.json", 'r') as f:
        local_players = json.load(f)
    
    local_player_ids = {player['Player ID'] for player in local_players}
    print(f"✅ Local JSON has {len(local_player_ids):,} unique player IDs")
    
    # Connect to staging database
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    import psycopg2
    
    with psycopg2.connect(staging_url) as conn:
        with conn.cursor() as cur:
            # Get APTA league ID
            cur.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
            league_result = cur.fetchone()
            league_id = league_result[0]
            
            # Get current staging player count
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
            current_count = cur.fetchone()[0]
            print(f"📊 Current staging players: {current_count:,}")
            
            # Get players to keep (those in local JSON)
            cur.execute("""
                SELECT id, tenniscores_player_id, first_name, last_name
                FROM players 
                WHERE league_id = %s 
                AND tenniscores_player_id IN %s
            """, (league_id, tuple(local_player_ids)))
            
            players_to_keep = cur.fetchall()
            print(f"✅ Players to keep: {len(players_to_keep):,}")
            
            # Get players to remove
            cur.execute("""
                SELECT id, tenniscores_player_id, first_name, last_name
                FROM players 
                WHERE league_id = %s 
                AND (tenniscores_player_id NOT IN %s OR tenniscores_player_id IS NULL OR tenniscores_player_id = '')
            """, (league_id, tuple(local_player_ids)))
            
            players_to_remove = cur.fetchall()
            print(f"🗑️  Players to remove: {len(players_to_remove):,}")
            
            if not players_to_remove:
                print("✅ No players need to be removed - staging is already clean!")
                return True
            
            # Show sample of players to be removed
            print(f"\n📋 SAMPLE OF PLAYERS TO BE REMOVED:")
            for i, (player_id, tenniscores_id, first_name, last_name) in enumerate(players_to_remove[:10], 1):
                print(f"   {i:2d}. {first_name} {last_name} ({tenniscores_id})")
            
            if len(players_to_remove) > 10:
                print(f"   ... and {len(players_to_remove) - 10:,} more")
            
            # Confirm removal
            print(f"\n⚠️  WARNING: This will permanently delete {len(players_to_remove):,} player records!")
            print("This includes all their team assignments, career stats, and related data.")
            
            # Remove players
            print(f"\n🗑️  Removing {len(players_to_remove):,} players...")
            
            # First, remove from player_history table
            cur.execute("""
                DELETE FROM player_history 
                WHERE player_id IN (
                    SELECT id FROM players 
                    WHERE league_id = %s 
                    AND (tenniscores_player_id NOT IN %s OR tenniscores_player_id IS NULL OR tenniscores_player_id = '')
                )
            """, (league_id, tuple(local_player_ids)))
            
            history_deleted = cur.rowcount
            print(f"   ✅ Removed {history_deleted:,} player history records")
            
            # Then remove from players table
            cur.execute("""
                DELETE FROM players 
                WHERE league_id = %s 
                AND (tenniscores_player_id NOT IN %s OR tenniscores_player_id IS NULL OR tenniscores_player_id = '')
            """, (league_id, tuple(local_player_ids)))
            
            players_deleted = cur.rowcount
            print(f"   ✅ Removed {players_deleted:,} player records")
            
            # Commit changes
            conn.commit()
            print(f"   ✅ Changes committed to database")
            
            # Verify final count
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
            final_count = cur.fetchone()[0]
            print(f"\n📊 Final staging players: {final_count:,}")
            print(f"📊 Expected (from JSON): {len(local_player_ids):,}")
            
            if final_count == len(local_player_ids):
                print("✅ SUCCESS: Staging database now matches local JSON exactly!")
                return True
            else:
                print(f"❌ MISMATCH: Expected {len(local_player_ids):,} but got {final_count:,}")
                return False

if __name__ == "__main__":
    success = clean_staging_database()
    sys.exit(0 if success else 1)
