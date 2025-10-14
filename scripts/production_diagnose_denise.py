#!/usr/bin/env python3
"""
PRODUCTION diagnostic for Denise Siegel's team visibility issue.
Player ID: cnswpl_WkM2eHhybndqUT09
Expected team: Series I in CNSWPL
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Production database URL
PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def diagnose_production():
    """Investigate Denise Siegel's account on production."""
    
    player_id = 'cnswpl_WkM2eHhybndqUT09'
    
    print("=" * 80)
    print("PRODUCTION: DENISE SIEGEL TEAM VISIBILITY DIAGNOSTIC")
    print("=" * 80)
    print(f"Player ID: {player_id}")
    print(f"Expected Team: Series I in CNSWPL")
    print("=" * 80)
    print()
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. Check if player exists in players table
        print("1. PLAYER RECORD IN PLAYERS TABLE")
        print("-" * 80)
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   l.league_name, c.name as club_name, s.name as series_name, p.team_id
            FROM players p
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
        """, (player_id,))
        player_record = cursor.fetchone()
        
        if player_record:
            print(f"✓ Player found:")
            print(f"  Database ID: {player_record['id']}")
            print(f"  Name: {player_record['first_name']} {player_record['last_name']}")
            print(f"  League: {player_record['league_name']}")
            print(f"  Club: {player_record['club_name']}")
            print(f"  Series: {player_record['series_name']}")
            print(f"  Team ID: {player_record['team_id']}")
        else:
            print(f"✗ Player NOT found with ID: {player_id}")
            cursor.close()
            conn.close()
            return
        print()
        
        # 2. Check if user account exists
        print("2. USER ACCOUNT")
        print("-" * 80)
        cursor.execute("""
            SELECT id, email, first_name, last_name, tenniscores_player_id, league_id
            FROM users
            WHERE tenniscores_player_id = %s OR (LOWER(first_name) = 'denise' AND LOWER(last_name) = 'siegel')
        """, (player_id,))
        user_record = cursor.fetchone()
        
        if user_record:
            user_id = user_record['id']
            print(f"✓ User account found:")
            print(f"  User ID: {user_id}")
            print(f"  Email: {user_record['email']}")
            print(f"  Name: {user_record['first_name']} {user_record['last_name']}")
            print(f"  Tenniscores Player ID: {user_record['tenniscores_player_id']}")
            print(f"  Current League ID: {user_record['league_id']}")
        else:
            print(f"✗ No user account found")
            cursor.close()
            conn.close()
            return
        print()
        
        # 3. Check user_player_associations
        print("3. USER PLAYER ASSOCIATIONS")
        print("-" * 80)
        cursor.execute("""
            SELECT upa.user_id, upa.tenniscores_player_id, upa.is_primary,
                   p.first_name, p.last_name, 
                   l.league_name, c.name as club_name, s.name as series_name
            FROM user_player_associations upa
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE upa.user_id = %s
            ORDER BY upa.is_primary DESC, l.league_name
        """, (user_id,))
        associations = cursor.fetchall()
        
        if associations:
            print(f"✓ Found {len(associations)} association(s):")
            for assoc in associations:
                print(f"  Player: {assoc['first_name']} {assoc['last_name']}")
                print(f"    Tenniscores ID: {assoc['tenniscores_player_id']}")
                print(f"    League: {assoc['league_name']}")
                print(f"    Club: {assoc['club_name']}")
                print(f"    Series: {assoc['series_name']}")
                print(f"    Is Primary: {assoc['is_primary']}")
                print()
        else:
            print(f"✗ No associations found for user_id: {user_id}")
        print()
        
        # 4. Check user_contexts
        print("4. USER CONTEXTS")
        print("-" * 80)
        cursor.execute("""
            SELECT uc.user_id, uc.team_id, t.team_name, s.name as series_name
            FROM user_contexts uc
            LEFT JOIN teams t ON uc.team_id = t.id
            LEFT JOIN series s ON t.series_id = s.id
            WHERE uc.user_id = %s
        """, (user_id,))
        context = cursor.fetchone()
        
        if context:
            print(f"✓ User context found:")
            print(f"  Team ID: {context['team_id']}")
            print(f"  Team Name: {context['team_name']}")
            print(f"  Series: {context['series_name']}")
        else:
            print(f"✗ No user_contexts record")
        print()
        
        # 5. Check all player records for Denise Siegel in CNSWPL
        print("5. ALL PLAYER RECORDS FOR 'SIEGEL' IN CNSWPL")
        print("-" * 80)
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   c.name as club_name, s.name as series_name, p.team_id
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE LOWER(p.last_name) LIKE '%siegel%' AND l.league_name ILIKE '%North Shore Women%'
            ORDER BY s.name
        """)
        all_records = cursor.fetchall()
        
        if all_records:
            print(f"✓ Found {len(all_records)} record(s):")
            for record in all_records:
                print(f"  Player ID (DB): {record['id']}")
                print(f"    Name: {record['first_name']} {record['last_name']}")
                print(f"    Tenniscores ID: {record['tenniscores_player_id']}")
                print(f"    Club: {record['club_name']}")
                print(f"    Series: {record['series_name']}")
                print(f"    Team ID: {record['team_id']}")
                print()
        print()
        
        # 6. Get CNSWPL league ID
        print("6. CNSWPL LEAGUE ID")
        print("-" * 80)
        cursor.execute("""
            SELECT id, league_name
            FROM leagues
            WHERE league_name ILIKE '%North Shore Women%'
        """)
        league = cursor.fetchone()
        
        if league:
            print(f"✓ League found:")
            print(f"  League ID: {league['id']}")
            print(f"  League Name: {league['league_name']}")
            cnswpl_league_id = league['id']
        else:
            print(f"✗ CNSWPL league not found")
            cnswpl_league_id = None
        print()
        
        # 7. Find Series I team ID
        print("7. SERIES I TEAM FOR TENNAQUA")
        print("-" * 80)
        cursor.execute("""
            SELECT t.id, t.team_name, s.name as series_name
            FROM teams t
            JOIN series s ON t.series_id = s.id
            JOIN clubs c ON t.club_id = c.id
            WHERE c.name = 'Tennaqua' AND s.name ILIKE '%Series I%'
        """)
        series_i_team = cursor.fetchone()
        
        if series_i_team:
            print(f"✓ Series I team found:")
            print(f"  Team ID: {series_i_team['id']}")
            print(f"  Team Name: {series_i_team['team_name']}")
            print(f"  Series: {series_i_team['series_name']}")
            series_i_team_id = series_i_team['id']
        else:
            print(f"✗ Series I team not found")
            series_i_team_id = None
        print()
        
        # Summary
        print("=" * 80)
        print("DIAGNOSIS SUMMARY")
        print("=" * 80)
        print(f"User ID: {user_id}")
        print(f"User Email: {user_record['email']}")
        print(f"Current tenniscores_player_id: {user_record['tenniscores_player_id']}")
        print(f"Current league_id: {user_record['league_id']}")
        print(f"Correct tenniscores_player_id: {player_id}")
        print(f"Correct league_id: {cnswpl_league_id}")
        print(f"Target team_id (Series I): {series_i_team_id}")
        print("=" * 80)
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    diagnose_production()

