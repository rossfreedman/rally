#!/usr/bin/env python3

from collections import defaultdict

from database_utils import execute_query


def debug_court_assignments():
    print("=== DEBUGGING COURT ASSIGNMENTS (LEAGUE FILTERED) ===")

    # Get matches on Ross's match dates
    player_id = "nndz-WlNhd3hMYi9nQT09"
    user_league_id = 3  # NSTF league ID

    # Get all matches from database (same as analysis function)
    all_matches = execute_query(
        """
        SELECT match_date, home_team, away_team, 
               home_player_1_id, home_player_2_id, 
               away_player_1_id, away_player_2_id, league_id
        FROM match_scores 
        ORDER BY match_date
    """
    )

    print(f"Found {len(all_matches)} total matches in database")

    # Filter by league (same logic as analysis function)
    league_matches = []
    for match in all_matches:
        match_league = match.get("league_id")
        if user_league_id and match_league == user_league_id:
            league_matches.append(match)

    print(f"Found {len(league_matches)} matches in NSTF league")

    # Use the same grouping logic as the fixed code
    matches_by_group = defaultdict(list)
    for match in league_matches:
        date = match["match_date"]
        # Group by date only for proper court assignment across all matches that day
        group_key = date
        matches_by_group[group_key].append(match)

    # Find max courts
    max_courts = 4
    for group_matches in matches_by_group.values():
        max_courts = max(max_courts, len(group_matches))

    print(f"Max courts detected: {max_courts}")
    print()

    # Focus on Ross's specific dates
    ross_dates = ["2025-05-29", "2025-06-05"]

    for date_key in ross_dates:
        if date_key in matches_by_group:
            day_matches = matches_by_group[date_key]
            print(f"Date: {date_key} ({len(day_matches)} NSTF league matches)")

            # Sort all matches for this group for deterministic court assignment (reverse alphabetical)
            day_matches_sorted = sorted(
                day_matches,
                key=lambda m: (m.get("home_team", ""), m.get("away_team", "")),
                reverse=True,
            )

            for i, match in enumerate(day_matches_sorted):
                court_num = i + 1

                # Check if Ross is in this match
                ross_player_ids = [
                    match["home_player_1_id"],
                    match["home_player_2_id"],
                    match["away_player_1_id"],
                    match["away_player_2_id"],
                ]

                is_ross_match = player_id in ross_player_ids
                marker = " <-- ROSS HERE!" if is_ross_match else ""

                if (
                    is_ross_match or court_num <= 5
                ):  # Show Ross matches and first 5 courts
                    print(
                        f"  Court {court_num}: {match['home_team']} vs {match['away_team']}{marker}"
                    )

            print()

    print("\n=== ANALYSIS ===")
    print(
        "Now using league-filtered matches (NSTF only) with reverse alphabetical sorting."
    )


if __name__ == "__main__":
    debug_court_assignments()
