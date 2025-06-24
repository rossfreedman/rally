#!/usr/bin/env python3
"""
Validate ETL Results - Ongoing Monitoring

This script should be run after each ETL process to validate
that team assignments remain healthy and catch issues early.

Usage:
    python scripts/validate_etl_results.py
    python scripts/validate_etl_results.py --detailed
    python scripts/validate_etl_results.py --fix-high-confidence
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def validate_team_assignment_health():
    """Run basic validation checks on team assignments"""
    print("🔍 TEAM ASSIGNMENT HEALTH CHECK")
    print("=" * 50)
    
    # Use our validation function
    validation_results = execute_query("SELECT * FROM validate_team_assignments()")
    
    total_issues = sum(result['issue_count'] for result in validation_results)
    
    print(f"📊 Validation Summary:")
    print(f"   Total Issues: {total_issues}")
    
    for result in validation_results:
        count = result['issue_count']
        status = "🟢" if count == 0 else "🟡" if count < 50 else "🔴"
        print(f"   {status} {result['validation_type']}: {count}")
        print(f"      {result['description']}")
    
    # Overall health score
    if total_issues == 0:
        health_status = "EXCELLENT"
        status_emoji = "🟢"
    elif total_issues < 100:
        health_status = "GOOD"
        status_emoji = "🟡"
    elif total_issues < 500:
        health_status = "NEEDS_ATTENTION"
        status_emoji = "🟠"
    else:
        health_status = "CRITICAL"
        status_emoji = "🔴"
    
    print(f"\n{status_emoji} Overall Health: {health_status}")
    
    return validation_results, health_status

def get_assignment_recommendations(limit=10):
    """Get top assignment recommendations from the intelligent function"""
    print(f"\n🎯 TOP {limit} ASSIGNMENT RECOMMENDATIONS")
    print("=" * 50)
    
    recommendations = execute_query(f"""
        SELECT * FROM assign_player_teams_from_matches() 
        ORDER BY match_count DESC 
        LIMIT {limit}
    """)
    
    if not recommendations:
        print("✅ No assignment recommendations - all players optimally assigned!")
        return []
    
    print(f"Found {len(recommendations)} recommendations:")
    
    for i, rec in enumerate(recommendations):
        confidence_emoji = {
            'HIGH': '🟢',
            'MEDIUM': '🟡', 
            'LOW': '🟠',
            'VERY_LOW': '🔴'
        }.get(rec['assignment_confidence'], '⚪')
        
        print(f"  {i+1}. {confidence_emoji} {rec['player_name']}")
        print(f"     {rec['old_team']} → {rec['new_team']}")
        print(f"     {rec['match_count']} matches, {rec['assignment_confidence']} confidence")
    
    return recommendations

def fix_high_confidence_issues():
    """Automatically fix high confidence assignment issues"""
    print(f"\n🔧 AUTO-FIXING HIGH CONFIDENCE ISSUES")
    print("=" * 50)
    
    high_confidence_fixes = execute_query("""
        SELECT * FROM assign_player_teams_from_matches() 
        WHERE assignment_confidence = 'HIGH'
        ORDER BY match_count DESC
        LIMIT 20
    """)
    
    if not high_confidence_fixes:
        print("✅ No high confidence fixes needed!")
        return 0
    
    print(f"Found {len(high_confidence_fixes)} high confidence fixes")
    
    fixed_count = 0
    
    for fix in high_confidence_fixes:
        try:
            # Find target team
            target_team = execute_query_one(
                "SELECT id FROM teams WHERE team_name = %s LIMIT 1",
                [fix['new_team']]
            )
            
            if target_team:
                # Apply fix
                execute_query(
                    "UPDATE players SET team_id = %s WHERE tenniscores_player_id = %s",
                    [target_team['id'], fix['player_id']]
                )
                
                print(f"  ✅ Fixed: {fix['player_name']} → {fix['new_team']}")
                fixed_count += 1
            else:
                print(f"  ❌ Team not found: {fix['new_team']}")
                
        except Exception as e:
            print(f"  ❌ Error fixing {fix['player_name']}: {e}")
    
    print(f"\n🎉 Applied {fixed_count} high confidence fixes")
    return fixed_count

def generate_monitoring_report():
    """Generate a monitoring report with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n📊 MONITORING REPORT - {timestamp}")
    print("=" * 50)
    
    # Get basic stats
    stats_query = """
        SELECT 
            COUNT(*) as total_players,
            COUNT(team_id) as assigned_players,
            COUNT(*) - COUNT(team_id) as unassigned_players,
            COUNT(DISTINCT team_id) as active_teams
        FROM players 
        WHERE is_active = TRUE
    """
    
    stats = execute_query_one(stats_query)
    
    print(f"📈 Current Statistics:")
    print(f"   Total Players: {stats['total_players']}")
    print(f"   Assigned: {stats['assigned_players']} ({stats['assigned_players']/stats['total_players']*100:.1f}%)")
    print(f"   Unassigned: {stats['unassigned_players']} ({stats['unassigned_players']/stats['total_players']*100:.1f}%)")
    print(f"   Active Teams: {stats['active_teams']}")
    
    # Team size distribution
    team_sizes_query = """
        WITH team_player_counts AS (
            SELECT 
                t.id,
                COUNT(p.id) as team_size
            FROM teams t
            LEFT JOIN players p ON t.id = p.team_id AND p.is_active = TRUE
            GROUP BY t.id
        )
        SELECT 
            team_size,
            COUNT(*) as team_count
        FROM team_player_counts
        GROUP BY team_size
        ORDER BY team_size
    """
    
    team_sizes = execute_query(team_sizes_query)
    
    print(f"\n🏆 Team Size Distribution:")
    for size_info in team_sizes:
        size = size_info['team_size']
        count = size_info['team_count']
        if size == 0:
            print(f"   Empty teams: {count}")
        else:
            print(f"   {size} players: {count} teams")

def main():
    parser = argparse.ArgumentParser(description='Validate ETL team assignment results')
    parser.add_argument('--detailed', action='store_true', help='Show detailed recommendations')
    parser.add_argument('--fix-high-confidence', action='store_true', help='Automatically fix high confidence issues')
    parser.add_argument('--limit', type=int, default=10, help='Limit for recommendations display')
    
    args = parser.parse_args()
    
    print("ETL Team Assignment Validation")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run basic health check
    validation_results, health_status = validate_team_assignment_health()
    
    # Show recommendations if requested
    if args.detailed:
        recommendations = get_assignment_recommendations(args.limit)
    
    # Auto-fix high confidence issues if requested
    if args.fix_high_confidence:
        fixed_count = fix_high_confidence_issues()
        
        if fixed_count > 0:
            print(f"\n🔄 Re-running validation after fixes...")
            validation_results, health_status = validate_team_assignment_health()
    
    # Generate monitoring report
    generate_monitoring_report()
    
    # Exit with appropriate code
    if health_status in ['EXCELLENT', 'GOOD']:
        print(f"\n✅ ETL validation passed - team assignments are healthy")
        sys.exit(0)
    elif health_status == 'NEEDS_ATTENTION':
        print(f"\n⚠️  ETL validation warning - some issues detected")
        sys.exit(1)
    else:
        print(f"\n🚨 ETL validation failed - critical issues detected")
        sys.exit(2)

if __name__ == "__main__":
    main() 