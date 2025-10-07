#!/usr/bin/env python3
"""
Comprehensive Local vs Staging Database Comparison

This script performs a detailed comparison between local and staging databases
to identify any remaining issues or inconsistencies.

COMPARISON AREAS:
- Series naming and counts
- Team assignments and player counts
- Player records and duplicates
- Club assignments
- League context
- Data integrity
"""

import psycopg2
import sys
from typing import Dict, List, Tuple, Any

# Database configurations
LOCAL_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'rally',
    'user': 'rossfreedman'
}

STAGING_DB_URL = 'postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway'
APTA_LEAGUE_ID = 4783

def get_local_connection():
    """Get local database connection."""
    try:
        from database_utils import execute_query
        return execute_query
    except ImportError:
        print("❌ Cannot import database_utils for local connection")
        return None

def get_staging_connection():
    """Get staging database connection."""
    try:
        return psycopg2.connect(STAGING_DB_URL)
    except Exception as e:
        print(f"❌ Cannot connect to staging: {e}")
        return None

def compare_series_data():
    """Compare series data between local and staging."""
    print("🔍 COMPARING SERIES DATA")
    print("=" * 30)
    
    local_query = get_local_connection()
    if not local_query:
        print("❌ Cannot compare series data - local connection failed")
        return
    
    staging_conn = get_staging_connection()
    if not staging_conn:
        print("❌ Cannot compare series data - staging connection failed")
        return
    
    try:
        # Local series data
        local_series_query = '''
        SELECT 
            s.id, s.name, s.league_id,
            COUNT(t.id) as team_count,
            COUNT(p.id) as player_count
        FROM series s
        LEFT JOIN teams t ON s.id = t.series_id
        LEFT JOIN players p ON t.id = p.team_id
        WHERE s.league_id = %s
        GROUP BY s.id, s.name, s.league_id
        ORDER BY s.name
        '''
        
        local_series = local_query(local_series_query, (APTA_LEAGUE_ID,))
        
        # Staging series data
        with staging_conn.cursor() as cur:
            cur.execute(local_series_query, (APTA_LEAGUE_ID,))
            staging_series = cur.fetchall()
        
        print(f"Local series: {len(local_series)}")
        print(f"Staging series: {len(staging_series)}")
        
        # Convert to comparable format
        local_dict = {s['name']: {'id': s['id'], 'teams': s['team_count'], 'players': s['player_count']} for s in local_series}
        staging_dict = {s[1]: {'id': s[0], 'teams': s[3], 'players': s[4]} for s in staging_series}
        
        # Find differences
        all_series = set(local_dict.keys()) | set(staging_dict.keys())
        
        differences = []
        for series_name in sorted(all_series):
            local_data = local_dict.get(series_name, {'teams': 0, 'players': 0})
            staging_data = staging_dict.get(series_name, {'teams': 0, 'players': 0})
            
            if local_data['teams'] != staging_data['teams'] or local_data['players'] != staging_data['players']:
                differences.append({
                    'series': series_name,
                    'local_teams': local_data['teams'],
                    'staging_teams': staging_data['teams'],
                    'local_players': local_data['players'],
                    'staging_players': staging_data['players']
                })
        
        if differences:
            print(f"\n⚠️  SERIES DIFFERENCES FOUND: {len(differences)}")
            for diff in differences:
                print(f"  - {diff['series']}:")
                print(f"    Teams: Local={diff['local_teams']}, Staging={diff['staging_teams']}")
                print(f"    Players: Local={diff['local_players']}, Staging={diff['staging_players']}")
        else:
            print("✅ Series data matches perfectly")
            
    except Exception as e:
        print(f"❌ Error comparing series data: {e}")
    finally:
        staging_conn.close()

