#!/usr/bin/env python3
"""
SSH Team Association Fix Script for Production
==============================================

This script should be run directly on the Railway production server via SSH
to fix missing team associations for APTA Chicago players.

Usage on production server:
    python3 ssh_fix_team_associations.py --dry-run    # Preview changes
    python3 ssh_fix_team_associations.py --execute    # Apply changes

The players.json file should be uploaded to the server first.
"""

import json
import sys
import os
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Production database connection (local on server)
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# Players file path (should be uploaded to server)
PLAYERS_FILE_PATH = "players.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_players_data(file_path: str) -> List[Dict]:
    """Load players data from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Players file not found: {file_path}")
        logger.error("💡 Make sure to upload the players.json file to the server first")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in players file: {e}")
        sys.exit(1)

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(PRODUCTION_DB_URL, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)

def build_team_cache(cursor) -> Dict[str, int]:
    """Build team lookup cache"""
    logger.info("🔧 Building team lookup cache...")
    
    cursor.execute("""
        SELECT l.league_id, t.team_name, t.id 
        FROM teams t 
        JOIN leagues l ON t.league_id = l.id
        WHERE l.league_id = 'APTA_CHICAGO'
    """)
    
    team_cache = {}
    for row in cursor.fetchall():
        team_cache[row['team_name']] = row['id']
    
    logger.info(f"✅ Cached {len(team_cache)} teams")
    return team_cache

def get_current_status(cursor):
    """Get current team association status"""
    cursor.execute("""
        SELECT 
            COUNT(*) as total_players,
            COUNT(team_id) as players_with_teams,
            COUNT(*) - COUNT(team_id) as players_missing_teams
        FROM players 
        WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')
    """)
    
    result = cursor.fetchone()
    return {
        'total': result['total_players'],
        'with_teams': result['players_with_teams'],
        'missing_teams': result['players_missing_teams'],
        'success_rate': (result['players_with_teams'] / result['total_players'] * 100) if result['total_players'] > 0 else 0
    }

def fix_team_associations(dry_run: bool = True):
    """Fix team associations for all APTA_CHICAGO players"""
    
    logger.info("🔧 Starting Team Association Fix")
    logger.info("=" * 50)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    
    # Load the JSON data
    logger.info(f"📖 Loading players data from {PLAYERS_FILE_PATH}")
    players_data = load_players_data(PLAYERS_FILE_PATH)
    logger.info(f"✅ Loaded {len(players_data)} player records")
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get initial status
        initial_status = get_current_status(cursor)
        logger.info(f"📊 Initial Status:")
        logger.info(f"  Total players: {initial_status['total']}")
        logger.info(f"  Players with teams: {initial_status['with_teams']}")
        logger.info(f"  Players missing teams: {initial_status['missing_teams']}")
        logger.info(f"  Success rate: {initial_status['success_rate']:.1f}%")
        
        # Build team lookup cache
        team_cache = build_team_cache(cursor)
        
        # Process each player record
        updates_planned = 0
        errors = 0
        sample_updates = []
        
        logger.info("🔄 Processing player records...")
        
        for i, record in enumerate(players_data):
            if i % 2000 == 0 and i > 0:
                logger.info(f"📊 Processed {i:,} records so far...")
                
            try:
                player_id = record.get("Player ID", "").strip()
                team_name = record.get("Team", "").strip()
                first_name = record.get("First Name", "").strip()
                last_name = record.get("Last Name", "").strip()
                
                if not player_id or not team_name:
                    continue
                
                # Look up team ID
                team_id = team_cache.get(team_name)
                if not team_id:
                    continue  # Skip if team not found
                
                if dry_run:
                    # Just check if this player needs updating
                    cursor.execute("""
                        SELECT team_id 
                        FROM players 
                        WHERE tenniscores_player_id = %s 
                        AND league_id = (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')
                    """, (player_id,))
                    
                    result = cursor.fetchone()
                    if result and result['team_id'] is None:
                        updates_planned += 1
                        if len(sample_updates) < 10:
                            sample_updates.append(f"  {first_name} {last_name} → {team_name} (Team ID: {team_id})")
                else:
                    # Actually update the player's team_id
                    cursor.execute("""
                        UPDATE players 
                        SET team_id = %s 
                        WHERE tenniscores_player_id = %s 
                        AND league_id = (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')
                        AND team_id IS NULL
                    """, (team_id, player_id))
                    
                    if cursor.rowcount > 0:
                        updates_planned += 1
                        if len(sample_updates) < 10:
                            sample_updates.append(f"  ✅ {first_name} {last_name} → {team_name} (Team ID: {team_id})")
                        
            except Exception as e:
                errors += 1
                if errors <= 10:  # Only show first 10 errors
                    logger.error(f"❌ Error processing {player_id}: {e}")
        
        if not dry_run:
            # Commit all changes
            conn.commit()
            logger.info("✅ All changes committed to database")
        
        logger.info("=" * 50)
        logger.info(f"📊 {'PLANNED CHANGES' if dry_run else 'ACTUAL CHANGES'} SUMMARY")
        logger.info("=" * 50)
        logger.info(f"📄 Total records processed: {len(players_data):,}")
        logger.info(f"✅ Team associations {'planned' if dry_run else 'fixed'}: {updates_planned:,}")
        logger.info(f"❌ Errors: {errors}")
        
        if sample_updates:
            logger.info(f"📋 Sample {'planned updates' if dry_run else 'updates made'}:")
            for update in sample_updates:
                logger.info(update)
            if updates_planned > len(sample_updates):
                logger.info(f"  ... and {updates_planned - len(sample_updates):,} more")
        
        if not dry_run:
            # Check final status
            final_status = get_current_status(cursor)
            logger.info("=" * 50)
            logger.info(f"📊 FINAL STATUS:")
            logger.info(f"  Total players: {final_status['total']:,}")
            logger.info(f"  Players with teams: {final_status['with_teams']:,}")
            logger.info(f"  Players missing teams: {final_status['missing_teams']:,}")
            logger.info(f"  Success rate: {final_status['success_rate']:.1f}%")
            logger.info(f"  Improvement: +{final_status['with_teams'] - initial_status['with_teams']:,} team associations")
        
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        if not dry_run:
            conn.rollback()
            logger.info("🔄 Database changes rolled back")
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Fix team associations for APTA Chicago players')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--execute', action='store_true', help='Apply changes to database')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        logger.error("❌ Must specify either --dry-run or --execute")
        parser.print_help()
        sys.exit(1)
    
    if args.dry_run and args.execute:
        logger.error("❌ Cannot specify both --dry-run and --execute")
        sys.exit(1)
    
    fix_team_associations(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
