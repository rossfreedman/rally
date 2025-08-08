"""
Merge/remove duplicate Division-series teams by consolidating them into the canonical Chicago-series teams.

Behavior:
- For each club within a league, if both "Chicago N" and "Division N" teams exist, prefer the
  Chicago team as canonical and re-point references to it, then delete the Division team.
- Operates safely with dry-run by default. Use --apply to execute.

Updated tables (foreign keys/refs):
- players.team_id
- match_scores.home_team_id / away_team_id
- schedule.home_team_id / away_team_id
- captain_messages.team_id
- polls.team_id

Usage:
  python scripts/cleanup_merge_division_series_teams.py --league APTA_CHICAGO --club Tennaqua --apply

If --club omitted, will process all clubs in the league.
"""

import argparse
import os
import sys
from typing import Dict, List, Tuple

# Ensure project root is importable when running this script directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database_utils import execute_query, execute_update


def find_duplicates(league_id: str, club: str = None) -> List[Dict]:
    """Find Chicago/Division duplicate pairs by club+numeric series within a league."""
    params: List = [
        league_id,
        'Chicago %', 'Division %',  # SELECT SUM(CASE ... LIKE ...)
        'Chicago %', 'Division %',  # HAVING SUM(CASE ... LIKE ...)
    ]
    club_filter = ""
    if club:
        club_filter = "AND c.name = %s"
        params.append(club)

    query = f"""
        SELECT
          c.id AS club_id,
          c.name AS club_name,
          REGEXP_REPLACE(s.name, '[^0-9]', '', 'g')::int AS series_num,
          SUM(CASE WHEN s.name LIKE %s THEN 1 ELSE 0 END) AS chicago_count,
          SUM(CASE WHEN s.name LIKE %s THEN 1 ELSE 0 END) AS division_count,
          MAX(CASE WHEN s.name LIKE %s THEN t.id END) AS chicago_team_id,
          MAX(CASE WHEN s.name LIKE %s THEN t.id END) AS division_team_id
        FROM teams t
        JOIN clubs c ON t.club_id = c.id
        JOIN series s ON t.series_id = s.id
        JOIN leagues l ON t.league_id = l.id
        WHERE l.league_id = %s {club_filter}
        GROUP BY c.id, c.name, REGEXP_REPLACE(s.name, '[^0-9]', '', 'g')
        HAVING SUM(CASE WHEN s.name LIKE %s THEN 1 ELSE 0 END) > 0
           AND SUM(CASE WHEN s.name LIKE %s THEN 1 ELSE 0 END) > 0
        ORDER BY c.name, series_num
    """
    # Add the two LIKE params used in MAX(CASE ...) right after the earlier ones
    # Our params currently: [league_id, 'Chicago %','Division %','Chicago %','Division %']
    # But in query order we used: SUM(CASE) x2, MAX(CASE) x2, league_id, HAVING SUM(CASE) x2
    # Reorder list accordingly:
    like_chi = 'Chicago %'
    like_div = 'Division %'
    ordered_params: List = [
        like_chi, like_div, like_chi, like_div,  # SELECT sums and maxes
        league_id,
        like_chi, like_div,                      # HAVING
    ]
    if club:
        ordered_params.insert(5, club)  # after league_id for WHERE ... AND c.name = %s
    return execute_query(query, ordered_params)


def reassign_refs(from_team_id: int, to_team_id: int, apply_changes: bool) -> Dict[str, int]:
    """Reassign foreign key references from one team to another across known tables."""
    stats = {"players": 0, "match_scores": 0, "schedule": 0, "captain_messages": 0, "polls": 0}

    updates = [
        ("players", "UPDATE players SET team_id = %s WHERE team_id = %s", (to_team_id, from_team_id), "players"),
        ("match_scores_home", "UPDATE match_scores SET home_team_id = %s WHERE home_team_id = %s", (to_team_id, from_team_id), "match_scores"),
        ("match_scores_away", "UPDATE match_scores SET away_team_id = %s WHERE away_team_id = %s", (to_team_id, from_team_id), "match_scores"),
        ("schedule_home", "UPDATE schedule SET home_team_id = %s WHERE home_team_id = %s", (to_team_id, from_team_id), "schedule"),
        ("schedule_away", "UPDATE schedule SET away_team_id = %s WHERE away_team_id = %s", (to_team_id, from_team_id), "schedule"),
        ("captain_messages", "UPDATE captain_messages SET team_id = %s WHERE team_id = %s", (to_team_id, from_team_id), "captain_messages"),
        ("polls", "UPDATE polls SET team_id = %s WHERE team_id = %s", (to_team_id, from_team_id), "polls"),
    ]

    for _, sql, params, bucket in updates:
        if apply_changes:
            execute_update(sql, params)
        stats[bucket] += 1  # Simple counter that an UPDATE was issued; DB will no-op if no rows

    return stats


def delete_team(team_id: int, apply_changes: bool) -> None:
    if apply_changes:
        execute_update("DELETE FROM teams WHERE id = %s", (team_id,))


def main():
    parser = argparse.ArgumentParser(description="Merge Division-series teams into Chicago-series teams")
    parser.add_argument("--league", required=True, help="League ID, e.g., APTA_CHICAGO")
    parser.add_argument("--club", help="Club name to scope cleanup, e.g., Tennaqua")
    parser.add_argument("--apply", action="store_true", help="Apply changes (otherwise dry-run)")
    args = parser.parse_args()

    duplicates = find_duplicates(args.league, args.club)
    if not duplicates:
        print("No Chicago/Division duplicates found.")
        return

    print(f"Found {len(duplicates)} duplicate series groups")
    total_stats = {"players": 0, "match_scores": 0, "schedule": 0, "captain_messages": 0, "polls": 0}

    for d in duplicates:
        chicago_id = d["chicago_team_id"]
        division_id = d["division_team_id"]
        series_num = d["series_num"]
        club_name = d["club_name"]

        if not (chicago_id and division_id):
            continue

        print(f"- {club_name} Series {series_num}: merging division team {division_id} -> chicago team {chicago_id}")
        stats = reassign_refs(division_id, chicago_id, args.apply)
        for k, v in stats.items():
            total_stats[k] += v
        delete_team(division_id, args.apply)

    print("Done.")
    print("Updates issued (per table; may be 0 changed rows if not present):")
    for k, v in total_stats.items():
        print(f"  {k}: {v}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to make changes.")


if __name__ == "__main__":
    main()


