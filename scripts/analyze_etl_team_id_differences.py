#!/usr/bin/env python3
"""
ETL Team ID Preservation Analysis
=================================

This script analyzes why team ID preservation worked on local/staging
but failed on production during the ETL process.

The issue: Practice times were orphaned on production because team IDs
changed, but the same ETL process preserved team IDs locally.

Usage:
    python scripts/analyze_etl_team_id_differences.py --compare-environments
"""

import argparse
import os
import sys
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db

def get_team_id_ranges(cursor, environment_name):
    """Get team ID ranges and key statistics"""
    print(f"\n🔍 Analyzing {environment_name} environment...")
    
    # Get team ID ranges
    cursor.execute("""
        SELECT MIN(id) as min_id, MAX(id) as max_id, COUNT(*) as total_teams
        FROM teams
    """)
    
    team_ranges = cursor.fetchone()
    if team_ranges:
        min_id, max_id, total_teams = team_ranges
        print(f"  Team ID range: {min_id} to {max_id}")
        print(f"  Total teams: {total_teams}")
        
        # Calculate ID gap (indicates if IDs were preserved vs recreated)
        id_gap = max_id - min_id + 1
        utilization = (total_teams / id_gap) * 100 if id_gap > 0 else 0
        print(f"  ID utilization: {utilization:.1f}% ({total_teams}/{id_gap})")
        
        if utilization < 50:
            print(f"  ⚠️  Low utilization suggests IDs were NOT preserved (many gaps)")
        else:
            print(f"  ✅ High utilization suggests IDs were preserved (few gaps)")
    
    # Check specific team patterns
    cursor.execute("""
        SELECT team_name, id, team_alias, created_at, updated_at
        FROM teams 
        WHERE team_name LIKE 'Tennaqua%'
        ORDER BY team_name, id
    """)
    
    tennaqua_teams = cursor.fetchall()
    print(f"  Tennaqua teams ({len(tennaqua_teams)} total):")
    for team in tennaqua_teams:
        team_name, team_id, alias, created_at, updated_at = team
        status = "UPDATED" if updated_at and updated_at > created_at else "CREATED"
        print(f"    {team_name} (ID: {team_id}, alias: {alias}) - {status}")
    
    # Check for practice times
    cursor.execute("""
        SELECT COUNT(*) FROM schedule 
        WHERE home_team ILIKE '%practice%'
    """)
    
    practice_count = cursor.fetchone()[0]
    print(f"  Practice times: {practice_count}")
    
    return {
        'min_id': min_id,
        'max_id': max_id,
        'total_teams': total_teams,
        'utilization': utilization,
        'tennaqua_teams': tennaqua_teams,
        'practice_count': practice_count
    }

def analyze_team_upsert_behavior(cursor, environment_name):
    """Analyze team UPSERT behavior by checking created_at vs updated_at timestamps"""
    print(f"\n🔧 Analyzing UPSERT behavior in {environment_name}...")
    
    # Check ratio of created vs updated teams
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN updated_at IS NULL OR updated_at = created_at THEN 1 ELSE 0 END) as created_count,
            SUM(CASE WHEN updated_at IS NOT NULL AND updated_at > created_at THEN 1 ELSE 0 END) as updated_count
        FROM teams
    """)
    
    result = cursor.fetchone()
    if result:
        total, created_count, updated_count = result
        created_pct = (created_count / total) * 100 if total > 0 else 0
        updated_pct = (updated_count / total) * 100 if total > 0 else 0
        
        print(f"  Total teams: {total}")
        print(f"  Created (new): {created_count} ({created_pct:.1f}%)")
        print(f"  Updated (preserved): {updated_count} ({updated_pct:.1f}%)")
        
        if created_pct > 80:
            print(f"  🚨 HIGH CREATE RATE: Most teams were recreated (IDs not preserved)")
        elif updated_pct > 80:
            print(f"  ✅ HIGH UPDATE RATE: Most teams were preserved (IDs preserved)")
        else:
            print(f"  ⚠️  MIXED BEHAVIOR: Some preserved, some recreated")
    
    # Check recent ETL activity
    cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as teams_created,
            MIN(created_at) as first_created,
            MAX(created_at) as last_created
        FROM teams 
        WHERE created_at > NOW() - INTERVAL '7 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """)
    
    recent_activity = cursor.fetchall()
    print(f"  Recent team creation activity:")
    if recent_activity:
        for activity in recent_activity:
            date, count, first, last = activity
            duration = last - first if last != first else "instant"
            print(f"    {date}: {count} teams created (duration: {duration})")
    else:
        print(f"    No recent team creation activity")

