#!/usr/bin/env python3
"""
Fix Series Conflicts and Team Assignments

This script resolves the series naming conflicts caused by the broken ETL mapping system
and reassigns players to the correct teams.

Issues resolved:
1. Duplicate series with different names (e.g., "Series 2B" vs "S2B")
2. Players assigned to wrong series IDs
3. Players with NULL team_id due to series mismatches
4. Broken team assignments across the platform

Usage: python scripts/fix_series_conflicts_and_team_assignments.py [--dry-run]
"""

import os
import sys
import argparse
from datetime import datetime

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db


def log(message: str, level: str = "INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def create_series_mapping_table(conn):
    """DEPRECATED: Create the series_name_mappings table if it doesn't exist"""
    log("📋 DEPRECATED: series_name_mappings table creation - now using series.display_name column")
    
    # This function is deprecated but kept for backward compatibility
    # The series.display_name migration has replaced the series_name_mappings table
    log("✅ Skipping series_name_mappings table creation (deprecated)")


def populate_series_mappings(conn):
    """Populate series mappings with the correct consolidation patterns"""
    log("🔧 Populating series mappings...")
    
    cursor = conn.cursor()
    
    # Define the series consolidation mappings
    # Format: (league_id, user_facing_format, database_format)
    mappings = [
        # NSTF: Consolidate "Series X" -> "SX" 
        ("NSTF", "Series 1", "S1"),
        ("NSTF", "Series 2A", "S2A"),
        ("NSTF", "Series 2B", "S2B"),
        ("NSTF", "Series 3", "S3"),
        ("NSTF", "Series 4", "S4"),
        
        # APTA_CHICAGO: Consolidate "Chicago X" -> "X"
        ("APTA_CHICAGO", "Chicago 1", "1"),
        ("APTA_CHICAGO", "Chicago 2", "2"),
        ("APTA_CHICAGO", "Chicago 3", "3"),
        ("APTA_CHICAGO", "Chicago 11", "11"),
        ("APTA_CHICAGO", "Chicago 12", "12"),
        ("APTA_CHICAGO", "Chicago 13", "13"),
        ("APTA_CHICAGO", "Chicago 21", "21"),
        ("APTA_CHICAGO", "Chicago 22", "22"),
        ("APTA_CHICAGO", "Chicago 23", "23"),
        ("APTA_CHICAGO", "Chicago 31", "31"),
        ("APTA_CHICAGO", "Chicago 32", "32"),
        ("APTA_CHICAGO", "Chicago 33", "33"),
        
        # CNSWPL: Consolidate "Division X" -> "X"
        ("CNSWPL", "Division 1", "1"),
        ("CNSWPL", "Division 1a", "1a"),
        ("CNSWPL", "Division 2", "2"),
        ("CNSWPL", "Division 2a", "2a"),
        ("CNSWPL", "Division 3", "3"),
    ]
    
    # DEPRECATED: Mappings are now handled by series.display_name column
    log("✅ Skipping series mappings population (deprecated - using series.display_name)")


def analyze_series_conflicts(conn):
    """Analyze and log series conflicts"""
    log("🔍 Analyzing series conflicts...")
    
    cursor = conn.cursor()
    
    # Find series conflicts using the mapping patterns
    conflicts = []
    
    # Check each league for conflicts
    leagues = ["NSTF", "APTA_CHICAGO", "CNSWPL"]
    
    for league_id in leagues:
        cursor.execute("""
            SELECT l.id as league_db_id
            FROM leagues l
            WHERE l.league_id = %s
        """, (league_id,))
        
        league_result = cursor.fetchone()
        if not league_result:
            continue
            
        league_db_id = league_result[0]
        
        # Get all series in this league
        cursor.execute("""
            SELECT s.id, s.name, s.display_name, COUNT(p.id) as player_count,
                   COUNT(t.id) as team_count
            FROM series s
            LEFT JOIN series_leagues sl ON s.id = sl.series_id
            LEFT JOIN players p ON s.id = p.series_id
            LEFT JOIN teams t ON s.id = t.series_id
            WHERE sl.league_id = %s
            GROUP BY s.id, s.name, s.display_name
            ORDER BY s.name
        """, (league_db_id,))
        
        series_data = cursor.fetchall()
        
        # Group by expected database format
        series_groups = {}
        for series_id, name, display_name, player_count, team_count in series_data:
            # Determine expected database format
            expected_db_format = get_expected_database_format(name, league_id)
            
            if expected_db_format not in series_groups:
                series_groups[expected_db_format] = []
            
            series_groups[expected_db_format].append({
                'id': series_id,
                'name': name,
                'display_name': display_name,
                'player_count': player_count,
                'team_count': team_count
            })
        
        # Find conflicts (multiple series mapping to same database format)
        for expected_format, series_list in series_groups.items():
            if len(series_list) > 1:
                conflicts.append({
                    'league_id': league_id,
                    'expected_format': expected_format,
                    'series_list': series_list
                })
    
    log(f"📊 Found {len(conflicts)} series conflicts")
    
    for conflict in conflicts:
        log(f"   🔍 {conflict['league_id']} - Expected: '{conflict['expected_format']}'")
        for series in conflict['series_list']:
            log(f"      Series ID {series['id']}: '{series['name']}' ({series['player_count']} players, {series['team_count']} teams)")
    
    return conflicts


def get_expected_database_format(series_name: str, league_id: str) -> str:
    """Get the expected database format for a series name"""
    # This matches the logic in the ETL script
    if league_id == "NSTF":
        if series_name.startswith("Series "):
            return series_name.replace("Series ", "S")
        else:
            return series_name
    elif league_id == "APTA_CHICAGO":
        if series_name.startswith("Chicago "):
            return series_name.replace("Chicago ", "")
        else:
            return series_name
    elif league_id == "CNSWPL":
        if series_name.startswith("Division "):
            return series_name.replace("Division ", "")
        else:
            return series_name
    
    return series_name


def consolidate_series_conflicts(conn, conflicts, dry_run=False):
    """Consolidate duplicate series by merging them"""
    log("🔧 Consolidating series conflicts...")
    
    cursor = conn.cursor()
    total_consolidated = 0
    
    for conflict in conflicts:
        league_id = conflict['league_id']
        expected_format = conflict['expected_format']
        series_list = conflict['series_list']
        
        # Find the "canonical" series to keep (prefer the one with database format name)
        canonical_series = None
        for series in series_list:
            if series['name'] == expected_format:
                canonical_series = series
                break
        
        # If no exact match, pick the one with the most players+teams
        if not canonical_series:
            canonical_series = max(series_list, key=lambda s: s['player_count'] + s['team_count'])
        
        # Get series IDs to merge
        series_ids_to_merge = [s['id'] for s in series_list if s['id'] != canonical_series['id']]
        
        if not series_ids_to_merge:
            continue
            
        log(f"   📋 {league_id}: Consolidating {len(series_ids_to_merge)} series into '{canonical_series['name']}' (ID: {canonical_series['id']})")
        
        if not dry_run:
            # Update all references to point to canonical series
            for old_series_id in series_ids_to_merge:
                # Update players
                cursor.execute("""
                    UPDATE players SET series_id = %s WHERE series_id = %s
                """, (canonical_series['id'], old_series_id))
                players_updated = cursor.rowcount
                
                # Update teams
                cursor.execute("""
                    UPDATE teams SET series_id = %s WHERE series_id = %s
                """, (canonical_series['id'], old_series_id))
                teams_updated = cursor.rowcount
                
                # Handle series_leagues carefully - delete old entries to avoid constraint violations
                cursor.execute("""
                    DELETE FROM series_leagues WHERE series_id = %s
                """, (old_series_id,))
                
                # Update series_stats
                cursor.execute("""
                    UPDATE series_stats SET series_id = %s WHERE series_id = %s
                """, (canonical_series['id'], old_series_id))
                
                log(f"      🔄 Merged series ID {old_series_id}: {players_updated} players, {teams_updated} teams")
            
            # Delete the old series
            for old_series_id in series_ids_to_merge:
                cursor.execute("DELETE FROM series WHERE id = %s", (old_series_id,))
            
            # Update canonical series name to expected format
            cursor.execute("""
                UPDATE series SET name = %s, display_name = %s WHERE id = %s
            """, (expected_format, expected_format, canonical_series['id']))
            
            conn.commit()
            total_consolidated += len(series_ids_to_merge)
        else:
            log(f"      [DRY RUN] Would merge {len(series_ids_to_merge)} series")
    
    log(f"✅ Consolidated {total_consolidated} duplicate series")
    return total_consolidated


def fix_player_team_assignments(conn, dry_run=False):
    """Fix players with NULL team_id by finding their correct teams"""
    log("🔧 Fixing player team assignments...")
    
    cursor = conn.cursor()
    
    # Find players with NULL team_id who should have teams
    cursor.execute("""
        SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
               p.club_id, p.series_id, p.league_id,
               c.name as club_name, s.name as series_name, l.league_name
        FROM players p
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        JOIN leagues l ON p.league_id = l.id
        WHERE p.team_id IS NULL
        ORDER BY l.league_name, c.name, s.name, p.last_name, p.first_name
    """)
    
    players_to_fix = cursor.fetchall()
    log(f"📊 Found {len(players_to_fix)} players with NULL team_id")
    
    fixed_count = 0
    
    for player in players_to_fix:
        player_id, tenniscores_id, first_name, last_name, club_id, series_id, league_id, club_name, series_name, league_name = player
        
        # Find team for this player's club/series/league combination
        cursor.execute("""
            SELECT t.id, t.team_name
            FROM teams t
            WHERE t.club_id = %s AND t.series_id = %s AND t.league_id = %s
        """, (club_id, series_id, league_id))
        
        team_result = cursor.fetchone()
        
        if team_result:
            team_id, team_name = team_result
            
            if not dry_run:
                cursor.execute("""
                    UPDATE players SET team_id = %s WHERE id = %s
                """, (team_id, player_id))
                
                fixed_count += 1
                
                if fixed_count <= 10:  # Log first 10 for verification
                    log(f"   ✅ Fixed: {first_name} {last_name} → {team_name}")
            else:
                log(f"   [DRY RUN] Would fix: {first_name} {last_name} → {team_name}")
                fixed_count += 1
    
    if not dry_run:
        conn.commit()
    
    log(f"✅ Fixed {fixed_count} player team assignments")
    return fixed_count


def validate_fix_results(conn):
    """Validate that the fixes worked correctly"""
    log("🔍 Validating fix results...")
    
    cursor = conn.cursor()
    
    # Check remaining series conflicts
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT s1.name, s2.name
            FROM series s1
            JOIN series s2 ON s1.id != s2.id
            WHERE (s1.name LIKE 'Series %' AND s2.name NOT LIKE 'Series %' AND s2.name LIKE '%' || REPLACE(s1.name, 'Series ', ''))
               OR (s2.name LIKE 'Series %' AND s1.name NOT LIKE 'Series %' AND s1.name LIKE '%' || REPLACE(s2.name, 'Series ', ''))
        ) AS conflicts
    """)
    
    remaining_conflicts = cursor.fetchone()[0]
    log(f"📊 Remaining series conflicts: {remaining_conflicts}")
    
    # Check players with NULL team_id
    cursor.execute("SELECT COUNT(*) FROM players WHERE team_id IS NULL")
    null_team_players = cursor.fetchone()[0]
    log(f"📊 Players with NULL team_id: {null_team_players}")
    
    # Check total series count
    cursor.execute("SELECT COUNT(*) FROM series")
    total_series = cursor.fetchone()[0]
    log(f"📊 Total series: {total_series}")
    
    # Check Ross's status specifically
    cursor.execute("""
        SELECT p.tenniscores_player_id, p.team_id, t.team_name, s.name as series_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN series s ON p.series_id = s.id
        WHERE p.tenniscores_player_id = 'nndz-WlNhd3hMYi9nQT09'
    """)
    
    ross_status = cursor.fetchone()
    if ross_status:
        log(f"📊 Ross's status: Team ID {ross_status[1]}, Team: {ross_status[2]}, Series: {ross_status[3]}")
    
    return {
        'remaining_conflicts': remaining_conflicts,
        'null_team_players': null_team_players,
        'total_series': total_series,
        'ross_fixed': ross_status and ross_status[1] is not None
    }


def main():
    parser = argparse.ArgumentParser(description="Fix series conflicts and team assignments")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()
    
    log("🚀 Starting series conflicts and team assignments fix...")
    log(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE UPDATE'}")
    
    try:
        with get_db() as conn:
            # Step 1: Create series mapping infrastructure
            create_series_mapping_table(conn)
            populate_series_mappings(conn)
            
            # Step 2: Analyze conflicts
            conflicts = analyze_series_conflicts(conn)
            
            # Step 3: Consolidate conflicts
            if conflicts:
                consolidated_count = consolidate_series_conflicts(conn, conflicts, args.dry_run)
            else:
                log("✅ No series conflicts found")
                consolidated_count = 0
            
            # Step 4: Fix player team assignments
            fixed_players = fix_player_team_assignments(conn, args.dry_run)
            
            # Step 5: Validate results
            if not args.dry_run:
                results = validate_fix_results(conn)
                
                log("\n🎯 FINAL RESULTS:")
                log(f"   Series consolidated: {consolidated_count}")
                log(f"   Players fixed: {fixed_players}")
                log(f"   Remaining conflicts: {results['remaining_conflicts']}")
                log(f"   Remaining NULL team players: {results['null_team_players']}")
                log(f"   Ross's status: {'✅ FIXED' if results['ross_fixed'] else '❌ STILL BROKEN'}")
                
                if results['remaining_conflicts'] == 0 and results['null_team_players'] < 100:
                    log("✅ Fix completed successfully!")
                else:
                    log("⚠️  Some issues remain - may need additional investigation")
            else:
                log("\n🎯 DRY RUN COMPLETE - No changes made")
                log("   Run without --dry-run to apply fixes")
    
    except Exception as e:
        log(f"❌ Error: {str(e)}", "ERROR")
        raise


if __name__ == "__main__":
    main() 