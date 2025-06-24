#!/usr/bin/env python3
"""
Rally Reference Data Cleanup Script

This script safely removes test reference data (leagues, clubs, series, teams)
from the database while preserving production data. It handles foreign key 
constraints by cleaning up data in the correct order.

Usage:
    python scripts/cleanup_reference_data.py [--dry-run] [--verbose]

Options:
    --dry-run       Show what would be deleted without actually deleting
    --verbose       Show detailed progress information
"""

import argparse
import sys
import os

# Add parent directory to path to import database_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update


def identify_test_reference_patterns():
    """Define patterns that identify test reference data"""
    return {
        'league_patterns': [
            'FAKE_LEAGUE',
            'TEST_LEAGUE',
            '%test%',
            '%fake%',
        ],
        'club_patterns': [
            '%Test Club%',
            '%Fake Club%',
            '%test%',
            '%fake%',
        ],
        'series_patterns': [
            '%Test Series%',
            '%Fake Series%',
            '%test%',
            '%fake%',
        ]
    }


def get_test_leagues(dry_run=False, verbose=False):
    """Get test leagues that should be cleaned up"""
    patterns = identify_test_reference_patterns()
    
    conditions = ' OR '.join([f"league_id ILIKE '{pattern}' OR league_name ILIKE '{pattern}'" 
                             for pattern in patterns['league_patterns']])
    
    query = f"""
        SELECT id, league_id, league_name
        FROM leagues 
        WHERE {conditions}
        ORDER BY id
    """
    
    try:
        test_leagues = execute_query(query)
        
        if verbose and test_leagues:
            print(f"🏆 Found {len(test_leagues)} test leagues:")
            for league in test_leagues:
                print(f"   ID {league['id']}: {league['league_id']} - {league['league_name']}")
        
        return test_leagues
        
    except Exception as e:
        print(f"❌ Error identifying test leagues: {e}")
        return []


def get_test_clubs(dry_run=False, verbose=False):
    """Get test clubs that should be cleaned up"""
    patterns = identify_test_reference_patterns()
    
    conditions = ' OR '.join([f"name ILIKE '{pattern}'" for pattern in patterns['club_patterns']])
    
    query = f"""
        SELECT id, name
        FROM clubs 
        WHERE {conditions}
        ORDER BY id
    """
    
    try:
        test_clubs = execute_query(query)
        
        if verbose and test_clubs:
            print(f"🏛️ Found {len(test_clubs)} test clubs:")
            for club in test_clubs:
                print(f"   ID {club['id']}: {club['name']}")
        
        return test_clubs
        
    except Exception as e:
        print(f"❌ Error identifying test clubs: {e}")
        return []


def get_test_series(dry_run=False, verbose=False):
    """Get test series that should be cleaned up"""
    patterns = identify_test_reference_patterns()
    
    conditions = ' OR '.join([f"name ILIKE '{pattern}'" for pattern in patterns['series_patterns']])
    
    query = f"""
        SELECT id, name
        FROM series 
        WHERE {conditions}
        ORDER BY id
    """
    
    try:
        test_series = execute_query(query)
        
        if verbose and test_series:
            print(f"📊 Found {len(test_series)} test series:")
            for series in test_series:
                print(f"   ID {series['id']}: {series['name']}")
        
        return test_series
        
    except Exception as e:
        print(f"❌ Error identifying test series: {e}")
        return []


