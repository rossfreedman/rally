"""
Dashboard service module - handles activity monitoring dashboard data
This module provides functions for comprehensive activity tracking and analytics.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from database_utils import execute_query, execute_query_one, execute_update
from app.models.database_models import ActivityLog, Player, Team, User
from utils.logging import log_user_activity as legacy_log_user_activity
import traceback

def log_activity(
    action_type: str,
    action_description: str,
    user_id: Optional[int] = None,
    player_id: Optional[int] = None,
    team_id: Optional[int] = None,
    related_id: Optional[str] = None,
    related_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_data: Optional[Dict] = None
) -> bool:
    """
    Log a comprehensive activity entry
    
    Args:
        action_type: Type of action (e.g., 'login', 'match_created', 'poll_response')
        action_description: Human-readable description of the action
        user_id: ID of the user performing the action
        player_id: ID of the player associated with the action
        team_id: ID of the team associated with the action
        related_id: ID of related object (match_id, poll_id, etc.)
        related_type: Type of related object ('match', 'poll', etc.)
        ip_address: User's IP address
        user_agent: Browser/device information
        extra_data: Additional data as dictionary (will be JSON serialized)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Serialize extra_data to JSON if provided
        extra_data_json = json.dumps(extra_data) if extra_data else None
        
        # Insert into activity_log table
        execute_update("""
            INSERT INTO activity_log (
                id, action_type, action_description, user_id, player_id, team_id,
                related_id, related_type, ip_address, user_agent, extra_data, timestamp
            ) VALUES (
                %(id)s, %(action_type)s, %(action_description)s, %(user_id)s, %(player_id)s, %(team_id)s,
                %(related_id)s, %(related_type)s, %(ip_address)s, %(user_agent)s, %(extra_data)s, %(timestamp)s
            )
        """, {
            'id': str(uuid.uuid4()),
            'action_type': action_type,
            'action_description': action_description,
            'user_id': user_id,
            'player_id': player_id,
            'team_id': team_id,
            'related_id': related_id,
            'related_type': related_type,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'extra_data': extra_data_json,
            'timestamp': datetime.now()
        })
        
        return True
        
    except Exception as e:
        print(f"Error logging activity: {str(e)}")
        print(traceback.format_exc())
        return False

