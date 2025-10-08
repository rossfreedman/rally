#!/usr/bin/env python3
"""
Comprehensive validation script to compare staging vs local APTA data.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def validate_apta_data(environment_name, db_url=None):
    """Validate APTA data for a specific environment."""
    print(f"🔍 VALIDATING APTA DATA - {environment_name.upper()}")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Environment: {environment_name}")
    print()
    
    # Set up database connection
    if db_url:
        # Use provided database URL (for staging)
        import psycopg2
        conn = psycopg2.connect(db_url)
        try:
            with conn.cursor() as cur:
                return _validate_with_cursor(cur, environment_name)
        finally:
            conn.close()
    else:
        # Use local database
        from database_config import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                return _validate_with_cursor(cur, environment_name)

def _validate_with_cursor(cur, environment_name):
    """Validate APTA data using a database cursor."""
    # Get APTA league ID
    cur.execute("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
    league_result = cur.fetchone()
    if not league_result:
        print(f"❌ APTA_CHICAGO league not found in {environment_name}")
        return None
    
    league_id = league_result[0]
    print(f"✅ Found APTA league ID: {league_id}")
    
    # Basic counts
    cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_id,))
    total_players = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM players WHERE league_id = %s AND captain_status = 'true'", (league_id,))
    captains = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT team_id) FROM players WHERE league_id = %s", (league_id,))
    unique_teams = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT club_id) FROM players WHERE league_id = %s", (league_id,))
    unique_clubs = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT series_id) FROM players WHERE league_id = %s", (league_id,))
    unique_series = cur.fetchone()[0]
    
    # Career stats analysis
    cur.execute("""
        SELECT 
            COUNT(*) as total_players,
            COUNT(CASE WHEN career_wins > 0 OR career_losses > 0 THEN 1 END) as players_with_career_stats,
            COUNT(CASE WHEN career_wins = 0 AND career_losses = 0 THEN 1 END) as players_without_career_stats,
            AVG(career_wins) as avg_career_wins,
            AVG(career_losses) as avg_career_losses,
            AVG(career_win_percentage) as avg_career_win_pct
        FROM players 
        WHERE league_id = %s
    """, (league_id,))
    career_stats = cur.fetchone()
    
    # Series distribution
    cur.execute("""
        SELECT s.name, COUNT(p.id) as player_count
        FROM players p
        JOIN series s ON p.series_id = s.id
        WHERE p.league_id = %s
        GROUP BY s.name
        ORDER BY player_count DESC
        LIMIT 10
    """, (league_id,))
    series_dist = cur.fetchall()
    
    # Club distribution
    cur.execute("""
        SELECT c.name, COUNT(p.id) as player_count
        FROM players p
        JOIN clubs c ON p.club_id = c.id
        WHERE p.league_id = %s
        GROUP BY c.name
        ORDER BY player_count DESC
        LIMIT 10
    """, (league_id,))
    club_dist = cur.fetchall()
    
    # Data quality checks
    cur.execute("""
        SELECT COUNT(*) FROM players 
        WHERE league_id = %s AND (first_name IS NULL OR first_name = '' OR last_name IS NULL OR last_name = '')
    """, (league_id,))
    missing_names = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM players 
        WHERE league_id = %s AND (tenniscores_player_id IS NULL OR tenniscores_player_id = '')
    """, (league_id,))
    missing_player_ids = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM players 
        WHERE league_id = %s AND team_id IS NULL
    """, (league_id,))
    missing_teams = cur.fetchone()[0]
    
    # Compile results
    results = {
        'environment': environment_name,
        'total_players': total_players,
        'captains': captains,
        'unique_teams': unique_teams,
        'unique_clubs': unique_clubs,
        'unique_series': unique_series,
        'career_stats': {
            'total_players': career_stats[0],
            'players_with_career_stats': career_stats[1],
            'players_without_career_stats': career_stats[2],
            'avg_career_wins': float(career_stats[3]) if career_stats[3] else 0,
            'avg_career_losses': float(career_stats[4]) if career_stats[4] else 0,
            'avg_career_win_pct': float(career_stats[5]) if career_stats[5] else 0
        },
        'series_distribution': series_dist,
        'club_distribution': club_dist,
        'data_quality': {
            'missing_names': missing_names,
            'missing_player_ids': missing_player_ids,
            'missing_teams': missing_teams
        }
    }
    
    # Print results
    print(f"📊 BASIC COUNTS:")
    print(f"   Total Players: {total_players:,}")
    print(f"   Captains: {captains:,}")
    print(f"   Unique Teams: {unique_teams:,}")
    print(f"   Unique Clubs: {unique_clubs:,}")
    print(f"   Unique Series: {unique_series:,}")
    print()
    
    print(f"📈 CAREER STATS:")
    print(f"   Players with career stats: {career_stats[1]:,}")
    print(f"   Players without career stats: {career_stats[2]:,}")
    print(f"   Average career wins: {career_stats[3]:.1f}")
    print(f"   Average career losses: {career_stats[4]:.1f}")
    print(f"   Average career win %: {career_stats[5]:.1f}%")
    print()
    
    print(f"🏆 TOP 5 SERIES:")
    for i, (series_name, count) in enumerate(series_dist[:5], 1):
        print(f"   {i}. {series_name}: {count:,} players")
    print()
    
    print(f"🏢 TOP 5 CLUBS:")
    for i, (club_name, count) in enumerate(club_dist[:5], 1):
        print(f"   {i}. {club_name}: {count:,} players")
    print()
    
    print(f"🔍 DATA QUALITY:")
    print(f"   Missing names: {missing_names:,}")
    print(f"   Missing player IDs: {missing_player_ids:,}")
    print(f"   Missing teams: {missing_teams:,}")
    print()
    
    return results

def compare_environments(local_results, staging_results):
    """Compare local vs staging results."""
    print("🔄 COMPARING LOCAL VS STAGING")
    print("=" * 60)
    
    if not local_results or not staging_results:
        print("❌ Cannot compare - missing results from one or both environments")
        return
    
    # Basic comparison
    print("📊 BASIC COUNTS COMPARISON:")
    fields = ['total_players', 'captains', 'unique_teams', 'unique_clubs', 'unique_series']
    for field in fields:
        local_val = local_results[field]
        staging_val = staging_results[field]
        match = "✅" if local_val == staging_val else "❌"
        print(f"   {field}: Local={local_val:,}, Staging={staging_val:,} {match}")
    
    print()
    
    # Career stats comparison
    print("📈 CAREER STATS COMPARISON:")
    career_fields = ['players_with_career_stats', 'players_without_career_stats', 'avg_career_wins', 'avg_career_losses', 'avg_career_win_pct']
    for field in career_fields:
        local_val = local_results['career_stats'][field]
        staging_val = staging_results['career_stats'][field]
        if isinstance(local_val, float):
            match = "✅" if abs(local_val - staging_val) < 0.1 else "❌"
            print(f"   {field}: Local={local_val:.1f}, Staging={staging_val:.1f} {match}")
        else:
            match = "✅" if local_val == staging_val else "❌"
            print(f"   {field}: Local={local_val:,}, Staging={staging_val:,} {match}")
    
    print()
    
    # Data quality comparison
    print("🔍 DATA QUALITY COMPARISON:")
    quality_fields = ['missing_names', 'missing_player_ids', 'missing_teams']
    for field in quality_fields:
        local_val = local_results['data_quality'][field]
        staging_val = staging_results['data_quality'][field]
        match = "✅" if local_val == staging_val else "❌"
        print(f"   {field}: Local={local_val:,}, Staging={staging_val:,} {match}")
    
    print()
    
    # Overall assessment
    total_matches = 0
    total_fields = 0
    
    for field in fields:
        total_fields += 1
        if local_results[field] == staging_results[field]:
            total_matches += 1
    
    for field in career_fields:
        total_fields += 1
        local_val = local_results['career_stats'][field]
        staging_val = staging_results['career_stats'][field]
        if isinstance(local_val, float):
            if abs(local_val - staging_val) < 0.1:
                total_matches += 1
        else:
            if local_val == staging_val:
                total_matches += 1
    
    for field in quality_fields:
        total_fields += 1
        if local_results['data_quality'][field] == staging_results['data_quality'][field]:
            total_matches += 1
    
    match_percentage = (total_matches / total_fields) * 100
    print(f"🎯 OVERALL MATCH: {total_matches}/{total_fields} fields match ({match_percentage:.1f}%)")
    
    if match_percentage >= 95:
        print("✅ EXCELLENT MATCH - Staging and local are nearly identical!")
    elif match_percentage >= 90:
        print("✅ GOOD MATCH - Minor differences detected")
    elif match_percentage >= 80:
        print("⚠️  MODERATE MATCH - Some differences detected")
    else:
        print("❌ POOR MATCH - Significant differences detected")

def main():
    print("🚀 COMPREHENSIVE STAGING VS LOCAL VALIDATION")
    print("=" * 70)
    print()
    
    # Validate local
    print("1️⃣ VALIDATING LOCAL DATABASE...")
    local_results = validate_apta_data("LOCAL")
    print()
    
    # Validate staging
    print("2️⃣ VALIDATING STAGING DATABASE...")
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    staging_results = validate_apta_data("STAGING", staging_url)
    print()
    
    # Compare results
    if local_results and staging_results:
        compare_environments(local_results, staging_results)
    else:
        print("❌ Validation failed for one or both environments")

if __name__ == "__main__":
    main()