def compare_team_assignments():
    """Compare team assignments for PD I/II teams."""
    print("\n🔍 COMPARING PD I/II TEAM ASSIGNMENTS")
    print("=" * 40)
    
    local_query = get_local_connection()
    if not local_query:
        print("❌ Cannot compare team assignments - local connection failed")
        return
    
    staging_conn = get_staging_connection()
    if not staging_conn:
        print("❌ Cannot compare team assignments - staging connection failed")
        return
    
    try:
        # Query for PD I/II teams
        team_query = '''
        SELECT 
            t.id, t.team_name, c.name as club_name, s.name as series_name,
            COUNT(p.id) as player_count
        FROM teams t
        JOIN clubs c ON t.club_id = c.id
        JOIN series s ON t.series_id = s.id
        LEFT JOIN players p ON t.id = p.team_id
        WHERE t.league_id = %s
            AND (t.team_name LIKE '% PD I %' OR t.team_name LIKE '% PD II %')
        GROUP BY t.id, t.team_name, c.name, s.name
        ORDER BY s.name, c.name, t.team_name
        '''
        
        # Local data
        local_teams = local_query(team_query, (APTA_LEAGUE_ID,))
        
        # Staging data
        with staging_conn.cursor() as cur:
            cur.execute(team_query, (APTA_LEAGUE_ID,))
            staging_teams = cur.fetchall()
        
        print(f"Local PD I/II teams: {len(local_teams)}")
        print(f"Staging PD I/II teams: {len(staging_teams)}")
        
        # Convert to comparable format
        local_dict = {}
        for team in local_teams:
            key = f"{team['club_name']} {team['team_name']} {team['series_name']}"
            local_dict[key] = {
                'id': team['id'],
                'players': team['player_count']
            }
        
        staging_dict = {}
        for team in staging_teams:
            key = f"{team[2]} {team[1]} {team[3]}"
            staging_dict[key] = {
                'id': team[0],
                'players': team[4]
            }
        
        # Find differences
        all_teams = set(local_dict.keys()) | set(staging_dict.keys())
        
        differences = []
        for team_key in sorted(all_teams):
            local_data = local_dict.get(team_key, {'players': 0})
            staging_data = staging_dict.get(team_key, {'players': 0})
            
            if local_data['players'] != staging_data['players']:
                differences.append({
                    'team': team_key,
                    'local_players': local_data['players'],
                    'staging_players': staging_data['players']
                })
        
        if differences:
            print(f"\n⚠️  TEAM ASSIGNMENT DIFFERENCES: {len(differences)}")
            for diff in differences:
                print(f"  - {diff['team']}:")
                print(f"    Players: Local={diff['local_players']}, Staging={diff['staging_players']}")
        else:
            print("✅ PD I/II team assignments match perfectly")
            
    except Exception as e:
        print(f"❌ Error comparing team assignments: {e}")
    finally:
        staging_conn.close()

def compare_duplicate_players():
    """Compare duplicate player records."""
    print("\n🔍 COMPARING DUPLICATE PLAYER RECORDS")
    print("=" * 40)
    
    local_query = get_local_connection()
    if not local_query:
        print("❌ Cannot compare duplicates - local connection failed")
        return
    
    staging_conn = get_staging_connection()
    if not staging_conn:
        print("❌ Cannot compare duplicates - staging connection failed")
        return
    
    try:
        # Query for duplicate players
        duplicate_query = '''
        SELECT 
            p.tenniscores_player_id,
            p.first_name, p.last_name,
            COUNT(*) as duplicate_count
        FROM players p
        JOIN teams t ON p.team_id = t.id
        WHERE t.league_id = %s
        GROUP BY p.tenniscores_player_id, p.first_name, p.last_name
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, p.last_name, p.first_name
        '''
        
        # Local duplicates
        local_duplicates = local_query(duplicate_query, (APTA_LEAGUE_ID,))
        
        # Staging duplicates
        with staging_conn.cursor() as cur:
            cur.execute(duplicate_query, (APTA_LEAGUE_ID,))
            staging_duplicates = cur.fetchall()
        
        print(f"Local duplicate players: {len(local_duplicates)}")
        print(f"Staging duplicate players: {len(staging_duplicates)}")
        
        if local_duplicates:
            print("\nLocal duplicates:")
            for dup in local_duplicates[:10]:  # Show first 10
                print(f"  - {dup['first_name']} {dup['last_name']} ({dup['tenniscores_player_id']}): {dup['duplicate_count']} records")
        
        if staging_duplicates:
            print("\nStaging duplicates:")
            for dup in staging_duplicates[:10]:  # Show first 10
                print(f"  - {dup[1]} {dup[2]} ({dup[0]}): {dup[3]} records")
        
        if not local_duplicates and not staging_duplicates:
            print("✅ No duplicate players found in either database")
        elif len(local_duplicates) == len(staging_duplicates):
            print("✅ Duplicate counts match between databases")
        else:
            print("⚠️  Duplicate counts differ between databases")
            
    except Exception as e:
        print(f"❌ Error comparing duplicates: {e}")
    finally:
        staging_conn.close()

