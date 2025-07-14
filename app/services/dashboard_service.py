"""
Dashboard service module - handles activity monitoring dashboard data
This module provides functions for comprehensive activity tracking and analytics.
"""

import json
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.models.database_models import ActivityLog, Player, Team, User
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity as legacy_log_user_activity


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
    extra_data: Optional[Dict] = None,
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
        execute_update(
            """
            INSERT INTO activity_log (
                id, action_type, action_description, user_id, player_id, team_id,
                related_id, related_type, ip_address, user_agent, extra_data, timestamp
            ) VALUES (
                %(id)s, %(action_type)s, %(action_description)s, %(user_id)s, %(player_id)s, %(team_id)s,
                %(related_id)s, %(related_type)s, %(ip_address)s, %(user_agent)s, %(extra_data)s, %(timestamp)s
            )
        """,
            {
                "id": str(uuid.uuid4()),
                "action_type": action_type,
                "action_description": action_description,
                "user_id": user_id,
                "player_id": player_id,
                "team_id": team_id,
                "related_id": related_id,
                "related_type": related_type,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "extra_data": extra_data_json,
                "timestamp": datetime.now(),
            },
        )

        return True

    except Exception as e:
        print(f"Error logging activity: {str(e)}")
        print(traceback.format_exc())
        return False


