#!/usr/bin/env python3
"""
Fix all team points in series_stats table by recalculating from match history

⚠️  ONE-TIME FIX SCRIPT: This addresses historical data with incorrect points.
⚠️  ROOT CAUSE FIXED: ETL process now calculates points correctly during import.

This script recalculates points based on actual match performance:
- 1 point per match win
- Additional points for sets won in losing matches
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update


def calculate_team_points(team_name, league_id):
    """Calculate correct points for a team based on match history"""

    # Get all matches for this team
    matches = execute_query(
        """
        SELECT match_date, home_team, away_team, winner, scores
        FROM match_scores
        WHERE (home_team = %s OR away_team = %s)
        AND league_id = %s
        ORDER BY match_date
    """,
        [team_name, team_name, league_id],
    )

    if not matches:
        return 0

    total_points = 0

    for match in matches:
        is_home = match["home_team"] == team_name
        won_match = (is_home and match["winner"] == "home") or (
            not is_home and match["winner"] == "away"
        )

        # 1 point for winning the match
        if won_match:
            total_points += 1

        # Additional points for sets won (even in losing matches)
        scores = match["scores"].split(", ") if match["scores"] else []
        for score_str in scores:
            if "-" in score_str:
                try:
                    # Extract just the numbers before any tiebreak info
                    clean_score = score_str.split("[")[0].strip()
                    our_score, their_score = map(int, clean_score.split("-"))
                    if not is_home:  # Flip scores if we're away team
                        our_score, their_score = their_score, our_score
                    if our_score > their_score:
                        total_points += 1
                except (ValueError, IndexError):
                    continue

    return total_points


def fix_all_team_points():
    """Fix points for all teams with incorrect calculations"""

    print("🔧 Recalculating points for all teams with 0 points but match wins...")
    print("=" * 70)

    # Get all teams with 0 points but match wins > 0
    problematic_teams = execute_query(
        """
        SELECT team, points, matches_won, matches_lost, series, league_id, id
        FROM series_stats
        WHERE points = 0 AND matches_won > 0
        ORDER BY matches_won DESC
    """
    )

    if not problematic_teams:
        print("✅ No teams found with incorrect points")
        return

    print(f"Found {len(problematic_teams)} teams to fix:")

    updated_count = 0

    for team_data in problematic_teams:
        team_name = team_data["team"]
        league_id = team_data["league_id"]
        current_points = team_data["points"]
        record = f"{team_data['matches_won']}-{team_data['matches_lost']}"

        print(f"\n📊 {team_name} ({team_data['series']}) - {record} record")
        print(f"   Current points: {current_points}")

        # Calculate correct points
        correct_points = calculate_team_points(team_name, league_id)
        print(f"   Calculated points: {correct_points}")

        if correct_points != current_points:
            # Update the points
            success = execute_update(
                """
                UPDATE series_stats 
                SET points = %s
                WHERE id = %s
            """,
                [correct_points, team_data["id"]],
            )

            if success:
                print(f"   ✅ Updated to {correct_points} points")
                updated_count += 1
            else:
                print(f"   ❌ Failed to update")
        else:
            print(f"   ✅ Points already correct")

    print("\n" + "=" * 70)
    print(f"✅ Fixed {updated_count} teams")
    print("Points recalculation complete!")


if __name__ == "__main__":
    fix_all_team_points()
