#!/usr/bin/env python3
"""
Fix Mismatched Team Assignments - Phase 1 (Immediate)

This script fixes the 133 players who have team assignments that don't match
their actual match participation, similar to Rob Werman's case.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def fix_mismatched_assignments():
    """Fix players whose assigned team doesn't match their match participation"""
    print("=" * 80)
    print("PHASE 1: FIXING MISMATCHED TEAM ASSIGNMENTS")
    print("=" * 80)
    
    # First, get all players with mismatched assignments (same query as diagnostic)
    print("1. Identifying players with mismatched team assignments...")
    
    mismatched_query = """
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
                t.team_name as assigned_team,
                p.team_id as current_team_id,
                COUNT(*) as match_count
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            WHERE p.is_active = TRUE
            GROUP BY p.tenniscores_player_id, p.first_name, p.last_name, 
                     t.team_name, p.team_id, match_team
        ),
        player_primary_teams AS (
            SELECT 
                tenniscores_player_id,
                first_name,
                last_name,
                assigned_team,
                current_team_id,
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
        AND assigned_team IS NOT NULL 
        AND assigned_team != primary_match_team
        ORDER BY last_name, first_name
    """
    
    mismatched_players = execute_query(mismatched_query)
    
    print(f"✅ Found {len(mismatched_players)} players with mismatched assignments")
    
    if not mismatched_players:
        print("🎉 No mismatched assignments found!")
        return True
    
    # Show preview of changes
    print(f"\n2. Preview of changes (first 10):")
    print("-" * 60)
    for i, player in enumerate(mismatched_players[:10]):
        print(f"   {i+1}. {player['first_name']} {player['last_name']}")
        print(f"      Current: {player['assigned_team']}")
        print(f"      Should be: {player['primary_match_team']} ({player['match_count']} matches)")
    
    if len(mismatched_players) > 10:
        print(f"   ... and {len(mismatched_players) - 10} more")
    
    # Ask for confirmation
    print(f"\n3. Ready to fix {len(mismatched_players)} mismatched assignments")
    response = input("Proceed with fixing all mismatched assignments? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled.")
        return False
    
    print(f"\n4. Processing fixes...")
    
    successful_fixes = 0
    failed_fixes = 0
    
    for i, player in enumerate(mismatched_players):
        try:
            print(f"   [{i+1}/{len(mismatched_players)}] Fixing {player['first_name']} {player['last_name']}...")
            
            # Find the team_id for the primary_match_team
            target_team_query = """
                SELECT id FROM teams 
                WHERE team_name = %s
                LIMIT 1
            """
            
            target_team = execute_query_one(target_team_query, [player['primary_match_team']])
            
            if not target_team:
                print(f"      ❌ Could not find team: {player['primary_match_team']}")
                failed_fixes += 1
                continue
            
            target_team_id = target_team['id']
            
            # Update the player's team assignment
            update_query = """
                UPDATE players 
                SET team_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE tenniscores_player_id = %s
            """
            
            execute_query(update_query, [target_team_id, player['tenniscores_player_id']])
            
            print(f"      ✅ Moved from {player['assigned_team']} → {player['primary_match_team']}")
            successful_fixes += 1
            
        except Exception as e:
            print(f"      ❌ Error fixing {player['first_name']} {player['last_name']}: {e}")
            failed_fixes += 1
    
    print(f"\n5. Fix Summary:")
    print(f"   ✅ Successfully fixed: {successful_fixes}")
    print(f"   ❌ Failed to fix: {failed_fixes}")
    print(f"   📊 Success rate: {(successful_fixes / len(mismatched_players) * 100):.1f}%")
    
    if successful_fixes > 0:
        print(f"\n🎉 Phase 1 Complete! {successful_fixes} players now have correct team assignments.")
        print(f"   These players will now see their actual teammates in track-byes-courts pages.")
    
    return successful_fixes > 0

def verify_fixes():
    """Verify that the fixes worked by re-running the diagnostic"""
    print(f"\n6. Verifying fixes...")
    
    # Re-run the mismatched query to see if we reduced the count
    verification_query = """
        WITH player_match_teams AS (
            SELECT 
                CASE 
                    WHEN ms.home_player_1_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.home_player_2_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.away_player_1_id = p.tenniscores_player_id THEN ms.away_team
                    WHEN ms.away_player_2_id = p.tenniscores_player_id THEN ms.away_team
                END as match_team,
                p.tenniscores_player_id,
                t.team_name as assigned_team,
                COUNT(*) as match_count
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            WHERE p.is_active = TRUE
            GROUP BY p.tenniscores_player_id, t.team_name, match_team
        ),
        player_primary_teams AS (
            SELECT 
                tenniscores_player_id,
                assigned_team,
                match_team as primary_match_team,
                match_count,
                ROW_NUMBER() OVER (
                    PARTITION BY tenniscores_player_id 
                    ORDER BY match_count DESC
                ) as rn
            FROM player_match_teams
        )
        SELECT COUNT(*) as remaining_mismatched
        FROM player_primary_teams
        WHERE rn = 1 
        AND assigned_team IS NOT NULL 
        AND assigned_team != primary_match_team
    """
    
    result = execute_query_one(verification_query)
    remaining_mismatched = result['remaining_mismatched'] if result else 0
    
    print(f"   Remaining mismatched assignments: {remaining_mismatched}")
    
    if remaining_mismatched == 0:
        print(f"   ✅ All mismatched assignments have been fixed!")
    else:
        print(f"   ⚠️  {remaining_mismatched} assignments still need attention")
    
    return remaining_mismatched

if __name__ == "__main__":
    print("Starting Phase 1: Fix Mismatched Team Assignments")
    print("This fixes players like Rob Werman who are assigned to wrong teams\n")
    
    success = fix_mismatched_assignments()
    
    if success:
        remaining = verify_fixes()
        
        if remaining == 0:
            print(f"\n🎉 PHASE 1 COMPLETED SUCCESSFULLY!")
            print(f"   All players now have team assignments that match their match participation.")
            print(f"   Ready to proceed to Phase 2: Assign teams to players with no assignment.")
        else:
            print(f"\n⚠️  PHASE 1 PARTIALLY COMPLETED")
            print(f"   {remaining} assignments still need manual review.")
    else:
        print(f"\n❌ PHASE 1 FAILED")
        print(f"   Please review the errors above and try again.") 