def get_recent_activities(limit: int = 50, filters: Optional[Dict] = None) -> List[Dict]:
    """
    Get recent activity timeline with optional filters
    
    Args:
        limit: Maximum number of activities to return
        filters: Dictionary with optional filters:
            - date_from: Start date filter
            - date_to: End date filter
            - action_type: Action type filter
            - team_id: Team filter
            - player_id: Player filter
    
    Returns:
        List of activity dictionaries
    """
    try:
        # Build WHERE clause based on filters
        where_clauses = []
        params = {'limit': limit}
        
        if filters:
            if filters.get('date_from'):
                where_clauses.append("ual.timestamp >= %(date_from)s")
                params['date_from'] = filters['date_from']
            
            if filters.get('date_to'):
                where_clauses.append("ual.timestamp <= %(date_to)s")
                params['date_to'] = filters['date_to']
            
            if filters.get('action_type'):
                where_clauses.append("ual.activity_type = %(action_type)s")
                params['action_type'] = filters['action_type']
            
            if filters.get('team_id'):
                where_clauses.append("t.id = %(team_id)s")
                params['team_id'] = filters['team_id']
            
            if filters.get('player_id'):
                where_clauses.append("p.id = %(player_id)s")
                params['player_id'] = filters['player_id']
        
        where_sql = " AND ".join(where_clauses)
        if where_sql:
            where_sql = "WHERE " + where_sql
        
        # Query the real user activity logs table
        activities = execute_query(f"""
            SELECT 
                ual.id,
                ual.activity_type as action_type,
                ual.details,
                ual.action,
                ual.page,
                ual.timestamp,
                ual.page as related_id,
                'page' as related_type,
                NULL as extra_data,
                u.first_name as user_first_name,
                u.last_name as user_last_name,
                ual.user_email as user_email,
                p.first_name as player_first_name,
                p.last_name as player_last_name,
                t.team_name,
                c.name as club_name,
                s.name as series_name
            FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            {' AND ' + ' AND '.join(where_clauses) if where_clauses else ''}
            ORDER BY ual.timestamp DESC
            LIMIT %(limit)s
        """, params)
        
        # Format activities for frontend
        formatted_activities = []
        for activity in activities:
            # Create descriptive action description
            action_description = create_activity_description(
                activity['action_type'],
                activity['page'],
                activity['details'],
                activity['action']
            )
            
            formatted_activity = {
                'id': str(activity['id']),
                'action_type': activity['action_type'],
                'action_description': action_description,
                'timestamp': activity['timestamp'].isoformat(),
                'related_id': activity['related_id'],
                'related_type': activity['related_type'],
                'user': None,
                'player': None,
                'team': None,
                'extra_data': json.loads(activity['extra_data']) if activity['extra_data'] else None
            }
            
            # Add user info if available
            if activity['user_first_name']:
                formatted_activity['user'] = {
                    'first_name': activity['user_first_name'],
                    'last_name': activity['user_last_name'],
                    'email': activity['user_email']
                }
            
            # Add player info if available
            if activity['player_first_name']:
                formatted_activity['player'] = {
                    'first_name': activity['player_first_name'],
                    'last_name': activity['player_last_name']
                }
            
            # Add team info if available
            if activity['team_name']:
                formatted_activity['team'] = {
                    'name': activity['team_name'],
                    'club_name': activity['club_name'],
                    'series_name': activity['series_name']
                }
            
            formatted_activities.append(formatted_activity)
        
        return formatted_activities
        
    except Exception as e:
        print(f"Error getting recent activities: {str(e)}")
        print(traceback.format_exc())
        return []

def get_activity_heatmap_data(days: int = 30) -> List[Dict]:
    """
    Get activity heatmap data for the specified number of days
    
    Args:
        days: Number of days to include in heatmap
    
    Returns:
        List of dictionaries with date and activity count
    """
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        heatmap_data = execute_query("""
            SELECT 
                DATE(ual.timestamp) as activity_date,
                COUNT(*) as activity_count
            FROM user_activity_logs ual
            WHERE DATE(ual.timestamp) >= %(start_date)s
            AND DATE(ual.timestamp) <= %(end_date)s
            AND ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            GROUP BY DATE(ual.timestamp)
            ORDER BY activity_date DESC
        """, {
            'start_date': start_date,
            'end_date': end_date
        })
        
        # Format for frontend
        formatted_data = []
        for item in heatmap_data:
            formatted_data.append({
                'date': item['activity_date'].isoformat(),
                'count': item['activity_count']
            })
        
        return formatted_data
        
    except Exception as e:
        print(f"Error getting heatmap data: {str(e)}")
        print(traceback.format_exc())
        return []

def get_top_active_players(limit: int = 10) -> List[Dict]:
    """
    Get top players by activity count
    
    Args:
        limit: Number of top players to return
    
    Returns:
        List of player dictionaries with activity counts
    """
    try:
        top_players = execute_query("""
            SELECT 
                p.id,
                p.first_name,
                p.last_name,
                c.name as club_name,
                s.name as series_name,
                COUNT(ual.id) as activity_count,
                COUNT(CASE WHEN ual.activity_type = 'login' THEN 1 END) as login_count,
                COUNT(CASE WHEN ual.activity_type = 'score_submitted' THEN 1 END) as matches_created,
                COUNT(CASE WHEN ual.activity_type = 'poll_response' THEN 1 END) as poll_responses,
                MAX(ual.timestamp) as last_activity
            FROM players p
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            LEFT JOIN users u ON upa.user_id = u.id AND upa.is_primary = true
            LEFT JOIN user_activity_logs ual ON u.email = ual.user_email
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE ual.id IS NOT NULL AND ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            GROUP BY p.id, p.first_name, p.last_name, c.name, s.name
            ORDER BY activity_count DESC
            LIMIT %(limit)s
        """, {'limit': limit})
        
        # Format for frontend
        formatted_players = []
        for player in top_players:
            formatted_players.append({
                'id': player['id'],
                'first_name': player['first_name'],
                'last_name': player['last_name'],
                'club_name': player['club_name'],
                'series_name': player['series_name'],
                'activity_count': player['activity_count'],
                'login_count': player['login_count'],
                'matches_created': player['matches_created'],
                'poll_responses': player['poll_responses'],
                'last_activity': player['last_activity'].isoformat() if player['last_activity'] else None
            })
        
        return formatted_players
        
    except Exception as e:
        print(f"Error getting top active players: {str(e)}")
        print(traceback.format_exc())
        return []

