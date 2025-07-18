"""
Admin service module - handles all admin-related business logic
This module provides functions for user management, club/series administration, and user activity tracking.
"""

import os
import traceback

from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity


def get_all_users():
    """Get all registered users with their club and series information, sorted by most recent activity"""
    try:
        users = execute_query(
            """
            SELECT DISTINCT ON (u.id) 
                u.id, u.first_name, u.last_name, u.email, u.last_login, u.created_at,
                c.name as club_name, s.name as series_name,
                -- Check for activity in past 24 hours
                CASE 
                    WHEN (ual.recent_activity_count > 0 OR al.recent_activity_count > 0) THEN true 
                    ELSE false 
                END as has_recent_activity,
                COALESCE(ual.recent_activity_count, 0) + COALESCE(al.recent_activity_count, 0) as recent_activity_count,
                -- Get the most recent activity timestamp from either system
                GREATEST(
                    COALESCE(ual.latest_activity, '1970-01-01'::timestamp),
                    COALESCE(al.latest_activity, '1970-01-01'::timestamp),
                    COALESCE(u.last_login, '1970-01-01'::timestamp),
                    COALESCE(u.created_at, '1970-01-01'::timestamp)
                ) as most_recent_activity
            FROM users u
            LEFT JOIN (
                -- Get recent activity count and latest timestamp from legacy system
                SELECT 
                    user_email,
                    COUNT(*) as recent_activity_count,
                    MAX(timestamp) as latest_activity
                FROM user_activity_logs 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                GROUP BY user_email
            ) ual ON u.email = ual.user_email
            LEFT JOIN (
                -- Get recent activity count and latest timestamp from comprehensive system
                SELECT 
                    user_id,
                    COUNT(*) as recent_activity_count,
                    MAX(timestamp) as latest_activity
                FROM activity_log 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                AND user_id IS NOT NULL
                GROUP BY user_id
            ) al ON u.id = al.user_id
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                AND (p.league_id = u.league_context OR u.league_context IS NULL)  -- Use league_context or fallback to any association
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            ORDER BY u.id, 
                     -- Prioritize league_context matches, then most recent associations
                     CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END,
                     upa.created_at DESC NULLS LAST
        """
        )
        
        # Sort the results by most recent activity (newest first)
        users.sort(key=lambda x: x['most_recent_activity'], reverse=True)
        
        return users
    except Exception as e:
        print(f"Error getting admin users: {str(e)}")
        raise e


def get_all_series_with_stats():
    """Get all active series with player counts and active clubs"""
    try:
        # Use PostgreSQL-compatible query with correct joins
        series = execute_query(
            """
            SELECT s.id, s.name, COUNT(DISTINCT u.id) as player_count,
                   STRING_AGG(DISTINCT c.name, ', ') as active_clubs
            FROM series s
            LEFT JOIN players p ON s.id = p.series_id
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            LEFT JOIN users u ON upa.user_id = u.id
            LEFT JOIN clubs c ON p.club_id = c.id
            GROUP BY s.id, s.name
            ORDER BY s.name
        """
        )

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "player_count": row["player_count"],
                "active_clubs": row["active_clubs"] or "None",
            }
            for row in series
        ]
    except Exception as e:
        print(f"Error getting admin series: {str(e)}")
        raise e


def get_all_leagues():
    """Get all leagues with statistics"""
    try:
        leagues = execute_query(
            """
            SELECT l.id, l.league_name, l.league_url,
                   COUNT(DISTINCT cl.club_id) as club_count,
                   COUNT(DISTINCT sl.series_id) as series_count
            FROM leagues l
            LEFT JOIN club_leagues cl ON l.id = cl.league_id
            LEFT JOIN series_leagues sl ON l.id = sl.league_id
            GROUP BY l.id, l.league_name, l.league_url
            ORDER BY l.league_name
        """
        )

        return leagues
    except Exception as e:
        print(f"Error getting admin leagues: {str(e)}")
        raise e


