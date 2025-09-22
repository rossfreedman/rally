#!/usr/bin/env python3
"""
Validate APTA Chicago production database against local JSON file.
This script compares the production database with the local players.json file.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def validate_apta_production():
    print("🔍 VALIDATING APTA CHICAGO PRODUCTION DATABASE")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load local players data
    players_file = "data/leagues/APTA_CHICAGO/players.json"
    if not os.path.exists(players_file):
        print(f"❌ {players_file} not found")
        return False
    
    with open(players_file, 'r') as f:
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
            if not league_result:
                print("❌ APTA_CHICAGO league not found in production")
                return False
            
            league_id = league_result[0]
            print(f"✅ Found APTA league ID: {league_id}")
            
            # Get current production player count
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
            current_count = cur.fetchone()[0]
            print(f"📊 Current production players: {current_count:,}")
            
            # Get players that match local JSON
            cur.execute("""
                SELECT id, tenniscores_player_id, first_name, last_name
                FROM players 
                WHERE league_id = %s 
                AND tenniscores_player_id IN %s
            """, (league_id, tuple(local_player_ids)))
            
            players_to_keep = cur.fetchall()
            print(f"✅ Players matching JSON: {len(players_to_keep):,}")
            
            # Get players that don't match local JSON
            cur.execute("""
                SELECT id, tenniscores_player_id, first_name, last_name
                FROM players 
                WHERE league_id = %s 
                AND (tenniscores_player_id NOT IN %s OR tenniscores_player_id IS NULL OR tenniscores_player_id = '')
            """, (league_id, tuple(local_player_ids)))
            
            players_to_remove = cur.fetchall()
            print(f"🗑️  Players to remove: {len(players_to_remove):,}")
            
            # Get series analysis
            cur.execute("""
                SELECT s.name, COUNT(p.id) as player_count
                FROM players p
                JOIN series s ON p.series_id = s.id
                WHERE p.league_id = %s
                GROUP BY s.name
                ORDER BY player_count DESC
            """, (league_id,))
            
            series_data = cur.fetchall()
            print(f"\n📊 SERIES DISTRIBUTION:")
            for series_name, count in series_data:
                print(f"   {series_name}: {count:,} players")
            
            # Get JSON series for comparison
            json_series = set(player['Series'] for player in local_players)
            print(f"\n✅ JSON has {len(json_series)} valid series: {sorted(json_series)}")
            
            # Check for invalid series
            db_series = {row[0] for row in series_data}
            invalid_series = db_series - json_series
            if invalid_series:
                print(f"\n❌ Invalid series in production (not in JSON): {len(invalid_series)}")
                for series_name in sorted(invalid_series):
                    series_count = next((count for name, count in series_data if name == series_name), 0)
                    print(f"   {series_name}: {series_count:,} players")
            else:
                print(f"\n✅ All series in production match JSON")
            
            # Summary
            print(f"\n📋 VALIDATION SUMMARY:")
            print(f"   Total production players: {current_count:,}")
            print(f"   Players matching JSON: {len(players_to_keep):,}")
            print(f"   Players to remove: {len(players_to_remove):,}")
            print(f"   Invalid series: {len(invalid_series)}")
            
            if players_to_remove or invalid_series:
                print(f"\n⚠️  Production database needs cleanup!")
                return False
            else:
                print(f"\n✅ Production database is clean and matches JSON!")
                return True

if __name__ == "__main__":
    success = validate_apta_production()
    sys.exit(0 if success else 1)