def get_activity_stats() -> Dict[str, Any]:
    """
    Get overall activity statistics
    
    Returns:
        Dictionary with various activity statistics
    """
    try:
        # Get basic counts
        total_activities = execute_query_one("""
            SELECT COUNT(*) as count FROM user_activity_logs
            WHERE timestamp IS NOT NULL
            AND NOT (page = 'admin_dashboard' AND details = 'Admin accessed activity monitoring dashboard')
        """)['count']
        
        # Get today's activities
        today_activities = execute_query_one("""
            SELECT COUNT(*) as count FROM user_activity_logs
            WHERE DATE(timestamp) = CURRENT_DATE
            AND timestamp IS NOT NULL
            AND NOT (page = 'admin_dashboard' AND details = 'Admin accessed activity monitoring dashboard')
        """)['count']
        
        # Get activities by type
        activity_types = execute_query("""
            SELECT 
                activity_type as action_type,
                COUNT(*) as count
            FROM user_activity_logs
            WHERE timestamp IS NOT NULL
            AND NOT (page = 'admin_dashboard' AND details = 'Admin accessed activity monitoring dashboard')
            GROUP BY activity_type
            ORDER BY count DESC
            LIMIT 10
        """)
        
        # Get unique users active today
        active_users_today = execute_query_one("""
            SELECT COUNT(DISTINCT user_email) as count FROM user_activity_logs
            WHERE DATE(timestamp) = CURRENT_DATE
            AND timestamp IS NOT NULL
            AND user_email IS NOT NULL
            AND NOT (page = 'admin_dashboard' AND details = 'Admin accessed activity monitoring dashboard')
        """)['count']
        
        return {
            'total_activities': total_activities,
            'today_activities': today_activities,
            'active_users_today': active_users_today,
            'activity_types': [
                {'type': item['action_type'], 'count': item['count']}
                for item in activity_types
            ]
        }
        
    except Exception as e:
        print(f"Error getting activity stats: {str(e)}")
        print(traceback.format_exc())
        return {
            'total_activities': 0,
            'today_activities': 0,
            'active_users_today': 0,
            'activity_types': []
        }

def get_player_activity_history(player_id: int, limit: int = 100) -> List[Dict]:
    """
    Get activity history for a specific player
    
    Args:
        player_id: ID of the player
        limit: Maximum number of activities to return
    
    Returns:
        List of activity dictionaries for the player
    """
    try:
        activities = execute_query("""
            SELECT 
                ual.id,
                ual.activity_type as action_type,
                ual.details,
                ual.action,
                ual.page,
                ual.timestamp,
                ual.page as related_id,
                'page' as related_type,
                NULL as extra_data,
                t.team_name,
                c.name as club_name,
                s.name as series_name
            FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.id = %(player_id)s AND ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            ORDER BY ual.timestamp DESC
            LIMIT %(limit)s
        """, {'player_id': player_id, 'limit': limit})
        
        # Format activities
        formatted_activities = []
        for activity in activities:
            # Create descriptive action description
            action_description = create_activity_description(
                activity['action_type'],
                activity['page'],
                activity['details'],
                activity['action']
            )
            
            formatted_activity = {
                'id': str(activity['id']),
                'action_type': activity['action_type'],
                'action_description': action_description,
                'timestamp': activity['timestamp'].isoformat(),
                'related_id': activity['related_id'],
                'related_type': activity['related_type'],
                'extra_data': json.loads(activity['extra_data']) if activity['extra_data'] else None,
                'team': None
            }
            
            if activity['team_name']:
                formatted_activity['team'] = {
                    'name': activity['team_name'],
                    'club_name': activity['club_name'],
                    'series_name': activity['series_name']
                }
            
            formatted_activities.append(formatted_activity)
        
        return formatted_activities
        
    except Exception as e:
        print(f"Error getting player activity history: {str(e)}")
        print(traceback.format_exc())
        return []

