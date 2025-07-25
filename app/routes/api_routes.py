"""
API Routes Blueprint

This module contains all API routes that were moved from the main server.py file.
These routes handle API endpoints for data retrieval, research, analytics, and other backend operations.
"""

import json
import logging
import os
from datetime import datetime, date, time, timedelta
from functools import wraps

import pytz
from flask import Blueprint, g, jsonify, request, session

from app.models.database_models import Player, SessionLocal, User, UserPlayerAssociation
from app.services.api_service import *
from app.services.dashboard_service import log_user_action
from app.services.mobile_service import get_club_players_data
from app.services.groups_service import GroupsService
from database_utils import execute_query, execute_query_one, execute_update, get_db_cursor
from utils.database_player_lookup import find_player_by_database_lookup
from utils.logging import log_user_activity

api_bp = Blueprint("api", __name__)

# Set up logger
logger = logging.getLogger(__name__)


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

        # Normalize series name (convert "Series 2B" to "S2B" for NSTF)
        normalized_series = user_series
        if user_series.startswith("Series "):
            normalized_series = user_series.replace("Series ", "S")

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
            team_query, [user_club, normalized_series, league_id_int]
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
                   u.ad_deuce_preference, u.dominant_hand, u.league_context, u.phone_number
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
            "phone_number": user_data["phone_number"] or "",
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
        update_fields = []
        update_values = []
        
        # Standard fields
        update_fields.extend([
            "first_name = %s", "last_name = %s", "email = %s",
            "ad_deuce_preference = %s", "dominant_hand = %s", "phone_number = %s"
        ])
        update_values.extend([
            data.get("firstName"),
            data.get("lastName"), 
            data.get("email"),
            data.get("adDeuce", ""),
            data.get("dominantHand", ""),
            data.get("phoneNumber", "")
        ])
        
        # Handle password update if provided
        current_password = data.get("currentPassword", "").strip()
        if current_password:
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash(current_password, method='pbkdf2:sha256')
            update_fields.append("password_hash = %s")
            update_values.append(password_hash)
            logger.info(f"Password update requested for user {user_email}")
        
        # Build and execute the update query
        update_query = f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE email = %s
        """
        update_values.append(user_email)
        
        execute_query(update_query, update_values)

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
            
            # Enhanced logging for settings update
            settings_update_details = {
                "action": "settings_update",
                "changes_made": {
                    "league_changed": new_league_id != current_league_id,
                    "club_changed": new_club != current_club,
                    "series_changed": new_series != current_series,
                    "player_lookup_attempted": should_perform_player_lookup,
                    "player_lookup_successful": player_lookup_success
                },
                "old_settings": {
                    "league_id": current_league_id,
                    "club": current_club,
                    "series": current_series,
                    "had_player_id": bool(current_tenniscores_player_id)
                },
                "new_settings": {
                    "league_id": fresh_session_data.get("league_id"),
                    "club": fresh_session_data.get("club"),
                    "series": fresh_session_data.get("series"),
                    "has_player_id": bool(fresh_session_data.get("tenniscores_player_id"))
                },
                "personal_info": {
                    "first_name": data.get("firstName"),
                    "last_name": data.get("lastName"),
                    "phone_updated": bool(data.get("phoneNumber")),
                    "dominant_hand": data.get("dominantHand", ""),
                    "ad_deuce_preference": data.get("adDeuce", ""),
                    "password_changed": bool(current_password)
                }
            }
            
            log_user_activity(
                user_email,
                "settings_update",
                action="update_user_settings",
                details=settings_update_details
            )
            
            # Add player lookup status and password update to response
            success_message = "Settings updated successfully"
            if current_password:
                success_message += " and password changed"
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

        # Enhanced logging for find people to play search
        search_filters = {}
        if series_filter: search_filters["series"] = series_filter
        if first_name_filter: search_filters["first_name"] = first_name_filter
        if last_name_filter: search_filters["last_name"] = last_name_filter
        if pti_min is not None: search_filters["pti_min"] = pti_min
        if pti_max is not None: search_filters["pti_max"] = pti_max
        search_filters["club_only"] = club_only
        
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
        
        # Log the search activity with detailed filters and results
        search_details = {
            "search_context": "find_people_to_play",
            "filters_used": search_filters,
            "results_count": len(result.get("players", [])),
            "user_league": session["user"].get("league_id", "Unknown"),
            "user_club": session["user"].get("club", "Unknown"),
            "user_series": session["user"].get("series", "Unknown")
        }
        # Add filters_applied summary
        filters = []
        if first_name_filter and last_name_filter:
            filters.append(f"name: {first_name_filter} {last_name_filter}")
        elif first_name_filter:
            filters.append(f"name: {first_name_filter}")
        elif last_name_filter:
            filters.append(f"name: {last_name_filter}")
        if series_filter: filters.append(f"series: {series_filter}")
        if pti_min is not None: filters.append(f"PTI min: {pti_min}")
        if pti_max is not None: filters.append(f"PTI max: {pti_max}")
        if club_only: filters.append("club only: true")
        filters_applied = ", ".join(filters) if filters else "no filters"
        search_details["filters_applied"] = filters_applied
        
        # Add top results if any found
        if result.get("players"):
            top_results = []
            for player in result["players"][:3]:
                player_info = f"{player.get('name', 'Unknown')}"
                if player.get("pti"):
                    player_info += f" (PTI: {player['pti']})"
                if player.get("series"):
                    player_info += f" - {player['series']}"
                top_results.append(player_info)
            search_details["top_results"] = top_results
        
        log_user_activity(
            session["user"]["email"],
            "player_search",
            action="find_people_to_play",
            details=search_details
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
        user_email = session["user"]["email"]
        
        # Store current context for logging
        current_context = {
            "from_team_id": session["user"].get("team_id"),
            "from_league_id": session["user"].get("league_id"),
            "from_club": session["user"].get("club", "Unknown"),
            "from_series": session["user"].get("series", "Unknown")
        }
        
        # Get the league for this team and verify user access
        team_league_query = """
            SELECT t.league_id, l.league_name, t.team_name, c.name as club_name, s.name as series_name
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s AND t.id = %s AND p.is_active = TRUE
        """
        team_info = execute_query_one(team_league_query, [user_id, team_id])
        
        if not team_info:
            # Log failed team switch attempt
            switch_details = {
                "action": "team_switch_attempt",
                "from_context": current_context,
                "to_team_id": team_id,
                "switch_method": "switch_team_context_api",
                "success": False,
                "error": "User does not have access to this team"
            }
            
            log_user_activity(
                user_email,
                "team_switch",
                action="switch_team_context_failed",
                details=switch_details
            )
            
            return jsonify({"success": False, "error": "User does not have access to this team"}), 403
        
        league_id = team_info["league_id"]
        league_name = team_info["league_name"]
        team_name = team_info["team_name"]
        club_name = team_info["club_name"]
        series_name = team_info["series_name"]
        
        # Update user's league_context field
        update_query = "UPDATE users SET league_context = %s WHERE id = %s"
        execute_query(update_query, [league_id, user_id])
        
        # Update current session
        session["user"]["league_context"] = league_id
        session.modified = True
        
        # Enhanced logging for successful team switch
        switch_details = {
            "action": "team_switch_successful",
            "from_context": current_context,
            "to_context": {
                "team_id": team_id,
                "team_name": team_name,
                "club_name": club_name,
                "series_name": series_name,
                "league_id": league_id,
                "league_name": league_name
            },
            "switch_method": "switch_team_context_api",
            "success": True
        }
        
        log_user_activity(
            user_email,
            "team_switch",
            action="switch_team_context_success",
            details=switch_details
        )
        
        return jsonify({
            "success": True,
            "league_id": league_id,
            "team_id": team_id,
            "message": f"Switched to {team_name} ({league_name})"
        })
            
    except Exception as e:
        # Log the error with context
        error_details = {
            "action": "team_switch_error",
            "error": str(e),
            "switch_method": "switch_team_context_api",
            "success": False,
            "attempted_team_id": data.get("team_id") if 'data' in locals() else None
        }
        
        log_user_activity(
            session["user"]["email"],
            "team_switch",
            action="switch_team_context_error", 
            details=error_details
        )
        
        logger.error(f"Error switching team context: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to switch team context"
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
        
        logger.info(f"Received switch league request data: {data}")
        
        if not data or not data.get("league_id"):
            logger.error(f"Missing league_id in request data: {data}")
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


@api_bp.route("/api/session-refresh-status", methods=["GET"])
@login_required
def get_session_refresh_status():
    """
    Get session refresh status for current user and system-wide statistics
    Useful for debugging ETL-related session issues
    """
    try:
        from data.etl.database_import.session_refresh_service import SessionRefreshService
        import logging
        
        logger = logging.getLogger(__name__)
        user_email = session["user"]["email"]
        
        # Get user-specific refresh status
        user_needs_refresh = SessionRefreshService.should_refresh_session(user_email)
        
        # Get system-wide refresh status
        system_status = SessionRefreshService.get_refresh_status()
        
        # Get refresh signal details for current user if exists
        user_signal = None
        if user_needs_refresh:
            from database_utils import execute_query_one
            user_signal = execute_query_one("""
                SELECT user_id, old_league_id, new_league_id, league_name, 
                       created_at, is_refreshed, refreshed_at
                FROM user_session_refresh_signals
                WHERE email = %s AND is_refreshed = FALSE
                ORDER BY created_at DESC
                LIMIT 1
            """, [user_email])
            
            if user_signal:
                user_signal = dict(user_signal)
        
        response_data = {
            "user_email": user_email,
            "user_needs_refresh": user_needs_refresh,
            "user_signal": user_signal,
            "system_status": system_status
        }
        
        return jsonify({
            "success": True,
            "data": response_data
        })
        
    except Exception as e:
        logger.error(f"Error getting session refresh status: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to get refresh status: {str(e)}"
        }), 500


@api_bp.route("/api/refresh-session", methods=["POST"])
@login_required  
def manual_refresh_session():
    """
    Manually refresh user's session (for testing/debugging)
    This forces a session refresh regardless of signals
    """
    try:
        from app.services.session_service import get_session_data_for_user
        import logging
        
        logger = logging.getLogger(__name__)
        user_email = session["user"]["email"]
        
        # Get fresh session data
        fresh_session_data = get_session_data_for_user(user_email)
        
        if fresh_session_data:
            # Update current session
            old_league_name = session["user"].get("league_name", "Unknown")
            session["user"] = fresh_session_data
            session.modified = True
            
            new_league_name = fresh_session_data.get("league_name", "Unknown")
            
            logger.info(f"Manual session refresh for {user_email}: {old_league_name} → {new_league_name}")
            
            return jsonify({
                "success": True,
                "message": "Session refreshed successfully",
                "old_league": old_league_name,
                "new_league": new_league_name,
                "user": fresh_session_data
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to get fresh session data"
            }), 500
            
    except Exception as e:
        logger.error(f"Error manually refreshing session: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Session refresh failed: {str(e)}"
        }), 500


@api_bp.route("/api/cleanup-session-refresh-signals", methods=["POST"])
@login_required
def cleanup_session_refresh_signals():
    """
    Admin endpoint to cleanup old session refresh signals
    """
    try:
        user = session["user"]
        if not user.get("is_admin"):
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        from data.etl.database_import.session_refresh_service import SessionRefreshService
        
        # Get days parameter (default 7)
        data = request.get_json() or {}
        days_old = data.get("days_old", 7)
        
        cleaned_count = SessionRefreshService.cleanup_old_refresh_signals(days_old)
        
        return jsonify({
            "success": True,
            "message": f"Cleaned up session refresh signals older than {days_old} days",
            "cleaned_count": cleaned_count
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Cleanup failed: {str(e)}"
        }), 500


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
        current_league_context = session["user"].get("league_context")
        
        # If no league context, try to get it from league_id
        if not current_league_context:
            current_league_context = session["user"].get("league_id")
        
        # If still no league context, use NULL for the comparison
        if not current_league_context:
            current_league_context = None
        
        # Add logging to debug the issue
        logger.info(f"get_user_leagues - user_id: {user_id}, current_league_context: {current_league_context}")
        logger.info(f"Session user data: {session.get('user', {})}")
        
        leagues_query = """
            SELECT DISTINCT 
                l.id as league_db_id,
                l.league_id as league_string_id,
                l.league_name,
                COUNT(p.id) as player_count,
                CASE WHEN l.id = %s THEN true ELSE false END as is_current
            FROM leagues l
            JOIN players p ON l.id = p.league_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s 
                AND p.is_active = TRUE
            GROUP BY l.id, l.league_id, l.league_name
            ORDER BY l.league_name
        """
        
        leagues_result = execute_query(leagues_query, [current_league_context, user_id])
        logger.info(f"Query returned {len(leagues_result) if leagues_result else 0} leagues")
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


# ==========================================
# PICKUP GAMES API ENDPOINTS
# ==========================================

@api_bp.route("/api/pickup-games", methods=["GET"])
@login_required
def get_pickup_games():
    """Get all pickup games (upcoming and past) with participant details"""
    try:
        # Get filter type from query parameters
        game_type = request.args.get('type', 'public')  # default to public
        
        # Determine is_private filter based on type
        if game_type == 'private':
            is_private_filter = "AND pg.is_private = true"
        else:  # public or no type specified
            is_private_filter = "AND pg.is_private = false"
        
        # Get current date/time for determining upcoming vs past
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()
        
        # Get current user's clubs for filtering
        user = session.get("user", {})
        user_id = user.get("id")
        
        # Build club filtering condition
        club_filter = ""
        if user_id:
            club_filter = """
                AND (
                    pg.club_only = false OR 
                    pg.club_id IS NULL OR
                    (pg.club_only = true AND pg.club_id IN (
                        SELECT DISTINCT p.club_id 
                        FROM user_player_associations upa
                        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                        WHERE upa.user_id = %s AND p.club_id IS NOT NULL
                    ))
                )
            """
        
        # Query for upcoming games (future date or today but future time)
        upcoming_query = f"""
            SELECT 
                pg.id,
                pg.description,
                pg.game_date,
                pg.game_time,
                pg.players_requested,
                pg.players_committed,
                pg.pti_low,
                pg.pti_high,
                pg.series_low,
                pg.series_high,
                pg.club_only,
                pg.is_private,
                pg.creator_user_id,
                pg.created_at,
                pg.club_id,
                COUNT(pgp.id) as actual_participants
            FROM pickup_games pg
            LEFT JOIN pickup_game_participants pgp ON pg.id = pgp.pickup_game_id
            WHERE ((pg.game_date > %s) OR (pg.game_date = %s AND pg.game_time > %s))
            {is_private_filter}
            {club_filter}
            GROUP BY pg.id
            ORDER BY pg.game_date ASC, pg.game_time ASC
        """
        
        # Query for past games
        past_query = f"""
            SELECT 
                pg.id,
                pg.description,
                pg.game_date,
                pg.game_time,
                pg.players_requested,
                pg.players_committed,
                pg.pti_low,
                pg.pti_high,
                pg.series_low,
                pg.series_high,
                pg.club_only,
                pg.is_private,
                pg.creator_user_id,
                pg.created_at,
                pg.club_id,
                COUNT(pgp.id) as actual_participants
            FROM pickup_games pg
            LEFT JOIN pickup_game_participants pgp ON pg.id = pgp.pickup_game_id
            WHERE ((pg.game_date < %s) OR (pg.game_date = %s AND pg.game_time <= %s))
            {is_private_filter}
            {club_filter}
            GROUP BY pg.id
            ORDER BY pg.game_date DESC, pg.game_time DESC
        """
        
        # Build parameters list for queries
        query_params = [current_date, current_date, current_time]
        if user_id and club_filter:
            query_params.append(user_id)
        
        upcoming_games = execute_query(upcoming_query, query_params)
        past_games = execute_query(past_query, query_params)
        
        # Helper function to get participants for a game
        def get_game_participants(game_id):
            """Get list of participants with user details for a game"""
            participants_query = """
                SELECT 
                    pgp.id,
                    pgp.user_id,
                    pgp.joined_at,
                    u.first_name,
                    u.last_name,
                    u.email
                FROM pickup_game_participants pgp
                JOIN users u ON pgp.user_id = u.id
                WHERE pgp.pickup_game_id = %s
                ORDER BY pgp.joined_at ASC
            """
            participants = execute_query(participants_query, [game_id])
            
            if not participants:
                return []
            
            return [
                {
                    "user_id": p["user_id"],
                    "name": f"{p['first_name']} {p['last_name']}".strip(),
                    "first_name": p["first_name"],
                    "last_name": p["last_name"],
                    "email": p["email"],
                    "joined_at": p["joined_at"].isoformat() if p["joined_at"] else None
                }
                for p in participants
            ]
        
        # Helper function to calculate game status
        def get_game_status(players_requested, actual_participants):
            if actual_participants >= players_requested:
                return "Closed"
            elif actual_participants >= players_requested * 0.8:  # 80% full
                return "Nearly Full"
            else:
                return "Open"
        
        # Get current user ID to check participation
        user = session["user"]
        current_user_id = user.get("id")
        
        # Helper function to check if user has joined a game
        def user_has_joined(game_id):
            if not current_user_id:
                return False
            participation_check = execute_query_one(
                "SELECT id FROM pickup_game_participants WHERE pickup_game_id = %s AND user_id = %s",
                [game_id, current_user_id]
            )
            return participation_check is not None
        
        # Helper function to get series criteria display
        def get_series_criteria_display(series_low_id, series_high_id):
            if not series_low_id and not series_high_id:
                return "All Series"
            
            series_names = []
            if series_low_id:
                series_record = execute_query_one("SELECT name FROM series WHERE id = %s", [series_low_id])
                if series_record:
                    series_names.append(series_record["name"])
            
            if series_high_id:
                series_record = execute_query_one("SELECT name FROM series WHERE id = %s", [series_high_id])
                if series_record:
                    series_names.append(series_record["name"])
            
            if len(series_names) == 2 and series_names[0] != series_names[1]:
                return f"Series {series_names[0]} to {series_names[1]}"
            elif len(series_names) == 1:
                return f"Series {series_names[0]} and below"
            else:
                return "All Series"
        
        # Helper function to format game data
        def format_game(game):
            # Get pickup game's club name for display
            game_club_name = "All Clubs"  # Default for games without specific club
            if game.get("club_id"):
                club_record = execute_query_one("SELECT name FROM clubs WHERE id = %s", [game["club_id"]])
                if club_record:
                    game_club_name = club_record["name"]
            
            # Get participants
            participants = get_game_participants(game["id"])
            
            # Calculate available slots
            available_slots = max(0, game["players_requested"] - len(participants))
            
            return {
                "id": game["id"],
                "description": game["description"],
                "date": game["game_date"].strftime('%Y-%m-%d'),
                "time": game["game_time"].strftime('%H:%M'),
                "formatted_date": game["game_date"].strftime('%A, %b %d'),
                "formatted_time": game["game_time"].strftime('%I:%M %p').lstrip('0'),
                "players_requested": game["players_requested"],
                "players_committed": game["actual_participants"],
                "status": get_game_status(game["players_requested"], game["actual_participants"]),
                "pti_range": f"{game['pti_low']}-{game['pti_high']}",
                "series_criteria": get_series_criteria_display(game["series_low"], game["series_high"]),
                "club_only": game["club_only"],
                "club_name": game_club_name,
                "club_id": game.get("club_id"),
                "creator_user_id": game["creator_user_id"],
                "user_has_joined": user_has_joined(game["id"]),
                # New fields for participants and slots
                "participants": participants,
                "available_slots": available_slots,
                "slots_filled": len(participants),
                "is_full": len(participants) >= game["players_requested"]
            }
        
        # Format the results
        upcoming_formatted = [format_game(game) for game in upcoming_games] if upcoming_games else []
        past_formatted = [format_game(game) for game in past_games] if past_games else []
        
        return jsonify({
            "upcoming_games": upcoming_formatted,
            "past_games": past_formatted,
            "total_upcoming": len(upcoming_formatted),
            "total_past": len(past_formatted)
        })
        
    except Exception as e:
        print(f"Error getting pickup games: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to retrieve pickup games"}), 500


@api_bp.route("/api/pickup-games", methods=["POST"])
@login_required
def create_pickup_game():
    """Create a new pickup game"""
    try:
        user = session["user"]
        user_email = user.get("email")
        user_id = user.get("id")
        
        print(f"[CREATE_PICKUP_GAME] User session data: email={user_email}, user_id={user_id}")
        
        # If user_id is not in session, try to get it from database
        if not user_id and user_email:
            user_record = execute_query_one("SELECT id FROM users WHERE email = %s", [user_email])
            if user_record:
                user_id = user_record["id"]
                print(f"[CREATE_PICKUP_GAME] Retrieved user_id from database: {user_id}")
            else:
                print(f"[CREATE_PICKUP_GAME] No user record found for email: {user_email}")
                return jsonify({"error": "User account not found"}), 400
        
        if not user_id:
            print(f"[CREATE_PICKUP_GAME] User ID still not found after database lookup")
            return jsonify({"error": "User ID not found. Please log out and log back in."}), 400
            
        data = request.get_json()
        print(f"[CREATE_PICKUP_GAME] Received data: {data}")
        
        # Validate required fields
        required_fields = ["description", "game_date", "game_time", "players_requested"]
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"[CREATE_PICKUP_GAME] Missing required field: {field}")
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Parse and validate data
        try:
            game_date_obj = datetime.strptime(data["game_date"], "%Y-%m-%d").date()
            game_time_obj = datetime.strptime(data["game_time"], "%H:%M").time()
            players_requested = int(data["players_requested"])
            
            if players_requested <= 0:
                return jsonify({"error": "Players requested must be greater than 0"}), 400
                
        except ValueError as e:
            print(f"[CREATE_PICKUP_GAME] Data parsing error: {str(e)}")
            return jsonify({"error": f"Invalid data format: {str(e)}"}), 400
        
        # Optional fields with defaults
        pti_low = data.get("pti_low", -30)
        pti_high = data.get("pti_high", 100)
        series_low = data.get("series_low")
        series_high = data.get("series_high")
        club_only = data.get("club_only", False)
        is_private = data.get("is_private", False)
        
        # Convert series names to series IDs if provided
        series_low_id = None
        series_high_id = None
        
        if series_low:
            series_record = execute_query_one("SELECT id FROM series WHERE name = %s", [series_low])
            if series_record:
                series_low_id = series_record["id"]
                print(f"[CREATE_PICKUP_GAME] Converted series_low '{series_low}' to ID {series_low_id}")
            else:
                print(f"[CREATE_PICKUP_GAME] Warning: series_low '{series_low}' not found in database")
                # Don't fail the creation if series is not found, just set to None
                series_low_id = None
        
        if series_high:
            series_record = execute_query_one("SELECT id FROM series WHERE name = %s", [series_high])
            if series_record:
                series_high_id = series_record["id"]
                print(f"[CREATE_PICKUP_GAME] Converted series_high '{series_high}' to ID {series_high_id}")
            else:
                print(f"[CREATE_PICKUP_GAME] Warning: series_high '{series_high}' not found in database")
                # Don't fail the creation if series is not found, just set to None
                series_high_id = None
        
        # Validate PTI range
        if pti_low > pti_high:
            return jsonify({"error": "PTI low cannot be greater than PTI high"}), 400
            
        # Validate series range
        if series_low_id is not None and series_high_id is not None and series_low_id > series_high_id:
            return jsonify({"error": "Series low cannot be greater than series high"}), 400
        
        # Insert the new pickup game
        insert_query = """
            INSERT INTO pickup_games 
            (description, game_date, game_time, players_requested, pti_low, pti_high, 
             series_low, series_high, club_only, is_private, creator_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        insert_params = [
            data["description"], game_date_obj, game_time_obj, players_requested,
            pti_low, pti_high, series_low_id, series_high_id, club_only, is_private, user_id
        ]
        
        print(f"[CREATE_PICKUP_GAME] Executing insert with params: {insert_params}")
        
        result = execute_query_one(insert_query, insert_params)
        
        if result:
            pickup_game_id = result["id"]
            print(f"[CREATE_PICKUP_GAME] Successfully created pickup game with ID: {pickup_game_id}")
            
            log_user_activity(user_email, "pickup_game_created", 
                            details=f"Created pickup game: {data['description']}")
            
            return jsonify({
                "success": True,
                "pickup_game_id": pickup_game_id,
                "message": "Pickup game created successfully"
            }), 201
        else:
            print(f"[CREATE_PICKUP_GAME] Insert query returned no result")
            return jsonify({"error": "Failed to create pickup game - database insert failed"}), 500
            
    except Exception as e:
        print(f"[CREATE_PICKUP_GAME] Error creating pickup game: {str(e)}")
        import traceback
        print(f"[CREATE_PICKUP_GAME] Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to create pickup game due to server error"}), 500