def get_recent_activities(
    limit: int = 50, filters: Optional[Dict] = None
) -> List[Dict]:
    """
    Get recent activities with comprehensive filtering options

    Args:
        limit: Maximum number of activities to return
        filters: Dictionary of filter criteria
            - date_from: Start date (YYYY-MM-DD format)
            - date_to: End date (YYYY-MM-DD format)  
            - action_type: Activity type to filter by
            - team_id: Team ID to filter by
            - player_id: Player ID to filter by
            - exclude_impersonated: Boolean to exclude impersonated activities
            - exclude_admin: Boolean to exclude admin activities

    Returns:
        List of activity dictionaries with formatted data
    """
    try:
        if filters is None:
            filters = {}

        # Build WHERE clauses based on filters
        where_clauses = []
        params = {"limit": limit}

        # Base exclusions
        where_clauses.append("ual.timestamp IS NOT NULL")
        where_clauses.append("NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')")
        
        # Admin exclusion (default: True)
        if filters.get('exclude_admin', True):
            where_clauses.append("NOT (u.is_admin = true AND ual.user_email = %(admin_email)s)")
            params["admin_email"] = 'rossfreedman@gmail.com'
        
        # Impersonation exclusion (default: False, so users can choose)
        if filters.get('exclude_impersonated', False):
            where_clauses.append("NOT (ual.details LIKE %(impersonation_pattern)s OR ual.action LIKE %(impersonation_pattern)s)")
            params["impersonation_pattern"] = '%impersonation%'

        # Date range filters
        if filters.get("date_from"):
            where_clauses.append("DATE(ual.timestamp) >= %(date_from)s")
            params["date_from"] = filters["date_from"]

        if filters.get("date_to"):
            where_clauses.append("DATE(ual.timestamp) <= %(date_to)s")
            params["date_to"] = filters["date_to"]

        # Action type filter
        if filters.get("action_type"):
            where_clauses.append("ual.activity_type = %(action_type)s")
            params["action_type"] = filters["action_type"]

        # Team filter
        if filters.get("team_id"):
            where_clauses.append("t.id = %(team_id)s")
            params["team_id"] = filters["team_id"]

        # Player filter
        if filters.get("player_id"):
            where_clauses.append("p.id = %(player_id)s")
            params["player_id"] = filters["player_id"]

        # Build the complete query
        where_sql = " AND ".join(where_clauses)

        activities = execute_query(
            f"""
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
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE {where_sql}
            ORDER BY ual.timestamp DESC
            LIMIT %(limit)s
        """,
            params,
        )

        # Format activities for frontend
        formatted_activities = []
        for activity in activities:
            # Create enhanced description for registration activities
            description = activity["details"] or f"{activity['action_type'].replace('_', ' ').title()} activity"
            
            # Handle registration activities with enhanced descriptions
            if activity["action_type"] == "registration_successful":
                # Try to parse details for enhanced description
                try:
                    if activity["details"]:
                        import json
                        details = json.loads(activity["details"])
                        if details.get("player_data"):
                            player_data = details["player_data"]
                            player_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
                            club = player_data.get("club_name", "Unknown")
                            series = player_data.get("series_name", "Unknown")
                            team_assigned = details.get("team_assigned", False)
                            
                            description = f"✅ Registration successful - Linked to player {player_name} ({club} - {series})"
                            if team_assigned:
                                description += " with team assignment"
                            else:
                                description += " (no team assigned)"
                except:
                    description = "✅ Registration successful"
                    
            elif activity["action_type"] == "registration_failed":
                # Try to parse details for enhanced description
                try:
                    if activity["details"]:
                        import json
                        details = json.loads(activity["details"])
                        reason = details.get("reason", "Unknown error")
                        action = activity.get("action", "unknown_failure")
                        
                        if action == "player_id_linking_failed":
                            lookup_attempt = details.get("lookup_attempt", {})
                            name = f"{lookup_attempt.get('first_name', '')} {lookup_attempt.get('last_name', '')}".strip()
                            club = lookup_attempt.get("club_name", "Unknown")
                            series = lookup_attempt.get("series_name", "Unknown")
                            description = f"❌ Registration failed - Player ID linking failed for {name} ({club} - {series})"
                            
                        elif action == "security_issue_player_id_claimed":
                            player_id = details.get("player_id", "Unknown")
                            existing_user = details.get("existing_user_email", "Unknown")
                            description = f"🚨 Security issue - Player ID {player_id[:15]}... already claimed by {existing_user}"
                            
                        elif action == "duplicate_email":
                            description = f"❌ Registration failed - Duplicate email address"
                            
                        elif action == "missing_required_fields":
                            provided_data = details.get("provided_data", {})
                            missing_fields = []
                            if not provided_data.get("league_id"): missing_fields.append("league")
                            if not provided_data.get("club_name"): missing_fields.append("club")
                            if not provided_data.get("series_name"): missing_fields.append("series")
                            description = f"❌ Registration failed - Missing required fields: {', '.join(missing_fields)}"
                            
                        elif action == "player_record_not_found":
                            player_id = details.get("player_id", "Unknown")
                            description = f"❌ Registration failed - Player record not found for ID {player_id[:15]}..."
                            
                        elif action == "player_lookup_exception":
                            error = details.get("error", "Unknown error")
                            description = f"❌ Registration failed - Player lookup exception: {error[:50]}..."
                            
                        else:
                            description = f"❌ Registration failed - {reason}"
                except:
                    description = "❌ Registration failed"

            formatted_activities.append({
                "id": activity["id"],
                "action_type": activity["action_type"],
                "action_description": description,
                "timestamp": activity["timestamp"].isoformat() if activity["timestamp"] else None,
                "user": {
                    "first_name": activity["user_first_name"],
                    "last_name": activity["user_last_name"],
                    "email": activity["user_email"],
                },
                "player_name": f"{activity['player_first_name'] or ''} {activity['player_last_name'] or ''}".strip() if activity['player_first_name'] else None,
                "team_name": activity["team_name"],
                "club_name": activity["club_name"],
                "series_name": activity["series_name"],
                "related_id": activity["related_id"],
                "related_type": activity["related_type"],
            })

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

        heatmap_data = execute_query(
            """
            SELECT 
                DATE(ual.timestamp) as activity_date,
                COUNT(*) as activity_count
            FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            WHERE DATE(ual.timestamp) >= %(start_date)s
            AND DATE(ual.timestamp) <= %(end_date)s
            AND ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            AND NOT (u.is_admin = true AND ual.user_email = 'rossfreedman@gmail.com')
            GROUP BY DATE(ual.timestamp)
            ORDER BY activity_date DESC
        """,
            {"start_date": start_date, "end_date": end_date},
        )

        # Format for frontend
        formatted_data = []
        for item in heatmap_data:
            formatted_data.append(
                {
                    "date": item["activity_date"].isoformat(),
                    "count": item["activity_count"],
                }
            )

        return formatted_data

    except Exception as e:
        print(f"Error getting heatmap data: {str(e)}")
        print(traceback.format_exc())
        return []