def get_all_clubs_with_stats():
    """Get all clubs with player counts and active series"""
    try:
        clubs = execute_query(
            """
            SELECT c.id, c.name, COUNT(DISTINCT p.id) as player_count,
                   STRING_AGG(DISTINCT s.name, ', ') as active_series
            FROM clubs c
            LEFT JOIN players p ON c.id = p.club_id
            LEFT JOIN series s ON p.series_id = s.id
            GROUP BY c.id, c.name
            ORDER BY c.name
        """
        )

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "player_count": row["player_count"],
                "active_series": row["active_series"] or "None",
            }
            for row in clubs
        ]
    except Exception as e:
        print(f"Error getting admin clubs: {str(e)}")
        raise e


def update_user_info(email, first_name, last_name, club_name, series_name, admin_email):
    """Update a user's information with admin logging"""
    try:
        if not all([email, first_name, last_name, club_name, series_name]):
            raise ValueError("Missing required fields")

        # Log admin action
        log_user_activity(
            admin_email,
            "admin_action",
            action="update_user",
            details=f"Updated user: {email}",
        )

        # Get club and series IDs using PostgreSQL
        club = execute_query_one(
            "SELECT id FROM clubs WHERE name = %(club_name)s", {"club_name": club_name}
        )
        series = execute_query_one(
            "SELECT id FROM series WHERE name = %(series_name)s",
            {"series_name": series_name},
        )

        if not club or not series:
            raise ValueError("Club or series not found")

        club_id = club["id"]
        series_id = series["id"]

        # Update user basic info
        execute_update(
            """
            UPDATE users 
            SET first_name = %(first_name)s, last_name = %(last_name)s
            WHERE email = %(email)s
        """,
            {"first_name": first_name, "last_name": last_name, "email": email},
        )

        # Update player info through the association
        execute_update(
            """
            UPDATE players 
            SET club_id = %(club_id)s, series_id = %(series_id)s
            WHERE tenniscores_player_id IN (
                SELECT upa.tenniscores_player_id 
                FROM user_player_associations upa 
                JOIN users u ON upa.user_id = u.id 
                WHERE u.email = %(email)s
            )
        """,
            {"club_id": club_id, "series_id": series_id, "email": email},
        )

        return True

    except Exception as e:
        print(f"Error updating user: {str(e)}")
        raise e


def update_club_name(old_name, new_name):
    """Update a club's name"""
    try:
        if not all([old_name, new_name]):
            raise ValueError("Missing required fields")

        # Update club name using PostgreSQL
        execute_update(
            "UPDATE clubs SET name = %(new_name)s WHERE name = %(old_name)s",
            {"new_name": new_name, "old_name": old_name},
        )

        return True
    except Exception as e:
        print(f"Error updating club: {str(e)}")
        raise e


def update_series_name(old_name, new_name):
    """Update a series' name"""
    try:
        if not all([old_name, new_name]):
            raise ValueError("Missing required fields")

        # Update series name using PostgreSQL
        execute_update(
            "UPDATE series SET name = %(new_name)s WHERE name = %(old_name)s",
            {"new_name": new_name, "old_name": old_name},
        )

        return True
    except Exception as e:
        print(f"Error updating series: {str(e)}")
        raise e


def delete_user_by_email(email, admin_email):
    """Delete a user and all related data from the database"""
    try:
        if not email:
            raise ValueError("Email is required")

        # Get user details for logging before deletion
        user = execute_query_one(
            "SELECT id, first_name, last_name FROM users WHERE email = %(email)s",
            {"email": email},
        )

        if not user:
            raise ValueError("User not found")

        user_id = user["id"]

        # Delete user and related data in the correct order to handle foreign key constraints
        execute_update(
            """
            DELETE FROM polls WHERE created_by = %(user_id)s;
            DELETE FROM activity_log WHERE user_id = %(user_id)s;
            DELETE FROM user_activity_logs WHERE user_email = %(email)s;
            DELETE FROM user_instructions WHERE user_email = %(email)s;
            DELETE FROM player_availability WHERE user_id = %(user_id)s;
            DELETE FROM user_player_associations WHERE user_id = %(user_id)s;
            DELETE FROM users WHERE email = %(email)s;
        """,
            {"email": email, "user_id": user_id},
        )

        # Log the deletion
        log_user_activity(
            admin_email,
            "admin_action",
            action="delete_user",
            details=f"Deleted user: {user['first_name']} {user['last_name']} ({email})",
        )

        return {
            "status": "success",
            "message": "User deleted successfully",
            "deleted_user": f"{user['first_name']} {user['last_name']}",
        }

    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        raise e


