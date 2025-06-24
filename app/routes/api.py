import json
from pathlib import Path

from flask import Blueprint, current_app, jsonify

api = Blueprint("api", __name__)


@api.route("/api/match-history", methods=["GET"])
def get_match_history():
    """Get match history from database - FIXED: Uses database instead of JSON"""
    try:
        from database_utils import execute_query
        
        # FIXED: Get matches from database instead of JSON
        matches_query = """
            SELECT 
                TO_CHAR(match_date, 'YYYY-MM-DD') as date,
                home_team,
                away_team,
                home_player_1_id,
                home_player_2_id,
                away_player_1_id,
                away_player_2_id,
                winner,
                scores,
                l.league_id
            FROM match_scores ms
            JOIN leagues l ON ms.league_id = l.id
            ORDER BY match_date DESC, ms.id DESC
        """
        
        matches = execute_query(matches_query)
        
        # Format to match expected JSON structure
        formatted_matches = []
        for match in matches:
            formatted_matches.append({
                "Date": match["date"],
                "Home Team": match["home_team"],
                "Away Team": match["away_team"], 
                "Home Player 1": match["home_player_1_id"],
                "Home Player 2": match["home_player_2_id"],
                "Away Player 1": match["away_player_1_id"],
                "Away Player 2": match["away_player_2_id"],
                "Winner": match["winner"],
                "Scores": match["scores"],
                "league_id": match["league_id"]
            })
        
        return jsonify(formatted_matches)
    except Exception as e:
        current_app.logger.error(f"Error loading match history from database: {str(e)}")
        return jsonify({"error": str(e)}), 500