def get_top_active_players(limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict]:
    """
    Get top users by activity count (aggregated by user, not individual player records)

    Args:
        limit: Number of top users to return
        filters: Dictionary with filtering options (exclude_impersonated, exclude_admin)

    Returns:
        List of user dictionaries with activity counts
    """
    try:
        # Handle filters
        if filters is None:
            filters = {"exclude_impersonated": False, "exclude_admin": False}
        
        exclude_impersonated_filter = filters.get("exclude_impersonated", False)
        exclude_admin_filter = filters.get("exclude_admin", False)
        
        # Build exclusion clauses
        base_exclusions = """
            WHERE ual.id IS NOT NULL AND ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
        """
        
        # Add filtering exclusions
        additional_exclusions = []
        
        if exclude_impersonated_filter:
            additional_exclusions.append("NOT (ual.details LIKE '%impersonation%' OR ual.action LIKE '%impersonation%')")
            
        if exclude_admin_filter:
            additional_exclusions.append("NOT (u.is_admin = true)")
        
        # Combine all exclusions
        all_exclusions = base_exclusions
        if additional_exclusions:
            all_exclusions += " AND " + " AND ".join(additional_exclusions)
        
        top_users = execute_query(
            f"""
            SELECT 
                u.id as user_id,
                u.first_name,
                u.last_name,
                -- Get primary club/series from user's league_context or most recent association
                COALESCE(
                    (SELECT c.name FROM user_player_associations upa 
                     JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                     JOIN clubs c ON p.club_id = c.id 
                     WHERE upa.user_id = u.id AND (p.league_id = u.league_context OR u.league_context IS NULL)
                     ORDER BY CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END, upa.created_at DESC 
                     LIMIT 1),
                    'No Club'
                ) as club_name,
                COALESCE(
                    (SELECT s.name FROM user_player_associations upa 
                     JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                     JOIN series s ON p.series_id = s.id 
                     WHERE upa.user_id = u.id AND (p.league_id = u.league_context OR u.league_context IS NULL)
                     ORDER BY CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END, upa.created_at DESC 
                     LIMIT 1),
                    'No Series'
                ) as series_name,
                COUNT(ual.id) as activity_count,
                COUNT(CASE WHEN ual.activity_type = 'login' THEN 1 END) as login_count,
                COUNT(CASE WHEN ual.activity_type = 'score_submitted' THEN 1 END) as matches_created,
                COUNT(CASE WHEN ual.activity_type = 'poll_response' THEN 1 END) as poll_responses,
                MAX(ual.timestamp) as last_activity
            FROM users u
            JOIN user_activity_logs ual ON u.email = ual.user_email
            {all_exclusions}
            GROUP BY u.id, u.first_name, u.last_name, u.league_context
            ORDER BY activity_count DESC
            LIMIT %(limit)s
        """,
            {"limit": limit},
        )

        # Format for frontend
        formatted_users = []
        for user in top_users:
            formatted_users.append(
                {
                    "id": user["user_id"],
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "club_name": user["club_name"],
                    "series_name": user["series_name"],
                    "activity_count": user["activity_count"],
                    "login_count": user["login_count"],
                    "matches_created": user["matches_created"],
                    "poll_responses": user["poll_responses"],
                    "last_activity": (
                        user["last_activity"].isoformat()
                        if user["last_activity"]
                        else None
                    ),
                }
            )

        return formatted_users

    except Exception as e:
        print(f"Error getting top active users: {str(e)}")
        print(traceback.format_exc())
        return []


