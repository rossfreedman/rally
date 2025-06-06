"""
Mobile routes blueprint - handles all mobile interface functionality
This module contains routes for mobile-specific pages and user interactions.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from utils.auth import login_required
from utils.logging import log_user_activity
from datetime import datetime
import json
import os
from urllib.parse import unquote

# Import availability functions from existing routes
from routes.act.schedule import get_matches_for_user_club
from routes.act.availability import get_user_availability

from app.services.mobile_service import (
    get_player_analysis_by_name,
    get_mobile_schedule_data,
    get_player_analysis,
    get_mobile_team_data,
    get_mobile_series_data,
    get_teams_players_data,
    get_player_search_data,
    get_mobile_club_data,
    get_mobile_player_stats,
    get_practice_times_data,
    get_all_team_availability_data,
    get_mobile_availability_data,
    get_club_players_data
)

# Create mobile blueprint
mobile_bp = Blueprint('mobile', __name__)

@mobile_bp.route('/mobile')
@login_required
def serve_mobile():
    """Serve the mobile version of the application"""
    print(f"=== SERVE_MOBILE FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    
    # Don't handle admin routes
    if '/admin' in request.path:
        print("Admin route detected in mobile, redirecting to serve_admin")
        return redirect(url_for('admin.serve_admin'))
        
    # Create session data script
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    # Log mobile access
    try:
        log_user_activity(
            session['user']['email'], 
            'page_visit',
            page='mobile_home'
        )
    except Exception as e:
        print(f"Error logging mobile access: {str(e)}")
    
    return render_template('mobile/index.html', session_data=session_data)

@mobile_bp.route('/mobile/rally')
@login_required
def serve_rally_mobile():
    """Redirect from old mobile interface to new one"""
    try:
        # Log the redirect
        log_user_activity(
            session['user']['email'], 
            'redirect',
            page='rally_mobile_to_new',
            details='Redirected from old mobile interface to new one'
        )
    except Exception as e:
        print(f"Error logging rally mobile redirect: {str(e)}")
    
    return redirect(url_for('mobile.serve_mobile'))

@mobile_bp.route('/mobile/matches')
@login_required
def serve_mobile_matches():
    """Serve the mobile matches page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_matches')
    return render_template('mobile/matches.html', session_data=session_data)

@mobile_bp.route('/mobile/rankings')
@login_required
def serve_mobile_rankings():
    """Serve the mobile rankings page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_rankings')
    return render_template('mobile/rankings.html', session_data=session_data)

@mobile_bp.route('/mobile/profile')
@login_required
def serve_mobile_profile():
    """Serve the mobile profile page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_profile')
    return render_template('mobile/profile.html', session_data=session_data)

