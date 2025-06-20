"""
API Routes Blueprint

This module contains all API routes that were moved from the main server.py file.
These routes handle API endpoints for data retrieval, research, analytics, and other backend operations.
"""

from flask import Blueprint, request, jsonify, session, g
from functools import wraps
from utils.logging import log_user_activity
from database_utils import execute_query, execute_query_one, execute_update
from app.services.dashboard_service import log_user_action
from app.services.api_service import *
from app.services.mobile_service import get_club_players_data
from datetime import datetime
import pytz
import json
import os
from utils.database_player_lookup import find_player_by_database_lookup
from app.models.database_models import SessionLocal, User, Player, UserPlayerAssociation

api_bp = Blueprint('api', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route('/api/series-stats')
@login_required
def get_series_stats():
    """Get series statistics"""
    return get_series_stats_data()

@api_bp.route('/api/test-log', methods=['GET'])
@login_required
def test_log():
    """Test log endpoint"""
    return test_log_data()

@api_bp.route('/api/verify-logging')
@login_required
def verify_logging():
    """Verify logging"""
    return verify_logging_data()

@api_bp.route('/api/log-click', methods=['POST'])
def log_click():
    """Log click events"""
    return log_click_data()

@api_bp.route('/api/research-team')
@login_required
def research_team():
    """Research team data"""
    return research_team_data()

@api_bp.route('/api/player-court-stats/<player_name>')
def player_court_stats(player_name):
    """Get player court statistics"""
    return get_player_court_stats_data(player_name)

@api_bp.route('/api/research-my-team')
@login_required
def research_my_team():
    """Research my team data"""
    return research_my_team_data()

@api_bp.route('/api/research-me')
@login_required
def research_me():
    """Research me data"""
    return research_me_data()

@api_bp.route('/api/win-streaks')
@login_required
def get_win_streaks():
    """Get win streaks"""
    return get_win_streaks_data()

@api_bp.route('/api/player-streaks')
def get_player_streaks():
    """Get player streaks"""
    return get_player_streaks_data()

@api_bp.route('/api/enhanced-streaks')
@login_required
def get_enhanced_streaks():
    """Get enhanced streaks"""
    return get_enhanced_streaks_data()

@api_bp.route('/api/last-3-matches')
@login_required
def get_last_3_matches():
    """Get the last 3 matches for the current user"""
    try:
        user = session['user']
        player_id = user.get('tenniscores_player_id')
        
        if not player_id:
            return jsonify({'error': 'Player ID not found'}), 404
        
        # Get user's league for filtering
        user_league_id = user.get('league_id', '')
        
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
            matches = execute_query(matches_query, [player_id, player_id, player_id, player_id, league_id_int])
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
            matches = execute_query(matches_query, [player_id, player_id, player_id, player_id])
        
        if not matches:
            return jsonify({'matches': [], 'message': 'No recent matches found'})
        
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
                    player_record = execute_query_one(name_query, [player_id, league_id_int])
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
            is_home = player_id in [match.get('Home Player 1'), match.get('Home Player 2')]
            winner = match.get('Winner', '').lower()
            
            # Determine if player won
            player_won = (is_home and winner == 'home') or (not is_home and winner == 'away')
            
            # Get partner name
            if is_home:
                partner_id = match.get('Home Player 2') if match.get('Home Player 1') == player_id else match.get('Home Player 1')
            else:
                partner_id = match.get('Away Player 2') if match.get('Away Player 1') == player_id else match.get('Away Player 1')
            
            partner_name = get_player_name(partner_id) if partner_id else 'No Partner'
            
            # Get opponent names
            if is_home:
                opponent1_id = match.get('Away Player 1')
                opponent2_id = match.get('Away Player 2')
            else:
                opponent1_id = match.get('Home Player 1')
                opponent2_id = match.get('Home Player 2')
            
            opponent1_name = get_player_name(opponent1_id) if opponent1_id else 'Unknown'
            opponent2_name = get_player_name(opponent2_id) if opponent2_id else 'Unknown'
            
            processed_match = {
                'date': match.get('Date'),
                'home_team': match.get('Home Team'),
                'away_team': match.get('Away Team'),
                'scores': match.get('Scores'),
                'player_was_home': is_home,
                'player_won': player_won,
                'partner_name': partner_name,
                'opponent1_name': opponent1_name,
                'opponent2_name': opponent2_name,
                'match_result': 'Won' if player_won else 'Lost'
            }
            processed_matches.append(processed_match)
        
        return jsonify({
            'matches': processed_matches,
            'total_matches': len(processed_matches)
        })
        
    except Exception as e:
        print(f"Error getting last 3 matches: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to retrieve matches'}), 500

@api_bp.route('/api/team-last-3-matches')
@login_required
def get_team_last_3_matches():
    """Get the last 3 matches for the current user's team using team_id"""
    try:
        user = session['user']
        
        # Get user's team information
        user_club = user.get('club', '')
        user_series = user.get('series', '')
        user_league_id = user.get('league_id', '')
        
        if not user_club or not user_series:
            return jsonify({'error': 'Team information not found'}), 404
        
        # Convert league_id to integer foreign key for database queries
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != '':
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", 
                    [user_league_id]
                )
                if league_record:
                    league_id_int = league_record['id']
                else:
                    return jsonify({'error': 'League not found'}), 404
            except Exception as e:
                return jsonify({'error': 'Failed to resolve league'}), 500
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
        
        team_record = execute_query_one(team_query, [user_club, user_series, league_id_int])
        
        if not team_record:
            return jsonify({'error': 'Team not found in database', 'club': user_club, 'series': user_series}), 404
        
        team_id = team_record['id']
        team_name = team_record['team_name']
        
        # Query the last 3 matches using team_id (much more efficient!)
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
            WHERE (home_team_id = %s OR away_team_id = %s)
            ORDER BY match_date DESC
            LIMIT 3
        """
        matches = execute_query(matches_query, [team_id, team_id])
        
        if not matches:
            return jsonify({'matches': [], 'message': 'No recent team matches found', 'team_name': team_name, 'team_id': team_id})
        
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
                    player_record = execute_query_one(name_query, [player_id, league_id_int])
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
            is_home = match.get('Home Team') == team_name
            winner = match.get('Winner', '').lower()
            
            # Determine if team won
            team_won = (is_home and winner == 'home') or (not is_home and winner == 'away')
            
            # Get our team's players
            if is_home:
                our_player1_id = match.get('Home Player 1')
                our_player2_id = match.get('Home Player 2')
                opponent_team = match.get('Away Team')
                opponent_player1_id = match.get('Away Player 1')
                opponent_player2_id = match.get('Away Player 2')
            else:
                our_player1_id = match.get('Away Player 1')
                our_player2_id = match.get('Away Player 2')
                opponent_team = match.get('Home Team')
                opponent_player1_id = match.get('Home Player 1')
                opponent_player2_id = match.get('Home Player 2')
            
            # Get readable names
            our_player1_name = get_player_name(our_player1_id) if our_player1_id else 'Unknown'
            our_player2_name = get_player_name(our_player2_id) if our_player2_id else 'Unknown'
            opponent_player1_name = get_player_name(opponent_player1_id) if opponent_player1_id else 'Unknown'
            opponent_player2_name = get_player_name(opponent_player2_id) if opponent_player2_id else 'Unknown'
            
            processed_match = {
                'date': match.get('Date'),
                'home_team': match.get('Home Team'),
                'away_team': match.get('Away Team'),
                'scores': match.get('Scores'),
                'team_was_home': is_home,
                'team_won': team_won,
                'our_player1_name': our_player1_name,
                'our_player2_name': our_player2_name,
                'opponent_team': opponent_team,
                'opponent_player1_name': opponent_player1_name,
                'opponent_player2_name': opponent_player2_name,
                'match_result': 'Won' if team_won else 'Lost'
            }
            processed_matches.append(processed_match)
        
        return jsonify({
            'matches': processed_matches,
            'total_matches': len(processed_matches),
            'team_name': team_name,
            'team_id': team_id
        })
        
    except Exception as e:
        print(f"Error getting team's last 3 matches: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to retrieve team matches'}), 500

@api_bp.route('/api/find-training-video', methods=['POST'])
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
        import os
        import json
        import random
        
        message_lower = message.lower()
        
        # Load training guide for detailed responses
        try:
            guide_path = os.path.join('data', 'leagues', 'apta', 'improve_data', 'complete_platform_tennis_training_guide.json')
            with open(guide_path, 'r', encoding='utf-8') as f:
                training_guide = json.load(f)
        except Exception:
            training_guide = {}
        
        # Define response patterns based on common queries
        if any(word in message_lower for word in ['serve', 'serving']):
            return generate_serve_response(training_guide)
        elif any(word in message_lower for word in ['volley', 'net', 'net play']):
            return generate_volley_response(training_guide)
        elif any(word in message_lower for word in ['return', 'returning']):
            return generate_return_response(training_guide)
        elif any(word in message_lower for word in ['blitz', 'blitzing', 'attack']):
            return generate_blitz_response(training_guide)
        elif any(word in message_lower for word in ['lob', 'lobbing', 'overhead']):
            return generate_lob_response(training_guide)
        elif any(word in message_lower for word in ['strategy', 'tactics', 'positioning']):
            return generate_strategy_response(training_guide)
        elif any(word in message_lower for word in ['footwork', 'movement', 'court position']):
            return generate_footwork_response(training_guide)
        elif any(word in message_lower for word in ['practice', 'drill', 'improve', 'training']):
            return generate_practice_response(training_guide)
        elif any(word in message_lower for word in ['beginner', 'start', 'new', 'basics']):
            return generate_beginner_response(training_guide)
        else:
            return generate_general_response(message, training_guide)
        
    except Exception as e:
        print(f"Error generating chat response: {str(e)}")
        return "I'm here to help you improve your paddle tennis game! Try asking me about serves, volleys, strategy, or any specific technique you'd like to work on."

def generate_serve_response(training_guide):
    """Generate response about serving"""
    serve_data = training_guide.get('Serve technique and consistency', {})
    tips = [
        "**Serve Fundamentals:**",
        "• Keep your toss consistent - aim for the same spot every time",
        "• Use a continental grip for better control and spin options",
        "• Follow through towards your target after contact",
        "• Practice hitting to different areas of the service box"
    ]
    
    if serve_data.get('Coach\'s Cues'):
        tips.extend([f"• {cue}" for cue in serve_data['Coach\'s Cues'][:2]])
    
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
        f"Regarding '{message}', here are some important fundamentals:"
    ]
    
    tips = [
        "**Focus on Fundamentals:** Master the basics before moving to advanced techniques",
        "**Practice Regularly:** Consistent practice is more valuable than occasional long sessions", 
        "**Play with Better Players:** You'll improve faster by challenging yourself",
        "**Watch and Learn:** Observe skilled players and ask questions",
        "**Stay Patient:** Improvement takes time - celebrate small victories!"
    ]
    
    follow_ups = [
        "What specific technique would you like to work on?",
        "Are you looking for practice drills or match strategy?",
        "What's the biggest challenge you're facing right now?",
        "Would you like tips for a particular shot or situation?"
    ]
    
    import random
    response = random.choice(responses) + "\n\n" + "\n".join(tips[:3]) + "\n\n" + random.choice(follow_ups)
    return response

@api_bp.route('/api/add-practice-times', methods=['POST'])
@login_required
def add_practice_times():
    """API endpoint to add practice times to the schedule"""
    try:
        # Get form data
        first_date = request.form.get('first_date')
        last_date = request.form.get('last_date')
        day = request.form.get('day')
        time = request.form.get('time')
        
        # Validate required fields
        if not all([first_date, last_date, day, time]):
            return jsonify({
                'success': False, 
                'message': 'All fields are required (first date, last date, day, and time)'
            }), 400
        
        # Get user's club to determine which team schedule to update
        user = session['user']
        user_club = user.get('club', '')
        user_series = user.get('series', '')
        
        if not user_club:
            return jsonify({
                'success': False, 
                'message': 'User club not found'
            }), 400
            
        if not user_series:
            return jsonify({
                'success': False, 
                'message': 'User series not found'
            }), 400
        
        # Convert form data to appropriate formats
        from datetime import datetime, timedelta
        import json
        import os
        
        # Parse the dates
        try:
            first_date_obj = datetime.strptime(first_date, "%Y-%m-%d")
            last_date_obj = datetime.strptime(last_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Invalid date format'
            }), 400
        
        # Validate date range
        if last_date_obj < first_date_obj:
            return jsonify({
                'success': False, 
                'message': 'Last practice date must be after or equal to first practice date'
            }), 400
        
        # Check for reasonable date range (not more than 2 years)
        date_diff = (last_date_obj - first_date_obj).days
        if date_diff > 730:  # 2 years
            return jsonify({
                'success': False, 
                'message': 'Date range too large. Please select a range of 2 years or less.'
            }), 400
        
        # Convert 24-hour time to 12-hour format
        try:
            time_obj = datetime.strptime(time, "%H:%M")
            formatted_time = time_obj.strftime("%I:%M %p").lstrip('0')
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Invalid time format'
            }), 400
        
        # Get league ID for the user
        league_id = None
        try:
            user_league = execute_query_one("""
                SELECT l.id 
                FROM users u 
                LEFT JOIN leagues l ON u.league_id = l.id 
                WHERE u.email = %(email)s
            """, {'email': user['email']})
            
            if user_league:
                league_id = user_league['id']
        except Exception as e:
            print(f"Could not get league ID for user: {e}")
        
        # Convert day name to number (0=Monday, 6=Sunday)
        day_map = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        target_weekday = day_map.get(day)
        
        if target_weekday is None:
            return jsonify({
                'success': False, 
                'message': 'Invalid day selected'
            }), 400
        
        # Start from the first practice date
        current_date = first_date_obj
        practices_added = 0
        added_practices = []  # Track the specific practices added
        failed_practices = []  # Track any failures
        
        # Check for existing practices to avoid duplicates
        practice_description = f"{user_club} Practice - {user_series}"
        existing_query = """
            SELECT match_date FROM schedule 
            WHERE league_id = %(league_id)s 
            AND home_team = %(practice_desc)s
            AND match_date BETWEEN %(start_date)s AND %(end_date)s
        """
        
        try:
            existing_practices = execute_query(existing_query, {
                'league_id': league_id,
                'practice_desc': practice_description,
                'start_date': first_date_obj.date(),
                'end_date': last_date_obj.date()
            })
            existing_dates = {practice['match_date'] for practice in existing_practices}
            
            if existing_dates:
                return jsonify({
                    'success': False,
                    'message': f'Some practice dates already exist in the schedule. Please remove existing practices first or choose different dates.'
                }), 400
                
        except Exception as e:
            print(f"Error checking existing practices: {e}")
            # Continue anyway - we'll handle duplicates during insertion
        
        # Add practice entries to database for the specified date range
        while current_date <= last_date_obj:
            # If current date is the target weekday, add practice
            if current_date.weekday() == target_weekday:
                try:
                    # Parse formatted time back to time object for database storage
                    time_obj = datetime.strptime(formatted_time, '%I:%M %p').time()
                    
                    # Insert practice into schedule table
                    execute_query("""
                        INSERT INTO schedule (league_id, match_date, match_time, home_team, away_team, location)
                        VALUES (%(league_id)s, %(match_date)s, %(match_time)s, %(practice_desc)s, '', %(location)s)
                    """, {
                        'league_id': league_id,
                        'match_date': current_date.date(),
                        'match_time': time_obj,
                        'practice_desc': practice_description,
                        'location': user_club
                    })
                    
                    practices_added += 1
                    
                    # Add to our tracking list for the response
                    added_practices.append({
                        "date": current_date.strftime("%m/%d/%Y"),
                        "time": formatted_time,
                        "day": day
                    })
                    
                except Exception as e:
                    print(f"Error inserting practice for {current_date}: {e}")
                    failed_practices.append({
                        "date": current_date.strftime("%m/%d/%Y"),
                        "error": str(e)
                    })
                    # Continue with other dates even if one fails
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Check if we had any successes
        if practices_added == 0:
            error_msg = 'No practices were added.'
            if failed_practices:
                error_msg += f' {len(failed_practices)} practices failed to add due to errors.'
            else:
                error_msg += f' No {day}s found between {first_date} and {last_date}.'
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500
        
        # Log the activity
        from utils.logging import log_user_activity
        log_user_activity(
            user['email'], 
            'practice_times_added',
            details=f'Added {practices_added} practice times for {user_series} {day}s at {formatted_time} from {first_date} to {last_date}'
        )
        
        success_message = f'Successfully added {practices_added} practice times to the schedule!'
        if failed_practices:
            success_message += f' ({len(failed_practices)} practices failed to add)'
        
        return jsonify({
            'success': True, 
            'message': success_message,
            'practices_added': added_practices,
            'count': practices_added,
            'series': user_series,
            'day': day,
            'time': formatted_time,
            'first_date': first_date,
            'last_date': last_date,
            'failed_count': len(failed_practices)
        })
        
    except Exception as e:
        print(f"Error adding practice times: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'message': 'An unexpected error occurred while adding practice times'
        }), 500

@api_bp.route('/api/remove-practice-times', methods=['POST'])
@login_required
def remove_practice_times():
    """Remove practice times"""
    return remove_practice_times_data()

@api_bp.route('/api/team-schedule-data')
@login_required
def get_team_schedule_data():
    """Get team schedule data"""
    return get_team_schedule_data_data()

@api_bp.route('/api/availability', methods=['POST'])
@login_required
def update_availability():
    """Update player availability for matches"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Accept either player_name (legacy) or tenniscores_player_id (preferred)
        player_name = data.get('player_name')
        tenniscores_player_id = data.get('tenniscores_player_id')
        match_date = data.get('match_date')
        availability_status = data.get('availability_status')
        series = data.get('series')
        notes = data.get('notes', '')  # Optional notes field
        
        # Validate required fields - prefer player ID over name
        if not all([match_date, availability_status]):
            return jsonify({'error': 'Missing required fields: match_date, availability_status'}), 400
            
        if not tenniscores_player_id and not player_name:
            return jsonify({'error': 'Either tenniscores_player_id or player_name is required'}), 400
        
        # Validate availability status
        if availability_status not in [1, 2, 3]:  # 1=available, 2=unavailable, 3=not_sure
            return jsonify({'error': 'Invalid availability_status. Must be 1, 2, or 3'}), 400
        
        # Convert date to proper UTC midnight format
        # Parse the date string (format: YYYY-MM-DD)
        try:
            date_obj = datetime.strptime(match_date, '%Y-%m-%d')
            # Create UTC midnight timestamp
            utc_midnight = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            utc_timezone = pytz.UTC
            utc_date = utc_timezone.localize(utc_midnight)
            formatted_date = utc_date.strftime('%Y-%m-%d %H:%M:%S%z')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Expected YYYY-MM-DD'}), 400
        
        # Get player info and series_id using tenniscores_player_id or fallback to player associations
        user_email = session['user']['email']
        
        # Use SQLAlchemy to get player info
        db_session = SessionLocal()
        try:
            player = None
            
            # If tenniscores_player_id is provided, use it directly
            if tenniscores_player_id:
                player = db_session.query(Player).filter(
                    Player.tenniscores_player_id == tenniscores_player_id,
                    Player.is_active == True
                ).first()
                
                if not player:
                    return jsonify({'error': f'Player with ID {tenniscores_player_id} not found or inactive'}), 404
                    
                # Also get the full name for legacy compatibility
                player_name = f"{player.first_name} {player.last_name}"
                
            else:
                # Fallback: use player associations (legacy approach)
                user_record = db_session.query(User).filter(User.email == user_email).first()
                
                if not user_record:
                    return jsonify({'error': 'User not found'}), 404
                
                # Get primary player association
                primary_association = db_session.query(UserPlayerAssociation).filter(
                    UserPlayerAssociation.user_id == user_record.id,
                    UserPlayerAssociation.is_primary == True
                ).first()
                
                if not primary_association:
                    return jsonify({'error': 'No player association found. Please update your settings to link your player profile.'}), 400
                
                # Check if the player association has a valid player record
                player = primary_association.get_player(db_session)
                if not player:
                    return jsonify({'error': 'Player record not found. Your player association may be broken. Please update your settings to re-link your player profile.'}), 400
                
                tenniscores_player_id = player.tenniscores_player_id
            
            # Get series_id from the player
            series_id = player.series_id
            
            if not series_id:
                return jsonify({'error': 'Player series not found'}), 400
                
        finally:
            db_session.close()
        
        # Get the internal player.id for the database FK relationship
        player_db_id = player.id
        
        print(f"Updating availability: {player_name} (tenniscores_id: {tenniscores_player_id}, db_id: {player_db_id}) for {match_date} status {availability_status} series_id {series_id}")
        
        # Check if record exists using player_id (internal database ID)
        check_query = """
            SELECT id FROM player_availability 
            WHERE player_id = %s AND match_date = %s AND series_id = %s
        """
        existing_record = execute_query_one(check_query, (player_db_id, formatted_date, series_id))
        
        if existing_record:
            # Update existing record
            update_query = """
                UPDATE player_availability 
                SET availability_status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE player_id = %s AND match_date = %s AND series_id = %s
            """
            result = execute_update(update_query, (availability_status, notes, player_db_id, formatted_date, series_id))
            print(f"Updated existing availability record: {result}")
        else:
            # Insert new record using existing schema (player_id + player_name)
            insert_query = """
                INSERT INTO player_availability (player_id, player_name, match_date, availability_status, series_id, notes, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            result = execute_update(insert_query, (player_db_id, player_name, formatted_date, availability_status, series_id, notes))
            print(f"Created new availability record: {result}")
        
        # Log the activity using comprehensive logging
        status_descriptions = {1: 'available', 2: 'unavailable', 3: 'not sure'}
        status_text = status_descriptions.get(availability_status, f'status {availability_status}')
        
        log_user_action(
            action_type='availability_update',
            action_description=f"Updated availability for {match_date} to {status_text}",
            user_email=user_email,
            user_id=session['user'].get('id'),
            player_id=player_db_id,
            team_id=None,  # We could look up team_id from player if needed
            related_id=str(series_id),
            related_type='series',
            legacy_action='availability_update',
            legacy_details=f'Set availability for {match_date} to status {availability_status} (Player: {player_name}, ID: {tenniscores_player_id})',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            extra_data={
                'match_date': match_date,
                'availability_status': availability_status,
                'status_text': status_text,
                'player_name': player_name,
                'tenniscores_player_id': tenniscores_player_id,
                'series_id': series_id,
                'notes': notes,
                'was_new_record': not existing_record
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Availability updated successfully',
            'player_name': player_name,
            'tenniscores_player_id': tenniscores_player_id,
            'match_date': match_date,
            'availability_status': availability_status
        })
        
    except Exception as e:
        print(f"Error updating availability: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update availability: {str(e)}'}), 500

@api_bp.route('/api/get-user-settings')
@login_required
def get_user_settings():
    """Get user settings for the settings page"""
    try:
        user_email = session['user']['email']
        
        # Get basic user data (no more foreign keys)
        user_data = execute_query_one('''
            SELECT u.first_name, u.last_name, u.email, u.club_automation_password, u.is_admin
            FROM users u
            WHERE u.email = %s
        ''', (user_email,))
        
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Get player association data using SQLAlchemy
        db_session = SessionLocal()
        try:
            user_record = db_session.query(User).filter(User.email == user_email).first()
            
            if user_record:
                # Get primary player association
                primary_association = db_session.query(UserPlayerAssociation).filter(
                    UserPlayerAssociation.user_id == user_record.id,
                    UserPlayerAssociation.is_primary == True
                ).first()
                
                if primary_association:
                    player = primary_association.get_player(db_session)
                    if player:
                        club_name = player.club.name
                        series_name = player.series.name
                        league_id = player.league.league_id
                        league_name = player.league.league_name
                        tenniscores_player_id = player.tenniscores_player_id
                    else:
                        club_name = series_name = league_id = league_name = tenniscores_player_id = ''
                else:
                    # No player association found
                    club_name = series_name = league_id = league_name = tenniscores_player_id = ''
            else:
                club_name = series_name = league_id = league_name = tenniscores_player_id = ''
                
        finally:
            db_session.close()
            
        response_data = {
            'first_name': user_data['first_name'] or '',
            'last_name': user_data['last_name'] or '',
            'email': user_data['email'] or '',
            'club_automation_password': user_data['club_automation_password'] or '',
            'club': club_name,
            'series': series_name,
            'league_id': league_id,
            'league_name': league_name,
            'tenniscores_player_id': tenniscores_player_id
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error getting user settings: {str(e)}")
        return jsonify({'error': 'Failed to get user settings'}), 500

def convert_series_to_mapping_id(series_name, club_name, league_id=None):
    """
    DEPRECATED: This function was used for JSON file lookups.
    Database lookups now use series names directly.
    Keeping for backward compatibility but marked for removal.
    """
    # This function is no longer needed for database-only lookups
    # but keeping for any legacy code that might still reference it
    logger.warning("convert_series_to_mapping_id is deprecated - use database lookups instead")
    return f"{club_name} {series_name}"  # Simple fallback

@api_bp.route('/api/update-settings', methods=['POST'])
@login_required
def update_settings():
    """Update user settings"""
    try:
        import logging
        
        logger = logging.getLogger(__name__)
        data = request.get_json()
        user_email = session['user']['email']
        
        # Validate required fields
        if not data.get('firstName') or not data.get('lastName') or not data.get('email'):
            return jsonify({'error': 'First name, last name, and email are required'}), 400
        
        # Enhanced player ID lookup logic:
        # 1. Always retry if user requests it OR they don't have a player ID
        # 2. Always retry if league/club/series has changed from current session
        # 3. Use database-only lookup strategy
        force_player_id_retry = data.get('forcePlayerIdRetry', False)
        current_player_id = session['user'].get('tenniscores_player_id')
        
        # Check if league/club/series has changed from current session
        current_league_id = session['user'].get('league_id')
        current_club = session['user'].get('club')
        current_series = session['user'].get('series')
        
        new_league_id = data.get('league_id')
        new_club = data.get('club')
        new_series = data.get('series')
        
        settings_changed = (
            new_league_id != current_league_id or
            new_club != current_club or
            new_series != current_series
        )
        
        should_retry_player_id = (
            force_player_id_retry or 
            not current_player_id or
            settings_changed
        )
        
        found_player_id = None
        player_association_created = False
        
        if should_retry_player_id and data.get('firstName') and data.get('lastName') and data.get('club') and data.get('series'):
            try:
                reason = []
                if force_player_id_retry:
                    reason.append("user requested retry")
                if not current_player_id:
                    reason.append("no existing player ID")
                if settings_changed:
                    reason.append(f"settings changed (league: {current_league_id} -> {new_league_id}, club: {current_club} -> {new_club}, series: {current_series} -> {new_series})")
                
                logger.info(f"Settings update: Retrying player ID lookup because: {', '.join(reason)}")
                
                # Use database-only lookup - NO MORE JSON FILES
                lookup_result = find_player_by_database_lookup(
                    first_name=data['firstName'],
                    last_name=data['lastName'],
                    club_name=data['club'],
                    series_name=data['series'],
                    league_id=data.get('league_id')
                )
                
                # Extract player ID from the enhanced result
                found_player_id = None
                if lookup_result and lookup_result.get('player'):
                    found_player_id = lookup_result['player']['tenniscores_player_id']
                    logger.info(f"Settings update: Match type: {lookup_result['match_type']} - {lookup_result['message']}")
                
                if found_player_id:
                    logger.info(f"Settings update: Found player ID via database lookup: {found_player_id}")
                    
                    # Create user-player association if player found
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
                                # Unset any existing primary associations for this user
                                db_session.query(UserPlayerAssociation).filter(
                                    UserPlayerAssociation.user_id == user_record.id,
                                    UserPlayerAssociation.is_primary == True
                                ).update({'is_primary': False})
                                
                                # Create new association as primary
                                association = UserPlayerAssociation(
                                    user_id=user_record.id,
                                    tenniscores_player_id=player_record.tenniscores_player_id,
                                    is_primary=True
                                )
                                db_session.add(association)
                                db_session.commit()
                                player_association_created = True
                                logger.info(f"Settings update: Created new primary association between user {user_email} and player {player_record.full_name}")
                            else:
                                # Association exists - make sure it's primary if settings changed
                                if settings_changed and not existing.is_primary:
                                    # Unset other primary associations
                                    db_session.query(UserPlayerAssociation).filter(
                                        UserPlayerAssociation.user_id == user_record.id,
                                        UserPlayerAssociation.is_primary == True
                                    ).update({'is_primary': False})
                                    
                                    # Set this association as primary
                                    existing.is_primary = True
                                    db_session.commit()
                                    logger.info(f"Settings update: Updated existing association to primary for user {user_email} and player {player_record.full_name}")
                                else:
                                    logger.info(f"Settings update: Association already exists between user {user_email} and player {player_record.full_name}")
                        else:
                            logger.warning(f"Settings update: Could not find user or player record for association")
                            
                    except Exception as assoc_error:
                        db_session.rollback()
                        logger.error(f"Settings update: Error creating user-player association: {str(assoc_error)}")
                    finally:
                        db_session.close()
                else:
                    logger.info(f"Settings update: No player ID found via database lookup")
                    
            except Exception as lookup_error:
                logger.warning(f"Settings update: Player ID lookup error: {str(lookup_error)}")
                found_player_id = None
        
        # Update user data (only basic user fields - no foreign keys)
        success = execute_update('''
            UPDATE users 
            SET first_name = %s, last_name = %s, email = %s, club_automation_password = %s
            WHERE email = %s
        ''', (
            data['firstName'], 
            data['lastName'], 
            data['email'],
            data.get('clubAutomationPassword', ''),
            user_email
        ))
        
        if not success:
            return jsonify({'error': 'Failed to update user data'}), 500
        
        logger.info(f"Settings update: Updated user basic data")
        
        # Get updated user data with player associations for session
        db_session = SessionLocal()
        try:
            user_record = db_session.query(User).filter(User.email == data['email']).first()
            
            if not user_record:
                return jsonify({'error': 'Failed to retrieve updated user data'}), 500
            
            # Get associated players
            associations = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_record.id
            ).all()
            
            # Find primary player for session data
            primary_player = None
            current_player_id = None
            
            for assoc in associations:
                if assoc.is_primary:
                    player = assoc.get_player(db_session)
                    if player and player.club and player.series and player.league:
                        primary_player = {
                            'club': player.club.name,
                            'series': player.series.name,
                            'league_id': player.league.league_id,
                            'league_name': player.league.league_name,
                            'tenniscores_player_id': player.tenniscores_player_id
                        }
                        current_player_id = player.tenniscores_player_id
                        break
            
            # Update session with new user data
            session['user'] = {
                'id': user_record.id,
                'email': user_record.email,
                'first_name': user_record.first_name,
                'last_name': user_record.last_name,
                'club': primary_player['club'] if primary_player else data.get('club', ''),
                'series': primary_player['series'] if primary_player else data.get('series', ''),
                'league_id': primary_player['league_id'] if primary_player else data.get('league_id'),
                'league_name': primary_player['league_name'] if primary_player else '',
                'club_automation_password': data.get('clubAutomationPassword', ''),
                'is_admin': user_record.is_admin,
                'tenniscores_player_id': current_player_id,
                'settings': '{}'  # Default empty settings for consistency with auth
            }
            
            # Explicitly mark session as modified to ensure persistence
            session.modified = True
            
            logger.info(f"Settings update: Session updated with player ID: {current_player_id}")
            
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully',
                'user': session['user'],
                'player_id_updated': found_player_id is not None,
                'player_id': current_player_id,
                'player_association_created': player_association_created,
                'player_id_retry_attempted': should_retry_player_id,
                'player_id_retry_successful': found_player_id is not None,
                'force_retry_requested': force_player_id_retry
            })
            
        finally:
            db_session.close()
        
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        return jsonify({'error': 'Failed to update settings'}), 500

@api_bp.route('/api/retry-player-id', methods=['POST'])
@login_required  
def retry_player_id_lookup():
    """Manual retry of player ID lookup for current user"""
    try:
        from utils.database_player_lookup import find_player_by_database_lookup
        import logging
        
        logger = logging.getLogger(__name__)
        user_email = session['user']['email']
        
        # Get current user data from session (since we can't rely on user table foreign keys anymore)
        first_name = session['user'].get('first_name')
        last_name = session['user'].get('last_name')
        club_name = session['user'].get('club')
        series_name = session['user'].get('series')
        league_id = session['user'].get('league_id')
        
        # If session doesn't have player data, this means user never had a player association
        # We can't do a retry without knowing what league/club/series to search in
        if not all([first_name, last_name]):
            missing = []
            if not first_name: missing.append('first name')
            if not last_name: missing.append('last name')
            return jsonify({
                'success': False, 
                'message': f'Missing required user data: {", ".join(missing)}'
            }), 400
        
        if not all([club_name, series_name, league_id]):
            return jsonify({
                'success': False,
                'message': 'Cannot retry player lookup - no club/series/league information available. Please update your settings with your club, series, and league information first.'
            }), 400
        
        try:
            logger.info(f"Manual retry: Looking up player via database for {first_name} {last_name}")
            
            # Use database-only lookup - NO MORE JSON FILES
            lookup_result = find_player_by_database_lookup(
                first_name=first_name,
                last_name=last_name,
                club_name=club_name,
                series_name=series_name,
                league_id=league_id
            )
            
            # Extract player ID from the enhanced result
            found_player_id = None
            if lookup_result and lookup_result.get('player'):
                found_player_id = lookup_result['player']['tenniscores_player_id']
                logger.info(f"Manual retry: Match type: {lookup_result['match_type']} - {lookup_result['message']}")
            
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
                                tenniscores_player_id=player_record.tenniscores_player_id,
                                is_primary=True  # First association becomes primary
                            )
                            db_session.add(association)
                            db_session.commit()
                            
                            # Update session with player data
                            session['user']['tenniscores_player_id'] = found_player_id
                            if player_record.club and player_record.series and player_record.league:
                                session['user']['club'] = player_record.club.name
                                session['user']['series'] = player_record.series.name
                                session['user']['league_id'] = player_record.league.league_id
                                session['user']['league_name'] = player_record.league.league_name
                            session.modified = True
                            
                            logger.info(f"Manual retry: Created association and updated session for player ID {found_player_id}")
                            
                            return jsonify({
                                'success': True,
                                'player_id': found_player_id,
                                'message': f'Player ID found and associated: {found_player_id}'
                            })
                        else:
                            logger.info(f"Manual retry: Association already exists for player ID {found_player_id}")
                            
                            # Update session anyway in case it was missing
                            session['user']['tenniscores_player_id'] = found_player_id
                            session.modified = True
                            
                            return jsonify({
                                'success': True,
                                'player_id': found_player_id,
                                'message': f'Player ID already associated: {found_player_id}'
                            })
                    else:
                        logger.error(f"Manual retry: Could not find user or player record for association")
                        return jsonify({
                            'success': False,
                            'message': 'Found player ID but could not create association'
                        }), 500
                        
                except Exception as assoc_error:
                    db_session.rollback()
                    logger.error(f"Manual retry: Association error: {str(assoc_error)}")
                    return jsonify({
                        'success': False,
                        'message': 'Found player ID but failed to create association'
                    }), 500
                finally:
                    db_session.close()
            else:
                logger.info(f"Manual retry: No player match found for {first_name} {last_name}")
                return jsonify({
                    'success': False,
                    'message': f'No matching player found for {first_name} {last_name} ({club_name}, {series_name})'
                })
                
        except Exception as lookup_error:
            logger.error(f"Manual retry: Database lookup error: {str(lookup_error)}")
            return jsonify({
                'success': False,
                'message': 'Player lookup failed due to database error'
            }), 500
            
    except Exception as e:
        logger.error(f"Manual retry endpoint error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Retry failed due to server error'
        }), 500

@api_bp.route('/api/get-leagues')
def get_leagues():
    """Get all available leagues"""
    try:
        query = """
            SELECT league_id, league_name, league_url
            FROM leagues
            ORDER BY league_name
        """
        
        leagues_data = execute_query(query)
        
        return jsonify({
            'leagues': leagues_data
        })
        
    except Exception as e:
        print(f"Error getting leagues: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/get-clubs-by-league')
def get_clubs_by_league():
    """Get clubs filtered by league"""
    try:
        league_id = request.args.get('league_id')
        
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
        
        clubs_list = [club['name'] for club in clubs_data]
        
        return jsonify({
            'clubs': clubs_list
        })
        
    except Exception as e:
        print(f"Error getting clubs by league: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/get-series-by-league')
def get_series_by_league():
    """Get series filtered by league"""
    try:
        league_id = request.args.get('league_id')
        
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
        def extract_series_number(series_name):
            import re
            numbers = re.findall(r'\d+', series_name)
            if numbers:
                return int(numbers[-1])
            else:
                return 999
        
        series_data.sort(key=lambda x: extract_series_number(x['series_name']))
        series_names = [item['series_name'] for item in series_data]
        
        return jsonify({
            'series': series_names
        })
        
    except Exception as e:
        print(f"Error getting series by league: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/teams')
@login_required
def get_teams():
    """Get teams filtered by user's league"""
    try:
        # Get user's league for filtering
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
            
        user_league_id = user.get('league_id', '')
        print(f"[DEBUG] /api/teams: User league_id: '{user_league_id}'")
        
        # Load stats data to get team names
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        stats_path = os.path.join(project_root, 'data', 'leagues', 'all', 'series_stats.json')
        
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
        
        # Filter stats data by user's league
        def is_user_league_team(team_data):
            team_league_id = team_data.get('league_id')
            if user_league_id.startswith('APTA'):
                # For APTA users, only include teams without league_id field (APTA teams)
                return team_league_id is None
            else:
                # For other leagues, match the league_id
                return team_league_id == user_league_id
        
        league_filtered_stats = [team for team in all_stats if is_user_league_team(team)]
        print(f"[DEBUG] Filtered from {len(all_stats)} total teams to {len(league_filtered_stats)} teams in user's league")
        
        # Extract team names and filter out BYE teams
        teams = sorted({s['team'] for s in league_filtered_stats if 'BYE' not in s['team'].upper()})
        
        return jsonify({
            'teams': teams
        })
        
    except Exception as e:
        print(f"Error getting teams: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/club-players')
@login_required
def get_club_players():
    """Get all players at the user's club with optional filtering"""
    try:
        # Get filter parameters
        series_filter = request.args.get('series', '').strip()
        first_name_filter = request.args.get('first_name', '').strip()
        last_name_filter = request.args.get('last_name', '').strip()
        pti_min = request.args.get('pti_min', type=float)
        pti_max = request.args.get('pti_max', type=float)
        club_only = request.args.get('club_only', 'true').lower() == 'true'  # Default to true

        # Use the mobile service function to get the data
        result = get_club_players_data(
            session['user'], 
            series_filter, 
            first_name_filter, 
            last_name_filter, 
            pti_min, 
            pti_max,
            club_only
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in club-players API: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/debug-club-data')
@login_required
def debug_club_data():
    """Debug endpoint to show user club and available clubs in players.json"""
    try:
        user_club = session['user'].get('club')
        
        # Use the mobile service function to get debug data
        result = get_club_players_data(session['user'])
        
        return jsonify({
            'user_club_in_session': user_club,
            'session_user': session['user'],
            'debug_data': result.get('debug', {})
        })
        
    except Exception as e:
        print(f"Debug endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Route moved to mobile_routes.py to avoid conflicts
# The mobile blueprint now handles /api/player-history-chart with database queries 

# ==========================================
# PTI ANALYSIS DATA ENDPOINTS
# ==========================================

@api_bp.route('/api/pti-analysis/players')
@login_required
def get_pti_analysis_players():
    """Get all players with PTI data for analysis"""
    try:
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
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/pti-analysis/player-history')
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
            player_name = row['name']
            
            if current_player != player_name:
                if current_player is not None:
                    players_history.append({
                        'name': current_player,
                        'matches': current_matches
                    })
                current_player = player_name
                current_matches = []
            
            # Format date as string for JSON serialization
            date_str = row['date'].strftime('%m/%d/%Y') if row['date'] else None
            
            current_matches.append({
                'series': row['series'],
                'date': date_str,
                'end_pti': float(row['end_pti']) if row['end_pti'] else None
            })
        
        # Add the last player
        if current_player is not None:
            players_history.append({
                'name': current_player,
                'matches': current_matches
            })
        
        return jsonify(players_history)
        
    except Exception as e:
        print(f"Error getting PTI analysis player history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/pti-analysis/match-history')
@login_required
def get_pti_analysis_match_history():
    """Get match history data for PTI analysis"""
    try:
        query = """
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
            ORDER BY ms.match_date DESC
        """
        
        match_data = execute_query(query)
        
        return jsonify(match_data)
        
    except Exception as e:
        print(f"Error getting PTI analysis match history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/player-season-tracking', methods=['GET', 'POST'])
@login_required
def handle_player_season_tracking():
    """Handle getting and updating player season tracking data"""
    try:
        user = session['user']
        current_year = datetime.now().year
        
        # Determine current tennis season year (Aug-July seasons)
        current_month = datetime.now().month
        if current_month >= 8:  # Aug-Dec: current season
            season_year = current_year
        else:  # Jan-Jul: previous season
            season_year = current_year - 1
        
        # Get user's league for filtering
        user_league_id = user.get('league_id', '')
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != '':
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", 
                    [user_league_id]
                )
                if league_record:
                    league_id_int = league_record['id']
            except Exception as e:
                pass
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
        
        if request.method == 'GET':
            # Return current season tracking data for all players in user's team/league
            
            # Get user's team ID to fetch team members
            from app.routes.mobile_routes import get_user_team_id
            team_id = get_user_team_id(user)
            
            if not team_id:
                return jsonify({'error': 'No team found for user'}), 400
            
            # Get team members
            team_members_query = '''
                SELECT p.tenniscores_player_id, p.first_name, p.last_name
                FROM players p
                WHERE p.team_id = %s AND p.is_active = TRUE
            '''
            team_members = execute_query(team_members_query, [team_id])
            
            # Get existing tracking data for these players
            if team_members and league_id_int:
                player_ids = [member['tenniscores_player_id'] for member in team_members]
                placeholders = ','.join(['%s'] * len(player_ids))
                
                tracking_query = f'''
                    SELECT player_id, forced_byes, not_available, injury
                    FROM player_season_tracking
                    WHERE player_id IN ({placeholders})
                    AND league_id = %s
                    AND season_year = %s
                '''
                tracking_data = execute_query(tracking_query, player_ids + [league_id_int, season_year])
                
                # Build response with player names and tracking data
                tracking_dict = {row['player_id']: row for row in tracking_data}
                
                result = []
                for member in team_members:
                    player_id = member['tenniscores_player_id']
                    tracking = tracking_dict.get(player_id, {
                        'forced_byes': 0, 'not_available': 0, 'injury': 0
                    })
                    
                    result.append({
                        'player_id': player_id,
                        'name': f"{member['first_name']} {member['last_name']}",
                        'forced_byes': tracking['forced_byes'],
                        'not_available': tracking['not_available'],
                        'injury': tracking['injury']
                    })
                
                return jsonify({
                    'season_year': season_year,
                    'players': result
                })
            else:
                return jsonify({
                    'season_year': season_year,
                    'players': []
                })
        
        elif request.method == 'POST':
            # Update tracking data for a specific player
            data = request.get_json()
            
            if not data or not all(key in data for key in ['player_id', 'type', 'value']):
                return jsonify({'error': 'Missing required fields: player_id, type, value'}), 400
            
            player_id = data['player_id']
            tracking_type = data['type']  # 'forced_byes', 'not_available', or 'injury'
            value = int(data['value'])
            
            # Validate tracking type
            if tracking_type not in ['forced_byes', 'not_available', 'injury']:
                return jsonify({'error': 'Invalid tracking type'}), 400
            
            # Validate value
            if value < 0 or value > 50:  # Reasonable limits
                return jsonify({'error': 'Value must be between 0 and 50'}), 400
            
            if not league_id_int:
                return jsonify({'error': 'Could not determine user league'}), 400
            
            # Use UPSERT to insert or update the tracking record
            upsert_query = f'''
                INSERT INTO player_season_tracking (player_id, league_id, season_year, {tracking_type})
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (player_id, league_id, season_year)
                DO UPDATE SET 
                    {tracking_type} = EXCLUDED.{tracking_type},
                    updated_at = CURRENT_TIMESTAMP
                RETURNING forced_byes, not_available, injury
            '''
            
            result = execute_query_one(upsert_query, [player_id, league_id_int, season_year, value])
            
            if result:
                # Log the activity
                log_user_activity(
                    user['email'], 
                    'update_season_tracking', 
                    action=f"Updated {tracking_type} to {value} for player {player_id}"
                )
                
                return jsonify({
                    'success': True,
                    'player_id': player_id,
                    'season_year': season_year,
                    'forced_byes': result['forced_byes'],
                    'not_available': result['not_available'],
                    'injury': result['injury']
                })
            else:
                return jsonify({'error': 'Failed to update tracking data'}), 500
        
    except Exception as e:
        print(f"Error in player season tracking API: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500 