"""
Download Routes Blueprint

This module contains routes for downloading various data formats including calendar files.
"""

import logging
import re
from datetime import datetime, date, time, timedelta
from functools import wraps

from flask import Blueprint, Response, session, request, jsonify
from icalendar import Calendar, Event
import pytz

from app.models.database_models import SessionLocal, Player, Team, Club, League, Schedule
from database_utils import execute_query, execute_query_one
from utils.auth import login_required

# Create download blueprint
download_bp = Blueprint("download", __name__)

# Set up logger
logger = logging.getLogger(__name__)


def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Debug session information
        logger.info(f"Login required check - Session keys: {list(session.keys())}")
        logger.info(f"Login required check - Session data: {dict(session)}")
        logger.info(f"Login required check - Request headers: {dict(request.headers)}")
        
        # Check if user exists in session
        if "user" not in session:
            logger.warning(f"Authentication failed: No user in session. Session keys: {list(session.keys())}")
            logger.warning(f"Authentication failed: Session data: {dict(session)}")
            logger.warning(f"Authentication failed: Request cookies: {dict(request.cookies)}")
            logger.warning(f"Authentication failed: Session cookie: {request.cookies.get('rally_session', 'Not found')}")
            
            # Mobile fallback: try to get user from mobile-specific headers or tokens
            if 'iPhone' in request.headers.get('User-Agent', '') or 'Mobile' in request.headers.get('User-Agent', ''):
                logger.warning("Mobile authentication fallback - checking for alternative auth methods")
                
                # Check if there's a mobile-specific authentication header
                mobile_auth = request.headers.get('X-Mobile-Auth', None)
                if mobile_auth:
                    logger.info(f"Found mobile auth header: {mobile_auth}")
                    # TODO: Implement mobile-specific authentication logic
                
                # Check if we can get user from referer or other mobile-specific data
                referer = request.headers.get('Referer', '')
                if referer and 'mobile' in referer.lower():
                    logger.info(f"Mobile referer detected: {referer}")
                    # TODO: Implement referer-based authentication for mobile
                
                # Check if this is a direct access to the calendar download
                if request.path == '/cal/season-download.ics':
                    logger.warning("Mobile direct access to calendar download detected - redirecting to mobile flow")
                    from flask import redirect, url_for
                    
                    # Redirect to mobile session setup instead of showing error
                    return redirect(url_for('download.mobile_session_setup'))
                
                # For other mobile routes, return a mobile-specific error message
                return jsonify({
                    "error": "Mobile authentication required",
                    "message": "Please follow the proper mobile flow to download your calendar.",
                    "mobile_specific": True,
                    "debug_info": {
                        "user_agent": request.headers.get('User-Agent', 'Unknown'),
                        "cookies_sent": len(request.cookies),
                        "referer": request.headers.get('Referer', 'No referer'),
                        "suggested_fix": "Go to mobile availability page first, then click Download button"
                    },
                    "instructions": [
                        "1. Go to the mobile availability page: /mobile/availability",
                        "2. Make sure you're logged in",
                        "3. Click the 'Download' button in the green banner",
                        "4. This will establish your mobile session properly"
                    ],
                    "correct_url": "/mobile/availability"
                }), 401
            
            return jsonify({"error": "Authentication required"}), 401
        
        user = session["user"]
        logger.info(f"Login required check - User from session: {user}")
        
        # Check if user has required fields
        if not user or not user.get("id") or not user.get("email"):
            logger.warning(f"Authentication failed: Invalid user data. User: {user}")
            return jsonify({"error": "Invalid user session"}), 401
            
        logger.info(f"Authentication successful for user: {user.get('email')}")
        return f(*args, **kwargs)
    return decorated_function


