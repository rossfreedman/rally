#!/usr/bin/env python3
"""
Export Series Stats from Database to JSON

This script exports series_stats from the database to JSON files,
allowing you to get production stats data for local testing.

Usage:
    python3 scripts/export_series_stats_from_db.py [--league CNSWPL|APTA_CHICAGO|all] [--env production|staging|local]
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database_config import get_db_url, get_database_mode, is_local_development
from database_utils import execute_query, get_db

def export_league_stats(league_key, league_dir, output_path):
    """Export series stats for a league from database to JSON"""
    print(f"📊 Exporting {league_key} series stats...")
    
    # Get league ID
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM leagues WHERE league_id = %s OR league_name = %s LIMIT 1",
                (league_key, league_key)
            )
            result = cur.fetchone()
            if not result:
                print(f"❌ League '{league_key}' not found in database")
                return False
            
            league_id = result[0]
            
            # Query series stats
            query = """
                SELECT 
                    series,
                    team,
                    points,
                    matches_won,
                    matches_lost,
                    matches_tied,
                    lines_won,
                    lines_lost,
                    lines_for,
                    lines_ret,
                    sets_won,
                    sets_lost,
                    games_won,
                    games_lost
                FROM series_stats
                WHERE league_id = %s
                ORDER BY series, team
            """
            
            cur.execute(query, [league_id])
            rows = cur.fetchall()
            
            # Convert to JSON format matching scraper output
            stats_data = []
            for row in rows:
                stat = {
                    "series": row[0],
                    "team": row[1],
                    "points": row[2],
                    "matches": {
                        "won": row[3] or 0,
                        "lost": row[4] or 0,
                        "tied": row[5] or 0,
                    },
                    "lines": {
                        "won": row[6] or 0,
                        "lost": row[7] or 0,
                    },
                    "sets": {
                        "won": row[10] or 0,
                        "lost": row[11] or 0,
                    },
                    "games": {
                        "won": row[12] or 0,
                        "lost": row[13] or 0,
                    },
                }
                stats_data.append(stat)
            
            # Save to JSON file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2)
            
            print(f"   ✅ Exported {len(stats_data)} team stat records")
            print(f"   📄 Saved to: {output_path}")
            return True

def main():
    parser = argparse.ArgumentParser(description='Export series_stats from database to JSON')
    parser.add_argument(
        '--league',
        choices=['CNSWPL', 'APTA_CHICAGO', 'all'],
        default='all',
        help='League to export (default: all)'
    )
    parser.add_argument(
        '--env',
        choices=['production', 'staging', 'local'],
        help='Environment to export from (default: current database connection)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("📤 Exporting Series Stats from Database to JSON")
    print("=" * 80)
    print()
    
    # Show current database info
    print(f"📊 Current Database:")
    print(f"   Mode: {get_database_mode()}")
    print(f"   Environment: {'Local' if is_local_development() else 'Railway/Production'}")
    print(f"   URL: {get_db_url()}")
    print()
    
    if args.env:
        print(f"⚠️  Note: --env flag is not yet implemented")
        print(f"   Currently uses the database from your current connection")
        print()
    
    # Define leagues
    leagues_config = {
        'CNSWPL': {
            'key': 'CNSWPL',
            'dir': 'CNSWPL',
        },
        'APTA_CHICAGO': {
            'key': 'APTA_CHICAGO',
            'dir': 'APTA_CHICAGO',
        }
    }
    
    # Determine which leagues to export
    if args.league == 'all':
        leagues_to_export = list(leagues_config.keys())
    else:
        leagues_to_export = [args.league]
    
    # Export each league
    exported = 0
    for league_key in leagues_to_export:
        if league_key in leagues_config:
            config = leagues_config[league_key]
            output_path = Path(f"data/leagues/{config['dir']}/series_stats.json")
            
            if export_league_stats(config['key'], config['dir'], output_path):
                exported += 1
            print()
    
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print(f"✅ Exported: {exported}/{len(leagues_to_export)} leagues")
    print()
    
    if exported > 0:
        print("✅ JSON files are ready for local testing!")
        print()
        print("You can now:")
        print("  1. Test the Series H fix: python3 scripts/fix_cnswpl_series_h_stats.py")
        print("  2. Re-import stats: python3 data/etl/import/import_stats.py CNSWPL")

if __name__ == "__main__":
    main()

