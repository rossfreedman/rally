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
    Get complete session data for a user based on their league_context.
    This is the single source of truth for all session data.
    
    Args:
        user_email: User's email address
        
    Returns:
        Complete session dict or None if user not found
    """
    print(f"[SESSION_SERVICE] Getting session data for: {user_email}")
    try:
        # FIRST: Check user's league_context and auto-fix if NULL
        user_check_query = """
            SELECT u.id, u.email, u.league_context
            FROM users u
            WHERE u.email = %s
        """
        user_info = execute_query_one(user_check_query, [user_email])
        
        if not user_info:
            logger.warning(f"No user found for email: {user_email}")
            print(f"[SESSION_SERVICE] No user found for: {user_email}")
            return None
        
        # ROOT CAUSE FIX: If league_context is NULL, set it to user's primary league
        if user_info["league_context"] is None:
            print(f"[SESSION_SERVICE] User {user_email} has NULL league_context, finding primary league...")
            
            # Find user's primary league (most recent or first active association)
            primary_league_query = """
                SELECT l.id as league_db_id, l.league_name,
                       COUNT(*) as player_count,
                       MAX(p.created_at) as most_recent
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                WHERE u.email = %s AND p.is_active = TRUE
                GROUP BY l.id, l.league_name
                ORDER BY most_recent DESC, player_count DESC
                LIMIT 1
            """
            primary_league = execute_query_one(primary_league_query, [user_email])
            
            if primary_league:
                primary_league_id = primary_league["league_db_id"]
                print(f"[SESSION_SERVICE] Setting league_context to {primary_league['league_name']} (ID: {primary_league_id})")
                
                # Update user's league_context
                from database_utils import execute_update
                execute_update(
                    "UPDATE users SET league_context = %s WHERE email = %s",
                    [primary_league_id, user_email]
                )
                print(f"[SESSION_SERVICE] Updated league_context for {user_email}")
            else:
                print(f"[SESSION_SERVICE] No active player associations found for {user_email}")
                return None
        
        # NOW: Get user and their active player based on league_context (which is now guaranteed to be set)
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
                -- Player data from league_context with ALL required IDs
                p.tenniscores_player_id,
                p.team_id,
                p.club_id,
                p.series_id,
                c.name as club,
                s.name as series,
                l.id as league_db_id,
                l.league_id as league_string_id,
                l.league_name
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                AND p.league_id = u.league_context 
                AND p.is_active = TRUE
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE u.email = %s
            ORDER BY (CASE WHEN p.tenniscores_player_id IS NOT NULL THEN 1 ELSE 2 END)
            LIMIT 1
        """
        
        result = execute_query_one(session_query, [user_email])
        print(f"[SESSION_SERVICE] Database query result: {result}")
        
        if not result:
            logger.warning(f"No user found for email: {user_email}")
            print(f"[SESSION_SERVICE] No user found for: {user_email}")
            return None
            
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
            "series": result["series"] or "",
            "club_id": result["club_id"],
            "series_id": result["series_id"],
            "team_id": result["team_id"],
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