"""
API Routes Blueprint

This module contains all API routes that were moved from the main server.py file.
These routes handle API endpoints for data retrieval, research, analytics, and other backend operations.
"""

import json
import logging
import os
from datetime import datetime
from functools import wraps

import pytz
from flask import Blueprint, g, jsonify, request, session

from app.models.database_models import Player, SessionLocal, User, UserPlayerAssociation
from app.services.api_service import *
from app.services.dashboard_service import log_user_action
from app.services.mobile_service import get_club_players_data
from database_utils import execute_query, execute_query_one, execute_update
from utils.database_player_lookup import find_player_by_database_lookup
from utils.logging import log_user_activity

api_bp = Blueprint("api", __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated_function


def convert_chicago_to_series_for_ui(series_name):
    """
    Convert "Chicago X" format to "Series X" format for APTA league UI display.
    Examples: "Chicago 1" -> "Series 1", "Chicago 21 SW" -> "Series 21 SW"
    """
    import re
    
    # Handle "Chicago X" format (with optional suffix like "SW")
    match = re.match(r'^Chicago\s+(\d+)([a-zA-Z\s]*)$', series_name)
    if match:
        number = match.group(1)
        suffix = match.group(2).strip() if match.group(2) else ''
        
        if suffix:
            return f"Series {number} {suffix}"
        else:
            return f"Series {number}"
    
    # Return unchanged if not in "Chicago X" format
    return series_name


@api_bp.route("/api/series-stats")
@login_required
def get_series_stats():
    """Get series statistics"""
    return get_series_stats_data()


@api_bp.route("/api/test-log", methods=["GET"])
@login_required
def test_log():
    """Test log endpoint"""
    return test_log_data()


@api_bp.route("/api/verify-logging")
@login_required
def verify_logging():
    """Verify logging"""
    return verify_logging_data()


@api_bp.route("/api/log-click", methods=["POST"])
def log_click():
    """Log click events"""
    return log_click_data()


@api_bp.route("/api/research-team")
@login_required
def research_team():
    """Research team data"""
    return research_team_data()


@api_bp.route("/api/player-court-stats/<player_name>")
def player_court_stats(player_name):
    """Get player court statistics"""
    return get_player_court_stats_data(player_name)


@api_bp.route("/api/research-my-team")
@login_required
def research_my_team():
    """Research my team data"""
    return research_my_team_data()


@api_bp.route("/api/research-me")
@login_required
def research_me():
    """Research me data"""
    return research_me_data()


@api_bp.route("/api/win-streaks")
@login_required
def get_win_streaks():
    """Get win streaks"""
    return get_win_streaks_data()


@api_bp.route("/api/player-streaks")
def get_player_streaks():
    """Get player streaks"""
    return get_player_streaks_data()


@api_bp.route("/api/enhanced-streaks")
@login_required
def get_enhanced_streaks():
    """Get enhanced streaks"""
    return get_enhanced_streaks_data()


@api_bp.route("/api/last-3-matches")
@login_required
def get_last_3_matches():
    """Get the last 3 matches for the current user"""
    try:
        user = session["user"]
        player_id = user.get("tenniscores_player_id")

        if not player_id:
            return jsonify({"error": "Player ID not found"}), 404

        # Get user's league for filtering
        user_league_id = user.get("league_id", "")

        # Convert league_id to integer if it's a string
        league_id_int = None
        if user_league_id and str(user_league_id).isdigit():
            league_id_int = int(user_league_id)

        # Query the last 3 matches for this player
        if league_id_int:
            matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    match_date,
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC
                LIMIT 3
            """
            matches = execute_query(
                matches_query,
                [player_id, player_id, player_id, player_id, league_id_int],
            )
        else:
            matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    match_date,
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                ORDER BY match_date DESC
                LIMIT 3
            """
            matches = execute_query(
                matches_query, [player_id, player_id, player_id, player_id]
            )

        if not matches:
            return jsonify({"matches": [], "message": "No recent matches found"})

        # Helper function to get player name from ID
        def get_player_name(player_id):
            if not player_id:
                return None
            try:
                if league_id_int:
                    name_query = """
                        SELECT first_name, last_name FROM players 
                        WHERE tenniscores_player_id = %s AND league_id = %s
                    """
                    player_record = execute_query_one(
                        name_query, [player_id, league_id_int]
                    )
                else:
                    name_query = """
                        SELECT first_name, last_name FROM players 
                        WHERE tenniscores_player_id = %s
                    """
                    player_record = execute_query_one(name_query, [player_id])

                if player_record:
                    return f"{player_record['first_name']} {player_record['last_name']}"
                else:
                    return f"Player {player_id[:8]}..."
            except Exception:
                return f"Player {player_id[:8]}..."

        # Process matches to add readable information
        processed_matches = []
        for match in matches:
            is_home = player_id in [
                match.get("Home Player 1"),
                match.get("Home Player 2"),
            ]
            winner = match.get("Winner", "").lower()

            # Determine if player won
            player_won = (is_home and winner == "home") or (
                not is_home and winner == "away"
            )

            # Get partner name
            if is_home:
                partner_id = (
                    match.get("Home Player 2")
                    if match.get("Home Player 1") == player_id
                    else match.get("Home Player 1")
                )
            else:
                partner_id = (
                    match.get("Away Player 2")
                    if match.get("Away Player 1") == player_id
                    else match.get("Away Player 1")
                )

            partner_name = get_player_name(partner_id) if partner_id else "No Partner"

            # Get opponent names
            if is_home:
                opponent1_id = match.get("Away Player 1")
                opponent2_id = match.get("Away Player 2")
            else:
                opponent1_id = match.get("Home Player 1")
                opponent2_id = match.get("Home Player 2")

            opponent1_name = (
                get_player_name(opponent1_id) if opponent1_id else "Unknown"
            )
            opponent2_name = (
                get_player_name(opponent2_id) if opponent2_id else "Unknown"
            )

            # Format scores so logged-in player's team score comes first
            def format_scores_for_player_team(raw_scores, player_was_home):
                """Format scores so the logged-in player's team score appears first in each set"""
                if not raw_scores:
                    return raw_scores
                
                try:
                    # Split by sets (comma-separated)
                    sets = raw_scores.split(", ")
                    formatted_sets = []
                    
                    for set_score in sets:
                        if "-" not in set_score:
                            formatted_sets.append(set_score)
                            continue
                            
                        # Split individual set score
                        scores = set_score.split("-")
                        if len(scores) != 2:
                            formatted_sets.append(set_score)
                            continue
                            
                        try:
                            home_score = int(scores[0])
                            away_score = int(scores[1])
                            
                            # Always show the logged-in player's team score first
                            if player_was_home:
                                # Player was home - show home score first (already correct)
                                formatted_sets.append(f"{home_score}-{away_score}")
                            else:
                                # Player was away - show away score first
                                formatted_sets.append(f"{away_score}-{home_score}")
                        except (ValueError, IndexError):
                            # If we can't parse scores, keep original
                            formatted_sets.append(set_score)
                    
                    return ", ".join(formatted_sets)
                    
                except Exception:
                    # If anything goes wrong, return original scores
                    return raw_scores

            formatted_scores = format_scores_for_player_team(
                match.get("Scores"), is_home
            )

            processed_match = {
                "date": match.get("Date"),
                "home_team": match.get("Home Team"),
                "away_team": match.get("Away Team"),
                "scores": formatted_scores,
                "player_was_home": is_home,
                "player_won": player_won,
                "partner_name": partner_name,
                "opponent1_name": opponent1_name,
                "opponent2_name": opponent2_name,
                "match_result": "Won" if player_won else "Lost",
            }
            processed_matches.append(processed_match)

        return jsonify(
            {"matches": processed_matches, "total_matches": len(processed_matches)}
        )

    except Exception as e:
        print(f"Error getting last 3 matches: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to retrieve matches"}), 500


@api_bp.route("/api/team-last-3-matches")
@login_required
def get_team_last_3_matches():
    """Get the last 3 matches for the current user's team using team_id"""
    try:
        user = session["user"]

        # Get user's team information
        user_club = user.get("club", "")
        user_series = user.get("series", "")
        user_league_id = user.get("league_id", "")

        if not user_club or not user_series:
            return jsonify({"error": "Team information not found"}), 404

        # Convert league_id to integer foreign key for database queries
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
                else:
                    return jsonify({"error": "League not found"}), 404
            except Exception as e:
                return jsonify({"error": "Failed to resolve league"}), 500
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id

        # Get the user's team_id using proper joins
        team_query = """
            SELECT t.id, t.team_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            WHERE c.name = %s 
            AND s.name = %s 
            AND l.id = %s
        """

        team_record = execute_query_one(
            team_query, [user_club, user_series, league_id_int]
        )

        if not team_record:
            return (
                jsonify(
                    {
                        "error": "Team not found in database",
                        "club": user_club,
                        "series": user_series,
                    }
                ),
                404,
            )

        team_id = team_record["id"]
        team_name = team_record["team_name"]

        # Query the last 3 TEAM matches (not individual player matches)
        # Group by date and teams to get unique team match dates
        team_matches_query = """
            WITH team_match_dates AS (
                SELECT DISTINCT 
                    match_date,
                    home_team,
                    away_team
                FROM match_scores
                WHERE (home_team_id = %s OR away_team_id = %s)
                ORDER BY match_date DESC
                LIMIT 3
            )
            SELECT 
                TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                ms.match_date,
                ms.home_team as "Home Team",
                ms.away_team as "Away Team",
                ms.winner as "Winner",
                ms.scores as "Scores",
                ms.home_player_1_id as "Home Player 1",
                ms.home_player_2_id as "Home Player 2",
                ms.away_player_1_id as "Away Player 1",
                ms.away_player_2_id as "Away Player 2"
            FROM match_scores ms
            INNER JOIN team_match_dates tmd ON (
                ms.match_date = tmd.match_date 
                AND ms.home_team = tmd.home_team 
                AND ms.away_team = tmd.away_team
            )
            WHERE (ms.home_team_id = %s OR ms.away_team_id = %s)
            ORDER BY ms.match_date DESC, ms.id
        """
        matches = execute_query(team_matches_query, [team_id, team_id, team_id, team_id])

        if not matches:
            return jsonify(
                {
                    "matches": [],
                    "message": "No recent team matches found",
                    "team_name": team_name,
                    "team_id": team_id,
                }
            )

        # Helper function to get player name from ID
        def get_player_name(player_id):
            if not player_id:
                return None
            try:
                if league_id_int:
                    name_query = """
                        SELECT first_name, last_name FROM players 
                        WHERE tenniscores_player_id = %s AND league_id = %s
                    """
                    player_record = execute_query_one(
                        name_query, [player_id, league_id_int]
                    )
                else:
                    name_query = """
                        SELECT first_name, last_name FROM players 
                        WHERE tenniscores_player_id = %s
                    """
                    player_record = execute_query_one(name_query, [player_id])

                if player_record:
                    return f"{player_record['first_name']} {player_record['last_name']}"
                else:
                    return f"Player {player_id[:8]}..."
            except Exception:
                return f"Player {player_id[:8]}..."

        # Group matches by team match (date + teams) and process
        from collections import defaultdict
        team_matches_grouped = defaultdict(list)
        
        # Group individual player matches by team match
        for match in matches:
            match_key = (match.get("Date"), match.get("Home Team"), match.get("Away Team"))
            team_matches_grouped[match_key].append(match)

        processed_matches = []
        
        # Process each team match
        for (date, home_team, away_team), individual_matches in team_matches_grouped.items():
            is_home = home_team == team_name
            opponent_team = away_team if is_home else home_team
            
            # Calculate team points based on sets won + match bonus
            our_team_points = 0
            opponent_team_points = 0
            
            # Collect all players for display
            our_players = set()
            opponent_players = set()
            
            for match in individual_matches:
                winner = match.get("Winner", "").lower()
                scores = match.get("Scores", "")
                
                # Determine which team won this individual match
                individual_team_won = (is_home and winner == "home") or (not is_home and winner == "away")
                
                # Calculate points from sets
                match_our_points = 0
                match_opponent_points = 0
                
                if scores:
                    # Parse set scores (format: "6-4, 4-6, 6-3" or similar)
                    sets = [s.strip() for s in scores.split(',')]
                    
                    for set_score in sets:
                        if '-' in set_score:
                            try:
                                # Remove any extra formatting like tiebreak scores [7-5]
                                clean_score = set_score.split('[')[0].strip()
                                home_score, away_score = map(int, clean_score.split('-'))
                                
                                # Award point for set win
                                if home_score > away_score:
                                    # Home team won this set
                                    if is_home:
                                        match_our_points += 1
                                    else:
                                        match_opponent_points += 1
                                elif away_score > home_score:
                                    # Away team won this set
                                    if is_home:
                                        match_opponent_points += 1
                                    else:
                                        match_our_points += 1
                            except (ValueError, IndexError):
                                # If we can't parse the score, skip it
                                continue
                
                # Add bonus point for winning the match
                if individual_team_won:
                    match_our_points += 1
                else:
                    match_opponent_points += 1
                
                # Add to team totals
                our_team_points += match_our_points
                opponent_team_points += match_opponent_points
                
                # Collect player names
                if is_home:
                    our_player1_id = match.get("Home Player 1")
                    our_player2_id = match.get("Home Player 2")
                    opponent_player1_id = match.get("Away Player 1")
                    opponent_player2_id = match.get("Away Player 2")
                else:
                    our_player1_id = match.get("Away Player 1")
                    our_player2_id = match.get("Away Player 2")
                    opponent_player1_id = match.get("Home Player 1")
                    opponent_player2_id = match.get("Home Player 2")
                
                # Add player names (avoid duplicates)
                if our_player1_id:
                    our_players.add(get_player_name(our_player1_id) or "Unknown")
                if our_player2_id:
                    our_players.add(get_player_name(our_player2_id) or "Unknown")
                if opponent_player1_id:
                    opponent_players.add(get_player_name(opponent_player1_id) or "Unknown")
                if opponent_player2_id:
                    opponent_players.add(get_player_name(opponent_player2_id) or "Unknown")
            
            # Determine team match result based on total points
            team_won = our_team_points > opponent_team_points
            
            # Format player lists for display
            our_players_list = sorted(list(our_players))
            opponent_players_list = sorted(list(opponent_players))
            
            # Use first two players for the main display
            our_player1_name = our_players_list[0] if our_players_list else "Unknown"
            our_player2_name = our_players_list[1] if len(our_players_list) > 1 else "Unknown"
            opponent_player1_name = opponent_players_list[0] if opponent_players_list else "Unknown"
            opponent_player2_name = opponent_players_list[1] if len(opponent_players_list) > 1 else "Unknown"
            
            # Create team match summary with proper paddle tennis scoring
            team_score_summary = f"{our_team_points}-{opponent_team_points}"
            
            processed_match = {
                "date": date,
                "home_team": home_team,
                "away_team": away_team,
                "scores": team_score_summary,  # Show team points like "15-12"
                "team_was_home": is_home,
                "team_won": team_won,
                "our_player1_name": our_player1_name,
                "our_player2_name": our_player2_name,
                "opponent_team": opponent_team,
                "opponent_player1_name": opponent_player1_name,
                "opponent_player2_name": opponent_player2_name,
                "match_result": "Won" if team_won else "Lost",
                "individual_matches_count": len(individual_matches),
                "our_team_points": our_team_points,
                "opponent_team_points": opponent_team_points
            }
            processed_matches.append(processed_match)

        return jsonify(
            {
                "matches": processed_matches,
                "total_matches": len(processed_matches),
                "team_name": team_name,
                "team_id": team_id,
            }
        )

    except Exception as e:
        print(f"Error getting team's last 3 matches: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to retrieve team matches"}), 500


