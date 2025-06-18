"""
Mobile routes blueprint - handles all mobile interface functionality
This module contains routes for mobile-specific pages and user interactions.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from utils.auth import login_required
from utils.logging import log_user_activity
from database_utils import execute_query, execute_query_one
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
    get_club_players_data,
    get_mobile_improve_data
)

# Import the new simulation functionality
from app.services.simulation import AdvancedMatchupSimulator, get_players_for_selection, get_teams_for_selection, get_players_by_team

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
    
    # Use the mobile service function with user context for league filtering
    analyze_data = get_player_analysis_by_name(player_name, session['user'])
    
    # PTI data is now handled within the service function with proper league filtering
    
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
        print(f"[DEBUG] Session user type: {type(session['user'])}")
        print(f"[DEBUG] Session user data: {session['user']}")
        
        # Get the session user
        session_user = session['user']
        
        # Check if session already has a tenniscores_player_id (set by league switching)
        if session_user.get('tenniscores_player_id'):
            print(f"[DEBUG] Using session player ID: {session_user.get('tenniscores_player_id')}")
            
            # Fix session data if league_id is None but league_name exists
            if session_user.get('league_id') is None and session_user.get('league_name'):
                print(f"[DEBUG] Session has league_name '{session_user.get('league_name')}' but league_id is None, attempting to resolve")
                try:
                    league_record = execute_query_one(
                        "SELECT id, league_id FROM leagues WHERE league_name = %s", 
                        [session_user.get('league_name')]
                    )
                    if league_record:
                        session_user['league_id'] = league_record['id']
                        print(f"[DEBUG] Resolved league_name to league_id: {league_record['id']} ('{league_record['league_id']}')")
                        # Update session for future requests
                        session['user']['league_id'] = league_record['id']
                    else:
                        print(f"[WARNING] Could not resolve league_name '{session_user.get('league_name')}' to league_id")
                except Exception as e:
                    print(f"[DEBUG] Error resolving league_name to league_id: {e}")
            
            # Use the session data (now with resolved league_id if applicable)
            analyze_data = get_player_analysis(session_user)
        else:
            # Fallback: Look up player data from database using name matching
            print(f"[DEBUG] No player ID in session, looking up from database")
            
            player_query = '''
                SELECT 
                    first_name,
                    last_name,
                    email,
                    tenniscores_player_id,
                    club_id,
                    series_id,
                    league_id
                FROM players 
                WHERE first_name = %s AND last_name = %s
            '''
            
            player_data = execute_query_one(player_query, [
                session_user.get('first_name'), 
                session_user.get('last_name')
            ])
            
            if player_data:
                # Create a complete user object with both session and database data
                complete_user = {
                    'email': session_user.get('email'),
                    'first_name': player_data['first_name'],
                    'last_name': player_data['last_name'],
                    'tenniscores_player_id': player_data['tenniscores_player_id'],
                    'club_id': player_data['club_id'],
                    'series_id': player_data['series_id'],
                    'league_id': player_data['league_id']
                }
                print(f"[DEBUG] Complete user data from DB lookup: {complete_user}")
                analyze_data = get_player_analysis(complete_user)
            else:
                print(f"[DEBUG] No player data found for {session_user.get('first_name')} {session_user.get('last_name')}")
                analyze_data = {
                    'error': 'Player data not found in database',
                    'current_season': None,
                    'court_analysis': {},
                    'career_stats': None
                }
        
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

@mobile_bp.route('/api/player-history-chart')
@login_required
def get_player_history_chart():
    """API endpoint to get player history data for PTI chart - matches rally_reference format"""
    try:
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user = session['user']
        player_id = user.get('tenniscores_player_id')
        player_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        
        if not player_id:
            return jsonify({'error': 'Player ID not found'}), 400
        
        # Get player's database ID first
        player_query = '''
            SELECT 
                p.id,
                p.pti as current_pti,
                p.series_id,
                s.name as series_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
        '''
        player_data = execute_query_one(player_query, [player_id])
        
        if not player_data:
            return jsonify({'error': 'Player not found'}), 404
        
        player_db_id = player_data['id']
        
        # Get PTI history from player_history table
        pti_history_query = '''
            SELECT 
                date,
                end_pti,
                series,
                TO_CHAR(date, 'MM/DD/YYYY') as formatted_date
            FROM player_history
            WHERE player_id = %s
            ORDER BY date ASC
        '''
        
        pti_records = execute_query(pti_history_query, [player_db_id])
        
        if not pti_records:
            # If no records found by player_id, try series matching as fallback
            series_name = player_data.get('series_name', '')
            if series_name:
                series_patterns = [
                    f'%{series_name}%',
                    f'%{series_name.split()[0]}%' if ' ' in series_name else f'%{series_name}%'
                ]
                
                for pattern in series_patterns:
                    series_history_query = '''
                        SELECT 
                            date,
                            end_pti,
                            series,
                            TO_CHAR(date, 'MM/DD/YYYY') as formatted_date
                        FROM player_history
                        WHERE series ILIKE %s
                        ORDER BY date ASC
                    '''
                    
                    pti_records = execute_query(series_history_query, [pattern])
                    if pti_records:
                        break
        
        if not pti_records:
            return jsonify({'error': 'No PTI history found'}), 404
        
        # Format matches data to match rally_reference format
        matches_data = []
        for record in pti_records:
            matches_data.append({
                'date': record['formatted_date'],  # MM/DD/YYYY format
                'end_pti': float(record['end_pti'])
            })
        
        # Return data in the format expected by rally_reference JavaScript
        response_data = {
            'name': player_name,
            'matches': matches_data,
            'success': True,
            'data': matches_data,  # Include both formats for compatibility
            'player_name': player_name,
            'total_matches': len(matches_data)
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error fetching player history chart: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to fetch player history chart'}), 500

@mobile_bp.route('/api/season-history')
@login_required
def get_season_history():
    """API endpoint to get previous season history data"""
    try:
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user = session['user']
        player_id = user.get('tenniscores_player_id')
        
        if not player_id:
            return jsonify({'error': 'Player ID not found'}), 400
        
        # Get player's database ID first
        player_query = '''
            SELECT 
                p.id,
                p.pti as current_pti,
                p.series_id,
                s.name as series_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
        '''
        player_data = execute_query_one(player_query, [player_id])
        
        if not player_data:
            return jsonify({'error': 'Player not found'}), 404
        
        player_db_id = player_data['id']
        
        # Debug logging
        print(f"[DEBUG] Season History - Player ID: {player_id}")
        print(f"[DEBUG] Season History - Player DB ID: {player_db_id}")  
        print(f"[DEBUG] Season History - Player Series: {player_data.get('series_name')}")
        print(f"[DEBUG] Season History - Player Current PTI: {player_data.get('current_pti')}")
        
        # Debug: Check all player_history records for this player
        debug_query = '''
            SELECT series, date, end_pti 
            FROM player_history 
            WHERE player_id = %s 
            ORDER BY date DESC 
        '''
        debug_records = execute_query(debug_query, [player_db_id])
        print(f"[DEBUG] Season History - ALL {len(debug_records)} player_history records for player_id {player_db_id}:")
        
        # Group by series to see what series this player actually has
        series_counts = {}
        for record in debug_records:
            series = record['series']
            if series not in series_counts:
                series_counts[series] = 0
            series_counts[series] += 1
            
        print(f"[DEBUG] Season History - Series breakdown:")
        for series, count in series_counts.items():
            print(f"  {series}: {count} records")
        
        # Show first few records from each series
        print(f"[DEBUG] Season History - Sample records:")
        for record in debug_records[:10]:
            print(f"  Date: {record['date']}, Series: {record['series']}, PTI: {record['end_pti']}")
        
        # Get season history data aggregated by series and tennis season (Aug-May)
        season_history_query = '''
            WITH season_data AS (
                SELECT 
                    series,
                    -- Calculate tennis season year (Aug-May spans two calendar years)
                    -- If month >= 8 (Aug-Dec), season starts that year
                    -- If month < 8 (Jan-Jul), season started previous year
                    CASE 
                        WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                        ELSE EXTRACT(YEAR FROM date) - 1
                    END as season_year,
                    date,
                    end_pti,
                    ROW_NUMBER() OVER (
                        PARTITION BY series, 
                        CASE 
                            WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                            ELSE EXTRACT(YEAR FROM date) - 1
                        END 
                        ORDER BY date ASC
                    ) as rn_start,
                    ROW_NUMBER() OVER (
                        PARTITION BY series, 
                        CASE 
                            WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                            ELSE EXTRACT(YEAR FROM date) - 1
                        END 
                        ORDER BY date DESC
                    ) as rn_end
                FROM player_history
                WHERE player_id = %s
                ORDER BY date DESC
            ),
            season_summary AS (
                SELECT 
                    series,
                    season_year,
                    MAX(CASE WHEN rn_start = 1 THEN end_pti END) as pti_start,
                    MAX(CASE WHEN rn_end = 1 THEN end_pti END) as pti_end,
                    COUNT(*) as matches_count
                FROM season_data
                GROUP BY series, season_year
                HAVING COUNT(*) >= 3  -- Only show seasons with at least 3 matches
            )
            SELECT 
                series,
                season_year,
                pti_start,
                pti_end,
                (pti_end - pti_start) as trend,
                matches_count
            FROM season_summary
            ORDER BY season_year ASC, series
            LIMIT 10
        '''
        
        # Debug: Let's also run the inner query to see what raw data the aggregation is working with
        debug_season_query = '''
            SELECT 
                series,
                CASE 
                    WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                    ELSE EXTRACT(YEAR FROM date) - 1
                END as season_year,
                date,
                end_pti
            FROM player_history
            WHERE player_id = %s
            ORDER BY season_year, series, date
        '''
        debug_season_records = execute_query(debug_season_query, [player_db_id])
        print(f"[DEBUG] Season History - Raw records going into season aggregation:")
        for record in debug_season_records:
            print(f"  Season: {record['season_year']}, Series: {record['series']}, Date: {record['date']}, PTI: {record['end_pti']}")
        
        season_records = execute_query(season_history_query, [player_db_id])
        
        print(f"[DEBUG] Season History - Direct player_id query returned {len(season_records) if season_records else 0} records")
        if season_records:
            print(f"[DEBUG] Season History - Direct query results (showing ALL series this player has participated in):")
            for record in season_records:
                print(f"  Series: {record['series']}, Season: {record['season_year']}, PTI: {record['pti_start']} -> {record['pti_end']}, Matches: {record['matches_count']}")
        
        if not season_records:
            # Try series matching as fallback
            series_name = player_data.get('series_name', '')
            print(f"[DEBUG] Season History - No direct results, trying series fallback with: '{series_name}'")
            if series_name:
                # Create more precise series patterns to avoid false matches
                series_patterns = [f'%{series_name}%']  # Exact series name match only
                
                # Only add first-word pattern if series name is very specific (has colon or numbers)
                if ':' in series_name or any(char.isdigit() for char in series_name):
                    first_part = series_name.split()[0] if ' ' in series_name else series_name
                    # Add pattern with colon to match "Chicago:" vs "Chicago 34"
                    if ':' not in first_part:
                        series_patterns.append(f'%{first_part}:%')
                    series_patterns.append(f'%{first_part}%')
                
                print(f"[DEBUG] Season History - Trying series patterns: {series_patterns}")
                
                for pattern in series_patterns:
                    print(f"[DEBUG] Season History - Trying pattern: '{pattern}'")
                    fallback_query = '''
                        WITH season_data AS (
                            SELECT 
                                series,
                                -- Calculate tennis season year (Aug-May spans two calendar years)
                                CASE 
                                    WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                                    ELSE EXTRACT(YEAR FROM date) - 1
                                END as season_year,
                                date,
                                end_pti,
                                ROW_NUMBER() OVER (
                                    PARTITION BY series, 
                                    CASE 
                                        WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                                        ELSE EXTRACT(YEAR FROM date) - 1
                                    END 
                                    ORDER BY date ASC
                                ) as rn_start,
                                ROW_NUMBER() OVER (
                                    PARTITION BY series, 
                                    CASE 
                                        WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                                        ELSE EXTRACT(YEAR FROM date) - 1
                                    END 
                                    ORDER BY date DESC
                                ) as rn_end
                            FROM player_history
                            WHERE series ILIKE %s
                            ORDER BY date DESC
                        ),
                        season_summary AS (
                            SELECT 
                                series,
                                season_year,
                                MAX(CASE WHEN rn_start = 1 THEN end_pti END) as pti_start,
                                MAX(CASE WHEN rn_end = 1 THEN end_pti END) as pti_end,
                                COUNT(*) as matches_count
                            FROM season_data
                            GROUP BY series, season_year
                            HAVING COUNT(*) >= 3  -- Only show seasons with at least 3 matches
                        )
                        SELECT 
                            series,
                            season_year,
                            pti_start,
                            pti_end,
                            (pti_end - pti_start) as trend,
                            matches_count
                        FROM season_summary
                        ORDER BY season_year ASC, series
                        LIMIT 10
                    '''
                    
                    season_records = execute_query(fallback_query, [pattern])
                    print(f"[DEBUG] Season History - Pattern '{pattern}' returned {len(season_records) if season_records else 0} records")
                    if season_records:
                        print(f"[DEBUG] Season History - Fallback query results:")
                        for record in season_records:
                            print(f"  Series: {record['series']}, Season: {record['season_year']}, PTI: {record['pti_start']} -> {record['pti_end']}")
                        break
        
        if not season_records:
            print(f"[DEBUG] Season History - No season records found for player {player_id}")
            return jsonify({'error': 'No season history found'}), 404
        
        print(f"[DEBUG] Season History - Final results: {len(season_records)} records found")
        
        # Format season data
        seasons = []
        for record in season_records:
            # Create season string (e.g., "2024-2025" for tennis season)
            season_year = int(record['season_year'])
            next_year = season_year + 1
            season_str = f"{season_year}-{next_year}"
            
            # Format trend with arrow (positive PTI change = worse performance = red)
            trend_value = float(record['trend'])
            if trend_value > 0:
                trend_display = f"+{trend_value:.1f} ▲"
                trend_class = "text-red-600"  # Positive = PTI went up = worse performance = red
            elif trend_value < 0:
                trend_display = f"{trend_value:.1f} ▼"
                trend_class = "text-green-600"  # Negative = PTI went down = better performance = green
            else:
                trend_display = "0.0 ─"
                trend_class = "text-gray-500"
            
            seasons.append({
                'season': season_str,
                'series': record['series'],
                'pti_start': round(float(record['pti_start']), 1),
                'pti_end': round(float(record['pti_end']), 1),
                'trend': trend_value,
                'trend_display': trend_display,
                'trend_class': trend_class,
                'matches_count': record['matches_count']
            })
        
        return jsonify({
            'success': True,
            'seasons': seasons,
            'player_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        })
        
    except Exception as e:
        print(f"Error fetching season history: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to fetch season history'}), 500

@mobile_bp.route('/mobile/my-team')
@login_required
def serve_mobile_my_team():
    """Serve the mobile My Team page"""
    print(f"🔥 ROUTE CALLED: /mobile/my-team with user: {session['user']['email']}")
    try:
        print(f"🔥 ABOUT TO CALL: get_mobile_team_data")
        result = get_mobile_team_data(session['user'])
        print(f"🔥 RESULT FROM get_mobile_team_data: {type(result)}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_my_team')
        
        # Extract all data from result
        team_data = result.get('team_data')
        court_analysis = result.get('court_analysis', {})
        top_players = result.get('top_players', [])
        strength_of_schedule = result.get('strength_of_schedule', {})
        error = result.get('error')
        
        return render_template('mobile/my_team.html', 
                             session_data=session_data,
                             team_data=team_data,
                             court_analysis=court_analysis,
                             top_players=top_players,
                             strength_of_schedule=strength_of_schedule,
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
                             strength_of_schedule={
                                 'sos_value': 0.0,
                                 'rank': 0,
                                 'total_teams': 0,
                                 'opponents_count': 0,
                                 'all_teams_sos': [],
                                 'user_team_name': '',
                                 'error': 'Failed to load team data'
                             },
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
    """Serve the mobile improve page with paddle tips"""
    try:
        user = session.get('user')
        if not user:
            return redirect('/login')
            
        session_data = {
            'user': user,
            'authenticated': True
        }
        
        # Load improve data using service function
        improve_data = get_mobile_improve_data(user)
        
        log_user_activity(
            user['email'], 
            'page_visit', 
            page='mobile_improve',
            details='Accessed improve page'
        )
        
        return render_template('mobile/improve.html', 
                              session_data=session_data, 
                              paddle_tips=improve_data.get('paddle_tips', []),
                              training_guide=improve_data.get('training_guide', {}))
        
    except Exception as e:
        print(f"Error serving improve page: {str(e)}")
        return redirect('/login')

@mobile_bp.route('/mobile/training-videos')
@login_required
def serve_mobile_training_videos():
    """Serve the mobile training videos page with YouTube-like interface"""
    try:
        user = session.get('user')
        if not user:
            return redirect('/login')
            
        session_data = {
            'user': user,
            'authenticated': True
        }
        
        # Load training videos from JSON file
        try:
            import os
            import json
            videos_path = os.path.join('data', 'leagues', 'all', 'improve_data', 'platform_tennis_videos_full_30.json')
            with open(videos_path, 'r', encoding='utf-8') as f:
                training_videos = json.load(f)
        except Exception as e:
            print(f"Error loading training videos: {str(e)}")
            training_videos = []
        
        log_user_activity(
            user['email'], 
            'page_visit', 
            page='mobile_training_videos',
            details='Accessed training videos library'
        )
        
        return render_template('mobile/training_videos.html', 
                              session_data=session_data,
                              training_videos=training_videos)
        
    except Exception as e:
        print(f"Error serving training videos page: {str(e)}")
        return redirect('/login')

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
        
        user_id = user.get('id')  # Add user_id extraction
        player_name = f"{user['first_name']} {user['last_name']}"
        series = user['series']

        # Get matches for the user's club/series using existing function (same as availability-calendar)
        matches = get_matches_for_user_club(user)
        
        # Get this user's availability for each match using existing function (same as availability-calendar)
        # FIXED: Pass user_id parameter for proper user-player associations
        availability = get_user_availability(player_name, matches, series, user_id)

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
        
        user_id = user.get('id')  # Add user_id extraction
        player_name = f"{user['first_name']} {user['last_name']}"
        series = user['series']

        # Get matches for the user's club/series using existing function
        matches = get_matches_for_user_club(user)
        
        # Get this user's availability for each match using existing function
        # FIXED: Pass user_id parameter for proper user-player associations
        availability = get_user_availability(player_name, matches, series, user_id)

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

@mobile_bp.route('/mobile/matchup-simulator')
@login_required
def serve_mobile_matchup_simulator():
    """Serve the mobile Matchup Simulator page"""
    try:
        # Get user's league ID and series for filtering
        user_league_id = session['user'].get('league_id')
        user_series = session['user'].get('series')
        user_club = session['user'].get('club')
        print(f"[DEBUG] serve_mobile_matchup_simulator: User league_id: '{user_league_id}', series: '{user_series}', club: '{user_club}'")
        
        # Get available teams for selection (filtered by user's series)
        available_teams = get_teams_for_selection(user_league_id, user_series, user_club)
        print(f"[DEBUG] serve_mobile_matchup_simulator: Found {len(available_teams)} teams in series '{user_series}' (all teams in this series)")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(session['user']['email'], 'page_visit', page='mobile_matchup_simulator')
        
        response = render_template('mobile/matchup_simulator.html', 
                             session_data=session_data,
                             available_teams=available_teams)
        
        # Add cache-busting headers
        from flask import make_response
        response = make_response(response)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
                             
    except Exception as e:
        print(f"Error serving mobile matchup simulator: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        return render_template('mobile/matchup_simulator.html', 
                             session_data=session_data,
                             available_teams=[],
                             error="Failed to load team data")

@mobile_bp.route('/api/run-simulation', methods=['POST'])
@login_required
def run_matchup_simulation():
    """API endpoint to run head-to-head simulation"""
    try:
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract team player IDs
        team_a_players = data.get('team_a_players', [])
        team_b_players = data.get('team_b_players', [])
        
        if len(team_a_players) != 2 or len(team_b_players) != 2:
            return jsonify({'error': 'Each team must have exactly 2 players'}), 400
        
        # Convert to integers
        try:
            team_a_players = [int(pid) for pid in team_a_players]
            team_b_players = [int(pid) for pid in team_b_players]
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid player IDs provided'}), 400
        
        # Get user's league ID for filtering
        user_league_id = session['user'].get('league_id')
        
        # Run the simulation
        simulator = AdvancedMatchupSimulator()
        result = simulator.simulate_matchup(team_a_players, team_b_players, user_league_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Log the simulation
        team_a_names = [p['name'] for p in result['team_a']['players']]
        team_b_names = [p['name'] for p in result['team_b']['players']]
        
        log_user_activity(
            session['user']['email'], 
            'simulation_run',
            page='mobile_matchup_simulator',
            details=f"Team A: {' & '.join(team_a_names)} vs Team B: {' & '.join(team_b_names)}"
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error running simulation: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Simulation failed. Please try again.'}), 500

@mobile_bp.route('/api/get-team-players/<team_name>')
@login_required
def get_team_players(team_name):
    """API endpoint to get players for a specific team"""
    try:
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Get user's league ID for filtering
        user_league_id = session['user'].get('league_id')
        print(f"[DEBUG] get_team_players: User league_id from session: '{user_league_id}' for team '{team_name}'")
        
        # Get players for the team
        players = get_players_by_team(team_name, user_league_id)
        print(f"[DEBUG] get_team_players: Found {len(players)} players for team '{team_name}' in league '{user_league_id}'")
        
        if not players:
            return jsonify({
                'success': False,
                'error': f'No players found for team {team_name}',
                'players': [],
                'team_name': team_name
            }), 404
        
        return jsonify({
            'success': True,
            'players': players,
            'team_name': team_name
        })
        
    except Exception as e:
        print(f"Error getting team players: {str(e)}")
        return jsonify({'error': 'Failed to get team players'}), 500

# Debug endpoint removed - new AdvancedMatchupSimulator uses sophisticated algorithms
# instead of the legacy debug functionality

@mobile_bp.route('/mobile/polls')
@login_required
def serve_mobile_polls():
    """Serve the mobile team polls management page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_polls')
    return render_template('mobile/team_polls.html', session_data=session_data)

@mobile_bp.route('/mobile/polls/<int:poll_id>')
def serve_mobile_poll_vote(poll_id):
    """Serve the mobile poll voting page (public link)"""
    # Check if user is logged in
    if 'user' not in session:
        # Store the poll URL for redirect after login
        session['redirect_after_login'] = f'/mobile/polls/{poll_id}'
        return redirect('/login')
    
    session_data = {
        'user': session['user'],
        'authenticated': True,
        'poll_id': poll_id
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_poll_vote', details=f'Poll {poll_id}')
    return render_template('mobile/poll_vote.html', session_data=session_data, poll_id=poll_id) 