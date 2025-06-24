#!/usr/bin/env python3
"""
Assign Teams to Unassigned Players - Phase 2 (Medium-term)

This script assigns teams to the 5,243 players who currently have no team 
assignment (team_id = NULL) based on their match participation.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def assign_teams_to_unassigned_players():
    """Assign teams to players who currently have no team assignment"""
    print("=" * 80)
    print("PHASE 2: ASSIGNING TEAMS TO UNASSIGNED PLAYERS")
    print("=" * 80)
    
    # First, get all players with no team assignment who have match data
    print("1. Identifying players with no team assignment...")
    
    unassigned_query = """
        WITH player_match_teams AS (
            SELECT 
                CASE 
                    WHEN ms.home_player_1_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.home_player_2_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.away_player_1_id = p.tenniscores_player_id THEN ms.away_team
                    WHEN ms.away_player_2_id = p.tenniscores_player_id THEN ms.away_team
                END as match_team,
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                COUNT(*) as match_count
            FROM players p
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            WHERE p.team_id IS NULL 
            AND p.is_active = TRUE
            GROUP BY p.tenniscores_player_id, p.first_name, p.last_name, match_team
        ),
        player_primary_teams AS (
            SELECT 
                tenniscores_player_id,
                first_name,
                last_name,
                match_team as primary_match_team,
                match_count,
                ROW_NUMBER() OVER (
                    PARTITION BY tenniscores_player_id 
                    ORDER BY match_count DESC
                ) as rn
            FROM player_match_teams
        )
        SELECT *
        FROM player_primary_teams
        WHERE rn = 1
        ORDER BY match_count DESC, last_name, first_name
    """
    
    unassigned_players = execute_query(unassigned_query)
    
    print(f"✅ Found {len(unassigned_players)} unassigned players with match data")
    
    if not unassigned_players:
        print("🎉 No unassigned players found!")
        return True
    
    # Show distribution by match count
    print(f"\n2. Distribution by match count:")
    match_counts = {}
    for player in unassigned_players:
        count = player['match_count']
        match_counts[count] = match_counts.get(count, 0) + 1
    
    for count in sorted(match_counts.keys(), reverse=True)[:10]:
        print(f"   {match_counts[count]} players with {count} matches")
    
    # Show preview of assignments
    print(f"\n3. Preview of assignments (first 15):")
    print("-" * 70)
    for i, player in enumerate(unassigned_players[:15]):
        print(f"   {i+1}. {player['first_name']} {player['last_name']}")
        print(f"      → {player['primary_match_team']} ({player['match_count']} matches)")
    
    if len(unassigned_players) > 15:
        print(f"   ... and {len(unassigned_players) - 15} more")
    
    # Ask for confirmation  
    print(f"\n4. Ready to assign teams to {len(unassigned_players)} players")
    response = input("Proceed with assigning teams to all unassigned players? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled.")
        return False
    
    print(f"\n5. Processing assignments...")
    
    successful_assignments = 0
    failed_assignments = 0
    
    for i, player in enumerate(unassigned_players):
        try:
            if (i + 1) % 100 == 0:  # Progress indicator
                print(f"   Progress: [{i+1}/{len(unassigned_players)}] ({(i+1)/len(unassigned_players)*100:.1f}%)")
            
            # Find the team_id for the primary_match_team
            target_team_query = """
                SELECT id FROM teams 
                WHERE team_name = %s
                LIMIT 1
            """
            
            target_team = execute_query_one(target_team_query, [player['primary_match_team']])
            
            if not target_team:
                print(f"      ❌ Could not find team: {player['primary_match_team']}")
                failed_assignments += 1
                continue
            
            target_team_id = target_team['id']
            
            # Update the player's team assignment
            update_query = """
                UPDATE players 
                SET team_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE tenniscores_player_id = %s
            """
            
            execute_query(update_query, [target_team_id, player['tenniscores_player_id']])
            successful_assignments += 1
            
        except Exception as e:
            print(f"      ❌ Error assigning {player['first_name']} {player['last_name']}: {e}")
            failed_assignments += 1
    
    print(f"\n6. Assignment Summary:")
    print(f"   ✅ Successfully assigned: {successful_assignments}")
    print(f"   ❌ Failed to assign: {failed_assignments}")
    print(f"   📊 Success rate: {(successful_assignments / len(unassigned_players) * 100):.1f}%")
    
    if successful_assignments > 0:
        print(f"\n🎉 Phase 2 Complete! {successful_assignments} players now have team assignments.")
        print(f"   These players will now appear in their team's track-byes-courts pages.")
    
    return successful_assignments > 0

def check_remaining_unassigned():
    """Check how many players still have no team assignment"""
    print(f"\n7. Checking remaining unassigned players...")
    
    # Check players with no team assignment
    remaining_query = """
        SELECT COUNT(*) as unassigned_count
        FROM players p
        WHERE p.team_id IS NULL 
        AND p.is_active = TRUE
    """
    
    result = execute_query_one(remaining_query)
    remaining_unassigned = result['unassigned_count'] if result else 0
    
    print(f"   Players still without team assignment: {remaining_unassigned}")
    
    # Check if these players have any matches
    no_matches_query = """
        SELECT COUNT(*) as no_matches_count
        FROM players p
        WHERE p.team_id IS NULL 
        AND p.is_active = TRUE
        AND NOT EXISTS (
            SELECT 1 FROM match_scores ms 
            WHERE ms.home_player_1_id = p.tenniscores_player_id
            OR ms.home_player_2_id = p.tenniscores_player_id
            OR ms.away_player_1_id = p.tenniscores_player_id
            OR ms.away_player_2_id = p.tenniscores_player_id
        )
    """
    
    no_matches_result = execute_query_one(no_matches_query)
    no_matches_count = no_matches_result['no_matches_count'] if no_matches_result else 0
    
    print(f"   Players without matches (can't assign): {no_matches_count}")
    print(f"   Players with matches but no team found: {remaining_unassigned - no_matches_count}")
    
    return remaining_unassigned

def show_team_size_improvements():
    """Show how team sizes have improved after assignments"""
    print(f"\n8. Team size improvements:")
    
    team_sizes_query = """
        SELECT 
            t.team_name,
            COUNT(p.id) as player_count
        FROM teams t
        LEFT JOIN players p ON t.id = p.team_id AND p.is_active = TRUE
        GROUP BY t.id, t.team_name
        HAVING COUNT(p.id) > 0
        ORDER BY COUNT(p.id) DESC
        LIMIT 10
    """
    
    team_sizes = execute_query(team_sizes_query)
    
    print("   Top 10 teams by player count:")
    for i, team in enumerate(team_sizes):
        print(f"   {i+1}. {team['team_name']}: {team['player_count']} players")
    
    # Count empty teams
    empty_teams_query = """
        SELECT COUNT(*) as empty_count
        FROM teams t
        WHERE NOT EXISTS (
            SELECT 1 FROM players p 
            WHERE p.team_id = t.id AND p.is_active = TRUE
        )
    """
    
    empty_result = execute_query_one(empty_teams_query)
    empty_count = empty_result['empty_count'] if empty_result else 0
    
    print(f"\n   Empty teams remaining: {empty_count}")

if __name__ == "__main__":
    print("Starting Phase 2: Assign Teams to Unassigned Players")
    print("This assigns teams to players who currently have team_id = NULL\n")
    
    success = assign_teams_to_unassigned_players()
    
    if success:
        remaining = check_remaining_unassigned()
        show_team_size_improvements()
        
        print(f"\n🎉 PHASE 2 COMPLETED!")
        print(f"   Most players now have team assignments based on match participation.")
        print(f"   {remaining} players still need manual review or have no match data.")
        print(f"   Ready to proceed to Phase 3: Rebuild ETL process.")
    else:
        print(f"\n❌ PHASE 2 FAILED")
        print(f"   Please review the errors above and try again.") 