def get_activity_stats(exclude_impersonated: bool = False, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get overall activity statistics

    Args:
        exclude_impersonated: Whether to exclude impersonated activities from stats (deprecated, use filters)
        filters: Dictionary with filtering options (exclude_impersonated, exclude_admin)

    Returns:
        Dictionary with various activity statistics
    """
    try:
        # Handle both old and new parameter patterns for backward compatibility
        if filters is None:
            filters = {"exclude_impersonated": exclude_impersonated, "exclude_admin": False}
        
        # Extract filter values
        exclude_impersonated_filter = filters.get("exclude_impersonated", exclude_impersonated)
        exclude_admin_filter = filters.get("exclude_admin", False)
        
        # Build base exclusion clauses
        base_exclusions = """
            WHERE ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
        """
        
        # Add filtering exclusions
        additional_exclusions = []
        
        if exclude_impersonated_filter:
            additional_exclusions.append("NOT (ual.details LIKE '%impersonation%' OR ual.action LIKE '%impersonation%')")
            
        if exclude_admin_filter:
            additional_exclusions.append("NOT (u.is_admin = true)")
        
        # Combine all exclusions
        all_exclusions = base_exclusions
        if additional_exclusions:
            all_exclusions += " AND " + " AND ".join(additional_exclusions)

        # Get basic counts
        total_activities = execute_query_one(
            f"""
            SELECT COUNT(*) as count FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            {all_exclusions}
        """
        )["count"]

        # Get today's activities
        today_activities = execute_query_one(
            f"""
            SELECT COUNT(*) as count FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            {all_exclusions}
            AND DATE(ual.timestamp) = CURRENT_DATE
        """
        )["count"]

        # Get activities by type
        activity_types = execute_query(
            f"""
            SELECT 
                ual.activity_type as action_type,
                COUNT(*) as count
            FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            {all_exclusions}
            GROUP BY ual.activity_type
            ORDER BY count DESC
            LIMIT 10
        """
        )

        # Get unique users active today - need to build custom query for this one
        active_users_exclusions = """
            WHERE DATE(ual.timestamp) = CURRENT_DATE
            AND ual.timestamp IS NOT NULL
            AND ual.user_email IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
        """
        
        # Add filtering exclusions to active users query
        if exclude_impersonated_filter:
            active_users_exclusions += " AND NOT (ual.details LIKE '%impersonation%' OR ual.action LIKE '%impersonation%')"
            
        if exclude_admin_filter:
            active_users_exclusions += " AND NOT (u.is_admin = true)"
        
        active_users_today = execute_query_one(
            f"""
            SELECT COUNT(DISTINCT ual.user_email) as count FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            {active_users_exclusions}
        """
        )["count"]

        return {
            "total_activities": total_activities,
            "today_activities": today_activities,
            "active_users_today": active_users_today,
            "activity_types": [
                {"type": item["action_type"], "count": item["count"]}
                for item in activity_types
            ],
        }

    except Exception as e:
        print(f"Error getting activity stats: {str(e)}")
        print(traceback.format_exc())
        return {
            "total_activities": 0,
            "today_activities": 0,
            "active_users_today": 0,
            "activity_types": [],
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
        activities = execute_query(
            """
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
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.id = %(player_id)s AND ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            ORDER BY ual.timestamp DESC
            LIMIT %(limit)s
        """,
            {"player_id": player_id, "limit": limit},
        )

        # Format activities
        formatted_activities = []
        for activity in activities:
            # Create descriptive action description
            action_description = create_activity_description(
                activity["action_type"],
                activity["page"],
                activity["details"],
                activity["action"],
            )

            formatted_activity = {
                "id": str(activity["id"]),
                "action_type": activity["action_type"],
                "action_description": action_description,
                "timestamp": activity["timestamp"].isoformat(),
                "related_id": activity["related_id"],
                "related_type": activity["related_type"],
                "extra_data": (
                    json.loads(activity["extra_data"])
                    if activity["extra_data"]
                    else None
                ),
                "team": None,
            }

            if activity["team_name"]:
                formatted_activity["team"] = {
                    "name": activity["team_name"],
                    "club_name": activity["club_name"],
                    "series_name": activity["series_name"],
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
        activities = execute_query(
            """
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
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE t.id = %(team_id)s AND ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            ORDER BY ual.timestamp DESC
            LIMIT %(limit)s
        """,
            {"team_id": team_id, "limit": limit},
        )

        # Format activities
        formatted_activities = []
        for activity in activities:
            # Create descriptive action description
            action_description = create_activity_description(
                activity["action_type"],
                activity["page"],
                activity["details"],
                activity["action"],
            )

            formatted_activity = {
                "id": str(activity["id"]),
                "action_type": activity["action_type"],
                "action_description": action_description,
                "timestamp": activity["timestamp"].isoformat(),
                "related_id": activity["related_id"],
                "related_type": activity["related_type"],
                "extra_data": (
                    json.loads(activity["extra_data"])
                    if activity["extra_data"]
                    else None
                ),
                "user": None,
                "player": None,
            }

            # Add user info if available
            if activity["user_first_name"]:
                formatted_activity["user"] = {
                    "first_name": activity["user_first_name"],
                    "last_name": activity["user_last_name"],
                }

            # Add player info if available
            if activity["player_first_name"]:
                formatted_activity["player"] = {
                    "first_name": activity["player_first_name"],
                    "last_name": activity["player_last_name"],
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
        action_types = execute_query(
            """
            SELECT DISTINCT ual.activity_type as action_type
            FROM user_activity_logs ual
            LEFT JOIN users u ON ual.user_email = u.email
            WHERE ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            ORDER BY ual.activity_type
        """
        )

        # Get teams with activity (through player associations)
        teams = execute_query(
            """
            SELECT DISTINCT t.id, t.team_name, c.name as club_name, s.name as series_name
            FROM teams t
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN users u ON upa.user_id = u.id
            JOIN user_activity_logs ual ON u.email = ual.user_email
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            WHERE ual.timestamp IS NOT NULL
            AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
            ORDER BY t.team_name
        """
        )

        return {
            "action_types": [item["action_type"] for item in action_types],
            "teams": [
                {
                    "id": team["id"],
                    "name": team["team_name"],
                    "club_name": team["club_name"],
                    "series_name": team["series_name"],
                }
                for team in teams
            ],
        }

    except Exception as e:
        print(f"Error getting filter options: {str(e)}")
        print(traceback.format_exc())
        return {"action_types": [], "teams": []}


def log_page_visit(
    user_email: str,
    page: str,
    user_id: Optional[int] = None,
    player_id: Optional[int] = None,
    team_id: Optional[int] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    is_impersonating: Optional[bool] = None,
):
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
        is_impersonating: Whether this activity is from an impersonating admin
    """
    try:
        # Add impersonation info to details if applicable
        enhanced_details = details
        if is_impersonating:
            enhanced_details = f"[IMPERSONATION] {details}" if details else "[IMPERSONATION] Page visit"

        # Legacy logging (existing system)
        legacy_log_user_activity(user_email, "page_visit", page=page, details=enhanced_details)

        # Comprehensive logging (new system)
        if user_id:  # Only log comprehensive if we have user_id
            page_display_name = format_page_name(page)
            log_activity(
                action_type="page_visit",
                action_description=f"Visited {page_display_name} page",
                user_id=user_id,
                player_id=player_id,
                team_id=team_id,
                related_id=None,
                related_type=None,
                ip_address=ip_address,
                user_agent=user_agent,
                extra_data={
                    "page": page,
                    "page_category": get_page_category(page),
                    "details": enhanced_details,
                    "is_impersonating": is_impersonating,
                },
            )
    except Exception as e:
        print(f"Error logging page visit for {page}: {str(e)}")


def log_user_action(
    action_type: str,
    action_description: str,
    user_email: str,
    user_id: Optional[int] = None,
    player_id: Optional[int] = None,
    team_id: Optional[int] = None,
    related_id: Optional[str] = None,
    related_type: Optional[str] = None,
    legacy_action: Optional[str] = None,
    legacy_details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_data: Optional[Dict] = None,
):
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
            details=legacy_details or action_description,
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
                extra_data=extra_data,
            )
    except Exception as e:
        print(f"Error logging user action {action_type}: {str(e)}")


