"""
Simple Session Management Service
================================

Unified, simple approach to session management and league switching.
Replaces the complex ContextService with a straightforward system.

Key principles:
1. One source of truth: Users.league_context
2. One session structure used everywhere  
3. One function to rebuild session from league_context
4. Used by: registration, settings, league toggling
"""

import logging
from typing import Dict, Any, Optional
from database_utils import execute_query_one, execute_query

logger = logging.getLogger(__name__)


def get_session_data_for_user(user_email: str) -> Optional[Dict[str, Any]]:
    """
    Build complete session data for a user from database.
    This is the centralized session builder used by login, registration, and league switching.
    """
    try:
        # First try to get user data with league context prioritization
        query = """
            SELECT DISTINCT ON (u.id)
                u.id, u.email, u.first_name, u.last_name, u.is_admin,
                u.ad_deuce_preference, u.dominant_hand, u.league_context,
                
                -- Player data (prioritize league_context team)
                c.name as club, c.logo_filename as club_logo,
                s.name as series, p.tenniscores_player_id,
                c.id as club_id, s.id as series_id, t.id as team_id,
                t.team_name, t.display_name,
                
                -- League data
                l.id as league_db_id, l.league_id as league_string_id, l.league_name
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                AND p.is_active = true 
                AND (CASE WHEN u.league_context IS NOT NULL THEN p.league_id = u.league_context ELSE true END)
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE u.email = %s
            ORDER BY u.id, 
                     (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END),
                     p.id DESC
            LIMIT 1
        """
        
        result = execute_query_one(query, [user_email])
        
        if not result:
            logger.warning(f"No user found for email: {user_email}")
            print(f"[SESSION_SERVICE] User not found in database: {user_email}")
            return None
            
        # If no player found in league context, try any active player
        if not result.get("tenniscores_player_id"):
            print(f"[SESSION_SERVICE] No player found in league context {result.get('league_context')}, trying any active player")
            
            fallback_query = """
                SELECT DISTINCT ON (u.id)
                    u.id, u.email, u.first_name, u.last_name, u.is_admin,
                    u.ad_deuce_preference, u.dominant_hand,
                    
                    -- Player data from any active player
                    c.name as club, c.logo_filename as club_logo,
                    s.name as series, p.tenniscores_player_id,
                    c.id as club_id, s.id as series_id, t.id as team_id,
                    t.team_name, t.display_name,
                    
                    -- League data
                    l.id as league_db_id, l.league_id as league_string_id, l.league_name
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = true
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                JOIN teams t ON p.team_id = t.id
                JOIN leagues l ON p.league_id = l.id
                WHERE u.email = %s
                ORDER BY u.id, p.id DESC
                LIMIT 1
            """
            
            fallback_result = execute_query_one(fallback_query, [user_email])
            if fallback_result:
                print(f"[SESSION_SERVICE] Found active player in {fallback_result['league_name']}")
                result = fallback_result
                
                # Update user's league context to match found player
                execute_query(
                    "UPDATE users SET league_context = %s WHERE email = %s",
                    [fallback_result["league_db_id"], user_email]
                )
                result["league_context"] = fallback_result["league_db_id"]
            else:
                print(f"[SESSION_SERVICE] No active players found for user")
                return None
            
        # Get raw series name from database
        raw_series_name = result["series"] or ""
        display_series_name = raw_series_name
        
        # Build standard session structure with ALL required IDs
        session_data = {
            "id": result["id"],
            "email": result["email"],
            "first_name": result["first_name"],
            "last_name": result["last_name"],
            "is_admin": result["is_admin"],
            "ad_deuce_preference": result["ad_deuce_preference"] or "",
            "dominant_hand": result["dominant_hand"] or "",
            "league_context": result["league_context"],
            
            # Player-specific data with ALL IDs
            "club": result["club"] or "",
            "club_logo": result["club_logo"] or "",
            "series": raw_series_name,  # 👈 Keep database format (e.g., "Chicago 22")
            "club_id": result["club_id"],
            "series_id": result["series_id"],
            "team_id": result["team_id"],
            "team_name": result["team_name"] or "",
            "display_name": result["display_name"] or result["team_name"] or "",  # Use display_name if available
            "tenniscores_player_id": result["tenniscores_player_id"] or "",
            
            # League data - provide both formats for compatibility
            "league_id": result["league_db_id"],  # INTEGER for database queries
            "league_string_id": result["league_string_id"] or "",  # STRING for display/API
            "league_name": result["league_name"] or "",
            
            # Legacy fields for compatibility
            "settings": "{}",
        }
        
        print(f"[SESSION_SERVICE] Built session data: {session_data}")
        logger.info(f"Built session for {user_email}: {session_data['league_name']} - {session_data['club']}")
        return session_data
        
    except Exception as e:
        print(f"[SESSION_SERVICE] ERROR: {e}")
        import traceback
        print(f"[SESSION_SERVICE] Traceback: {traceback.format_exc()}")
        logger.error(f"Error building session data for {user_email}: {e}")
        return None