@download_bp.route("/calendar-download")
@login_required
def calendar_download_page():
    """
    Serve the calendar download explanation page.
    
    Returns:
        str: Rendered HTML template
    """
    try:
        from flask import render_template
        from app.services.session_service import get_session_data_for_user
        
        # Get session data for the user (required by mobile layout)
        user = session["user"]
        logger.info(f"Calendar download page - User session: {user.get('email') if user else 'None'}")
        logger.info(f"Calendar download page - Session keys: {list(session.keys())}")
        logger.info(f"Calendar download page - Session data: {dict(session)}")
        logger.info(f"Calendar download page - Request cookies: {dict(request.cookies)}")
        logger.info(f"Calendar download page - User agent: {request.headers.get('User-Agent', 'Unknown')}")
        logger.info(f"Calendar download page - Referer: {request.headers.get('Referer', 'No referer')}")
        
        session_data = get_session_data_for_user(user["email"])
        logger.info(f"Calendar download page - Session data retrieved: {session_data.get('email') if session_data else 'None'}")
        
        # Wrap session data in the structure expected by mobile layout template
        template_data = {
            "user": session_data,
            "authenticated": True
        }
        
        return render_template("mobile/calendar_download.html", session_data=template_data)
    except Exception as e:
        logger.error(f"Error rendering calendar download page: {str(e)}")
        return "Error loading page", 500