def get_team_activity_history(team_id: int, limit: int = 100) -> List[Dict]:
    """
    Get activity history for a specific team
    
    Args:
        team_id: ID of the team
        limit: Maximum number of activities to return
    
    Returns:
        List of activity dictionaries for the team
    """
    try:
        activities = execute_query("""
            SELECT 
                ual.id,
                ual.activity_type as action_type,
                ual.details,
                ual.action,
                ual.page,
                ual.timestamp,
                ual.page as related_id,
                'page' as related_type,
                NULL as extra_data,
                u.first_name as user_first_name,
                u.last_name as user_last_name,
                p.first_name as player_first_name,
                p.last_name as player_last_name
            FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE t.id = %(team_id)s AND ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            ORDER BY ual.timestamp DESC
            LIMIT %(limit)s
        """, {'team_id': team_id, 'limit': limit})
        
        # Format activities
        formatted_activities = []
        for activity in activities:
            # Create descriptive action description
            action_description = create_activity_description(
                activity['action_type'],
                activity['page'],
                activity['details'],
                activity['action']
            )
            
            formatted_activity = {
                'id': str(activity['id']),
                'action_type': activity['action_type'],
                'action_description': action_description,
                'timestamp': activity['timestamp'].isoformat(),
                'related_id': activity['related_id'],
                'related_type': activity['related_type'],
                'extra_data': json.loads(activity['extra_data']) if activity['extra_data'] else None,
                'user': None,
                'player': None
            }
            
            # Add user info if available
            if activity['user_first_name']:
                formatted_activity['user'] = {
                    'first_name': activity['user_first_name'],
                    'last_name': activity['user_last_name']
                }
            
            # Add player info if available
            if activity['player_first_name']:
                formatted_activity['player'] = {
                    'first_name': activity['player_first_name'],
                    'last_name': activity['player_last_name']
                }
            
            formatted_activities.append(formatted_activity)
        
        return formatted_activities
        
    except Exception as e:
        print(f"Error getting team activity history: {str(e)}")
        print(traceback.format_exc())
        return []

def get_filter_options() -> Dict[str, List]:
    """
    Get options for dashboard filters
    
    Returns:
        Dictionary with filter options for action types, teams, etc.
    """
    try:
        # Get unique action types
        action_types = execute_query("""
            SELECT DISTINCT activity_type as action_type
            FROM user_activity_logs
            WHERE timestamp IS NOT NULL
            AND NOT (page = 'admin_dashboard' AND details = 'Admin accessed activity monitoring dashboard')
            ORDER BY activity_type
        """)
        
        # Get teams with activity (through player associations)
        teams = execute_query("""
            SELECT DISTINCT t.id, t.team_name, c.name as club_name, s.name as series_name
            FROM teams t
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN users u ON upa.user_id = u.id AND upa.is_primary = true
            JOIN user_activity_logs ual ON u.email = ual.user_email
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            WHERE ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            ORDER BY t.team_name
        """)
        
        return {
            'action_types': [item['action_type'] for item in action_types],
            'teams': [
                {
                    'id': team['id'],
                    'name': team['team_name'],
                    'club_name': team['club_name'],
                    'series_name': team['series_name']
                }
                for team in teams
            ]
        }
        
    except Exception as e:
        print(f"Error getting filter options: {str(e)}")
        print(traceback.format_exc())
        return {
            'action_types': [],
            'teams': []
        }

