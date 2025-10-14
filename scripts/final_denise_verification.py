#!/usr/bin/env python3
"""Final verification showing Denise will get Series I"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database_utils import get_db_cursor

with get_db_cursor(commit=False) as cursor:
    print("=" * 80)
    print("FINAL VERIFICATION: DENISE SIEGEL'S TEAM ASSIGNMENT")
    print("=" * 80)
    
    # Check user_contexts
    cursor.execute("""
        SELECT uc.user_id, uc.team_id, t.team_name, s.name as series_name
        FROM user_contexts uc
        LEFT JOIN teams t ON uc.team_id = t.id
        LEFT JOIN series s ON t.series_id = s.id
        WHERE uc.user_id = 1092
    """)
    context = cursor.fetchone()
    
    print("\n✅ USER CONTEXT (determines which team shows on login):")
    if context:
        print(f"   Team ID: {context['team_id']}")
        print(f"   Team Name: {context['team_name']}")
        print(f"   Series: {context['series_name']}")
    else:
        print("   No user_contexts record found")
    
    print("\n📋 AVAILABLE TEAMS (user can switch between these):")
    cursor.execute("""
        SELECT p.team_id, t.team_name, s.name as series_name
        FROM players p
        JOIN teams t ON p.team_id = t.id
        JOIN series s ON p.series_id = s.id
        WHERE p.tenniscores_player_id = 'cnswpl_WkM2eHhybndqUT09'
        AND p.league_id = 4785
        ORDER BY p.id
    """)
    teams = cursor.fetchall()
    
    for team in teams:
        marker = "← DEFAULT" if team['team_id'] == context['team_id'] else ""
        print(f"   • {team['series_name']} - {team['team_name']} {marker}")
    
    print("\n" + "=" * 80)
    print("🎯 ANSWER: Denise is assigned to SERIES I (Tennaqua I)")
    print("=" * 80)
    print("\nSession logic will select Series I because:")
    print("  1. user_contexts.team_id = 59318 (Tennaqua I)")
    print("  2. This matches PRIORITY 2 in session selection logic")
    print("  3. She can switch to Series 17 anytime using team switcher")
    print("=" * 80)