@api_bp.route("/api/pickup-games/<int:game_id>/join", methods=["POST"])
@login_required
def join_pickup_game(game_id):
    """Join a pickup game"""
    try:
        user = session["user"]
        user_email = user.get("email")
        user_id = user.get("id")
        
        print(f"[JOIN_PICKUP_GAME] User {user_email} attempting to join game {game_id}")
        
        # If user_id is not in session, try to get it from database
        if not user_id and user_email:
            user_record = execute_query_one("SELECT id FROM users WHERE email = %s", [user_email])
            if user_record:
                user_id = user_record["id"]
                print(f"[JOIN_PICKUP_GAME] Retrieved user_id from database: {user_id}")
        
        if not user_id:
            print(f"[JOIN_PICKUP_GAME] User ID not found for {user_email}")
            return jsonify({"error": "User ID not found. Please log out and log back in."}), 400
        
        # Check if game exists and is not full
        game_query = """
            SELECT pg.*, COUNT(pgp.id) as current_participants
            FROM pickup_games pg
            LEFT JOIN pickup_game_participants pgp ON pg.id = pgp.pickup_game_id
            WHERE pg.id = %s
            GROUP BY pg.id
        """
        
        game = execute_query_one(game_query, [game_id])
        
        if not game:
            return jsonify({"error": "Pickup game not found"}), 404
            
        if game["current_participants"] >= game["players_requested"]:
            return jsonify({"error": "Pickup game is full"}), 400
        
        # Check if user is already in this game
        existing_query = """
            SELECT id FROM pickup_game_participants 
            WHERE pickup_game_id = %s AND user_id = %s
        """
        
        existing = execute_query_one(existing_query, [game_id, user_id])
        
        if existing:
            return jsonify({"error": "You have already joined this game"}), 400
        
        # Add user to the game
        join_query = """
            INSERT INTO pickup_game_participants (pickup_game_id, user_id)
            VALUES (%s, %s)
            RETURNING id
        """
        
        result = execute_query_one(join_query, [game_id, user_id])
        
        if result:
            # Update the players_committed count
            update_query = """
                UPDATE pickup_games 
                SET players_committed = (
                    SELECT COUNT(*) FROM pickup_game_participants 
                    WHERE pickup_game_id = %s
                )
                WHERE id = %s
            """
            execute_update(update_query, [game_id, game_id])
            
            print(f"[JOIN_PICKUP_GAME] User {user_email} successfully joined game {game_id}")
            
            log_user_activity(user_email, "pickup_game_joined", 
                            details=f"Joined pickup game ID: {game_id}")
            
            return jsonify({
                "success": True,
                "message": "Successfully joined pickup game"
            })
        else:
            print(f"[JOIN_PICKUP_GAME] Failed to insert participant record for user {user_email} and game {game_id}")
            return jsonify({"error": "Failed to join pickup game - database insert failed"}), 500
            
    except Exception as e:
        print(f"Error joining pickup game: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to join pickup game"}), 500