@api_bp.route("/api/find-training-video", methods=["POST"])
def find_training_video():
    """Find training video"""
    return find_training_video_data()


# COMMENTED OUT: Using enhanced OpenAI Assistant from rally_ai.py instead
# @api_bp.route('/api/chat', methods=['POST'])
# @login_required
# def handle_chat():
#     """Handle chat requests for Coach Rally on mobile improve page"""
#     try:
#         data = request.get_json()
#         if not data:
#             return jsonify({'error': 'No data provided'}), 400
#
#         message = data.get('message', '').strip()
#         thread_id = data.get('thread_id')
#
#         if not message:
#             return jsonify({'error': 'Message is required'}), 400
#
#         print(f"[CHAT] User: {session.get('user', {}).get('email', 'unknown')} | Message: {message[:50]}...")
#
#         # Generate thread ID if not provided
#         if not thread_id:
#             import uuid
#             thread_id = str(uuid.uuid4())
#
#         # Load training guide for context-aware responses
#         response_text = generate_chat_response(message)
#
#         return jsonify({
#             'response': response_text,
#             'thread_id': thread_id
#         })
#
#     except Exception as e:
#         print(f"Error in chat handler: {str(e)}")
#         return jsonify({'error': 'Sorry, there was an error processing your request. Please try again.'}), 500


def generate_chat_response(message):
    """Generate a helpful response to user's paddle tennis question"""
    try:
        import json
        import os
        import random

        message_lower = message.lower()

        # Load training guide for detailed responses
        try:
            guide_path = os.path.join(
                "data",
                "leagues",
                "apta",
                "improve_data",
                "complete_platform_tennis_training_guide.json",
            )
            with open(guide_path, "r", encoding="utf-8") as f:
                training_guide = json.load(f)
        except Exception:
            training_guide = {}

        # Define response patterns based on common queries
        if any(word in message_lower for word in ["serve", "serving"]):
            return generate_serve_response(training_guide)
        elif any(word in message_lower for word in ["volley", "net", "net play"]):
            return generate_volley_response(training_guide)
        elif any(word in message_lower for word in ["return", "returning"]):
            return generate_return_response(training_guide)
        elif any(word in message_lower for word in ["blitz", "blitzing", "attack"]):
            return generate_blitz_response(training_guide)
        elif any(word in message_lower for word in ["lob", "lobbing", "overhead"]):
            return generate_lob_response(training_guide)
        elif any(
            word in message_lower for word in ["strategy", "tactics", "positioning"]
        ):
            return generate_strategy_response(training_guide)
        elif any(
            word in message_lower for word in ["footwork", "movement", "court position"]
        ):
            return generate_footwork_response(training_guide)
        elif any(
            word in message_lower
            for word in ["practice", "drill", "improve", "training"]
        ):
            return generate_practice_response(training_guide)
        elif any(
            word in message_lower for word in ["beginner", "start", "new", "basics"]
        ):
            return generate_beginner_response(training_guide)
        else:
            return generate_general_response(message, training_guide)

    except Exception as e:
        print(f"Error generating chat response: {str(e)}")
        return "I'm here to help you improve your paddle tennis game! Try asking me about serves, volleys, strategy, or any specific technique you'd like to work on."


def generate_serve_response(training_guide):
    """Generate response about serving"""
    serve_data = training_guide.get("Serve technique and consistency", {})
    tips = [
        "**Serve Fundamentals:**",
        "• Keep your toss consistent - aim for the same spot every time",
        "• Use a continental grip for better control and spin options",
        "• Follow through towards your target after contact",
        "• Practice hitting to different areas of the service box",
    ]

    if serve_data.get("Coach's Cues"):
        tips.extend([f"• {cue}" for cue in serve_data["Coach's Cues"][:2]])

    tips.append("\nWhat specific aspect of your serve would you like to work on?")
    return "\n".join(tips)


def generate_volley_response(training_guide):
    """Generate response about volleys"""
    return """**Volley Mastery:**

• **Ready Position:** Stay on your toes with paddle up and ready
• **Short Backswing:** Keep your swing compact - punch, don't swing
• **Move Forward:** Step into the volley whenever possible
• **Watch the Ball:** Keep your eye on the ball through contact
• **Firm Wrist:** Maintain a stable wrist at contact

**Common Mistakes to Avoid:**
• Taking the paddle back too far
• Letting the ball drop too low before contact
• Being too passive - attack short balls!

Would you like specific drills to improve your volleys?"""


def generate_return_response(training_guide):
    """Generate response about returns"""
    return """**Return Strategy:**

**1. Positioning:**
• Stand about 2-3 feet behind the baseline
• Split step as your opponent contacts the serve
• Be ready to move in any direction

**2. Return Goals:**
• **Deep Returns:** Push your opponents back
• **Low Returns:** Keep the ball below net level when possible
• **Placement:** Aim for the corners or right at their feet

**3. Mental Approach:**
• Stay aggressive but controlled
• Look for opportunities to take the net
• Mix up your return patterns

What type of serves are giving you the most trouble?"""


def generate_blitz_response(training_guide):
    """Generate response about blitzing"""
    return """**Blitzing Strategy:**

**When to Blitz:**
• When your opponents hit a weak shot
• Against players who struggle under pressure
• When you have good court position

**Execution:**
• **Move Together:** Both players advance as a unit
• **Stay Low:** Keep your paddle ready and knees bent
• **Communicate:** Call out who takes which shots
• **Be Patient:** Wait for the right opportunity to finish

**Key Tips:**
• Don't blitz every point - pick your spots
• Watch for lobs and be ready to retreat
• Aim for their feet or open court

Ready to practice some blitzing drills?"""


def generate_lob_response(training_guide):
    """Generate response about lobs"""
    return """**Effective Lobbing:**

**Defensive Lobs:**
• Use when under pressure at the net
• Aim high and deep to buy time
• Get good height to clear opponents

**Offensive Lobs:**
• Use when opponents are crowding the net
• Lower trajectory but still over their reach
• Aim for the corners

**Overhead Response:**
• If you hit a short lob, get ready to defend
• Move back and prepare for the overhead
• Sometimes it's better to concede the point than get hurt

**Practice Tip:** Work on lobbing from different court positions!

What situation are you finding most challenging with lobs?"""


def generate_strategy_response(training_guide):
    """Generate response about strategy"""
    return """**Platform Tennis Strategy:**

**Court Positioning:**
• **Offense:** Both players at net when possible
• **Defense:** One up, one back or both back
• **Transition:** Move as a unit

**Shot Selection:**
• **High Percentage:** Aim for bigger targets when under pressure
• **Patience:** Wait for your opportunity to attack
• **Placement:** Use the entire court - corners, angles, and feet

**Communication:**
• Call "mine" or "yours" clearly
• Discuss strategy between points
• Support your partner

**Adapting to Opponents:**
• Identify their weaknesses early
• Exploit what's working
• Stay flexible with your game plan

What type of opponents are you struggling against most?"""


def generate_footwork_response(training_guide):
    """Generate response about footwork"""
    return """**Footwork Fundamentals:**

**Ready Position:**
• Stay on balls of your feet
• Slight bend in knees
• Weight slightly forward

**Movement Patterns:**
• **Split Step:** As opponent contacts ball
• **First Step:** Explosive first step toward the ball
• **Recovery:** Return to ready position after each shot

**Court Coverage:**
• Move as a unit with your partner
• Communicate to avoid collisions
• Practice specific movement patterns

**Balance Tips:**
• Keep your center of gravity low
• Don't cross your feet when moving sideways
• Practice stopping and starting quickly

Would you like some specific footwork drills to practice?"""


def generate_practice_response(training_guide):
    """Generate response about practice"""
    return """**Effective Practice Tips:**

**Warm-Up Routine:**
• 5-10 minutes of easy hitting
• Work on basic strokes: forehand, backhand, volleys
• Practice serves and returns

**Skill Development:**
• Focus on one technique at a time
• Repeat movements until they feel natural
• Get feedback from experienced players

**Match Simulation:**
• Practice point patterns you see in games
• Work on specific situations (serving, returning, etc.)
• Play practice points with purpose

**Mental Training:**
• Visualize successful shots
• Practice staying positive after mistakes
• Work on communication with your partner

**Consistency is Key:** Regular practice beats occasional long sessions!

What specific skill would you like to focus on in your next practice?"""


def generate_beginner_response(training_guide):
    """Generate response for beginners"""
    return """**Welcome to Platform Tennis!**

**Start with the Basics:**

**1. Grip:**
• Continental grip for serves and volleys
• Eastern forehand for groundstrokes
• Don't squeeze too tight!

**2. Basic Strokes:**
• **Forehand:** Turn shoulders, step forward, follow through
• **Backhand:** Two hands for control and power
• **Volley:** Short, punching motion with firm wrist

**3. Court Awareness:**
• Learn the dimensions and boundaries
• Understand how to use the screens
• Practice moving to the ball

**4. Safety:**
• Always warm up before playing
• Wear appropriate footwear
• Communicate with your partner

**Next Steps:** Find a local pro for lessons or join a beginner group!

What aspect of the game interests you most as you're getting started?"""


def generate_general_response(message, training_guide):
    """Generate a general helpful response"""
    responses = [
        f"That's a great question about '{message}'! Here are some key points to consider:",
        f"Let me help you with '{message}'. Here's what I recommend:",
        f"Regarding '{message}', here are some important fundamentals:",
    ]

    tips = [
        "**Focus on Fundamentals:** Master the basics before moving to advanced techniques",
        "**Practice Regularly:** Consistent practice is more valuable than occasional long sessions",
        "**Play with Better Players:** You'll improve faster by challenging yourself",
        "**Watch and Learn:** Observe skilled players and ask questions",
        "**Stay Patient:** Improvement takes time - celebrate small victories!",
    ]

    follow_ups = [
        "What specific technique would you like to work on?",
        "Are you looking for practice drills or match strategy?",
        "What's the biggest challenge you're facing right now?",
        "Would you like tips for a particular shot or situation?",
    ]

    import random

    response = (
        random.choice(responses)
        + "\n\n"
        + "\n".join(tips[:3])
        + "\n\n"
        + random.choice(follow_ups)
    )
    return response


@api_bp.route("/api/add-practice-times", methods=["POST"])
@login_required
def add_practice_times():
    """API endpoint to add practice times to the schedule"""
    try:
        # Get form data
        first_date = request.form.get("first_date")
        last_date = request.form.get("last_date")
        day = request.form.get("day")
        time = request.form.get("time")

        # Validate required fields
        if not all([first_date, last_date, day, time]):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "All fields are required (first date, last date, day, and time)",
                    }
                ),
                400,
            )

        # Get user's club to determine which team schedule to update
        user = session["user"]
        user_club = user.get("club", "")
        user_series = user.get("series", "")

        if not user_club:
            return jsonify({"success": False, "message": "User club not found"}), 400

        if not user_series:
            return jsonify({"success": False, "message": "User series not found"}), 400

        # Convert form data to appropriate formats
        import json
        import os
        from datetime import datetime, timedelta

        # Parse the dates
        try:
            first_date_obj = datetime.strptime(first_date, "%Y-%m-%d")
            last_date_obj = datetime.strptime(last_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format"}), 400

        # Validate date range
        if last_date_obj < first_date_obj:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Last practice date must be after or equal to first practice date",
                    }
                ),
                400,
            )

        # Check for reasonable date range (not more than 2 years)
        date_diff = (last_date_obj - first_date_obj).days
        if date_diff > 730:  # 2 years
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Date range too large. Please select a range of 2 years or less.",
                    }
                ),
                400,
            )

        # Convert 24-hour time to 12-hour format
        try:
            time_obj = datetime.strptime(time, "%H:%M")
            formatted_time = time_obj.strftime("%I:%M %p").lstrip("0")
        except ValueError:
            return jsonify({"success": False, "message": "Invalid time format"}), 400

        # Get league ID for the user
        league_id = None
        try:
            user_league = execute_query_one(
                """
                SELECT l.id 
                FROM users u 
                LEFT JOIN leagues l ON u.league_id = l.id 
                WHERE u.email = %(email)s
            """,
                {"email": user["email"]},
            )

            if user_league:
                league_id = user_league["id"]
        except Exception as e:
            print(f"Could not get league ID for user: {e}")

        # FIXED: Use priority-based team detection (same as availability page and other functions)
        user_team_id = None
        
        # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
        session_team_id = user.get("team_id")
        print(f"[DEBUG] Practice add: session_team_id from user: {session_team_id}")
        
        if session_team_id:
            user_team_id = session_team_id
            print(f"[DEBUG] Practice add: Using team_id from session: {user_team_id}")
        
        # PRIORITY 2: Use team_context from user if provided
        if not user_team_id:
            team_context = user.get("team_context")
            if team_context:
                user_team_id = team_context
                print(f"[DEBUG] Practice add: Using team_context: {user_team_id}")
        
        # PRIORITY 3: Fallback to session service
        if not user_team_id:
            try:
                from app.services.session_service import get_session_data_for_user
                session_data = get_session_data_for_user(user["email"])
                if session_data:
                    user_team_id = session_data.get("team_id")
                    print(f"[DEBUG] Practice add: Found team_id via session service: {user_team_id}")
            except Exception as e:
                print(f"Could not get team ID via session service: {e}")

        # Convert day name to number (0=Monday, 6=Sunday)
        day_map = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6,
        }
        target_weekday = day_map.get(day)

        if target_weekday is None:
            return jsonify({"success": False, "message": "Invalid day selected"}), 400

        # Start from the first practice date
        current_date = first_date_obj
        practices_added = 0
        added_practices = []  # Track the specific practices added
        failed_practices = []

        # Check for existing practices to avoid duplicates
        practice_description = f"{user_club} Practice - {user_series}"
        
        # FIXED: Use team_id-based duplicate checking for precision (handle NULL league_id)
        existing_query = """
            SELECT match_date FROM schedule 
            WHERE home_team_id = %(team_id)s
            AND (league_id = %(league_id)s OR (league_id IS NULL AND %(league_id)s IS NOT NULL))
            AND home_team = %(practice_desc)s
            AND match_date BETWEEN %(start_date)s AND %(end_date)s
        """

        try:
            existing_practices = execute_query(
                existing_query,
                {
                    "team_id": user_team_id,
                    "league_id": league_id,
                    "practice_desc": practice_description,
                    "start_date": first_date_obj.date(),
                    "end_date": last_date_obj.date(),
                },
            )
            existing_dates = {practice["match_date"] for practice in existing_practices}

            if existing_dates:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Some practice dates already exist in the schedule. Please remove existing practices first or choose different dates.",
                        }
                    ),
                    400,
                )

        except Exception as e:
            print(f"Error checking existing practices: {e}")
            # Continue anyway - we'll handle duplicates during insertion

        # Add practice entries to database for the specified date range
        while current_date <= last_date_obj:
            # If current date is the target weekday, add practice
            if current_date.weekday() == target_weekday:
                try:
                    # Parse formatted time back to time object for database storage
                    time_obj = datetime.strptime(formatted_time, "%I:%M %p").time()

                    # FIXED: Insert practice into schedule table with proper team_id
                    execute_query(
                        """
                        INSERT INTO schedule (league_id, match_date, match_time, home_team, away_team, home_team_id, location)
                        VALUES (%(league_id)s, %(match_date)s, %(match_time)s, %(practice_desc)s, '', %(team_id)s, %(location)s)
                    """,
                        {
                            "league_id": league_id,
                            "match_date": current_date.date(),
                            "match_time": time_obj,
                            "practice_desc": practice_description,
                            "team_id": user_team_id,  # This is the key fix
                            "location": user_club,
                        },
                    )

                    practices_added += 1

                    # Add to our tracking list for the response
                    added_practices.append(
                        {
                            "date": current_date.strftime("%m/%d/%Y"),
                            "time": formatted_time,
                            "day": day,
                        }
                    )

                except Exception as e:
                    print(f"Error inserting practice for {current_date}: {e}")
                    failed_practices.append(
                        {"date": current_date.strftime("%m/%d/%Y"), "error": str(e)}
                    )
                    # Continue with other dates even if one fails

            # Move to next day
            current_date += timedelta(days=1)

        # Check if we had any successes
        if practices_added == 0:
            error_msg = "No practices were added."
            if failed_practices:
                error_msg += (
                    f" {len(failed_practices)} practices failed to add due to errors."
                )
            else:
                error_msg += f" No {day}s found between {first_date} and {last_date}."
            return jsonify({"success": False, "message": error_msg}), 500

        # Log the activity
        from utils.logging import log_user_activity

        log_user_activity(
            user["email"],
            "practice_times_added",
            details=f"Added {practices_added} practice times for {user_series} {day}s at {formatted_time} from {first_date} to {last_date}",
        )

        success_message = (
            f"Successfully added {practices_added} practice times to the schedule!"
        )
        if failed_practices:
            success_message += f" ({len(failed_practices)} practices failed to add)"

        return jsonify(
            {
                "success": True,
                "message": success_message,
                "practices_added": added_practices,
                "count": practices_added,
                "series": user_series,
                "day": day,
                "time": formatted_time,
                "first_date": first_date,
                "last_date": last_date,
                "failed_count": len(failed_practices),
            }
        )

    except Exception as e:
        print(f"Error adding practice times: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An unexpected error occurred while adding practice times",
                }
            ),
            500,
        )


