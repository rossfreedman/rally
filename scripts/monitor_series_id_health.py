#!/usr/bin/env python3
"""
Monitor Series ID Health
========================

This script monitors the health of series_id foreign key relationships in series_stats table.
It detects NULL series_id values and provides detailed analysis of missing relationships.

Usage: python scripts/monitor_series_id_health.py [--fix] [--league LEAGUE_ID]
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one, execute_update


def log(message, level="INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def analyze_null_series_ids(league_filter=None):
    """Analyze records with NULL series_id"""
    log("🔍 Analyzing NULL series_id records...")
    
    # Base query for NULL series_id records
    where_clause = "WHERE s.series_id IS NULL"
    params = []
    
    if league_filter:
        where_clause += " AND l.league_id = %s"
        params.append(league_filter)
    
    query = f"""
        SELECT 
            l.league_name,
            l.league_id,
            s.series,
            COUNT(*) as team_count,
            STRING_AGG(DISTINCT s.team, ', ' ORDER BY s.team) as teams
        FROM series_stats s
        JOIN leagues l ON s.league_id = l.id
        {where_clause}
        GROUP BY l.league_name, l.league_id, s.series
        ORDER BY l.league_name, s.series
    """
    
    null_records = execute_query(query, params)
    
    if not null_records:
        log("✅ No NULL series_id records found!")
        return []
    
    total_teams = sum(record['team_count'] for record in null_records)
    log(f"❌ Found {len(null_records)} different series with NULL series_id affecting {total_teams} teams")
    
    print("\n" + "="*80)
    print("NULL SERIES_ID ANALYSIS")
    print("="*80)
    
    current_league = None
    for record in null_records:
        if record['league_name'] != current_league:
            current_league = record['league_name']
            print(f"\n🏆 {current_league} ({record['league_id']}):")
            print("-" * 60)
        
        teams_list = record['teams'][:100] + "..." if len(record['teams']) > 100 else record['teams']
        print(f"  📊 {record['series']} - {record['team_count']} teams")
        print(f"     Teams: {teams_list}")
    
    return null_records


def check_missing_series_in_database(null_records):
    """Check which series exist in the series table but aren't linked"""
    log("🔍 Checking for missing series in database...")
    
    missing_series = []
    
    for record in null_records:
        league_id = record['league_id']
        series_name = record['series']
        
        # Check if series exists in series table for this league
        existing_series = execute_query_one("""
            SELECT s.id, s.name
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            JOIN leagues l ON sl.league_id = l.id
            WHERE l.league_id = %s AND (
                s.name = %s OR
                s.name ILIKE %s OR
                s.name = %s OR
                s.name = %s
            )
        """, [
            league_id, 
            series_name,
            f"%{series_name.split()[-1]}%",  # Try to match by number/suffix
            series_name.replace("Series ", ""),
            series_name.replace("Division ", "S")
        ])
        
        if not existing_series:
            missing_series.append({
                'league_id': league_id,
                'league_name': record['league_name'],
                'series_name': series_name,
                'team_count': record['team_count']
            })
    
    if missing_series:
        print(f"\n❌ Found {len(missing_series)} series that don't exist in series table:")
        for series in missing_series:
            print(f"  {series['league_name']}: '{series['series_name']}' ({series['team_count']} teams)")
    else:
        print(f"\n✅ All series exist in series table - just need linking")
    
    return missing_series


def generate_health_score():
    """Generate overall health score for series_id relationships"""
    log("📊 Calculating series_id health score...")
    
    # Total records
    total_records = execute_query_one("SELECT COUNT(*) as count FROM series_stats")["count"]
    
    # Records with series_id
    with_series_id = execute_query_one("SELECT COUNT(*) as count FROM series_stats WHERE series_id IS NOT NULL")["count"]
    
    # Records with NULL series_id
    null_series_id = execute_query_one("SELECT COUNT(*) as count FROM series_stats WHERE series_id IS NULL")["count"]
    
    health_score = (with_series_id / total_records * 100) if total_records > 0 else 0
    
    print(f"\n📊 SERIES_ID HEALTH SCORE: {health_score:.1f}%")
    print(f"   Total records: {total_records:,}")
    print(f"   With series_id: {with_series_id:,}")
    print(f"   NULL series_id: {null_series_id:,}")
    
    if health_score >= 95:
        print("   Status: ✅ EXCELLENT")
    elif health_score >= 85:
        print("   Status: ⚠️  GOOD")  
    elif health_score >= 75:
        print("   Status: ⚠️  FAIR")
    else:
        print("   Status: ❌ POOR")
    
    return {
        'score': health_score,
        'total': total_records,
        'with_series_id': with_series_id,
        'null_series_id': null_series_id
    }


def create_missing_series(missing_series, dry_run=True):
    """Create missing series in the database"""
    if not missing_series:
        log("✅ No missing series to create")
        return
    
    if dry_run:
        log(f"🔍 DRY RUN: Would create {len(missing_series)} missing series:")
        for series in missing_series:
            log(f"   CREATE: {series['series_name']} in {series['league_name']}")
        return
    
    log(f"🔧 Creating {len(missing_series)} missing series...")
    
    created_count = 0
    for series_info in missing_series:
        try:
            # Get league DB ID
            league_record = execute_query_one(
                "SELECT id FROM leagues WHERE league_id = %s", 
                [series_info['league_id']]
            )
            
            if not league_record:
                log(f"❌ League {series_info['league_id']} not found", "ERROR")
                continue
            
            league_db_id = league_record["id"]
            
            # Create series
            series_id = execute_query_one("""
                INSERT INTO series (name, created_at)
                VALUES (%s, CURRENT_TIMESTAMP)
                RETURNING id
            """, [series_info['series_name']])["id"]
            
            # Create series-league relationship
            execute_update("""
                INSERT INTO series_leagues (series_id, league_id, created_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
            """, [series_id, league_db_id])
            
            log(f"✅ Created series '{series_info['series_name']}' (ID: {series_id}) in {series_info['league_name']}")
            created_count += 1
            
        except Exception as e:
            log(f"❌ Failed to create series '{series_info['series_name']}': {e}", "ERROR")
    
    log(f"✅ Created {created_count} new series")


def main():
    parser = argparse.ArgumentParser(description='Monitor series_id health')
    parser.add_argument('--fix', action='store_true', help='Fix issues (create missing series)')
    parser.add_argument('--league', help='Filter by specific league ID')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    log("🚀 Starting Series ID Health Monitor")
    print("=" * 60)
    
    # Step 1: Analyze NULL series_id records
    null_records = analyze_null_series_ids(args.league)
    
    # Step 2: Check which series are missing from database
    missing_series = check_missing_series_in_database(null_records)
    
    # Step 3: Generate health score
    health_stats = generate_health_score()
    
    # Step 4: Optionally fix issues
    if args.fix and missing_series:
        create_missing_series(missing_series, dry_run=args.dry_run)
        
        # Re-run population script after creating series
        if not args.dry_run:
            log("🔄 Re-running series_id population...")
            from scripts.populate_series_id_in_series_stats import main as populate_main
            populate_main()
    
    print("\n" + "="*60)
    log("✅ Series ID Health Monitor completed")
    
    return health_stats['score'] >= 85


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 