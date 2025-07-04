#!/usr/bin/env python3
"""
Regenerate series_stats table from actual match_scores data

This script calculates team statistics directly from match results
and updates the series_stats table with accurate data including proper points calculation.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from collections import defaultdict

from database_utils import execute_query, execute_query_one


def calculate_team_stats_from_matches():
    """Calculate team statistics from match_scores table"""
    print("🔄 Calculating team statistics from match_scores data...")

    # Get all matches
    matches_query = """
        SELECT 
            home_team, away_team, winner, scores, league_id,
            home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
        FROM match_scores
        WHERE home_team IS NOT NULL AND away_team IS NOT NULL
        ORDER BY home_team, away_team
    """
    matches = execute_query(matches_query)

    print(f"   Found {len(matches)} total matches")

    # Initialize team stats
    team_stats = defaultdict(
        lambda: {
            "league_id": None,
            "matches_won": 0,
            "matches_lost": 0,
            "matches_tied": 0,
            "lines_won": 0,
            "lines_lost": 0,
            "sets_won": 0,
            "sets_lost": 0,
            "games_won": 0,
            "games_lost": 0,
            "points": 0,
        }
    )

    for match in matches:
        home_team = match["home_team"]
        away_team = match["away_team"]
        winner = match.get("winner", "").lower() if match.get("winner") else ""
        scores = match.get("scores", "")
        league_id = match["league_id"]

        # Set league_id for teams
        team_stats[home_team]["league_id"] = league_id
        team_stats[away_team]["league_id"] = league_id

        # Parse scores to count sets and games
        home_sets = 0
        away_sets = 0
        home_games = 0
        away_games = 0

        if scores:
            # Parse scores like "6-1, 6-0" or "5-7, 6-3, 6-1"
            set_scores = [s.strip() for s in scores.split(",")]
            for set_score in set_scores:
                # Handle tiebreak scores like "6-7 [1-7]"
                if "[" in set_score:
                    set_score = set_score.split("[")[0].strip()

                if "-" in set_score:
                    try:
                        parts = set_score.split("-")
                        if len(parts) == 2:
                            h_games = int(parts[0].strip())
                            a_games = int(parts[1].strip())

                            home_games += h_games
                            away_games += a_games

                            # Determine set winner
                            if h_games > a_games:
                                home_sets += 1
                            else:
                                away_sets += 1
                    except (ValueError, IndexError):
                        pass

        # Update set and game stats
        team_stats[home_team]["sets_won"] += home_sets
        team_stats[home_team]["sets_lost"] += away_sets
        team_stats[home_team]["games_won"] += home_games
        team_stats[home_team]["games_lost"] += away_games

        team_stats[away_team]["sets_won"] += away_sets
        team_stats[away_team]["sets_lost"] += home_sets
        team_stats[away_team]["games_won"] += away_games
        team_stats[away_team]["games_lost"] += home_games

        # Count lines (each match = 1 line)
        team_stats[home_team]["lines_won"] += 1 if winner == "home" else 0
        team_stats[home_team]["lines_lost"] += 1 if winner == "away" else 0

        team_stats[away_team]["lines_won"] += 1 if winner == "away" else 0
        team_stats[away_team]["lines_lost"] += 1 if winner == "home" else 0

        # Count matches (need to aggregate by date and teams to avoid double counting)
        # For now, we'll handle this in a second pass

    # Second pass: count team matches (not individual lines)
    print("   Calculating team match results...")

    team_matches_query = """
        SELECT 
            home_team, away_team, match_date, 
            COUNT(*) as total_lines,
            SUM(CASE WHEN winner = 'home' THEN 1 ELSE 0 END) as home_lines_won,
            SUM(CASE WHEN winner = 'away' THEN 1 ELSE 0 END) as away_lines_won,
            league_id
        FROM match_scores
        WHERE home_team IS NOT NULL AND away_team IS NOT NULL
        AND winner IN ('home', 'away')
        GROUP BY home_team, away_team, match_date, league_id
        ORDER BY match_date, home_team, away_team
    """

    team_matches = execute_query(team_matches_query)

    # Reset match counts for proper calculation
    for team in team_stats:
        team_stats[team]["matches_won"] = 0
        team_stats[team]["matches_lost"] = 0
        team_stats[team]["matches_tied"] = 0

    for team_match in team_matches:
        home_team = team_match["home_team"]
        away_team = team_match["away_team"]
        home_lines = team_match["home_lines_won"]
        away_lines = team_match["away_lines_won"]
        total_lines = team_match["total_lines"]

        # Determine team match winner (majority of lines)
        if home_lines > away_lines:
            team_stats[home_team]["matches_won"] += 1
            team_stats[away_team]["matches_lost"] += 1
        elif away_lines > home_lines:
            team_stats[away_team]["matches_won"] += 1
            team_stats[home_team]["matches_lost"] += 1
        else:
            team_stats[home_team]["matches_tied"] += 1
            team_stats[away_team]["matches_tied"] += 1

    # Calculate points (1 point per match win)
    for team in team_stats:
        team_stats[team]["points"] = team_stats[team]["matches_won"]

    print(f"   Calculated stats for {len(team_stats)} teams")
    return team_stats


def get_team_series_mapping():
    """Get mapping of team names to series"""
    print("📋 Getting team to series mapping...")

    # First try from teams table
    teams_query = """
        SELECT t.team_name, s.name as series_name, l.id as league_id
        FROM teams t
        JOIN series s ON t.series_id = s.id  
        JOIN leagues l ON t.league_id = l.id
    """
    teams = execute_query(teams_query)

    team_series_map = {}
    for team in teams:
        team_series_map[team["team_name"]] = {
            "series": team["series_name"],
            "league_id": team["league_id"],
        }

    print(f"   Found series mapping for {len(team_series_map)} teams")
    return team_series_map


def update_series_stats_table(team_stats, team_series_map):
    """Update the series_stats table with calculated data"""
    print("💾 Updating series_stats table...")

    # Clear existing data
    execute_query("DELETE FROM series_stats")
    print("   Cleared existing series_stats data")

    updated_count = 0

    for team_name, stats in team_stats.items():
        # Get series information
        series_info = team_series_map.get(team_name)
        if not series_info:
            print(f"   ⚠️  No series mapping found for team: {team_name}")
            continue

        series_name = series_info["series"]
        league_id = series_info["league_id"]

        # Get team_id from teams table
        team_id_query = """
            SELECT t.id FROM teams t
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            WHERE t.team_name = %s AND s.name = %s AND l.id = %s
        """
        team_row = execute_query_one(team_id_query, [team_name, series_name, league_id])
        team_id = team_row["id"] if team_row else None

        # Get series_id from series table
        series_id_query = """
            SELECT s.id FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            WHERE s.name = %s AND sl.league_id = %s
        """
        series_row = execute_query_one(series_id_query, [series_name, league_id])
        series_id = series_row["id"] if series_row else None

        # Insert new record
        insert_query = """
            INSERT INTO series_stats (
                series, team, series_id, team_id, points, 
                matches_won, matches_lost, matches_tied,
                lines_won, lines_lost, lines_for, lines_ret,
                sets_won, sets_lost, games_won, games_lost,
                league_id, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """

        execute_query(
            insert_query,
            [
                series_name,
                team_name,
                series_id,
                team_id,
                stats["points"],
                stats["matches_won"],
                stats["matches_lost"],
                stats["matches_tied"],
                stats["lines_won"],
                stats["lines_lost"],
                0,
                0,  # lines_for, lines_ret
                stats["sets_won"],
                stats["sets_lost"],
                stats["games_won"],
                stats["games_lost"],
                league_id,
            ],
        )

        updated_count += 1

    print(f"   ✅ Updated {updated_count} team records in series_stats")


def verify_tennaqua_12():
    """Verify Tennaqua 12 has correct data"""
    print("🔍 Verifying Tennaqua 12 data...")

    tennaqua_stats = execute_query_one(
        """
        SELECT 
            series, team, points, matches_won, matches_lost,
            lines_won, lines_lost, sets_won, sets_lost, games_won, games_lost
        FROM series_stats
        WHERE team = %s
    """,
        ["Tennaqua 12"],
    )

    if tennaqua_stats:
        print("   ✅ Tennaqua 12 stats updated:")
        print(f"      Series: {tennaqua_stats['series']}")
        print(f"      Points: {tennaqua_stats['points']}")
        print(
            f"      Matches: {tennaqua_stats['matches_won']}-{tennaqua_stats['matches_lost']}"
        )
        print(
            f"      Lines: {tennaqua_stats['lines_won']}-{tennaqua_stats['lines_lost']}"
        )
        print(f"      Sets: {tennaqua_stats['sets_won']}-{tennaqua_stats['sets_lost']}")
        print(
            f"      Games: {tennaqua_stats['games_won']}-{tennaqua_stats['games_lost']}"
        )
    else:
        print("   ❌ Tennaqua 12 not found in updated series_stats")


def main():
    """Main execution"""
    print("🚀 Starting series_stats regeneration...")
    print("=" * 60)

    try:
        # Step 1: Calculate team statistics from match data
        team_stats = calculate_team_stats_from_matches()

        # Step 2: Get team to series mapping
        team_series_map = get_team_series_mapping()

        # Step 3: Update series_stats table
        update_series_stats_table(team_stats, team_series_map)

        # Step 4: Verify specific team
        verify_tennaqua_12()

        print("\n✅ Series stats regeneration completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Error during regeneration: {str(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
