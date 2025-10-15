#!/usr/bin/env python3
"""
Quick analysis of the (S) records created during scraper run.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def analyze():
    print("=" * 80)
    print("QUICK ANALYSIS OF NEW (S) RECORDS")
    print("=" * 80)
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get the 4 active (S) records created
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   s.name as series_name, t.team_name, p.created_at
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE (p.first_name LIKE '%(S)' OR p.last_name LIKE '%(S)')
            AND p.created_at > NOW() - INTERVAL '24 hours'
            AND p.is_active = true
            ORDER BY p.created_at
        """)
        
        active_s = cursor.fetchall()
        
        print(f"Found {len(active_s)} active (S) records created recently:")
        print()
        
        for player in active_s:
            print(f"Player: {player['first_name']} {player['last_name']}")
            print(f"  Tenniscores ID: {player['tenniscores_player_id']}")
            print(f"  Series: {player['series_name']}")
            print(f"  Team: {player['team_name']}")
            print(f"  Created: {player['created_at']}")
            print()
            
            # Check if this player has a regular counterpart
            clean_name = player['first_name'].replace('(S)', '').strip()
            
            cursor.execute("""
                SELECT p.id, p.first_name, p.last_name, p.is_active
                FROM players p
                WHERE p.tenniscores_player_id = %s
                AND p.first_name NOT LIKE %s
                AND p.last_name NOT LIKE %s
                AND p.is_active = true
                LIMIT 1
            """, (player['tenniscores_player_id'], '%(S)', '%(S)'))
            
            regular = cursor.fetchone()
            
            if regular:
                print(f"  ✓ Has regular counterpart: {regular['first_name']} {regular['last_name']} (ID: {regular['id']})")
            else:
                print(f"  ✗ No regular counterpart found")
            print()
        
        print("=" * 80)
        print("CONCLUSION")
        print("=" * 80)
        print("The scraper fixes were deployed but still created (S) records.")
        print("This suggests either:")
        print("1. The scraper code wasn't actually running the fixed version")
        print("2. There's a different code path creating these records")
        print("3. The (S) suffix is being added somewhere else in the pipeline")
        print("=" * 80)
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    analyze()
