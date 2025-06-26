#!/usr/bin/env python3

"""
Post-ETL Health Check
====================

This script provides a comprehensive health check after ETL operations to ensure
all user associations and league contexts are working properly. Run this after
any database import to verify system integrity.

Usage:
    python scripts/post_etl_health_check.py [--fix-issues] [--detailed]
"""

import sys
import os
import argparse
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one


def check_association_health():
    """Check user-player association system health"""
    print("🔗 USER-PLAYER ASSOCIATION HEALTH")
    print("=" * 50)
    
    # Total users
    total_users = execute_query_one("SELECT COUNT(*) as count FROM users")['count']
    
    # Users with associations
    users_with_associations = execute_query_one("""
        SELECT COUNT(DISTINCT user_id) as count 
        FROM user_player_associations
    """)['count']
    
    # Total associations
    total_associations = execute_query_one("""
        SELECT COUNT(*) as count 
        FROM user_player_associations
    """)['count']
    
    # Broken associations (pointing to non-existent players)
    broken_associations = execute_query_one("""
        SELECT COUNT(*) as count
        FROM user_player_associations upa
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE p.tenniscores_player_id IS NULL
    """)['count']
    
    print(f"📊 Association Statistics:")
    print(f"   Total users: {total_users:,}")
    print(f"   Users with associations: {users_with_associations:,}")
    print(f"   Total associations: {total_associations:,}")
    print(f"   Broken associations: {broken_associations:,}")
    
    if total_users > 0:
        association_coverage = (users_with_associations / total_users) * 100
        print(f"   Coverage: {association_coverage:.1f}%")
        
        if broken_associations > 0:
            print(f"❌ ISSUE: {broken_associations} broken associations found")
            return False
        elif association_coverage < 80:
            print(f"⚠️  WARNING: Low association coverage ({association_coverage:.1f}%)")
            return False
        else:
            print(f"✅ GOOD: Association system healthy")
            return True
    
    return True


def check_league_context_health():
    """Check league context system health"""
    print("\n🎯 LEAGUE CONTEXT HEALTH")
    print("=" * 50)
    
    # Total users with associations
    total_users_with_assoc = execute_query_one("""
        SELECT COUNT(DISTINCT u.id) as count
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
    """)['count']
    
    # Users with NULL league_context
    null_context_count = execute_query_one("""
        SELECT COUNT(DISTINCT u.id) as count
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE u.league_context IS NULL
    """)['count']
    
    # Users with valid league_context
    valid_context_count = execute_query_one("""
        SELECT COUNT(DISTINCT u.id) as count
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE u.league_context = p.league_id AND p.is_active = true
    """)['count']
    
    # Users with broken league_context
    broken_context_count = execute_query_one("""
        SELECT COUNT(DISTINCT u.id) as count
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE u.league_context IS NOT NULL
        AND u.league_context NOT IN (
            SELECT DISTINCT p.league_id
            FROM user_player_associations upa_inner
            JOIN players p ON upa_inner.tenniscores_player_id = p.tenniscores_player_id
            WHERE upa_inner.user_id = u.id AND p.is_active = true
        )
    """)['count']
    
    print(f"📊 League Context Statistics:")
    print(f"   Total users with associations: {total_users_with_assoc:,}")
    print(f"   Users with NULL context: {null_context_count:,}")
    print(f"   Users with valid context: {valid_context_count:,}")
    print(f"   Users with broken context: {broken_context_count:,}")
    
    if total_users_with_assoc > 0:
        health_score = (valid_context_count / total_users_with_assoc) * 100
        print(f"   Health Score: {health_score:.1f}%")
        
        if health_score < 70:
            print("🚨 CRITICAL: League context system needs immediate repair")
            return False
        elif health_score < 90:
            print("⚠️  WARNING: League context system needs attention")
            return False
        else:
            print("✅ GOOD: League context system healthy")
            return True
    
    return True


def check_session_service_health():
    """Check if session service would work for users"""
    print("\n🔑 SESSION SERVICE HEALTH")
    print("=" * 50)
    
    # Test session creation for a sample of users
    sample_users = execute_query("""
        SELECT u.id, u.email, u.first_name, u.last_name
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        ORDER BY u.last_login DESC NULLS LAST
        LIMIT 10
    """)
    
    successful_sessions = 0
    failed_sessions = 0
    
    for user in sample_users:
        # Test the session service query
        session_result = execute_query_one("""
            SELECT 
                u.id,
                u.email, 
                u.first_name, 
                u.last_name,
                u.league_context,
                p.tenniscores_player_id,
                c.name as club,
                s.name as series,
                l.league_name
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                AND p.league_id = u.league_context 
                AND p.is_active = TRUE
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE u.id = %s
            ORDER BY (CASE WHEN p.tenniscores_player_id IS NOT NULL THEN 1 ELSE 2 END)
            LIMIT 1
        """, [user['id']])
        
        if session_result and session_result['tenniscores_player_id']:
            successful_sessions += 1
        else:
            failed_sessions += 1
            print(f"   ❌ {user['first_name']} {user['last_name']} ({user['email']}): Session would fail")
    
    print(f"📊 Session Service Test Results:")
    print(f"   Successful sessions: {successful_sessions}/{len(sample_users)}")
    print(f"   Failed sessions: {failed_sessions}/{len(sample_users)}")
    
    if failed_sessions == 0:
        print("✅ GOOD: Session service working for all tested users")
        return True
    elif failed_sessions <= 2:
        print("⚠️  WARNING: Some users would see profile alerts")
        return False
    else:
        print("🚨 CRITICAL: Many users would see profile alerts")
        return False


