#!/usr/bin/env python3
"""
Automated Orphaned Teams Cleanup for ETL
=========================================

This module provides automatic cleanup of orphaned teams during ETL imports.
Should be called after all team/player/match imports are complete.

Usage:
    from data.etl.import.cleanup_orphaned_teams import cleanup_orphaned_teams_post_etl
    
    # After ETL imports complete:
    deleted_count = cleanup_orphaned_teams_post_etl(conn)
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def cleanup_orphaned_teams_post_etl(conn) -> Dict[str, int]:
    """
    Clean up orphaned teams after ETL import.
    
    An orphaned team is one that has:
    - Zero players assigned
    - Zero matches played
    - Zero schedule entries
    - Zero series stats
    
    These are "ghost" teams created by bootstrap but never populated with data.
    
    Args:
        conn: Database connection (psycopg2 connection object)
        
    Returns:
        Dict with cleanup statistics:
        {
            'teams_checked': int,
            'orphaned_found': int,
            'orphaned_deleted': int,
            'errors': int
        }
    """
    
    stats = {
        'teams_checked': 0,
        'orphaned_found': 0,
        'orphaned_deleted': 0,
        'errors': 0
    }
    
    try:
        cur = conn.cursor()
        
        # Count total teams before cleanup
        cur.execute("SELECT COUNT(*) FROM teams")
        stats['teams_checked'] = cur.fetchone()[0]
        
        logger.info(f"🔍 Checking {stats['teams_checked']} teams for orphaned records...")
        
        # Find orphaned teams
        cur.execute("""
            SELECT 
                t.id,
                t.team_name,
                l.league_id
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE (SELECT COUNT(*) FROM players p WHERE p.team_id = t.id) = 0
              AND (SELECT COUNT(*) FROM match_scores ms WHERE ms.home_team_id = t.id OR ms.away_team_id = t.id) = 0
              AND (SELECT COUNT(*) FROM schedule s WHERE s.home_team_id = t.id OR s.away_team_id = t.id) = 0
              AND (SELECT COUNT(*) FROM series_stats ss WHERE ss.team_id = t.id) = 0
        """)
        
        orphaned_teams = cur.fetchall()
        stats['orphaned_found'] = len(orphaned_teams)
        
        if stats['orphaned_found'] == 0:
            logger.info("✅ No orphaned teams found - database is clean!")
            return stats
        
        # Log orphaned teams by league
        by_league = {}
        for team_id, team_name, league_id in orphaned_teams:
            if league_id not in by_league:
                by_league[league_id] = []
            by_league[league_id].append((team_id, team_name))
        
        logger.warning(f"⚠️  Found {stats['orphaned_found']} orphaned teams:")
        for league_id, teams in by_league.items():
            logger.warning(f"   {league_id}: {len(teams)} orphaned teams")
            # Log first few examples
            for team_id, team_name in teams[:3]:
                logger.warning(f"      - {team_name} (ID: {team_id})")
            if len(teams) > 3:
                logger.warning(f"      ... and {len(teams) - 3} more")
        
        # Delete orphaned teams
        team_ids = [row[0] for row in orphaned_teams]
        cur.execute("""
            DELETE FROM teams 
            WHERE id = ANY(%s)
        """, (team_ids,))
        
        stats['orphaned_deleted'] = cur.rowcount
        conn.commit()
        
        logger.info(f"🧹 Successfully deleted {stats['orphaned_deleted']} orphaned teams")
        logger.info(f"✅ Database cleanup complete - {stats['teams_checked'] - stats['orphaned_deleted']} valid teams remain")
        
    except Exception as e:
        logger.error(f"❌ Error during orphaned teams cleanup: {e}")
        stats['errors'] = 1
        conn.rollback()
        # Don't raise - cleanup failure shouldn't break ETL
    
    return stats


def validate_no_orphaned_teams(conn) -> bool:
    """
    Validate that no orphaned teams exist (for testing/monitoring).
    
    Args:
        conn: Database connection
        
    Returns:
        True if no orphaned teams found, False otherwise
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM teams t
            WHERE (SELECT COUNT(*) FROM players p WHERE p.team_id = t.id) = 0
              AND (SELECT COUNT(*) FROM match_scores ms WHERE ms.home_team_id = t.id OR ms.away_team_id = t.id) = 0
              AND (SELECT COUNT(*) FROM schedule s WHERE s.home_team_id = t.id OR s.away_team_id = t.id) = 0
              AND (SELECT COUNT(*) FROM series_stats ss WHERE ss.team_id = t.id) = 0
        """)
        
        orphaned_count = cur.fetchone()[0]
        
        if orphaned_count > 0:
            logger.warning(f"⚠️  Validation failed: {orphaned_count} orphaned teams found")
            return False
        
        logger.info("✅ Validation passed: No orphaned teams found")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error validating orphaned teams: {e}")
        return False


if __name__ == '__main__':
    """
    Can be run standalone for testing or manual cleanup.
    """
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from database_config import get_db
    
    print("=" * 80)
    print("ORPHANED TEAMS CLEANUP (Standalone)")
    print("=" * 80)
    
    with get_db() as conn:
        stats = cleanup_orphaned_teams_post_etl(conn)
        
        print("\nCleanup Statistics:")
        print(f"  Teams checked:   {stats['teams_checked']}")
        print(f"  Orphaned found:  {stats['orphaned_found']}")
        print(f"  Orphaned deleted: {stats['orphaned_deleted']}")
        print(f"  Errors:          {stats['errors']}")
        
        # Validate
        if validate_no_orphaned_teams(conn):
            print("\n✅ Database is clean!")
        else:
            print("\n⚠️ Validation failed - orphaned teams still exist")
            sys.exit(1)