@api_bp.route("/api/remove-practice-times", methods=["POST"])
@login_required
def remove_practice_times():
    """Remove practice times"""
    return remove_practice_times_data()


@api_bp.route("/api/team-schedule-data")
@login_required
def get_team_schedule_data():
    """Get team schedule data"""
    return get_team_schedule_data_data()


@api_bp.route("/api/availability", methods=["POST"])
@login_required
def update_availability():
    """Update player availability for matches"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Accept either player_name (legacy) or tenniscores_player_id (preferred)
        player_name = data.get("player_name")
        tenniscores_player_id = data.get("tenniscores_player_id")
        match_date = data.get("match_date")
        availability_status = data.get("availability_status")
        series = data.get("series")
        notes = data.get("notes", "")  # Optional notes field

        # Validate required fields - prefer player ID over name
        if not all([match_date, availability_status]):
            return (
                jsonify(
                    {
                        "error": "Missing required fields: match_date, availability_status"
                    }
                ),
                400,
            )

        if not tenniscores_player_id and not player_name:
            return (
                jsonify(
                    {"error": "Either tenniscores_player_id or player_name is required"}
                ),
                400,
            )

        # Validate availability status
        if availability_status not in [
            1,
            2,
            3,
        ]:  # 1=available, 2=unavailable, 3=not_sure
            return (
                jsonify({"error": "Invalid availability_status. Must be 1, 2, or 3"}),
                400,
            )

        # Parse date and store as UTC midnight (required by database constraint)
        try:
            date_obj = datetime.strptime(match_date, "%Y-%m-%d")
            # Create UTC midnight timestamp to satisfy database constraint
            utc_midnight = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            utc_timezone = pytz.UTC
            utc_date = utc_timezone.localize(utc_midnight)
            formatted_date = utc_date.strftime("%Y-%m-%d %H:%M:%S%z")
        except ValueError:
            return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD"}), 400

        # Get player info and series_id using tenniscores_player_id or fallback to player associations
        user_email = session["user"]["email"]

        # Use SQLAlchemy to get player info
        db_session = SessionLocal()
        try:
            player = None

            # If tenniscores_player_id is provided, use it directly
            if tenniscores_player_id:
                player = (
                    db_session.query(Player)
                    .filter(
                        Player.tenniscores_player_id == tenniscores_player_id,
                        Player.is_active == True,
                    )
                    .first()
                )

                if not player:
                    return (
                        jsonify(
                            {
                                "error": f"Player with ID {tenniscores_player_id} not found or inactive"
                            }
                        ),
                        404,
                    )

                # Also get the full name for legacy compatibility
                player_name = f"{player.first_name} {player.last_name}"

            else:
                # Fallback: use player associations (legacy approach)
                user_record = (
                    db_session.query(User).filter(User.email == user_email).first()
                )

                if not user_record:
                    return jsonify({"error": "User not found"}), 404

                # Get player association based on current league context
                player_association = None
                
                # First try: get association for current league context
                if user_record.league_context:
                    associations = (
                        db_session.query(UserPlayerAssociation)
                        .filter(UserPlayerAssociation.user_id == user_record.id)
                        .all()
                    )
                    
                    for assoc in associations:
                        player = assoc.get_player(db_session)
                        if player and player.league_id == user_record.league_context:
                            player_association = assoc
                            break
                
                # Fallback: get any association
                if not player_association:
                    player_association = (
                        db_session.query(UserPlayerAssociation)
                        .filter(UserPlayerAssociation.user_id == user_record.id)
                        .first()
                    )

                if not player_association:
                    return (
                        jsonify(
                            {
                                "error": "No player association found. Please update your settings to link your player profile."
                            }
                        ),
                        400,
                    )

                # Check if the player association has a valid player record
                player = player_association.get_player(db_session)
                if not player:
                    return (
                        jsonify(
                            {
                                "error": "Player record not found. Your player association may be broken. Please update your settings to re-link your player profile."
                            }
                        ),
                        400,
                    )

                tenniscores_player_id = player.tenniscores_player_id

            # Get series_id from the player
            series_id = player.series_id

            if not series_id:
                return jsonify({"error": "Player series not found"}), 400

        finally:
            db_session.close()

        # Get the internal player.id for backward compatibility
        player_db_id = player.id

        # CRITICAL: Get user_id for stable reference pattern
        user_record = (
            db_session.query(User).filter(User.email == user_email).first()
        )
        
        if not user_record:
            return jsonify({"error": "User not found"}), 404
            
        user_id = user_record.id

        print(
            f"Updating availability: {player_name} (tenniscores_id: {tenniscores_player_id}, db_id: {player_db_id}, user_id: {user_id}) for {match_date} status {availability_status}"
        )

        # STABLE APPROACH: Use user_id + match_date as primary key (same pattern as user_player_associations)
        check_query = """
            SELECT id FROM player_availability 
            WHERE user_id = %s AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
        """
        existing_record = execute_query_one(
            check_query, (user_id, formatted_date)
        )

        if existing_record:
            # Update existing record using stable user_id reference
            update_query = """
                UPDATE player_availability 
                SET availability_status = %s, 
                    notes = %s, 
                    player_id = %s,
                    series_id = %s,
                    player_name = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
            """
            result = execute_update(
                update_query,
                (availability_status, notes, player_db_id, series_id, player_name, user_id, formatted_date),
            )
            print(f"✅ Updated existing availability record via stable user_id: {result}")
        else:
            # Insert new record using stable user_id reference
            insert_query = """
                INSERT INTO player_availability (user_id, match_date, availability_status, notes, player_id, series_id, player_name, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            result = execute_update(
                insert_query,
                (
                    user_id,
                    formatted_date,
                    availability_status,
                    notes,
                    player_db_id,
                    series_id,
                    player_name,
                ),
            )
            print(f"✅ Created new availability record via stable user_id: {result}")

        # Log the activity using comprehensive logging
        status_descriptions = {1: "available", 2: "unavailable", 3: "not sure"}
        status_text = status_descriptions.get(
            availability_status, f"status {availability_status}"
        )

        log_user_action(
            action_type="availability_update",
            action_description=f"Updated availability for {match_date} to {status_text}",
            user_email=user_email,
            user_id=session["user"].get("id"),
            player_id=player_db_id,
            team_id=None,  # We could look up team_id from player if needed
            related_id=str(series_id),
            related_type="series",
            legacy_action="availability_update",
            legacy_details=f"Set availability for {match_date} to status {availability_status} (Player: {player_name}, ID: {tenniscores_player_id})",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            extra_data={
                "match_date": match_date,
                "availability_status": availability_status,
                "status_text": status_text,
                "player_name": player_name,
                "tenniscores_player_id": tenniscores_player_id,
                "series_id": series_id,
                "notes": notes,
                "was_new_record": not existing_record,
            },
        )

        return jsonify(
            {
                "success": True,
                "message": "Availability updated successfully",
                "player_name": player_name,
                "tenniscores_player_id": tenniscores_player_id,
                "match_date": match_date,
                "availability_status": availability_status,
            }
        )

    except Exception as e:
        print(f"Error updating availability: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Failed to update availability: {str(e)}"}), 500


