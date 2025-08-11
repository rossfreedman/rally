#!/usr/bin/env python3
"""
Reset Staging Database for Fresh ETL
====================================

Clears staging database to prepare for fresh ETL import.
Designed specifically for staging environment (Railway).

This script removes:
- All match scores, schedules, series stats
- All teams and team-dependent data
- Keeps users, user associations, and league structure

Usage:
  railway ssh python scripts/reset_staging_for_fresh_etl.py --force
"""

import argparse
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

# Tables to clear in dependency order
TABLES_TO_CLEAR = [
    "match_scores",        # Match data
    "schedule",            # Schedule data
    "series_stats",        # Series statistics
    "captain_messages",    # Team-dependent messages
    "saved_lineups",       # Team lineups
    "poll_responses",      # Poll responses
    "poll_choices",        # Poll choices
    "polls",               # Polls (depends on teams)
    "team_mapping_backup", # Utility table
    "teams"                # Teams (clear last)
]

# Update operations to null team references
NULL_TEAM_OPERATIONS = [
    ("UPDATE players SET team_id = NULL WHERE team_id IS NOT NULL", "Null players.team_id"),
]

def table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        )
    """, (table_name,))
    return cursor.fetchone()[0]

def get_table_count(cursor, table_name):
    """Get row count for a table"""
    if not table_exists(cursor, table_name):
        return 0
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]

def main():
    parser = argparse.ArgumentParser(description="Reset staging database for fresh ETL")
    parser.add_argument("--force", action="store_true", help="Skip confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    print("🔄 STAGING DATABASE RESET FOR FRESH ETL")
    print("=" * 50)
    print("This will clear all season data from staging database")
    print("Keeping: users, user_player_associations, leagues, clubs, series")
    print()

    if not args.force and not args.dry_run:
        response = input("Continue with staging reset? (y/N): ")
        if response.lower() != 'y':
            print("❌ Reset cancelled")
            sys.exit(0)

    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made")
        print()

    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                
                # Show current counts
                print("📊 Current table counts:")
                total_records = 0
                for table in TABLES_TO_CLEAR:
                    if table_exists(cursor, table):
                        count = get_table_count(cursor, table)
                        total_records += count
                        print(f"  - {table}: {count:,}")
                    else:
                        print(f"  - {table}: (not found)")
                
                print(f"\n📈 Total records to clear: {total_records:,}")
                print()

                if args.dry_run:
                    print("✅ Dry run complete - no changes made")
                    return

                # Start clearing
                print("🚀 Starting reset...")
                
                # 1. Null team references
                for sql, description in NULL_TEAM_OPERATIONS:
                    try:
                        cursor.execute(sql)
                        print(f"✅ {description}")
                    except Exception as e:
                        print(f"⚠️  {description} - skipped: {e}")

                # 2. Clear tables in order
                cleared_count = 0
                for table in TABLES_TO_CLEAR:
                    if table_exists(cursor, table):
                        try:
                            cursor.execute(f"DELETE FROM {table}")
                            rows_affected = cursor.rowcount
                            cleared_count += rows_affected
                            print(f"✅ Cleared {table} ({rows_affected:,} rows)")
                        except Exception as e:
                            print(f"❌ Failed to clear {table}: {e}")
                    else:
                        print(f"⚠️  Table {table} not found - skipped")

                # Commit all changes
                conn.commit()
                
                print()
                print("🎉 STAGING RESET COMPLETE!")
                print(f"📊 Total records cleared: {cleared_count:,}")
                print()
                print("✅ Staging database is ready for fresh ETL import")
                print("🚀 Next step: Run master ETL import")
                
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