def switch_user_league(user_email: str, new_league_id: str) -> bool:
    """
    Switch user to a new league by updating league_context.
    
    Args:
        user_email: User's email
        new_league_id: New league ID string (e.g., 'APTA_CHICAGO', 'NSTF')
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert league_id string to database ID
        league_lookup = execute_query_one(
            "SELECT id FROM leagues WHERE league_id = %s", 
            [new_league_id]
        )
        
        if not league_lookup:
            logger.error(f"League not found: {new_league_id}")
            return False
            
        league_db_id = league_lookup["id"]
        
        # Verify user has a player in this league
        player_check = execute_query_one("""
            SELECT p.tenniscores_player_id 
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE u.email = %s AND p.league_id = %s AND p.is_active = true
            LIMIT 1
        """, [user_email, league_db_id])
        
        if not player_check:
            logger.error(f"User {user_email} has no active player in league {new_league_id}")
            return False
        
        # Update user's league_context
        execute_query(
            "UPDATE users SET league_context = %s WHERE email = %s",
            [league_db_id, user_email]
        )
        
        logger.info(f"Switched {user_email} to league {new_league_id} (DB ID: {league_db_id})")
        return True
        
    except Exception as e:
        logger.error(f"Error switching {user_email} to league {new_league_id}: {e}")
        return False


def get_user_leagues(user_email: str) -> list:
    """
    Get all leagues this user can switch to.
    
    Args:
        user_email: User's email
        
    Returns:
        List of league dicts with id, league_id, league_name
    """
    try:
        leagues_query = """
            SELECT DISTINCT l.id, l.league_id, l.league_name
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            JOIN leagues l ON p.league_id = l.id
            WHERE u.email = %s AND p.is_active = true
            ORDER BY l.league_name
        """
        
        leagues = execute_query(leagues_query, [user_email])
        return leagues or []
        
    except Exception as e:
        logger.error(f"Error getting leagues for {user_email}: {e}")
        return []


def update_session_from_db(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refresh session data from database based on current user.
    Used after league switching to update session variables.
    
    Args:
        session: Current session dict (must have 'user' with 'email')
        
    Returns:
        Updated session dict
    """
    try:
        user_email = session.get("user", {}).get("email")
        if not user_email:
            logger.warning("No user email in session for refresh")
            return session
            
        # Get fresh session data from database
        fresh_data = get_session_data_for_user(user_email)
        if fresh_data:
            session["user"] = fresh_data
            logger.info(f"Refreshed session for {user_email}")
        else:
            logger.warning(f"Could not refresh session for {user_email}")
            
        return session
        
    except Exception as e:
        logger.error(f"Error refreshing session: {e}")
        return session 


