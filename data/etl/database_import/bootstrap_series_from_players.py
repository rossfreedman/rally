#!/usr/bin/env python3
"""
Bootstrap Series From Players JSON
==================================

Reads data/leagues/all/players.json and ensures that all series referenced by
players exist in the database, with proper linkage in series_leagues.

This is required after a destructive reset where series and series_leagues were
cleared, so that subsequent ETL steps (stats, players, schedules) can resolve
series IDs.

Usage:
  python3 data/etl/database_import/bootstrap_series_from_players.py [--league LEAGUE_ID]

If --league is provided (e.g., APTA_CHICAGO), only bootstrap series for that
league. Otherwise bootstraps for all leagues found in players.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, Set, Tuple, Optional

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(script_dir).parent.parent.parent
sys.path.insert(0, str(project_root))

from database_utils import execute_query_one, execute_update
from utils.league_utils import normalize_league_id


def _series_has_display_name_not_null() -> bool:
    # Check if display_name column exists
    row = execute_query_one(
        """
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'series' AND column_name = 'display_name'
        LIMIT 1
        """,
        (),
    )
    if not row:
        return False
    # If exists, check nullability
    row2 = execute_query_one(
        """
        SELECT is_nullable FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'series' AND column_name = 'display_name'
        LIMIT 1
        """,
        (),
    )
    if not row2:
        return False
    return str(row2.get('is_nullable', 'YES')).upper() == 'NO'


def load_players_all() -> list:
    data_dir = project_root / "data" / "leagues" / "all"
    players_path = data_dir / "players.json"
    if not players_path.exists():
        raise FileNotFoundError(f"players.json not found at {players_path}")
    with players_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        if not isinstance(data, list):
            data = [data]
        return data


def get_league_db_id(league_id_str: str) -> Optional[int]:
    row = execute_query_one("SELECT id FROM leagues WHERE league_id = %s", (league_id_str,))
    return row["id"] if row else None


def ensure_series(series_name: str, league_id: int) -> int:
    # Try fetch existing series for this league first
    row = execute_query_one(
        "SELECT id FROM series WHERE name = %s AND league_id = %s", 
        (series_name, league_id)
    )
    if row:
        return int(row["id"])
    
    # Insert new series with league_id
    if _series_has_display_name_not_null():
        execute_update(
            "INSERT INTO series (name, display_name, league_id) VALUES (%s, %s, %s) ON CONFLICT (name, league_id) DO NOTHING",
            (series_name, series_name, league_id),
        )
    else:
        execute_update(
            "INSERT INTO series (name, league_id) VALUES (%s, %s) ON CONFLICT (name, league_id) DO NOTHING",
            (series_name, league_id),
        )
    
    # Fetch again
    row = execute_query_one(
        "SELECT id FROM series WHERE name = %s AND league_id = %s", 
        (series_name, league_id)
    )
    if not row:
        raise RuntimeError(f"Failed to ensure series row for '{series_name}' in league {league_id}")
    return int(row["id"])


def ensure_series_league(series_id: int, league_db_id: int) -> None:
    # Check existence to avoid relying on unique constraints
    existing = execute_query_one(
        "SELECT id FROM series_leagues WHERE series_id = %s AND league_id = %s",
        (series_id, league_db_id),
    )
    if existing:
        return
    # Minimal insert compatible with older schemas
    execute_update(
        "INSERT INTO series_leagues (series_id, league_id) VALUES (%s, %s)",
        (series_id, league_db_id),
    )


def bootstrap(only_league: Optional[str] = None) -> Dict[str, int]:
    players = load_players_all()
    seen: Set[Tuple[str, str]] = set()
    created_series = 0
    linked_pairs = 0
    skipped = 0

    for rec in players:
        raw_league = (rec.get("League") or "").strip()
        series_name = (rec.get("Series") or "").strip()
        if not raw_league or not series_name:
            skipped += 1
            continue
        norm_league = normalize_league_id(raw_league)
        # Filter by requested league
        if only_league and only_league != norm_league and only_league != raw_league and only_league != (rec.get("source_league") or "").strip():
            continue

        key = (norm_league, series_name)
        if key in seen:
            continue
        seen.add(key)

        league_db_id = get_league_db_id(norm_league) or get_league_db_id(raw_league)
        if not league_db_id:
            # Try uppercase variant
            league_db_id = get_league_db_id((raw_league or "").upper())
        if not league_db_id:
            # Unknown league in DB, skip
            skipped += 1
            continue

        series_id = ensure_series(series_name, league_db_id)
        # Count only if newly created (best-effort: check link absence)
        # We can't easily detect insert vs conflict here; treat all as linked
        ensure_series_league(series_id, league_db_id)
        linked_pairs += 1

    return {
        "unique_series_pairs": len(seen),
        "linked_pairs": linked_pairs,
        "skipped": skipped,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Bootstrap series and series_leagues from players.json")
    parser.add_argument("--league", help="Limit bootstrapping to a specific league_id (e.g., APTA_CHICAGO)")
    args = parser.parse_args()

    stats = bootstrap(args.league)
    print("📊 Bootstrap complete:")
    for k, v in stats.items():
        print(f" - {k}: {v}")


if __name__ == "__main__":
    main()