@api_bp.route("/api/get-user-settings")
@login_required
def get_user_settings():
    """Get user settings for the settings page"""
    try:
        user_email = session["user"]["email"]

        # Get basic user data including league_context
        user_data = execute_query_one(
            """
            SELECT u.first_name, u.last_name, u.email, u.is_admin, 
                   u.ad_deuce_preference, u.dominant_hand, u.league_context
            FROM users u
            WHERE u.email = %s
        """,
            (user_email,),
        )

        if not user_data:
            return jsonify({"error": "User not found"}), 404

        # Get player association data using SQLAlchemy
        db_session = SessionLocal()
        try:
            user_record = (
                db_session.query(User).filter(User.email == user_email).first()
            )

            if user_record:
                # Get player based on league context
                club_name = series_name = league_id = league_name = tenniscores_player_id = ""
                
                # Get all associations for this user
                associations = (
                    db_session.query(UserPlayerAssociation)
                    .filter(UserPlayerAssociation.user_id == user_record.id)
                    .all()
                )
                
                selected_player = None
                
                # First priority: find player matching league_context
                if user_record.league_context and associations:
                    for assoc in associations:
                        player = assoc.get_player(db_session)
                        if player and player.league and player.league.id == user_record.league_context:
                            selected_player = player
                            break
                
                # Second priority: use first available player
                if not selected_player and associations:
                    for assoc in associations:
                        player = assoc.get_player(db_session)
                        if player and player.club and player.series and player.league:
                            selected_player = player
                            break
                
                # Extract player data if found
                if selected_player:
                    club_name = selected_player.club.name if selected_player.club else ""
                    raw_series_name = selected_player.series.name if selected_player.series else ""
                    league_id = selected_player.league.league_id if selected_player.league else ""
                    league_name = selected_player.league.league_name if selected_player.league else ""
                    tenniscores_player_id = selected_player.tenniscores_player_id
                    
                    # Get display name from series table if available
                    series_name = raw_series_name
                    if raw_series_name:
                        try:
                            # Check for display_name in series table
                            display_name_query = """
                                SELECT display_name
                                FROM series
                                WHERE name = %s
                                LIMIT 1
                            """
                            
                            display_result = execute_query_one(display_name_query, (raw_series_name,))
                            
                            if display_result and display_result["display_name"]:
                                series_name = display_result["display_name"]
                                print(f"[GET_USER_SETTINGS] Using display_name: '{raw_series_name}' -> '{series_name}'")
                            else:
                                # For APTA league, try converting Chicago format to Series format as fallback
                                if league_id and league_id.startswith("APTA") and raw_series_name.startswith("Chicago"):
                                    series_name = convert_chicago_to_series_for_ui(raw_series_name)
                                    print(f"[GET_USER_SETTINGS] Applied Chicago->Series conversion: '{raw_series_name}' -> '{series_name}'")
                                else:
                                    print(f"[GET_USER_SETTINGS] No display_name found for '{raw_series_name}', using as-is")
                        except Exception as display_error:
                            print(f"[GET_USER_SETTINGS] Error getting display name: {display_error}")
                            series_name = raw_series_name
            else:
                club_name = series_name = league_id = league_name = (
                    tenniscores_player_id
                ) = ""

        finally:
            db_session.close()

        response_data = {
            "first_name": user_data["first_name"] or "",
            "last_name": user_data["last_name"] or "",
            "email": user_data["email"] or "",
            "club": club_name,
            "series": series_name,
            "league_id": league_id,  # This should be the string ID for JavaScript compatibility
            "league_name": league_name,
            "league_context": user_data["league_context"],  # Add league context to response
            "tenniscores_player_id": tenniscores_player_id,
            "ad_deuce_preference": user_data["ad_deuce_preference"] or "",
            "dominant_hand": user_data["dominant_hand"] or "",
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error getting user settings: {str(e)}")
        return jsonify({"error": "Failed to get user settings"}), 500


def convert_series_to_mapping_id(series_name, club_name, league_id=None):
    """
    DEPRECATED: This function was used for JSON file lookups.
    Database lookups now use series names directly.
    Keeping for backward compatibility but marked for removal.
    """
    # This function is no longer needed for database-only lookups
    # but keeping for any legacy code that might still reference it
    logger.warning(
        "convert_series_to_mapping_id is deprecated - use database lookups instead"
    )
    return f"{club_name} {series_name}"  # Simple fallback


@api_bp.route("/api/update-settings", methods=["POST"])
@login_required
def update_settings():
    """Update user settings with intelligent player lookup"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from app.services.session_service import switch_user_league, get_session_data_for_user
        from utils.database_player_lookup import find_player_by_database_lookup
        from app.models.database_models import User, Player, UserPlayerAssociation, SessionLocal
        data = request.get_json()
        user_email = session["user"]["email"]

        # Validate required fields
        if not data.get("firstName") or not data.get("lastName") or not data.get("email"):
            return jsonify({"error": "First name, last name, and email are required"}), 400

        logger.info(f"Settings update for {user_email}: {data}")

        # Get current user data for comparison
        current_user_data = session["user"]
        current_tenniscores_player_id = current_user_data.get("tenniscores_player_id")
        current_league_id = current_user_data.get("league_id")
        current_club = current_user_data.get("club")
        current_series = current_user_data.get("series")

        # Check if settings have changed
        new_league_id = data.get("league_id")
        new_club = data.get("club")
        new_series = data.get("series")
        
        settings_changed = (
            new_league_id != current_league_id or
            new_club != current_club or
            new_series != current_series
        )

        # Determine if we should perform player lookup
        should_perform_player_lookup = (
            not current_tenniscores_player_id or  # User doesn't have player ID
            settings_changed  # Settings have changed
        )

        logger.info(f"Player lookup decision: should_perform={should_perform_player_lookup}, "
                   f"has_player_id={bool(current_tenniscores_player_id)}, "
                   f"settings_changed={settings_changed}")

        # Update basic user data first
        execute_query("""
            UPDATE users 
            SET first_name = %s, last_name = %s, email = %s,
                ad_deuce_preference = %s, dominant_hand = %s
            WHERE email = %s
        """, [
            data.get("firstName"),
            data.get("lastName"), 
            data.get("email"),
            data.get("adDeuce", ""),
            data.get("dominantHand", ""),
            user_email
        ])

        # Handle league switching if league changed
        if new_league_id and new_league_id != current_league_id:
            logger.info(f"League change requested: {current_league_id} -> {new_league_id}")
            
            # Switch to new league
            if switch_user_league(user_email, new_league_id):
                logger.info(f"Successfully switched to {new_league_id}")
            else:
                return jsonify({
                    "success": False, 
                    "message": f"Could not switch to {new_league_id}. You may not have a player record in that league."
                }), 400

        # Perform player lookup if needed
        player_lookup_success = False
        if should_perform_player_lookup and new_league_id and new_club and new_series:
            logger.info(f"Performing player lookup for {data.get('firstName')} {data.get('lastName')}")
            
            try:
                # Use database-only lookup
                lookup_result = find_player_by_database_lookup(
                    first_name=data.get("firstName"),
                    last_name=data.get("lastName"),
                    club_name=new_club,
                    series_name=new_series,
                    league_id=new_league_id
                )

                # Extract player ID from the enhanced result
                found_player_id = None
                if lookup_result and lookup_result.get("player"):
                    found_player_id = lookup_result["player"]["tenniscores_player_id"]
                    logger.info(f"Player lookup result: {lookup_result['match_type']} - {lookup_result['message']}")

                if found_player_id:
                    # Create user-player association
                    db_session = SessionLocal()
                    try:
                        # Get user and player records
                        user_record = db_session.query(User).filter(User.email == user_email).first()
                        player_record = db_session.query(Player).filter(
                            Player.tenniscores_player_id == found_player_id,
                            Player.is_active == True
                        ).first()

                        if user_record and player_record:
                            # Check if association already exists
                            existing = db_session.query(UserPlayerAssociation).filter(
                                UserPlayerAssociation.user_id == user_record.id,
                                UserPlayerAssociation.tenniscores_player_id == player_record.tenniscores_player_id
                            ).first()

                            if not existing:
                                # Create new association
                                association = UserPlayerAssociation(
                                    user_id=user_record.id,
                                    tenniscores_player_id=player_record.tenniscores_player_id
                                )
                                db_session.add(association)
                                
                                # Update user's league context
                                user_record.league_context = player_record.league_id

                                # Ensure player has team assignment
                                from app.services.auth_service_refactored import assign_player_to_team
                                team_assigned = assign_player_to_team(player_record, db_session)
                                if team_assigned:
                                    logger.info(f"Team assignment successful for {player_record.full_name}")

                                db_session.commit()
                                logger.info(f"Created player association for {found_player_id}")
                                player_lookup_success = True
                            else:
                                logger.info(f"Association already exists for player ID {found_player_id}")
                                player_lookup_success = True
                        else:
                            logger.error("Could not find user or player record for association")

                    except Exception as assoc_error:
                        db_session.rollback()
                        logger.error(f"Association error: {str(assoc_error)}")
                    finally:
                        db_session.close()
                else:
                    logger.info(f"No player match found for {data.get('firstName')} {data.get('lastName')}")

            except Exception as lookup_error:
                logger.error(f"Player lookup error: {str(lookup_error)}")

        # Handle series update with reverse mapping
        if new_series:
            logger.info(f"Series update requested: {new_series}")
            
            # Convert user-facing series name back to database series name
            database_series_name = new_series
            
            try:
                # Check for reverse mapping using display_name column
                reverse_mapping_query = """
                    SELECT name as database_series_name
                    FROM series
                    WHERE display_name = %s OR name = %s
                    LIMIT 1
                """
                
                mapping_result = execute_query_one(reverse_mapping_query, (new_series, new_series))
                
                if mapping_result:
                    database_series_name = mapping_result["database_series_name"]
                    logger.info(f"Found series mapping: '{new_series}' -> '{database_series_name}'")
                else:
                    logger.info(f"No series mapping found for '{new_series}', using as-is")
            except Exception as e:
                logger.warning(f"Error looking up series mapping: {e}")
            
            # Find the series_id for the database series name
            series_lookup_query = """
                SELECT s.id as series_id
                FROM series s
                WHERE s.name = %s
                LIMIT 1
            """
            
            series_result = execute_query_one(series_lookup_query, (database_series_name,))
            
            if series_result:
                series_id = series_result["series_id"]
                logger.info(f"Found series_id {series_id} for series '{database_series_name}'")
                
                # Update the user's primary player record with the new series
                # This ensures the session service picks up the new series
                player_update_query = """
                    UPDATE players p
                    SET series_id = %s
                    FROM user_player_associations upa
                    JOIN users u ON upa.user_id = u.id
                    WHERE u.email = %s 
                    AND p.tenniscores_player_id = upa.tenniscores_player_id
                    AND (u.league_context IS NULL OR p.league_id = u.league_context)
                """
                
                execute_query(player_update_query, (series_id, user_email))
                logger.info(f"Updated player series to '{database_series_name}' for user {user_email}")
            else:
                logger.warning(f"Series '{database_series_name}' not found in database")

        # Rebuild session from database (this gets the updated league_context and player association)
        fresh_session_data = get_session_data_for_user(user_email)
        if fresh_session_data:
            session["user"] = fresh_session_data
            session.modified = True
            logger.info(f"Session updated: {fresh_session_data.get('league_name', 'Unknown')} - {fresh_session_data.get('club', 'Unknown')}")
            
            # Add player lookup status to response
            success_message = "Settings updated successfully"
            if player_lookup_success:
                success_message += f" and player ID found: {fresh_session_data.get('tenniscores_player_id', 'Unknown')}"
            elif should_perform_player_lookup:
                success_message += " (Note: Player lookup attempted but no match found)"
            
            return jsonify({
                "success": True, 
                "message": success_message,
                "user": fresh_session_data,
                "player_lookup_performed": should_perform_player_lookup,
                "player_lookup_success": player_lookup_success
            })
        else:
            return jsonify({"success": False, "message": "Failed to update session"}), 500

    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({"success": False, "message": f"Update failed: {str(e)}"}), 500


@api_bp.route("/api/retry-player-id", methods=["POST"])
@login_required
def retry_player_id_lookup():
    """Manual retry of player ID lookup for current user"""
    try:
        import logging

        from utils.database_player_lookup import find_player_by_database_lookup

        logger = logging.getLogger(__name__)
        user_email = session["user"]["email"]

        # Get current user data from session (since we can't rely on user table foreign keys anymore)
        first_name = session["user"].get("first_name")
        last_name = session["user"].get("last_name")
        club_name = session["user"].get("club")
        series_name = session["user"].get("series")
        league_id = session["user"].get("league_id")

        # If session doesn't have player data, this means user never had a player association
        # We can't do a retry without knowing what league/club/series to search in
        if not all([first_name, last_name]):
            missing = []
            if not first_name:
                missing.append("first name")
            if not last_name:
                missing.append("last name")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f'Missing required user data: {", ".join(missing)}',
                    }
                ),
                400,
            )

        if not all([club_name, series_name, league_id]):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Cannot retry player lookup - no club/series/league information available. Please update your settings with your club, series, and league information first.",
                    }
                ),
                400,
            )

        try:
            logger.info(
                f"Manual retry: Looking up player via database for {first_name} {last_name}"
            )

            # Use database-only lookup - NO MORE JSON FILES
            lookup_result = find_player_by_database_lookup(
                first_name=first_name,
                last_name=last_name,
                club_name=club_name,
                series_name=series_name,
                league_id=league_id,
            )

            # Extract player ID from the enhanced result
            found_player_id = None
            if lookup_result and lookup_result.get("player"):
                found_player_id = lookup_result["player"]["tenniscores_player_id"]
                logger.info(
                    f"Manual retry: Match type: {lookup_result['match_type']} - {lookup_result['message']}"
                )

            if found_player_id:
                # Create user-player association
                db_session = SessionLocal()
                try:
                    # Get user and player records
                    user_record = (
                        db_session.query(User).filter(User.email == user_email).first()
                    )
                    player_record = (
                        db_session.query(Player)
                        .filter(
                            Player.tenniscores_player_id == found_player_id,
                            Player.is_active == True,
                        )
                        .first()
                    )

                    if user_record and player_record:
                        # Check if association already exists
                        existing = (
                            db_session.query(UserPlayerAssociation)
                            .filter(
                                UserPlayerAssociation.user_id == user_record.id,
                                UserPlayerAssociation.tenniscores_player_id
                                == player_record.tenniscores_player_id,
                            )
                            .first()
                        )

                        if not existing:
                            # Create new association
                            association = UserPlayerAssociation(
                                user_id=user_record.id,
                                tenniscores_player_id=player_record.tenniscores_player_id,
                            )
                            db_session.add(association)
                            
                            # Update user's league context
                            user_record.league_context = player_record.league_id

                            # ✅ CRITICAL: Ensure player has team assignment for polls functionality
                            from app.services.auth_service_refactored import (
                                assign_player_to_team,
                            )

                            team_assigned = assign_player_to_team(
                                player_record, db_session
                            )
                            if team_assigned:
                                logger.info(
                                    f"Manual retry: Team assignment successful for {player_record.full_name}"
                                )
                            else:
                                logger.warning(
                                    f"Manual retry: Could not assign team to {player_record.full_name}"
                                )

                            db_session.commit()

                            # Update session with player data
                            session["user"]["tenniscores_player_id"] = found_player_id
                            session["user"]["league_context"] = player_record.league_id
                            if (
                                player_record.club
                                and player_record.series
                                and player_record.league
                            ):
                                session["user"]["club"] = player_record.club.name
                                session["user"]["series"] = player_record.series.name
                                session["user"][
                                    "league_id"
                                ] = player_record.league.league_id
                                session["user"][
                                    "league_name"
                                ] = player_record.league.league_name
                            session.modified = True

                            logger.info(
                                f"Manual retry: Created association and updated session for player ID {found_player_id}"
                            )

                            return jsonify(
                                {
                                    "success": True,
                                    "player_id": found_player_id,
                                    "message": f"Player ID found and associated: {found_player_id}",
                                }
                            )
                        else:
                            logger.info(
                                f"Manual retry: Association already exists for player ID {found_player_id}"
                            )

                            # Update session anyway in case it was missing
                            session["user"]["tenniscores_player_id"] = found_player_id
                            session["user"]["league_context"] = player_record.league_id
                            session.modified = True

                            return jsonify(
                                {
                                    "success": True,
                                    "player_id": found_player_id,
                                    "message": f"Player ID already associated: {found_player_id}",
                                }
                            )
                    else:
                        logger.error(
                            f"Manual retry: Could not find user or player record for association"
                        )
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "message": "Found player ID but could not create association",
                                }
                            ),
                            500,
                        )

                except Exception as assoc_error:
                    db_session.rollback()
                    logger.error(f"Manual retry: Association error: {str(assoc_error)}")
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "Found player ID but failed to create association",
                            }
                        ),
                        500,
                    )
                finally:
                    db_session.close()
            else:
                logger.info(
                    f"Manual retry: No player match found for {first_name} {last_name}"
                )
                return jsonify(
                    {
                        "success": False,
                        "message": f"No matching player found for {first_name} {last_name} ({club_name}, {series_name})",
                    }
                )

        except Exception as lookup_error:
            logger.error(f"Manual retry: Database lookup error: {str(lookup_error)}")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Player lookup failed due to database error",
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Manual retry endpoint error: {str(e)}")
        return (
            jsonify({"success": False, "message": "Retry failed due to server error"}),
            500,
        )


@api_bp.route("/api/get-leagues")
def get_leagues():
    """Get all available leagues"""
    try:
        query = """
            SELECT league_id, league_name, league_url
            FROM leagues
            ORDER BY league_name
        """

        leagues_data = execute_query(query)

        return jsonify({"leagues": leagues_data})

    except Exception as e:
        print(f"Error getting leagues: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/get-clubs-by-league")
def get_clubs_by_league():
    """Get clubs filtered by league"""
    try:
        league_id = request.args.get("league_id")

        if not league_id:
            # Return all clubs if no league specified
            query = "SELECT name FROM clubs ORDER BY name"
            clubs_data = execute_query(query)
        else:
            # Get clubs for specific league
            query = """
                SELECT c.name
                FROM clubs c
                JOIN club_leagues cl ON c.id = cl.club_id
                JOIN leagues l ON cl.league_id = l.id
                WHERE l.league_id = %s
                ORDER BY c.name
            """
            clubs_data = execute_query(query, (league_id,))

        clubs_list = [club["name"] for club in clubs_data]

        return jsonify({"clubs": clubs_list})

    except Exception as e:
        print(f"Error getting clubs by league: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/get-series-by-league")
def get_series_by_league():
    """Get series filtered by league"""
    try:
        league_id = request.args.get("league_id")

        if not league_id:
            # Return all series if no league specified
            query = """
                SELECT DISTINCT s.name as series_name
                FROM series s
                ORDER BY s.name
            """
            series_data = execute_query(query)
        else:
            # Get series for specific league
            query = """
                SELECT s.name as series_name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                JOIN leagues l ON sl.league_id = l.id
                WHERE l.league_id = %s
                ORDER BY s.name
            """
            series_data = execute_query(query, (league_id,))

        # Process the series data to extract numbers and sort properly
        def get_series_sort_key(series_name):
            import re
            
            # Handle series with numeric values: "Chicago 1", "Series 2", "Division 3", etc.
            match = re.match(r'^(?:(Chicago|Series|Division)\s+)?(\d+)([a-zA-Z\s]*)$', series_name)
            if match:
                prefix = match.group(1) or ''
                number = int(match.group(2))
                suffix = match.group(3).strip() if match.group(3) else ''
                
                # Sort by: prefix priority, then number, then suffix
                prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                return (0, prefix_priority, number, suffix)  # Numeric series first
            
            # Handle letter-only series (Series A, Series B, etc.)
            match = re.match(r'^(?:(Chicago|Series|Division)\s+)?([A-Z]+)$', series_name)
            if match:
                prefix = match.group(1) or ''
                letter = match.group(2)
                prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                return (1, prefix_priority, 0, letter)  # Letters after numbers
            
            # Everything else goes last (sorted alphabetically)
            return (2, 0, 0, series_name)

        series_data.sort(key=lambda x: get_series_sort_key(x["series_name"]))
        
        # Convert series names for APTA league UI display
        series_names = []
        for item in series_data:
            series_name = item["series_name"]
            
            # For APTA league, convert "Chicago" to "Series" in the UI
            if league_id and league_id.startswith("APTA"):
                series_name = convert_chicago_to_series_for_ui(series_name)
            
            series_names.append(series_name)

        # DEDUPLICATION FIX: Remove duplicates while preserving order
        # This fixes the issue where both "Chicago X" and "Division X" map to "Series X"
        seen = set()
        deduplicated_series = []
        for name in series_names:
            if name not in seen:
                seen.add(name)
                deduplicated_series.append(name)
                
        print(f"[API] get-series-by-league - Deduplicated: {len(series_names)} -> {len(deduplicated_series)} unique series")

        return jsonify({"series": deduplicated_series})

    except Exception as e:
        print(f"Error getting series by league: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/get-user-facing-series-by-league")
def get_user_facing_series_by_league():
    """Get user-facing series names using the series.display_name column - SIMPLIFIED VERSION"""
    try:
        league_id = request.args.get("league_id")

        # If no league_id parameter provided, get it from user session
        if not league_id and "user" in session:
            # Try both league_string_id and league_id from session
            league_id = session["user"].get("league_string_id") or session["user"].get("league_id", "")
            print(f"[DEBUG] No league_id parameter, using session league_id: {league_id}")

        if not league_id:
            # If still no league_id, return empty series list instead of all series
            print(f"[WARNING] No league_id found in parameter or session, returning empty series list")
            return jsonify({"series": []})
            
        # Convert integer league_id to string format if needed
        if isinstance(league_id, int):
            try:
                league_record = execute_query_one("SELECT league_id FROM leagues WHERE id = %s", [league_id])
                if league_record:
                    league_id = league_record["league_id"]
                    print(f"[DEBUG] Converted integer league_id {league_id} to string format")
            except Exception as e:
                print(f"[WARNING] Could not convert integer league_id: {e}")
            
        # SIMPLIFIED: Get series with display names using the new display_name column
        simplified_query = """
            SELECT DISTINCT 
                s.name as database_series_name,
                COALESCE(s.display_name, s.name) as display_name
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            JOIN leagues l ON sl.league_id = l.id
            WHERE l.league_id = %s
            ORDER BY s.name
        """
        series_data = execute_query(simplified_query, (league_id,))
        
        # Process all series and use display_name if available, fallback to transformations
        user_facing_names = []
        
        for series_item in series_data:
            database_name = series_item["database_series_name"]
            display_name = series_item["display_name"]
            
            # Skip problematic Chicago series that don't follow standard pattern
            if league_id and league_id.startswith("APTA") and database_name in ["Chicago", "Chicago Chicago"]:
                print(f"[API] Skipping problematic series: {database_name}")
                continue
            
            # Use display_name if it exists and is different from database name
            if display_name and display_name != database_name:
                user_facing_name = display_name
                print(f"[API] Using display_name: '{database_name}' -> '{display_name}'")
            else:
                # No display name set, use database name as-is or apply fallback transformations
                user_facing_name = database_name
                
                # For APTA league, try to convert "Chicago" to "Series" in the UI
                if league_id and league_id.startswith("APTA"):
                    converted_name = convert_chicago_to_series_for_ui(user_facing_name)
                    # Use converted name if it actually changed
                    if converted_name != user_facing_name:
                        user_facing_name = converted_name
                        print(f"[API] Applied fallback transformation: '{database_name}' -> '{user_facing_name}'")
            
            user_facing_names.append(user_facing_name)
        
        # DEDUPLICATION FIX: Remove duplicates while preserving order
        # This fixes the issue where both "Chicago X" and "Division X" map to "Series X"
        seen = set()
        series_names = []
        for name in user_facing_names:
            if name not in seen:
                seen.add(name)
                series_names.append(name)
                
        print(f"[API] Deduplicated series list: {len(user_facing_names)} -> {len(series_names)} unique series")

        # Sort series properly (numbers before letters)
        def get_sort_key(series_name):
            import re
            
            # Handle series with numeric values: "Chicago 1", "Series 2", "Division 3", etc.
            # Extract prefix, number, and optional suffix (like "SW" or letters)
            match = re.match(r'^(?:(Chicago|Series|Division)\s+)?(\d+)([a-zA-Z\s]*)$', series_name)
            if match:
                prefix = match.group(1) or ''
                number = int(match.group(2))
                suffix = match.group(3).strip() if match.group(3) else ''
                
                # Sort by: prefix priority, then number, then suffix
                prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                return (0, prefix_priority, number, suffix)  # Numeric series first
            
            # Handle letter-only series (Series A, Series B, etc.)
            match = re.match(r'^(?:(Chicago|Series|Division)\s+)?([A-Z]+)$', series_name)
            if match:
                prefix = match.group(1) or ''
                letter = match.group(2)
                prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                return (1, prefix_priority, 0, letter)  # Letters after numbers
            
            # Everything else goes last (sorted alphabetically)
            return (2, 0, 0, series_name)

        series_names.sort(key=get_sort_key)
        
        print(f"[API] Returning user-facing series for {league_id}: {series_names}")
        return jsonify({"series": series_names})

    except Exception as e:
        print(f"Error getting user-facing series by league: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/teams")
@login_required
def get_teams():
    """Get teams filtered by user's league"""
    try:
        # Get user's league for filtering
        user = session.get("user")
        if not user:
            return jsonify({"error": "Not authenticated"}), 401

        # FIXED: Use league_string_id instead of league_id (which is now an integer)
        user_league_string_id = user.get("league_string_id", "")
        print(f"[DEBUG] /api/teams: User league_string_id: '{user_league_string_id}'")

        # Load stats data to get team names
        import os

        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        stats_path = os.path.join(
            project_root, "data", "leagues", "all", "series_stats.json"
        )

        with open(stats_path, "r") as f:
            all_stats = json.load(f)

        # Filter stats data by user's league
        def is_user_league_team(team_data):
            team_league_id = team_data.get("league_id")
            if user_league_string_id.startswith("APTA"):
                # For APTA users, only include teams without league_id field (APTA teams)
                return team_league_id is None
            else:
                # For other leagues, match the league_id
                return team_league_id == user_league_string_id

        league_filtered_stats = [
            team for team in all_stats if is_user_league_team(team)
        ]
        print(
            f"[DEBUG] Filtered from {len(all_stats)} total teams to {len(league_filtered_stats)} teams in user's league"
        )

        # Extract team names and filter out BYE teams
        teams = sorted(
            {s["team"] for s in league_filtered_stats if "BYE" not in s["team"].upper()}
        )

        return jsonify({"teams": teams})

    except Exception as e:
        print(f"Error getting teams: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/teams-with-ids")
@login_required
def get_teams_with_ids():
    """Get teams with IDs filtered by user's league"""
    try:
        print(f"[DEBUG] teams-with-ids API called")
        user = session.get("user")
        if not user:
            return jsonify({"error": "Not authenticated"}), 401

        # Get user's league for filtering
        user_league_id = user.get("league_id", "")
        print(f"[DEBUG] teams-with-ids: User league_id: {user_league_id}")

        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
                    print(f"[DEBUG] Converted league_id '{user_league_id}' to integer: {league_id_int}")
                else:
                    print(f"[WARNING] League '{user_league_id}' not found in leagues table")
            except Exception as e:
                print(f"[DEBUG] Could not convert league ID: {e}")
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
            print(f"[DEBUG] League_id already integer: {league_id_int}")

        # Get teams from database with IDs
        if league_id_int:
            teams_query = """
                SELECT DISTINCT t.id as team_id, t.team_name, t.display_name
                FROM teams t
                WHERE t.league_id = %s AND t.is_active = TRUE
                AND t.team_name NOT ILIKE '%BYE%'
                ORDER BY t.team_name
            """
            teams_data = execute_query(teams_query, [league_id_int])
        else:
            teams_query = """
                SELECT DISTINCT t.id as team_id, t.team_name, t.display_name
                FROM teams t
                WHERE t.is_active = TRUE
                AND t.team_name NOT ILIKE '%BYE%'
                ORDER BY t.team_name
            """
            teams_data = execute_query(teams_query)

        # Format teams data
        teams = []
        for team in teams_data:
            teams.append({
                "team_id": team["team_id"],
                "team_name": team["team_name"],
                "display_name": team["display_name"] or team["team_name"]
            })

        print(f"[DEBUG] teams-with-ids: Found {len(teams)} teams with IDs for league {league_id_int}")
        print(f"[DEBUG] teams-with-ids: Sample teams: {teams[:3] if teams else 'None'}")

        return jsonify({"teams": teams})

    except Exception as e:
        print(f"Error getting teams with IDs: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/club-players-metadata")
@login_required
def get_club_players_metadata():
    """Get metadata for club players page (series list, PTI range, etc.) without requiring filter criteria"""
    try:
        from database_utils import execute_query
        
        user_club = session["user"].get("club")
        user_league_id = session["user"].get("league_id", "")
        
        # Convert league_id to integer foreign key
        user_league_db_id = None
        if user_league_id:
            try:
                user_league_db_id = int(user_league_id)
            except (ValueError, TypeError):
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        user_league_db_id = league_record["id"]
                except Exception:
                    pass
        
        # Get available series for the user's league
        available_series = []
        if user_league_db_id:
            series_query = """
                SELECT DISTINCT s.name as series_name
                FROM players p
                JOIN series s ON p.series_id = s.id
                WHERE p.league_id = %s AND p.is_active = true
                ORDER BY s.name
            """
            series_results = execute_query(series_query, (user_league_db_id,))
            available_series = [row["series_name"] for row in series_results]
        
        # Get PTI range for the user's league
        pti_range = {"min": -30, "max": 100}
        pti_filters_available = False
        if user_league_db_id:
            pti_query = """
                SELECT MIN(p.pti) as min_pti, MAX(p.pti) as max_pti, COUNT(*) as total_players,
                       COUNT(CASE WHEN p.pti IS NOT NULL THEN 1 END) as players_with_pti
                FROM players p
                WHERE p.league_id = %s AND p.is_active = true
            """
            pti_result = execute_query_one(pti_query, (user_league_db_id,))
            if pti_result and pti_result["min_pti"] is not None:
                pti_range = {"min": float(pti_result["min_pti"]), "max": float(pti_result["max_pti"])}
                # Show PTI filters if at least 10% of players have PTI values
                pti_percentage = (pti_result["players_with_pti"] / pti_result["total_players"] * 100) if pti_result["total_players"] > 0 else 0
                pti_filters_available = pti_percentage >= 10.0
        
        return jsonify({
            "available_series": available_series,
            "pti_range": pti_range,
            "pti_filters_available": pti_filters_available,
            "user_club": user_club or "Unknown Club",
        })

    except Exception as e:
        print(f"Error in club-players-metadata API: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/club-players")
@login_required
def get_club_players():
    """Get all players at the user's club with optional filtering"""
    try:
        # Get filter parameters
        series_filter = request.args.get("series", "").strip()
        first_name_filter = request.args.get("first_name", "").strip()
        last_name_filter = request.args.get("last_name", "").strip()
        pti_min = request.args.get("pti_min", type=float)
        pti_max = request.args.get("pti_max", type=float)
        club_only = (
            request.args.get("club_only", "true").lower() == "true"
        )  # Default to true

        # Use the mobile service function to get the data
        result = get_club_players_data(
            session["user"],
            series_filter,
            first_name_filter,
            last_name_filter,
            pti_min,
            pti_max,
            club_only,
        )

        return jsonify(result)

    except Exception as e:
        print(f"Error in club-players API: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/debug-club-data")
@login_required
def debug_club_data():
    """Debug endpoint to show user club and available clubs in players.json"""
    try:
        user_club = session["user"].get("club")

        # Use the mobile service function to get debug data
        result = get_club_players_data(session["user"])

        return jsonify(
            {
                "user_club_in_session": user_club,
                "session_user": session["user"],
                "debug_data": result.get("debug", {}),
            }
        )

    except Exception as e:
        print(f"Debug endpoint error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Route moved to mobile_routes.py to avoid conflicts
# The mobile blueprint now handles /api/player-history-chart with database queries

# ==========================================
# PTI ANALYSIS DATA ENDPOINTS
# ==========================================


@api_bp.route("/api/pti-analysis/players")
@login_required
def get_pti_analysis_players():
    """Get all players with PTI data for analysis - FIXED: Now league context aware"""
    try:
        # Get user's current league context
        user = session["user"]
        user_league_id = user.get("league_id", "")
        
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                pass
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
        
        # Build query with league filtering
        if league_id_int:
            query = """
                SELECT 
                    CONCAT(p.first_name, ' ', p.last_name) as name,
                    p.first_name as "First Name",
                    p.last_name as "Last Name", 
                    p.pti as "PTI",
                    p.wins,
                    p.losses,
                    p.win_percentage,
                    l.league_name as league,
                    c.name as club,
                    s.name as series
                FROM players p
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id  
                LEFT JOIN series s ON p.series_id = s.id
                WHERE p.is_active = true
                AND p.pti IS NOT NULL
                AND p.league_id = %s
                ORDER BY p.first_name, p.last_name
            """
            players_data = execute_query(query, [league_id_int])
        else:
            # Fallback: return all players if no league context
            query = """
                SELECT 
                    CONCAT(p.first_name, ' ', p.last_name) as name,
                    p.first_name as "First Name",
                    p.last_name as "Last Name", 
                    p.pti as "PTI",
                    p.wins,
                    p.losses,
                    p.win_percentage,
                    l.league_name as league,
                    c.name as club,
                    s.name as series
                FROM players p
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id  
                LEFT JOIN series s ON p.series_id = s.id
                WHERE p.is_active = true
                AND p.pti IS NOT NULL
                ORDER BY p.first_name, p.last_name
            """
            players_data = execute_query(query)

        return jsonify(players_data)

    except Exception as e:
        print(f"Error getting PTI analysis players: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/pti-analysis/player-history")
@login_required
def get_pti_analysis_player_history():
    """Get player history data for PTI analysis"""
    try:
        query = """
            SELECT 
                CONCAT(p.first_name, ' ', p.last_name) as name,
                ph.series,
                ph.date,
                ph.end_pti,
                l.league_name as league
            FROM player_history ph
            JOIN players p ON ph.player_id = p.id
            LEFT JOIN leagues l ON ph.league_id = l.id
            WHERE ph.end_pti IS NOT NULL
            ORDER BY p.first_name, p.last_name, ph.date
        """

        history_data = execute_query(query)

        # Group by player name and structure like the original JSON
        players_history = []
        current_player = None
        current_matches = []

        for row in history_data:
            player_name = row["name"]

            if current_player != player_name:
                if current_player is not None:
                    players_history.append(
                        {"name": current_player, "matches": current_matches}
                    )
                current_player = player_name
                current_matches = []

            # Format date as string for JSON serialization
            date_str = row["date"].strftime("%m/%d/%Y") if row["date"] else None

            current_matches.append(
                {
                    "series": row["series"],
                    "date": date_str,
                    "end_pti": float(row["end_pti"]) if row["end_pti"] else None,
                }
            )

        # Add the last player
        if current_player is not None:
            players_history.append({"name": current_player, "matches": current_matches})

        return jsonify(players_history)

    except Exception as e:
        print(f"Error getting PTI analysis player history: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/pti-analysis/match-history")
@login_required
def get_pti_analysis_match_history():
    """Get match history data for PTI analysis - FIXED: Now league context aware"""
    try:
        # Get user's current league context
        user = session["user"]
        user_league_id = user.get("league_id", "")
        
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                pass
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
        
        # Build query with league filtering
        base_query = """
            SELECT 
                TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                ms.home_team as "Home Team",
                ms.away_team as "Away Team",
                COALESCE(p1.first_name || ' ' || p1.last_name, ms.home_player_1_id) as "Home Player 1",
                COALESCE(p2.first_name || ' ' || p2.last_name, ms.home_player_2_id) as "Home Player 2", 
                COALESCE(p3.first_name || ' ' || p3.last_name, ms.away_player_1_id) as "Away Player 1",
                COALESCE(p4.first_name || ' ' || p4.last_name, ms.away_player_2_id) as "Away Player 2",
                ms.scores as "Scores",
                ms.winner as "Winner",
                l.league_name as league
            FROM match_scores ms
            LEFT JOIN players p1 ON (
                CASE 
                    WHEN NULLIF(TRIM(ms.home_player_1_id), '') ~ '^[0-9]+$' 
                    THEN NULLIF(TRIM(ms.home_player_1_id), '')::INTEGER 
                    ELSE NULL 
                END = p1.id
            )
            LEFT JOIN players p2 ON (
                CASE 
                    WHEN NULLIF(TRIM(ms.home_player_2_id), '') ~ '^[0-9]+$' 
                    THEN NULLIF(TRIM(ms.home_player_2_id), '')::INTEGER 
                    ELSE NULL 
                END = p2.id
            )
            LEFT JOIN players p3 ON (
                CASE 
                    WHEN NULLIF(TRIM(ms.away_player_1_id), '') ~ '^[0-9]+$' 
                    THEN NULLIF(TRIM(ms.away_player_1_id), '')::INTEGER 
                    ELSE NULL 
                END = p3.id
            )
            LEFT JOIN players p4 ON (
                CASE 
                    WHEN NULLIF(TRIM(ms.away_player_2_id), '') ~ '^[0-9]+$' 
                    THEN NULLIF(TRIM(ms.away_player_2_id), '')::INTEGER 
                    ELSE NULL 
                END = p4.id
            )
            LEFT JOIN leagues l ON ms.league_id = l.id
            WHERE ms.match_date IS NOT NULL
        """
        
        if league_id_int:
            query = base_query + " AND ms.league_id = %s ORDER BY ms.match_date DESC"
            match_data = execute_query(query, [league_id_int])
        else:
            query = base_query + " ORDER BY ms.match_date DESC"
            match_data = execute_query(query)

        return jsonify(match_data)

    except Exception as e:
        print(f"Error getting PTI analysis match history: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/api/player-season-tracking", methods=["GET", "POST"])
@login_required
def handle_player_season_tracking():
    """Handle getting and updating player season tracking data"""
    try:
        user = session["user"]
        current_year = datetime.now().year

        # Determine current tennis season year (Aug-July seasons)
        current_month = datetime.now().month
        if current_month >= 8:  # Aug-Dec: current season
            season_year = current_year
        else:  # Jan-Jul: previous season
            season_year = current_year - 1

        # Get user's league for filtering
        user_league_id = user.get("league_id", "")
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                pass
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id

        if request.method == "GET":
            # Return current season tracking data for all players in user's team/league

            # Get user's team ID to fetch team members
            from app.routes.mobile_routes import get_user_team_id

            team_id = get_user_team_id(user)

            if not team_id:
                return jsonify({"error": "No team found for user"}), 400

            # Get team members
            team_members_query = """
                SELECT p.tenniscores_player_id, p.first_name, p.last_name
                FROM players p
                WHERE p.team_id = %s AND p.is_active = TRUE
            """
            team_members = execute_query(team_members_query, [team_id])

            # Get existing tracking data for these players
            if team_members and league_id_int:
                player_ids = [
                    member["tenniscores_player_id"] for member in team_members
                ]
                placeholders = ",".join(["%s"] * len(player_ids))

                tracking_query = f"""
                    SELECT player_id, forced_byes, not_available, injury
                    FROM player_season_tracking
                    WHERE player_id IN ({placeholders})
                    AND league_id = %s
                    AND season_year = %s
                """
                tracking_data = execute_query(
                    tracking_query, player_ids + [league_id_int, season_year]
                )

                # Build response with player names and tracking data
                tracking_dict = {row["player_id"]: row for row in tracking_data}

                result = []
                for member in team_members:
                    player_id = member["tenniscores_player_id"]
                    tracking = tracking_dict.get(
                        player_id, {"forced_byes": 0, "not_available": 0, "injury": 0}
                    )

                    result.append(
                        {
                            "player_id": player_id,
                            "name": f"{member['first_name']} {member['last_name']}",
                            "forced_byes": tracking["forced_byes"],
                            "not_available": tracking["not_available"],
                            "injury": tracking["injury"],
                        }
                    )

                return jsonify({"season_year": season_year, "players": result})
            else:
                return jsonify({"season_year": season_year, "players": []})

        elif request.method == "POST":
            # Update tracking data for a specific player
            data = request.get_json()

            if not data or not all(
                key in data for key in ["player_id", "type", "value"]
            ):
                return (
                    jsonify(
                        {"error": "Missing required fields: player_id, type, value"}
                    ),
                    400,
                )

            player_id = data["player_id"]
            tracking_type = data["type"]  # 'forced_byes', 'not_available', or 'injury'
            value = int(data["value"])

            # Validate tracking type
            if tracking_type not in ["forced_byes", "not_available", "injury"]:
                return jsonify({"error": "Invalid tracking type"}), 400

            # Validate value
            if value < 0 or value > 50:  # Reasonable limits
                return jsonify({"error": "Value must be between 0 and 50"}), 400

            if not league_id_int:
                return jsonify({"error": "Could not determine user league"}), 400

            # Use UPSERT to insert or update the tracking record
            upsert_query = f"""
                INSERT INTO player_season_tracking (player_id, league_id, season_year, {tracking_type})
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (player_id, league_id, season_year)
                DO UPDATE SET 
                    {tracking_type} = EXCLUDED.{tracking_type},
                    updated_at = CURRENT_TIMESTAMP
                RETURNING forced_byes, not_available, injury
            """

            result = execute_query_one(
                upsert_query, [player_id, league_id_int, season_year, value]
            )

            if result:
                # Log the activity
                log_user_activity(
                    user["email"],
                    "update_season_tracking",
                    action=f"Updated {tracking_type} to {value} for player {player_id}",
                )

                return jsonify(
                    {
                        "success": True,
                        "player_id": player_id,
                        "season_year": season_year,
                        "forced_byes": result["forced_byes"],
                        "not_available": result["not_available"],
                        "injury": result["injury"],
                    }
                )
            else:
                return jsonify({"error": "Failed to update tracking data"}), 500

    except Exception as e:
        print(f"Error in player season tracking API: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/api/switch-team-context", methods=["POST"])
@login_required
def switch_team_context():
    """API endpoint for switching user's team/league context using existing league_context field"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        team_id = data.get("team_id")
        
        if not team_id:
            return jsonify({"success": False, "error": "team_id required"}), 400
        
        user_id = session["user"]["id"]
        
        # Get the league for this team and verify user access
        team_league_query = """
            SELECT t.league_id, l.league_name, t.team_name
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s AND t.id = %s AND p.is_active = TRUE
        """
        team_info = execute_query_one(team_league_query, [user_id, team_id])
        
        if not team_info:
            return jsonify({"success": False, "error": "User does not have access to this team"}), 403
        
        league_id = team_info["league_id"]
        league_name = team_info["league_name"]
        team_name = team_info["team_name"]
        
        # Update user's league_context field
        update_query = "UPDATE users SET league_context = %s WHERE id = %s"
        execute_query(update_query, [league_id, user_id])
        
        # Update current session
        session["user"]["league_context"] = league_id
        session.modified = True
        
        return jsonify({
            "success": True,
            "league_id": league_id,
            "team_id": team_id,
            "message": f"Switched to {team_name} ({league_name})"
        })
            
    except Exception as e:
        logger.error(f"Error switching team context: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to switch team context"
        }), 500


@api_bp.route("/api/user-context-info", methods=["GET"])
@login_required
def get_user_context_info():
    """Get current user context information"""
    try:
        from app.services.context_service import ContextService
        
        user_id = session["user"]["id"]
        
        # Get context info
        context_info = ContextService.get_context_info(user_id)
        user_leagues = ContextService.get_user_leagues(user_id)
        user_teams = ContextService.get_user_teams(user_id)
        
        return jsonify({
            "success": True,
            "context": context_info,
            "leagues": user_leagues,
            "teams": user_teams,
            "is_multi_league": len(user_leagues) > 1,
            "is_multi_team": len(user_teams) > 1
        })
        
    except Exception as e:
        logger.error(f"Error getting user context info: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to get context info"
        }), 500


@api_bp.route("/api/switch-league", methods=["POST"])
@login_required
def switch_league():
    """Simple league switching API using new session service"""
    try:
        from app.services.session_service import switch_user_league, get_session_data_for_user
        import logging

        logger = logging.getLogger(__name__)
        data = request.get_json()
        
        if not data or not data.get("league_id"):
            return jsonify({"success": False, "error": "league_id required"}), 400
        
        user_email = session["user"]["email"]
        new_league_id = data.get("league_id")
        
        logger.info(f"League switch requested: {user_email} -> {new_league_id}")
        
        # Switch to new league
        if switch_user_league(user_email, new_league_id):
            # Rebuild session from database
            fresh_session_data = get_session_data_for_user(user_email)
            if fresh_session_data:
                session["user"] = fresh_session_data
                session.modified = True
                
                return jsonify({
                    "success": True,
                    "message": f"Switched to {fresh_session_data['league_name']}",
                    "user": fresh_session_data
                })
            else:
                return jsonify({"success": False, "error": "Failed to update session"}), 500
        else:
            return jsonify({
                "success": False, 
                "error": f"Could not switch to {new_league_id}. You may not have a player record in that league."
            }), 400
            
    except Exception as e:
        logger.error(f"Error switching league: {str(e)}")
        return jsonify({"success": False, "error": f"League switch failed: {str(e)}"}), 500


@api_bp.route("/api/get-user-teams", methods=["GET"])
@login_required
def get_user_teams():
    """
    API endpoint to get user's teams for enhanced league/team context switching.
    Returns teams user belongs to and current team context.
    """
    try:
        user_id = session["user"]["id"]
        user_email = session["user"]["email"]
        
        # Get user's teams across all leagues
        teams_query = """
            SELECT DISTINCT 
                t.id,
                t.team_name,
                c.name as club_name,
                s.name as series_name,
                l.id as league_db_id,
                l.league_id as league_string_id,
                l.league_name,
                COUNT(ms.id) as match_count
            FROM teams t
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            LEFT JOIN match_scores ms ON (t.id = ms.home_team_id OR t.id = ms.away_team_id)
            WHERE upa.user_id = %s 
                AND p.is_active = TRUE 
                AND t.is_active = TRUE
            GROUP BY t.id, t.team_name, c.name, s.name, l.id, l.league_id, l.league_name
            ORDER BY l.league_name, c.name, s.name
        """
        
        teams_result = execute_query(teams_query, [user_id])
        teams = [dict(team) for team in teams_result] if teams_result else []
        
        # Get current team context based on user's league_context
        current_team = None
        if session["user"].get("league_context"):
            league_context = session["user"]["league_context"]
            
            # Find user's active team in current league context
            current_team_query = """
                SELECT DISTINCT
                    t.id,
                    t.team_name,
                    c.name as club_name,
                    s.name as series_name,
                    l.id as league_db_id,
                    l.league_id as league_string_id,
                    l.league_name
                FROM teams t
                JOIN players p ON t.id = p.team_id
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                JOIN clubs c ON t.club_id = c.id
                JOIN series s ON t.series_id = s.id
                JOIN leagues l ON t.league_id = l.id
                WHERE upa.user_id = %s 
                    AND l.id = %s
                    AND p.is_active = TRUE 
                    AND t.is_active = TRUE
                ORDER BY t.team_name
                LIMIT 1
            """
            
            current_team_result = execute_query_one(current_team_query, [user_id, league_context])
            if current_team_result:
                current_team = dict(current_team_result)
        
        # Filter teams for current league if we have league context
        current_league_teams = []
        if session["user"].get("league_context"):
            league_context = session["user"]["league_context"]
            current_league_teams = [team for team in teams if team["league_db_id"] == league_context]
        
        return jsonify({
            "success": True,
            "teams": teams,
            "current_team": current_team,
            "current_league_teams": current_league_teams,
            "has_multiple_teams": len(teams) > 1,
            "has_multiple_teams_in_current_league": len(current_league_teams) > 1,
            "user_id": user_id
        })
        
    except Exception as e:
        logger.error(f"Error getting user teams for user {session.get('user', {}).get('id', 'unknown')}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "teams": [],
            "current_team": None
        }), 500


@api_bp.route("/api/get-user-leagues", methods=["GET"])
@login_required
def get_user_leagues():
    """
    API endpoint to check if user has associations in multiple leagues.
    Used for league selector visibility - includes all associations, not just team assignments.
    """
    try:
        user_id = session["user"]["id"]
        
        # Get all leagues user has associations in (regardless of team assignments)
        leagues_query = """
            SELECT DISTINCT 
                l.id as league_db_id,
                l.league_id as league_string_id,
                l.league_name,
                COUNT(p.id) as player_count
            FROM leagues l
            JOIN players p ON l.id = p.league_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s 
                AND p.is_active = TRUE
            GROUP BY l.id, l.league_id, l.league_name
            ORDER BY l.league_name
        """
        
        leagues_result = execute_query(leagues_query, [user_id])
        leagues = [dict(league) for league in leagues_result] if leagues_result else []
        
        return jsonify({
            "success": True,
            "leagues": leagues,
            "has_multiple_leagues": len(leagues) > 1,
            "league_count": len(leagues)
        })
        
    except Exception as e:
        logger.error(f"Error getting user leagues for user {session.get('user', {}).get('id', 'unknown')}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "leagues": [],
            "has_multiple_leagues": False
        }), 500


@api_bp.route("/api/switch-team-in-league", methods=["POST"])
@login_required
def switch_team_in_league():
    """
    API endpoint for switching user's team/club within the same league.
    This is separate from league switching - it only changes team context within current league.
    """
    try:
        from app.services.session_service import (
            switch_user_team_in_league, 
            get_session_data_for_user_team
        )
        import logging

        logger = logging.getLogger(__name__)
        data = request.get_json()
        
        if not data or not data.get("team_id"):
            return jsonify({"success": False, "error": "team_id required"}), 400
        
        team_id = data.get("team_id")
        user_email = session["user"]["email"]
        
        # Validate team switch using session service
        if not switch_user_team_in_league(user_email, team_id):
            return jsonify({"success": False, "error": "Cannot switch to this team"}), 400
        
        # Build new session data with team context
        fresh_session_data = get_session_data_for_user_team(user_email, team_id)
        if not fresh_session_data:
            return jsonify({"success": False, "error": "Failed to build session with new team"}), 500
        
        # Update session
        session["user"] = fresh_session_data
        session.modified = True
        
        logger.info(f"User {user_email} switched to team {fresh_session_data['team_name']} (ID: {team_id})")
        
        return jsonify({
            "success": True,
            "team_id": team_id,
            "team_name": fresh_session_data.get("team_name"),
            "club_name": fresh_session_data["club"],
            "series_name": fresh_session_data["series"],
            "league_name": fresh_session_data["league_name"],
            "message": f"Switched to {fresh_session_data['club']} - {fresh_session_data['series']}"
        })
        
    except Exception as e:
        logger.error(f"Error switching team: {str(e)}")
        return jsonify({"success": False, "error": f"Team switch failed: {str(e)}"}), 500


@api_bp.route("/api/get-user-teams-in-current-league", methods=["GET"])
@login_required
def get_user_teams_in_current_league():
    """
    API endpoint to get user's teams within their current league only.
    Used for club/team switching within the same league.
    """
    try:
        logger = logging.getLogger(__name__)
        user_id = session["user"]["id"]
        current_league_context = session["user"].get("league_context")
        
        logger.info(f"get_user_teams_in_current_league called for user {user_id}, league_context: {current_league_context}")
        logger.info(f"Full session user data: {session.get('user', {})}")
        
        # Fallback to league_id if league_context is not set
        if not current_league_context:
            current_league_context = session["user"].get("league_id")
            logger.info(f"league_context was None, trying league_id fallback: {current_league_context}")
        
        # Convert string league_id to numeric league_id if needed
        if isinstance(current_league_context, str):
            league_lookup_query = "SELECT id FROM leagues WHERE league_id = %s"
            league_record = execute_query_one(league_lookup_query, [current_league_context])
            if league_record:
                current_league_context = league_record["id"]
                logger.info(f"Converted string league_id to numeric id: {current_league_context}")
            else:
                logger.error(f"Could not find league with league_id: {current_league_context}")
                return jsonify({
                    "success": False,
                    "error": "Invalid league context",
                    "teams": []
                }), 400
        
        if not current_league_context:
            logger.error(f"No league context or league_id found for user {user_id}")
            return jsonify({
                "success": False,
                "error": "No league context found",
                "teams": []
            }), 400
        
        # Get user's teams in current league only
        teams_query = """
            SELECT DISTINCT 
                t.id as team_id,
                t.team_name,
                c.name as club_name,
                s.name as series_name,
                l.league_name,
                COUNT(ms.id) as match_count,
                -- Check if this is the current team context
                CASE WHEN t.id = %s THEN true ELSE false END as is_current
            FROM teams t
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            LEFT JOIN match_scores ms ON (t.id = ms.home_team_id OR t.id = ms.away_team_id)
            WHERE upa.user_id = %s 
                AND t.league_id = %s
                AND p.is_active = TRUE 
                AND t.is_active = TRUE
            GROUP BY t.id, t.team_name, c.name, s.name, l.league_name
            ORDER BY c.name, s.name
        """
        
        current_team_id = session["user"].get("team_id")
        logger.info(f"Executing teams query with params: current_team_id={current_team_id}, user_id={user_id}, league_context={current_league_context}")
        
        teams_result = execute_query(teams_query, [current_team_id, user_id, current_league_context])
        teams = [dict(team) for team in teams_result] if teams_result else []
        
        logger.info(f"Query returned {len(teams)} teams: {teams}")
        
        return jsonify({
            "success": True,
            "teams": teams,
            "has_multiple_teams": len(teams) > 1,
            "current_league_id": current_league_context
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Error getting user teams in current league: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        logger.error(f"Session data: {session.get('user', {})}")
        return jsonify({
            "success": False,
            "error": str(e),
            "teams": []
        }), 500


@api_bp.route("/api/create-team/players")
@login_required
def get_create_team_players():
    """Get all players with PTI data for team creation analysis"""
    try:
        user = session["user"]
        user_league_id = user.get("league_id", "")
        
        # Convert league_id to integer foreign key
        league_id_int = None
        if user_league_id:
            try:
                # Convert league_id to string for database query (league_id column is VARCHAR)
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [str(user_league_id)]
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                print(f"Error converting league_id {user_league_id}: {e}")
                pass
        
        # Get all players with PTI data from user's league
        players_query = """
            SELECT 
                p.id,
                p.first_name,
                p.last_name,
                p.tenniscores_player_id,
                p.pti,
                p.wins,
                p.losses,
                c.name as club_name,
                s.name as series_name,
                s.id as series_id,
                CASE 
                    WHEN p.wins + p.losses > 0 
                    THEN ROUND((p.wins::DECIMAL / (p.wins + p.losses)) * 100, 1)
                    ELSE 0 
                END as win_rate
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.is_active = TRUE
            AND p.pti IS NOT NULL
            AND p.pti > 0
            {}
            ORDER BY p.pti ASC
        """.format("AND p.league_id = %s" if league_id_int else "")
        
        params = [league_id_int] if league_id_int else []
        players_data = execute_query(players_query, params)
        
        players = []
        for player in players_data:
            # Convert Chicago format to Series format for UI display
            display_series_name = convert_chicago_to_series_for_ui(player["series_name"]) if player["series_name"] else "Unknown"
            
            players.append({
                "id": player["id"],
                "name": f"{player['first_name']} {player['last_name']}",
                "first_name": player["first_name"],
                "last_name": player["last_name"],
                "tenniscores_player_id": player["tenniscores_player_id"],
                "pti": float(player["pti"]) if player["pti"] else 0.0,
                "wins": player["wins"] or 0,
                "losses": player["losses"] or 0,
                "win_rate": float(player["win_rate"]) if player["win_rate"] else 0.0,
                "club": player["club_name"] or "Unknown",
                "series": display_series_name,
                "series_id": player["series_id"]
            })
        
        return jsonify({
            "success": True,
            "players": players,
            "total_players": len(players)
        })
        
    except Exception as e:
        print(f"Error getting create team players: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to get players data"}), 500


@api_bp.route("/api/create-team/analyze-series")
@login_required
def analyze_series_pti_ranges():
    """Analyze PTI ranges for all series to provide expert guidance"""
    try:
        user = session["user"]
        user_league_id = user.get("league_id", "")
        
        # Convert league_id to integer foreign key
        league_id_int = None
        if user_league_id:
            try:
                # Convert league_id to string for database query (league_id column is VARCHAR)
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [str(user_league_id)]
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                print(f"Error converting league_id {user_league_id}: {e}")
                pass
        
        # Get PTI statistics by series (excluding SW series)
        base_query = """
            SELECT 
                s.name as series_name,
                s.id as series_id,
                COUNT(p.id) as player_count,
                MIN(p.pti) as min_pti,
                MAX(p.pti) as max_pti,
                AVG(p.pti) as avg_pti,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY p.pti) as pti_25th,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY p.pti) as pti_75th,
                STDDEV(p.pti) as pti_stddev
            FROM series s
            JOIN players p ON s.id = p.series_id
            WHERE p.is_active = TRUE
            AND p.pti IS NOT NULL
            AND p.pti > 0
            AND s.name NOT LIKE '%%SW%%'
        """
        
        if league_id_int:
            series_analysis_query = base_query + """
                AND p.league_id = %s
                GROUP BY s.name, s.id
                HAVING COUNT(p.id) >= 3
                ORDER BY AVG(p.pti) ASC
            """
            series_data = execute_query(series_analysis_query, (league_id_int,))
        else:
            series_analysis_query = base_query + """
                GROUP BY s.name, s.id
                HAVING COUNT(p.id) >= 3
                ORDER BY AVG(p.pti) ASC
            """
            series_data = execute_query(series_analysis_query)
        
        series_ranges = []
        for series in series_data:
            # Calculate recommended PTI range using statistical analysis
            avg_pti = float(series["avg_pti"])
            std_dev = float(series["pti_stddev"]) if series["pti_stddev"] else 5.0
            min_pti = float(series["min_pti"])
            max_pti = float(series["max_pti"])
            pti_25th = float(series["pti_25th"])
            pti_75th = float(series["pti_75th"])
            
            # Use inter-quartile range for more robust recommendations
            recommended_min = max(min_pti, pti_25th - (std_dev * 0.5))
            recommended_max = min(max_pti, pti_75th + (std_dev * 0.5))
            
            # Convert Chicago format to Series format for UI display
            display_series_name = convert_chicago_to_series_for_ui(series["series_name"])
            
            series_ranges.append({
                "series_name": display_series_name,
                "series_id": series["series_id"],
                "player_count": series["player_count"],
                "current_range": {
                    "min": round(min_pti, 1),
                    "max": round(max_pti, 1)
                },
                "recommended_range": {
                    "min": round(recommended_min, 1),
                    "max": round(recommended_max, 1)
                },
                "statistics": {
                    "avg": round(avg_pti, 1),
                    "std_dev": round(std_dev, 1),
                    "percentiles": {
                        "25th": round(pti_25th, 1),
                        "75th": round(pti_75th, 1)
                    }
                }
            })
        
        # Sort series numerically using the same logic as other endpoints
        def get_series_sort_key_for_analysis(series_name):
            import re
            
            # Handle series with numeric values: "Chicago 1", "Series 2", "Division 3", etc.
            match = re.match(r'^(?:(Chicago|Series|Division)\s+)?(\d+)([a-zA-Z\s]*)$', series_name)
            if match:
                prefix = match.group(1) or ''
                number = int(match.group(2))
                suffix = match.group(3).strip() if match.group(3) else ''
                
                # Sort by: prefix priority, then number, then suffix
                prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                return (0, prefix_priority, number, suffix)  # Numeric series first
            
            # Handle letter-only series (Series A, Series B, etc.)
            match = re.match(r'^(?:(Chicago|Series|Division)\s+)?([A-Z]+)$', series_name)
            if match:
                prefix = match.group(1) or ''
                letter = match.group(2)
                prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                return (1, prefix_priority, 0, letter)  # Letters after numbers
            
            # Everything else goes last (sorted alphabetically)
            return (2, 0, 0, series_name)

        series_ranges.sort(key=lambda x: get_series_sort_key_for_analysis(x["series_name"]))
        
        return jsonify({
            "success": True,
            "series_ranges": series_ranges,
            "total_series": len(series_ranges)
        })
        
    except Exception as e:
        print(f"Error analyzing series PTI ranges: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to analyze series data"}), 500


@api_bp.route("/api/create-team/calculate-balanced-ranges", methods=["POST"])
@login_required
def calculate_balanced_pti_ranges():
    """Calculate balanced PTI ranges by stratifying all players evenly across series"""
    try:
        user = session["user"]
        user_league_id = user.get("league_id", "")
        
        # Convert league_id to integer foreign key
        league_id_int = None
        if user_league_id:
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [str(user_league_id)]
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                print(f"Error converting league_id {user_league_id}: {e}")
                pass

        # Get all active players with PTI data, sorted by PTI (ascending = lowest first)
        base_players_query = """
            SELECT 
                p.id,
                p.first_name,
                p.last_name,
                p.pti,
                s.name as current_series_name,
                s.id as current_series_id
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.is_active = TRUE
            AND p.pti IS NOT NULL
            AND p.pti > 0
        """
        
        if league_id_int:
            players_query = base_players_query + " AND p.league_id = %s ORDER BY p.pti ASC"
            all_players = execute_query(players_query, [league_id_int])
        else:
            players_query = base_players_query + " ORDER BY p.pti ASC"
            all_players = execute_query(players_query)

        if not all_players:
            return jsonify({"error": "No players with PTI data found"}), 404

        # Get all available series for this league (excluding SW series)
        base_series_query = """
            SELECT DISTINCT s.name as series_name, s.id as series_id
            FROM series s
            JOIN players p ON s.id = p.series_id
            WHERE p.is_active = TRUE
            AND s.name NOT LIKE '%%SW%%'
        """
        
        if league_id_int:
            series_query = base_series_query + " AND p.league_id = %s ORDER BY s.name"
            available_series = execute_query(series_query, [league_id_int])
        else:
            series_query = base_series_query + " ORDER BY s.name"
            available_series = execute_query(series_query)

        if not available_series:
            return jsonify({"error": "No series found"}), 404

        # Sort series numerically for proper ordering
        def get_series_sort_key(series_name):
            import re
            
            # Handle series with numeric values: "Chicago 1", "Series 2", etc.
            match = re.match(r'^(?:(Chicago|Series|Division)\s+)?(\d+)([a-zA-Z\s]*)$', series_name)
            if match:
                number = int(match.group(2))
                return (0, number)  # Numeric series first, by number
            
            # Handle letter-only series
            match = re.match(r'^(?:(Chicago|Series|Division)\s+)?([A-Z]+)$', series_name)
            if match:
                letter = match.group(2)
                return (1, letter)  # Letters after numbers
            
            # Everything else
            return (2, series_name)

        available_series.sort(key=lambda x: get_series_sort_key(x["series_name"]))

        # Get overall PTI range for perfect stratification
        total_players = len(all_players)
        num_series = len(available_series)
        min_overall_pti = float(all_players[0]["pti"])  # Lowest PTI (already sorted)
        max_overall_pti = float(all_players[-1]["pti"])  # Highest PTI
        total_pti_span = max_overall_pti - min_overall_pti

        print(f"Balanced calculation: {total_players} players, {num_series} series")
        print(f"PTI range: {min_overall_pti} - {max_overall_pti} (span: {total_pti_span})")

        # Calculate equal PTI range per series
        if num_series == 0:
            return jsonify({"error": "No series available"}), 404
        
        if total_pti_span == 0:
            # All players have the same PTI - create minimal ranges
            pti_range_per_series = 0.01
        else:
            pti_range_per_series = total_pti_span / num_series

        # Create perfectly contiguous ranges
        balanced_ranges = []
        
        for i, series in enumerate(available_series):
            # Calculate PTI boundaries for this series
            if i == 0:
                # First series starts at absolute minimum
                min_pti = min_overall_pti
            else:
                # Subsequent series start exactly where previous ended + 0.01
                min_pti = balanced_ranges[-1]["current_range"]["max"] + 0.01
            
            if i == num_series - 1:
                # Last series ends at absolute maximum
                max_pti = max_overall_pti
            else:
                # Calculate end of this series' range
                max_pti = min_overall_pti + ((i + 1) * pti_range_per_series)

            # Count how many players fall within this PTI range (convert Decimal to float for comparison)
            players_in_range = [p for p in all_players if min_pti <= float(p["pti"]) <= max_pti]
            players_in_this_series = len(players_in_range)

            # Convert series name for UI display
            display_series_name = convert_chicago_to_series_for_ui(series["series_name"])
            
            # Calculate statistics for this range
            if players_in_range:
                # Convert Decimal types to float for mathematical operations
                pti_values = [float(p["pti"]) for p in players_in_range]
                avg_pti = sum(pti_values) / len(pti_values)
                std_dev = (sum((pti - avg_pti) ** 2 for pti in pti_values) / len(pti_values)) ** 0.5
                lowest_player = min(players_in_range, key=lambda x: float(x["pti"]))
                highest_player = max(players_in_range, key=lambda x: float(x["pti"]))
                lowest_player_name = f"{lowest_player['first_name']} {lowest_player['last_name']}"
                highest_player_name = f"{highest_player['first_name']} {highest_player['last_name']}"
            else:
                avg_pti = (min_pti + max_pti) / 2
                std_dev = 0.0
                lowest_player_name = "None"
                highest_player_name = "None"

            balanced_ranges.append({
                "series_name": display_series_name,
                "series_id": series["series_id"],
                "player_count": players_in_this_series,
                "current_range": {
                    "min": round(min_pti, 2),
                    "max": round(max_pti, 2)
                },
                "recommended_range": {
                    "min": round(min_pti, 2),
                    "max": round(max_pti, 2)
                },
                "statistics": {
                    "avg": round(avg_pti, 2),
                    "std_dev": round(std_dev, 2),
                    "percentiles": {
                        "25th": round(min_pti, 2),
                        "75th": round(max_pti, 2)
                    }
                },
                "stratification_info": {
                    "pti_range_span": round(max_pti - min_pti, 2),
                    "lowest_pti_player": lowest_player_name,
                    "highest_pti_player": highest_player_name,
                    "range_coverage": f"{min_pti:.2f} - {max_pti:.2f}"
                }
            })

        return jsonify({
            "success": True,
            "series_ranges": balanced_ranges,
            "total_series": len(balanced_ranges),
            "total_players": total_players,
            "stratification_summary": {
                "method": "Contiguous PTI Range Stratification",
                "description": "PTI range divided evenly across series with no gaps",
                "pti_range_per_series": round(pti_range_per_series, 2),
                "total_pti_span": round(total_pti_span, 2),
                "lowest_pti": round(min_overall_pti, 2),
                "highest_pti": round(max_overall_pti, 2),
                "coverage": "Complete PTI spectrum with contiguous ranges"
            }
        })
        
    except Exception as e:
        print(f"Error calculating balanced PTI ranges: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to calculate balanced ranges"}), 500


@api_bp.route("/api/create-team/save", methods=["POST"])
@login_required
def save_team_assignments():
    """Save team assignments (for future implementation)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # For now, just validate the data structure
        teams = data.get("teams", {})
        if not teams:
            return jsonify({"error": "No team data provided"}), 400
        
        # Validate each team has players and PTI totals
        validated_teams = {}
        for series_name, team_data in teams.items():
            players = team_data.get("players", [])
            total_pti = team_data.get("total_pti", 0)
            
            if len(players) < 2:
                return jsonify({"error": f"Series {series_name} needs at least 2 players"}), 400
            
            validated_teams[series_name] = {
                "players": players,
                "total_pti": total_pti,
                "avg_pti": total_pti / len(players) if players else 0
            }
        
        # Log the team creation activity
        log_user_activity(
            session["user"]["email"],
            "team_creation",
            page="create_team",
            details=f"Created {len(validated_teams)} teams"
        )
        
        return jsonify({
            "success": True,
            "message": "Team assignments validated successfully",
            "teams": validated_teams
        })
        
    except Exception as e:
        print(f"Error saving team assignments: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to save team assignments"}), 500