def get_user_activity_logs(email):
    """Get comprehensive activity logs for a specific user using the new activity_log system"""
    try:
        print(f"\n=== Getting Comprehensive Activity for User: {email} ===")

        # Get user details with enhanced information
        print("Fetching user details...")
        user = execute_query_one(
            """
            SELECT DISTINCT ON (u.id)
                u.id, u.first_name, u.last_name, u.email, u.last_login, u.created_at,
                c.name as club_name, s.name as series_name,
                -- Check for activity in past 24 hours from both systems
                CASE 
                    WHEN (ual.recent_activity_count > 0 OR al.recent_activity_count > 0) THEN true 
                    ELSE false 
                END as has_recent_activity,
                COALESCE(ual.recent_activity_count, 0) + COALESCE(al.recent_activity_count, 0) as recent_activity_count
            FROM users u
            LEFT JOIN (
                -- Get recent legacy activity count for this user
                SELECT 
                    user_email,
                    COUNT(*) as recent_activity_count
                FROM user_activity_logs 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                AND user_email = %(email)s
                GROUP BY user_email
            ) ual ON u.email = ual.user_email
            LEFT JOIN (
                -- Get recent comprehensive activity count for this user
                SELECT 
                    user_id,
                    COUNT(*) as recent_activity_count
                FROM activity_log 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                AND user_id IS NOT NULL
                GROUP BY user_id
            ) al ON u.id = al.user_id
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                AND (p.league_id = u.league_context OR u.league_context IS NULL)
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE u.email = %(email)s
            ORDER BY u.id, 
                     -- Prioritize league_context matches, then most recent associations
                     CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END,
                     upa.created_at DESC NULLS LAST
            LIMIT 1
            """,
            {"email": email},
        )

        if not user:
            print(f"User not found: {email}")
            raise ValueError("User not found")

        print(f"Found user: {user['first_name']} {user['last_name']}")

        # Get comprehensive activity logs from the new activity_log table
        print("Fetching comprehensive activity logs...")
        comprehensive_logs = execute_query(
            """
            SELECT 
                al.id,
                al.action_type,
                al.action_description,
                al.related_id,
                al.related_type,
                al.ip_address,
                al.user_agent,
                al.extra_data,
                timezone('America/Chicago', al.timestamp) as central_time,
                -- Mark activities from last 24 hours
                CASE 
                    WHEN al.timestamp > NOW() - INTERVAL '24 hours' THEN true 
                    ELSE false 
                END as is_recent,
                -- User info
                u.first_name as user_first_name,
                u.last_name as user_last_name,
                -- Player info
                p.first_name as player_first_name,
                p.last_name as player_last_name,
                -- Team info
                t.team_name,
                c.name as club_name,
                s.name as series_name
            FROM activity_log al
            LEFT JOIN users u ON al.user_id = u.id
            LEFT JOIN players p ON al.player_id = p.id
            LEFT JOIN teams t ON al.team_id = t.id
            LEFT JOIN clubs c ON t.club_id = c.id
            LEFT JOIN series s ON t.series_id = s.id
            WHERE u.email = %(email)s
            ORDER BY al.timestamp DESC
            LIMIT 1000
            """,
            {"email": email},
        )

        # Also get legacy logs for completeness (until full migration)
        print("Fetching legacy activity logs for comparison...")
        legacy_logs = execute_query(
            """
            SELECT 
                'legacy_' || id::text as id,
                activity_type,
                page,
                action,
                details,
                ip_address,
                NULL as user_agent,
                NULL as extra_data,
                timezone('America/Chicago', timestamp) as central_time,
                -- Mark activities from last 24 hours
                CASE 
                    WHEN timestamp > NOW() - INTERVAL '24 hours' THEN true 
                    ELSE false 
                END as is_recent
            FROM user_activity_logs
            WHERE user_email = %(email)s
            ORDER BY timestamp DESC
            LIMIT 200
            """,
            {"email": email},
        )

        print(f"Found {len(comprehensive_logs)} comprehensive logs and {len(legacy_logs)} legacy logs")

        # Format comprehensive logs
        formatted_comprehensive = []
        for log in comprehensive_logs:
            # Parse extra_data if it exists
            extra_data = None
            if log["extra_data"]:
                try:
                    import json
                    extra_data = json.loads(log["extra_data"])
                except:
                    extra_data = None

            # Create enhanced action description for registration activities
            action_description = log["action_description"]
            if log["action_type"] == "registration_successful":
                if extra_data and extra_data.get("player_data"):
                    player_data = extra_data["player_data"]
                    player_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()
                    club = player_data.get("club_name", "Unknown")
                    series = player_data.get("series_name", "Unknown")
                    player_id = extra_data.get("player_id", "Unknown")
                    team_assigned = extra_data.get("team_assigned", False)
                    
                    action_description = f"✅ Registration successful - Linked to player {player_name} ({club} - {series})"
                    if team_assigned:
                        action_description += " with team assignment"
                    else:
                        action_description += " (no team assigned)"
                        
            elif log["action_type"] == "registration_failed":
                if extra_data:
                    reason = extra_data.get("reason", "Unknown error")
                    action_type = log.get("action", "unknown_failure")
                    
                    if action_type == "player_id_linking_failed":
                        lookup_attempt = extra_data.get("lookup_attempt", {})
                        name = f"{lookup_attempt.get('first_name', '')} {lookup_attempt.get('last_name', '')}".strip()
                        club = lookup_attempt.get("club_name", "Unknown")
                        series = lookup_attempt.get("series_name", "Unknown")
                        action_description = f"❌ Registration failed - Player ID linking failed for {name} ({club} - {series})"
                        
                    elif action_type == "security_issue_player_id_claimed":
                        player_id = extra_data.get("player_id", "Unknown")
                        existing_user = extra_data.get("existing_user_email", "Unknown")
                        action_description = f"🚨 Security issue - Player ID {player_id[:15]}... already claimed by {existing_user}"
                        
                    elif action_type == "duplicate_email":
                        action_description = f"❌ Registration failed - Duplicate email address"
                        
                    elif action_type == "missing_required_fields":
                        provided_data = extra_data.get("provided_data", {})
                        missing_fields = []
                        if not provided_data.get("league_id"): missing_fields.append("league")
                        if not provided_data.get("club_name"): missing_fields.append("club")
                        if not provided_data.get("series_name"): missing_fields.append("series")
                        action_description = f"❌ Registration failed - Missing required fields: {', '.join(missing_fields)}"
                        
                    elif action_type == "player_record_not_found":
                        player_id = extra_data.get("player_id", "Unknown")
                        action_description = f"❌ Registration failed - Player record not found for ID {player_id[:15]}..."
                        
                    elif action_type == "player_lookup_exception":
                        error = extra_data.get("error", "Unknown error")
                        action_description = f"❌ Registration failed - Player lookup exception: {error[:50]}..."
                        
                    else:
                        action_description = f"❌ Registration failed - {reason}"

            formatted_comprehensive.append({
                "id": str(log["id"]),
                "system": "comprehensive",
                "activity_type": log["action_type"],
                "action_description": action_description,
                "page": extra_data.get("page") if extra_data else None,
                "related_id": log["related_id"],
                "related_type": log["related_type"],
                "ip_address": log["ip_address"],
                "user_agent": log["user_agent"],
                "extra_data": extra_data,
                "timestamp": log["central_time"].isoformat(),
                "is_recent": log["is_recent"],
                # Context information
                "user_name": f"{log['user_first_name'] or ''} {log['user_last_name'] or ''}".strip(),
                "player_name": f"{log['player_first_name'] or ''} {log['player_last_name'] or ''}".strip() if log['player_first_name'] else None,
                "team_name": log["team_name"],
                "club_name": log["club_name"],
                "series_name": log["series_name"],
            })

        # Format legacy logs for comparison
        formatted_legacy = []
        for log in legacy_logs:
            formatted_legacy.append({
                "id": log["id"],
                "system": "legacy",
                "activity_type": log["activity_type"],
                "action_description": log["details"] or f"{log['activity_type'].replace('_', ' ').title()} activity",
                "page": log["page"],
                "action": log["action"],
                "details": log["details"],
                "ip_address": log["ip_address"],
                "user_agent": log["user_agent"],
                "timestamp": log["central_time"].isoformat(),
                "is_recent": log["is_recent"],
            })

        # Combine and sort by timestamp (most recent first)
        all_activities = formatted_comprehensive + formatted_legacy
        all_activities.sort(key=lambda x: x["timestamp"], reverse=True)

        print(f"Returning {len(all_activities)} total activities ({len(formatted_comprehensive)} comprehensive, {len(formatted_legacy)} legacy)")
        if all_activities:
            print(f"Most recent activity: {all_activities[0]['activity_type']} at {all_activities[0]['timestamp']}")

        response_data = {
            "user": {
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": user["email"],
                "last_login": user["last_login"],
                "created_at": user["created_at"],  # Date registered
                "club_name": user["club_name"],   # Club from league_context
                "series_name": user["series_name"], # Series from league_context  
                "has_recent_activity": user["has_recent_activity"],
                "recent_activity_count": user["recent_activity_count"] or 0,
            },
            "activities": all_activities,
            "summary": {
                "total_activities": len(all_activities),
                "comprehensive_activities": len(formatted_comprehensive),
                "legacy_activities": len(formatted_legacy),
            }
        }

        print("Returning comprehensive response data")
        print("=== End Comprehensive Activity Request ===\n")

        return response_data

    except Exception as e:
        print(f"Error getting comprehensive user activity: {str(e)}")
        print(traceback.format_exc())
        raise e


