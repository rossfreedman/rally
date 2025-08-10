#!/usr/bin/env python3
"""
Delete All CNSWPL Data from Database

This script safely removes all CNSWPL-related data from the database before re-importing
with fixed scrapers.

Usage:
    python scripts/delete_cnswpl_data.py [--confirm]
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update, get_db_cursor

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_cnswpl_data_counts():
    """Get counts of CNSWPL data before deletion for verification"""
    try:
        counts = {}
        
        # Count CNSWPL players
        player_count = execute_query("""
            SELECT COUNT(*) as count 
            FROM players p 
            JOIN leagues l ON p.league_id = l.id 
            WHERE l.league_id = 'CNSWPL'
        """)
        counts['players'] = player_count[0]['count'] if player_count else 0
        
        # Count CNSWPL match scores
        match_count = execute_query("""
            SELECT COUNT(*) as count 
            FROM match_scores ms 
            JOIN leagues l ON ms.league_id = l.id 
            WHERE l.league_id = 'CNSWPL'
        """)
        counts['match_scores'] = match_count[0]['count'] if match_count else 0
        
        # Count CNSWPL schedules
        schedule_count = execute_query("""
            SELECT COUNT(*) as count 
            FROM schedule s 
            JOIN leagues l ON s.league_id = l.id 
            WHERE l.league_id = 'CNSWPL'
        """)
        counts['schedules'] = schedule_count[0]['count'] if schedule_count else 0
        
        # Count CNSWPL series stats
        stats_count = execute_query("""
            SELECT COUNT(*) as count 
            FROM series_stats ss 
            JOIN leagues l ON ss.league_id = l.id 
            WHERE l.league_id = 'CNSWPL'
        """)
        counts['series_stats'] = stats_count[0]['count'] if stats_count else 0
        
        # Count CNSWPL teams
        teams_count = execute_query("""
            SELECT COUNT(*) as count 
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id 
            WHERE l.league_id = 'CNSWPL'
        """)
        counts['teams'] = teams_count[0]['count'] if teams_count else 0
        
        # Count CNSWPL clubs (that only have CNSWPL teams)
        clubs_count = execute_query("""
            SELECT COUNT(DISTINCT c.id) as count 
            FROM clubs c 
            JOIN teams t ON c.id = t.club_id
            JOIN leagues l ON t.league_id = l.id 
            WHERE l.league_id = 'CNSWPL'
            AND c.id NOT IN (
                SELECT DISTINCT c2.id 
                FROM clubs c2 
                JOIN teams t2 ON c2.id = t2.club_id
                JOIN leagues l2 ON t2.league_id = l2.id 
                WHERE l2.league_id != 'CNSWPL'
            )
        """)
        counts['cnswpl_only_clubs'] = clubs_count[0]['count'] if clubs_count else 0
        
        return counts
        
    except Exception as e:
        logger.error(f"Error getting CNSWPL data counts: {e}")
        return {}

def delete_cnswpl_data():
    """Delete all CNSWPL data from database in correct order (respecting foreign keys)"""
    try:
        with get_db_cursor() as cursor:
            logger.info("🗑️ Starting CNSWPL data deletion...")
            
            # Get CNSWPL league ID
            cursor.execute("SELECT id FROM leagues WHERE league_id = 'CNSWPL'")
            cnswpl_league = cursor.fetchone()
            if not cnswpl_league:
                logger.warning("CNSWPL league not found in database")
                return
            
            cnswpl_league_id = cnswpl_league['id']
            logger.info(f"Found CNSWPL league with database ID: {cnswpl_league_id}")
            
            # Delete in order to respect foreign key constraints
            
            # 1. Delete user associations to CNSWPL players (preserve users)
            logger.info("Deleting user player associations for CNSWPL players...")
            cursor.execute("""
                DELETE FROM user_player_associations 
                WHERE tenniscores_player_id IN (
                    SELECT tenniscores_player_id 
                    FROM players 
                    WHERE league_id = %s
                )
            """, [cnswpl_league_id])
            associations_deleted = cursor.rowcount
            logger.info(f"Deleted {associations_deleted} user player associations")
            
            # 2. Delete match scores
            logger.info("Deleting CNSWPL match scores...")
            cursor.execute("DELETE FROM match_scores WHERE league_id = %s", [cnswpl_league_id])
            matches_deleted = cursor.rowcount
            logger.info(f"Deleted {matches_deleted} match scores")
            
            # 3. Delete schedules
            logger.info("Deleting CNSWPL schedules...")
            cursor.execute("DELETE FROM schedule WHERE league_id = %s", [cnswpl_league_id])
            schedules_deleted = cursor.rowcount
            logger.info(f"Deleted {schedules_deleted} schedules")
            
            # 4. Delete series stats
            logger.info("Deleting CNSWPL series stats...")
            cursor.execute("DELETE FROM series_stats WHERE league_id = %s", [cnswpl_league_id])
            stats_deleted = cursor.rowcount
            logger.info(f"Deleted {stats_deleted} series stats")
            
            # 5. Delete players
            logger.info("Deleting CNSWPL players...")
            cursor.execute("DELETE FROM players WHERE league_id = %s", [cnswpl_league_id])
            players_deleted = cursor.rowcount
            logger.info(f"Deleted {players_deleted} players")
            
            # 6. Delete teams
            logger.info("Deleting CNSWPL teams...")
            cursor.execute("DELETE FROM teams WHERE league_id = %s", [cnswpl_league_id])
            teams_deleted = cursor.rowcount
            logger.info(f"Deleted {teams_deleted} teams")
            
            # 7. Delete clubs that only belonged to CNSWPL
            logger.info("Deleting CNSWPL-only clubs...")
            cursor.execute("""
                DELETE FROM clubs 
                WHERE id IN (
                    SELECT c.id 
                    FROM clubs c 
                    WHERE c.id NOT IN (
                        SELECT DISTINCT t.club_id 
                        FROM teams t 
                        WHERE t.club_id IS NOT NULL
                    )
                    AND c.id IN (
                        SELECT DISTINCT club_id 
                        FROM teams 
                        WHERE league_id = %s
                    )
                )
            """, [cnswpl_league_id])
            clubs_deleted = cursor.rowcount
            logger.info(f"Deleted {clubs_deleted} CNSWPL-only clubs")
            
            # 8. Delete series that only belonged to CNSWPL
            logger.info("Deleting CNSWPL-only series...")
            cursor.execute("""
                DELETE FROM series 
                WHERE id IN (
                    SELECT s.id 
                    FROM series s 
                    WHERE s.id NOT IN (
                        SELECT DISTINCT t.series_id 
                        FROM teams t 
                        WHERE t.series_id IS NOT NULL
                    )
                    AND s.id IN (
                        SELECT DISTINCT series_id 
                        FROM teams 
                        WHERE league_id = %s
                    )
                )
            """, [cnswpl_league_id])
            series_deleted = cursor.rowcount
            logger.info(f"Deleted {series_deleted} CNSWPL-only series")
            
            logger.info("✅ CNSWPL data deletion completed successfully!")
            
            return {
                'associations_deleted': associations_deleted,
                'matches_deleted': matches_deleted,
                'schedules_deleted': schedules_deleted,
                'stats_deleted': stats_deleted,
                'players_deleted': players_deleted,
                'teams_deleted': teams_deleted,
                'clubs_deleted': clubs_deleted,
                'series_deleted': series_deleted
            }
            
    except Exception as e:
        logger.error(f"Error deleting CNSWPL data: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Delete all CNSWPL data from database')
    parser.add_argument('--confirm', action='store_true', 
                       help='Confirm deletion (required to prevent accidental runs)')
    
    args = parser.parse_args()
    
    if not args.confirm:
        print("❌ This script will DELETE ALL CNSWPL data from the database!")
        print("   Run with --confirm flag if you're sure you want to proceed.")
        print("   Example: python scripts/delete_cnswpl_data.py --confirm")
        return
    
    print("🔍 Getting current CNSWPL data counts...")
    before_counts = get_cnswpl_data_counts()
    
    if before_counts:
        print("📊 Current CNSWPL data in database:")
        for data_type, count in before_counts.items():
            print(f"   {data_type}: {count:,}")
        
        total_records = sum(before_counts.values())
        if total_records == 0:
            print("✅ No CNSWPL data found in database - nothing to delete")
            return
        
        print(f"\n⚠️  About to delete {total_records:,} CNSWPL records!")
        response = input("Are you absolutely sure? Type 'DELETE CNSWPL' to confirm: ")
        
        if response != "DELETE CNSWPL":
            print("❌ Deletion cancelled - confirmation text didn't match")
            return
    
    print(f"\n🗑️ Starting deletion at {datetime.now()}")
    deletion_results = delete_cnswpl_data()
    
    if deletion_results:
        print("\n📊 Deletion Summary:")
        for data_type, count in deletion_results.items():
            print(f"   {data_type}: {count:,}")
    
    print("\n🔍 Verifying deletion...")
    after_counts = get_cnswpl_data_counts()
    
    if after_counts:
        print("📊 Remaining CNSWPL data:")
        for data_type, count in after_counts.items():
            print(f"   {data_type}: {count:,}")
        
        remaining_total = sum(after_counts.values())
        if remaining_total == 0:
            print("\n✅ All CNSWPL data successfully deleted!")
        else:
            print(f"\n⚠️  {remaining_total:,} CNSWPL records still remain")
    
    print(f"\n✅ Deletion completed at {datetime.now()}")
    print("\nNext steps:")
    print("1. Re-scrape CNSWPL data with fixed scrapers")
    print("2. Re-import CNSWPL data to database")

if __name__ == "__main__":
    main()
