#!/usr/bin/env python3

"""
Debug script to investigate staging database ID mismatches
Checks what league 4693 and team 42417 represent, and finds Ross's actual data
"""

import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_staging_ids():
    """Check what the staging IDs represent and find Ross's actual data"""
    from database_utils import execute_query, execute_query_one
    
    print("🔍 STAGING DATABASE ID INVESTIGATION")
    print("=" * 50)
    
    # Ross's details
    ross_player_id = "nndz-WkMrK3didjlnUT09"
    ross_email = "rossfreedman@gmail.com"
    
    # Staging IDs (wrong)
    staging_league_id = 4693
    staging_team_id = 42417
    
    # Local IDs (correct)
    local_league_id = 4683  
    local_team_id = 44279
    
    print(f"🏓 Ross's Player ID: {ross_player_id}")
    print(f"📧 Ross's Email: {ross_email}")
    print()
    
    # 1. Check what staging league 4693 is
    print("1️⃣ CHECKING STAGING LEAGUE 4693:")
    staging_league = execute_query_one(
        "SELECT id, league_id, league_name FROM leagues WHERE id = %s",
        [staging_league_id]
    )
    if staging_league:
        print(f"   League 4693 = {staging_league['league_name']} (league_id: {staging_league['league_id']})")
    else:
        print(f"   ❌ League 4693 not found!")
    print()
    
    # 2. Check what staging team 42417 is  
    print("2️⃣ CHECKING STAGING TEAM 42417:")
    staging_team = execute_query_one(
        "SELECT id, team_name, league_id FROM teams WHERE id = %s",
        [staging_team_id]
    )
    if staging_team:
        print(f"   Team 42417 = '{staging_team['team_name']}' in league {staging_team['league_id']}")
    else:
        print(f"   ❌ Team 42417 not found!")
    print()
    
    # 3. Check if local league 4683 exists on staging
    print("3️⃣ CHECKING IF LOCAL LEAGUE 4683 EXISTS ON STAGING:")
    local_league_on_staging = execute_query_one(
        "SELECT id, league_id, league_name FROM leagues WHERE id = %s",
        [local_league_id]
    )
    if local_league_on_staging:
        print(f"   ✅ League 4683 = {local_league_on_staging['league_name']} (league_id: {local_league_on_staging['league_id']})")
    else:
        print(f"   ❌ League 4683 not found on staging!")
    print()
    
    # 4. Check if local team 44279 exists on staging
    print("4️⃣ CHECKING IF LOCAL TEAM 44279 EXISTS ON STAGING:")
    local_team_on_staging = execute_query_one(
        "SELECT id, team_name, league_id FROM teams WHERE id = %s",
        [local_team_id]
    )
    if local_team_on_staging:
        print(f"   ✅ Team 44279 = '{local_team_on_staging['team_name']}' in league {local_team_on_staging['league_id']}")
    else:
        print(f"   ❌ Team 44279 not found on staging!")
    print()
    
    # 5. Search for Ross's matches by player ID (regardless of league/team)
    print("5️⃣ SEARCHING FOR ROSS'S MATCHES ON STAGING (ANY LEAGUE/TEAM):")
    ross_matches = execute_query(
        """
        SELECT 
            league_id,
            home_team_id,
            away_team_id,
            home_team,
            away_team,
            COUNT(*) as match_count,
            MIN(match_date) as earliest_match,
            MAX(match_date) as latest_match
        FROM match_scores 
        WHERE home_player_1_id = %s OR home_player_2_id = %s 
           OR away_player_1_id = %s OR away_player_2_id = %s
        GROUP BY league_id, home_team_id, away_team_id, home_team, away_team
        ORDER BY match_count DESC
        """,
        [ross_player_id, ross_player_id, ross_player_id, ross_player_id]
    )
    
    if ross_matches:
        print(f"   ✅ Found {len(ross_matches)} different team contexts for Ross:")
        for i, match_group in enumerate(ross_matches, 1):
            print(f"   {i}. League {match_group['league_id']} | Teams: {match_group['home_team']} vs {match_group['away_team']}")
            print(f"      Team IDs: {match_group['home_team_id']} vs {match_group['away_team_id']}")
            print(f"      {match_group['match_count']} matches | {match_group['earliest_match']} to {match_group['latest_match']}")
            print()
    else:
        print(f"   ❌ No matches found for Ross's player ID on staging!")
    print()
    
    # 6. Check Ross's user association on staging
    print("6️⃣ CHECKING ROSS'S USER ASSOCIATION ON STAGING:")
    ross_user = execute_query_one(
        "SELECT id, email, league_context FROM users WHERE email = %s",
        [ross_email]
    )
    if ross_user:
        print(f"   User ID: {ross_user['id']}")
        print(f"   League Context: {ross_user['league_context']}")
        
        # Check his player associations
        associations = execute_query(
            """
            SELECT upa.tenniscores_player_id, p.league_id, p.team_id, 
                   t.team_name, l.league_name, p.first_name, p.last_name
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id  
            JOIN teams t ON p.team_id = t.id
            JOIN leagues l ON p.league_id = l.id
            WHERE upa.user_id = %s
            """,
            [ross_user['id']]
        )
        
        if associations:
            print(f"   📋 Player Associations ({len(associations)}):")
            for j, assoc in enumerate(associations, 1):
                print(f"      {j}. {assoc['first_name']} {assoc['last_name']} | Player ID: {assoc['tenniscores_player_id']}")
                print(f"         League: {assoc['league_name']} (ID: {assoc['league_id']})")
                print(f"         Team: {assoc['team_name']} (ID: {assoc['team_id']})")
                print()
        else:
            print(f"   ❌ No player associations found!")
    else:
        print(f"   ❌ Ross's user account not found on staging!")
    
    print("=" * 50)
    print("🎯 SUMMARY:")
    if ross_matches:
        best_match = ross_matches[0]  # Most matches
        print(f"✅ Ross's match data is in League {best_match['league_id']}")
        print(f"✅ Most matches in teams {best_match['home_team_id']} vs {best_match['away_team_id']}")
        print(f"❌ But his user account is associated with League {staging_league_id}, Team {staging_team_id}")
        print(f"🔧 SOLUTION: Update Ross's user league_context from {staging_league_id} to {best_match['league_id']}")
    else:
        print(f"❌ No match data found for Ross on staging - database sync issue!")

if __name__ == "__main__":
    debug_staging_ids() 