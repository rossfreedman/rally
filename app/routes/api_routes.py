"""
API Routes Blueprint

This module contains all API routes that were moved from the main server.py file.
These routes handle API endpoints for data retrieval, research, analytics, and other backend operations.
"""

from flask import Blueprint, request, jsonify, session, g
from functools import wraps
from utils.logging import log_user_activity
from database_utils import execute_query, execute_query_one, execute_update
from app.services.api_service import *
from app.services.mobile_service import get_club_players_data
from datetime import datetime
import pytz
import json
import os

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

@api_bp.route('/api/find-training-video', methods=['POST'])
def find_training_video():
    """Find training video"""
    return find_training_video_data()

@api_bp.route('/api/chat', methods=['POST'])
@login_required
def handle_chat():
    """Handle chat requests for Coach Rally on mobile improve page"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        message = data.get('message', '').strip()
        thread_id = data.get('thread_id')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        print(f"[CHAT] User: {session.get('user', {}).get('email', 'unknown')} | Message: {message[:50]}...")
        
        # Generate thread ID if not provided
        if not thread_id:
            import uuid
            thread_id = str(uuid.uuid4())
        
        # Load training guide for context-aware responses
        response_text = generate_chat_response(message)
        
        return jsonify({
            'response': response_text,
            'thread_id': thread_id
        })
        
    except Exception as e:
        print(f"Error in chat handler: {str(e)}")
        return jsonify({'error': 'Sorry, there was an error processing your request. Please try again.'}), 500

def generate_chat_response(message):
    """Generate a helpful response to user's paddle tennis question"""
    try:
        import os
        import json
        import random
        
        message_lower = message.lower()
        
        # Load training guide for detailed responses
        try:
            guide_path = os.path.join('data', 'improve_data', 'complete_platform_tennis_training_guide.json')
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
        day = request.form.get('day')
        time = request.form.get('time')
        
        # Validate required fields
        if not all([first_date, day, time]):
            return jsonify({
                'success': False, 
                'message': 'All fields are required'
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
        
        # Parse the first date
        try:
            first_date_obj = datetime.strptime(first_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Invalid date format'
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
        
        # Load the current schedule
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        schedule_file = os.path.join(project_root, "data", "schedules.json")
        try:
            with open(schedule_file, 'r') as f:
                schedule = json.load(f)
        except FileNotFoundError:
            return jsonify({
                'success': False, 
                'message': 'Schedule file not found'
            }), 500
        except json.JSONDecodeError:
            return jsonify({
                'success': False, 
                'message': 'Invalid schedule file format'
            }), 500
        
        # Determine end date - set to end of current season (April 18, 2025)
        # You may want to make this configurable
        end_date = datetime(2025, 4, 18)
        
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
        
        # Add practice entries until end of season
        while current_date <= end_date:
            # If current date is the target weekday, add practice
            if current_date.weekday() == target_weekday:
                # Create practice entry - using "Practice" field to match original script
                practice_entry = {
                    "date": current_date.strftime("%m/%d/%Y"),
                    "time": formatted_time,
                    "Practice": user_club,  # Use the user's club as the practice location
                    "Series": user_series   # Add the user's series from session
                }
                # Insert at the beginning of the schedule
                schedule.insert(0, practice_entry)
                practices_added += 1
                
                # Add to our tracking list for the response
                added_practices.append({
                    "date": current_date.strftime("%m/%d/%Y"),
                    "time": formatted_time,
                    "day": day
                })
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Sort the schedule by date and time
        def sort_key(x):
            try:
                date_obj = datetime.strptime(x['date'], "%m/%d/%Y")
                time_obj = datetime.strptime(x['time'], "%I:%M %p")
                return (date_obj, time_obj)
            except ValueError:
                # If parsing fails, put it at the end
                return (datetime.max, datetime.max)
        
        schedule.sort(key=sort_key)
        
        # Save updated schedule
        try:
            with open(schedule_file, 'w') as f:
                json.dump(schedule, f, indent=4)
        except Exception as e:
            return jsonify({
                'success': False, 
                'message': f'Failed to save schedule: {str(e)}'
            }), 500
        
        # Log the activity
        from utils.logging import log_user_activity
        log_user_activity(
            user['email'], 
            'practice_times_added',
            details=f'Added {practices_added} practice times for {user_series} {day}s at {formatted_time} starting {first_date}'
        )
        
        return jsonify({
            'success': True, 
            'message': f'Successfully added {practices_added} practice times to the schedule!',
            'practices_added': added_practices,
            'count': practices_added,
            'series': user_series,
            'day': day,
            'time': formatted_time
        })
        
    except Exception as e:
        print(f"Error adding practice times: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'An unexpected error occurred'
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
        
        player_name = data.get('player_name')
        match_date = data.get('match_date')
        availability_status = data.get('availability_status')
        series = data.get('series')
        
        # Validate required fields
        if not all([player_name, match_date, availability_status]):
            return jsonify({'error': 'Missing required fields: player_name, match_date, availability_status'}), 400
        
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
        
        # Get user's series_id from session
        user_email = session['user']['email']
        user_query = """
            SELECT u.series_id 
            FROM users u 
            WHERE u.email = %s
        """
        user_result = execute_query_one(user_query, (user_email,))
        
        if not user_result or not user_result.get('series_id'):
            return jsonify({'error': 'User series not found'}), 400
        
        series_id = user_result['series_id']
        
        print(f"Updating availability: {player_name} for {match_date} status {availability_status} series_id {series_id}")
        
        # Check if record exists
        check_query = """
            SELECT id FROM player_availability 
            WHERE player_name = %s AND match_date = %s AND series_id = %s
        """
        existing_record = execute_query_one(check_query, (player_name, formatted_date, series_id))
        
        if existing_record:
            # Update existing record
            update_query = """
                UPDATE player_availability 
                SET availability_status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE player_name = %s AND match_date = %s AND series_id = %s
            """
            result = execute_update(update_query, (availability_status, player_name, formatted_date, series_id))
            print(f"Updated existing availability record: {result}")
        else:
            # Insert new record
            insert_query = """
                INSERT INTO player_availability (player_name, match_date, availability_status, series_id, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            result = execute_update(insert_query, (player_name, formatted_date, availability_status, series_id))
            print(f"Created new availability record: {result}")
        
        # Log the activity
        log_user_activity(
            player_name,
            'availability_update',
            page='mobile_availability',
            details=f'Set availability for {match_date} to status {availability_status}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Availability updated successfully',
            'player_name': player_name,
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
        
        # Get user data with club and series names
        user_data = execute_query_one('''
            SELECT u.first_name, u.last_name, u.email, u.club_automation_password,
                   c.name as club, s.name as series, u.tenniscores_player_id
            FROM users u
            LEFT JOIN clubs c ON u.club_id = c.id
            LEFT JOIN series s ON u.series_id = s.id
            WHERE u.email = %s
        ''', (user_email,))
        
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
            
        response_data = {
            'first_name': user_data['first_name'] or '',
            'last_name': user_data['last_name'] or '',
            'email': user_data['email'] or '',
            'club_automation_password': user_data['club_automation_password'] or '',
            'club': user_data['club'] or '',
            'series': user_data['series'] or '',
            'tenniscores_player_id': user_data['tenniscores_player_id'] or ''
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error getting user settings: {str(e)}")
        return jsonify({'error': 'Failed to get user settings'}), 500

@api_bp.route('/api/update-settings', methods=['POST'])
@login_required
def update_settings():
    """Update user settings"""
    try:
        data = request.get_json()
        user_email = session['user']['email']
        
        # Validate required fields
        if not data.get('firstName') or not data.get('lastName') or not data.get('email'):
            return jsonify({'error': 'First name, last name, and email are required'}), 400
        
        # Get club_id and series_id from names
        club_id = None
        series_id = None
        
        if data.get('club'):
            club_result = execute_query_one('SELECT id FROM clubs WHERE name = %s', (data['club'],))
            if club_result:
                club_id = club_result['id']
        
        if data.get('series'):
            series_result = execute_query_one('SELECT id FROM series WHERE name = %s', (data['series'],))
            if series_result:
                series_id = series_result['id']
        
        # Update user data
        success = execute_update('''
            UPDATE users 
            SET first_name = %s, last_name = %s, email = %s, 
                club_id = %s, series_id = %s, club_automation_password = %s
            WHERE email = %s
        ''', (
            data['firstName'], 
            data['lastName'], 
            data['email'],
            club_id,
            series_id,
            data.get('clubAutomationPassword', ''),
            user_email
        ))
        
        if not success:
            return jsonify({'error': 'Failed to update user data'}), 500
        
        # Get updated user data to return and update session
        updated_user = execute_query_one('''
            SELECT u.first_name, u.last_name, u.email, u.club_automation_password,
                   c.name as club, s.name as series, u.is_admin, u.tenniscores_player_id
            FROM users u
            LEFT JOIN clubs c ON u.club_id = c.id
            LEFT JOIN series s ON u.series_id = s.id
            WHERE u.email = %s
        ''', (data['email'],))  # Use new email in case it was changed
        
        if updated_user:
            # Update session with new user data
            session['user'] = {
                'email': updated_user['email'],
                'first_name': updated_user['first_name'],
                'last_name': updated_user['last_name'],
                'club': updated_user['club'],
                'series': updated_user['series'],
                'club_automation_password': updated_user['club_automation_password'],
                'is_admin': updated_user['is_admin'],
                'tenniscores_player_id': updated_user['tenniscores_player_id']
            }
            
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully',
                'user': session['user']
            })
        else:
            return jsonify({'error': 'Failed to retrieve updated user data'}), 500
        
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        return jsonify({'error': 'Failed to update settings'}), 500

@api_bp.route('/api/get-series')
def get_series():
    """Get all available series from database and current user's series"""
    try:
        from flask import session
        
        query = """
            SELECT DISTINCT s.name as series_name
            FROM series s
            ORDER BY s.name
        """
        
        series_data = execute_query(query)
        
        # Process the series data to extract numbers and sort properly
        def extract_series_number(series_name):
            import re
            # Look for numbers in the series name
            numbers = re.findall(r'\d+', series_name)
            if numbers:
                return int(numbers[-1])  # Return the last number as an integer
            else:
                return 999  # Put non-numeric series at the end
        
        # Sort by extracted number
        series_data.sort(key=lambda x: extract_series_number(x['series_name']))
        
        # Extract just the series names
        series_names = [item['series_name'] for item in series_data]
        
        # Get current user's series from session
        current_user_series = session.get('user', {}).get('series', '')
        
        return jsonify({
            'series': current_user_series,  # Current user's series
            'all_series': series_names      # All available series
        })
        
    except Exception as e:
        print(f"Error getting series: {str(e)}")
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

        # Use the mobile service function to get the data
        result = get_club_players_data(
            session['user'], 
            series_filter, 
            first_name_filter, 
            last_name_filter, 
            pti_min, 
            pti_max
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

@api_bp.route('/api/player-history')
@login_required
def get_player_history():
    """Get player PTI history for charts"""
    try:
        user = session['user']
        print(f"[DEBUG] API called for user: {user}")
        
        # Get current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        
        # Load player history data
        player_history_path = os.path.join(project_root, 'data', 'player_history.json')
        print(f"[DEBUG] Loading data from: {player_history_path}")
        
        with open(player_history_path, 'r') as f:
            all_players = json.load(f)
        
        print(f"[DEBUG] Loaded {len(all_players)} players")
        
        # Find the current user's player data
        user_player = None
        
        # First try to match by tenniscores_player_id if available
        if user.get('tenniscores_player_id'):
            print(f"[DEBUG] Looking for player ID: {user.get('tenniscores_player_id')}")
            for player in all_players:
                if player.get('player_id') == user['tenniscores_player_id']:
                    user_player = player
                    print(f"[DEBUG] Found player by ID: {player.get('name')}")
                    break
        
        # If not found by ID, try to match by name
        if not user_player:
            user_full_name = f"{user['first_name']} {user['last_name']}"
            print(f"[DEBUG] Looking for player name: {user_full_name}")
            for player in all_players:
                if player.get('name') == user_full_name:
                    user_player = player
                    print(f"[DEBUG] Found player by name: {player.get('name')}")
                    break
        
        if not user_player:
            print(f"[DEBUG] No player found for user: {user}")
            return jsonify({
                'success': False, 
                'message': 'No player found for this user',
                'data': []
            })
        
        if not user_player.get('matches'):
            print(f"[DEBUG] Player has no matches: {user_player.get('name')}")
            return jsonify({
                'success': False, 
                'message': 'No PTI history found for this player',
                'data': []
            })
        
        # Sort matches by date (most recent first for chart display)
        matches = user_player['matches']
        sorted_matches = sorted(matches, key=lambda x: x['date'], reverse=False)
        
        print(f"[DEBUG] Returning {len(sorted_matches)} matches for {user_player.get('name')}")
        
        # Return the match data for the chart
        response_data = {
            'success': True,
            'data': sorted_matches,
            'player_name': user_player.get('name'),
            'total_matches': len(sorted_matches)
        }
        print(f"[DEBUG] Response data keys: {list(response_data.keys())}")
        print(f"[DEBUG] Data type: {type(response_data['data'])}")
        print(f"[DEBUG] Data length: {len(response_data['data'])}")
        
        return jsonify(response_data)
        
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'message': 'Player history data not found',
            'data': []
        })
    except Exception as e:
        print(f"Error getting player history: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error loading player history: {str(e)}',
            'data': []
        }) 