@download_bp.route("/cal/season-download.ics")
@login_required
def download_season_calendar():
    """
    Generate and download a season calendar (.ics file) for the authenticated user.
    
    Returns:
        Response: .ics file with practices and matches for the current season
    """
    try:
        # Additional session debugging for mobile
        logger.info(f"Download route - Session keys: {list(session.keys())}")
        logger.info(f"Download route - Session user: {session.get('user')}")
        logger.info(f"Download route - Request user agent: {request.headers.get('User-Agent', 'Unknown')}")
        logger.info(f"Download route - Request cookies: {dict(request.cookies)}")
        logger.info(f"Download route - Session cookie name: {request.cookies.get('rally_session', 'Not found')}")
        logger.info(f"Download route - All session cookies: {[k for k in request.cookies.keys() if 'session' in k.lower()]}")
        logger.info(f"Download route - All cookies: {list(request.cookies.keys())}")
        logger.info(f"Download route - Cookie values: {[(k, v[:50] + '...' if len(v) > 50 else v) for k, v in request.cookies.items()]}")
        logger.info(f"Download route - Session object type: {type(session)}")
        logger.info(f"Download route - Session object dir: {dir(session)}")
        logger.info(f"Download route - Session permanent: {getattr(session, '_permanent', 'Not found')}")
        logger.info(f"Download route - Session modified: {getattr(session, '_modified', 'Not found')}")
        logger.info(f"Download route - Session new: {getattr(session, '_new', 'Not found')}")
        logger.info(f"Download route - Session invalid: {getattr(session, '_invalid', 'Not found')}")
        logger.info(f"Download route - Session cookie domain: {getattr(session, '_domain', 'Not found')}")
        logger.info(f"Download route - Session cookie path: {getattr(session, '_path', 'Not found')}")
        logger.info(f"Download route - Session cookie secure: {getattr(session, '_secure', 'Not found')}")
        
        # Check if this is a mobile request and log additional info
        if 'iPhone' in request.headers.get('User-Agent', '') or 'Mobile' in request.headers.get('User-Agent', ''):
            logger.warning("MOBILE REQUEST DETECTED - Enhanced mobile debugging")
            logger.warning(f"Mobile - Referer: {request.headers.get('Referer', 'No referer')}")
            logger.warning(f"Mobile - Origin: {request.headers.get('Origin', 'No origin')}")
            logger.warning(f"Mobile - Accept: {request.headers.get('Accept', 'No accept')}")
            logger.warning(f"Mobile - Sec-Fetch-Site: {request.headers.get('Sec-Fetch-Site', 'No sec-fetch-site')}")
            logger.warning(f"Mobile - Sec-Fetch-Mode: {request.headers.get('Sec-Fetch-Mode', 'No sec-fetch-mode')}")
            logger.warning(f"Mobile - Sec-Fetch-Dest: {request.headers.get('Sec-Fetch-Dest', 'No sec-fetch-dest')}")
            
            # Check if this is a direct access (no referer from mobile pages)
            if not request.headers.get('Referer') or 'mobile' not in request.headers.get('Referer', '').lower():
                logger.error("MOBILE DIRECT ACCESS DETECTED - User bypassed mobile flow!")
                logger.error("This should not happen - user should go through /cal/mobile-session-setup first")
                logger.error("Check if the mobile availability page link was updated correctly")
        
        user = session["user"]
        user_id = user.get("id")
        
        # Fallback: try to get user from session in different ways
        if not user_id:
            logger.warning(f"User ID not found in session, trying fallback methods")
            # Try alternative session access methods
            if hasattr(session, 'get'):
                user = session.get("user")
                user_id = user.get("id") if user else None
                logger.info(f"Fallback 1 - User from session.get: {user}")
            
            if not user_id and "user" in session:
                user = session["user"]
                user_id = user.get("id") if user else None
                logger.info(f"Fallback 2 - User from session['user']: {user}")
            
                    # Mobile-specific fallback: check if this is a mobile request
        if not user_id and 'iPhone' in request.headers.get('User-Agent', ''):
            logger.warning("Mobile iPhone detected - checking for mobile session issues")
            # Try to get session from different cookie names
            for cookie_name in request.cookies.keys():
                if 'session' in cookie_name.lower():
                    logger.info(f"Found potential session cookie: {cookie_name}")
                    # Try to decode the session cookie
                    try:
                        import base64
                        cookie_value = request.cookies.get(cookie_name)
                        if cookie_value:
                            logger.info(f"Session cookie value: {cookie_value[:100]}...")
                    except Exception as e:
                        logger.error(f"Error decoding session cookie: {e}")
            
            # Check if session was created but not persisted
            logger.warning("Mobile session debugging - checking session persistence")
            logger.warning(f"Session permanent: {getattr(session, '_permanent', 'Not found')}")
            logger.warning(f"Session modified: {getattr(session, '_modified', 'Not found')}")
            logger.warning(f"Session new: {getattr(session, '_new', 'Not found')}")
            
            # Try to manually set a test session value
            try:
                session['mobile_test'] = 'test_value'
                session.modified = True
                logger.warning("Manually set mobile test session value")
            except Exception as e:
                logger.error(f"Error setting mobile test session: {e}")
        
        if not user_id:
            logger.error(f"User ID not found in session after fallbacks. User data: {user}")
            logger.error(f"Session type: {type(session)}, Session content: {dict(session)}")
            return jsonify({"error": "User ID not found in session"}), 400
        
        # Get date range for upcoming events (next 6 months instead of fixed season)
        from datetime import date, timedelta
        today = date.today()
        season_start = today  # Start from today
        season_end = today + timedelta(days=180)  # Next 6 months
        
        logger.info(f"Generating calendar for user {user_id}, date range: {season_start} to {season_end}")
        
        # Get player's timezone or default to America/Chicago
        player_timezone = user.get("tz_name", "America/Chicago")
        tz = pytz.timezone(player_timezone)
        logger.info(f"Using timezone: {player_timezone}")
        
        # Get player's team IDs from team membership
        team_ids = get_player_team_ids(user_id)
        if not team_ids:
            logger.warning(f"No teams found for user {user_id}")
            return jsonify({"error": "No teams found for user"}), 404
        
        logger.info(f"Found {len(team_ids)} teams for user: {team_ids}")
        
        # Generate calendar
        cal = generate_season_calendar(user_id, team_ids, season_start, season_end, tz)
        
        # Check if calendar has events
        event_count = len(cal.walk('VEVENT'))
        logger.info(f"Generated calendar with {event_count} events")
        
        if event_count == 0:
            logger.warning("Calendar generated with 0 events - adding informational event")
            
            # Add an informational event to explain why the calendar is empty
            info_event = Event()
            info_event.add('summary', 'No Events Scheduled')
            info_event.add('description', 
                'Your team doesn\'t have any practice times or upcoming matches scheduled for the current season.\n\n'
                'Please contact your team captain or league administrator to add:\n'
                '- Practice times\n'
                '- Match schedules\n\n'
                'This calendar will be updated automatically once events are added.'
            )
            
            # Set event to today at 9 AM
            today = datetime.now(tz)
            info_event.add('dtstart', today)
            info_event.add('dtend', today)
            info_event.add('dtstamp', today)
            
            cal.add_component(info_event)
            event_count = 1
            logger.info("Added informational event to empty calendar")
        
        # Generate filename
        player_name = f"{user.get('first_name', 'Player')}_{user.get('last_name', '')}".strip()
        filename = f"rally_{player_name}_season.ics"
        
        # Return .ics file
        return Response(
            cal.to_ical(),
            mimetype="text/calendar",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error generating calendar: {str(e)}")
        return jsonify({"error": "Failed to generate calendar"}), 500


@download_bp.route("/cal/mobile-session-setup")
def mobile_session_setup():
    """
    Route to help mobile users establish a session before downloading.
    This should be called from the mobile availability page.
    """
    try:
        from flask import make_response, jsonify, redirect, url_for
        
        # Check if user is already authenticated
        if "user" in session and session["user"]:
            logger.info(f"Mobile session setup - User already authenticated: {session['user'].get('email', 'Unknown')}")
            # Redirect to calendar download page
            return redirect(url_for('download.calendar_download_page'))
        
        # Check if this is a mobile request
        is_mobile = 'iPhone' in request.headers.get('User-Agent', '') or 'Mobile' in request.headers.get('User-Agent', '')
        
        logger.info(f"Mobile session setup - Request from: {request.headers.get('User-Agent', 'Unknown')}")
        logger.info(f"Mobile session setup - Is mobile: {is_mobile}")
        logger.info(f"Mobile session setup - Referer: {request.headers.get('Referer', 'No referer')}")
        logger.info(f"Mobile session setup - Session keys: {list(session.keys())}")
        
        if not is_mobile:
            return jsonify({"error": "This route is for mobile users only"}), 400
        
        # Try to establish a mobile session
        logger.info("Mobile session setup - Attempting to establish session")
        
        # Check if we have any authentication tokens or referer info
        referer = request.headers.get('Referer', '')
        if 'mobile/availability' in referer:
            logger.info(f"Mobile session setup - Valid referer: {referer}")
            # This is a valid mobile flow, try to redirect to login or establish session
            return redirect(url_for('mobile.serve_mobile_availability'))
        
        # If no valid referer, provide instructions
        logger.warning(f"Mobile session setup - Invalid referer: {referer}")
        logger.warning("User did not follow proper mobile flow - providing instructions")
        
        return jsonify({
            "message": "Mobile session setup required",
            "instructions": [
                "1. Go to the mobile availability page first: /mobile/availability",
                "2. Make sure you're logged in",
                "3. Then click the download button in the green banner",
                "4. This will establish your mobile session properly"
            ],
            "mobile_availability_url": url_for('mobile.serve_mobile_availability'),
            "correct_flow": "/mobile/availability → Click Download → Calendar Download",
            "is_mobile": True,
            "error": "Invalid mobile flow - please follow the instructions above"
        })
        
    except Exception as e:
        logger.error(f"Error in mobile session setup: {str(e)}")
        return jsonify({"error": str(e)}), 500


@download_bp.route("/cal/mobile-auth-test")
def mobile_auth_test():
    """
    Test route specifically for mobile authentication debugging.
    """
    try:
        from flask import make_response, jsonify
        
        # Log all request information for mobile debugging
        mobile_info = {
            "user_agent": request.headers.get('User-Agent', 'Unknown'),
            "is_mobile": 'iPhone' in request.headers.get('User-Agent', '') or 'Mobile' in request.headers.get('User-Agent', ''),
            "cookies": dict(request.cookies),
            "headers": dict(request.headers),
            "session_keys": list(session.keys()),
            "session_data": dict(session),
            "referer": request.headers.get('Referer', 'No referer'),
            "origin": request.headers.get('Origin', 'No origin'),
            "host": request.headers.get('Host', 'No host'),
            "x_forwarded_proto": request.headers.get('X-Forwarded-Proto', 'No protocol'),
            "cf_visitor": request.headers.get('Cf-Visitor', 'No cloudflare info')
        }
        
        # Try to set a test session value
        try:
            session['mobile_test'] = 'mobile_session_test'
            session['test_time'] = str(datetime.now())
            session.modified = True
            mobile_info["session_set_success"] = True
            mobile_info["session_test_value"] = session.get('mobile_test', 'Not set')
        except Exception as e:
            mobile_info["session_set_success"] = False
            mobile_info["session_set_error"] = str(e)
        
        # Create response with mobile debugging info
        response = make_response(jsonify(mobile_info))
        
        # Try to set multiple types of cookies for testing
        try:
            # Test cookie 1: Basic cookie
            response.set_cookie(
                'test_mobile_basic',
                'basic_test_value',
                max_age=3600,
                secure=False,  # Try without secure first
                httponly=False,
                samesite='Lax'
            )
            
            # Test cookie 2: Secure cookie (like production)
            response.set_cookie(
                'test_mobile_secure',
                'secure_test_value',
                max_age=3600,
                secure=True,
                httponly=False,
                samesite='Lax'
            )
            
            # Test cookie 3: Session-like cookie
            response.set_cookie(
                'test_mobile_session',
                'session_test_value',
                max_age=3600,
                secure=True,
                httponly=True,
                samesite='Lax'
            )
            
            mobile_info["cookies_set"] = True
        except Exception as e:
            mobile_info["cookies_set"] = False
            mobile_info["cookies_error"] = str(e)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in mobile auth test route: {str(e)}")
        return jsonify({"error": str(e)}), 500


@download_bp.route("/cal/test-session")
def test_session_setting():
    """
    Test route to check if session cookies can be set on mobile.
    """
    try:
        from flask import make_response
        
        # Try to set a test session value
        session['test_mobile'] = 'mobile_session_test'
        session['test_time'] = str(datetime.now())
        
        # Create response with session debugging
        response_data = {
            "session_keys": list(session.keys()),
            "session_data": dict(session),
            "cookies_sent": dict(request.cookies),
            "user_agent": request.headers.get('User-Agent', 'Unknown'),
            "test_value_set": session.get('test_mobile', 'Not set')
        }
        
        response = make_response(jsonify(response_data))
        
        # Try to explicitly set a test cookie
        response.set_cookie(
            'test_mobile_cookie',
            'mobile_test_value',
            max_age=3600,
            secure=True,
            httponly=False,  # Allow JavaScript access for testing
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in test session route: {str(e)}")
        return jsonify({"error": str(e)}), 500


@download_bp.route("/cal/debug")
@login_required
def debug_calendar_generation():
    """
    Debug route to check calendar generation without downloading.
    """
    try:
        user = session["user"]
        user_id = user.get("id")
        
        if not user_id:
            return jsonify({"error": "User ID not found in session"}), 400
        
        # Get date range for upcoming events (next 6 months instead of fixed season)
        from datetime import date, timedelta
        today = date.today()
        season_start = today  # Start from today
        season_end = today + timedelta(days=180)  # Next 6 months
        
        # Get player's timezone or default to America/Chicago
        player_timezone = user.get("tz_name", "America/Chicago")
        tz = pytz.timezone(player_timezone)
        
        # Get player's team IDs from team membership
        team_ids = get_player_team_ids(user_id)
        if not team_ids:
            return jsonify({"error": "No teams found for user"}), 404
        
        # Generate calendar
        cal = generate_season_calendar(user_id, team_ids, season_start, season_end, tz)
        
        # Check if calendar has events
        event_count = len(cal.walk('VEVENT'))
        
        # Get some sample event details
        events_info = []
        for event in cal.walk('VEVENT'):
            summary = event.get('summary', 'No Summary')
            start = event.get('dtstart', 'No Start Time')
            events_info.append({
                'summary': str(summary),
                'start': str(start)
            })
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "team_ids": team_ids,
            "season_start": str(season_start),
            "season_end": str(season_end),
            "timezone": player_timezone,
            "total_events": event_count,
            "sample_events": events_info[:5]  # First 5 events
        })
        
    except Exception as e:
        logger.error(f"Error in debug route: {str(e)}")
        return jsonify({"error": str(e)}), 500


