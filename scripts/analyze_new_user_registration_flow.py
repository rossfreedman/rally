#!/usr/bin/env python3
"""
Analyze New User Registration Flow

This script thoroughly analyzes what happens during new user registration
and whether my assessment that "every new user will have broken league switching"
was accurate or overly alarmist.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update
from app.services.auth_service_refactored import register_user
from app.services.association_discovery_service import AssociationDiscoveryService

def analyze_registration_flow():
    """Analyze the complete registration flow for new users"""
    print("=" * 80)
    print("ANALYZING NEW USER REGISTRATION FLOW")
    print("=" * 80)
    
    # 1. Check recent registrations and their outcomes
    print("\n1. Analyzing recent user registrations...")
    
    recent_users_query = """
        SELECT u.id, u.email, u.first_name, u.last_name, u.created_at,
               u.league_context,
               COUNT(upa.tenniscores_player_id) as association_count
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE u.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY u.id, u.email, u.first_name, u.last_name, u.created_at, u.league_context
        ORDER BY u.created_at DESC
        LIMIT 20
    """
    
    recent_users = execute_query(recent_users_query)
    
    print(f"   Found {len(recent_users)} users registered in last 30 days")
    
    single_league_count = 0
    multi_league_count = 0
    no_association_count = 0
    
    for user in recent_users:
        association_count = user['association_count']
        if association_count == 0:
            no_association_count += 1
        elif association_count == 1:
            single_league_count += 1
        else:
            multi_league_count += 1
        
        print(f"   - {user['first_name']} {user['last_name']}: {association_count} associations")
    
    print(f"\n   Summary:")
    print(f"   - No associations: {no_association_count}")
    print(f"   - Single league: {single_league_count}")
    print(f"   - Multi-league: {multi_league_count}")
    
    # 2. Analyze team assignment status for recent users
    print("\n2. Checking team assignment status for recent users...")
    
    team_assignment_query = """
        SELECT u.id, u.email, u.first_name, u.last_name,
               COUNT(CASE WHEN p.team_id IS NOT NULL THEN 1 END) as players_with_teams,
               COUNT(CASE WHEN p.team_id IS NULL THEN 1 END) as players_without_teams,
               COUNT(p.id) as total_players
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = TRUE
        WHERE u.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY u.id, u.email, u.first_name, u.last_name
        HAVING COUNT(p.id) > 0
        ORDER BY u.id
    """
    
    team_assignments = execute_query(team_assignment_query)
    
    users_with_broken_teams = 0
    users_with_all_teams = 0
    users_mixed_teams = 0
    
    for user in team_assignments:
        total = user['total_players']
        with_teams = user['players_with_teams']
        without_teams = user['players_without_teams']
        
        if without_teams == 0:
            users_with_all_teams += 1
            status = "✅ All teams assigned"
        elif with_teams == 0:
            users_with_broken_teams += 1
            status = "❌ No teams assigned"
        else:
            users_mixed_teams += 1
            status = "⚠️ Mixed (some teams missing)"
        
        print(f"   - {user['first_name']} {user['last_name']}: {with_teams}/{total} players have teams - {status}")
    
    print(f"\n   Team Assignment Summary:")
    print(f"   - All teams assigned: {users_with_all_teams}")
    print(f"   - Mixed assignments: {users_mixed_teams}")
    print(f"   - No teams assigned: {users_with_broken_teams}")
    
    # 3. Test API response for users with missing teams
    print("\n3. Testing /api/get-user-teams behavior for users with NULL team_id...")
    
    # Find a user with NULL team assignments
    null_team_user_query = """
        SELECT DISTINCT u.id, u.email, u.first_name, u.last_name
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE p.team_id IS NULL AND p.is_active = TRUE
        LIMIT 1
    """
    
    null_team_user = execute_query_one(null_team_user_query)
    
    if null_team_user:
        user_id = null_team_user['id']
        print(f"   Testing with user: {null_team_user['first_name']} {null_team_user['last_name']} (ID: {user_id})")
        
        # Simulate the /api/get-user-teams query (this is what determines league switching)
        api_teams_query = """
            SELECT DISTINCT 
                t.id,
                t.team_name,
                c.name as club_name,
                s.name as series_name,
                l.id as league_db_id,
                l.league_id as league_string_id,
                l.league_name
            FROM teams t
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            WHERE upa.user_id = %s 
                AND p.is_active = TRUE 
                AND t.is_active = TRUE
            ORDER BY l.league_name, c.name, s.name
        """
        
        api_teams = execute_query(api_teams_query, [user_id])
        
        print(f"   API would return {len(api_teams)} teams for this user")
        if len(api_teams) == 0:
            print("   ❌ This user would have broken league switching (no teams returned)")
        elif len(api_teams) == 1:
            print("   ⚠️ This user would not see league switching UI (single team)")
        else:
            print("   ✅ This user would see league switching UI (multiple teams)")
        
        for team in api_teams:
            print(f"      - {team['league_name']}: {team['club_name']} - {team['series_name']}")
    else:
        print("   No users found with NULL team assignments")
    
    # 4. Analyze what registration actually does for team assignment
    print("\n4. Analyzing registration function team assignment behavior...")
    
    # Check the assign_player_to_team function success rate
    team_assignment_stats_query = """
        SELECT 
            l.league_name,
            COUNT(CASE WHEN p.team_id IS NOT NULL THEN 1 END) as players_with_teams,
            COUNT(CASE WHEN p.team_id IS NULL THEN 1 END) as players_without_teams,
            ROUND(
                COUNT(CASE WHEN p.team_id IS NOT NULL THEN 1 END) * 100.0 / 
                COUNT(*), 1
            ) as assignment_rate
        FROM players p
        JOIN leagues l ON p.league_id = l.id
        WHERE p.is_active = TRUE
        GROUP BY l.league_name
        ORDER BY assignment_rate DESC
    """
    
    assignment_stats = execute_query(team_assignment_stats_query)
    
    for stat in assignment_stats:
        print(f"   {stat['league_name']}: {stat['assignment_rate']}% assignment rate ({stat['players_with_teams']}/{stat['players_with_teams'] + stat['players_without_teams']})")
    
    # 5. Test association discovery effectiveness
    print("\n5. Testing association discovery effectiveness...")
    
    # Find users with 0 or 1 associations who might benefit from discovery
    discovery_candidates_query = """
        SELECT u.id, u.email, u.first_name, u.last_name,
               COUNT(upa.tenniscores_player_id) as current_associations
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE u.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY u.id, u.email, u.first_name, u.last_name
        HAVING COUNT(upa.tenniscores_player_id) <= 1
        ORDER BY current_associations ASC
        LIMIT 5
    """
    
    candidates = execute_query(discovery_candidates_query)
    
    discovery_helped = 0
    for candidate in candidates:
        user_id = candidate['id']
        email = candidate['email']
        name = f"{candidate['first_name']} {candidate['last_name']}"
        current_count = candidate['current_associations']
        
        print(f"   Testing discovery for {name} (current: {current_count} associations)")
        
        # Run discovery (dry run - don't actually create associations)
        potential_players = AssociationDiscoveryService._find_potential_players(
            candidate['first_name'], candidate['last_name'], email
        )
        
        if potential_players:
            print(f"      ✅ Discovery would find {len(potential_players)} additional associations")
            discovery_helped += 1
        else:
            print(f"      ❌ Discovery would find no additional associations")
    
    print(f"   Discovery could help {discovery_helped}/{len(candidates)} tested users")
    
    # 6. Final assessment
    print("\n" + "=" * 80)
    print("FINAL ASSESSMENT")
    print("=" * 80)
    
    total_recent_users = len(recent_users)
    if total_recent_users == 0:
        print("❌ No recent users to analyze")
        return
    
    # Calculate actual percentages
    no_association_pct = (no_association_count / total_recent_users) * 100
    broken_team_pct = (users_with_broken_teams / max(len(team_assignments), 1)) * 100
    
    print(f"\n📊 REGISTRATION FLOW ANALYSIS:")
    print(f"   - {no_association_pct:.1f}% of new users get no player associations")
    print(f"   - {broken_team_pct:.1f}% of users with associations have broken team assignments")
    
    # Overall league switching impact
    users_likely_affected = no_association_count + users_with_broken_teams
    overall_impact_pct = (users_likely_affected / total_recent_users) * 100
    
    print(f"\n🚨 LEAGUE SWITCHING IMPACT:")
    print(f"   - {users_likely_affected}/{total_recent_users} users ({overall_impact_pct:.1f}%) likely affected by league switching issues")
    
    if overall_impact_pct > 50:
        print("   - ASSESSMENT: Most new users WILL have broken league switching")
    elif overall_impact_pct > 25:
        print("   - ASSESSMENT: Many new users will have broken league switching")
    elif overall_impact_pct > 10:
        print("   - ASSESSMENT: Some new users will have broken league switching")
    else:
        print("   - ASSESSMENT: Few new users will have broken league switching")
    
    print(f"\n🔧 MITIGATION FACTORS:")
    print(f"   - Association discovery can help {discovery_helped}/{len(candidates)} tested users")
    print(f"   - Team assignment during registration varies by league")
    
    # Show the registration flow fallbacks
    print(f"\n⚙️ REGISTRATION FALLBACKS:")
    print(f"   1. Registration creates user account (always succeeds)")
    print(f"   2. Player lookup attempts to find matching player (varies by data quality)")
    print(f"   3. Association creation links user to player (depends on step 2)")
    print(f"   4. Team assignment via assign_player_to_team() (depends on team availability)")
    print(f"   5. Association discovery runs post-registration (finds additional associations)")
    print(f"   6. /api/get-user-teams filters out NULL team_id players (causes UI issues)")
    
    return {
        "total_users": total_recent_users,
        "no_associations": no_association_count,
        "broken_teams": users_with_broken_teams,
        "overall_impact_pct": overall_impact_pct
    }

if __name__ == "__main__":
    try:
        results = analyze_registration_flow()
        print(f"\n✅ Analysis complete")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc() 