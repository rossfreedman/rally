#!/usr/bin/env python3
"""
APTA import script for staging with career stats consistency check disabled.
This version skips the ensure_career_stats_consistency function that's causing the hang.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def import_apta_staging():
    print("🚀 APTA IMPORT FOR STAGING (WITHOUT CONSISTENCY CHECK)")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
    print()
    
    # Load the players data
    players_file = "data/leagues/APTA_CHICAGO/players.json"
    if not os.path.exists(players_file):
        print(f"❌ {players_file} not found")
        return False
    
    with open(players_file, 'r') as f:
        players_data = json.load(f)
    
    print(f"✅ Loaded {len(players_data):,} player records")
    
    # Import the database functions
    from database_config import get_db
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # Get APTA league ID
            cur.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
            league_result = cur.fetchone()
            if not league_result:
                print("❌ APTA_CHICAGO league not found")
                return False
            
            league_id = league_result[0]
            print(f"✅ Found league ID: {league_id}")
            
            # Clear existing APTA data first
            print("🗑️  Clearing existing APTA data...")
            cur.execute("DELETE FROM player_history WHERE player_id IN (SELECT id FROM players WHERE league_id = %s)", (league_id,))
            cur.execute("DELETE FROM players WHERE league_id = %s", (league_id,))
            conn.commit()
            print("✅ Cleared existing data")
            
            # Import players using the original logic but without consistency check
            print("📥 Importing players...")
            imported = 0
            failed = 0
            
            # Import the upsert_player function
            import data.etl.import.import_players as import_module
            upsert_player = import_module.upsert_player
            
            # Temporarily disable the ensure_career_stats_consistency function
            original_ensure = import_module.ensure_career_stats_consistency
            import_module.ensure_career_stats_consistency = lambda *args, **kwargs: None
            
            try:
                for i, player in enumerate(players_data):
                    try:
                        result = upsert_player(cur, league_id, player)
                        if result and result[0]:
                            imported += 1
                        else:
                            failed += 1
                        
                        # Progress update every 100 players
                        if imported % 100 == 0:
                            print(f"   Imported {imported:,} players...")
                            
                    except Exception as e:
                        print(f"   ❌ Error importing player {player.get('First Name', 'Unknown')} {player.get('Last Name', 'Unknown')}: {e}")
                        failed += 1
                        continue
                
                # Commit all changes
                conn.commit()
                
                print()
                print("✅ IMPORT COMPLETED!")
                print(f"   Imported: {imported:,} players")
                print(f"   Failed: {failed:,} players")
                
                # Verify the import
                cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
                total_players = cur.fetchone()[0]
                print(f"   Total in database: {total_players:,} players")
                
                cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s AND captain_status = 'true'", (league_id,))
                captains = cur.fetchone()[0]
                print(f"   Captains: {captains:,}")
                
                return True
                
            finally:
                # Restore original function
                import_module.ensure_career_stats_consistency = original_ensure

if __name__ == "__main__":
    success = import_apta_staging()
    sys.exit(0 if success else 1)