@api_bp.route("/api/pickup-games/<int:game_id>/add-player", methods=["POST"])
@login_required
def add_player_to_pickup_game(game_id):
    """Add another player to a pickup game"""
    try:
        user = session["user"]
        user_email = user.get("email")
        user_id = user.get("id")
        
        print(f"[ADD_PLAYER_TO_PICKUP_GAME] User {user_email} attempting to add player to game {game_id}")
        
        # If user_id is not in session, try to get it from database
        if not user_id and user_email:
            user_record = execute_query_one("SELECT id FROM users WHERE email = %s", [user_email])
            if user_record:
                user_id = user_record["id"]
                print(f"[ADD_PLAYER_TO_PICKUP_GAME] Retrieved user_id from database: {user_id}")
        
        if not user_id:
            print(f"[ADD_PLAYER_TO_PICKUP_GAME] User ID not found for {user_email}")
            return jsonify({"error": "User ID not found. Please log out and log back in."}), 400
        
        # Get the player data from request
        data = request.get_json()
        player_name = data.get("player_name")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        
        if not player_name or not first_name or not last_name:
            return jsonify({"error": "Player name information is required"}), 400
        
        print(f"[ADD_PLAYER_TO_PICKUP_GAME] Adding player: {player_name} ({first_name} {last_name})")
        
        # Check if game exists and is not full
        game_query = """
            SELECT pg.*, COUNT(pgp.id) as current_participants
            FROM pickup_games pg
            LEFT JOIN pickup_game_participants pgp ON pg.id = pgp.pickup_game_id
            WHERE pg.id = %s
            GROUP BY pg.id
        """
        
        game = execute_query_one(game_query, [game_id])
        
        if not game:
            return jsonify({"error": "Pickup game not found"}), 404
            
        if game["current_participants"] >= game["players_requested"]:
            return jsonify({"error": "Pickup game is full"}), 400
        
        # Find the player in the system by searching for their name
        # First try to find an exact match with a user account
        player_search_query = """
            SELECT DISTINCT p.*, u.id as user_id, u.email
            FROM players p
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            LEFT JOIN users u ON upa.user_id = u.id
            WHERE LOWER(p.first_name) = LOWER(%s) 
            AND LOWER(p.last_name) = LOWER(%s)
            AND p.is_active = true
            ORDER BY u.id DESC NULLS LAST
            LIMIT 1
        """
        
        player_record = execute_query_one(player_search_query, [first_name, last_name])
        
        if not player_record:
            return jsonify({"error": f"Player {player_name} not found in the system"}), 404
        
        target_user_id = player_record["user_id"]
        
        # If player doesn't have a user account, create a placeholder for them
        if not target_user_id:
            # Create or find placeholder user
            placeholder_email = f"{player_record['tenniscores_player_id']}@placeholder.rally"
            
            # Check if placeholder already exists
            existing_placeholder = execute_query_one(
                "SELECT id FROM users WHERE email = %s", [placeholder_email]
            )
            
            if existing_placeholder:
                target_user_id = existing_placeholder["id"]
                print(f"[ADD_PLAYER_TO_PICKUP_GAME] Using existing placeholder user {target_user_id}")
            else:
                # Create new placeholder user
                create_user_query = """
                    INSERT INTO users (first_name, last_name, email, password_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """
                
                new_user_result = execute_query_one(create_user_query, [
                    player_record["first_name"],
                    player_record["last_name"],
                    placeholder_email,
                    "placeholder"
                ])
                
                if new_user_result:
                    target_user_id = new_user_result["id"]
                    print(f"[ADD_PLAYER_TO_PICKUP_GAME] Created placeholder user {target_user_id}")
                    
                    # Create the player association
                    create_association_query = """
                        INSERT INTO user_player_associations (user_id, tenniscores_player_id)
                        VALUES (%s, %s)
                    """
                    
                    execute_update(create_association_query, [target_user_id, player_record["tenniscores_player_id"]])
                    print(f"[ADD_PLAYER_TO_PICKUP_GAME] Created player association for placeholder user")
                else:
                    return jsonify({"error": "Failed to create user record for player"}), 500
        
        # Check if player is already in this game
        existing_query = """
            SELECT id FROM pickup_game_participants 
            WHERE pickup_game_id = %s AND user_id = %s
        """
        
        existing = execute_query_one(existing_query, [game_id, target_user_id])
        
        if existing:
            return jsonify({"error": f"{player_name} is already in this pickup game"}), 400
        
        # Add player to the game
        add_query = """
            INSERT INTO pickup_game_participants (pickup_game_id, user_id)
            VALUES (%s, %s)
            RETURNING id
        """
        
        result = execute_query_one(add_query, [game_id, target_user_id])
        
        if result:
            # Update the players_committed count
            update_query = """
                UPDATE pickup_games 
                SET players_committed = (
                    SELECT COUNT(*) FROM pickup_game_participants 
                    WHERE pickup_game_id = %s
                )
                WHERE id = %s
            """
            execute_update(update_query, [game_id, game_id])
            
            print(f"[ADD_PLAYER_TO_PICKUP_GAME] Successfully added {player_name} to game {game_id}")
            
            log_user_activity(user_email, "pickup_game_player_added", 
                            details=f"Added {player_name} to pickup game ID: {game_id}")
            
            return jsonify({
                "success": True,
                "message": f"Successfully added {player_name} to pickup game"
            })
        else:
            print(f"[ADD_PLAYER_TO_PICKUP_GAME] Failed to insert participant record for {player_name} and game {game_id}")
            return jsonify({"error": "Failed to add player to pickup game - database insert failed"}), 500
            
    except Exception as e:
        print(f"Error adding player to pickup game: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to add player to pickup game"}), 500


@api_bp.route("/api/pickup-games/<int:game_id>", methods=["PUT"])
@login_required
def update_pickup_game(game_id):
    """Update an existing pickup game (only by creator)"""
    try:
        user = session["user"]
        user_email = user.get("email")
        user_id = user.get("id")
        
        print(f"[UPDATE_PICKUP_GAME] User {user_email} attempting to update game {game_id}")
        
        # If user_id is not in session, try to get it from database
        if not user_id and user_email:
            user_record = execute_query_one("SELECT id FROM users WHERE email = %s", [user_email])
            if user_record:
                user_id = user_record["id"]
                print(f"[UPDATE_PICKUP_GAME] Retrieved user_id from database: {user_id}")
        
        if not user_id:
            print(f"[UPDATE_PICKUP_GAME] User ID not found for {user_email}")
            return jsonify({"error": "User ID not found. Please log out and log back in."}), 400
        
        # Check if game exists and user is the creator
        game_check_query = """
            SELECT creator_user_id 
            FROM pickup_games 
            WHERE id = %s
        """
        
        existing_game = execute_query_one(game_check_query, [game_id])
        
        if not existing_game:
            return jsonify({"error": "Pickup game not found"}), 404
            
        if existing_game["creator_user_id"] != user_id:
            return jsonify({"error": "Only the creator can edit this pickup game"}), 403
        
        # Get the update data
        data = request.get_json()
        print(f"[UPDATE_PICKUP_GAME] Received data: {data}")
        
        # Validate required fields
        required_fields = ["description", "game_date", "game_time", "players_requested"]
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"[UPDATE_PICKUP_GAME] Missing required field: {field}")
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Parse and validate data
        try:
            game_date_obj = datetime.strptime(data["game_date"], "%Y-%m-%d").date()
            game_time_obj = datetime.strptime(data["game_time"], "%H:%M").time()
            players_requested = int(data["players_requested"])
            
            if players_requested <= 0:
                return jsonify({"error": "Players requested must be greater than 0"}), 400
                
        except ValueError as e:
            print(f"[UPDATE_PICKUP_GAME] Data parsing error: {str(e)}")
            return jsonify({"error": f"Invalid data format: {str(e)}"}), 400
        
        # Optional fields with defaults
        pti_low = data.get("pti_low", -30)
        pti_high = data.get("pti_high", 100)
        series_low = data.get("series_low")
        series_high = data.get("series_high")
        club_only = data.get("club_only", False)
        is_private = data.get("is_private", False)
        
        # Convert series names to series IDs if provided
        series_low_id = None
        series_high_id = None
        
        if series_low:
            series_record = execute_query_one("SELECT id FROM series WHERE name = %s", [series_low])
            if series_record:
                series_low_id = series_record["id"]
                print(f"[UPDATE_PICKUP_GAME] Converted series_low '{series_low}' to ID {series_low_id}")
        
        if series_high:
            series_record = execute_query_one("SELECT id FROM series WHERE name = %s", [series_high])
            if series_record:
                series_high_id = series_record["id"]
                print(f"[UPDATE_PICKUP_GAME] Converted series_high '{series_high}' to ID {series_high_id}")
        
        # Validate PTI range
        if pti_low > pti_high:
            return jsonify({"error": "PTI low cannot be greater than PTI high"}), 400
            
        # Validate series range
        if series_low_id is not None and series_high_id is not None and series_low_id > series_high_id:
            return jsonify({"error": "Series low cannot be greater than series high"}), 400
        
        # Update the pickup game
        update_query = """
            UPDATE pickup_games 
            SET description = %s, game_date = %s, game_time = %s, players_requested = %s,
                pti_low = %s, pti_high = %s, series_low = %s, series_high = %s, club_only = %s, is_private = %s
            WHERE id = %s
        """
        
        update_params = [
            data["description"], game_date_obj, game_time_obj, players_requested,
            pti_low, pti_high, series_low_id, series_high_id, club_only, is_private, game_id
        ]
        
        print(f"[UPDATE_PICKUP_GAME] Executing update with params: {update_params}")
        
        rows_updated = execute_update(update_query, update_params)
        
        if rows_updated > 0:
            print(f"[UPDATE_PICKUP_GAME] Successfully updated pickup game {game_id}")
            
            log_user_activity(user_email, "pickup_game_updated", 
                            details=f"Updated pickup game ID: {game_id}")
            
            return jsonify({
                "success": True,
                "message": "Pickup game updated successfully"
            })
        else:
            print(f"[UPDATE_PICKUP_GAME] Update query affected 0 rows for game {game_id}")
            return jsonify({"error": "Failed to update pickup game"}), 500
            
    except Exception as e:
        print(f"[UPDATE_PICKUP_GAME] Error updating pickup game: {str(e)}")
        import traceback
        print(f"[UPDATE_PICKUP_GAME] Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to update pickup game due to server error"}), 500


