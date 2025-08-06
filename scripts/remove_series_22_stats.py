#!/usr/bin/env python3
"""
Remove Series 22 (Chicago 22) Statistics from Local Database
============================================================

This script removes ONLY the series_stats data for Series 22 (Chicago 22)
while keeping all teams, players, and other data intact.

This is useful for testing purposes when you want to remove the standings
and statistics but keep the underlying team and player data.

Usage:
    python3 scripts/remove_series_22_stats.py [--dry-run] [--force]
"""

import argparse
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one


def get_series_22_stats():
    """Get all Series 22 statistics from series_stats table"""
    # Get stats by series name
    stats_query = """
        SELECT id, team, points, matches_won, matches_lost, matches_tied,
               lines_won, lines_lost, sets_won, sets_lost, games_won, games_lost
        FROM series_stats 
        WHERE series = 'Chicago 22'
        ORDER BY points DESC, team ASC
    """
    stats = execute_query(stats_query)
    return stats


def delete_series_22_stats():
    """Delete Series 22 statistics from series_stats table"""
    try:
        # Delete by series name
        delete_query = """
            DELETE FROM series_stats 
            WHERE series = 'Chicago 22'
        """
        result = execute_query(delete_query)
        
        # Get the number of deleted rows
        deleted_count = result.rowcount if hasattr(result, 'rowcount') else 0
        
        print(f"✅ Successfully deleted {deleted_count} Series 22 statistics records")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting Series 22 statistics: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Remove Series 22 statistics from series_stats table")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without executing")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    print("🔍 Analyzing Series 22 statistics in series_stats table...")
    
    # Get current stats
    stats = get_series_22_stats()
    
    if not stats:
        print("❌ No Series 22 statistics found in series_stats table")
        return
    
    # Display summary
    print(f"\n📊 Series 22 Statistics Summary:")
    print(f"   Total records: {len(stats)}")
    print(f"   Teams with stats: {len(set(stat['team'] for stat in stats))}")
    
    print(f"\n📈 Current Series 22 Standings (to be deleted):")
    for i, stat in enumerate(stats, 1):
        print(f"   {i:2d}. {stat['team']:25s} - {stat['points']:3d} points ({stat['matches_won']:2d}W/{stat['matches_lost']:2d}L)")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No data will be deleted")
        return
    
    # Confirm deletion
    if not args.force:
        print(f"\n⚠️  WARNING: This will permanently delete {len(stats)} Series 22 statistics records!")
        print("   Teams and players will remain intact - only standings/statistics will be removed.")
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Operation cancelled")
            return
    
    # Delete stats
    print("\n🗑️  Deleting Series 22 statistics...")
    success = delete_series_22_stats()
    
    if success:
        print("\n✅ Series 22 statistics successfully removed from series_stats table")
        print("   Teams and players remain intact")
        print("\n🔄 To restore these statistics later, run the ETL import process again")
    else:
        print("\n❌ Failed to delete Series 22 statistics")


if __name__ == "__main__":
    main() 