def switch_user_team_in_league(user_email: str, team_id: int) -> bool:
    """
    Switch user to a different team within the same league.
    This updates their session context but keeps the league_context the same.
    
    Args:
        user_email: User's email
        team_id: New team ID (integer)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get user ID and current league context
        user_info = execute_query_one(
            "SELECT id, league_context FROM users WHERE email = %s", 
            [user_email]
        )
        
        if not user_info or not user_info["league_context"]:
            logger.error(f"User {user_email} not found or has no league context")
            return False
            
        user_id = user_info["id"]
        current_league_id = user_info["league_context"]
        
        # Verify user has access to this team and it's in the same league
        team_verification_query = """
            SELECT 
                t.id as team_id,
                t.team_name,
                t.league_id,
                c.name as club_name,
                s.name as series_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s AND t.id = %s AND p.is_active = TRUE
        """
        
        team_info = execute_query_one(team_verification_query, [user_id, team_id])
        
        if not team_info:
            logger.error(f"User {user_email} does not have access to team {team_id}")
            return False
        
        # Verify team is in the same league as current context
        if team_info["league_id"] != current_league_id:
            logger.error(f"Team {team_id} is not in user's current league context {current_league_id}")
            return False
        
        logger.info(f"Switched {user_email} to team {team_info['team_name']} (ID: {team_id}) in same league")
        return True
        
    except Exception as e:
        logger.error(f"Error switching {user_email} to team {team_id}: {e}")
        return False


def get_session_data_for_user_team(user_email: str, team_id: int) -> Optional[Dict[str, Any]]:
    """
    Get session data for a user with a specific team context.
    Used after team switching to build session with the new team.
    
    Args:
        user_email: User's email address
        team_id: Specific team ID to use for context
        
    Returns:
        Complete session dict with team context or None if invalid
    """
    print(f"[SESSION_SERVICE] Getting session data for: {user_email} with team_id: {team_id}")
    try:
        # Build session with specific team context
        session_query = """
            SELECT 
                u.id,
                u.email, 
                u.first_name, 
                u.last_name,
                u.is_admin,
                u.ad_deuce_preference,
                u.dominant_hand,
                u.league_context,
                -- Player data from specific team
                p.tenniscores_player_id,
                p.team_id,
                p.club_id,
                p.series_id,
                c.name as club,
                c.logo_filename as club_logo,
                s.name as series,
                l.id as league_db_id,
                l.league_id as league_string_id,
                l.league_name,
                t.team_name
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                AND p.team_id = %s
                AND p.is_active = TRUE
            JOIN teams t ON p.team_id = t.id
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            JOIN leagues l ON p.league_id = l.id
            WHERE u.email = %s
            LIMIT 1
        """
        
        result = execute_query_one(session_query, [team_id, user_email])
        print(f"[SESSION_SERVICE] Team-specific query result: {result}")
        
        if not result:
            logger.warning(f"No user/team combination found for email: {user_email}, team_id: {team_id}")
            print(f"[SESSION_SERVICE] No user/team found for: {user_email}, team_id: {team_id}")
            return None
            
        # Build standard session structure with team-specific data
        session_data = {
            "id": result["id"],
            "email": result["email"],
            "first_name": result["first_name"],
            "last_name": result["last_name"],
            "is_admin": result["is_admin"],
            "ad_deuce_preference": result["ad_deuce_preference"] or "",
            "dominant_hand": result["dominant_hand"] or "",
            "league_context": result["league_context"],
            
            # Team-specific player data
            "club": result["club"] or "",
            "club_logo": result["club_logo"] or "",
            "series": result["series"] or "",
            "club_id": result["club_id"],
            "series_id": result["series_id"],
            "team_id": result["team_id"],
            "team_name": result["team_name"],
            "tenniscores_player_id": result["tenniscores_player_id"] or "",
            
            # League data
            "league_id": result["league_db_id"],
            "league_string_id": result["league_string_id"] or "",
            "league_name": result["league_name"] or "",
            
            # Legacy fields for compatibility
            "settings": "{}",
        }
        
        print(f"[SESSION_SERVICE] Built team-specific session data: {session_data}")
        logger.info(f"Built team session for {user_email}: {session_data['league_name']} - {session_data['club']} - {session_data['series']}")
        return session_data
        
    except Exception as e:
        print(f"[SESSION_SERVICE] ERROR building team session: {e}")
        import traceback
        print(f"[SESSION_SERVICE] Traceback: {traceback.format_exc()}")
        logger.error(f"Error building team session data for {user_email}: {e}")
        return None


def get_user_teams_in_league(user_email: str, league_id: int) -> list:
    """
    Get all teams this user can switch to within a specific league.
    
    Args:
        user_email: User's email
        league_id: League database ID (integer)
        
    Returns:
        List of team dicts with team_id, team_name, club_name, series_name
    """
    try:
        teams_query = """
            SELECT DISTINCT 
                t.id as team_id,
                t.team_name,
                c.name as club_name,
                s.name as series_name,
                COUNT(ms.id) as match_count
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            JOIN teams t ON p.team_id = t.id
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            LEFT JOIN match_scores ms ON (t.id = ms.home_team_id OR t.id = ms.away_team_id)
            WHERE u.email = %s AND t.league_id = %s AND p.is_active = true AND t.is_active = true
            GROUP BY t.id, t.team_name, c.name, s.name
            ORDER BY c.name, s.name
        """
        
        teams = execute_query(teams_query, [user_email, league_id])
        return [dict(team) for team in teams] if teams else []
        
    except Exception as e:
        logger.error(f"Error getting teams for {user_email} in league {league_id}: {e}")
        return [] 