@api_bp.route("/api/pickup-games/<int:game_id>", methods=["GET"])
@login_required
def get_pickup_game(game_id):
    """Get a single pickup game for editing (only by creator)"""
    try:
        user = session["user"]
        user_email = user.get("email")
        user_id = user.get("id")
        
        # If user_id is not in session, try to get it from database
        if not user_id and user_email:
            user_record = execute_query_one("SELECT id FROM users WHERE email = %s", [user_email])
            if user_record:
                user_id = user_record["id"]
        
        if not user_id:
            return jsonify({"error": "User ID not found. Please log out and log back in."}), 400
        
        # Get the pickup game
        game_query = """
            SELECT 
                pg.id,
                pg.description,
                pg.game_date,
                pg.game_time,
                pg.players_requested,
                pg.pti_low,
                pg.pti_high,
                pg.series_low,
                pg.series_high,
                pg.club_only,
                pg.is_private,
                pg.creator_user_id,
                s_low.name as series_low_name,
                s_high.name as series_high_name
            FROM pickup_games pg
            LEFT JOIN series s_low ON pg.series_low = s_low.id
            LEFT JOIN series s_high ON pg.series_high = s_high.id
            WHERE pg.id = %s
        """
        
        game = execute_query_one(game_query, [game_id])
        
        if not game:
            return jsonify({"error": "Pickup game not found"}), 404
            
        # Check if user is the creator
        if game["creator_user_id"] != user_id:
            return jsonify({"error": "Only the creator can view edit details for this pickup game"}), 403
        
        # Format the response (return game data directly as expected by frontend)
        game_data = {
            "id": game["id"],
            "description": game["description"],
            "game_date": game["game_date"].strftime('%Y-%m-%d'),
            "game_time": game["game_time"].strftime('%H:%M'),
            "players_requested": game["players_requested"],
            "pti_low": float(game["pti_low"]),
            "pti_high": float(game["pti_high"]),
            "series_low": game["series_low_name"],
            "series_high": game["series_high_name"],
            "club_only": game["club_only"],
            "is_private": game["is_private"],
            "creator_user_id": game["creator_user_id"]
        }
        
        print(f"[GET_PICKUP_GAME] Returning game data: {game_data}")
        return jsonify(game_data)
        
    except Exception as e:
        print(f"Error getting pickup game: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to retrieve pickup game"}), 500





@api_bp.route("/api/pickup-games/<int:game_id>/leave", methods=["DELETE"])
@login_required
def leave_pickup_game(game_id):
    """Leave a pickup game"""
    try:
        user = session["user"]
        user_email = user.get("email")
        user_id = user.get("id")
        
        print(f"[LEAVE_PICKUP_GAME] User {user_email} attempting to leave game {game_id}")
        
        # If user_id is not in session, try to get it from database
        if not user_id and user_email:
            user_record = execute_query_one("SELECT id FROM users WHERE email = %s", [user_email])
            if user_record:
                user_id = user_record["id"]
                print(f"[LEAVE_PICKUP_GAME] Retrieved user_id from database: {user_id}")
        
        if not user_id:
            print(f"[LEAVE_PICKUP_GAME] User ID not found for {user_email}")
            return jsonify({"error": "User ID not found. Please log out and log back in."}), 400
        
        # Check if user is in this game
        existing_query = """
            SELECT id FROM pickup_game_participants 
            WHERE pickup_game_id = %s AND user_id = %s
        """
        
        existing = execute_query_one(existing_query, [game_id, user_id])
        
        if not existing:
            return jsonify({"error": "You are not in this game"}), 400
        
        # Remove user from the game
        leave_query = """
            DELETE FROM pickup_game_participants 
            WHERE pickup_game_id = %s AND user_id = %s
        """
        
        # Remove user from the game
        with get_db_cursor() as cursor:
            cursor.execute(leave_query, [game_id, user_id])
            rows_affected = cursor.rowcount
            print(f"[LEAVE_PICKUP_GAME] Rows affected: {rows_affected}")
        
        if rows_affected > 0:
            # Update the players_committed count
            update_query = """
                UPDATE pickup_games 
                SET players_committed = (
                    SELECT COUNT(*) FROM pickup_game_participants 
                    WHERE pickup_game_id = %s
                )
                WHERE id = %s
            """
            execute_update(update_query, [game_id, game_id])
            
            print(f"[LEAVE_PICKUP_GAME] User {user_email} successfully left game {game_id}")
            
            log_user_activity(user_email, "pickup_game_left", 
                            details=f"Left pickup game ID: {game_id}")
            
            return jsonify({
                "success": True,
                "message": "Successfully left pickup game"
            })
        else:
            print(f"[LEAVE_PICKUP_GAME] No rows affected when trying to remove user {user_email} from game {game_id}")
            return jsonify({"error": "Failed to leave pickup game - no participant record found"}), 500
            
    except Exception as e:
        print(f"Error leaving pickup game: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to leave pickup game"}), 500


@api_bp.route("/api/pickup-games/<int:game_id>", methods=["DELETE"])
@login_required
def delete_pickup_game(game_id):
    """Delete a pickup game (only by creator)"""
    try:
        user = session["user"]
        user_email = user.get("email")
        user_id = user.get("id")
        
        print(f"[DELETE_PICKUP_GAME] User {user_email} attempting to delete game {game_id}")
        
        # If user_id is not in session, try to get it from database
        if not user_id and user_email:
            user_record = execute_query_one("SELECT id FROM users WHERE email = %s", [user_email])
            if user_record:
                user_id = user_record["id"]
                print(f"[DELETE_PICKUP_GAME] Retrieved user_id from database: {user_id}")
        
        if not user_id:
            print(f"[DELETE_PICKUP_GAME] User ID not found for {user_email}")
            return jsonify({"error": "User ID not found. Please log out and log back in."}), 400
        
        # Check if game exists and user is the creator
        game_query = """
            SELECT 
                creator_user_id,
                description,
                game_date,
                game_time,
                (SELECT COUNT(*) FROM pickup_game_participants WHERE pickup_game_id = %s) as participant_count
            FROM pickup_games 
            WHERE id = %s
        """
        
        game = execute_query_one(game_query, [game_id, game_id])
        
        if not game:
            return jsonify({"error": "Pickup game not found"}), 404
            
        if game["creator_user_id"] != user_id:
            return jsonify({"error": "Only the creator can delete this pickup game"}), 403
        
        # Check if there are participants (optional warning, but still allow deletion)
        participant_count = game["participant_count"]
        
        # Delete all participants first (cascade delete)
        delete_participants_query = """
            DELETE FROM pickup_game_participants 
            WHERE pickup_game_id = %s
        """
        
        participants_deleted = execute_update(delete_participants_query, [game_id])
        print(f"[DELETE_PICKUP_GAME] Deleted {participants_deleted} participants from game {game_id}")
        
        # Delete the pickup game
        delete_game_query = """
            DELETE FROM pickup_games 
            WHERE id = %s AND creator_user_id = %s
        """
        
        rows_deleted = execute_update(delete_game_query, [game_id, user_id])
        
        if rows_deleted > 0:
            print(f"[DELETE_PICKUP_GAME] Successfully deleted pickup game {game_id}")
            
            log_user_activity(user_email, "pickup_game_deleted", 
                            details=f"Deleted pickup game ID: {game_id}, Description: {game['description']}")
            
            # Create response message
            message = f"Successfully deleted pickup game '{game['description']}'"
            if participant_count > 0:
                message += f" and removed {participant_count} participant(s)"
            
            return jsonify({
                "success": True,
                "message": message,
                "participants_removed": participant_count
            })
        else:
            print(f"[DELETE_PICKUP_GAME] No rows affected when trying to delete game {game_id}")
            return jsonify({"error": "Failed to delete pickup game - game not found or access denied"}), 500
            
    except Exception as e:
        print(f"[DELETE_PICKUP_GAME] Error deleting pickup game: {str(e)}")
        import traceback
        print(f"[DELETE_PICKUP_GAME] Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to delete pickup game due to server error"}), 500


@api_bp.route("/api/series-options", methods=["GET"])
@login_required  
def get_series_options():
    """Get series options for dropdown in pickup game creation"""
    try:
        user = session["user"]
        user_league_id = user.get("league_id")
        
        if not user_league_id:
            return jsonify({"error": "User league not found"}), 400
        
        # Convert league_id to integer if needed
        if isinstance(user_league_id, str) and user_league_id.isdigit():
            league_id_int = int(user_league_id)
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
        else:
            # Try to look up league by string ID
            league_record = execute_query_one(
                "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
            )
            if league_record:
                league_id_int = league_record["id"]
            else:
                return jsonify({"error": "League not found"}), 404
        
        # Get series for this league - we'll sort manually for proper numerical ordering
        series_query = """
            SELECT DISTINCT s.name, s.display_name
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            WHERE sl.league_id = %s
        """
        
        series_data = execute_query(series_query, [league_id_int])
        
        # Helper function to extract numerical sort key from series name
        def get_series_sort_key(series_name):
            """Extract numerical sort key from series name for proper ordering"""
            import re
            
            # Handle various series name formats
            if not series_name:
                return (0, "")
            
            # Extract number from series name (e.g., "Chicago 12" -> 12, "Series 5" -> 5)
            number_match = re.search(r'(\d+)', series_name)
            if number_match:
                number = int(number_match.group(1))
            else:
                number = 0
            
            # Return tuple for sorting: (number, full_name)
            # This ensures proper numerical ordering while maintaining alphabetical 
            # ordering for series with the same number
            return (number, series_name.lower())
        
        # Format and sort series options for dropdown
        series_options = []
        for series in series_data:
            # Use display_name if available, otherwise fall back to name
            display_name = series.get("display_name") or series["name"]
            series_options.append({
                "value": series["name"],
                "display_name": display_name
            })
        
        # Sort by numerical value using the sort key function
        series_options.sort(key=lambda x: get_series_sort_key(x["display_name"]))
        
        return jsonify({
            "series_options": series_options,
            "league_id": league_id_int
        })
        
    except Exception as e:
        print(f"Error getting series options: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to retrieve series options"}), 500


# =====================================================
# GROUPS API ROUTES
# =====================================================

@api_bp.route("/api/groups", methods=["GET"])
@login_required
def get_user_groups():
    """Get all groups for the current user"""
    try:
        user = session["user"]
        user_id = user.get("id")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        # Get database session
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            groups = groups_service.get_user_groups(user_id)
            
            return jsonify({
                "success": True,
                "groups": groups
            })
    
    except Exception as e:
        print(f"Error getting user groups: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to retrieve groups"}), 500


@api_bp.route("/api/groups", methods=["POST"])
@login_required
def create_group():
    """Create a new group"""
    try:
        user = session["user"]
        user_id = user.get("id")
        user_email = user.get("email")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get("name"):
            return jsonify({"error": "Group name is required"}), 400
        
        group_name = data["name"].strip()
        description = data.get("description", "").strip()
        
        if len(group_name) < 2:
            return jsonify({"error": "Group name must be at least 2 characters"}), 400
        
        # Get database session
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            result = groups_service.create_group(user_id, group_name, description)
            
            if result["success"]:
                log_user_activity(user_email, "group_created", 
                                details=f"Created group: {group_name}")
            
            return jsonify(result), 201 if result["success"] else 400
    
    except Exception as e:
        print(f"Error creating group: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to create group"}), 500


@api_bp.route("/api/groups/<int:group_id>", methods=["GET"])
@login_required
def get_group_details(group_id):
    """Get detailed information about a group"""
    try:
        user = session["user"]
        user_id = user.get("id")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        # Get database session
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            result = groups_service.get_group_details(group_id, user_id)
            
            return jsonify(result), 200 if result["success"] else 404
    
    except Exception as e:
        print(f"Error getting group details: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to retrieve group details"}), 500


@api_bp.route("/api/groups/<int:group_id>", methods=["DELETE"])
@login_required
def delete_group(group_id):
    """Delete a group (creator only)"""
    try:
        user = session["user"]
        user_id = user.get("id")
        user_email = user.get("email")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        # Get database session
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            result = groups_service.delete_group(group_id, user_id)
            
            if result["success"]:
                log_user_activity(user_email, "group_deleted", 
                                details=f"Deleted group ID: {group_id}")
            
            return jsonify(result), 200 if result["success"] else 400
    
    except Exception as e:
        print(f"Error deleting group: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to delete group"}), 500