def compare_data_integrity():
    """Compare overall data integrity metrics."""
    print("\n🔍 COMPARING DATA INTEGRITY METRICS")
    print("=" * 40)
    
    local_query = get_local_connection()
    if not local_query:
        print("❌ Cannot compare integrity - local connection failed")
        return
    
    staging_conn = get_staging_connection()
    if not staging_conn:
        print("❌ Cannot compare integrity - staging connection failed")
        return
    
    try:
        # Overall counts query
        counts_query = '''
        SELECT 
            'leagues' as table_name, COUNT(*) as count FROM leagues WHERE id = %s
        UNION ALL
        SELECT 'clubs', COUNT(*) FROM clubs WHERE league_id = %s
        UNION ALL
        SELECT 'series', COUNT(*) FROM series WHERE league_id = %s
        UNION ALL
        SELECT 'teams', COUNT(*) FROM teams WHERE league_id = %s
        UNION ALL
        SELECT 'players', COUNT(*) FROM players p JOIN teams t ON p.team_id = t.id WHERE t.league_id = %s
        '''
        
        # Local counts
        local_counts = local_query(counts_query, (APTA_LEAGUE_ID, APTA_LEAGUE_ID, APTA_LEAGUE_ID, APTA_LEAGUE_ID, APTA_LEAGUE_ID))
        
        # Staging counts
        with staging_conn.cursor() as cur:
            cur.execute(counts_query, (APTA_LEAGUE_ID, APTA_LEAGUE_ID, APTA_LEAGUE_ID, APTA_LEAGUE_ID, APTA_LEAGUE_ID))
            staging_counts = cur.fetchall()
        
        print("Data integrity comparison:")
        print(f"{'Table':<10} {'Local':<10} {'Staging':<10} {'Match':<5}")
        print("-" * 40)
        
        all_match = True
        for i, (local_count, staging_count) in enumerate(zip(local_counts, staging_counts)):
            table_name = local_count['table_name']
            local_val = local_count['count']
            staging_val = staging_count[1]
            match = local_val == staging_val
            all_match = all_match and match
            
            print(f"{table_name:<10} {local_val:<10} {staging_val:<10} {'✅' if match else '❌'}")
        
        if all_match:
            print("\n✅ All data integrity metrics match perfectly")
        else:
            print("\n⚠️  Some data integrity metrics differ")
            
    except Exception as e:
        print(f"❌ Error comparing data integrity: {e}")
    finally:
        staging_conn.close()

def main():
    """Main comparison function."""
    print("🔍 COMPREHENSIVE LOCAL vs STAGING COMPARISON")
    print("=" * 50)
    print(f"League ID: {APTA_LEAGUE_ID}")
    print(f"Local: {LOCAL_DB_CONFIG['host']}:{LOCAL_DB_CONFIG['port']}/{LOCAL_DB_CONFIG['dbname']}")
    print(f"Staging: switchback.proxy.rlwy.net:28473/railway")
    print()
    
    # Run all comparisons
    compare_series_data()
    compare_team_assignments()
    compare_duplicate_players()
    compare_data_integrity()
    
    print("\n🎯 COMPARISON COMPLETE")
    print("=" * 25)
    print("Review the results above to identify any remaining issues.")
    print("Focus on any ⚠️ warnings or ❌ mismatches found.")

if __name__ == "__main__":
    main()