def cleanup_dependent_data(test_leagues, test_clubs, test_series, dry_run=False, verbose=False):
    """Clean up data that depends on test reference data"""
    total_cleaned = 0
    
    if not any([test_leagues, test_clubs, test_series]):
        return 0
    
    # Get IDs for deletion
    league_ids = [league['id'] for league in test_leagues]
    club_ids = [club['id'] for club in test_clubs]
    series_ids = [series['id'] for series in test_series]
    
    # Clean up in order of dependencies (most dependent first)
    cleanup_queries = []
    
    # 1. Players that reference test data
    if league_ids:
        cleanup_queries.append((
            "Players (by league)",
            f"DELETE FROM players WHERE league_id = ANY(%s)",
            [league_ids]
        ))
    if club_ids:
        cleanup_queries.append((
            "Players (by club)", 
            f"DELETE FROM players WHERE club_id = ANY(%s)",
            [club_ids]
        ))
    if series_ids:
        cleanup_queries.append((
            "Players (by series)",
            f"DELETE FROM players WHERE series_id = ANY(%s)", 
            [series_ids]
        ))
    
    # 2. Teams that reference test data
    if league_ids:
        cleanup_queries.append((
            "Teams (by league)",
            f"DELETE FROM teams WHERE league_id = ANY(%s)",
            [league_ids]
        ))
    if club_ids:
        cleanup_queries.append((
            "Teams (by club)",
            f"DELETE FROM teams WHERE club_id = ANY(%s)",
            [club_ids]
        ))
    if series_ids:
        cleanup_queries.append((
            "Teams (by series)",
            f"DELETE FROM teams WHERE series_id = ANY(%s)",
            [series_ids]
        ))
    
    # 3. Schedule entries
    if league_ids:
        cleanup_queries.append((
            "Schedule entries",
            f"DELETE FROM schedule WHERE league_id = ANY(%s)",
            [league_ids]
        ))
    
    # 4. Match scores
    if league_ids:
        cleanup_queries.append((
            "Match scores",
            f"DELETE FROM match_scores WHERE league_id = ANY(%s)",
            [league_ids]
        ))
    
    # 5. Series stats
    if league_ids:
        cleanup_queries.append((
            "Series stats",
            f"DELETE FROM series_stats WHERE league_id = ANY(%s)",
            [league_ids]
        ))
    
    # Execute cleanup queries
    for description, query, params in cleanup_queries:
        try:
            if verbose:
                print(f"🔧 Cleaning {description}...")
            
            if not dry_run:
                result = execute_update(query, params)
                count = getattr(result, 'rowcount', 0) if result else 0
                total_cleaned += count
                if verbose and count > 0:
                    print(f"   ✅ Deleted {count} {description.lower()}")
            else:
                # For dry run, count what would be deleted
                count_query = query.replace("DELETE FROM", "SELECT COUNT(*) as count FROM")
                count_result = execute_query(count_query, params)
                count = count_result[0]['count'] if count_result else 0
                total_cleaned += count
                if verbose:
                    print(f"   🔍 Would delete {count} {description.lower()}")
                    
        except Exception as e:
            print(f"❌ Error cleaning {description}: {e}")
    
    return total_cleaned


def cleanup_test_series(test_series, dry_run=False, verbose=False):
    """Clean up test series"""
    if not test_series:
        return 0
        
    series_ids = [series['id'] for series in test_series]
    count = len(series_ids)
    
    if verbose:
        print(f"📊 Cleaning {count} test series...")
        
    if not dry_run and count > 0:
        delete_query = "DELETE FROM series WHERE id = ANY(%s)"
        execute_update(delete_query, [series_ids])
        
    return count


def cleanup_test_clubs(test_clubs, dry_run=False, verbose=False):
    """Clean up test clubs"""
    if not test_clubs:
        return 0
        
    club_ids = [club['id'] for club in test_clubs]
    count = len(club_ids)
    
    if verbose:
        print(f"🏛️ Cleaning {count} test clubs...")
        
    if not dry_run and count > 0:
        delete_query = "DELETE FROM clubs WHERE id = ANY(%s)"
        execute_update(delete_query, [club_ids])
        
    return count