@api_bp.route("/api/groups/search-players", methods=["GET"])
@login_required
def search_players_for_groups():
    """Search for players to add to groups"""
    try:
        user = session["user"]
        user_id = user.get("id")
        user_club_id = user.get("club_id")  # Get user's current club ID
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        query = request.args.get("q", "").strip()
        league_id = request.args.get("league_id")
        
        if len(query) < 2:
            return jsonify({"success": True, "players": []})
        
        # Convert league_id to integer foreign key if provided
        league_id_int = None
        if league_id:
            try:
                # First try direct integer conversion
                league_id_int = int(league_id)
            except ValueError:
                # If that fails, try to look up by string league_id
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                    else:
                        print(f"League not found for league_id: {league_id}")
                        return jsonify({"error": f"League not found: {league_id}"}), 400
                except Exception as e:
                    print(f"Error looking up league: {e}")
                    return jsonify({"error": "Invalid league ID"}), 400
        
        print(f"Searching players: query='{query}', user_id={user_id}, league_id_int={league_id_int}, user_club_id={user_club_id}")
        
        # Use GroupsService to search players
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            matching_players = groups_service.search_players(
                query=query,
                user_id=user_id,
                league_id=league_id_int,
                club_id=user_club_id  # Filter by user's current club
            )
        
        # Enhanced logging for groups player search
        search_details = {
            "search_query": query,
            "search_context": "groups_player_search",
            "league_filter": league_id,
            "club_filter": user_club_id,
            "results_count": len(matching_players),
            "user_league": user.get("league_id", "Unknown"),
            "user_club": user.get("club", "Unknown")
        }
        # Add filters_applied summary
        filters = []
        if query:
            filters.append(f"name: {query}")
        if league_id:
            filters.append(f"league: {league_id}")
        if user_club_id:
            filters.append(f"club: {user_club_id}")
        filters_applied = ", ".join(filters) if filters else "no filters"
        search_details["filters_applied"] = filters_applied
        
        log_user_activity(
            user["email"],
            "player_search",
            action="groups_search",
            details=search_details
        )
        
        print(f"Found {len(matching_players)} matching players")
        
        return jsonify({
            "success": True,
            "players": matching_players
        })
        
    except Exception as e:
        print(f"Error in search_players_for_groups: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Search failed"}), 500


@api_bp.route("/api/groups/<int:group_id>/members", methods=["POST"])
@login_required
def add_group_member(group_id):
    """Add a member to a group"""
    try:
        user = session["user"]
        user_id = user.get("id")
        user_email = user.get("email")
        user_club_id = user.get("club_id")  # Get user's current club ID
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        data = request.get_json()
        member_user_id = data.get("user_id")
        
        # Handle players without accounts
        if not member_user_id:
            # Check if we have player info for someone without an account
            tenniscores_player_id = data.get("tenniscores_player_id")
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            no_account = data.get("no_account", False)
            
            if no_account and tenniscores_player_id and first_name and last_name:
                # Handle player without account
                with SessionLocal() as db_session:
                    groups_service = GroupsService(db_session)
                    result = groups_service.add_player_without_account_to_group(
                        group_id, user_id, tenniscores_player_id, first_name, last_name, user_club_id
                    )
                    
                    if result["success"]:
                        log_user_activity(user_email, "group_member_added", 
                                        details=f"Added player without account to group ID: {group_id}")
                    
                    return jsonify(result), 200 if result["success"] else 400
            else:
                return jsonify({"error": "User ID or valid player information is required"}), 400
        
        try:
            member_user_id = int(member_user_id)
        except ValueError:
            return jsonify({"error": "Invalid user ID"}), 400
        
        # Get database session
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            result = groups_service.add_member_to_group(group_id, user_id, member_user_id)
            
            if result["success"]:
                log_user_activity(user_email, "group_member_added", 
                                details=f"Added member to group ID: {group_id}")
            
            return jsonify(result), 200 if result["success"] else 400
    
    except Exception as e:
        print(f"Error adding group member: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to add group member"}), 500


@api_bp.route("/api/groups/<int:group_id>/members/<int:member_user_id>", methods=["DELETE"])
@login_required
def remove_group_member(group_id, member_user_id):
    """Remove a member from a group"""
    try:
        user = session["user"]
        user_id = user.get("id")
        user_email = user.get("email")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        # Get database session
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            result = groups_service.remove_member_from_group(group_id, user_id, member_user_id)
            
            if result["success"]:
                log_user_activity(user_email, "group_member_removed", 
                                details=f"Removed member from group ID: {group_id}")
            
            return jsonify(result), 200 if result["success"] else 400
    
    except Exception as e:
        print(f"Error removing group member: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to remove group member"}), 500


@api_bp.route("/api/groups/<int:group_id>", methods=["PUT"])
@login_required
def update_group(group_id):
    """Update group details (creator only)"""
    try:
        user = session["user"]
        user_id = user.get("id")
        user_email = user.get("email")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get("name"):
            return jsonify({"error": "Group name is required"}), 400
        
        group_name = data["name"].strip()
        description = data.get("description", "").strip()
        
        if len(group_name) < 2:
            return jsonify({"error": "Group name must be at least 2 characters"}), 400
        
        # Get database session
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            result = groups_service.update_group(group_id, user_id, group_name, description)
            
            if result["success"]:
                log_user_activity(user_email, "group_updated", 
                                details=f"Updated group ID: {group_id}")
            
            return jsonify(result), 200 if result["success"] else 400
    
    except Exception as e:
        print(f"Error updating group: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to update group"}), 500


@api_bp.route("/api/groups/send-message", methods=["POST"])
@login_required
def send_group_message():
    """Send SMS messages to all members of a group"""
    try:
        user = session["user"]
        user_id = user.get("id")
        user_email = user.get("email")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get("group_id"):
            return jsonify({"error": "Group ID is required"}), 400
        
        if not data.get("message"):
            return jsonify({"error": "Message content is required"}), 400
        
        group_id = data["group_id"]
        subject = data.get("subject", "Group Message").strip()  # Make subject optional
        message = data["message"].strip()
        
        # Validate message length for SMS
        if len(message) > 800:  # Leave room for sender info and formatting
            return jsonify({"error": "Message too long. Please keep under 800 characters for SMS."}), 400
        
        try:
            group_id = int(group_id)
        except ValueError:
            return jsonify({"error": "Invalid group ID"}), 400
        
        # Get database session
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            result = groups_service.send_group_message(group_id, user_id, subject, message)
            
            # Enhanced logging
            if result["success"]:
                details = result.get("details", {})
                log_user_activity(user_email, "group_message_sent", 
                                details=f"Group: {details.get('group_name')}, "
                                      f"Sent to {details.get('successful_sends', 0)} members")
            else:
                log_user_activity(user_email, "group_message_failed", 
                                details=f"Group ID: {group_id}, Error: {result.get('error')}")
            
            # Return appropriate status code
            if result["success"]:
                return jsonify(result), 200
            else:
                # Check if it's a user error (no phone numbers) vs system error
                error_msg = result.get("error", "")
                if "phone numbers" in error_msg.lower():
                    return jsonify(result), 422  # Unprocessable Entity - user action needed
                else:
                    return jsonify(result), 400  # Bad Request - general error
    
    except Exception as e:
        print(f"Error sending group message: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": "System error occurred while sending messages. Please try again."
        }), 500


@api_bp.route("/api/home/notifications")
@login_required
def get_home_notifications():
    """Get personalized notifications for the home page in the specified order"""
    try:
        # TEMPORARY: Fix schema issues if they exist
        try:
            from scripts.fix_staging_schema_internal import fix_staging_schema_internal
            fix_staging_schema_internal()
        except Exception as e:
            logger.warning(f"Schema fix attempt failed (this is normal): {str(e)}")
        
        user = session["user"]
        user_id = user.get("id")
        player_id = user.get("tenniscores_player_id")
        league_id = user.get("league_id")
        team_id = user.get("team_id")
        
        logger.info(f"Getting notifications for user {user_id}, player_id: {player_id}, league_id: {league_id}, team_id: {team_id}")
        
        if not user_id:
            logger.error(f"No user_id found for user: {user}")
            return jsonify({"error": "User ID not found"}), 404
            
        notifications = []
        
        # 1. Captains Message (priority 1)
        try:
            captain_notifications = get_captain_messages(user_id, player_id, league_id, team_id)
            notifications.extend(captain_notifications)
        except Exception as e:
            logger.error(f"Error getting captain messages: {str(e)}")
        
        # 2. Upcoming Schedule (priority 2)
        try:
            schedule_notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
            notifications.extend(schedule_notifications)
        except Exception as e:
            logger.error(f"Error getting schedule notifications: {str(e)}")
        
        # 3. Team Position (priority 3)
        try:
            team_position_notifications = get_team_position_notifications(user_id, player_id, league_id, team_id)
            notifications.extend(team_position_notifications)
        except Exception as e:
            logger.error(f"Error getting team position notifications: {str(e)}")
        
        # 4. Team Poll (priority 4)
        try:
            poll_notifications = get_team_poll_notifications(user_id, player_id, league_id, team_id)
            notifications.extend(poll_notifications)
        except Exception as e:
            logger.error(f"Error getting poll notifications: {str(e)}")
        
        # 5. Pickup Games Available (priority 5)
        try:
            pickup_notifications = get_pickup_games_notifications(user_id, player_id, league_id, team_id)
            notifications.extend(pickup_notifications)
        except Exception as e:
            logger.error(f"Error getting pickup games notifications: {str(e)}")
        
        # 6. My Win Streaks (priority 6)
        try:
            win_streaks_notifications = get_my_win_streaks_notifications(user_id, player_id, league_id, team_id)
            notifications.extend(win_streaks_notifications)
        except Exception as e:
            logger.error(f"Error getting win streaks notifications: {str(e)}")
        
        # Sort by priority and show all notifications (no limit)
        notifications.sort(key=lambda x: x["priority"])
        
        # Ensure there are always notifications by adding fallbacks if needed
        try:
            if len(notifications) == 0:
                notifications = get_fallback_notifications(user_id, player_id, league_id, team_id)
            elif len(notifications) < 2:
                # Add some fallback notifications to ensure we have at least 2
                fallbacks = get_fallback_notifications(user_id, player_id, league_id, team_id)
                # Add fallbacks that don't duplicate existing ones
                existing_ids = {n["id"] for n in notifications}
                for fallback in fallbacks:
                    if fallback["id"] not in existing_ids and len(notifications) < 3:
                        notifications.append(fallback)
        except Exception as e:
            logger.error(f"Error getting fallback notifications: {str(e)}")
            # Ultimate fallback
            notifications = [
                {
                    "id": "rally_welcome",
                    "type": "personal",
                    "title": "Welcome to Rally!",
                    "message": "Explore your stats, team performance, and stay connected with your teammates.",
                    "cta": {"label": "Get Started", "href": "/mobile/analyze-me"},
                    "detail_link": {"label": "View Stats", "href": "/mobile/analyze-me"},
                    "priority": 1
                }
            ]
        
        # Final safety check - ensure we always have notifications
        if not notifications:
            logger.warning("No notifications generated, using ultimate fallback")
            notifications = [
                {
                    "id": "rally_welcome",
                    "type": "personal",
                    "title": "Welcome to Rally!",
                    "message": "Explore your stats, team performance, and stay connected with your teammates.",
                    "cta": {"label": "Get Started", "href": "/mobile/analyze-me"},
                    "detail_link": {"label": "View Stats", "href": "/mobile/analyze-me"},
                    "priority": 1
                }
            ]
        
        logger.info(f"Returning {len(notifications)} notifications for user {user_id}")
        return jsonify({"notifications": notifications})
        
    except Exception as e:
        logger.error(f"Error getting home notifications: {str(e)}")
        # Return fallback notifications instead of error
        fallback_notifications = [
            {
                "id": "rally_welcome",
                "type": "personal",
                "title": "Welcome to Rally!",
                "message": "Explore your stats, team performance, and stay connected with your teammates.",
                "cta": {"label": "Get Started", "href": "/mobile/analyze-me"},
                "detail_link": {"label": "View Stats", "href": "/mobile/analyze-me"},
                "priority": 1
            }
        ]
        return jsonify({"notifications": fallback_notifications})


