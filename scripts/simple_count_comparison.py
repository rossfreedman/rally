#!/usr/bin/env python3
"""
Simple count comparison between JSON and staging.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def simple_count_comparison():
    print("🔍 SIMPLE COUNT COMPARISON")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load local players data
    with open("data/leagues/APTA_CHICAGO/players.json", 'r') as f:
        local_players = json.load(f)
    
    print(f"📊 JSON DATA:")
    print(f"   Total records: {len(local_players):,}")
    
    # Count unique players
    unique_players = set(player['Player ID'] for player in local_players)
    print(f"   Unique players: {len(unique_players):,}")
    
    # Count by series
    series_count = {}
    for player in local_players:
        series = player.get('Series', 'Unknown')
        series_count[series] = series_count.get(series, 0) + 1
    
    print(f"   Unique series: {len(series_count):,}")
    print(f"   Top 5 series:")
    for series, count in sorted(series_count.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"     {series}: {count:,} players")
    
    print()
    
    # Connect to staging database
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    import psycopg2
    
    with psycopg2.connect(staging_url) as conn:
        with conn.cursor() as cur:
            # Get APTA league ID
            cur.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
            league_result = cur.fetchone()
            league_id = league_result[0]
            
            print(f"📊 STAGING DATABASE:")
            
            # Total players
            cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
            total_staging = cur.fetchone()[0]
            print(f"   Total records: {total_staging:,}")
            
            # Unique players
            cur.execute("""
                SELECT COUNT(DISTINCT tenniscores_player_id) 
                FROM players 
                WHERE league_id = %s AND tenniscores_player_id IS NOT NULL AND tenniscores_player_id != ''
            """, (league_id,))
            unique_staging = cur.fetchone()[0]
            print(f"   Unique players: {unique_staging:,}")
            
            # Count by series
            cur.execute("""
                SELECT s.name, COUNT(*) as count
                FROM players p
                JOIN series s ON p.series_id = s.id
                WHERE p.league_id = %s
                GROUP BY s.name
                ORDER BY count DESC
            """, (league_id,))
            
            staging_series = cur.fetchall()
            print(f"   Unique series: {len(staging_series):,}")
            print(f"   Top 5 series:")
            for series_name, count in staging_series[:5]:
                print(f"     {series_name}: {count:,} players")
            
            print()
            
            # Calculate difference
            difference = total_staging - len(local_players)
            print(f"📊 DIFFERENCE:")
            print(f"   Staging - JSON: {difference:,} records")
            print(f"   Percentage: {(difference / len(local_players)) * 100:.1f}%")
            
            if difference == 0:
                print("✅ PERFECT MATCH!")
            elif difference > 0:
                print(f"❌ Staging has {difference:,} extra records")
            else:
                print(f"❌ Staging has {abs(difference):,} fewer records")

if __name__ == "__main__":
    simple_count_comparison()
