#!/usr/bin/env python3
"""
Test script to simulate my-series page data loading
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import json
from database_utils import execute_query
from app.services.session_service import get_session_data_for_user

def test_my_series_data():
    """Test the my-series page data loading"""
    print("=== TESTING MY-SERIES PAGE DATA ===")
    
    # Get Ross's session data
    user_email = 'rossfreedman@gmail.com'
    session_data = get_session_data_for_user(user_email)
    
    print(f"1. Session data for {user_email}:")
    print(f"   - series_id: {session_data.get('series_id')}")
    print(f"   - league_id: {session_data.get('league_id')}")
    print(f"   - series: {session_data.get('series')}")
    print(f"   - team_id: {session_data.get('team_id')}")
    
    # Simulate the API query that the my-series page uses
    user_series_id = session_data.get("series_id")
    user_league_id = session_data.get("league_id")
    
    if not user_series_id or not user_league_id:
        print("❌ Missing series_id or league_id")
        return
    
    # Query series stats (same as API endpoint)
    series_stats_query = """
        SELECT 
            s.series,
            s.team,
            s.points,
            s.matches_won,
            s.matches_lost,
            s.matches_tied,
            s.lines_won,
            s.lines_lost,
            s.lines_for,
            s.lines_ret,
            s.sets_won,
            s.sets_lost,
            s.games_won,
            s.games_lost,
            l.league_id,
            t.display_name
        FROM series_stats s
        LEFT JOIN leagues l ON s.league_id = l.id
        LEFT JOIN teams t ON s.team = t.team_name AND s.league_id = t.league_id
        WHERE s.series_id = %s AND s.league_id = %s
        ORDER BY s.points DESC, s.team ASC
    """
    
    db_results = execute_query(series_stats_query, [user_series_id, user_league_id])
    
    print(f"\n2. Database query results:")
    print(f"   Found {len(db_results)} teams")
    
    # Transform to match API response format
    teams = []
    for row in db_results:
        # Calculate percentages
        total_matches = (
            row["matches_won"] + row["matches_lost"] + (row["matches_tied"] or 0)
        )
        match_percentage = (
            f"{round((row['matches_won'] / total_matches) * 100, 1)}%"
            if total_matches > 0
            else "0%"
        )

        total_lines = row["lines_won"] + row["lines_lost"]
        line_percentage = (
            f"{round((row['lines_won'] / total_lines) * 100, 1)}%"
            if total_lines > 0
            else "0%"
        )

        total_sets = row["sets_won"] + row["sets_lost"]
        set_percentage = (
            f"{round((row['sets_won'] / total_sets) * 100, 1)}%"
            if total_sets > 0
            else "0%"
        )

        total_games = row["games_won"] + row["games_lost"]
        game_percentage = (
            f"{round((row['games_won'] / total_games) * 100, 1)}%"
            if total_games > 0
            else "0%"
        )

        team_data = {
            "series": row["series"],
            "team": row["team"],
            "display_name": row.get("display_name", row["team"]),
            "league_id": row.get("league_id", user_league_id),
            "points": row["points"],
            "matches": {
                "won": row["matches_won"],
                "lost": row["matches_lost"],
                "tied": row["matches_tied"] or 0,
                "percentage": match_percentage,
            },
            "lines": {
                "won": row["lines_won"],
                "lost": row["lines_lost"],
                "for": row.get("lines_for", 0),
                "ret": row.get("lines_ret", 0),
                "percentage": line_percentage,
            },
            "sets": {
                "won": row["sets_won"],
                "lost": row["sets_lost"],
                "percentage": set_percentage,
            },
            "games": {
                "won": row["games_won"],
                "lost": row["games_lost"],
                "percentage": game_percentage,
            },
        }
        teams.append(team_data)
    
    print(f"\n3. Transformed API response:")
    print(f"   Teams count: {len(teams)}")
    
    # Show the first few teams
    for i, team in enumerate(teams[:3], 1):
        print(f"   {i}. {team['team']} - {team['points']} points ({team['matches']['won']}-{team['matches']['lost']})")
    
    # Check if Tennaqua S2B is in the data
    tennaqua_team = None
    for team in teams:
        if 'Tennaqua' in team['team']:
            tennaqua_team = team
            break
    
    if tennaqua_team:
        print(f"\n4. ✅ Tennaqua team found:")
        print(f"   - Team: {tennaqua_team['team']}")
        print(f"   - Points: {tennaqua_team['points']}")
        print(f"   - Record: {tennaqua_team['matches']['won']}-{tennaqua_team['matches']['lost']}")
        
        # Calculate position
        sorted_teams = sorted(teams, key=lambda x: x['points'], reverse=True)
        position = next((i for i, t in enumerate(sorted_teams, 1) if 'Tennaqua' in t['team']), None)
        print(f"   - Position: {position} out of {len(sorted_teams)}")
    else:
        print(f"\n4. ❌ Tennaqua team not found in data")
    
    # Simulate what the JavaScript would receive
    api_response = {"teams": teams, "pointsProgression": {}}
    print(f"\n5. Full API response structure:")
    print(f"   - Has 'teams' key: {'teams' in api_response}")
    print(f"   - Teams is array: {isinstance(api_response['teams'], list)}")
    print(f"   - Teams length: {len(api_response['teams'])}")
    
    return api_response

if __name__ == "__main__":
    test_my_series_data() 