def cleanup_test_leagues(test_leagues, dry_run=False, verbose=False):
    """Clean up test leagues"""
    if not test_leagues:
        return 0
        
    league_ids = [league['id'] for league in test_leagues]
    count = len(league_ids)
    
    if verbose:
        print(f"🏆 Cleaning {count} test leagues...")
        
    if not dry_run and count > 0:
        delete_query = "DELETE FROM leagues WHERE id = ANY(%s)"
        execute_update(delete_query, [league_ids])
        
    return count


def get_reference_stats():
    """Get current reference data statistics"""
    stats = {}
    
    tables = {
        'leagues': 'SELECT COUNT(*) as count FROM leagues',
        'clubs': 'SELECT COUNT(*) as count FROM clubs',
        'series': 'SELECT COUNT(*) as count FROM series',
        'teams': 'SELECT COUNT(*) as count FROM teams',
        'players': 'SELECT COUNT(*) as count FROM players',
    }
    
    for table, query in tables.items():
        try:
            result = execute_query(query)
            stats[table] = result[0]['count'] if result else 0
        except Exception:
            stats[table] = 'Error'
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Clean up Rally test reference data')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed progress information')
    
    args = parser.parse_args()
    
    print("🧹 Rally Reference Data Cleanup")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be deleted")
        print()
    
    # Show initial stats
    if args.verbose:
        print("📊 Current reference data statistics:")
        initial_stats = get_reference_stats()
        for table, count in initial_stats.items():
            print(f"   {table}: {count}")
        print()
    
    # Identify test reference data
    print("🔍 Identifying test reference data...")
    test_leagues = get_test_leagues(args.dry_run, args.verbose)
    test_clubs = get_test_clubs(args.dry_run, args.verbose)
    test_series = get_test_series(args.dry_run, args.verbose)
    
    total_test_items = len(test_leagues) + len(test_clubs) + len(test_series)
    
    if total_test_items == 0:
        print("✅ No test reference data found to clean up!")
        return
    
    print(f"\n🎯 Found {total_test_items} test reference items to process")
    print(f"   Leagues: {len(test_leagues)}")
    print(f"   Clubs: {len(test_clubs)}")
    print(f"   Series: {len(test_series)}")
    
    if not args.dry_run:
        # Confirm deletion
        response = input(f"\n⚠️  About to delete {total_test_items} reference items and dependent data. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cleanup cancelled")
            return
    
    print("\n🗂️  Cleaning up in proper order to respect foreign keys...")
    
    # Clean up in proper order
    total_cleaned = 0
    
    # 1. Clean dependent data first (players, teams, etc.)
    print("\n🔧 Step 1: Cleaning dependent data...")
    dependent_count = cleanup_dependent_data(test_leagues, test_clubs, test_series, args.dry_run, args.verbose)
    total_cleaned += dependent_count
    
    # 2. Clean series (may be referenced by teams)
    print("\n🔧 Step 2: Cleaning test series...")
    series_count = cleanup_test_series(test_series, args.dry_run, args.verbose)
    total_cleaned += series_count
    
    # 3. Clean clubs 
    print("\n🔧 Step 3: Cleaning test clubs...")
    clubs_count = cleanup_test_clubs(test_clubs, args.dry_run, args.verbose)
    total_cleaned += clubs_count
    
    # 4. Clean leagues (top level)
    print("\n🔧 Step 4: Cleaning test leagues...")
    leagues_count = cleanup_test_leagues(test_leagues, args.dry_run, args.verbose)
    total_cleaned += leagues_count
    
    # Show final stats
    print(f"\n📈 Summary:")
    print(f"   Reference items processed: {total_test_items}")
    print(f"   Total records affected: {total_cleaned}")
    
    if not args.dry_run:
        print("   Status: ✅ Reference data cleanup completed successfully!")
        
        if args.verbose:
            print("\n📊 Final reference data statistics:")
            final_stats = get_reference_stats()
            for table, count in final_stats.items():
                print(f"   {table}: {count}")
    else:
        print("   Status: 🔍 Dry run completed (no data deleted)")
        print("\n💡 Run without --dry-run to actually delete the data")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1) 