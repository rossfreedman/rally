#!/usr/bin/env python3
"""
Clean production database to match local JSON exactly (AUTO VERSION).
Remove all APTA players that are not in the current JSON file.
This version automatically proceeds without user confirmation.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def clean_production_database_auto():
    print("🧹 CLEANING PRODUCTION DATABASE (AUTO)")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load local players data
    with open("data/leagues/APTA_CHICAGO/players.json", 'r') as f:
        local_players = json.load(f)
    
    local_player_ids = {player['Player ID'] for player in local_players}
    print(f"✅ Local JSON has {len(local_player_ids):,} unique player IDs")
    
    # Connect to production database
    production_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
    import psycopg2
    
    with psycopg2.connect(production_url) as conn:
        with conn.cursor() as cur:
            # Get APTA league ID
            cur.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
            league_result = cur.fetchone()
            league_id = league_result[0]
            
            # Get current production player count
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
            current_count = cur.fetchone()[0]
            print(f"📊 Current production players: {current_count:,}")
            
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
                print("✅ No players need to be removed - production is already clean!")
                return True
            
            # Show sample of players to be removed
            print(f"\n📋 SAMPLE OF PLAYERS TO BE REMOVED:")
            for i, (player_id, tenniscores_id, first_name, last_name) in enumerate(players_to_remove[:10]):
                print(f"   {i+1}. {first_name} {last_name} (ID: {tenniscores_id})")
            
            if len(players_to_remove) > 10:
                print(f"   ... and {len(players_to_remove) - 10} more")
            
            print(f"\n⚠️  AUTO-PROCEEDING: Removing {len(players_to_remove):,} players from production...")
            
            # Remove players from player_history table first
            print(f"\n🗑️  Removing player history records...")
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
            
            # Remove players from players table
            print(f"🗑️  Removing player records...")
            cur.execute("""
                DELETE FROM players 
                WHERE league_id = %s 
                AND (tenniscores_player_id NOT IN %s OR tenniscores_player_id IS NULL OR tenniscores_player_id = '')
            """, (league_id, tuple(local_player_ids)))
            
            players_deleted = cur.rowcount
            print(f"   ✅ Removed {players_deleted:,} player records")
            
            # Clean up invalid series
            print(f"\n🧹 Cleaning up invalid series...")
            
            # Get JSON series
            json_series = set(player['Series'] for player in local_players)
            print(f"   Valid series from JSON: {sorted(json_series)}")
            
            # Find invalid series
            cur.execute("""
                SELECT DISTINCT s.name, COUNT(p.id) as player_count
                FROM players p
                JOIN series s ON p.series_id = s.id
                WHERE p.league_id = %s
                GROUP BY s.name
            """, (league_id,))
            
            db_series_data = cur.fetchall()
            invalid_series = [name for name, count in db_series_data if name not in json_series]
            
            if invalid_series:
                print(f"   Invalid series to remove: {invalid_series}")
                
                # Remove players from invalid series
                cur.execute("""
                    DELETE FROM player_history 
                    WHERE player_id IN (
                        SELECT p.id 
                        FROM players p
                        JOIN series s ON p.series_id = s.id
                        WHERE p.league_id = %s 
                        AND s.name = ANY(%s)
                    )
                """, (league_id, invalid_series))
                
                history_deleted = cur.rowcount
                print(f"   ✅ Removed {history_deleted:,} history records from invalid series")
                
                cur.execute("""
                    DELETE FROM players 
                    WHERE id IN (
                        SELECT p.id 
                        FROM players p
                        JOIN series s ON p.series_id = s.id
                        WHERE p.league_id = %s 
                        AND s.name = ANY(%s)
                    )
                """, (league_id, invalid_series))
                
                series_players_deleted = cur.rowcount
                print(f"   ✅ Removed {series_players_deleted:,} players from invalid series")
            else:
                print(f"   ✅ No invalid series found")
            
            # Commit changes
            conn.commit()
            print(f"\n✅ All changes committed to production database")
            
            # Final verification
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
            final_count = cur.fetchone()[0]
            print(f"\n📊 FINAL COUNTS:")
            print(f"   Players before cleanup: {current_count:,}")
            print(f"   Players after cleanup: {final_count:,}")
            print(f"   Players removed: {current_count - final_count:,}")
            
            return True

if __name__ == "__main__":
    success = clean_production_database_auto()
    sys.exit(0 if success else 1)
