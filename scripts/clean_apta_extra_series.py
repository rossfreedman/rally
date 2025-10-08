#!/usr/bin/env python3
"""
Clean APTA_CHICAGO extra series from staging database.
Remove Series A, B, C, D, E, F that shouldn't be in APTA.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def clean_apta_extra_series():
    print("🧹 CLEANING APTA_CHICAGO EXTRA SERIES FROM STAGING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load local players data to get the correct series list
    with open("data/leagues/APTA_CHICAGO/players.json", 'r') as f:
        local_players = json.load(f)
    
    json_series = set(player['Series'] for player in local_players)
    print(f"✅ APTA_CHICAGO JSON has {len(json_series)} valid series")
    print(f"   Valid series: {sorted(json_series)}")
    print()
    
    # Connect to staging database
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    import psycopg2
    
    with psycopg2.connect(staging_url) as conn:
        with conn.cursor() as cur:
            # Get APTA_CHICAGO league ID
            cur.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
            league_result = cur.fetchone()
            if not league_result:
                print("❌ APTA_CHICAGO league not found in staging")
                return False
            
            league_id = league_result[0]
            print(f"✅ Found APTA_CHICAGO league ID: {league_id}")
            
            # Get current APTA_CHICAGO player count
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
            current_count = cur.fetchone()[0]
            print(f"📊 Current APTA_CHICAGO players: {current_count:,}")
            
            # Find series that are in staging but not in JSON (invalid series)
            cur.execute("""
                SELECT DISTINCT s.name, s.id, COUNT(p.id) as player_count
                FROM players p
                JOIN series s ON p.series_id = s.id
                WHERE p.league_id = %s
                GROUP BY s.name, s.id
                ORDER BY s.name
            """, (league_id,))
            
            staging_series = cur.fetchall()
            staging_series_names = {row[0] for row in staging_series}
            
            invalid_series = staging_series_names - json_series
            print(f"❌ Invalid series in APTA_CHICAGO (not in JSON): {len(invalid_series)}")
            
            if invalid_series:
                for series_name in sorted(invalid_series):
                    series_count = next((count for name, _, count in staging_series if name == series_name), 0)
                    print(f"   {series_name}: {series_count:,} players")
                
                print(f"\n⚠️  WARNING: This will remove {len(invalid_series)} invalid series from APTA_CHICAGO!")
                print("This will NOT affect CNSWPL or any other league data.")
                
                # Remove players from invalid series
                print(f"\n🗑️  Removing players from invalid series...")
                
                # First, remove from player_history table
                cur.execute("""
                    DELETE FROM player_history 
                    WHERE player_id IN (
                        SELECT p.id 
                        FROM players p
                        JOIN series s ON p.series_id = s.id
                        WHERE p.league_id = %s 
                        AND s.name = ANY(%s)
                    )
                """, (league_id, list(invalid_series)))
                
                history_deleted = cur.rowcount
                print(f"   ✅ Removed {history_deleted:,} player history records")
                
                # Then remove from players table
                cur.execute("""
                    DELETE FROM players 
                    WHERE id IN (
                        SELECT p.id 
                        FROM players p
                        JOIN series s ON p.series_id = s.id
                        WHERE p.league_id = %s 
                        AND s.name = ANY(%s)
                    )
                """, (league_id, list(invalid_series)))
                
                players_deleted = cur.rowcount
                print(f"   ✅ Removed {players_deleted:,} player records")
                
                # Commit changes
                conn.commit()
                print(f"   ✅ Changes committed to database")
                
                # Verify final count
                cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
                final_count = cur.fetchone()[0]
                print(f"\n📊 Final APTA_CHICAGO players: {final_count:,}")
                print(f"📊 Expected (from JSON): {len(local_players):,}")
                
                if final_count == len(local_players):
                    print("✅ SUCCESS: APTA_CHICAGO database now matches JSON exactly!")
                    return True
                else:
                    print(f"❌ Still have mismatch: {final_count:,} vs {len(local_players):,}")
                    
                    # Show remaining series
                    cur.execute("""
                        SELECT DISTINCT s.name, COUNT(p.id) as player_count
                        FROM players p
                        JOIN series s ON p.series_id = s.id
                        WHERE p.league_id = %s
                        GROUP BY s.name
                        ORDER BY player_count DESC
                    """, (league_id,))
                    
                    remaining_series = cur.fetchall()
                    print(f"\n📋 REMAINING SERIES IN APTA_CHICAGO:")
                    for series_name, count in remaining_series:
                        status = "✅" if series_name in json_series else "❌"
                        print(f"   {status} {series_name}: {count:,} players")
                    
                    return False
            else:
                print("✅ No invalid series found - APTA_CHICAGO is clean!")
                return True

if __name__ == "__main__":
    success = clean_apta_extra_series()
    sys.exit(0 if success else 1)
