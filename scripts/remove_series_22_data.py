#!/usr/bin/env python3
"""
Remove Series 22 (Chicago 22) Data from Local Database
======================================================

This script safely removes all Series 22 (Chicago 22) data from the local database
for testing purposes. It removes data from multiple tables that reference Series 22.

Tables affected:
- series_stats (team statistics for Series 22)
- match_scores (match results for Series 22 teams)
- schedule (scheduled matches for Series 22 teams)
- teams (team records for Series 22)

Safety features:
- Shows what will be deleted before executing
- Creates backup of affected data
- Confirms before deletion
- Provides rollback instructions

Usage:
    python scripts/remove_series_22_data.py [--dry-run] [--force]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one


def get_series_22_id():
    """Get the database ID for Series 22 (Chicago 22)"""
    query = "SELECT id FROM series WHERE name = 'Chicago 22'"
    result = execute_query_one(query)
    if result:
        return result['id']
    return None


def get_series_22_teams():
    """Get all teams associated with Series 22"""
    series_id = get_series_22_id()
    if not series_id:
        print("❌ Series 22 (Chicago 22) not found in database")
        return []
    
    query = """
        SELECT id, team_name, club_id, league_id 
        FROM teams 
        WHERE series_id = %s
    """
    teams = execute_query(query, [series_id])
    return teams


def get_series_22_data_summary():
    """Get summary of all Series 22 data that would be affected"""
    series_id = get_series_22_id()
    if not series_id:
        return None
    
    summary = {
        'series_id': series_id,
        'series_name': 'Chicago 22',
        'teams': [],
        'series_stats': [],
        'match_scores': [],
        'schedule': []
    }
    
    # Get teams
    teams = get_series_22_teams()
    summary['teams'] = teams
    
    # Get series stats
    if teams:
        team_ids = [team['id'] for team in teams]
        team_names = [team['team_name'] for team in teams]
        
        # Series stats by team_id
        if team_ids:
            stats_query = """
                SELECT id, team, points, matches_won, matches_lost 
                FROM series_stats 
                WHERE team_id = ANY(%s)
            """
            summary['series_stats'] = execute_query(stats_query, [team_ids])
        
        # Series stats by series name (fallback)
        stats_query = """
            SELECT id, team, points, matches_won, matches_lost 
            FROM series_stats 
            WHERE series = 'Chicago 22'
        """
        summary['series_stats'].extend(execute_query(stats_query))
        
        # Match scores
        if team_ids:
            matches_query = """
                SELECT id, match_date, home_team, away_team, winner
                FROM match_scores 
                WHERE home_team_id = ANY(%s) OR away_team_id = ANY(%s)
            """
            summary['match_scores'] = execute_query(matches_query, [team_ids, team_ids])
        
        # Schedule
        if team_ids:
            schedule_query = """
                SELECT id, match_date, home_team, away_team, location
                FROM schedule 
                WHERE home_team_id = ANY(%s) OR away_team_id = ANY(%s)
            """
            summary['schedule'] = execute_query(schedule_query, [team_ids, team_ids])
    
    return summary


def create_backup(summary):
    """Create backup of Series 22 data"""
    if not summary:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    backup_file = backup_dir / f"series_22_backup_{timestamp}.json"
    
    # Create a clean backup data structure without circular references
    backup_data = {
        'timestamp': timestamp,
        'series_id': summary['series_id'],
        'series_name': summary['series_name'],
        'teams_count': len(summary['teams']),
        'series_stats_count': len(summary['series_stats']),
        'match_scores_count': len(summary['match_scores']),
        'schedule_count': len(summary['schedule']),
        'teams': [
            {
                'id': team['id'],
                'team_name': team['team_name'],
                'club_id': team['club_id'],
                'league_id': team['league_id']
            }
            for team in summary['teams']
        ],
        'series_stats': [
            {
                'id': stat['id'],
                'team': stat['team'],
                'points': stat['points'],
                'matches_won': stat['matches_won'],
                'matches_lost': stat['matches_lost']
            }
            for stat in summary['series_stats']
        ],
        'match_scores': [
            {
                'id': match['id'],
                'match_date': match['match_date'].isoformat() if match['match_date'] else None,
                'home_team': match['home_team'],
                'away_team': match['away_team'],
                'winner': match['winner']
            }
            for match in summary['match_scores']
        ],
        'schedule': [
            {
                'id': schedule['id'],
                'match_date': schedule['match_date'].isoformat() if schedule['match_date'] else None,
                'home_team': schedule['home_team'],
                'away_team': schedule['away_team'],
                'location': schedule['location']
            }
            for schedule in summary['schedule']
        ],
        'rollback_instructions': """
