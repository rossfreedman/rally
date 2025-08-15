#!/usr/bin/env python3
"""
Bootstrap Teams From Players JSON
=================================

Creates missing teams using data/leagues/all/players.json by grouping on
League + Series + Club, with team_name from "Series Mapping ID". Ensures
series exists (and is linked to league) before team insert.

Usage:
  python3 data/etl/database_import/bootstrap_teams_from_players.py --league APTA_CHICAGO
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Tuple, Set

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(script_dir).parent.parent.parent
sys.path.insert(0, str(project_root))

from database_utils import execute_query_one, execute_update
from utils.league_utils import normalize_league_id


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
    # Check if display_name exists and is NOT NULL
    col = execute_query_one(
        "SELECT is_nullable FROM information_schema.columns WHERE table_name='series' AND column_name='display_name' LIMIT 1",
        (),
    )
    if col and str(col.get("is_nullable", "YES")).upper() == "NO":
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
    exists = execute_query_one(
        "SELECT id FROM series_leagues WHERE series_id=%s AND league_id=%s",
        (series_id, league_db_id),
    )
    if exists:
        return
    execute_update(
        "INSERT INTO series_leagues (series_id, league_id) VALUES (%s, %s)",
        (series_id, league_db_id),
    )


def get_club_id_by_name(name: str) -> Optional[int]:
    row = execute_query_one("SELECT id FROM clubs WHERE name = %s", (name,))
    return row["id"] if row else None


def _teams_has_display_name_not_null() -> bool:
    row = execute_query_one(
        "SELECT is_nullable FROM information_schema.columns WHERE table_name='teams' AND column_name='display_name' LIMIT 1",
        (),
    )
    if not row:
        return False
    return str(row.get('is_nullable', 'YES')).upper() == 'NO'


def ensure_team(team_name: str, club_id: int, series_id: int, league_db_id: int) -> None:
    # Check if team already exists with either constraint
    # 1. Check unique_team_club_series_league constraint
    existing_by_combo = execute_query_one(
        "SELECT id FROM teams WHERE club_id = %s AND series_id = %s AND league_id = %s",
        (club_id, series_id, league_db_id)
    )
    if existing_by_combo:
        return  # Team already exists with this club/series/league combination
    
    # 2. Check unique_team_name_per_league constraint
    existing_by_name = execute_query_one(
        "SELECT id FROM teams WHERE team_name = %s AND league_id = %s",
        (team_name, league_db_id)
    )
    if existing_by_name:
        # Team name already exists in league, skip to avoid conflict
        print(f"⚠️  Skipping team '{team_name}' - name already exists in league {league_db_id}")
        return
    
    # Insert with natural uniqueness, setting display_name if required
    if _teams_has_display_name_not_null():
        execute_update(
            """
            INSERT INTO teams (team_name, team_alias, club_id, series_id, league_id, is_active, created_at, display_name)
            VALUES (%s, NULL, %s, %s, %s, true, NOW(), %s)
            ON CONFLICT ON CONSTRAINT unique_team_club_series_league DO NOTHING
            """,
            (team_name, club_id, series_id, league_db_id, team_name),
        )
    else:
        execute_update(
            """
            INSERT INTO teams (team_name, club_id, series_id, league_id, is_active, created_at)
            VALUES (%s, %s, %s, %s, true, NOW())
            ON CONFLICT ON CONSTRAINT unique_team_club_series_league DO NOTHING
            """,
            (team_name, club_id, series_id, league_db_id),
        )


def bootstrap(league: str) -> Dict[str, int]:
    players = load_players_all()
    created = 0
    skipped = 0
    seen: Set[Tuple[str, str, str]] = set()  # (league, series_name, team_name)

    norm_league = normalize_league_id(league)
    league_db_id = get_league_db_id(league) or get_league_db_id(norm_league)
    if not league_db_id:
        raise RuntimeError(f"League not found in DB: {league}")

    for rec in players:
        raw_league = (rec.get("League") or "").strip()
        if not raw_league:
            continue
        this_norm = normalize_league_id(raw_league)
        if this_norm != norm_league and raw_league != league:
            continue

        series_name = (rec.get("Series") or "").strip()
        team_name = (rec.get("Series Mapping ID") or "").strip()
        club_name = (rec.get("Club") or "").strip()
        if not series_name or not team_name or not club_name:
            skipped += 1
            continue

        key = (series_name, team_name, club_name)
        if key in seen:
            continue
        seen.add(key)

        series_id = ensure_series(series_name, league_db_id)
        ensure_series_league(series_id, league_db_id)
        club_id = get_club_id_by_name(club_name)
        if not club_id:
            skipped += 1
            continue
        ensure_team(team_name, club_id, series_id, league_db_id)
        created += 1

    return {"unique_team_triplets": len(seen), "teams_processed": created, "skipped": skipped}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Bootstrap teams from players.json for a league")
    parser.add_argument("--league", required=True, help="League identifier, e.g., APTA_CHICAGO")
    args = parser.parse_args()

    stats = bootstrap(args.league)
    print("📊 Team bootstrap complete:")
    for k, v in stats.items():
        print(f" - {k}: {v}")


if __name__ == "__main__":
    main()


