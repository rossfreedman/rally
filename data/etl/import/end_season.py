#!/usr/bin/env python3
"""
End Season Script for Rally App

Removes season-specific data for a single league while preserving:
- leagues, users, user_player_associations, players

Usage: python data/etl/import/end_season.py <LEAGUE_KEY>
Example: python data/etl/import/end_season.py CNSWPL
"""

import argparse
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Add the project root to Python path to import database_config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from database_config import get_db_url, get_database_mode, is_local_development


def validate_league_key(league_key):
    """Validate the league key to prevent accidental deletion."""
    if not league_key or not isinstance(league_key, str):
        return False, "League key must be a non-empty string"
    
    league_key = league_key.strip()
    if not league_key:
        return False, "League key cannot be empty"
    
    # Prevent dangerous operations on production-like environments
    dangerous_patterns = ['prod', 'production', 'live', 'main']
    if any(pattern in league_key.lower() for pattern in dangerous_patterns):
        return False, f"League key '{league_key}' contains potentially dangerous patterns"
    
    return True, league_key

def confirm_deletion(league_key, league_id, data_summary):
    """Ask for confirmation before deleting data."""
    print(f"\n⚠️  WARNING: You are about to delete ALL season data for league '{league_key}' (ID: {league_id})")
    print("This will permanently remove:")
    print("  - All schedules")
    print("  - All match scores")
    print("  - All series stats")
    print("  - All player availability")
    print("  - All player season tracking")
    print("  - All teams")
    print("  - All series")
    print("  - All clubs")
    print("  - All players")
    print("\nThe following data will be PRESERVED:")
    print("  - League definition")
    print("  - User accounts")
    print("  - User-player associations")
    
    print(f"\n📊 Data to be deleted:")
    for table, count in data_summary.items():
        print(f"  {table}: {count:,} records")
    
    print(f"\nTotal records to be deleted: {sum(data_summary.values()):,}")
    
    response = input(f"\nAre you sure you want to continue? Type 'YES' to confirm: ")
    if response != "YES":
        print("Operation cancelled.")
        return False
    
    # Double confirmation for large datasets
    if sum(data_summary.values()) > 1000:
        response2 = input(f"This will delete {sum(data_summary.values()):,} records. Type 'CONFIRM' to proceed: ")
        if response2 != "CONFIRM":
            print("Operation cancelled.")
            return False
    
    return True

def get_data_summary(cur, league_id):
    """Get a summary of data that will be deleted."""
    summary = {}
    
    # Count records in each table
    tables_to_check = [
        ("schedule", "SELECT COUNT(*) FROM schedule WHERE league_id = %s"),
        ("match_scores", "SELECT COUNT(*) FROM match_scores WHERE home_team_id IN (SELECT id FROM teams WHERE league_id = %s) OR away_team_id IN (SELECT id FROM teams WHERE league_id = %s)"),
        ("series_stats", "SELECT COUNT(*) FROM series_stats WHERE league_id = %s OR team_id IN (SELECT id FROM teams WHERE league_id = %s)"),
        ("player_availability", "SELECT COUNT(*) FROM player_availability WHERE player_id IN (SELECT id FROM players WHERE league_id = %s)"),
        ("player_season_tracking", "SELECT COUNT(*) FROM player_season_tracking WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)"),
        ("teams", "SELECT COUNT(*) FROM teams WHERE league_id = %s"),
        ("series", "SELECT COUNT(*) FROM series WHERE league_id = %s"),
        ("clubs", "SELECT COUNT(*) FROM clubs WHERE id IN (SELECT DISTINCT club_id FROM teams WHERE league_id = %s)"),
        ("players", "SELECT COUNT(*) FROM players WHERE league_id = %s")
    ]
    
    for table_name, query in tables_to_check:
        try:
            if "teams WHERE league_id" in query:
                # Handle queries that reference teams table
                cur.execute(query, (league_id, league_id))
            else:
                cur.execute(query, (league_id,))
            count = cur.fetchone()[0]
            summary[table_name] = count
        except Exception as e:
            print(f"  Warning: Could not count {table_name}: {e}")
            summary[table_name] = 0
    
    return summary