def create_activity_description(
    activity_type: str, page: str, details: str, action: str
) -> str:
    """Create descriptive activity descriptions based on activity type and context"""

    # Handle page visits
    if activity_type == "page_visit":
        # If details is a dict, try to extract a summary or join key fields
        import json
        try:
            details_obj = json.loads(details) if details and details.strip().startswith('{') else details
        except Exception:
            details_obj = details
        if details_obj:
            if isinstance(details_obj, dict):
                # Try to use a 'summary' or join key fields
                summary = details_obj.get('summary')
                if summary:
                    return summary
                # Join key fields for display
                key_fields = [str(v) for k, v in details_obj.items() if v and k not in ('is_impersonating', 'page', 'page_category')]
                if key_fields:
                    return ", ".join(key_fields)
            elif isinstance(details_obj, str) and details_obj.strip() and not details_obj.lower().startswith('visited'):
                return details_obj
        # Fallback to page name
        if page:
            page_name = format_page_name(page)
            return f"Visited {page_name}"
        return "Visited a page"

    # Handle authentication
    elif activity_type == "auth":
        if details and "Login successful" in details:
            return "Logged in"
        elif details and "logout" in details.lower():
            return "Logged out"
        return "Authentication activity"

    # Handle login specifically
    elif activity_type == "login":
        if details and "Login successful" in details:
            # Extract user name if available
            import re
            user_match = re.search(r"User (\w+ \w+) logged in", details)
            if user_match:
                return f"{user_match.group(1)} logged in"
        return "User logged in"

    # Handle availability updates
    elif activity_type == "availability_update":
        if details and "Set availability for" in details:
            # Extract date from details if possible
            import re

            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", details)
            if date_match:
                date = date_match.group(1)
                return f"Updated availability for {date}"
        return "Updated availability"

    # Handle admin actions
    elif activity_type == "admin_action":
        if details:
            if "Started scraping" in details:
                return "Started data scraping"
            elif "Cleared stuck ETL processes" in details:
                return "Cleared ETL processes"
            elif "Deleted poll" in details:
                return "Deleted a poll"
            elif "Updated user" in details:
                return "Updated user account"
            elif "Created poll" in details:
                return "Created a poll"
        return "Performed admin action"

    # Handle polls
    elif activity_type == "poll_voted":
        return "Voted in team poll"
    elif activity_type == "poll_created":
        return "Created team poll"

    # Handle AI interactions
    elif activity_type == "ai_chat":
        return "Asked AI a question"

    # Handle simulations
    elif activity_type == "simulation_run":
        return "Ran matchup simulation"

    # Handle player search
    elif activity_type == "player_search":
        import json
        try:
            details_obj = json.loads(details) if details and details.strip().startswith('{') else details
        except Exception:
            details_obj = details
        if details_obj:
            filters_applied = None
            if isinstance(details_obj, dict):
                filters_applied = details_obj.get('filters_applied')
            if filters_applied:
                return f"Player search ({filters_applied})"
            if isinstance(details_obj, str) and details_obj.strip():
                return details_obj
        return "Searched for players"

    # Handle season tracking
    elif activity_type == "update_season_tracking":
        return "Updated season tracking"

    # Handle practice times
    elif activity_type == "practice_times_added":
        return "Added practice times"

    # Handle debug activities
    elif activity_type == "debug_partnership":
        return "Debugged partnership data"

    # Handle match submissions
    elif activity_type == "score_submitted":
        return "Submitted match score"
    
    # Handle user registration
    elif activity_type == "user_registration":
        if details and "registered successfully" in details:
            import re
            user_match = re.search(r"New user (\w+ \w+) registered", details)
            if user_match:
                return f"{user_match.group(1)} registered"
        return "New user registered"
    
    # Handle lineup activities
    elif activity_type == "lineup_update":
        return "Updated team lineup"
    elif activity_type == "lineup_escrow":
        return "Accessed lineup escrow"
    
    # Handle reservation activities
    elif activity_type == "court_reservation":
        return "Reserved a court"
    
    # Handle team communication
    elif activity_type == "team_email":
        return "Sent team email"
    
    # Handle data synchronization
    elif activity_type == "data_sync":
        return "Synchronized data"
    
    # Handle system maintenance
    elif activity_type == "system_maintenance":
        return "System maintenance activity"

    # Fallback for unknown activity types
    else:
        if details:
            return details
        elif action:
            return action.replace("_", " ").title()
        else:
            return f"{activity_type.replace('_', ' ').title()} activity"