def check_constraint_differences(cursor, environment_name):
    """Check if database constraints are different between environments"""
    print(f"\n🔒 Checking constraints in {environment_name}...")
    
    # Check unique constraints on teams table
    cursor.execute("""
        SELECT 
            tc.constraint_name,
            string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) as columns
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'teams' 
        AND tc.constraint_type = 'UNIQUE'
        GROUP BY tc.constraint_name
        ORDER BY tc.constraint_name
    """)
    
    constraints = cursor.fetchall()
    print(f"  Unique constraints on teams table:")
    for constraint in constraints:
        name, columns = constraint
        print(f"    {name}: ({columns})")
    
    # Check for potential constraint violations that might force recreation
    cursor.execute("""
        SELECT club_id, series_id, league_id, COUNT(*) as count
        FROM teams 
        GROUP BY club_id, series_id, league_id
        HAVING COUNT(*) > 1
        LIMIT 5
    """)
    
    violations = cursor.fetchall()
    if violations:
        print(f"  ⚠️  Potential constraint violations (multiple teams with same club/series/league):")
        for violation in violations:
            print(f"    Club {violation[0]}, Series {violation[1]}, League {violation[2]}: {violation[3]} teams")
    else:
        print(f"  ✅ No constraint violations found")

def compare_environments():
    """Compare team ID behavior between local and production"""
    environments = [
        ('LOCAL', None),
        ('PRODUCTION', 'railway_production')
    ]
    
    results = {}
    
    for env_name, env_var in environments:
        try:
            # Set environment
            if env_var:
                original_env = os.environ.get('RALLY_ENV')
                os.environ['RALLY_ENV'] = env_var
            
            print(f"\n{'='*60}")
            print(f"🔍 ANALYZING {env_name} ENVIRONMENT")
            print(f"{'='*60}")
            
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Get team ID analysis
                team_analysis = get_team_id_ranges(cursor, env_name)
                
                # Analyze UPSERT behavior
                analyze_team_upsert_behavior(cursor, env_name)
                
                # Check constraints
                check_constraint_differences(cursor, env_name)
                
                results[env_name] = team_analysis
        
        except Exception as e:
            print(f"❌ Error analyzing {env_name}: {str(e)}")
            results[env_name] = None
        
        finally:
            # Restore environment
            if env_var and 'original_env' in locals():
                if original_env:
                    os.environ['RALLY_ENV'] = original_env
                else:
                    os.environ.pop('RALLY_ENV', None)
    
    # Compare results
    print(f"\n{'='*60}")
    print(f"📊 ENVIRONMENT COMPARISON")
    print(f"{'='*60}")
    
    if results['LOCAL'] and results['PRODUCTION']:
        local = results['LOCAL']
        prod = results['PRODUCTION']
        
        print(f"Team ID Ranges:")
        print(f"  LOCAL:      {local['min_id']} to {local['max_id']} ({local['total_teams']} teams)")
        print(f"  PRODUCTION: {prod['min_id']} to {prod['max_id']} ({prod['total_teams']} teams)")
        
        print(f"\nID Utilization:")
        print(f"  LOCAL:      {local['utilization']:.1f}%")
        print(f"  PRODUCTION: {prod['utilization']:.1f}%")
        
        print(f"\nPractice Times:")
        print(f"  LOCAL:      {local['practice_count']}")
        print(f"  PRODUCTION: {prod['practice_count']}")
        
        # Analysis
        print(f"\n🔍 ANALYSIS:")
        
        if abs(local['min_id'] - prod['min_id']) > 1000:
            print(f"  🚨 MAJOR ID DIFFERENCE: Production and local have very different team ID ranges")
            print(f"     This suggests teams were completely recreated on production")
        
        if local['practice_count'] > 0 and prod['practice_count'] == 0:
            print(f"  🚨 PRACTICE TIME LOSS: Local has practice times, production doesn't")
            print(f"     This confirms the practice time restoration failed on production")
        
        if local['utilization'] > 80 and prod['utilization'] < 50:
            print(f"  🚨 ID PRESERVATION FAILURE: Local preserved IDs (high utilization)")
            print(f"     but production recreated them (low utilization)")

def main():
    parser = argparse.ArgumentParser(description='Analyze ETL team ID preservation differences')
    parser.add_argument('--compare-environments', action='store_true',
                       help='Compare team ID behavior between local and production')
    parser.add_argument('--environment', choices=['local', 'staging', 'production'],
                       help='Analyze specific environment only')
    
    args = parser.parse_args()
    
    if args.compare_environments:
        compare_environments()
    elif args.environment:
        # Analyze single environment
        if args.environment == 'production':
            os.environ['RALLY_ENV'] = 'railway_production'
        elif args.environment == 'staging':
            os.environ['RALLY_ENV'] = 'railway_staging'
        
        with get_db() as conn:
            cursor = conn.cursor()
            get_team_id_ranges(cursor, args.environment.upper())
            analyze_team_upsert_behavior(cursor, args.environment.upper())
            check_constraint_differences(cursor, args.environment.upper())
    else:
        print("Please specify --compare-environments or --environment")

if __name__ == "__main__":
    main() 