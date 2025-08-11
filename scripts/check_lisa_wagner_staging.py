#!/usr/bin/env python3
"""
Check Lisa Wagner Data on Staging
=================================

This script checks Lisa Wagner's match data on staging database.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_lisa_wagner_data():
    print("🔍 CHECKING LISA WAGNER DATA ON STAGING")
    print("=" * 50)

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # Check Lisa Wagner player ID matches
        player_id = "nndz-WkM2eHhybi9qUT09"
        cursor.execute("""
            SELECT COUNT(*) as matches
            FROM match_scores ms
            JOIN leagues l ON ms.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND (ms.home_player_1_id = %s OR ms.home_player_2_id = %s
                   OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s)
        """, (player_id, player_id, player_id, player_id))
        
        result = cursor.fetchone()
        print(f"📊 Lisa Wagner player ID matches: {result['matches']}")
        
        # Check matches by name
        cursor.execute("""
            SELECT COUNT(*) as name_matches
            FROM match_scores ms
            JOIN leagues l ON ms.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND (LOWER(ms.home_player_1_name) LIKE '%lisa%wagner%' 
                   OR LOWER(ms.home_player_2_name) LIKE '%lisa%wagner%'
                   OR LOWER(ms.away_player_1_name) LIKE '%lisa%wagner%'
                   OR LOWER(ms.away_player_2_name) LIKE '%lisa%wagner%')
        """)
        
        name_result = cursor.fetchone()
        print(f"👤 Lisa Wagner name matches: {name_result['name_matches']}")
        
        # Check total CNSWPL matches
        cursor.execute("""
            SELECT COUNT(*) as total_cnswpl
            FROM match_scores ms
            JOIN leagues l ON ms.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
        """)
        
        total_result = cursor.fetchone()
        print(f"🏆 Total CNSWPL matches: {total_result['total_cnswpl']}")
        
        # Check NULL player IDs in CNSWPL
        cursor.execute("""
            SELECT COUNT(*) as null_ids
            FROM match_scores ms
            JOIN leagues l ON ms.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND (ms.home_player_1_id IS NULL OR ms.home_player_2_id IS NULL
                   OR ms.away_player_1_id IS NULL OR ms.away_player_2_id IS NULL)
        """)
        
        null_result = cursor.fetchone()
        print(f"🚨 CNSWPL matches with NULL player IDs: {null_result['null_ids']}")
        
        # Sample some matches to see the data
        cursor.execute("""
            SELECT ms.match_date, ms.home_team, ms.away_team,
                   ms.home_player_1_name, ms.home_player_1_id,
                   ms.home_player_2_name, ms.home_player_2_id
            FROM match_scores ms
            JOIN leagues l ON ms.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND (ms.home_team LIKE '%Tennaqua%' OR ms.away_team LIKE '%Tennaqua%')
            LIMIT 3
        """)
        
        sample_matches = cursor.fetchall()
        print(f"\n📋 Sample Tennaqua matches:")
        for match in sample_matches:
            print(f"   {match['match_date']} | {match['home_team']} vs {match['away_team']}")
            print(f"      Home: {match['home_player_1_name']} ({match['home_player_1_id']}) & {match['home_player_2_name']} ({match['home_player_2_id']})")

    conn.close()

if __name__ == "__main__":
    check_lisa_wagner_data()