def format_page_name(page: str) -> str:
    """Format page identifier into a readable display name"""
    page_names = {
        # Mobile App Pages
        "mobile_home": "Home Page",
        "mobile_matches": "Matches",
        "mobile_rankings": "Rankings",
        "mobile_profile": "Profile",
        "mobile_view_schedule": "Schedule",
        "mobile_analyze_me": "Analyze Me",
        "mobile_my_team": "My Team Page",
        "mobile_settings": "Settings",
        "mobile_my_series": "My Series Page",
        "mobile_teams_players": "Teams & Players",
        "mobile_player_search": "Player Search",
        "mobile_my_club": "My Club Page",
        "mobile_player_stats": "Player Stats",
        "mobile_email_team": "Email Team",
        "mobile_practice_times": "Practice Times",
        "mobile_availability": "Availability",
        "mobile_availability_calendar": "Availability Calendar",
        "mobile_all_team_availability": "Team Availability",
        "mobile_team_schedule": "Team Schedule",
        "mobile_matchup_simulator": "Matchup Simulator",
        "mobile_polls": "Team Polls",
        "mobile_poll_vote": "Poll Vote",
        "mobile_ask_ai": "Ask AI",
        "mobile_find_subs": "Find Subs",
        "mobile_find_people_to_play": "Find People to Play",
        "mobile_lineup": "Lineup",
        "mobile_lineup_escrow": "Lineup Escrow",
        "mobile_improve": "Improve Game",
        "mobile_training_videos": "Training Videos",
        "mobile_reserve_court": "Reserve Court",
        "mobile_player_detail": "Player Detail",
        # Utility Pages
        "track_byes_courts": "Track Byes & Courts",
        "contact_sub": "Contact Sub",
        "player_detail": "Player Detail",
        "pti_vs_opponents_analysis": "PTI vs Opponents Analysis",
        # Admin Pages
        "admin": "Admin Dashboard",
        "admin_users": "Admin Users",
        "admin_leagues": "Admin Leagues",
        "admin_clubs": "Admin Clubs",
        "admin_series": "Admin Series",
        "admin_etl": "Admin ETL",
        "admin_user_activity": "Admin User Activity",
        "admin_dashboard": "Admin Activity Dashboard",
    }

    return page_names.get(page, page.replace("_", " ").title())


def get_page_category(page: str) -> str:
    """Get the category of a page for analytics grouping"""
    if page.startswith("admin"):
        return "admin"
    elif page.startswith("mobile"):
        return "mobile"
    elif "match" in page.lower():
        return "matches"
    elif "team" in page.lower():
        return "team"
    elif "player" in page.lower():
        return "player"
    elif any(word in page.lower() for word in ["availability", "schedule"]):
        return "scheduling"
    elif any(word in page.lower() for word in ["stats", "analyze", "ranking"]):
        return "analytics"
    else:
        return "general"
