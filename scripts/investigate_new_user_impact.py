#!/usr/bin/env python3
"""
Investigate New User Impact

This script investigates whether new users logging in will face the same 
team assignment issues we just fixed, and provides prevention strategies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query

def check_recent_etl_imports():
    """Check if recent ETL imports are creating players with missing teams"""
    print("🔍 CHECKING RECENT ETL IMPORTS")
    print("=" * 40)
    
    # Check players created in the last 7 days
    recent_players = execute_query("""
    SELECT 
        COUNT(*) as total_recent,
        COUNT(CASE WHEN team_id IS NULL THEN 1 END) as missing_teams,
        COUNT(CASE WHEN team_id IS NOT NULL THEN 1 END) as has_teams,
        league_id,
        CASE 
            WHEN league_id = 4722 THEN 'APTA Chicago'
            WHEN league_id = 4723 THEN 'CITA'
            WHEN league_id = 4724 THEN 'CNSWPL'
            WHEN league_id = 4725 THEN 'NSTF'
            ELSE CONCAT('League ', league_id)
        END as league_name
    FROM players 
    WHERE created_at >= NOW() - INTERVAL '7 days'
      AND is_active = true
    GROUP BY league_id
    ORDER BY league_id
    """)
    
    print("\n1. RECENT PLAYER IMPORTS (Last 7 days):")
    print("-" * 42)
    
    total_recent = 0
    total_missing = 0
    
    for league in recent_players:
        total_recent += league['total_recent']
        total_missing += league['missing_teams']
        
        missing_pct = (league['missing_teams'] / league['total_recent'] * 100) if league['total_recent'] > 0 else 0
        
        print(f"  {league['league_name']}:")
        print(f"    Total imported: {league['total_recent']}")
        print(f"    Missing teams: {league['missing_teams']} ({missing_pct:.1f}%)")
        print(f"    Has teams: {league['has_teams']}")
        print()
    
    if total_recent > 0:
        overall_missing_pct = (total_missing / total_recent * 100)
        print(f"📊 OVERALL: {total_missing}/{total_recent} ({overall_missing_pct:.1f}%) recent players missing teams")
        
        if overall_missing_pct > 50:
            print("🚨 CRITICAL: ETL is still importing players with missing teams!")
            return "critical_issue"
        elif overall_missing_pct > 10:
            print("⚠️  WARNING: Significant percentage of new players have missing teams")
            return "ongoing_issue"
        else:
            print("✅ GOOD: Most recent players have proper team assignments")
            return "mostly_fixed"
    else:
        print("ℹ️  No recent player imports found")
        return "no_recent_data"

def simulate_new_user_registration():
    """Simulate what happens when a new user tries to register"""
    print("\n2. NEW USER REGISTRATION SIMULATION:")
    print("-" * 40)
    
    # Find some recent players with missing teams to simulate
    sample_broken_players = execute_query("""
    SELECT 
        tenniscores_player_id,
        first_name,
        last_name,
        club_id,
        series_id,
        team_id,
        league_id,
        created_at,
        CASE 
            WHEN league_id = 4722 THEN 'APTA Chicago'
            WHEN league_id = 4723 THEN 'CITA'
            WHEN league_id = 4724 THEN 'CNSWPL'
            WHEN league_id = 4725 THEN 'NSTF'
            ELSE CONCAT('League ', league_id)
        END as league_name
    FROM players 
    WHERE team_id IS NULL 
      AND is_active = true
      AND created_at >= NOW() - INTERVAL '30 days'
    ORDER BY created_at DESC
    LIMIT 5
    """)
    
    if sample_broken_players:
        print("  Sample recent players with missing teams:")
        for player in sample_broken_players:
            print(f"    {player['first_name']} {player['last_name']} ({player['league_name']})")
            print(f"      Player ID: {player['tenniscores_player_id']}")
            print(f"      Created: {player['created_at']}")
            print(f"      Issue: team_id = NULL, series_id = {player['series_id']}")
            print()
        
        print("🎯 IMPACT: If these players try to register, they would have:")
        print("   ❌ Missing team assignments")
        print("   ❌ Broken league switching (if multi-league)")
        print("   ❌ API returning incomplete team data")
        
        return True
    else:
        print("  ✅ No recent players found with missing teams")
        return False

def check_association_discovery_for_new_users():
    """Check if association discovery would catch and fix issues for new users"""
    print("\n3. ASSOCIATION DISCOVERY EFFECTIVENESS:")
    print("-" * 43)
    
    # Check if association discovery service would help
    print("  Current association discovery capabilities:")
    print("    ✅ Finds player records by name/email matching")
    print("    ✅ Links found players to user accounts")
    print("    ❌ Does NOT fix missing team assignments")
    print("    ❌ Does NOT validate team_id is populated")
    
    print("\n  📋 What happens during new user registration:")
    print("    1. User provides name/email")
    print("    2. Association discovery finds player record(s)")
    print("    3. Player record(s) linked to user account")
    print("    4. ❌ If player has team_id=NULL, issue persists")
    print("    5. ❌ /api/get-user-teams returns incomplete data")
    print("    6. ❌ League switching UI doesn't appear")

def analyze_prevention_strategies():
    """Analyze strategies to prevent new user issues"""
    print("\n4. PREVENTION STRATEGIES:")
    print("-" * 28)
    
    print("🛡️ IMMEDIATE FIXES (Prevent new user issues):")
    print()
    
    print("  Strategy A: ETL Validation (BEST)")
    print("    ✅ Add team assignment validation to ETL process")
    print("    ✅ Fail import if players can't be assigned to teams")
    print("    ✅ Fix root cause - prevents all future issues")
    print("    ⭐ RECOMMENDED: Highest impact")
    print()
    
    print("  Strategy B: Registration-Time Fixes (GOOD)")
    print("    ✅ Enhance association discovery to fix team assignments")
    print("    ✅ Auto-assign teams during registration if missing")
    print("    ✅ Catches issues at user onboarding")
    print("    ⚠️  Reactive approach - issues still created")
    print()
    
    print("  Strategy C: Background Cleanup (HELPFUL)")
    print("    ✅ Run periodic scripts to fix missing team assignments")
    print("    ✅ Gradually resolves existing 3,592 broken players")
    print("    ✅ Reduces impact over time")
    print("    ⚠️  Doesn't prevent new issues from being created")
    print()
    
    print("  Strategy D: API Graceful Degradation (SAFETY NET)")
    print("    ✅ Modify API to handle missing teams gracefully")
    print("    ✅ Show single team instead of failing completely")
    print("    ✅ Prevents complete UI breakage")
    print("    ❌ Doesn't fix underlying data integrity issue")

def recommend_immediate_actions():
    """Recommend immediate actions to prevent new user issues"""
    print("\n5. IMMEDIATE ACTION PLAN:")
    print("-" * 30)
    
    print("🚨 CRITICAL (Do First):")
    print("   1. Fix ETL process to validate team assignments")
    print("   2. Prevent future imports of players with team_id=NULL")
    print("   3. Add foreign key constraints to enforce data integrity")
    print()
    
    print("⚡ HIGH PRIORITY (Do Soon):")
    print("   4. Enhance association discovery to auto-fix team assignments")
    print("   5. Run background cleanup for existing 3,592 broken players")
    print("   6. Set up monitoring/alerts for team assignment failures")
    print()
    
    print("🛠️ MEDIUM PRIORITY (Ongoing):")
    print("   7. Add API graceful degradation for missing teams")
    print("   8. Regular health checks and data audits")
    print("   9. Cross-environment consistency validation")

def main():
    """Main execution function"""
    try:
        print("🔍 NEW USER IMPACT INVESTIGATION")
        print("=" * 50)
        print("Analyzing if new users will face the same team assignment issues\n")
        
        # Check recent ETL imports
        etl_status = check_recent_etl_imports()
        
        # Simulate new user registration
        has_broken_recent = simulate_new_user_registration()
        
        # Check association discovery effectiveness
        check_association_discovery_for_new_users()
        
        # Analyze prevention strategies
        analyze_prevention_strategies()
        
        # Recommend actions
        recommend_immediate_actions()
        
        # Final assessment
        print("\n" + "=" * 50)
        print("📋 FINAL ASSESSMENT")
        print("=" * 50)
        
        if etl_status == "critical_issue" or has_broken_recent:
            print("🚨 CRITICAL: YES - New users WILL face the same issues!")
            print("   ❌ ETL is still importing players with missing teams")
            print("   ❌ New user registration will inherit these problems")
            print("   🎯 URGENT: Fix ETL process immediately")
        elif etl_status == "ongoing_issue":
            print("⚠️  WARNING: New users MAY face similar issues")
            print("   ⚠️  Some recent imports still have missing teams")
            print("   🎯 RECOMMENDED: Implement prevention strategies")
        else:
            print("✅ BETTER: New users less likely to face issues")
            print("   ✅ Recent imports appear to have proper teams")
            print("   🎯 MAINTAIN: Keep monitoring and prevention active")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 