def is_user_admin(user_email):
    """Check if a user has admin privileges"""
    try:
        user = execute_query_one(
            "SELECT id, email, is_admin FROM users WHERE email = %(email)s",
            {"email": user_email},
        )

        if not user:
            return False

        # Check the is_admin column from the database
        return bool(user.get("is_admin", False))

    except Exception as e:
        print(f"Error checking admin status: {str(e)}")
        return False


def log_admin_action(admin_email, action, details):
    """Log an admin action for audit purposes"""
    try:
        return log_user_activity(
            admin_email, "admin_action", action=action, details=details
        )
    except Exception as e:
        print(f"Error logging admin action: {str(e)}")
        return False


def get_all_users_with_player_contexts():
    """Get all non-admin users with their player association contexts for impersonation"""
    try:
        # First get all non-admin users
        all_users = execute_query(
            """
            SELECT u.id as user_id, u.first_name, u.last_name, u.email, u.last_login
            FROM users u
            WHERE u.is_admin = false  -- Don't allow impersonating other admins
            ORDER BY u.last_name, u.first_name
        """
        )
        
        # Then get all associations with full context for these users
        user_ids = [str(user['user_id']) for user in all_users]
        associations = []
        
        if user_ids:
            user_ids_str = ','.join(user_ids)
            associations = execute_query(
                f"""
                SELECT u.id as user_id, u.first_name, u.last_name, u.email, u.last_login,
                       upa.tenniscores_player_id,
                       p.first_name as player_first_name, p.last_name as player_last_name,
                       c.name as club_name, s.name as series_name, l.league_name,
                       l.league_id as league_id
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                JOIN leagues l ON p.league_id = l.id
                WHERE u.id IN ({user_ids_str})
                ORDER BY u.last_name, u.first_name, c.name, s.name
            """
            )
        
        # Build users dictionary starting with all users
        users_dict = {}
        for user in all_users:
            user_id = user['user_id']
            users_dict[user_id] = {
                'id': user_id,
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'email': user['email'],
                'last_login': user['last_login'],
                'player_contexts': []
            }
        
        # Add player contexts for users who have associations
        for assoc in associations:
            user_id = assoc['user_id']
            if user_id in users_dict:
                users_dict[user_id]['player_contexts'].append({
                    'tenniscores_player_id': assoc['tenniscores_player_id'],
                    'player_name': f"{assoc['player_first_name']} {assoc['player_last_name']}",
                    'club_name': assoc['club_name'],
                    'series_name': assoc['series_name'],
                    'league_name': assoc['league_name'],
                    'league_id': assoc['league_id'],
                    'display_name': f"{assoc['club_name']}, {assoc['series_name']} ({assoc['league_name']})"
                })
        
        # Convert to list and sort
        users_list = list(users_dict.values())
        users_list.sort(key=lambda x: (x['last_name'], x['first_name']))
        
        return users_list
        
    except Exception as e:
        print(f"Error getting users with player contexts: {str(e)}")
        raise e


