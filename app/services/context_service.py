"""
Enhanced Team Switching Context Service
======================================

⚠️  DEPRECATED - This service is being replaced by the simple session_service.py
⚠️  Use app.services.session_service instead for new development

This service handles dynamic context switching for users across multiple leagues and teams.
It replaces the problematic "primary association" concept with dynamic, session-based context management.

Key Features:
- Multi-league support
- Multi-team support within same league  
- Session-based context persistence
- Automatic context detection
- Fallback mechanisms for edge cases

DEPRECATION NOTICE:
This complex service is being replaced by a simpler approach in session_service.py.
The new approach uses:
1. Users.league_context as single source of truth
2. Simple session rebuilding from database
3. Unified league switching for registration, settings, and toggles
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from app.models.database_models import (
    User, UserContext, UserPlayerAssociation, Player, Team, League, Club, Series
)
from database_utils import execute_query, execute_query_one
from database_config import get_db_engine
from sqlalchemy.orm import sessionmaker

# Create session factory to match auth service pattern
engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger(__name__)

class ContextService:
    """Service for managing user context across multiple leagues and teams"""
    
    @staticmethod
    def get_user_context(user_id: int, db_session=None) -> Optional[UserContext]:
        """Get the current user context"""
        should_close = False
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        
        try:
            return db_session.query(UserContext).filter(UserContext.user_id == user_id).first()
        finally:
            if should_close:
                db_session.close()
    
    @staticmethod
    def get_user_leagues(user_id: int) -> List[Dict[str, Any]]:
        """Get all leagues this user is associated with"""
        query = """
            SELECT DISTINCT 
                l.id, l.league_id, l.league_name,
                COUNT(DISTINCT t.id) as team_count,
                COUNT(DISTINCT p.id) as player_count
            FROM leagues l
            JOIN players p ON l.id = p.league_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            LEFT JOIN teams t ON p.team_id = t.id AND t.is_active = TRUE
            WHERE upa.user_id = %s AND p.is_active = TRUE
            GROUP BY l.id, l.league_id, l.league_name
            ORDER BY l.league_name
        """
        
        results = execute_query(query, [user_id])
        return [dict(result) for result in results] if results else []
    
    @staticmethod
    def get_user_teams(user_id: int, league_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all teams this user is associated with, optionally filtered by league"""
        query = """
            SELECT DISTINCT 
                t.id, t.team_name, t.team_alias,
                c.name as club_name,
                s.name as series_name,
                l.id as league_id, l.league_name,
                COUNT(ms.id) as match_count
            FROM teams t
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            LEFT JOIN match_scores ms ON (t.id = ms.home_team_id OR t.id = ms.away_team_id)
            WHERE upa.user_id = %s 
                AND p.is_active = TRUE 
                AND t.is_active = TRUE
        """
        
        params = [user_id]
        if league_id:
            query += " AND t.league_id = %s"
            params.append(league_id)
            
        query += """
            GROUP BY t.id, t.team_name, t.team_alias, c.name, s.name, l.id, l.league_name
            ORDER BY l.league_name, c.name, s.name
        """
        
        results = execute_query(query, params)
        return [dict(result) for result in results] if results else []
    
    @staticmethod
    def switch_context(user_id: int, league_id: Optional[int] = None, team_id: Optional[int] = None) -> Dict[str, Any]:
        """Switch user's active context"""
        db_session = SessionLocal()
        
        try:
            # Validate team belongs to league if both provided
            if team_id and league_id:
                team_check = execute_query_one(
                    "SELECT id FROM teams WHERE id = %s AND league_id = %s",
                    [team_id, league_id]
                )
                if not team_check:
                    return {"success": False, "error": "Team does not belong to specified league"}
            
            # Validate user has access to team/league
            if team_id:
                team_access = execute_query_one("""
                    SELECT t.id, t.team_name, t.league_id, l.league_name
                    FROM teams t
                    JOIN players p ON t.id = p.team_id
                    JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                    JOIN leagues l ON t.league_id = l.id
                    WHERE upa.user_id = %s AND t.id = %s AND p.is_active = TRUE
                """, [user_id, team_id])
                
                if not team_access:
                    return {"success": False, "error": "User does not have access to this team"}
                    
                # Auto-set league if not provided
                if not league_id:
                    league_id = team_access["league_id"]
            
            elif league_id:
                league_access = execute_query_one("""
                    SELECT l.id, l.league_name
                    FROM leagues l
                    JOIN players p ON l.id = p.league_id
                    JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                    WHERE upa.user_id = %s AND l.id = %s AND p.is_active = TRUE
                """, [user_id, league_id])
                
                if not league_access:
                    return {"success": False, "error": "User does not have access to this league"}
            
            # Get or create user context
            context = db_session.query(UserContext).filter(UserContext.user_id == user_id).first()
            if not context:
                context = UserContext(user_id=user_id)
                db_session.add(context)
            
            # Update context
            if league_id:
                context.active_league_id = league_id
            if team_id:
                context.active_team_id = team_id
                # If team is specified, also set the league
                if not league_id:
                    team = db_session.query(Team).filter(Team.id == team_id).first()
                    if team:
                        context.active_league_id = team.league_id
            
            db_session.commit()
            
            # Get updated context info
            context_info = ContextService.get_context_info(user_id)
            
            logger.info(f"Context switched for user {user_id}: League {league_id}, Team {team_id}")
            
            return {
                "success": True,
                "context": context_info,
                "message": f"Switched to {context_info.get('team_name', context_info.get('league_name', 'new context'))}"
            }
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error switching context for user {user_id}: {e}")
            return {"success": False, "error": f"Failed to switch context: {str(e)}"}
        finally:
            db_session.close()
    
    @staticmethod
    def get_context_info(user_id: int) -> Dict[str, Any]:
        """Get detailed information about user's current context"""
        query = """
            SELECT 
                uc.user_id,
                uc.active_league_id,
                uc.active_team_id,
                l.league_id as league_string_id,
                l.league_name,
                t.team_name,
                t.team_alias,
                c.name as club_name,
                s.name as series_name,
                p.tenniscores_player_id
            FROM user_contexts uc
            LEFT JOIN leagues l ON uc.active_league_id = l.id
            LEFT JOIN teams t ON uc.active_team_id = t.id
            LEFT JOIN clubs c ON t.club_id = c.id
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN players p ON t.id = p.team_id AND p.is_active = TRUE
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id AND upa.user_id = uc.user_id
            WHERE uc.user_id = %s
            LIMIT 1
        """
        
        result = execute_query_one(query, [user_id])
        
        if result:
            return {
                "user_id": result["user_id"],
                "league_id": result["active_league_id"],
                "league_string_id": result["league_string_id"],
                "league_name": result["league_name"],
                "team_id": result["active_team_id"],
                "team_name": result["team_name"],
                "team_alias": result["team_alias"],
                "club_name": result["club_name"],
                "series_name": result["series_name"],
                "tenniscores_player_id": result["tenniscores_player_id"]
            }
        
        # No context set - return empty context
        return {
            "user_id": user_id,
            "league_id": None,
            "league_string_id": None,
            "league_name": None,
            "team_id": None,
            "team_name": None,
            "team_alias": None,
            "club_name": None,
            "series_name": None,
            "tenniscores_player_id": None
        }
    
    @staticmethod
    def auto_detect_context(user_id: int) -> Dict[str, Any]:
        """Automatically detect and set appropriate context for user"""
        # Get user's teams
        user_teams = ContextService.get_user_teams(user_id)
        
        if not user_teams:
            return {"success": False, "error": "No teams found for user"}
        
        # Strategy 1: If user has only one team, use it
        if len(user_teams) == 1:
            team = user_teams[0]
            return ContextService.switch_context(
                user_id, 
                league_id=team["league_id"], 
                team_id=team["id"]
            )
        
        # Strategy 2: Use team with most recent matches
        team_with_most_matches = max(user_teams, key=lambda x: x["match_count"])
        if team_with_most_matches["match_count"] > 0:
            return ContextService.switch_context(
                user_id,
                league_id=team_with_most_matches["league_id"],
                team_id=team_with_most_matches["id"]
            )
        
        # Strategy 3: Use first team alphabetically
        first_team = min(user_teams, key=lambda x: (x["league_name"], x["club_name"], x["series_name"]))
        return ContextService.switch_context(
            user_id,
            league_id=first_team["league_id"],
            team_id=first_team["id"]
        )
    
    @staticmethod
    def create_enhanced_session_data(user_data: Dict[str, Any], user_id: int, preserve_context: bool = False) -> Dict[str, Any]:
        """Create enhanced session data with context information"""
        # Get current context
        context_info = ContextService.get_context_info(user_id)
        
        # Only auto-detect if no context exists AND we're not preserving context
        if not context_info.get("league_id") and not preserve_context:
            auto_context_result = ContextService.auto_detect_context(user_id)
            if auto_context_result.get("success"):
                context_info = ContextService.get_context_info(user_id)
        
        # Get all user leagues and teams for UI
        user_leagues = ContextService.get_user_leagues(user_id)
        user_teams = ContextService.get_user_teams(user_id)
        
        # Enhanced session data
        enhanced_session = {
            **user_data,  # Include original user data
            
            # Current context
            "context": context_info,
            
            # For backwards compatibility
            "league_id": context_info.get("league_string_id"),
            "league_name": context_info.get("league_name"),
            "club": context_info.get("club_name"),
            "series": context_info.get("series_name"),
            "tenniscores_player_id": context_info.get("tenniscores_player_id"),
            
            # Multi-league/team metadata
            "user_leagues": user_leagues,
            "user_teams": user_teams,
            "is_multi_league": len(user_leagues) > 1,
            "is_multi_team": len(user_teams) > 1,
            
            # Context switching capabilities
            "can_switch_leagues": len(user_leagues) > 1,
            "can_switch_teams": len(user_teams) > 1,
        }
        
        return enhanced_session
    
    @staticmethod
    def handle_url_context_switch(user_id: int, url_params: Dict[str, Any]) -> Tuple[bool, str]:
        """Handle context switching from URL parameters"""
        team_id = url_params.get("team_id")
        league_id = url_params.get("league_id")
        
        if not team_id and not league_id:
            return False, "No context parameters provided"
        
        try:
            if team_id:
                team_id = int(team_id)
            if league_id:
                league_id = int(league_id)
        except (ValueError, TypeError):
            return False, "Invalid context parameters"
        
        result = ContextService.switch_context(user_id, league_id=league_id, team_id=team_id)
        
        if result["success"]:
            return True, result["message"]
        else:
            return False, result["error"]

# Convenience functions for backwards compatibility
def get_user_team_id(user_id: int) -> Optional[int]:
    """Get user's current team ID from context"""
    context_info = ContextService.get_context_info(user_id)
    return context_info.get("team_id")

def get_user_league_id(user_id: int) -> Optional[int]:
    """Get user's current league ID from context"""
    context_info = ContextService.get_context_info(user_id)
    return context_info.get("league_id") 