def get_player_team_ids(user_id):
    """
    Get all team IDs for a user from their player associations.
    
    Args:
        user_id (int): User ID
        
    Returns:
        list: List of team IDs
    """
    try:
        # Query to get team IDs from user's player associations
        query = """
            SELECT DISTINCT p.team_id
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s AND p.team_id IS NOT NULL
        """
        
        results = execute_query(query, (user_id,))
        return [row["team_id"] for row in results if row["team_id"]]
        
    except Exception as e:
        logger.error(f"Error getting player team IDs: {str(e)}")
        return []


def generate_season_calendar(user_id, team_ids, season_start, season_end, tz):
    """
    Generate a calendar with practices and matches for the season.
    
    Args:
        user_id (int): User ID
        team_ids (list): List of team IDs
        season_start (date): Season start date
        season_end (date): Season end date
        tz (pytz.timezone): Player's timezone
        
    Returns:
        Calendar: iCalendar object with events
    """
    cal = Calendar()
    cal.add('prodid', '-//Rally//Calendar//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    
    # Add practices
    add_practices_to_calendar(cal, team_ids, season_start, season_end, tz)
    
    # Add matches
    add_matches_to_calendar(cal, team_ids, season_start, season_end, tz)
    
    return cal


def add_practices_to_calendar(cal, team_ids, season_start, season_end, tz):
    """
    Add practice events to the calendar using the same logic as availability page.
    
    Args:
        cal (Calendar): iCalendar object
        team_ids (list): List of team IDs
        season_start (date): Season start date
        season_end (date): Season end date
        tz (pytz.timezone): Player's timezone
    """
    try:
        # Use the exact same simple query as the availability page, but include club info for Google Maps
        team_ids_str = ','.join(map(str, team_ids))
        query = """
            SELECT DISTINCT
                s.match_date,
                s.match_time,
                s.home_team,
                s.away_team,
                s.location,
                s.home_team_id,
                s.away_team_id,
                hc.name as home_club_name,
                hc.club_address as home_club_address
            FROM schedule s
            JOIN teams ht ON s.home_team_id = ht.id
            JOIN clubs hc ON ht.club_id = hc.id
            WHERE (s.home_team_id IN ({}) OR s.away_team_id IN ({}))
            ORDER BY s.match_date ASC, s.match_time ASC
            LIMIT 100
        """.format(team_ids_str, team_ids_str)
        
        all_events = execute_query(query)
        logger.info(f"Found {len(all_events)} total events in schedule for teams {team_ids}")
        
        # Filter for practices (same logic as availability page)
        practices = []
        for event in all_events:
            home_team = event.get('home_team', '')
            away_team = event.get('away_team', '')
            
            # Detect practice sessions (same logic as availability page)
            is_practice = (
                'Practice' in home_team or 
                'Practice' in away_team or
                (not away_team or away_team.strip() == '')
            )
            
            if is_practice:
                practices.append(event)
        
        logger.info(f"Found {len(practices)} practice records in schedule for teams {team_ids}")
        
        practice_events_added = 0
        for practice in practices:
            logger.info(f"Processing practice: {practice['home_team']} on {practice['match_date']}")
            
            # Create practice event
            event = Event()
            # Extract series name from home_team (e.g., "Tennaqua Practice - Series 22" -> "Series 22")
            series_name = practice['home_team'].split(' - ')[-1] if ' - ' in practice['home_team'] else practice['home_team']
            event.add('summary', f"{series_name} Weekly Practice")
            
            # Set start and end times
            if practice["match_time"]:
                start_datetime = datetime.combine(practice["match_date"], practice["match_time"])
                # Default practice duration to 90 minutes
                end_datetime = start_datetime + timedelta(minutes=90)
            else:
                # Default to 6 PM if no time specified
                start_datetime = datetime.combine(practice["match_date"], time(18, 0))
                end_datetime = start_datetime + timedelta(minutes=90)
            
            # Apply timezone
            start_dt = tz.localize(start_datetime)
            end_dt = tz.localize(end_datetime)
            
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)
            event.add('dtstamp', datetime.now(tz))
            
            # Add description with Google Maps link
            description = f"Team: {practice['home_team']}"
            if practice.get("location"):
                description += f"\nLocation: {practice['location']}"
            
            # Add Google Maps link if club address is available
            if practice.get("home_club_address"):
                import urllib.parse
                encoded_address = urllib.parse.quote(practice["home_club_address"])
                direction_url = f"https://www.google.com/maps/search/?api=1&query={encoded_address}"
                description += f"\nDirections: {direction_url}"
            
            event.add('description', description)
            
            # Add to calendar
            cal.add_component(event)
            practice_events_added += 1
        
        logger.info(f"Added {practice_events_added} practice events to calendar")
                
    except Exception as e:
        logger.error(f"Error adding practices to calendar: {str(e)}")
        logger.error(f"Exception details: {e}")