def get_urgent_match_notifications(user_id, player_id, league_id, team_id):
    """Get urgent match-related notifications"""
    notifications = []
    
    try:
        # Check for tonight's match
        tonight_query = """
            SELECT 
                match_date,
                home_team,
                away_team,
                home_player_1_id,
                home_player_2_id,
                away_player_1_id,
                away_player_2_id
            FROM match_scores 
            WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
            AND league_id = %s
            AND match_date = CURRENT_DATE
            ORDER BY match_date DESC
            LIMIT 1
        """
        
        if league_id and player_id:
            tonight_match = execute_query_one(tonight_query, [player_id, player_id, player_id, player_id, league_id])
            
            if tonight_match:
                notifications.append({
                    "id": f"tonight_match_{tonight_match['match_date']}",
                    "type": "match",
                    "title": "Tonight's Match",
                    "message": f"You have a match tonight: {tonight_match['home_team']} vs {tonight_match['away_team']}",
                    "cta": {"label": "View Details", "href": "/mobile/matches"},
                    "detail_link": {"label": "View Match", "href": "/mobile/matches"},
                    "priority": 1
                })
        
        # Check for availability status
        availability_query = """
            SELECT 
                match_date,
                availability_status,
                notes
            FROM player_availability 
            WHERE user_id = %s 
            AND match_date >= CURRENT_DATE
            ORDER BY match_date ASC
            LIMIT 3
        """
        
        availability_records = execute_query(availability_query, [user_id])
        
        for record in availability_records:
            if record["availability_status"] == 3:  # Not sure
                notifications.append({
                    "id": f"availability_{record['match_date']}",
                    "type": "match",
                    "title": "Update Availability",
                    "message": f"Please confirm your availability for {record['match_date'].strftime('%b %d')}",
                    "cta": {"label": "Update Now", "href": "/mobile/availability-calendar"},
                    "detail_link": {"label": "View Calendar", "href": "/mobile/availability-calendar"},
                    "priority": 2
                })
                break
        
        # Check for latest team poll
        poll_query = """
            SELECT 
                p.id,
                p.question,
                p.created_at,
                u.first_name,
                u.last_name
            FROM polls p
            JOIN users u ON p.created_by = u.id
            WHERE p.team_id = %s
            ORDER BY p.created_at DESC
            LIMIT 1
        """
        
        if team_id:
            latest_poll = execute_query_one(poll_query, [team_id])
            
            if latest_poll:
                captain_name = f"{latest_poll['first_name']} {latest_poll['last_name']}"
                poll_age = datetime.now() - latest_poll['created_at']
                
                if poll_age.days == 0:
                    time_text = "today"
                elif poll_age.days == 1:
                    time_text = "yesterday"
                else:
                    time_text = f"{poll_age.days} days ago"
                
                notifications.append({
                    "id": f"poll_{latest_poll['id']}",
                    "type": "captain",
                    "title": "Team Poll",
                    "message": f"{captain_name} asked: {latest_poll['question'][:40]}... ({time_text})",
                    "cta": {"label": "Respond Now", "href": f"/mobile/polls/{latest_poll['id']}"},
                    "detail_link": {"label": "View Poll", "href": f"/mobile/polls/{latest_poll['id']}"},
                    "priority": 4
                })
            
    except Exception as e:
        logger.error(f"Error getting urgent notifications: {str(e)}")
    
    return notifications


def get_recent_match_results(user_id, player_id, league_id, team_id):
    """Get recent match result notifications - both personal and team results"""
    notifications = []
    
    try:
        if not player_id or not league_id:
            return notifications
            
        # Get most recent match with detailed information
        results_query = """
            SELECT 
                match_date,
                home_team,
                away_team,
                winner,
                scores,
                home_player_1_id,
                home_player_2_id,
                away_player_1_id,
                away_player_2_id,
                CASE 
                    WHEN home_player_1_id = %s OR home_player_2_id = %s THEN home_team
                    ELSE away_team
                END as player_team,
                CASE 
                    WHEN home_player_1_id = %s OR home_player_2_id = %s THEN 'home'
                    ELSE 'away'
                END as player_side
            FROM match_scores 
            WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
            AND league_id = %s
            ORDER BY match_date DESC
            LIMIT 1
        """
        
        recent_match = execute_query_one(results_query, [player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, league_id])
        
        if recent_match:
            is_winner = recent_match["winner"] == recent_match["player_team"]
            result_text = "won" if is_winner else "lost"
            match_date_str = recent_match["match_date"].strftime("%b %d")
            
            # Determine opponent team
            if recent_match["player_side"] == "home":
                opponent_team = recent_match["away_team"]
            else:
                opponent_team = recent_match["home_team"]
            
            # TEMPORARILY HIDE LOSS NOTIFICATIONS - Only show wins
            if is_winner:
                # 1. Personal match result notification - Only show wins
                notifications.append({
                    "id": f"personal_result_{recent_match['match_date']}",
                    "type": "personal",
                    "title": f"Your Last Match - {result_text.title()}",
                    "message": f"On {match_date_str}, you {result_text} playing against {opponent_team}",
                    "cta": {"label": "View Your Stats", "href": "/mobile/analyze-me"},
                    "priority": 3
                })
                
                # 2. Team match result notification - Only show wins
                notifications.append({
                    "id": f"team_result_{recent_match['match_date']}",
                    "type": "team",
                    "title": f"Team {result_text.title()}",
                    "message": f"{recent_match['home_team']} vs {recent_match['away_team']} - {recent_match['winner']} took the win",
                    "cta": {"label": "View Team Stats", "href": "/mobile/myteam"},
                    "priority": 3
                })
            
    except Exception as e:
        logger.error(f"Error getting recent results: {str(e)}")
    
    return notifications


def get_personal_performance_highlights(user_id, player_id, league_id, team_id):
    """Get personal performance highlight notifications"""
    notifications = []
    
    try:
        if not player_id or not league_id:
            return notifications
            
        # Check for win/loss streaks - FIXED: Proper streak calculation
        streak_query = """
            WITH match_results AS (
                SELECT 
                    match_date,
                    CASE 
                        WHEN home_player_1_id = %s OR home_player_2_id = %s THEN 
                            CASE WHEN winner = home_team THEN 'W' ELSE 'L' END
                        ELSE 
                            CASE WHEN winner = away_team THEN 'W' ELSE 'L' END
                    END as result
                FROM match_scores 
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC
            ),
            streak_groups AS (
                SELECT 
                    result,
                    match_date,
                    ROW_NUMBER() OVER (ORDER BY match_date DESC) as rn,
                    ROW_NUMBER() OVER (PARTITION BY result ORDER BY match_date DESC) as streak_rn,
                    ROW_NUMBER() OVER (ORDER BY match_date DESC) - 
                    ROW_NUMBER() OVER (PARTITION BY result ORDER BY match_date DESC) as streak_group
                FROM match_results
            ),
            current_streak AS (
                SELECT 
                    result,
                    COUNT(*) as streak_length
                FROM streak_groups 
                WHERE streak_group = 0  -- Current streak (most recent consecutive matches)
                GROUP BY result
                ORDER BY streak_length DESC
                LIMIT 1
            )
            SELECT * FROM current_streak
        """
        
        streak_result = execute_query_one(streak_query, [player_id, player_id, player_id, player_id, player_id, player_id, league_id])
        
        # TEMPORARILY HIDE LOSS STREAKS - Only show win streaks
        if streak_result and streak_result["streak_length"] >= 3 and streak_result["result"] == "W":
            streak_type = "win"
            notifications.append({
                "id": f"streak_{streak_type}",
                "type": "personal",
                "title": f"{streak_result['streak_length']}-Match {streak_type.title()} Streak",
                "message": f"You're on a {streak_result['streak_length']}-match {streak_type} streak!",
                "cta": {"label": "View Stats", "href": "/mobile/analyze-me"},
                "priority": 4
            })
            
        # Check for PTI changes since last match
        pti_query = """
            WITH player_current_pti AS (
                SELECT p.pti as current_pti, p.updated_at
                FROM players p
                WHERE p.tenniscores_player_id = %s
                AND p.league_id = %s
            ),
            player_last_match AS (
                SELECT match_date
                FROM match_scores 
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC
                LIMIT 1
            ),
            player_pti_before_match AS (
                SELECT ph.end_pti as previous_pti
                FROM player_history ph
                JOIN players p ON ph.player_id = p.id
                WHERE p.tenniscores_player_id = %s
                AND ph.league_id = %s
                AND ph.date <= (SELECT match_date FROM player_last_match)
                ORDER BY ph.date DESC
                LIMIT 1
            )
            SELECT 
                pcp.current_pti,
                pcp.updated_at,
                lmm.match_date as last_match_date,
                ppbm.previous_pti
            FROM player_current_pti pcp
            LEFT JOIN player_last_match lmm ON TRUE
            LEFT JOIN player_pti_before_match ppbm ON TRUE
            WHERE pcp.current_pti IS NOT NULL
            AND ppbm.previous_pti IS NOT NULL
            AND ABS(pcp.current_pti - ppbm.previous_pti) >= 5
        """
        
        pti_result = execute_query_one(pti_query, [player_id, league_id, player_id, player_id, player_id, player_id, league_id, player_id, league_id])
        
        # TEMPORARILY HIDE PTI DECREASES - Only show increases
        if pti_result and pti_result["current_pti"] and pti_result["previous_pti"]:
            pti_change = pti_result["current_pti"] - pti_result["previous_pti"]
            if pti_change > 0:  # Only show positive changes
                change_direction = "increased"
                change_emoji = "📈"
                notifications.append({
                    "id": f"pti_change",
                    "type": "personal",
                    "title": f"{change_emoji} PTI Rating Update",
                    "message": f"Your rating {change_direction} by {abs(pti_change)} points since your last match",
                    "cta": {"label": "View Your Progress", "href": "/mobile/analyze-me"},
                    "priority": 4
                })
            
    except Exception as e:
        logger.error(f"Error getting personal highlights: {str(e)}")
    
    return notifications


def get_team_performance_highlights(user_id, player_id, league_id, team_id):
    """Get team performance highlight notifications"""
    notifications = []
    
    try:
        if not team_id or not league_id:
            return notifications
            
        # Check team standings
        standings_query = """
            SELECT 
                team_name,
                wins,
                losses,
                position,
                total_matches
            FROM series_stats 
            WHERE team_id = %s 
            AND league_id = %s
            ORDER BY updated_at DESC
            LIMIT 1
        """
        
        team_stats = execute_query_one(standings_query, [team_id, league_id])
        
        if team_stats:
            # TEMPORARILY HIDE TEAM LOSSES - Only show positive team performance
            # Check if team is in playoff position (top 4)
            if team_stats["position"] <= 4 and team_stats["total_matches"] >= 5:
                notifications.append({
                    "id": f"playoff_position",
                    "type": "team",
                    "title": "Playoff Position",
                    "message": f"Your team is in {team_stats['position']}rd place - playoff bound!",
                    "cta": {"label": "View Standings", "href": "/mobile/my-series"},
                    "priority": 5
                })
            # Check for recent team success (only show if wins significantly outweigh losses)
            elif team_stats["wins"] >= 3 and team_stats["losses"] <= 1:
                notifications.append({
                    "id": f"team_success",
                    "type": "team",
                    "title": "Team Success",
                    "message": f"Your team is {team_stats['wins']}-{team_stats['losses']} this season!",
                    "cta": {"label": "View Team", "href": "/mobile/myteam"},
                    "priority": 5
                })
            
    except Exception as e:
        logger.error(f"Error getting team highlights: {str(e)}")
    
    return notifications


def get_fallback_notifications(user_id, player_id, league_id, team_id):
    """Provide fallback notifications when no specific notifications are available"""
    # Return empty list to never show welcome cards
    return []


def get_team_poll_notifications(user_id, player_id, league_id, team_id):
    """Get team poll notifications - most recent poll for user's team"""
    notifications = []
    
    try:
        if not team_id:
            return notifications
            
        # Get the most recent poll for the user's team
        poll_query = """
            SELECT 
                p.id,
                p.question,
                p.created_at,
                p.created_by,
                u.first_name as creator_first_name,
                u.last_name as creator_last_name,
                COUNT(DISTINCT pr.player_id) as response_count
            FROM polls p
            LEFT JOIN users u ON p.created_by = u.id
            LEFT JOIN poll_responses pr ON p.id = pr.poll_id
            WHERE p.team_id = %s
            GROUP BY p.id, p.question, p.created_at, p.created_by, u.first_name, u.last_name
            ORDER BY p.created_at DESC
            LIMIT 1
        """
        
        recent_poll = execute_query_one(poll_query, [team_id])
        
        if recent_poll:
            # Format the creation date
            created_date = recent_poll["created_at"]
            if hasattr(created_date, 'date'):
                created_date = created_date.date()
            
            today = datetime.now().date()
            if created_date == today:
                date_display = "Today"
            elif created_date == today - timedelta(days=1):
                date_display = "Yesterday"
            else:
                date_display = created_date.strftime("%b %d")
            
            creator_name = f"{recent_poll['creator_first_name']} {recent_poll['creator_last_name']}"
            
            notifications.append({
                "id": f"team_poll_{recent_poll['id']}",
                "type": "team",
                "title": "Team Poll",
                "message": f"{recent_poll['question']}",
                "cta": {"label": "Vote Now", "href": f"/mobile/polls/{recent_poll['id']}"},
                "detail_link": {"label": "View Poll", "href": f"/mobile/polls/{recent_poll['id']}"},
                "priority": 4
            })
            
    except Exception as e:
        logger.error(f"Error getting team poll notifications: {str(e)}")
    
    return notifications