def get_league_id(cur, league_key):
    """Get league ID from database."""
    cur.execute(
        "SELECT id FROM leagues WHERE league_id = %s OR league_name = %s LIMIT 1",
        (league_key, league_key)
    )
    result = cur.fetchone()
    if not result:
        print(f"ERROR: League '{league_key}' not found in database")
        sys.exit(1)
    return result[0]


def delete_league_data(cur, league_id):
    """Delete ALL season-specific data for a league including clubs and series."""
    total_deleted = 0
    
    # Step 1: Delete data that references teams (but not teams themselves)
    try:
        # Delete match_scores via team references
        cur.execute("""
            DELETE FROM match_scores 
            WHERE home_team_id IN (SELECT id FROM teams WHERE league_id = %s)
               OR away_team_id IN (SELECT id FROM teams WHERE league_id = %s)
        """, (league_id, league_id))
        deleted_count = cur.rowcount
        print(f"  match_scores: {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  match_scores: ERROR - {e}")
        raise
    
    try:
        # Delete schedule records first (they reference teams)
        # Delete by league_id first
        cur.execute("DELETE FROM schedule WHERE league_id = %s", (league_id,))
        deleted_by_league = cur.rowcount
        
        # Also delete any schedule records that reference teams from this league
        # (in case league_id is NULL but team references exist)
        cur.execute("""
            DELETE FROM schedule 
            WHERE home_team_id IN (SELECT id FROM teams WHERE league_id = %s)
               OR away_team_id IN (SELECT id FROM teams WHERE league_id = %s)
        """, (league_id, league_id))
        deleted_by_team_ref = cur.rowcount
        
        total_schedule_deleted = deleted_by_league + deleted_by_team_ref
        print(f"  schedule: {total_schedule_deleted} rows deleted")
        print(f"    - By league_id: {deleted_by_league}")
        print(f"    - By team references: {deleted_by_team_ref}")
        total_deleted += total_schedule_deleted
    except Exception as e:
        print(f"  schedule: ERROR - {e}")
        raise
    
    try:
        # Delete series_stats via team references
        cur.execute("""
            DELETE FROM series_stats 
            WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)
        """, (league_id,))
        deleted_count = cur.rowcount
        print(f"  series_stats (by team): {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  series_stats: ERROR - {e}")
        raise
    
    try:
        # Delete remaining series_stats by league_id (for series-level stats)
        cur.execute("DELETE FROM series_stats WHERE league_id = %s", (league_id,))
        deleted_count = cur.rowcount
        print(f"  series_stats (by league): {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  series_stats (by league): ERROR - {e}")
        raise
    
    try:
        # Delete player_availability via player references (active records)
        cur.execute("""
            DELETE FROM player_availability 
            WHERE player_id IN (SELECT id FROM players WHERE league_id = %s)
        """, (league_id,))
        deleted_active = cur.rowcount
        
        # ENHANCED: Also delete orphaned availability records via series_id
        # This catches records where player_id no longer exists but series_id does
        cur.execute("""
            DELETE FROM player_availability 
            WHERE series_id IN (SELECT id FROM series WHERE league_id = %s)
        """, (league_id,))
        deleted_by_series = cur.rowcount
        
        # ENHANCED: Clean up any remaining orphaned records for this league
        # Find and delete records that reference non-existent players
        cur.execute("""
            DELETE FROM player_availability pa
            USING series s
            WHERE pa.series_id = s.id 
            AND s.league_id = %s
            AND pa.player_id NOT IN (SELECT id FROM players WHERE id IS NOT NULL)
        """, (league_id,))
        deleted_orphaned = cur.rowcount
        
        total_availability_deleted = deleted_active + deleted_by_series + deleted_orphaned
        print(f"  player_availability: {total_availability_deleted} rows deleted")
        print(f"    - Active records (via player_id): {deleted_active}")
        print(f"    - Via series_id: {deleted_by_series}")  
        print(f"    - Orphaned records: {deleted_orphaned}")
        total_deleted += total_availability_deleted
    except Exception as e:
        print(f"  player_availability: ERROR - {e}")
        raise
    
    try:
        # Delete player_history via player references
        cur.execute("""
            DELETE FROM player_history 
            WHERE player_id IN (SELECT id FROM players WHERE league_id = %s)
        """, (league_id,))
        deleted_count = cur.rowcount
        print(f"  player_history: {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  player_history: ERROR - {e}")
        raise
    
    try:
        # Delete player_season_tracking via team references
        cur.execute("""
            DELETE FROM player_season_tracking 
            WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)
        """, (league_id,))
        deleted_count = cur.rowcount
        print(f"  player_season_tracking: {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  player_season_tracking: ERROR - {e}")
        raise
    
    # Step 2: Clear all foreign key references to teams
    try:
        print("  Clearing team_id references...")
        
        # First clear team_id in players table
        cur.execute("UPDATE players SET team_id = NULL WHERE league_id = %s AND team_id IS NOT NULL", (league_id,))
        players_updated = cur.rowcount
        if players_updated > 0:
            print(f"    Players updated: {players_updated} team_id references cleared")
        
        # Tables that can have NULL team_id (set to NULL)
        cur.execute("UPDATE lineup_escrow SET initiator_team_id = NULL WHERE initiator_team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_id,))
        cur.execute("UPDATE lineup_escrow SET recipient_team_id = NULL WHERE recipient_team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_id,))
        cur.execute("UPDATE user_instructions SET team_id = NULL WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_id,))
        cur.execute("UPDATE users SET team_id = NULL WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_id,))
        cur.execute("UPDATE user_contexts SET team_id = NULL WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_id,))
        cur.execute("UPDATE polls SET team_id = NULL WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_id,))
        
        # Tables that cannot have NULL team_id (delete records)
        cur.execute("DELETE FROM captain_messages WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_id,))
        cur.execute("DELETE FROM saved_lineups WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_id,))
        
        print(f"  All team_id references cleared")
    except Exception as e:
        print(f"  team_id references clear: ERROR - {e}")
        raise
    
    # Step 3: Delete teams (now safe since no references)
    try:
        cur.execute("DELETE FROM teams WHERE league_id = %s", (league_id,))
        deleted_count = cur.rowcount
        print(f"  teams: {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  teams: ERROR - {e}")
        raise
    
    # Step 4: Delete players (now safe since no teams reference them)
    try:
        cur.execute("DELETE FROM players WHERE league_id = %s", (league_id,))
        deleted_count = cur.rowcount
        print(f"  players: {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  players: ERROR - {e}")
        raise
    
    # Step 5: Clear series references in other tables
    try:
        print("  Clearing series_id references...")
        cur.execute("UPDATE user_contexts SET series_id = NULL WHERE series_id IN (SELECT id FROM series WHERE league_id = %s)", (league_id,))
        cur.execute("UPDATE user_instructions SET series_id = NULL WHERE series_id IN (SELECT id FROM series WHERE league_id = %s)", (league_id,))
        print(f"  All series_id references cleared")
    except Exception as e:
        print(f"  series_id references clear: ERROR - {e}")
        raise
    
    # Step 6: Delete series (now safe since no players reference them)
    try:
        cur.execute("DELETE FROM series WHERE league_id = %s", (league_id,))
        deleted_count = cur.rowcount
        print(f"  series: {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  series: ERROR - {e}")
        raise
    
    # Step 7: Clear club references in other tables
    try:
        print("  Clearing club_id references...")
        cur.execute("DELETE FROM club_leagues WHERE club_id IN (SELECT id FROM clubs WHERE league_id = %s)", (league_id,))
        cur.execute("UPDATE pickup_games SET club_id = NULL WHERE club_id IN (SELECT id FROM clubs WHERE league_id = %s)", (league_id,))
        print(f"  All club_id references cleared")
    except Exception as e:
        print(f"  club_id references clear: ERROR - {e}")
        raise
    
    # Step 8: Delete clubs (now safe since no players reference them)
    try:
        cur.execute("""
            DELETE FROM clubs 
            WHERE id IN (SELECT club_id FROM club_leagues WHERE league_id = %s)
        """, (league_id,))
        deleted_count = cur.rowcount
        print(f"  clubs: {deleted_count} rows deleted")
        total_deleted += deleted_count
    except Exception as e:
        print(f"  clubs: ERROR - {e}")
        raise
    
    return total_deleted


def validate_data_integrity_post_cleanup(cur, league_id, league_key):
    """Validate data integrity after cleanup to ensure no orphaned records remain"""
    print(f"\n🔍 VALIDATING DATA INTEGRITY POST-CLEANUP")
    print("=" * 50)
    
    issues_found = 0
    
    # Check for orphaned availability records
    cur.execute("""
        SELECT COUNT(*) FROM player_availability pa
        LEFT JOIN players p ON pa.player_id = p.id
        WHERE p.id IS NULL
    """)
    orphaned_availability = cur.fetchone()[0]
    
    if orphaned_availability > 0:
        print(f"❌ Found {orphaned_availability} orphaned availability records")
        issues_found += 1
    else:
        print(f"✅ No orphaned availability records")
    
    # Check for series_id mismatches in availability
    cur.execute("""
        SELECT COUNT(*) FROM player_availability pa
        JOIN players p ON pa.player_id = p.id
        WHERE pa.series_id != p.series_id
    """)
    series_mismatches = cur.fetchone()[0]
    
    if series_mismatches > 0:
        print(f"❌ Found {series_mismatches} availability records with series_id mismatches")
        issues_found += 1
    else:
        print(f"✅ No series_id mismatches in availability records")
    
    # Check for duplicate series names within the same league
    cur.execute("""
        SELECT name, COUNT(*) as count
        FROM series 
        WHERE league_id = %s
        GROUP BY name
        HAVING COUNT(*) > 1
    """, (league_id,))
    duplicate_series = cur.fetchall()
    
    if duplicate_series:
        print(f"❌ Found duplicate series names in league {league_key}:")
        for name, count in duplicate_series:
            print(f"   - '{name}': {count} instances")
        issues_found += len(duplicate_series)
    else:
        print(f"✅ No duplicate series names in league {league_key}")
    
    print(f"\n📊 DATA INTEGRITY SUMMARY:")
    print(f"   Issues found: {issues_found}")
    if issues_found == 0:
        print(f"   ✅ ALL DATA INTEGRITY CHECKS PASSED")
    else:
        print(f"   ⚠️ {issues_found} data integrity issues need attention")
    
    return issues_found == 0

def main():
    parser = argparse.ArgumentParser(description="End season for a league")
    parser.add_argument("league_key", help="League key (e.g., CNSWPL, APTA_CHICAGO)")
    parser.add_argument("--validate-integrity", action="store_true", help="Run data integrity validation after cleanup")
    args = parser.parse_args()
    
    league_key = args.league_key.strip()
    
    if not league_key:
        print("ERROR: League key cannot be empty")
        sys.exit(1)
    
    print(f"Ending season for league: {league_key}")
    
    # Show environment information
    print(f"Environment: {'Local Development' if is_local_development() else 'Railway/Production'}")
    print(f"Database Mode: {get_database_mode()}")
    print(f"Database URL: {get_db_url()}")
    print()
    
    # Database connection
    try:
        conn = psycopg2.connect(get_db_url())
        conn.autocommit = False
        cur = conn.cursor()
    except Exception as e:
        print(f"ERROR: Database connection failed: {e}")
        sys.exit(1)
    
    try:
        # Get league ID
        league_id = get_league_id(cur, league_key)
        print(f"Found league ID: {league_id}")
        
        # Validate league key
        is_valid, validation_message = validate_league_key(league_key)
        if not is_valid:
            print(f"ERROR: Invalid league key: {validation_message}")
            sys.exit(1)
        
        # Get data summary
        data_summary = get_data_summary(cur, league_id)
        
        # Confirm deletion
        if not confirm_deletion(league_key, league_id, data_summary):
            sys.exit(1)
        
        # Delete season data
        print("Deleting season-specific data...")
        total_deleted = delete_league_data(cur, league_id)
        
        # Commit transaction
        conn.commit()
        print(f"\nSeason ended successfully!")
        print(f"Total rows deleted: {total_deleted}")
        
        # ENHANCED: Run data integrity validation if requested
        if args.validate_integrity:
            integrity_passed = validate_data_integrity_post_cleanup(cur, league_id, league_key)
            if not integrity_passed:
                print(f"\n⚠️ Data integrity issues found after cleanup")
                print(f"Consider running cleanup scripts to resolve remaining issues")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: Failed to end season: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
