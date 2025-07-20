#!/usr/bin/env python3
"""
Restore Missing Practice Times After ETL
========================================

This script restores practice times that were lost during ETL import due to
team ID preservation failure on production.

Target Players:
- nndz-WkMrK3didjlnUT09 (Ross Freedman, Tennaqua - 22, Team 51727)
- nndz-WlNhd3hMYi9nQT09 (Ross Freedman, Tennaqua S2B, Team 51747)

Usage:
    python scripts/restore_missing_practice_times.py --environment production --execute
"""

import argparse
import os
import sys
from datetime import datetime, time

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db

def get_practice_time_patterns():
    """Define the practice time patterns that should exist based on local data"""
    return [
        {
            'pattern': 'Tennaqua Practice - Chicago 22',
            'player_id': 'nndz-WkMrK3didjlnUT09',
            'expected_team_name': 'Tennaqua - 22',
            'expected_count': 13,
            'club': 'Tennaqua',
            'series_pattern': 'Chicago 22'
        },
        {
            'pattern': 'Tennaqua Practice - Series 2B', 
            'player_id': 'nndz-WlNhd3hMYi9nQT09',
            'expected_team_name': 'Tennaqua S2B',
            'expected_count': 14,
            'club': 'Tennaqua',
            'series_pattern': 'Series 2B'
        }
    ]

def find_target_team_ids(cursor):
    """Find the current team IDs for the affected players"""
    team_mappings = {}
    
    for pattern in get_practice_time_patterns():
        cursor.execute("""
            SELECT p.team_id, t.team_name, t.team_alias
            FROM players p
            JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = %s
        """, [pattern['player_id']])
        
        result = cursor.fetchone()
        if result:
            team_id, team_name, team_alias = result
            team_mappings[pattern['player_id']] = {
                'team_id': team_id,
                'team_name': team_name,
                'team_alias': team_alias,
                'practice_pattern': pattern['pattern']
            }
            print(f"✅ Found team for {pattern['player_id']}: {team_name} (ID: {team_id})")
        else:
            print(f"❌ Could not find team for player {pattern['player_id']}")
    
    return team_mappings

def generate_practice_dates():
    """Generate practice dates based on the pattern from local data"""
    from datetime import timedelta
    
    base_dates = []
    
    # Generate practice dates for Chicago 22 (13 times) - Fridays
    start_date = datetime(2025, 7, 25)  # Friday
    for i in range(13):
        practice_date = start_date + timedelta(weeks=i)
        if practice_date.year == 2025:  # Stay within 2025
            base_dates.append({
                'date': practice_date.date(),
                'time': time(21, 0),  # 9:00 PM
                'pattern': 'Tennaqua Practice - Chicago 22',
                'location': 'Tennaqua'
            })
    
    # Generate practice dates for Series 2B (14 times) - Saturdays  
    start_date = datetime(2025, 7, 26)  # Saturday
    for i in range(14):
        practice_date = start_date + timedelta(weeks=i)
        if practice_date.year == 2025:  # Stay within 2025
            base_dates.append({
                'date': practice_date.date(),
                'time': time(19, 0),  # 7:00 PM
                'pattern': 'Tennaqua Practice - Series 2B',
                'location': 'Tennaqua'
            })
    
    return base_dates

def check_existing_practice_times(cursor):
    """Check what practice times currently exist"""
    print("\n🔍 Checking existing practice times...")
    
    cursor.execute("""
        SELECT home_team, home_team_id, COUNT(*) as count
        FROM schedule 
        WHERE home_team ILIKE '%practice%'
        GROUP BY home_team, home_team_id
        ORDER BY count DESC
    """)
    
    existing = cursor.fetchall()
    if existing:
        print("Current practice times:")
        for practice in existing:
            print(f"  {practice[0]} -> Team {practice[1]} ({practice[2]} times)")
    else:
        print("  No practice times found")
    
    return existing