@api_bp.route("/api/captain-messages", methods=["POST"])
@login_required
def create_captain_message():
    """Create a new captain message for the team"""
    try:
        user = session["user"]
        user_id = user.get("id")
        team_id = user.get("team_id")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
            
        if not team_id:
            # Enhanced error message with context
            club = user.get("club", "Unknown")
            series = user.get("series", "Unknown")
            league = user.get("league_name", "Unknown")
            return jsonify({
                "error": "Team ID not found when creating captain's message",
                "details": f"You are logged in as {club} - {series} ({league}), but this player record is not assigned to a team. Please contact support to fix your team assignment."
            }), 400
        
        data = request.get_json()
        message = data.get("message", "").strip()
        
        if not message:
            return jsonify({"error": "Message content is required"}), 400
        
        if len(message) > 1000:
            return jsonify({"error": "Message too long (max 1000 characters)"}), 400
        
        # Insert the captain message into the database
        insert_query = """
            INSERT INTO captain_messages (team_id, captain_user_id, message, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING id
        """
        
        result = execute_query_one(insert_query, [team_id, user_id, message])
        
        if result:
            message_id = result["id"]
            
            # Log the activity
            log_user_activity(
                user.get("email"),
                "captain_message_created",
                details=f"Created captain message for team {team_id}: {message[:50]}..."
            )
            
            return jsonify({
                "success": True,
                "message_id": message_id,
                "message": "Captain message created successfully"
            }), 201
        else:
            return jsonify({"error": "Failed to create captain message"}), 500
            
    except Exception as e:
        logger.error(f"Error creating captain message: {str(e)}")
        return jsonify({"error": "Failed to create captain message"}), 500


@api_bp.route("/api/captain-messages", methods=["DELETE"])
@login_required
def remove_captain_message():
    """Remove the current captain message for the team"""
    try:
        user = session["user"]
        user_id = user.get("id")
        team_id = user.get("team_id")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
            
        if not team_id:
            # Enhanced error message with context
            club = user.get("club", "Unknown")
            series = user.get("series", "Unknown")
            league = user.get("league_name", "Unknown")
            return jsonify({
                "error": "Team ID not found when removing captain's message",
                "details": f"You are logged in as {club} - {series} ({league}), but this player record is not assigned to a team. Please contact support to fix your team assignment."
            }), 400
        
        # Get the most recent captain message for the team
        message_query = """
            SELECT id, message, captain_user_id
            FROM captain_messages 
            WHERE team_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        current_message = execute_query_one(message_query, [team_id])
        
        if not current_message:
            return jsonify({"error": "No captain message found to remove"}), 404
        
        # Check if the user is the captain who created the message
        if current_message["captain_user_id"] != user_id:
            return jsonify({"error": "Only the captain who created the message can remove it"}), 403
        
        # Delete the captain message
        delete_query = """
            DELETE FROM captain_messages 
            WHERE id = %s
        """
        
        result = execute_query(delete_query, [current_message["id"]])
        
        if result:
            # Log the activity
            log_user_activity(
                user.get("email"),
                "captain_message_removed",
                details=f"Removed captain message for team {team_id}: {current_message['message'][:50]}..."
            )
            
            return jsonify({
                "success": True,
                "message": "Captain message removed successfully"
            }), 200
        else:
            return jsonify({"error": "Failed to remove captain message"}), 500
            
    except Exception as e:
        logger.error(f"Error removing captain message: {str(e)}")
        return jsonify({"error": "Failed to remove captain message"}), 500


def get_captain_messages(user_id, player_id, league_id, team_id):
    """Get captain message notifications from database"""
    notifications = []
    
    try:
        if not team_id:
            return notifications
        
        # Get the most recent captain message for the team
        message_query = """
            SELECT 
                cm.id,
                cm.message,
                cm.created_at,
                u.first_name,
                u.last_name
            FROM captain_messages cm
            JOIN users u ON cm.captain_user_id = u.id
            WHERE cm.team_id = %s
            ORDER BY cm.created_at DESC
            LIMIT 1
        """
        
        captain_message = execute_query_one(message_query, [team_id])
        
        if captain_message:
            # Calculate how long ago the message was created
            # Handle timezone-aware datetime comparison
            now = datetime.now()
            created_at = captain_message['created_at']
            
            # If created_at is timezone-aware, make now timezone-aware too
            if created_at.tzinfo is not None:
                from datetime import timezone
                now = now.replace(tzinfo=timezone.utc)
            
            message_age = now - created_at
            
            if message_age.days == 0:
                time_text = "today"
            elif message_age.days == 1:
                time_text = "yesterday"
            else:
                time_text = f"{message_age.days} days ago"
            
            captain_name = f"{captain_message['first_name']} {captain_message['last_name']}"
            
            notifications.append({
                "id": f"captain_message_{captain_message['id']}",
                "type": "captain",
                "title": "Captain's Message",
                "message": f"{captain_message['message'][:60]}{'...' if len(captain_message['message']) > 60 else ''}",
                "detail_link": {"label": "View Message", "href": "/mobile/polls"},
                "priority": 1
            })
            
    except Exception as e:
        logger.error(f"Error getting captain messages: {str(e)}")
    
    return notifications


def get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id):
    """Get upcoming practice and match notifications from schedule with weather data"""
    notifications = []
    
    try:
        if not team_id:
            return notifications
        
        # Get user's team information from database instead of session
        user_info_query = """
            SELECT 
                c.name as club_name,
                s.name as series_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
            ORDER BY p.id DESC
            LIMIT 1
        """
        
        user_info = execute_query_one(user_info_query, [player_id])
        if not user_info:
            return notifications
            
        user_club = user_info.get("club_name")
        user_series = user_info.get("series_name")
        
        if not user_club or not user_series:
            return notifications
        
        # Build team pattern for matches
        if "Series" in user_series:
            # NSTF format: "Series 2B" -> "S2B"
            series_code = user_series.replace("Series ", "S")
            team_pattern = f"{user_club} {series_code} - {user_series}"
        elif "Division" in user_series:
            # CNSWPL format: "Division 12" -> "12"
            division_num = user_series.replace("Division ", "")
            team_pattern = f"{user_club} {division_num} - Series {division_num}"
        else:
            # APTA format: "Chicago 22" -> extract number
            series_num = user_series.split()[-1] if user_series else ""
            team_pattern = f"{user_club} - {series_num}"
        
        # Build practice pattern
        if "Division" in user_series:
            division_num = user_series.replace("Division ", "")
            practice_pattern = f"{user_club} Practice - Series {division_num}"
        else:
            practice_pattern = f"{user_club} Practice - {user_series}"
        
        # Get current date/time
        now = datetime.now()
        current_date = now.date()
        
        # Query upcoming schedule entries using team_id for robust matching
        schedule_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team_id,
                s.away_team_id,
                s.home_team,
                s.away_team,
                s.location,
                c.club_address,
                CASE 
                    WHEN s.home_team_id = %s AND s.away_team_id IS NULL THEN 'practice'
                    WHEN s.home_team_id = %s AND s.away_team_id IS NOT NULL THEN 'match'
                    WHEN s.away_team_id = %s THEN 'match'
                    ELSE 'unknown'
                END as type
            FROM schedule s
            LEFT JOIN teams t ON (s.home_team_id = t.id OR s.away_team_id = t.id)
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE (s.home_team_id = %s OR s.away_team_id = %s)
            AND s.match_date >= %s
            ORDER BY s.match_date ASC, s.match_time ASC
            LIMIT 10
        """
        
        schedule_entries = execute_query(schedule_query, [team_id, team_id, team_id, team_id, team_id, current_date])
        
        if not schedule_entries:
            return notifications
        
        # Debug logging
        logger.info(f"Schedule notification debug - team_id: {team_id}, found {len(schedule_entries)} entries")
        for entry in schedule_entries:
            logger.info(f"  {entry['match_date']} {entry['match_time']}: {entry['home_team']} vs {entry['away_team']} (type: {entry['type']})")
        
        # Find next practice and next match
        next_practice = None
        next_match = None
        
        for entry in schedule_entries:
            if entry["type"] == "practice" and not next_practice:
                next_practice = entry
            elif entry["type"] == "match" and not next_match:
                next_match = entry
            
            if next_practice and next_match:
                break
        
        # Get weather data for upcoming events
        weather_data = {}
        try:
            from app.services.weather_service import WeatherService
            weather_service = WeatherService()
            
            # Prepare schedule entries for weather lookup
            weather_entries = []
            if next_practice:
                weather_entries.append({
                    'id': f"practice_{next_practice['id']}",
                    'location': next_practice.get('club_address') or next_practice.get('location') or f"{user_club}, IL",
                    'match_date': next_practice['match_date'].strftime('%Y-%m-%d')
                })
            
            if next_match:
                weather_entries.append({
                    'id': f"match_{next_match['id']}",
                    'location': next_match.get('club_address') or next_match.get('location') or f"{user_club}, IL",
                    'match_date': next_match['match_date'].strftime('%Y-%m-%d')
                })
            
            # Get weather forecasts
            weather_data = weather_service.get_weather_for_schedule_entries(weather_entries)
            
        except Exception as e:
            logger.warning(f"Could not fetch weather data: {str(e)}")
        
        # Build notification message with weather
        practice_text = "No upcoming practices"
        match_text = "No upcoming matches"
        
        if next_practice:
            # Only show practices that are within the next 30 days
            practice_date = next_practice["match_date"]
            days_until_practice = (practice_date - current_date).days
            
            if days_until_practice <= 30:
                practice_date_str = practice_date.strftime("%b %d")
                practice_time = next_practice["match_time"].strftime("%I:%M %p").lstrip("0") if next_practice["match_time"] else ""
                practice_text = f"Practice: {practice_date_str}"
                if practice_time:
                    practice_text += f" at {practice_time}"
                logger.info(f"Schedule notification: Showing practice on {practice_date_str} ({days_until_practice} days away)")
            else:
                logger.info(f"Schedule notification: Practice on {practice_date} is too far away ({days_until_practice} days), not showing")
        
        if next_match:
            match_date = next_match["match_date"].strftime("%b %d")
            match_time = next_match["match_time"].strftime("%I:%M %p").lstrip("0") if next_match["match_time"] else ""
            # Determine opponent using team_id
            if next_match["home_team_id"] == team_id:
                opponent = next_match["away_team"]
            else:
                opponent = next_match["home_team"]
            match_text = f"Match: {match_date}"
            if match_time:
                match_text += f" at {match_time}"
            if opponent:
                match_text += f" vs {opponent}"
        
        # Create notification with weather data
        notification_data = {
            "id": "upcoming_schedule",
            "type": "schedule",
            "title": "Upcoming Schedule",
            "message": f"{practice_text}\n{match_text}",
            "cta": {"label": "View Schedule", "href": "/mobile/availability"},
            "detail_link": {"label": "View Schedule", "href": "/mobile/availability"},
            "priority": 2
        }
        
        # Add weather data to notification if available
        if weather_data:
            # Convert WeatherForecast objects to dictionaries for JSON serialization
            weather_dict = {}
            for key, forecast in weather_data.items():
                if hasattr(forecast, '__dict__'):
                    weather_dict[key] = {
                        'date': forecast.date,
                        'temperature_high': forecast.temperature_high,
                        'temperature_low': forecast.temperature_low,
                        'condition': forecast.condition,
                        'condition_code': forecast.condition_code,
                        'precipitation_chance': forecast.precipitation_chance,
                        'wind_speed': forecast.wind_speed,
                        'humidity': forecast.humidity,
                        'icon': forecast.icon
                    }
                else:
                    weather_dict[key] = forecast
            notification_data["weather"] = weather_dict
        
        notifications.append(notification_data)
        
    except Exception as e:
        logger.error(f"Error getting schedule notifications: {str(e)}")
    
    return notifications