def get_detailed_issues():
    """Get detailed information about specific issues"""
    print("\n🔍 DETAILED ISSUE ANALYSIS")
    print("=" * 50)
    
    # Users who would see profile alerts
    problem_users = execute_query("""
        SELECT u.id, u.email, u.first_name, u.last_name, u.league_context
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE u.id NOT IN (
            SELECT DISTINCT u2.id
            FROM users u2
            LEFT JOIN user_player_associations upa2 ON u2.id = upa2.user_id
            LEFT JOIN players p2 ON upa2.tenniscores_player_id = p2.tenniscores_player_id 
                AND p2.league_id = u2.league_context 
                AND p2.is_active = TRUE
            WHERE p2.tenniscores_player_id IS NOT NULL
        )
        ORDER BY u.email
        LIMIT 10
    """)
    
    if problem_users:
        print(f"👥 Users who would see profile alerts ({len(problem_users)} shown):")
        for user in problem_users:
            print(f"   - {user['first_name']} {user['last_name']} ({user['email']})")
            print(f"     League context: {user['league_context']}")
            
            # Show their actual associations
            associations = execute_query("""
                SELECT l.league_name, l.id as league_id, c.name as club, s.name as series
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                WHERE upa.user_id = %s AND p.is_active = true
            """, [user['id']])
            
            print(f"     Actual associations:")
            for assoc in associations:
                print(f"       - {assoc['league_name']} (ID: {assoc['league_id']}): {assoc['club']} / {assoc['series']}")
    else:
        print("✅ No users found who would see profile alerts")
    
    # Broken associations
    broken_assocs = execute_query("""
        SELECT u.email, u.first_name, u.last_name, upa.tenniscores_player_id
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE p.tenniscores_player_id IS NULL
        LIMIT 5
    """)
    
    if broken_assocs:
        print(f"\n🔗 Broken associations ({len(broken_assocs)} shown):")
        for assoc in broken_assocs:
            print(f"   - {assoc['first_name']} {assoc['last_name']} ({assoc['email']})")
            print(f"     Missing player: {assoc['tenniscores_player_id']}")
    else:
        print("\n✅ No broken associations found")


def run_health_check(detailed=False, fix_issues=False):
    """Run comprehensive health check"""
    print("🏥 POST-ETL HEALTH CHECK")
    print("=" * 50)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if fix_issues:
        print("🔧 REPAIR MODE - Will attempt to fix issues found")
    
    # Run health checks
    association_healthy = check_association_health()
    context_healthy = check_league_context_health()
    session_healthy = check_session_service_health()
    
    if detailed:
        get_detailed_issues()
    
    # Overall health score
    health_checks = [association_healthy, context_healthy, session_healthy]
    healthy_count = sum(health_checks)
    overall_score = (healthy_count / len(health_checks)) * 100
    
    print(f"\n🏥 OVERALL HEALTH SCORE: {overall_score:.1f}%")
    
    if overall_score == 100:
        print("🎉 EXCELLENT: System is fully healthy!")
        return True
    elif overall_score >= 66:
        print("⚠️  WARNING: System has some issues but is mostly functional")
        
        if fix_issues:
            print("\n🔧 RUNNING REPAIR COMMANDS...")
            return run_repairs()
        else:
            print("\n💡 RECOMMENDED ACTIONS:")
            print("   python scripts/fix_broken_league_contexts.py")
            print("   python scripts/re_associate_all_users.py")
            return False
    else:
        print("🚨 CRITICAL: System has major issues!")
        
        if fix_issues:
            print("\n🔧 RUNNING EMERGENCY REPAIRS...")
            return run_repairs()
        else:
            print("\n🚨 EMERGENCY ACTIONS REQUIRED:")
            print("   python scripts/fix_broken_league_contexts.py")
            print("   python scripts/re_associate_all_users.py")
            return False


def run_repairs():
    """Run repair scripts automatically"""
    import subprocess
    
    success = True
    
    try:
        print("🔧 Fixing broken league contexts...")
        result = subprocess.run([
            "python", "scripts/fix_broken_league_contexts.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ League context repair completed")
        else:
            print(f"❌ League context repair failed: {result.stderr}")
            success = False
            
    except Exception as e:
        print(f"❌ Error running league context repair: {e}")
        success = False
    
    try:
        print("🔧 Re-associating all users...")
        result = subprocess.run([
            "python", "scripts/re_associate_all_users.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ User re-association completed")
        else:
            print(f"❌ User re-association failed: {result.stderr}")
            success = False
            
    except Exception as e:
        print(f"❌ Error running user re-association: {e}")
        success = False
    
    if success:
        print("🎉 All repairs completed successfully!")
        print("🔄 Re-running health check...")
        return run_health_check(detailed=False, fix_issues=False)
    else:
        print("❌ Some repairs failed - manual intervention required")
        return False


def main():
    parser = argparse.ArgumentParser(description="Post-ETL health check")
    parser.add_argument("--fix-issues", action="store_true",
                       help="Automatically attempt to fix issues found")
    parser.add_argument("--detailed", action="store_true",
                       help="Show detailed analysis of issues")
    
    args = parser.parse_args()
    
    try:
        success = run_health_check(detailed=args.detailed, fix_issues=args.fix_issues)
        
        print(f"\n🏁 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if success:
            print("✅ System is healthy - no action required")
            return 0
        else:
            print("⚠️  System needs attention - see recommendations above")
            return 1
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 