def get_detailed_logging_notifications_setting():
    """Get the current status of detailed logging notifications"""
    try:
        result = execute_query_one(
            "SELECT value FROM system_settings WHERE key = 'detailed_logging_notifications'"
        )
        
        if result:
            # Return True if value is 'true', False otherwise
            return result['value'].lower() == 'true'
        else:
            # If setting doesn't exist, return False (disabled by default)
            return False
            
    except Exception as e:
        print(f"Error getting detailed logging notifications setting: {str(e)}")
        # Return False on error (fail safe - don't send notifications if there's a problem)
        return False


def set_detailed_logging_notifications_setting(enabled, admin_email):
    """Enable or disable detailed logging notifications"""
    try:
        # Convert boolean to string for database storage
        value = 'true' if enabled else 'false'
        
        # Update the setting
        execute_update(
            """
            INSERT INTO system_settings (key, value, description)
            VALUES ('detailed_logging_notifications', %s, 'Enable/disable SMS notifications to admin for every user activity logged')
            ON CONFLICT (key) DO UPDATE SET 
                value = EXCLUDED.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            [value]
        )
        
        # Log the admin action
        action_description = "enabled" if enabled else "disabled"
        log_admin_action(
            admin_email=admin_email,
            action="toggle_detailed_logging_notifications",
            details=f"Detailed logging notifications {action_description}"
        )
        
        return True
        
    except Exception as e:
        print(f"Error setting detailed logging notifications: {str(e)}")
        raise e


    def get_lineup_escrow_analytics(self):
        """Get analytics for lineup escrow usage."""
        try:
            # Get total escrow sessions
            total_sessions = self.db.execute("""
                SELECT COUNT(*) as total_sessions,
                       COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
                       COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_sessions,
                       COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_sessions
                FROM lineup_escrow_sessions
            """).fetchone()
            
            # Get usage by team
            team_usage = self.db.execute("""
                SELECT t.name as team_name, l.name as league_name,
                       COUNT(*) as sessions_created,
                       COUNT(CASE WHEN les.status = 'completed' THEN 1 END) as completed_sessions
                FROM lineup_escrow_sessions les
                JOIN teams t ON les.team_id = t.id
                JOIN leagues l ON t.league_id = l.id
                GROUP BY t.id, t.name, l.name
                ORDER BY sessions_created DESC
                LIMIT 20
            """).fetchall()
            
            # Get recent activity
            recent_activity = self.db.execute("""
                SELECT les.id, les.created_at, les.status,
                       t.name as team_name, l.name as league_name,
                       u.email as created_by
                FROM lineup_escrow_sessions les
                JOIN teams t ON les.team_id = t.id
                JOIN leagues l ON t.league_id = l.id
                JOIN users u ON les.created_by_user_id = u.id
                ORDER BY les.created_at DESC
                LIMIT 50
            """).fetchall()
            
            # Get saved lineups stats
            saved_lineups_stats = self.db.execute("""
                SELECT COUNT(*) as total_saved,
                       COUNT(DISTINCT user_id) as users_with_saved,
                       COUNT(DISTINCT team_id) as teams_with_saved
                FROM saved_lineups
            """).fetchone()
            
            return {
                'total_sessions': total_sessions['total_sessions'],
                'completed_sessions': total_sessions['completed_sessions'],
                'pending_sessions': total_sessions['pending_sessions'],
                'expired_sessions': total_sessions['expired_sessions'],
                'completion_rate': (total_sessions['completed_sessions'] / total_sessions['total_sessions'] * 100) if total_sessions['total_sessions'] > 0 else 0,
                'team_usage': team_usage,
                'recent_activity': recent_activity,
                'saved_lineups': {
                    'total_saved': saved_lineups_stats['total_saved'],
                    'users_with_saved': saved_lineups_stats['users_with_saved'],
                    'teams_with_saved': saved_lineups_stats['teams_with_saved']
                }
            }
        except Exception as e:
            logger.error(f"Error getting lineup escrow analytics: {e}")
            return None