def get_pickup_games_notifications(user_id, player_id, league_id, team_id):
    """Get pickup games notifications for games where user meets criteria"""
    notifications = []
    
    try:
        # Get user's PTI and series information from all player associations
        # Find a player record with a valid PTI (not None)
        user_info_query = """
            SELECT 
                p.pti as user_pti,
                p.series_id as user_series_id,
                s.name as user_series_name,
                c.name as user_club_name
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN clubs c ON p.club_id = c.id
            WHERE upa.user_id = %s AND p.pti IS NOT NULL
            ORDER BY p.pti DESC
            LIMIT 1
        """
        
        user_info = execute_query_one(user_info_query, [user_id])
        
        if not user_info or not user_info.get("user_pti"):
            return notifications
        
        user_pti = user_info["user_pti"]
        user_series_id = user_info["user_series_id"]
        user_club_name = user_info["user_club_name"]
        
        # Get current date/time for determining upcoming games
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()
        
        # Find pickup games where user meets criteria
        pickup_games_query = """
            SELECT 
                pg.id,
                pg.description,
                pg.game_date,
                pg.game_time,
                pg.players_requested,
                pg.pti_low,
                pg.pti_high,
                pg.series_low,
                pg.series_high,
                pg.club_only,
                COUNT(pgp.id) as current_participants
            FROM pickup_games pg
            LEFT JOIN pickup_game_participants pgp ON pg.id = pgp.pickup_game_id
            WHERE ((pg.game_date > %s) OR (pg.game_date = %s AND pg.game_time > %s))
            AND (pg.pti_low <= %s AND pg.pti_high >= %s)
            AND (
                (pg.series_low IS NULL AND pg.series_high IS NULL) OR
                (pg.series_low IS NOT NULL AND pg.series_low <= %s) OR
                (pg.series_high IS NOT NULL AND pg.series_high >= %s) OR
                (pg.series_low IS NOT NULL AND pg.series_high IS NOT NULL AND pg.series_low <= %s AND pg.series_high >= %s)
            )
            AND (
                pg.club_only = false OR 
                pg.club_id IS NULL OR
                (pg.club_only = true AND pg.club_id IN (
                    SELECT DISTINCT p.club_id 
                    FROM user_player_associations upa
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    WHERE upa.user_id = %s AND p.club_id IS NOT NULL
                ))
            )
            AND NOT EXISTS (
                SELECT 1 FROM pickup_game_participants pgp2 
                WHERE pgp2.pickup_game_id = pg.id AND pgp2.user_id = %s
            )
            GROUP BY pg.id
            HAVING COUNT(pgp.id) < pg.players_requested
            ORDER BY pg.game_date ASC, pg.game_time ASC
            LIMIT 3
        """
        
        matching_games = execute_query(pickup_games_query, [
            current_date, current_date, current_time,
            user_pti, user_pti,
            user_series_id, user_series_id, user_series_id, user_series_id,
            user_id,
            user_id
        ])
        
        for game in matching_games:
            # Format game date and time
            game_date = game["game_date"]
            game_time = game["game_time"]
            
            # Format date for display
            if game_date == current_date:
                date_display = "Today"
            elif game_date == current_date + timedelta(days=1):
                date_display = "Tomorrow"
            else:
                date_display = game_date.strftime("%A, %b %d")
            
            # Format time for display
            time_display = game_time.strftime("%I:%M %p").lstrip('0')
            
            # Calculate available slots
            available_slots = game["players_requested"] - game["current_participants"]
            
            # Create notification
            notifications.append({
                "id": f"pickup_game_{game['id']}",
                "type": "match",
                "title": "Pickup Game Available",
                "message": f"{game['description']} - {date_display} at {time_display} ({available_slots} spots left)",
                "cta": {"label": "Join Game", "href": "/mobile/pickup-games"},
                "detail_link": {"label": "View Game", "href": f"/mobile/pickup-games/{game['id']}"},
                "priority": 5
            })
            
    except Exception as e:
        logger.error(f"Error getting pickup games notifications: {str(e)}")
    
    return notifications


def get_team_position_notifications(user_id, player_id, league_id, team_id):
    """Get team position notifications showing current standings"""
    notifications = []
    
    try:
        if not team_id:
            return notifications
            
        # Get team information first to get series_id and league_id
        team_info_query = """
            SELECT 
                t.id as team_id,
                t.team_name,
                t.series_id,
                t.league_id,
                s.name as series_name,
                c.name as club_name
            FROM teams t
            JOIN series s ON t.series_id = s.id
            JOIN clubs c ON t.club_id = c.id
            WHERE t.id = %s
        """
        
        team_info = execute_query_one(team_info_query, [team_id])
        
        if not team_info:
            return notifications
            
        # Get team standings information using series_id and league_id (same logic as /api/series-stats)
        # Strategy 1: Try direct series_id lookup
        standings_query = """
            SELECT 
                ss.team,
                ss.points,
                ss.matches_won,
                ss.matches_lost,
                ss.matches_tied,
                ss.league_id,
                ss.series_id
            FROM series_stats ss
            WHERE ss.series_id = %s AND ss.league_id = %s
            AND ss.team = %s
            ORDER BY ss.updated_at DESC
            LIMIT 1
        """
        
        team_stats = execute_query_one(standings_query, [team_info["series_id"], team_info["league_id"], team_info["team_name"]])
        
        # Strategy 2: Fallback to series name matching if direct lookup failed
        if not team_stats:
            # Try to find series_stats by team name and league_id (ignore series_id mismatch)
            fallback_query = """
                SELECT 
                    ss.team,
                    ss.points,
                    ss.matches_won,
                    ss.matches_lost,
                    ss.matches_tied,
                    ss.league_id,
                    ss.series_id
                FROM series_stats ss
                WHERE ss.league_id = %s
                AND ss.team = %s
                ORDER BY ss.updated_at DESC
                LIMIT 1
            """
            
            team_stats = execute_query_one(fallback_query, [team_info["league_id"], team_info["team_name"]])
        
        if not team_stats:
            return notifications
            
        # Get all teams in the same series for ranking
        # Use the series_id from team_stats (which might be different from team_info)
        all_teams_query = """
            SELECT 
                ss.team,
                ss.points,
                ss.matches_won,
                ss.matches_lost,
                ss.matches_tied
            FROM series_stats ss
            WHERE ss.series_id = %s AND ss.league_id = %s
            ORDER BY ss.points DESC
        """
        
        all_teams = execute_query(all_teams_query, [team_stats["series_id"], team_stats["league_id"]])
        
        if not all_teams:
            return notifications
            
        # Find team's position
        team_position = 1
        first_place_points = all_teams[0]["points"] if all_teams else 0
        
        for i, team in enumerate(all_teams, 1):
            if team["team"] == team_info["team_name"]:
                team_position = i
                break
        
        # Calculate average points per week
        total_matches = team_stats["matches_won"] + team_stats["matches_lost"] + (team_stats["matches_tied"] or 0)
        avg_points_per_week = round(team_stats["points"] / total_matches, 1) if total_matches > 0 else 0
        
        # Calculate points back from first place
        points_back = first_place_points - team_stats["points"]
        
        # Format team name
        team_display_name = team_info["team_name"]
        
        # Create notification message
        if points_back == 0:
            position_text = f"{team_display_name} is in 1st place with {team_stats['points']} total points, averaging {avg_points_per_week} points per week."
        else:
            position_text = f"{team_display_name} has {team_stats['points']} total points, averaging {avg_points_per_week} points per week and is currently {points_back} points back."
        
        notifications.append({
            "id": f"team_position_{team_id}",
            "type": "team",
            "title": "Team Position",
            "message": position_text,
            "cta": {"label": "View Standings", "href": "/mobile/my-series"},
            "detail_link": {"label": "View Standings", "href": "/mobile/my-series"},
            "priority": 3
        })
            
    except Exception as e:
        logger.error(f"Error getting team position notifications: {str(e)}")
    
    return notifications


def get_my_win_streaks_notifications(user_id, player_id, league_id, team_id):
    """Get current player's win streaks notification"""
    notifications = []
    
    try:
        if not player_id or not league_id:
            return notifications
            
        # Get user's name for personalized messages
        user_query = """
            SELECT first_name, last_name
            FROM users 
            WHERE id = %s
        """
        user_info = execute_query_one(user_query, [user_id])
        user_name = user_info.get("first_name", "Player") if user_info else "Player"
            
        # Calculate both current streak and best season streak
        streak_query = """
            WITH match_results AS (
                SELECT 
                    match_date,
                    CASE 
                        WHEN home_player_1_id = %s OR home_player_2_id = %s THEN 
                            CASE WHEN winner = 'home' THEN 'W' ELSE 'L' END
                        ELSE 
                            CASE WHEN winner = 'away' THEN 'W' ELSE 'L' END
                    END as result
                FROM match_scores 
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                ORDER BY match_date ASC
            ),
            streak_groups AS (
                SELECT 
                    result,
                    match_date,
                    ROW_NUMBER() OVER (ORDER BY match_date) as rn,
                    ROW_NUMBER() OVER (PARTITION BY result ORDER BY match_date) as streak_rn,
                    ROW_NUMBER() OVER (ORDER BY match_date) - 
                    ROW_NUMBER() OVER (PARTITION BY result ORDER BY match_date) as streak_group
                FROM match_results
            ),
            streak_lengths AS (
                SELECT 
                    result, 
                    streak_group, 
                    COUNT(*) as streak_length,
                    MAX(match_date) as last_match_date
                FROM streak_groups 
                GROUP BY result, streak_group
            ),
            current_streak AS (
                SELECT 
                    result,
                    streak_length
                FROM streak_lengths 
                WHERE last_match_date = (SELECT MAX(match_date) FROM match_results)
            ),
            best_win_streak AS (
                SELECT streak_length, MAX(last_match_date) as last_win_date
                FROM streak_lengths
                WHERE result = 'W'
                GROUP BY streak_length
                ORDER BY streak_length DESC, last_win_date DESC
                LIMIT 1
            )
            SELECT 
                cs.result as current_streak_result,
                cs.streak_length as current_streak_length,
                COALESCE(bws.streak_length, 0) as best_win_streak_length,
                bws.last_win_date as best_win_streak_end_date
            FROM current_streak cs
            CROSS JOIN best_win_streak bws
        """
        
        streak_result = execute_query_one(streak_query, [player_id, player_id, player_id, player_id, player_id, player_id, league_id])
        
        # Always show a notification card with appropriate message
        if streak_result:
            current_streak_length = streak_result.get("current_streak_length", 0)
            current_streak_result = streak_result.get("current_streak_result", "")
            best_win_streak_length = streak_result.get("best_win_streak_length", 0) or 0
            best_win_streak_end_date = streak_result.get("best_win_streak_end_date")
            
            if current_streak_length >= 3 and current_streak_result == "W":
                # Show current win streak message
                notifications.append({
                    "id": f"my_win_streak_{player_id}",
                    "type": "personal",
                    "title": "My Win Streaks",
                    "message": f"Great job {user_name}, you're on a {current_streak_length}-match win streak! Keep the momentum going.",
                    "cta": {"label": "View My Stats", "href": "/mobile/analyze-me"},
                    "detail_link": {"label": "View My Stats", "href": "/mobile/analyze-me"},
                    "priority": 6
                })
            elif best_win_streak_length >= 3:
                # Show best season streak message
                if best_win_streak_end_date:
                    from datetime import datetime
                    try:
                        date_obj = best_win_streak_end_date
                        if isinstance(date_obj, str):
                            date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
                        date_str = date_obj.strftime("%B %d, %Y")
                    except Exception:
                        date_str = str(best_win_streak_end_date)
                else:
                    date_str = "unknown date"
                notifications.append({
                    "id": f"my_best_streak_{player_id}",
                    "type": "personal",
                    "title": "My Win Streaks",
                    "message": f"Your best win streak this season was {best_win_streak_length}, which ended on {date_str}.",
                    "cta": {"label": "View My Stats", "href": "/mobile/analyze-me"},
                    "detail_link": {"label": "View My Stats", "href": "/mobile/analyze-me"},
                    "priority": 6
                })
            else:
                # Show no streaks message
                notifications.append({
                    "id": f"my_no_streaks_{player_id}",
                    "type": "personal",
                    "title": "My Win Streaks",
                    "message": f"You don't have any winning streaks this season.",
                    "cta": {"label": "View My Stats", "href": "/mobile/analyze-me"},
                    "detail_link": {"label": "View My Stats", "href": "/mobile/analyze-me"},
                    "priority": 6
                })
        else:
            # No match data available
            notifications.append({
                "id": f"my_no_streaks_{player_id}",
                "type": "personal",
                "title": "My Win Streaks",
                "message": f"You don't have any winning streaks this season.",
                "cta": {"label": "View My Stats", "href": "/mobile/analyze-me"},
                "detail_link": {"label": "View My Stats", "href": "/mobile/analyze-me"},
                "priority": 6
            })
            
    except Exception as e:
        logger.error(f"Error getting my win streaks notifications: {str(e)}")
    
    return notifications
