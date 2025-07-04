#!/usr/bin/env python3
"""
ETL Series ID Validator
======================

This script validates series_id integrity during and after ETL processes.
It ensures all series_stats records have proper foreign key relationships.

Usage: python scripts/etl_series_id_validator.py [--auto-fix] [--pre-etl] [--post-etl]
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


def validate_series_id_integrity():
    """Validate series_id integrity in series_stats table"""
    log("🔍 Validating series_id integrity...")
    
    # Check 1: NULL series_id count
    null_count = execute_query_one("""
        SELECT COUNT(*) as count 
        FROM series_stats 
        WHERE series_id IS NULL
    """)["count"]
    
    # Check 2: Invalid series_id references
    invalid_refs = execute_query_one("""
        SELECT COUNT(*) as count
        FROM series_stats s
        LEFT JOIN series sr ON s.series_id = sr.id
        WHERE s.series_id IS NOT NULL AND sr.id IS NULL
    """)["count"]
    
    # Check 3: Mismatched league relationships
    mismatched_leagues = execute_query_one("""
        SELECT COUNT(*) as count
        FROM series_stats s
        JOIN series sr ON s.series_id = sr.id
        LEFT JOIN series_leagues sl ON sr.id = sl.series_id AND s.league_id = sl.league_id
        WHERE s.series_id IS NOT NULL AND sl.series_id IS NULL
    """)["count"]
    
    total_records = execute_query_one("SELECT COUNT(*) as count FROM series_stats")["count"]
    
    issues = []
    if null_count > 0:
        issues.append(f"NULL series_id: {null_count:,} records")
    if invalid_refs > 0:
        issues.append(f"Invalid references: {invalid_refs:,} records")
    if mismatched_leagues > 0:
        issues.append(f"League mismatches: {mismatched_leagues:,} records")
    
    if issues:
        log(f"❌ Found {len(issues)} integrity issues:", "ERROR")
        for issue in issues:
            log(f"   - {issue}", "ERROR")
        return False
    else:
        log(f"✅ All {total_records:,} series_stats records have valid series_id relationships")
        return True


def pre_etl_validation():
    """Validation to run before ETL process"""
    log("🔍 Running PRE-ETL series_id validation...")
    
    # Check current state before ETL
    current_health = validate_series_id_integrity()
    
    # Check if series table has sufficient coverage
    series_count = execute_query_one("SELECT COUNT(*) as count FROM series")["count"]
    leagues_count = execute_query_one("SELECT COUNT(*) as count FROM leagues")["count"]
    
    log(f"📊 Current state: {series_count} series across {leagues_count} leagues")
    
    if series_count < leagues_count:
        log("⚠️  WARNING: Very few series defined - ETL may create many NULL series_id records", "WARNING")
    
    return current_health


def post_etl_validation():
    """Validation to run after ETL process"""
    log("🔍 Running POST-ETL series_id validation...")
    
    # Check if ETL introduced new NULL series_id records
    current_health = validate_series_id_integrity()
    
    if not current_health:
        log("❌ ETL process introduced series_id integrity issues!", "ERROR")
        
        # Get breakdown by league
        league_breakdown = execute_query("""
            SELECT 
                l.league_name,
                l.league_id,
                COUNT(*) as null_count
            FROM series_stats s
            JOIN leagues l ON s.league_id = l.id
            WHERE s.series_id IS NULL
            GROUP BY l.league_name, l.league_id
            ORDER BY null_count DESC
        """)
        
        log("NULL series_id breakdown by league:")
        for league in league_breakdown:
            log(f"   {league['league_name']}: {league['null_count']:,} records")
        
        return False
    else:
        log("✅ ETL maintained series_id integrity")
        return True


def auto_fix_series_id_issues():
    """Automatically fix series_id issues where possible"""
    log("🔧 Auto-fixing series_id issues...")
    
    # Run the population script
    try:
        from scripts.populate_series_id_in_series_stats import main as populate_main
        log("Running series_id population script...")
        populate_result = populate_main()
        
        # Check if any issues remain
        remaining_nulls = execute_query_one("""
            SELECT COUNT(*) as count 
            FROM series_stats 
            WHERE series_id IS NULL
        """)["count"]
        
        if remaining_nulls > 0:
            log(f"⚠️  {remaining_nulls:,} records still have NULL series_id after auto-fix", "WARNING")
            log("These may require manual series creation", "WARNING")
        else:
            log("✅ All series_id issues resolved!")
        
        return remaining_nulls == 0
        
    except Exception as e:
        log(f"❌ Auto-fix failed: {e}", "ERROR")
        return False


def generate_series_coverage_report():
    """Generate a report of series coverage across leagues"""
    log("📊 Generating series coverage report...")
    
    coverage_data = execute_query("""
        SELECT 
            l.league_name,
            l.league_id,
            COUNT(DISTINCT s.series) as total_series_in_stats,
            COUNT(DISTINCT sr.id) as linked_series_count,
            COUNT(DISTINCT CASE WHEN s.series_id IS NOT NULL THEN s.series END) as covered_series,
            COUNT(*) as total_teams,
            COUNT(CASE WHEN s.series_id IS NOT NULL THEN 1 END) as teams_with_series_id
        FROM series_stats s
        JOIN leagues l ON s.league_id = l.id
        LEFT JOIN series sr ON s.series_id = sr.id
        GROUP BY l.league_name, l.league_id
        ORDER BY l.league_name
    """)
    
    print("\n" + "="*80)
    print("SERIES COVERAGE REPORT")
    print("="*80)
    print(f"{'League':<25} {'Total Series':<12} {'Covered':<8} {'Coverage %':<10} {'Teams w/ ID':<12}")
    print("-" * 80)
    
    total_teams = 0
    total_covered_teams = 0
    
    for data in coverage_data:
        coverage_pct = (data['teams_with_series_id'] / data['total_teams'] * 100) if data['total_teams'] > 0 else 0
        total_teams += data['total_teams']
        total_covered_teams += data['teams_with_series_id']
        
        status = "✅" if coverage_pct >= 95 else "⚠️" if coverage_pct >= 75 else "❌"
        
        print(f"{data['league_name'][:24]:<25} {data['total_series_in_stats']:<12} {data['covered_series']:<8} {coverage_pct:>8.1f}% {status} {data['teams_with_series_id']:<12}")
    
    overall_coverage = (total_covered_teams / total_teams * 100) if total_teams > 0 else 0
    print("-" * 80)
    print(f"{'OVERALL':<25} {'':<12} {'':<8} {overall_coverage:>8.1f}% {'✅' if overall_coverage >= 85 else '❌'} {total_covered_teams:<12}")
    print("="*80)
    
    return overall_coverage


def main():
    parser = argparse.ArgumentParser(description='Validate ETL series_id integrity')
    parser.add_argument('--auto-fix', action='store_true', help='Automatically fix issues where possible')
    parser.add_argument('--pre-etl', action='store_true', help='Run pre-ETL validation')
    parser.add_argument('--post-etl', action='store_true', help='Run post-ETL validation') 
    parser.add_argument('--report', action='store_true', help='Generate coverage report')
    
    args = parser.parse_args()
    
    log("🚀 Starting ETL Series ID Validator")
    print("=" * 60)
    
    success = True
    
    # Run appropriate validation based on arguments
    if args.pre_etl:
        success = pre_etl_validation()
    elif args.post_etl:
        success = post_etl_validation()
        if not success and args.auto_fix:
            log("🔄 Attempting auto-fix...")
            success = auto_fix_series_id_issues()
    else:
        # Default: comprehensive validation
        success = validate_series_id_integrity()
        if not success and args.auto_fix:
            log("🔄 Attempting auto-fix...")
            success = auto_fix_series_id_issues()
    
    # Generate report if requested
    if args.report:
        coverage = generate_series_coverage_report()
        if coverage < 85:
            success = False
    
    print("\n" + "="*60)
    if success:
        log("✅ Series ID validation completed successfully")
    else:
        log("❌ Series ID validation found issues", "ERROR")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 