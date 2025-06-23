#!/usr/bin/env python3
"""
Script to diagnose and fix match count issues in the track-byes-courts page.
This script can be run to check all players on a team and identify any discrepancies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def check_team_match_counts():
    """Check match counts for all players and identify any issues"""
    
    print("=== TEAM MATCH COUNT DIAGNOSTIC ===")
    print()
    
    # Get all active teams
    teams = execute_query("""
        SELECT DISTINCT t.id, t.team_name, t.team_alias, COUNT(p.id) as player_count
        FROM teams t
        LEFT JOIN players p ON t.id = p.team_id AND p.is_active = TRUE
        GROUP BY t.id, t.team_name, t.team_alias
        HAVING COUNT(p.id) > 0
        ORDER BY t.team_name
    """)
    
    print(f"Found {len(teams)} teams with active players:")
    for i, team in enumerate(teams):
        print(f"{i+1}. {team['team_name']} ({team['player_count']} players)")
    
    print()
    team_choice = input("Enter team number to check (or 'all' for all teams): ").strip()
    
    if team_choice.lower() == 'all':
        selected_teams = teams
    else:
        try:
            team_index = int(team_choice) - 1
            if 0 <= team_index < len(teams):
                selected_teams = [teams[team_index]]
            else:
                print("Invalid team number")
                return
        except ValueError:
            print("Invalid input")
            return
    
    print()
    print("=== CHECKING MATCH COUNTS ===")
    
    for team in selected_teams:
        print(f"\nTeam: {team['team_name']}")
        print("-" * 50)
        
        # Get team members
        team_members = execute_query("""
            SELECT id, first_name, last_name, tenniscores_player_id, league_id
            FROM players 
            WHERE team_id = %s AND is_active = TRUE
            ORDER BY first_name, last_name
        """, [team['id']])
        
        if not team_members:
            print("No active players found")
            continue
            
        issues_found = []
        
        for member in team_members:
            player_id = member['tenniscores_player_id']
            player_name = f"{member['first_name']} {member['last_name']}"
            user_league_id = member['league_id']
            
            if not player_id:
                issues_found.append(f"{player_name}: No tenniscores_player_id")
                continue
            
            # Get total matches (unfiltered)
            total_matches = execute_query_one("""
                SELECT COUNT(DISTINCT id) as match_count
                FROM match_scores
                WHERE home_player_1_id = %s 
                   OR home_player_2_id = %s 
                   OR away_player_1_id = %s 
                   OR away_player_2_id = %s
            """, [player_id, player_id, player_id, player_id])
            
            total_count = total_matches['match_count'] if total_matches else 0
            
            # Get filtered matches (with league filter if applicable)
            filtered_count = total_count
            if user_league_id:
                # Test league filtering
                league_id_int = None
                if isinstance(user_league_id, str) and user_league_id != "":
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                elif isinstance(user_league_id, int):
                    league_id_int = user_league_id
                
                if league_id_int:
                    filtered_matches = execute_query_one("""
                        SELECT COUNT(DISTINCT id) as match_count
                        FROM match_scores
                        WHERE (home_player_1_id = %s 
                           OR home_player_2_id = %s 
                           OR away_player_1_id = %s 
                           OR away_player_2_id = %s)
                        AND league_id = %s
                    """, [player_id, player_id, player_id, player_id, league_id_int])
                    
                    filtered_count = filtered_matches['match_count'] if filtered_matches else 0
            
            # Check for the specific problematic player ID
            is_problematic = player_id == "nndz-WkNPd3g3citnQT09"
            
            status = "✓"
            if total_count == 0:
                status = "⚠️  No matches"
            elif is_problematic:
                status = "🔍 Reported issue"
            elif filtered_count != total_count:
                status = f"⚠️  Filter discrepancy"
            
            print(f"{status} {player_name}")
            print(f"   ID: {player_id}")
            print(f"   Total: {total_count}, Filtered: {filtered_count}, League: {user_league_id}")
            
            if total_count == 0:
                issues_found.append(f"{player_name}: Zero matches found")
            elif filtered_count != total_count:
                issues_found.append(f"{player_name}: Filtered count ({filtered_count}) differs from total ({total_count})")
        
        if issues_found:
            print(f"\n⚠️  Issues found for {team['team_name']}:")
            for issue in issues_found:
                print(f"   - {issue}")
        else:
            print(f"\n✅ No issues found for {team['team_name']}")

if __name__ == "__main__":
    check_team_match_counts() 