@mobile_bp.route('/mobile/player-detail/<player_id>')
@login_required
def serve_mobile_player_detail(player_id):
    """Serve the mobile player detail page (server-rendered, consistent with other mobile pages)"""
    player_name = unquote(player_id)
    
    # Use the mobile service function that we just implemented
    analyze_data = get_player_analysis_by_name(player_name)
    
    # Get current PTI from player history for the viewed player
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        player_history_path = os.path.join(project_root, 'data', 'player_history.json')
        
        with open(player_history_path, 'r') as f:
            player_history = json.load(f)
            
        # Find the player's record by matching name
        player_record = next((p for p in player_history if p.get('name', '').lower() == player_name.lower()), None)
        
        if player_record and player_record.get('matches'):
            # Sort matches by date to find most recent
            matches = sorted(player_record['matches'], key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y'), reverse=True)
            if matches:
                current_pti = matches[0].get('end_pti')
                
                # Calculate weekly PTI change
                weekly_pti_change = None
                if len(matches) > 1:
                    current_date = datetime.strptime(matches[0]['date'], '%m/%d/%Y')
                    # Find the match closest to one week ago
                    prev_match = None
                    for match in matches[1:]:
                        match_date = datetime.strptime(match['date'], '%m/%d/%Y')
                        if (current_date - match_date).days >= 5:
                            prev_match = match
                            break
                    
                    if prev_match and 'end_pti' in prev_match:
                        prev_pti = prev_match['end_pti']
                        weekly_pti_change = current_pti - prev_pti
                
                if current_pti is not None:
                    analyze_data['current_pti'] = float(current_pti)
                    analyze_data['weekly_pti_change'] = float(weekly_pti_change) if weekly_pti_change is not None else None
                else:
                    analyze_data['current_pti'] = None
                    analyze_data['weekly_pti_change'] = None
            else:
                analyze_data['current_pti'] = None
                analyze_data['weekly_pti_change'] = None
        else:
            analyze_data['current_pti'] = None
            analyze_data['weekly_pti_change'] = None
            
    except Exception as e:
        print(f"Error getting current PTI: {str(e)}")
        analyze_data['current_pti'] = None
        analyze_data['weekly_pti_change'] = None
    
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    log_user_activity(
        session['user']['email'], 
        'page_visit', 
        page='mobile_player_detail',
        details=f'Viewed player {player_name}'
    )
    return render_template('mobile/player_detail.html', 
                          session_data=session_data, 
                          analyze_data=analyze_data,
                          player_name=player_name)

@mobile_bp.route('/mobile/view-schedule')
@login_required
def serve_mobile_view_schedule():
    """Serve the mobile View Schedule page with the user's schedule."""
    try:
        schedule_data = get_mobile_schedule_data(session['user'])
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_view_schedule')
        
        return render_template('mobile/view_schedule.html', 
                             session_data=session_data,
                             **schedule_data)
                             
    except Exception as e:
        print(f"Error serving mobile view schedule: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/view_schedule.html', 
                             session_data=session_data,
                             error="Failed to load schedule data")

@mobile_bp.route('/mobile/analyze-me')
@login_required
def serve_mobile_analyze_me():
    """Serve the mobile Analyze Me page"""
    try:
        analyze_data = get_player_analysis(session['user'])
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_analyze_me')
        
        return render_template('mobile/analyze_me.html', 
                             session_data=session_data,
                             analyze_data=analyze_data)
                             
    except Exception as e:
        print(f"Error serving mobile analyze me: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        # Create a basic analyze_data structure with error message for the template
        analyze_data = {
            'error': f"Failed to load analysis data: {str(e)}",
            'current_season': None,
            'court_analysis': {},
            'career_stats': None,
            'player_history': None,
            'current_pti': None,
            'weekly_pti_change': None
        }
        
        return render_template('mobile/analyze_me.html', 
                             session_data=session_data,
                             analyze_data=analyze_data)

@mobile_bp.route('/mobile/my-team')
@login_required
def serve_mobile_my_team():
    """Serve the mobile My Team page"""
    try:
        result = get_mobile_team_data(session['user'])
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_my_team')
        
        # Extract all data from result
        team_data = result.get('team_data')
        court_analysis = result.get('court_analysis', {})
        top_players = result.get('top_players', [])
        error = result.get('error')
        
        return render_template('mobile/my_team.html', 
                             session_data=session_data,
                             team_data=team_data,
                             court_analysis=court_analysis,
                             top_players=top_players,
                             error=error)
                             
    except Exception as e:
        print(f"Error serving mobile my team: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/my_team.html', 
                             session_data=session_data,
                             team_data=None,
                             court_analysis={},
                             top_players=[],
                             error="Failed to load team data")

@mobile_bp.route('/mobile/myteam')
@login_required
def serve_mobile_myteam():
    """Redirect from old myteam path to my-team"""
    return redirect(url_for('mobile.serve_mobile_my_team'))

@mobile_bp.route('/mobile/settings')
@login_required
def serve_mobile_settings():
    """Serve the mobile settings page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_settings')
    return render_template('mobile/user_settings.html', session_data=session_data)

@mobile_bp.route('/mobile/my-series')
@login_required
def serve_mobile_my_series():
    """Serve the mobile My Series page"""
    try:
        series_data = get_mobile_series_data(session['user'])
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_my_series')
        
        return render_template('mobile/my_series.html', 
                             session_data=session_data,
                             **series_data)
                             
    except Exception as e:
        print(f"Error serving mobile my series: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/my_series.html', 
                             session_data=session_data,
                             error="Failed to load series data")

@mobile_bp.route('/mobile/myseries')
@login_required
def redirect_myseries():
    """Redirect from old myseries path to my-series"""
    return redirect(url_for('mobile.serve_mobile_my_series'))

@mobile_bp.route('/mobile/teams-players', methods=['GET'])
@login_required
def mobile_teams_players():
    """Get teams and players for mobile interface"""
    try:
        data = get_teams_players_data(session['user'])
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_teams_players')
        
        return render_template('mobile/teams_players.html', 
                             session_data={'user': session['user'], 'authenticated': True},
                             **data)
                             
    except Exception as e:
        print(f"Error in mobile teams players: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        return render_template('mobile/teams_players.html', 
                             session_data={'user': session['user'], 'authenticated': True},
                             error="Failed to load teams and players data")

@mobile_bp.route('/mobile/player-search', methods=['GET'])
@login_required  
def mobile_player_search():
    """Serve the mobile player search page with enhanced fuzzy matching"""
    try:
        search_data = get_player_search_data(session['user'])
        
        # Add logging for search activity if a search was attempted
        if search_data.get('search_attempted') and search_data.get('search_query'):
            matching_count = len(search_data.get('matching_players', []))
            log_user_activity(
                session['user']['email'], 
                'player_search',
                details=f'Searched for {search_data["search_query"]}, found {matching_count} matches'
            )
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_player_search')
        
        return render_template('mobile/player_search.html', 
                             session_data=session_data,
                             **search_data)
                             
    except Exception as e:
        print(f"Error in mobile player search: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/player_search.html', 
                             session_data=session_data,
                             first_name='',
                             last_name='',
                             search_attempted=False,
                             matching_players=[],
                             search_query=None,
                             error="Failed to load player search data")

@mobile_bp.route('/mobile/my-club')
@login_required
def my_club():
    """Serve the mobile My Club page"""
    try:
        club_data = get_mobile_club_data(session['user'])
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_my_club')
        
        return render_template('mobile/my_club.html', 
                             session_data=session_data,
                             **club_data)
                             
    except Exception as e:
        print(f"Error serving mobile my club: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/my_club.html', 
                             session_data=session_data,
                             error="Failed to load club data")

@mobile_bp.route('/mobile/player-stats')
@login_required
def serve_mobile_player_stats():
    """Serve the mobile player stats page"""
    try:
        stats_data = get_mobile_player_stats(session['user'])
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_player_stats')
        
        return render_template('mobile/player_stats.html', 
                             session_data=session_data,
                             **stats_data)
                             
    except Exception as e:
        print(f"Error serving mobile player stats: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/player_stats.html', 
                             session_data=session_data,
                             error="Failed to load player stats")

@mobile_bp.route('/mobile/improve')
@login_required
def serve_mobile_improve():
    """Serve the mobile improve page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_improve')
    return render_template('mobile/improve.html', session_data=session_data)

@mobile_bp.route('/mobile/email-team')
@login_required
def serve_mobile_email_team():
    """Serve the mobile email team page"""
    session_data = {'user': session['user'], 'authenticated': True}
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_email_team')
    return render_template('mobile/email_team.html', session_data=session_data)

@mobile_bp.route('/mobile/practice-times')
@login_required
def serve_mobile_practice_times():
    """Serve the mobile practice times page"""
    try:
        practice_data = get_practice_times_data(session['user'])
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_practice_times')
        
        return render_template('mobile/practice_times.html', 
                             session_data=session_data,
                             **practice_data)
                             
    except Exception as e:
        print(f"Error serving mobile practice times: {str(e)}")
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/practice_times.html', 
                             session_data=session_data,
                             error="Failed to load practice times data")

@mobile_bp.route('/mobile/availability')
@login_required
def serve_mobile_availability():
    """Serve the mobile availability page for viewing/setting user availability"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'error': 'No user in session'}), 400
        
        player_name = f"{user['first_name']} {user['last_name']}"
        series = user['series']

        # Get matches for the user's club/series using existing function (same as availability-calendar)
        matches = get_matches_for_user_club(user)
        
        # Get this user's availability for each match using existing function (same as availability-calendar)
        availability = get_user_availability(player_name, matches, series)

        # Create match-availability pairs for the template
        match_avail_pairs = list(zip(matches, availability))

        session_data = {
            'user': user,
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_availability')
        
        return render_template('mobile/availability.html', 
                             session_data=session_data,
                             match_avail_pairs=match_avail_pairs,
                             players=[{'name': player_name}])
    except Exception as e:
        print(f"Error serving mobile availability: {str(e)}")
        return f"Error loading availability page: {str(e)}", 500

@mobile_bp.route('/mobile/all-team-availability')
@login_required
def serve_all_team_availability():
    """Serve the mobile all team availability page"""
    try:
        # Get the selected date from query parameter
        selected_date = request.args.get('date')
        
        # Call the service function with the selected date
        availability_data = get_all_team_availability_data(session['user'], selected_date)
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_all_team_availability')
        
        return render_template('mobile/all_team_availability.html', 
                             session_data=session_data,
                             **availability_data)
                             
    except Exception as e:
        print(f"Error serving mobile all team availability: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/all_team_availability.html', 
                             session_data=session_data,
                             error="Failed to load availability data")

@mobile_bp.route('/mobile/team-schedule')
@login_required
def serve_mobile_team_schedule():
    """Serve the team schedule page with loading screen"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Please log in first'}), 401
            
        club_name = user.get('club')
        series = user.get('series')
        
        if not club_name or not series:
            return render_template('mobile/team_schedule.html', 
                                 session_data={'user': user},
                                 error='Please set your club and series in your profile settings')

        # Create a clean team name string for the title
        team_name = f"{club_name} - {series}"
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_team_schedule')
        
        return render_template(
            'mobile/team_schedule.html',
            team=team_name,
            session_data={'user': user}
        )
        
    except Exception as e:
        print(f"❌ Error in serve_mobile_team_schedule: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        session_data = {
            'user': session.get('user'),
            'authenticated': True
        }
        
        return render_template('mobile/team_schedule.html', 
                             session_data=session_data,
                             error='An error occurred while loading the team schedule')

@mobile_bp.route('/mobile/availability-calendar')
@login_required  
def serve_mobile_availability_calendar():
    """Serve the mobile availability calendar page"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'error': 'No user in session'}), 400
        
        player_name = f"{user['first_name']} {user['last_name']}"
        series = user['series']

        # Get matches for the user's club/series using existing function
        matches = get_matches_for_user_club(user)
        
        # Get this user's availability for each match using existing function
        availability = get_user_availability(player_name, matches, series)

        session_data = {
            'user': user,
            'authenticated': True,
            'matches': matches,
            'availability': availability,
            'players': [{'name': player_name}]
        }
        
        log_user_activity(
            session['user']['email'], 
            'page_visit', 
            page='mobile_availability_calendar'
        )
        
        return render_template('mobile/availability-calendar.html', 
                             session_data=session_data)
        
    except Exception as e:
        print(f"ERROR in mobile_availability_calendar: {str(e)}")
        return f"Error: {str(e)}", 500

@mobile_bp.route('/mobile/find-people-to-play')
@login_required
def serve_mobile_find_people_to_play():
    """Serve the mobile Find People to Play page"""
    try:
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(
            session['user']['email'], 
            'page_visit', 
            page='mobile_find_people_to_play'
        )
        
        return render_template('mobile/find_people_to_play.html', session_data=session_data)
        
    except Exception as e:
        print(f"Error serving find people to play page: {str(e)}")
        return jsonify({'error': str(e)}), 500

@mobile_bp.route('/mobile/reserve-court')
@login_required
def serve_mobile_reserve_court():
    """Serve the mobile Reserve Court page"""
    try:
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(
            session['user']['email'], 
            'page_visit', 
            page='mobile_reserve_court'
        )
        
        return render_template('mobile/reserve-court.html', session_data=session_data)
        
    except Exception as e:
        print(f"Error serving reserve court page: {str(e)}")
        return jsonify({'error': str(e)}), 500 