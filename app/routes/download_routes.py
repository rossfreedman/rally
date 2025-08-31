"""
Download Routes Blueprint

This module contains routes for downloading various data formats including calendar files.
"""

import logging
import re
from datetime import datetime, date, time, timedelta
from functools import wraps

from flask import Blueprint, Response, session, request, jsonify, redirect
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
    """Decorator to require authentication - same as other Rally pages"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user exists in session (same logic as other pages)
        if "user" not in session:
            # For mobile requests without session, redirect to login instead of JSON error
            user_agent = request.headers.get('User-Agent', '')
            is_mobile = 'iPhone' in user_agent or 'Android' in user_agent or 'Mobile' in user_agent
            
            if is_mobile and request.path.startswith('/cal/'):
                # Mobile calendar download without session - redirect to login
                return redirect('/login')
            else:
                return jsonify({"error": "Authentication required"}), 401

        user = session["user"]

        # Check if user has required fields (same validation as other pages)
        if not user or not user.get("id") or not user.get("email"):
            return jsonify({"error": "Invalid user session"}), 401

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
        
        session_data = get_session_data_for_user(user["email"])
        
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
        # Get user from session (same as other Rally pages)
        user = session["user"]
        user_id = user.get("id")
        
        if not user_id:
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



