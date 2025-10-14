#!/usr/bin/env python3
"""
PRODUCTION FIX for Denise Siegel's team visibility issue.

This script will:
1. Set users.tenniscores_player_id = 'cnswpl_WkM2eHhybndqUT09'
2. Set users.league_id to CNSWPL league ID
3. Ensure user_player_associations exists and is marked primary
4. Set user_contexts.team_id to Series I team (Tennaqua I)
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Production database URL
PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def fix_denise_production():
    """Fix Denise Siegel's account on production."""
    
    player_id = 'cnswpl_WkM2eHhybndqUT09'
    
    print("=" * 80)
    print("PRODUCTION: FIXING DENISE SIEGEL'S ACCOUNT")
    print("=" * 80)
    print()
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Step 1: Find the user
        print("STEP 1: Finding user...")
        print("-" * 80)
        cursor.execute("""
            SELECT id, email, first_name, last_name, tenniscores_player_id, league_id
            FROM users
            WHERE LOWER(first_name) = 'denise' AND LOWER(last_name) = 'siegel'
        """)
        user = cursor.fetchone()
        
        if not user:
            print("✗ User not found!")
            return
        
        user_id = user['id']
        print(f"✓ Found user:")
        print(f"  User ID: {user_id}")
        print(f"  Email: {user['email']}")
        print(f"  Current tenniscores_player_id: {user['tenniscores_player_id']}")
        print(f"  Current league_id: {user['league_id']}")
        print()
        
        # Step 2: Get CNSWPL league ID
        print("STEP 2: Finding CNSWPL league ID...")
        print("-" * 80)
        cursor.execute("""
            SELECT id, league_name
            FROM leagues
            WHERE league_name ILIKE '%North Shore Women%'
        """)
        league = cursor.fetchone()
        
        if not league:
            print("✗ CNSWPL league not found!")
            return
        
        cnswpl_league_id = league['id']
        print(f"✓ Found CNSWPL league:")
        print(f"  League ID: {cnswpl_league_id}")
        print(f"  League Name: {league['league_name']}")
        print()
        
        # Step 3: Find Series I team for Tennaqua
        print("STEP 3: Finding Series I team...")
        print("-" * 80)
        cursor.execute("""
            SELECT t.id, t.team_name, s.name as series_name
            FROM teams t
            JOIN series s ON t.series_id = s.id
            JOIN clubs c ON t.club_id = c.id
            WHERE c.name = 'Tennaqua' AND s.name ILIKE '%Series I%'
            LIMIT 1
        """)
        series_i_team = cursor.fetchone()
        
        if not series_i_team:
            print("✗ Series I team not found!")
            return
        
        series_i_team_id = series_i_team['id']
        print(f"✓ Found Series I team:")
        print(f"  Team ID: {series_i_team_id}")
        print(f"  Team Name: {series_i_team['team_name']}")
        print(f"  Series: {series_i_team['series_name']}")
        print()
        
        # Step 4: Update users table
        print("STEP 4: Updating users table...")
        print("-" * 80)
        cursor.execute("""
            UPDATE users
            SET tenniscores_player_id = %s,
                league_id = %s
            WHERE id = %s
        """, (player_id, cnswpl_league_id, user_id))
        print(f"✓ Updated users table:")
        print(f"  Set tenniscores_player_id = {player_id}")
        print(f"  Set league_id = {cnswpl_league_id}")
        print()
        
        # Step 5: Check/update user_player_associations
        print("STEP 5: Updating user_player_associations...")
        print("-" * 80)
        
        # Check if association exists
        cursor.execute("""
            SELECT * FROM user_player_associations
            WHERE user_id = %s AND tenniscores_player_id = %s
        """, (user_id, player_id))
        association = cursor.fetchone()
        
        if association:
            print(f"✓ Association already exists")
            # Set it as primary
            cursor.execute("""
                UPDATE user_player_associations
                SET is_primary = false
                WHERE user_id = %s
            """, (user_id,))
            cursor.execute("""
                UPDATE user_player_associations
                SET is_primary = true
                WHERE user_id = %s AND tenniscores_player_id = %s
            """, (user_id, player_id))
            print(f"✓ Marked association as primary")
        else:
            print(f"Creating new association...")
            cursor.execute("""
                INSERT INTO user_player_associations (user_id, tenniscores_player_id, is_primary)
                VALUES (%s, %s, true)
            """, (user_id, player_id))
            print(f"✓ Created primary association")
        print()
        
        # Step 6: Set user_contexts to Series I team
        print("STEP 6: Setting user_contexts to Series I team...")
        print("-" * 80)
        
        # Check if user_contexts exists
        cursor.execute("""
            SELECT * FROM user_contexts WHERE user_id = %s
        """, (user_id,))
        context = cursor.fetchone()
        
        if context:
            print(f"Updating existing user_contexts...")
            cursor.execute("""
                UPDATE user_contexts
                SET team_id = %s
                WHERE user_id = %s
            """, (series_i_team_id, user_id))
            print(f"✓ Updated user_contexts.team_id = {series_i_team_id}")
        else:
            print(f"Creating new user_contexts...")
            cursor.execute("""
                INSERT INTO user_contexts (user_id, team_id)
                VALUES (%s, %s)
            """, (user_id, series_i_team_id))
            print(f"✓ Created user_contexts with team_id = {series_i_team_id}")
        print()
        
        # Commit all changes
        conn.commit()
        
        # Verification
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        
        cursor.execute("""
            SELECT u.id, u.email, u.tenniscores_player_id, u.league_id,
                   l.league_name, uc.team_id, t.team_name, s.name as series_name
            FROM users u
            LEFT JOIN leagues l ON u.league_id = l.id
            LEFT JOIN user_contexts uc ON u.id = uc.user_id
            LEFT JOIN teams t ON uc.team_id = t.id
            LEFT JOIN series s ON t.series_id = s.id
            WHERE u.id = %s
        """, (user_id,))
        result = cursor.fetchone()
        
        print(f"User ID: {result['id']}")
        print(f"Email: {result['email']}")
        print(f"Tenniscores Player ID: {result['tenniscores_player_id']}")
        print(f"League ID: {result['league_id']} ({result['league_name']})")
        print(f"Default Team ID: {result['team_id']} ({result['team_name']})")
        print(f"Default Series: {result['series_name']}")
        print()
        
        print("=" * 80)
        print("✅ FIX COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Ask Denise to log out and log back in")
        print("2. She should now see her Series I team (Tennaqua I)")
        print("3. She can switch to Series 17 if needed using the team switcher")
        print("=" * 80)
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    response = input("⚠️  This will modify PRODUCTION database. Continue? (yes/no): ")
    if response.lower() == 'yes':
        fix_denise_production()
    else:
        print("Aborted.")