def add_matches_to_calendar(cal, team_ids, season_start, season_end, tz):
    """
    Add match events to the calendar.
    
    Args:
        cal (Calendar): iCalendar object
        team_ids (list): List of team IDs
        season_start (date): Season start date
        season_end (date): Season end date
        tz (pytz.timezone): Player's timezone
    """
    try:
        # Query matches for the player's teams (same simple approach as practices, but include club info)
        team_ids_str = ','.join(map(str, team_ids))
        query = """
            SELECT DISTINCT
                s.match_date,
                s.match_time,
                s.home_team,
                s.away_team,
                s.location,
                s.home_team_id,
                s.away_team_id,
                hc.name as home_club_name,
                hc.club_address as home_club_address
            FROM schedule s
            JOIN teams ht ON s.home_team_id = ht.id
            JOIN clubs hc ON ht.club_id = hc.id
            WHERE (s.home_team_id IN ({}) OR s.away_team_id IN ({}))
            ORDER BY s.match_date ASC, s.match_time ASC
            LIMIT 100
        """.format(team_ids_str, team_ids_str)
        
        all_events = execute_query(query)
        logger.info(f"Found {len(all_events)} total events in schedule for teams {team_ids}")
        
        # Filter for matches (non-practice events)
        matches = []
        for event in all_events:
            home_team = event.get('home_team', '')
            away_team = event.get('away_team', '')
            
            # Detect matches (opposite of practice logic)
            is_match = (
                'Practice' not in home_team and 
                'Practice' not in away_team and
                away_team and away_team.strip() != ''
            )
            
            if is_match:
                matches.append(event)
        
        logger.info(f"Found {len(matches)} match records in schedule for teams {team_ids}")
        
        match_events_added = 0
        for match in matches:
            logger.info(f"Processing match: {match['home_team']} vs {match['away_team']} on {match['match_date']}")
            
            # Create match event
            event = Event()
            
            # Set event title with HOME/AWAY indicator based on location vs home team club
            # Use the logic specified: strip series number from home team and compare with location
            home_team = match.get('home_team', '')
            match_location = match.get("location", "").strip() if match.get("location") else ""
            
            # Strip series number from home team (e.g., "Tennaqua 22" -> "Tennaqua")
            # Look for patterns like "Series X", "SX", or just numbers at the end
            stripped_home_team = re.sub(r'\s*(?:Series\s*)?(?:S?\d+[A-Za-z]*)\s*$', '', home_team).strip()
            
            # Use fuzzy matching to compare stripped home team with location
            # Convert both to lowercase and check if location contains the stripped team name
            is_home_match = (
                stripped_home_team.lower() in match_location.lower() or
                match_location.lower() in stripped_home_team.lower()
            )
            
            # Determine if user is on home team or away team
            user_is_home_team = match["home_team_id"] in team_ids
            user_is_away_team = match["away_team_id"] in team_ids
            
            # Debug logging to see the matching logic
            logger.info(f"Match: {match['home_team']} vs {match['away_team']}")
            logger.info(f"  Home team: '{home_team}'")
            logger.info(f"  Stripped home team: '{stripped_home_team}'")
            logger.info(f"  Location: '{match_location}'")
            logger.info(f"  Is home match: {is_home_match}")
            logger.info(f"  User team IDs: {team_ids}")
            logger.info(f"  Home team ID: {match['home_team_id']}, Away team ID: {match['away_team_id']}")
            logger.info(f"  User is home team: {user_is_home_team}, User is away team: {user_is_away_team}")
            
            # Determine if USER is HOME or AWAY based on:
            # 1. Is the match at the home team's club? (is_home_match)
            # 2. Is the user on the home team or away team?
            
            if user_is_home_team:
                # User is on the home team
                if is_home_match:
                    # Match is at home team's club = USER is HOME
                    event.add('summary', f"{match['home_team']} vs {match['away_team']} (HOME)")
                else:
                    # Match is NOT at home team's club = USER is AWAY
                    event.add('summary', f"{match['away_team']} vs {match['home_team']} (AWAY)")
            else:
                # User is on the away team
                if is_home_match:
                    # Match is at home team's club = USER is AWAY
                    event.add('summary', f"{match['away_team']} vs {match['home_team']} (AWAY)")
                else:
                    # Match is NOT at home team's club = USER is HOME
                    event.add('summary', f"{match['home_team']} vs {match['away_team']} (HOME)")
            
            # Set start and end times
            if match["match_time"]:
                start_datetime = datetime.combine(match["match_date"], match["match_time"])
                # Default match duration to 2 hours
                end_datetime = start_datetime + timedelta(hours=2)
            else:
                # Default to 6 PM if no time specified
                start_datetime = datetime.combine(match["match_date"], time(18, 0))
                end_datetime = start_datetime + timedelta(hours=2)
            
            # Apply timezone
            start_dt = tz.localize(start_datetime)
            end_dt = tz.localize(end_datetime)
            
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)
            event.add('dtstamp', datetime.now(tz))
            
            # Add location if available
            if match.get("location"):
                event.add('location', match["location"])
            
            # Create description with Google Maps link
            description = f"Home: {match['home_team']}\n"
            description += f"Away: {match['away_team']}"
            
            if match.get("location"):
                description += f"\nLocation: {match['location']}"
            
            # Add Google Maps link if club address is available
            if match.get("home_club_address"):
                import urllib.parse
                encoded_address = urllib.parse.quote(match["home_club_address"])
                direction_url = f"https://www.google.com/maps/search/?api=1&query={encoded_address}"
                description += f"\nDirections: {direction_url}"
            
            event.add('description', description)
            
            # Add to calendar
            cal.add_component(event)
            match_events_added += 1
        
        logger.info(f"Added {match_events_added} match events to calendar")
            
    except Exception as e:
        logger.error(f"Error adding matches to calendar: {str(e)}")
        logger.error(f"Exception details: {e}")