def restore_practice_times(cursor, team_mappings, practice_dates, dry_run=True):
    """Restore the missing practice times"""
    
    print(f"\n{'🔍 DRY RUN:' if dry_run else '💾 EXECUTING:'} Restoring practice times...")
    
    restored_count = 0
    
    for practice_date in practice_dates:
        # Find the team ID for this practice pattern
        target_team_id = None
        
        for player_id, team_info in team_mappings.items():
            if team_info['practice_pattern'] == practice_date['pattern']:
                target_team_id = team_info['team_id']
                break
        
        if not target_team_id:
            print(f"  ⚠️  Could not find team for pattern: {practice_date['pattern']}")
            continue
        
        # Check if this practice time already exists
        cursor.execute("""
            SELECT COUNT(*) FROM schedule 
            WHERE home_team = %s 
            AND match_date = %s 
            AND home_team_id = %s
        """, [practice_date['pattern'], practice_date['date'], target_team_id])
        
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            print(f"  ⏭️  Skipping existing: {practice_date['pattern']} on {practice_date['date']}")
            continue
        
        if not dry_run:
            # Insert the practice time
            cursor.execute("""
                INSERT INTO schedule (
                    league_id, match_date, match_time, home_team, away_team, 
                    home_team_id, location, created_at
                )
                SELECT 
                    t.league_id, %s, %s, %s, '', %s, %s, CURRENT_TIMESTAMP
                FROM teams t
                WHERE t.id = %s
            """, [
                practice_date['date'], 
                practice_date['time'],
                practice_date['pattern'],
                target_team_id,
                practice_date['location'],
                target_team_id
            ])
            
            print(f"  ✅ Restored: {practice_date['pattern']} on {practice_date['date']} for team {target_team_id}")
        else:
            print(f"  📝 Would restore: {practice_date['pattern']} on {practice_date['date']} for team {target_team_id}")
        
        restored_count += 1
    
    return restored_count

def validate_restoration(cursor, team_mappings):
    """Validate that practice times were restored correctly"""
    print("\n✅ Validating restoration...")
    
    for player_id, team_info in team_mappings.items():
        cursor.execute("""
            SELECT COUNT(*) FROM schedule 
            WHERE home_team_id = %s AND home_team ILIKE '%practice%'
        """, [team_info['team_id']])
        
        count = cursor.fetchone()[0]
        print(f"  Player {player_id} ({team_info['team_name']}): {count} practice times")

def main():
    parser = argparse.ArgumentParser(description='Restore missing practice times after ETL')
    parser.add_argument('--environment', choices=['local', 'staging', 'production'], 
                       default='local', help='Target environment')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually execute the restoration (default is dry run)')
    
    args = parser.parse_args()
    
    # Set environment
    if args.environment == 'production':
        print("🚀 Targeting PRODUCTION environment")
        os.environ['RALLY_ENV'] = 'railway_production'
    elif args.environment == 'staging':
        print("🏗️  Targeting STAGING environment")
        os.environ['RALLY_ENV'] = 'railway_staging'
    else:
        print("🖥️  Targeting LOCAL environment")
    
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print("=" * 60)
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Step 1: Check current state
            existing_practices = check_existing_practice_times(cursor)
            
            # Step 2: Find target team IDs
            team_mappings = find_target_team_ids(cursor)
            
            if not team_mappings:
                print("❌ Could not find target teams. Exiting.")
                return
            
            # Step 3: Generate practice dates
            practice_dates = generate_practice_dates()
            print(f"\n📅 Generated {len(practice_dates)} practice dates")
            
            # Step 4: Restore practice times
            restored_count = restore_practice_times(
                cursor, team_mappings, practice_dates, dry_run=not args.execute
            )
            
            if args.execute:
                conn.commit()
                print(f"\n✅ Successfully restored {restored_count} practice times")
                
                # Step 5: Validate
                validate_restoration(cursor, team_mappings)
            else:
                print(f"\n📝 Dry run complete. Would restore {restored_count} practice times")
                print("Run with --execute to actually restore the practice times")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 