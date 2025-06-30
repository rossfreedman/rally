#!/usr/bin/env python3
"""
ETL Failure Diagnostic Script

This script analyzes the current state of the database after an ETL failure
to understand what was imported successfully and what might be causing issues.
"""

import os
import sys
import traceback
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one


def analyze_database_state():
    """Analyze current database state after ETL failure"""
    print("=" * 60)
    print("🔍 ETL FAILURE DIAGNOSTIC ANALYSIS")
    print("=" * 60)
    print(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Check table row counts
        print("\n📊 TABLE ROW COUNTS:")
        print("-" * 30)
        
        tables = [
            'leagues', 'clubs', 'series', 'teams', 'players', 
            'player_history', 'match_scores', 'series_stats', 'schedule'
        ]
        
        for table in tables:
            try:
                count = execute_query_one(f"SELECT COUNT(*) as count FROM {table}")
                print(f"  {table:<15}: {count['count']:>8,} records")
            except Exception as e:
                print(f"  {table:<15}: ERROR - {str(e)}")
        
        # 2. Check player_history specifically for issues
        print("\n🎾 PLAYER HISTORY ANALYSIS:")
        print("-" * 30)
        
        # Check for null player_ids
        null_player_ids = execute_query_one(
            "SELECT COUNT(*) as count FROM player_history WHERE player_id IS NULL"
        )
        print(f"  Null player_id records: {null_player_ids['count']:,}")
        
        # Check for duplicate records
        duplicates = execute_query_one("""
            SELECT COUNT(*) as count FROM (
                SELECT player_id, date, series, COUNT(*) 
                FROM player_history 
                WHERE player_id IS NOT NULL
                GROUP BY player_id, date, series
                HAVING COUNT(*) > 1
            ) dupes
        """)
        print(f"  Duplicate records: {duplicates['count']:,}")
        
        # Check date ranges
        date_range = execute_query_one("""
            SELECT 
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                COUNT(DISTINCT date) as unique_dates
            FROM player_history 
            WHERE date IS NOT NULL
        """)
        if date_range['earliest_date']:
            print(f"  Date range: {date_range['earliest_date']} to {date_range['latest_date']}")
            print(f"  Unique dates: {date_range['unique_dates']:,}")
        
        # 3. Check for orphaned player_history records
        print("\n🔍 ORPHANED RECORD ANALYSIS:")
        print("-" * 30)
        
        orphaned_players = execute_query_one("""
            SELECT COUNT(*) as count 
            FROM player_history ph
            LEFT JOIN players p ON ph.player_id = p.id
            WHERE p.id IS NULL AND ph.player_id IS NOT NULL
        """)
        print(f"  Orphaned player_history records: {orphaned_players['count']:,}")
        
        # Check for players without league context
        no_league = execute_query_one("""
            SELECT COUNT(*) as count 
            FROM player_history ph
            LEFT JOIN leagues l ON ph.league_id = l.id
            WHERE l.id IS NULL AND ph.league_id IS NOT NULL
        """)
        print(f"  Records with invalid league_id: {no_league['count']:,}")
        
        # 4. Check recent import activity
        print("\n⏰ RECENT IMPORT ACTIVITY:")
        print("-" * 30)
        
        recent_records = execute_query("""
            SELECT 
                DATE(created_at) as import_date,
                COUNT(*) as records_imported
            FROM player_history 
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY import_date DESC
            LIMIT 10
        """)
        
        if recent_records:
            for record in recent_records:
                print(f"  {record['import_date']}: {record['records_imported']:,} records")
        else:
            print("  No recent import activity found")
        
        # 5. Check for problematic data patterns
        print("\n⚠️  POTENTIAL ISSUES:")
        print("-" * 30)
        
        # Check for records with missing end_pti
        missing_pti = execute_query_one("""
            SELECT COUNT(*) as count 
            FROM player_history 
            WHERE end_pti IS NULL
        """)
        print(f"  Records missing end_pti: {missing_pti['count']:,}")
        
        # Check for invalid dates
        invalid_dates = execute_query_one("""
            SELECT COUNT(*) as count 
            FROM player_history 
            WHERE date IS NULL OR date > CURRENT_DATE + INTERVAL '1 year'
        """)
        print(f"  Records with invalid dates: {invalid_dates['count']:,}")
        
        # 6. Sample recent errors (if any error logging exists)
        print("\n🔴 CHECKING FOR RECENT ERRORS:")
        print("-" * 30)
        
        # Look for any records that might indicate import issues
        try:
            suspicious_records = execute_query("""
                SELECT series, COUNT(*) as count
                FROM player_history 
                WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
                GROUP BY series
                ORDER BY count DESC
                LIMIT 5
            """)
            
            if suspicious_records:
                print("  Recent imports by series:")
                for record in suspicious_records:
                    print(f"    {record['series']}: {record['count']:,} records")
            else:
                print("  No recent player_history imports detected")
                
        except Exception as e:
            print(f"  Error checking recent imports: {str(e)}")
        
        # 7. Database connection health
        print("\n💚 DATABASE CONNECTION HEALTH:")
        print("-" * 30)
        
        # Check active connections
        try:
            connections = execute_query_one("""
                SELECT 
                    count(*) as total_connections,
                    count(*) filter (where state = 'active') as active_connections,
                    count(*) filter (where state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)
            print(f"  Total connections: {connections['total_connections']}")
            print(f"  Active connections: {connections['active_connections']}")
            print(f"  Idle connections: {connections['idle_connections']}")
        except Exception as e:
            print(f"  Could not check connections: {str(e)}")
        
        # Check for long-running queries
        try:
            long_queries = execute_query_one("""
                SELECT COUNT(*) as count
                FROM pg_stat_activity 
                WHERE state = 'active' 
                AND query_start < NOW() - INTERVAL '5 minutes'
                AND datname = current_database()
            """)
            print(f"  Long-running queries (>5min): {long_queries['count']}")
        except Exception as e:
            print(f"  Could not check long queries: {str(e)}")
        
        print("\n" + "=" * 60)
        print("✅ DIAGNOSTIC ANALYSIS COMPLETE")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during diagnostic analysis: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


def provide_recommendations():
    """Provide recommendations based on analysis"""
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 30)
    
    print("1. 🔄 RETRY STRATEGIES:")
    print("   • Use the resume import functionality")
    print("   • Run imports during off-peak hours")
    print("   • Consider batch size reduction")
    
    print("\n2. 🛠️ OPTIMIZATION OPTIONS:")
    print("   • Increase error threshold temporarily")
    print("   • Disable player ID validation for bulk imports")
    print("   • Use database connection pooling")
    
    print("\n3. 🔍 MONITORING:")
    print("   • Check Railway resource usage")
    print("   • Monitor database connection limits")
    print("   • Track import progress more granularly")
    
    print("\n4. 🚀 IMMEDIATE ACTIONS:")
    print("   • Clear any stuck ETL processes")
    print("   • Check data/leagues/all/ for corrupt JSON files")
    print("   • Verify database schema integrity")


if __name__ == "__main__":
    print("Starting ETL failure diagnostic analysis...")
    
    success = analyze_database_state()
    
    if success:
        provide_recommendations()
    else:
        print("\n❌ Diagnostic analysis failed - check database connectivity")
    
    print(f"\nDiagnostic completed at {datetime.now().strftime('%H:%M:%S')}") 