To restore Series 22 data:
1. Run the ETL import process again
2. Or manually restore from this backup file
        """
    }
    
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    print(f"💾 Backup created: {backup_file}")
    return backup_file


def delete_series_22_data(summary):
    """Delete Series 22 data from database"""
    if not summary:
        print("❌ No Series 22 data found to delete")
        return False
    
    series_id = summary['series_id']
    team_ids = [team['id'] for team in summary['teams']]
    
    deleted_counts = {}
    
    try:
        # Delete schedule entries
        if team_ids:
            schedule_query = """
                DELETE FROM schedule 
                WHERE home_team_id = ANY(%s) OR away_team_id = ANY(%s)
            """
            result = execute_query(schedule_query, [team_ids, team_ids])
            deleted_counts['schedule'] = result.rowcount if hasattr(result, 'rowcount') else 0
        
        # Delete match scores
        if team_ids:
            matches_query = """
                DELETE FROM match_scores 
                WHERE home_team_id = ANY(%s) OR away_team_id = ANY(%s)
            """
            result = execute_query(matches_query, [team_ids, team_ids])
            deleted_counts['match_scores'] = result.rowcount if hasattr(result, 'rowcount') else 0
        
        # Delete series stats
        if team_ids:
            stats_query = """
                DELETE FROM series_stats 
                WHERE team_id = ANY(%s)
            """
            result = execute_query(stats_query, [team_ids])
            deleted_counts['series_stats'] = result.rowcount if hasattr(result, 'rowcount') else 0
        
        # Also delete by series name (fallback)
        stats_query = """
            DELETE FROM series_stats 
            WHERE series = 'Chicago 22'
        """
        result = execute_query(stats_query)
        deleted_counts['series_stats_by_name'] = result.rowcount if hasattr(result, 'rowcount') else 0
        
        # Handle players associated with Series 22 teams
        if team_ids:
            # First, get count of affected players
            players_query = """
                SELECT COUNT(*) as count FROM players WHERE team_id = ANY(%s)
            """
            player_count = execute_query_one(players_query, [team_ids])
            deleted_counts['players_affected'] = player_count['count'] if player_count else 0
            
            # Set team_id to NULL for players (safer than deleting)
            players_update_query = """
                UPDATE players SET team_id = NULL WHERE team_id = ANY(%s)
            """
            result = execute_query(players_update_query, [team_ids])
            deleted_counts['players_updated'] = result.rowcount if hasattr(result, 'rowcount') else 0
        
        # Delete teams (now safe since no players reference them)
        if team_ids:
            teams_query = """
                DELETE FROM teams 
                WHERE id = ANY(%s)
            """
            result = execute_query(teams_query, [team_ids])
            deleted_counts['teams'] = result.rowcount if hasattr(result, 'rowcount') else 0
        
        print("✅ Series 22 data deleted successfully")
        print(f"📊 Deleted counts: {deleted_counts}")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting Series 22 data: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Remove Series 22 data from local database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without executing")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    print("🔍 Analyzing Series 22 data in local database...")
    
    # Get data summary
    summary = get_series_22_data_summary()
    
    if not summary:
        print("❌ No Series 22 data found in database")
        return
    
    # Display summary
    print(f"\n📊 Series 22 Data Summary:")
    print(f"   Series ID: {summary['series_id']}")
    print(f"   Series Name: {summary['series_name']}")
    print(f"   Teams: {len(summary['teams'])}")
    print(f"   Series Stats: {len(summary['series_stats'])}")
    print(f"   Match Scores: {len(summary['match_scores'])}")
    print(f"   Schedule: {len(summary['schedule'])}")
    
    if summary['teams']:
        print(f"\n🏆 Teams to be deleted:")
        for team in summary['teams']:
            print(f"   - {team['team_name']} (ID: {team['id']})")
    
    if summary['series_stats']:
        print(f"\n📈 Series Stats to be deleted:")
        for stat in summary['series_stats'][:5]:  # Show first 5
            print(f"   - {stat['team']}: {stat['points']} points ({stat['matches_won']}W/{stat['matches_lost']}L)")
        if len(summary['series_stats']) > 5:
            print(f"   ... and {len(summary['series_stats']) - 5} more")
    
    if summary['match_scores']:
        print(f"\n🎾 Match Scores to be deleted:")
        for match in summary['match_scores'][:5]:  # Show first 5
            print(f"   - {match['match_date']}: {match['home_team']} vs {match['away_team']} (Winner: {match['winner']})")
        if len(summary['match_scores']) > 5:
            print(f"   ... and {len(summary['match_scores']) - 5} more")
    
    if summary['schedule']:
        print(f"\n📅 Schedule entries to be deleted:")
        for schedule in summary['schedule'][:5]:  # Show first 5
            print(f"   - {schedule['match_date']}: {schedule['home_team']} vs {schedule['away_team']} at {schedule['location']}")
        if len(summary['schedule']) > 5:
            print(f"   ... and {len(summary['schedule']) - 5} more")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No data will be deleted")
        return
    
    # Create backup
    backup_file = create_backup(summary)
    
    # Confirm deletion
    if not args.force:
        print(f"\n⚠️  WARNING: This will permanently delete all Series 22 data!")
        print(f"💾 Backup created at: {backup_file}")
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Operation cancelled")
            return
    
    # Delete data
    print("\n🗑️  Deleting Series 22 data...")
    success = delete_series_22_data(summary)
    
    if success:
        print("\n✅ Series 22 data successfully removed from local database")
        print(f"💾 Backup available at: {backup_file}")
        print("\n🔄 To restore this data later, run the ETL import process again")
    else:
        print("\n❌ Failed to delete Series 22 data")


if __name__ == "__main__":
    main() 