#!/usr/bin/env python3
"""
Database Differences Summary
Simple and clean analysis of differences between local and Railway databases
"""

import psycopg2
from urllib.parse import urlparse
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'sslmode': 'require',
        'connect_timeout': 10
    }
    return psycopg2.connect(**conn_params)

def main():
    """Main analysis function"""
    print("=" * 100)
    print("🔍 DATABASE DIFFERENCES ANALYSIS")
    print("=" * 100)
    
    with get_db() as local_conn:
        railway_conn = connect_to_railway()
        
        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()
        
        # 1. TABLE COUNTS COMPARISON
        print("\n📊 TABLE COUNTS COMPARISON")
        print("=" * 80)
        
        tables = [
            'users', 'leagues', 'clubs', 'players', 'series', 'series_stats',
            'match_scores', 'player_availability', 'schedule', 'player_history',
            'user_player_associations', 'user_instructions', 'user_activity_logs'
        ]
        
        print(f"{'Table':<25} {'Local':<12} {'Railway':<12} {'Difference':<12} {'Status':<15}")
        print("-" * 80)
        
        critical_gaps = []
        partial_migrations = []
        perfect_matches = []
        
        for table in tables:
            try:
                local_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                local_count = local_cursor.fetchone()[0]
                
                railway_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                railway_count = railway_cursor.fetchone()[0]
                
                diff = railway_count - local_count
                coverage = (railway_count / local_count * 100) if local_count > 0 else 0
                
                if railway_count == local_count:
                    status = "✅ PERFECT"
                    perfect_matches.append((table, local_count))
                elif railway_count == 0 and local_count > 0:
                    status = "❌ MISSING"
                    critical_gaps.append((table, local_count))
                elif coverage < 90:
                    status = f"🟡 {coverage:.1f}%"
                    partial_migrations.append((table, local_count, railway_count, coverage))
                else:
                    status = f"🟢 {coverage:.1f}%"
                
                print(f"{table:<25} {local_count:<12} {railway_count:<12} {diff:<12} {status:<15}")
                
            except Exception as e:
                print(f"{table:<25} {'ERROR':<12} {'ERROR':<12} {'N/A':<12} {'❌ ERROR':<15}")
        
        # 2. CRITICAL GAPS ANALYSIS
        if critical_gaps:
            print(f"\n❌ CRITICAL DATA GAPS")
            print("=" * 80)
            for table, count in critical_gaps:
                print(f"  • {table}: {count:,} records missing from Railway")
        
        # 3. PARTIAL MIGRATIONS
        if partial_migrations:
            print(f"\n🟡 PARTIAL MIGRATIONS")
            print("=" * 80)
            for table, local, railway, coverage in partial_migrations:
                missing = local - railway
                print(f"  • {table}: {missing:,} records missing ({coverage:.1f}% coverage)")
        
        # 4. PERFECT MATCHES
        if perfect_matches:
            print(f"\n✅ PERFECT MIGRATIONS")
            print("=" * 80)
            for table, count in perfect_matches:
                print(f"  • {table}: {count:,} records (100% match)")
        
        # 5. LEAGUE-SPECIFIC ANALYSIS
        print(f"\n🏆 LEAGUE-SPECIFIC ANALYSIS")
        print("=" * 80)
        
        # Get league distribution
        league_query = """
            SELECT l.league_name, COUNT(p.id) as player_count, COUNT(DISTINCT p.club_id) as club_count
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            GROUP BY l.id, l.league_name
            ORDER BY player_count DESC
        """
        
        print("LOCAL DATABASE:")
        local_cursor.execute(league_query)
        local_leagues = local_cursor.fetchall()
        for league, players, clubs in local_leagues:
            print(f"  • {league}: {players:,} players across {clubs} clubs")
        
        print("\nRAILWAY DATABASE:")
        railway_cursor.execute(league_query)
        railway_leagues = railway_cursor.fetchall()
        for league, players, clubs in railway_leagues:
            print(f"  • {league}: {players:,} players across {clubs} clubs")
        
        # 6. CLUBS COMPARISON
        print(f"\n🏢 CLUBS COMPARISON")
        print("=" * 80)
        
        # Get club names
        local_cursor.execute("SELECT name FROM clubs ORDER BY name")
        local_clubs = {row[0].strip().lower() for row in local_cursor.fetchall()}
        
        railway_cursor.execute("SELECT name FROM clubs ORDER BY name")
        railway_clubs = {row[0].strip().lower() for row in railway_cursor.fetchall()}
        
        missing_in_railway = local_clubs - railway_clubs
        extra_in_railway = railway_clubs - local_clubs
        common_clubs = local_clubs & railway_clubs
        
        print(f"  • Total clubs in local: {len(local_clubs)}")
        print(f"  • Total clubs in Railway: {len(railway_clubs)}")
        print(f"  • Common clubs: {len(common_clubs)}")
        print(f"  • Missing from Railway: {len(missing_in_railway)}")
        print(f"  • Extra in Railway: {len(extra_in_railway)}")
        
        if missing_in_railway:
            print(f"\n  Missing clubs from Railway:")
            for club in sorted(missing_in_railway)[:10]:
                print(f"    - {club}")
        
        if extra_in_railway:
            print(f"\n  Extra clubs in Railway:")
            for club in sorted(extra_in_railway)[:10]:
                print(f"    - {club}")
        
        # 7. SERIES COMPARISON
        print(f"\n🏆 SERIES COMPARISON")
        print("=" * 80)
        
        # Get series names
        local_cursor.execute("SELECT name FROM series ORDER BY name")
        local_series = {row[0].strip().lower() for row in local_cursor.fetchall()}
        
        railway_cursor.execute("SELECT name FROM series ORDER BY name")
        railway_series = {row[0].strip().lower() for row in railway_cursor.fetchall()}
        
        missing_series = local_series - railway_series
        extra_series = railway_series - local_series
        common_series = local_series & railway_series
        
        print(f"  • Total series in local: {len(local_series)}")
        print(f"  • Total series in Railway: {len(railway_series)}")
        print(f"  • Common series: {len(common_series)}")
        print(f"  • Missing from Railway: {len(missing_series)}")
        print(f"  • Extra in Railway: {len(extra_series)}")
        
        if missing_series:
            print(f"\n  Missing series from Railway:")
            for series in sorted(missing_series):
                print(f"    - {series}")
        
        # 8. DATA QUALITY CHECK
        print(f"\n🔬 DATA QUALITY COMPARISON")
        print("=" * 80)
        
        # Check for duplicate player names
        duplicate_query = """
            SELECT first_name, last_name, COUNT(*) as count
            FROM players 
            GROUP BY first_name, last_name 
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """
        
        print("LOCAL DATABASE DUPLICATES:")
        local_cursor.execute(duplicate_query)
        local_dups = local_cursor.fetchall()
        if local_dups:
            for fname, lname, count in local_dups:
                print(f"  • {fname} {lname}: {count} instances")
        else:
            print("  • No significant duplicates found")
        
        print("\nRAILWAY DATABASE DUPLICATES:")
        railway_cursor.execute(duplicate_query)
        railway_dups = railway_cursor.fetchall()
        if railway_dups:
            for fname, lname, count in railway_dups:
                print(f"  • {fname} {lname}: {count} instances")
        else:
            print("  • No significant duplicates found")
        
        # 9. SUMMARY AND RECOMMENDATIONS
        print(f"\n💡 SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        
        total_local_records = sum(local_count for table, local_count in perfect_matches) + sum(local for _, local, _, _ in partial_migrations) + sum(count for _, count in critical_gaps)
        total_railway_records = sum(local_count for table, local_count in perfect_matches) + sum(railway for _, _, railway, _ in partial_migrations)
        
        overall_coverage = (total_railway_records / total_local_records * 100) if total_local_records > 0 else 0
        
        print(f"📊 OVERALL STATUS:")
        print(f"  • Migration Coverage: {overall_coverage:.1f}%")
        print(f"  • Perfect Matches: {len(perfect_matches)} tables")
        print(f"  • Partial Migrations: {len(partial_migrations)} tables")
        print(f"  • Critical Gaps: {len(critical_gaps)} tables")
        
        print(f"\n🎯 PRIORITY ACTIONS:")
        if critical_gaps:
            print(f"  1. HIGH: Migrate missing data tables")
            for table, count in critical_gaps:
                if count > 1000:
                    print(f"     - {table}: {count:,} records (HIGH IMPACT)")
        
        if missing_in_railway:
            print(f"  2. MEDIUM: Add {len(missing_in_railway)} missing clubs to Railway")
        
        if partial_migrations:
            print(f"  3. LOW: Complete partial migrations")
            for table, local, railway, coverage in partial_migrations:
                if coverage < 80:
                    print(f"     - {table}: {local-railway:,} missing records")
        
        railway_conn.close()

if __name__ == "__main__":
    main() 