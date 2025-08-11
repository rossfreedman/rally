#!/usr/bin/env python3
"""
Reset dynamic season data for local database (safe for ETL repopulation)
======================================================================

Removes dynamic, season-specific data in a dependency-safe order to simulate
the start of a new season. This is designed for LOCAL use only.

What this script does:
- Nulls references to teams in dependent tables where nullable
- Clears season data tables: match_scores, schedule, series_stats
- Clears dependent team-based tables: saved_lineups, captain_messages, polls (+ choices/responses)
- Deletes all teams
- Clears safety/utility table: team_mapping_backup (if exists)

Intentionally NOT deleting due to hard FK dependencies used by ETL and app:
- series (players.series_id is NOT NULL, player_availability.series_id is NOT NULL)
- series_leagues (ETL needs this to resolve series → league mapping)

Usage:
  python scripts/reset_for_new_season.py --force
  python scripts/reset_for_new_season.py --dry-run
  python scripts/reset_for_new_season.py --wipe-series --league APTA_CHICAGO --force

Flags:
  --dry-run   Show what would happen without changing the database
  --force     Skip interactive confirmation

Exit codes:
  0 on success, 1 on failure
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Tuple

# Ensure project root imports work
import os
import pathlib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db  # type: ignore


SEASON_TABLES_TO_CLEAR_IN_ORDER: List[str] = [
    # Dependent detail tables (no FKs or nullable FKs to teams)
    "match_scores",
    "schedule",
    "series_stats",
]

TEAM_DEPENDENT_TABLE_ACTIONS: List[Tuple[str, str]] = [
    # (SQL, human-readable description)
    ("UPDATE players SET team_id = NULL WHERE team_id IS NOT NULL", "Null players.team_id"),
    ("UPDATE user_contexts SET active_team_id = NULL WHERE active_team_id IS NOT NULL", "Null user_contexts.active_team_id"),
    ("UPDATE lineup_escrow SET initiator_team_id = NULL WHERE initiator_team_id IS NOT NULL", "Null lineup_escrow.initiator_team_id"),
    ("UPDATE lineup_escrow SET recipient_team_id = NULL WHERE recipient_team_id IS NOT NULL", "Null lineup_escrow.recipient_team_id"),
    ("UPDATE user_instructions SET team_id = NULL WHERE team_id IS NOT NULL", "Null user_instructions.team_id"),
]

TEAM_DEPENDENT_TABLES_TO_DELETE: List[str] = [
    # Hard FKs to teams (cannot null); safe to clear contents locally
    "saved_lineups",
    "captain_messages",
    # Polls references teams but cascades to choices/responses via ORM; clear explicitly
    "poll_responses",
    "poll_choices",
    "polls",
]

OPTIONAL_UTILITY_TABLES_TO_CLEAR: List[str] = [
    "team_mapping_backup",
]


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (table_name,),
    )
    return bool(cursor.fetchone()[0])


def _count_rows(cursor, table_name: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return int(cursor.fetchone()[0])


def summarize_counts(cursor) -> Dict[str, int]:
    tables = [
        *TEAM_DEPENDENT_TABLES_TO_DELETE,
        *SEASON_TABLES_TO_CLEAR_IN_ORDER,
        "teams",
        *OPTIONAL_UTILITY_TABLES_TO_CLEAR,
    ]
    summary: Dict[str, int] = {}
    for t in tables:
        if _table_exists(cursor, t):
            summary[t] = _count_rows(cursor, t)
    return summary


def run(dry_run: bool = False) -> None:
    with get_db() as conn:
        with conn.cursor() as cursor:
            # Pre-summarize
            before = summarize_counts(cursor)

            print("=== Reset for New Season (LOCAL) ===")
            print("This will clear dynamic season data and remove all teams.")
            print("Keeping: leagues, clubs, users, user_player_associations, players, series, series_leagues")
            print("")
            if before:
                print("Current row counts:")
                for name in sorted(before.keys()):
                    print(f" - {name}: {before[name]:,}")
            else:
                print("No target tables found to summarize.")

            if dry_run:
                print("\nDRY RUN: No changes will be made.")
                return

            # Start transaction
            try:
                # 1) Null out team references where nullable (check table existence first)
                for table_name, sql, desc in TEAM_DEPENDENT_TABLE_ACTIONS:
                    if _table_exists(cursor, table_name):
                        try:
                            cursor.execute(sql)
                            print(f"✓ {desc}")
                        except Exception as e:
                            # Handle column doesn't exist errors gracefully
                            if "does not exist" in str(e):
                                print(f"⚠ Skipped {desc} (column doesn't exist in {table_name})")
                            else:
                                raise e
                    else:
                        print(f"⚠ Skipped {desc} (table {table_name} doesn't exist)")

                # 2) Clear hard-dependent tables that block team deletion
                for table in TEAM_DEPENDENT_TABLES_TO_DELETE:
                    if _table_exists(cursor, table):
                        cursor.execute(f"DELETE FROM {table}")
                        print(f"✓ Cleared {table}")

                # 3) Clear season result tables
                for table in SEASON_TABLES_TO_CLEAR_IN_ORDER:
                    if _table_exists(cursor, table):
                        cursor.execute(f"DELETE FROM {table}")
                        print(f"✓ Cleared {table}")

                # 4) Delete all teams
                if _table_exists(cursor, "teams"):
                    cursor.execute("DELETE FROM teams")
                    print("✓ Deleted all teams")

                # 5) Optional utility table(s)
                for table in OPTIONAL_UTILITY_TABLES_TO_CLEAR:
                    if _table_exists(cursor, table):
                        cursor.execute(f"DELETE FROM {table}")
                        print(f"✓ Cleared {table}")

                # 6) Explicitly keep series & series_leagues due to FKs used by ETL
                print("ℹ Keeping tables: series, series_leagues (required for ETL & FKs)")

                conn.commit()
                print("\n✅ Reset complete.")

                # Post-summarize
                after = summarize_counts(cursor)
                if after:
                    print("\nNew row counts:")
                    for name in sorted(after.keys()):
                        print(f" - {name}: {after[name]:,}")
                else:
                    print("No target tables found after reset.")

            except Exception as e:
                conn.rollback()
                print(f"\n❌ Reset failed: {e}")
                sys.exit(1)


def run_wipe_series(league: str, dry_run: bool = False) -> None:
    """
    Destructive mode for starting a fresh season for a specific league.
    Deletes players and player_availability for that league, then removes
    series_leagues links and any series that are no longer referenced by
    any league. Finally, clears teams for the league.

    After this, you must run bootstrap_series_from_players.py and the ETL.
    """
    if not league:
        print("❌ --wipe-series requires --league LEAGUE_ID (e.g., APTA_CHICAGO)")
        sys.exit(1)

    with get_db() as conn:
        with conn.cursor() as cursor:
            # Resolve league DB id
            cursor.execute("SELECT id FROM leagues WHERE league_id = %s", (league,))
            row = cursor.fetchone()
            if not row:
                print(f"❌ League not found: {league}")
                sys.exit(1)
            league_db_id = int(row[0])

            print(f"=== WIPE SERIES MODE for {league} (id={league_db_id}) ===")

            # Summaries
            def count(sql, params=()):
                cursor.execute(sql, params)
                return int(cursor.fetchone()[0])

            before = {
                "players": count("SELECT COUNT(*) FROM players WHERE league_id = %s", (league_db_id,)),
                "player_availability": count("SELECT COUNT(*) FROM player_availability WHERE series_id IN (SELECT s.id FROM series s JOIN series_leagues sl ON sl.series_id = s.id WHERE sl.league_id = %s)", (league_db_id,)),
                "teams": count("SELECT COUNT(*) FROM teams WHERE league_id = %s", (league_db_id,)),
                "series_links": count("SELECT COUNT(*) FROM series_leagues WHERE league_id = %s", (league_db_id,)),
            }

            for k, v in before.items():
                print(f" - {k}: {v:,}")

            if dry_run:
                print("\nDRY RUN: No changes will be made.")
                return

            try:
                # 1) Null team refs in this league to enable deletion
                cursor.execute("UPDATE players SET team_id = NULL WHERE league_id = %s AND team_id IS NOT NULL", (league_db_id,))
                cursor.execute("UPDATE user_contexts SET active_team_id = NULL WHERE active_team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_db_id,))
                cursor.execute("UPDATE lineup_escrow SET initiator_team_id = NULL WHERE initiator_team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_db_id,))
                cursor.execute("UPDATE lineup_escrow SET recipient_team_id = NULL WHERE recipient_team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_db_id,))
                cursor.execute("UPDATE user_instructions SET team_id = NULL WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_db_id,))

                # 2) Clear season tables scoped to league
                cursor.execute("DELETE FROM match_scores WHERE league_id = %s", (league_db_id,))
                cursor.execute("DELETE FROM schedule WHERE league_id = %s", (league_db_id,))
                cursor.execute("DELETE FROM series_stats WHERE league_id = %s", (league_db_id,))

                # 3) Delete dependent team-based tables scoped to league
                cursor.execute("DELETE FROM saved_lineups WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_db_id,))
                cursor.execute("DELETE FROM captain_messages WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_db_id,))
                cursor.execute("DELETE FROM poll_responses WHERE poll_id IN (SELECT id FROM polls WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s))", (league_db_id,))
                cursor.execute("DELETE FROM poll_choices WHERE poll_id IN (SELECT id FROM polls WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s))", (league_db_id,))
                cursor.execute("DELETE FROM polls WHERE team_id IN (SELECT id FROM teams WHERE league_id = %s)", (league_db_id,))

                # 4) Delete teams for this league
                cursor.execute("DELETE FROM teams WHERE league_id = %s", (league_db_id,))

                # 5) Delete players & availability for this league
                cursor.execute("DELETE FROM poll_responses WHERE player_id IN (SELECT id FROM players WHERE league_id = %s)", (league_db_id,))
                cursor.execute("DELETE FROM player_history WHERE league_id = %s", (league_db_id,))
                cursor.execute("DELETE FROM player_availability WHERE series_id IN (SELECT s.id FROM series s JOIN series_leagues sl ON sl.series_id = s.id WHERE sl.league_id = %s)", (league_db_id,))
                cursor.execute("DELETE FROM players WHERE league_id = %s", (league_db_id,))

                # 6) Remove series links for this league
                cursor.execute("DELETE FROM series_leagues WHERE league_id = %s", (league_db_id,))

                # 7) Remove any series now orphaned (no links in series_leagues)
                cursor.execute("DELETE FROM series s WHERE NOT EXISTS (SELECT 1 FROM series_leagues sl WHERE sl.series_id = s.id)")

                conn.commit()
                print("\n✅ Wipe-series complete.")
            except Exception as e:
                conn.rollback()
                print(f"\n❌ Wipe-series failed: {e}")
                sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset local DB dynamic season data in a safe order")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without executing")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--wipe-series", action="store_true", help="Destructively wipe series, series_leagues, players, player_availability and teams for a league")
    parser.add_argument("--league", help="League identifier (e.g., APTA_CHICAGO) required with --wipe-series")
    args = parser.parse_args()

    if args.wipe_series:
        if not args.league:
            print("❌ --wipe-series requires --league LEAGUE_ID (e.g., APTA_CHICAGO)")
            sys.exit(1)
        if not args.force and not args.dry_run:
            resp = input(f"This will DELETE series, links, players, player_availability, teams for {args.league}. Continue? (y/N): ")
            if resp.strip().lower() != "y":
                print("Cancelled.")
                sys.exit(0)
        run_wipe_series(args.league, dry_run=args.dry_run)
    else:
        if not args.force and not args.dry_run:
            resp = input("This will DELETE season data and ALL teams in your LOCAL DB. Continue? (y/N): ")
            if resp.strip().lower() != "y":
                print("Cancelled.")
                sys.exit(0)
        run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()