@api_bp.route("/api/create-team/update-range", methods=["POST"])
@login_required
def update_pti_range():
    """Update PTI range for a series with real-time validation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        series_id = data.get('series_id')
        series_name = data.get('series_name')
        recommended_range = data.get('recommended_range')
        
        if not all([series_id, series_name, recommended_range]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        min_pti = recommended_range.get('min')
        max_pti = recommended_range.get('max')
        
        if min_pti is None or max_pti is None:
            return jsonify({"success": False, "error": "Invalid range values"}), 400
        
        # Validate range
        if min_pti >= max_pti:
            return jsonify({"success": False, "error": "Minimum PTI must be less than maximum PTI"}), 400
        
        if min_pti < 10 or max_pti > 80:
            return jsonify({"success": False, "error": "PTI values must be between 10 and 80"}), 400
        
        user = session["user"]
        user_email = user.get("email")
        
        # Log the range update action
        log_user_activity(user_email, "pti_range_update", action="update_range", details={
            "series_id": series_id,
            "series_name": series_name,
            "old_range": "unknown",  # Could be tracked if needed
            "new_range": f"{min_pti}-{max_pti}",
            "timestamp": datetime.now().isoformat()
        })
        
        # In a full implementation, you would save this to a settings/preferences table
        # For now, we'll just validate and return success
        
        return jsonify({
            "success": True,
            "message": f"PTI range updated for {series_name}",
            "series_name": series_name,
            "new_range": {
                "min": min_pti,
                "max": max_pti
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error updating PTI range: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": "Failed to update PTI range"}), 500


@api_bp.route("/api/create-team/update-series-range", methods=["POST"])
@login_required  
def update_series_range():
    """Update PTI range for a specific series with enhanced validation and error handling"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False, 
                "error": "No data provided in request body"
            }), 400
        
        series_name = data.get('series_name')
        min_pti = data.get('min_pti')
        max_pti = data.get('max_pti')
        
        # Enhanced field validation
        missing_fields = []
        if not series_name:
            missing_fields.append('series_name')
        if min_pti is None:
            missing_fields.append('min_pti')
        if max_pti is None:
            missing_fields.append('max_pti')
            
        if missing_fields:
            return jsonify({
                "success": False, 
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Convert and validate numeric values
        try:
            min_pti = float(min_pti)
            max_pti = float(max_pti)
        except (ValueError, TypeError) as e:
            return jsonify({
                "success": False, 
                "error": f"Invalid PTI values - must be numeric: {str(e)}"
            }), 400
        
        # Enhanced range validation
        validation_errors = []
        
        if min_pti >= max_pti:
            validation_errors.append("Minimum PTI must be less than maximum PTI")
        
        if abs(max_pti - min_pti) < 0.01:
            validation_errors.append("PTI range must be at least 0.01 points wide")
        
        if min_pti < -30:
            validation_errors.append("Minimum PTI cannot be below -30")
        
        if max_pti > 100:
            validation_errors.append("Maximum PTI cannot exceed 100")
        
        if abs(max_pti - min_pti) > 50:
            validation_errors.append("PTI range cannot exceed 50 points (too wide)")
        
        # Check for reasonable PTI values
        if min_pti > 80:
            validation_errors.append("Minimum PTI above 80 is unrealistic")
        
        if max_pti < -20:
            validation_errors.append("Maximum PTI below -20 is unrealistic")
        
        if validation_errors:
            return jsonify({
                "success": False, 
                "error": "; ".join(validation_errors)
            }), 400
        
        user = session["user"]
        user_email = user.get("email", "unknown")
        
        # Enhanced logging with validation info
        log_user_activity(
            user_email, 
            "series_range_update", 
            action="update_series_range", 
            details={
                "series_name": series_name,
                "min_pti": min_pti,
                "max_pti": max_pti,
                "range_width": round(max_pti - min_pti, 2),
                "validation_passed": True,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # TODO: In a full implementation, you would:
        # 1. Save to series_ranges table
        # 2. Validate against other series for conflicts
        # 3. Update related team assignments
        # 4. Trigger recalculations if needed
        
        # For now, simulate successful update with enhanced response
        return jsonify({
            "success": True,
            "message": f"PTI range successfully updated for {series_name}",
            "series_name": series_name,
            "updated_range": {
                "min": round(min_pti, 2),
                "max": round(max_pti, 2),
                "width": round(max_pti - min_pti, 2)
            },
            "validation": {
                "passed": True,
                "range_check": "valid",
                "bounds_check": "within_limits"
            },
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error in update_series_range: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        # Return structured error response
        return jsonify({
            "success": False, 
            "error": f"Server error: {str(e)}",
            "error_type": "server_error",
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route("/api/debug/database-state")
@login_required
def debug_database_state():
    """Debug endpoint to check database state - helps diagnose staging issues"""
    try:
        from database_utils import execute_query_one, execute_query
        
        # Only allow this for admin users or in debug mode
        user = session.get("user", {})
        if not user.get("is_admin", False):
            return jsonify({"error": "Admin access required"}), 403
            
        debug_info = {}
        
        # Check total match scores
        total_matches = execute_query_one('SELECT COUNT(*) as count FROM match_scores')
        debug_info['total_match_scores'] = total_matches['count']
        
        # Check match scores by league
        league_breakdown = execute_query('''
            SELECT league_id, COUNT(*) as count 
            FROM match_scores 
            GROUP BY league_id 
            ORDER BY count DESC
        ''')
        debug_info['matches_by_league'] = [
            {"league_id": row['league_id'], "count": row['count']} 
            for row in league_breakdown
        ]
        
        # Check recent matches (top 10)
        recent_matches = execute_query('''
            SELECT match_date, home_team, away_team, league_id, 
                   home_team_id, away_team_id,
                   home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
            FROM match_scores 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        debug_info['recent_matches'] = [
            {
                "date": str(row['match_date']),
                "home_team": row['home_team'], 
                "away_team": row['away_team'],
                "league_id": row['league_id'],
                "home_team_id": row['home_team_id'],
                "away_team_id": row['away_team_id'],
                "players": f"{row['home_player_1_id'][:8] if row['home_player_1_id'] else 'None'}..."
            }
            for row in recent_matches
        ]
        
        # Check specific user (Ross Freedman)
        ross_player_id = 'nndz-WkMrK3didjlnUT09'
        user_matches = execute_query_one('''
            SELECT COUNT(*) as count
            FROM match_scores 
            WHERE home_player_1_id = %s OR home_player_2_id = %s 
               OR away_player_1_id = %s OR away_player_2_id = %s
        ''', [ross_player_id] * 4)
        debug_info['ross_freedman_matches'] = user_matches['count']
        
        # Check specific team (15083 - Tennaqua 22)
        team_matches = execute_query_one('''
            SELECT COUNT(*) as count
            FROM match_scores 
            WHERE home_team_id = %s OR away_team_id = %s
        ''', [15083, 15083])
        debug_info['team_15083_matches'] = team_matches['count']
        
        # Check APTA Chicago league (4515) specifically
        apta_matches = execute_query_one('''
            SELECT COUNT(*) as count
            FROM match_scores 
            WHERE league_id = %s
        ''', [4515])
        debug_info['apta_chicago_matches'] = apta_matches['count']
        
        # Check team name matches (fallback)
        tennaqua_name_matches = execute_query_one('''
            SELECT COUNT(*) as count
            FROM match_scores 
            WHERE home_team LIKE %s OR away_team LIKE %s
        ''', ['%Tennaqua%', '%Tennaqua%'])
        debug_info['tennaqua_name_matches'] = tennaqua_name_matches['count']
        
        # Check other key tables for context
        players_count = execute_query_one('SELECT COUNT(*) as count FROM players')
        teams_count = execute_query_one('SELECT COUNT(*) as count FROM teams')
        leagues_count = execute_query_one('SELECT COUNT(*) as count FROM leagues')
        
        debug_info['table_counts'] = {
            'players': players_count['count'],
            'teams': teams_count['count'],
            'leagues': leagues_count['count']
        }
        
        # Check specific user details (safely handle missing columns)
        try:
            ross_user = execute_query_one('''
                SELECT id, first_name, last_name, 
                       tenniscores_player_id, league_context
                FROM users 
                WHERE email = %s
            ''', ['rossfreedman@gmail.com'])
            debug_info['ross_user_details'] = dict(ross_user) if ross_user else None
        except Exception as user_query_error:
            debug_info['ross_user_details'] = {"error": str(user_query_error)}
        
        # Check if team 15083 exists
        team_15083 = execute_query_one('''
            SELECT id, team_name, league_id 
            FROM teams 
            WHERE id = %s
        ''', [15083])
        debug_info['team_15083_details'] = dict(team_15083) if team_15083 else None
        
        return jsonify({
            "success": True,
            "debug_info": debug_info,
            "timestamp": str(datetime.now())
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Debug check failed: {str(e)}",
            "timestamp": str(datetime.now())
        }), 500


@api_bp.route("/api/debug/test-mobile-service")
@login_required
def debug_test_mobile_service():
    """Debug endpoint to test mobile service directly on staging"""
    try:
        from app.services.mobile_service import get_player_analysis
        from app.services.session_service import get_session_data_for_user
        import json
        from datetime import datetime
        
        # Get current user from session
        user_email = session.get("user", {}).get("email")
        if not user_email:
            return jsonify({"error": "No user email in session"}), 400
            
        # Test 1: Check session service
        session_data = get_session_data_for_user(user_email)
        
        # Test 2: Check mobile service
        mobile_result = None
        if session_data:
            mobile_result = get_player_analysis(session_data)
        
        # Return debug info
        debug_info = {
            "timestamp": datetime.now().isoformat(),
            "user_email": user_email,
            "session_data": {
                "exists": session_data is not None,
                "player_id": session_data.get("tenniscores_player_id") if session_data else None,
                "first_name": session_data.get("first_name") if session_data else None,
                "last_name": session_data.get("last_name") if session_data else None,
                "league_id": session_data.get("league_id") if session_data else None,
                "team_id": session_data.get("team_id") if session_data else None,
                "club": session_data.get("club") if session_data else None,
                "series": session_data.get("series") if session_data else None,
            },
            "mobile_service": {
                "success": mobile_result is not None,
                "current_season": mobile_result.get("current_season") if mobile_result else None,
                "career_stats": mobile_result.get("career_stats") if mobile_result else None,
                "error": mobile_result.get("error") if mobile_result else None,
                "pti_data_available": mobile_result.get("pti_data_available") if mobile_result else None,
            },
            "expected_vs_actual": {
                "expected_matches": 18,  # We know Wes should have 18
                "actual_matches": mobile_result.get("current_season", {}).get("matches", 0) if mobile_result else 0,
                "expected_player": "Wes Maher",
                "actual_player": f"{session_data.get('first_name', '')} {session_data.get('last_name', '')}" if session_data else "Unknown"
            }
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }), 500


@api_bp.route("/debug/test-mobile-service-public", methods=["GET"])
def test_mobile_service_public():
    """
    Public debug endpoint for testing mobile service on staging
    This bypasses authentication for staging testing only
    """
    import os
    
    # Only allow on staging environment
    if os.environ.get("RAILWAY_ENVIRONMENT") != "staging":
        return jsonify({"error": "This endpoint only works on staging"}), 403
    
    try:
        # Import here to avoid circular imports
        from app.services.mobile_service import get_mobile_analyze_me_data
        from app.services.session_service import get_session_data_for_user
        
        # Test with Wes Maher email
        test_email = "wmaher@gmail.com"
        
        print(f"🔍 Testing mobile service for: {test_email}")
        
        # Get session data
        session_data = get_session_data_for_user(test_email)
        
        if not session_data:
            return jsonify({
                "error": "No session data found",
                "test_email": test_email
            })
        
        print(f"Session data: {session_data}")
        
        # Get mobile analyze me data
        mobile_data = get_mobile_analyze_me_data(session_data)
        
        return jsonify({
            "success": True,
            "test_email": test_email,
            "session_user": {
                "email": session_data.user.email,
                "player_id": session_data.user.tenniscores_player_id,
                "league_id": session_data.league_id,
                "team_id": session_data.team_id,
                "club": session_data.club,
                "series": session_data.series
            },
            "mobile_data_summary": {
                "total_matches": len(mobile_data.get('matches', [])),
                "win_loss_record": mobile_data.get('win_loss_record'),
                "overall_win_percentage": mobile_data.get('overall_win_percentage'),
                "pti_score": mobile_data.get('pti_score'),
                "pti_percentile": mobile_data.get('pti_percentile')
            },
            "debug_info": {
                "matches_found": len(mobile_data.get('matches', [])),
                "court_performance": mobile_data.get('court_performance', {}),
                "partners": len(mobile_data.get('partners', [])),
                "opponents": len(mobile_data.get('opponents', []))
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "test_email": test_email
        }), 500