def log_page_visit(user_email: str, page: str, user_id: Optional[int] = None, player_id: Optional[int] = None, team_id: Optional[int] = None, details: Optional[str] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    """
    Helper function to log page visits with both legacy and comprehensive activity logging
    
    Args:
        user_email: User's email for legacy logging
        page: Page identifier 
        user_id: User ID for comprehensive logging
        player_id: Player ID if available
        team_id: Team ID if available
        details: Additional details for legacy logging
        ip_address: User's IP address
        user_agent: User's browser/device info
    """
    try:
        # Legacy logging (existing system)
        legacy_log_user_activity(user_email, 'page_visit', page=page, details=details)
        
        # Comprehensive logging (new system)
        if user_id:  # Only log comprehensive if we have user_id
            page_display_name = format_page_name(page)
            log_activity(
                action_type='page_visit',
                action_description=f"Visited {page_display_name} page",
                user_id=user_id,
                player_id=player_id,
                team_id=team_id,
                related_id=None,
                related_type=None,
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data={
                    'page': page,
                    'page_category': get_page_category(page),
                    'details': details
                }
            )
    except Exception as e:
        print(f"Error logging page visit for {page}: {str(e)}")

def log_user_action(action_type: str, action_description: str, user_email: str, user_id: Optional[int] = None, player_id: Optional[int] = None, team_id: Optional[int] = None, related_id: Optional[str] = None, related_type: Optional[str] = None, legacy_action: Optional[str] = None, legacy_details: Optional[str] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None, extra_data: Optional[Dict] = None):
    """
    Helper function to log user actions with both legacy and comprehensive activity logging
    
    Args:
        action_type: Type of action for comprehensive logging
        action_description: Description for comprehensive logging
        user_email: User's email for legacy logging
        user_id: User ID for comprehensive logging
        player_id: Player ID if available
        team_id: Team ID if available
        related_id: Related object ID
        related_type: Type of related object
        legacy_action: Action type for legacy logging (defaults to action_type)
        legacy_details: Details for legacy logging (defaults to action_description)
        ip_address: User's IP address
        user_agent: User's browser/device info
        extra_data: Additional data for comprehensive logging
    """
    try:
        # Legacy logging (existing system)
        legacy_log_user_activity(
            user_email, 
            legacy_action or action_type,
            action=legacy_action or action_type,
            details=legacy_details or action_description
        )
        
        # Comprehensive logging (new system)
        if user_id:  # Only log comprehensive if we have user_id
            log_activity(
                action_type=action_type,
                action_description=action_description,
                user_id=user_id,
                player_id=player_id,
                team_id=team_id,
                related_id=related_id,
                related_type=related_type,
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data=extra_data
            )
    except Exception as e:
        print(f"Error logging user action {action_type}: {str(e)}")

def create_activity_description(activity_type: str, page: str, details: str, action: str) -> str:
    """Create descriptive activity descriptions based on activity type and context"""
    
    # Handle page visits
    if activity_type == 'page_visit':
        if page:
            page_name = format_page_name(page)
            return f"Visited {page_name}"
        return "Visited a page"
    
    # Handle authentication
    elif activity_type == 'auth':
        if details and 'Login successful' in details:
            return "Logged in"
        elif details and 'logout' in details.lower():
            return "Logged out"
        return "Authentication activity"
    
    # Handle availability updates
    elif activity_type == 'availability_update':
        if details and 'Set availability for' in details:
            # Extract date from details if possible
            import re
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', details)
            if date_match:
                date = date_match.group(1)
                return f"Updated availability for {date}"
        return "Updated availability"
    
    # Handle admin actions
    elif activity_type == 'admin_action':
        if details:
            if 'Started scraping' in details:
                return "Started data scraping"
            elif 'Cleared stuck ETL processes' in details:
                return "Cleared ETL processes"
            elif 'Deleted poll' in details:
                return "Deleted a poll"
            elif 'Updated user' in details:
                return "Updated user account"
            elif 'Created poll' in details:
                return "Created a poll"
        return "Performed admin action"
    
    # Handle polls
    elif activity_type == 'poll_voted':
        return "Voted in team poll"
    elif activity_type == 'poll_created':
        return "Created team poll"
    
    # Handle AI interactions
    elif activity_type == 'ai_chat':
        return "Asked AI a question"
    
    # Handle simulations
    elif activity_type == 'simulation_run':
        return "Ran matchup simulation"
    
    # Handle player search
    elif activity_type == 'player_search':
        return "Searched for players"
    
    # Handle season tracking
    elif activity_type == 'update_season_tracking':
        return "Updated season tracking"
    
    # Handle practice times
    elif activity_type == 'practice_times_added':
        return "Added practice times"
    
    # Handle debug activities
    elif activity_type == 'debug_partnership':
        return "Debugged partnership data"
    
    # Fallback for unknown activity types
    else:
        if details:
            return details
        elif action:
            return action.replace('_', ' ').title()
        else:
            return f"{activity_type.replace('_', ' ').title()} activity"

def format_page_name(page: str) -> str:
    """Format page identifier into a readable display name"""
    page_names = {
        # Mobile App Pages
        'mobile_home': 'Home Page',
        'mobile_matches': 'Matches',
        'mobile_rankings': 'Rankings', 
        'mobile_profile': 'Profile',
        'mobile_view_schedule': 'Schedule',
        'mobile_analyze_me': 'Analyze Me',
        'mobile_my_team': 'My Team Page',
        'mobile_settings': 'Settings',
        'mobile_my_series': 'My Series Page',
        'mobile_teams_players': 'Teams & Players',
        'mobile_player_search': 'Player Search',
        'mobile_my_club': 'My Club Page',
        'mobile_player_stats': 'Player Stats',
        'mobile_email_team': 'Email Team',
        'mobile_practice_times': 'Practice Times',
        'mobile_availability': 'Availability',
        'mobile_availability_calendar': 'Availability Calendar',
        'mobile_all_team_availability': 'Team Availability',
        'mobile_team_schedule': 'Team Schedule',
        'mobile_matchup_simulator': 'Matchup Simulator',
        'mobile_polls': 'Team Polls',
        'mobile_poll_vote': 'Poll Vote',
        'mobile_ask_ai': 'Ask AI',
        'mobile_find_subs': 'Find Subs',
        'mobile_find_people_to_play': 'Find People to Play',
        'mobile_lineup': 'Lineup',
        'mobile_lineup_escrow': 'Lineup Escrow',
        'mobile_improve': 'Improve Game',
        'mobile_training_videos': 'Training Videos',
        'mobile_reserve_court': 'Reserve Court',
        'mobile_player_detail': 'Player Detail',
        
        # Utility Pages
        'track_byes_courts': 'Track Byes & Courts',
        'contact_sub': 'Contact Sub',
        'player_detail': 'Player Detail',
        'pti_vs_opponents_analysis': 'PTI vs Opponents Analysis',
        
        # Admin Pages
        'admin': 'Admin Dashboard',
        'admin_users': 'Admin Users',
        'admin_leagues': 'Admin Leagues',
        'admin_clubs': 'Admin Clubs',
        'admin_series': 'Admin Series',
        'admin_etl': 'Admin ETL',
        'admin_user_activity': 'Admin User Activity',
        'admin_dashboard': 'Admin Activity Dashboard'
    }
    
    return page_names.get(page, page.replace('_', ' ').title())

def get_page_category(page: str) -> str:
    """Get the category of a page for analytics grouping"""
    if page.startswith('admin'):
        return 'admin'
    elif page.startswith('mobile'):
        return 'mobile'
    elif 'match' in page.lower():
        return 'matches'
    elif 'team' in page.lower():
        return 'team'
    elif 'player' in page.lower():
        return 'player'
    elif any(word in page.lower() for word in ['availability', 'schedule']):
        return 'scheduling'
    elif any(word in page.lower() for word in ['stats', 'analyze', 'ranking']):
        return 'analytics'
    else:
        return 'general' 