"""
Rally Authentication Service - Refactored for New Schema
Clean separation between user authentication and player data
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.database_models import (
    Club,
    ClubLeague,
    League,
    Player,
    Series,
    SeriesLeague,
    Team,
    User,
    UserPlayerAssociation,
)
from app.services.dashboard_service import log_activity
from database_config import get_db_engine
from utils.database_player_lookup import find_player_by_database_lookup
from utils.logging import log_user_activity
from database_utils import execute_query_one

logger = logging.getLogger(__name__)

# Create session factory
engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class AuthenticationError(Exception):
    """Authentication-related errors"""

    pass


class PlayerMatchingError(Exception):
    """Player matching-related errors"""

    pass


def convert_series_to_mapping_id(series_name, club_name, league_id=None):
    """
    DEPRECATED: This function was used for JSON file lookups.
    Database lookups now use series names directly.
    Keeping minimal version for backward compatibility.
    """
    logger.warning(
        "convert_series_to_mapping_id is deprecated - database lookups use series names directly"
    )
    return series_name  # Database lookups use the series name as-is


def hash_password(password: str) -> str:
    """Hash a password using Werkzeug's secure method"""
    return generate_password_hash(password, method="pbkdf2:sha256")


def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a password against its hash"""
    # Handle old-style hash (format: plain SHA-256)
    if len(stored_password) == 64:  # SHA-256 hash length
        old_hash = hashlib.sha256(provided_password.encode()).hexdigest()
        return stored_password == old_hash
    # Handle new-style Werkzeug hash
    return check_password_hash(stored_password, provided_password)


def assign_player_to_team(player: Player, db_session) -> bool:
    """
    Assign a player to an appropriate team if they don't already have one

    Args:
        player: Player object to assign to a team
        db_session: Database session

    Returns:
        bool: True if team was assigned or player already had a team, False otherwise
    """
    try:
        # Check if player already has a team assigned
        if player.team_id:
            logger.info(
                f"Team assignment: Player {player.full_name} already has team_id: {player.team_id}"
            )
            return True

        logger.info(
            f"Team assignment: Looking for suitable team for {player.full_name}"
        )
        logger.info(f"  League ID: {player.league_id}")
        logger.info(f"  Club ID: {player.club_id}")
        logger.info(f"  Series ID: {player.series_id}")

        # Find teams matching the player's league, club, and series
        matching_teams = (
            db_session.query(Team)
            .filter(
                Team.league_id == player.league_id,
                Team.club_id == player.club_id,
                Team.series_id == player.series_id,
                Team.is_active == True,
            )
            .all()
        )

        if matching_teams:
            # Assign to the first matching team
            selected_team = matching_teams[0]
            player.team_id = selected_team.id

            logger.info(
                f"Team assignment: Assigned {player.full_name} to team {selected_team.id} ({selected_team.team_name})"
            )
            return True
        else:
            # Try broader search - just club and league
            broader_teams = (
                db_session.query(Team)
                .filter(
                    Team.league_id == player.league_id,
                    Team.club_id == player.club_id,
                    Team.is_active == True,
                )
                .all()
            )

            if broader_teams:
                selected_team = broader_teams[0]
                player.team_id = selected_team.id

                logger.info(
                    f"Team assignment: No exact match, assigned {player.full_name} to team {selected_team.id} ({selected_team.team_name}) from broader search"
                )
                return True
            else:
                logger.warning(
                    f"Team assignment: No suitable teams found for {player.full_name}"
                )
                return False

    except Exception as e:
        logger.error(f"Team assignment error for player {player.full_name}: {str(e)}")
        return False


def find_player_matches(
    first_name: str,
    last_name: str,
    league_name: str = None,
    club_name: str = None,
    series_name: str = None,
    db_session=None,
) -> List[Player]:
    """
    Find player records that match user-provided criteria
    Returns list of potential matches for user selection
    """
    should_close = False
    if db_session is None:
        db_session = SessionLocal()
        should_close = True

    try:
        # Start with basic name matching
        query = db_session.query(Player).filter(
            and_(
                Player.first_name.ilike(f"%{first_name}%"),
                Player.last_name.ilike(f"%{last_name}%"),
                Player.is_active == True,
            )
        )

        # Add league filter if provided
        if league_name:
            query = query.join(League).filter(
                or_(
                    League.league_name.ilike(f"%{league_name}%"),
                    League.league_id.ilike(f"%{league_name}%"),
                )
            )

        # Add club filter if provided
        if club_name:
            query = query.join(Club).filter(Club.name.ilike(f"%{club_name}%"))

        # Add series filter if provided
        if series_name:
            query = query.join(Series).filter(Series.name.ilike(f"%{series_name}%"))

        # Include related data for display
        query = query.options(
            db_session.query(Player).join(League).join(Club).join(Series)
        )

        matches = query.all()

        logger.info(f"Found {len(matches)} player matches for {first_name} {last_name}")
        return matches

    except Exception as e:
        logger.error(f"Error finding player matches: {str(e)}")
        raise PlayerMatchingError(f"Failed to search for players: {str(e)}")
    finally:
        if should_close:
            db_session.close()


def get_or_create_league(league_name: str, db_session=None) -> League:
    """Get existing league or create new one"""
    should_close = False
    if db_session is None:
        db_session = SessionLocal()
        should_close = True

    try:
        # Try to find existing league
        league = (
            db_session.query(League)
            .filter(
                or_(
                    League.league_name.ilike(league_name),
                    League.league_id.ilike(league_name.upper().replace(" ", "_")),
                )
            )
            .first()
        )

        if not league:
            # Create new league
            league_id = league_name.upper().replace(" ", "_")
            league = League(league_id=league_id, league_name=league_name)
            db_session.add(league)
            db_session.flush()
            logger.info(f"Created new league: {league_name}")

        return league

    finally:
        if should_close:
            db_session.close()


def get_or_create_club(club_name: str, db_session=None) -> Club:
    """Get existing club or create new one"""
    should_close = False
    if db_session is None:
        db_session = SessionLocal()
        should_close = True

    try:
        club = db_session.query(Club).filter(Club.name.ilike(club_name)).first()

        if not club:
            club = Club(name=club_name)
            db_session.add(club)
            db_session.flush()
            logger.info(f"Created new club: {club_name}")

        return club

    finally:
        if should_close:
            db_session.close()


def get_or_create_series(series_name: str, db_session=None) -> Series:
    """Get existing series or create new one"""
    should_close = False
    if db_session is None:
        db_session = SessionLocal()
        should_close = True

    try:
        series = db_session.query(Series).filter(Series.name.ilike(series_name)).first()

        if not series:
            series = Series(name=series_name)
            db_session.add(series)
            db_session.flush()
            logger.info(f"Created new series: {series_name}")

        return series

    finally:
        if should_close:
            db_session.close()


def register_user(email: str, password: str, first_name: str, last_name: str, 
                  league_id: str = None, club_name: str = None, series_name: str = None,
                  ad_deuce_preference: str = None, dominant_hand: str = None) -> Dict[str, Any]:
    """
    Register a new user with optional player association.
    
    Args:
        email: User's email address
        password: User's password
        first_name: User's first name
        last_name: User's last name
        league_id: League identifier (optional)
        club_name: Club name (optional)
        series_name: Series name (optional)
        ad_deuce_preference: User's ad/deuce preference (optional)
        dominant_hand: User's dominant hand (optional)
        
    Returns:
        Dict with success status and user data or error message
    """
    db_session = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db_session.query(User).filter(User.email == email).first()
        if existing_user:
            return {"success": False, "error": "User with this email already exists"}
        
        # Create new user (but don't commit yet)
        password_hash = hash_password(password)
        new_user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            ad_deuce_preference=ad_deuce_preference,
            dominant_hand=dominant_hand
        )
        
        db_session.add(new_user)
        db_session.flush()  # Get user ID but don't commit yet
        
        logger.info(f"Created new user (pending commit): {email}")
        
        # If league/club/series provided, try to find player and create association
        if league_id and club_name and series_name:
            try:
                # Use existing player lookup logic
                lookup_result = find_player_by_database_lookup(
                    first_name=first_name,
                    last_name=last_name,
                    club_name=club_name,
                    series_name=series_name,
                    league_id=league_id
                )
                
                if lookup_result and lookup_result.get("player"):
                    player_id = lookup_result["player"]["tenniscores_player_id"]
                    logger.info(f"Registration: Found player {player_id} for {email}")
                    
                    # ⚠️ SECURITY CHECK: Verify player ID isn't already associated with another user
                    existing_association = db_session.query(UserPlayerAssociation).filter(
                        UserPlayerAssociation.tenniscores_player_id == player_id
                    ).first()
                    
                    if existing_association:
                        # Get the other user's email for security logging
                        other_user = db_session.query(User).filter(
                            User.id == existing_association.user_id
                        ).first()
                        
                        logger.warning(f"🚨 SECURITY: Player ID {player_id} already associated with {other_user.email if other_user else 'unknown user'}")
                        logger.warning(f"🚨 SECURITY: Preventing {email} from claiming existing player identity")
                        
                        # Rollback the transaction - user won't be created
                        db_session.rollback()
                        return {
                            "success": False, 
                            "error": f"Player identity is already associated with another account. If this is your player record, please contact support.",
                            "security_issue": True
                        }
                    
                    # Get the player record to find the league
                    player_record = db_session.query(Player).filter(
                        Player.tenniscores_player_id == player_id,
                        Player.is_active == True
                    ).first()
                    
                    if player_record:
                        # Create user-player association
                        association = UserPlayerAssociation(
                            user_id=new_user.id,
                            tenniscores_player_id=player_id
                        )
                        db_session.add(association)
                        
                        # Set user's league_context to this player's league
                        new_user.league_context = player_record.league_id
                        
                        # Assign player to team for polls functionality
                        team_assigned = assign_player_to_team(player_record, db_session)
                        if team_assigned:
                            logger.info(f"Registration: Team assignment successful for {player_record.full_name}")
                        
                        logger.info(f"Registration: Created association between {email} and player {player_id}")
                else:
                    logger.info(f"Registration: No player found for {email} with provided details")
                    
            except Exception as e:
                logger.warning(f"Registration: Player lookup error for {email}: {e}")
                # Continue with registration even if player lookup fails
        
        # Commit the transaction - this is where the user record is actually saved
        db_session.commit()
        logger.info(f"Registration completed successfully for {email}")
        
        # Build session data using our simple service
        from app.services.session_service import get_session_data_for_user
        session_data = get_session_data_for_user(email)
        
        return {
            "success": True,
            "message": "Registration successful",
            "user": session_data
        }
        
    except Exception as e:
        logger.error(f"Registration failed for {email}: {str(e)}")
        db_session.rollback()
        return {"success": False, "error": "Registration failed. Please try again."}
    finally:
        db_session.close()


def associate_user_with_player(
    user_id: int, player_id: int, is_primary: bool = False
) -> Dict[str, Any]:
    """
    Associate an existing user with a player record
    Used after registration when user selects from multiple matches
    """
    db_session = SessionLocal()

    try:
        # Verify user and player exist
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        player = (
            db_session.query(Player)
            .filter(Player.id == player_id, Player.is_active == True)
            .first()
        )
        if not player:
            return {"success": False, "error": "Player not found or inactive"}

        # Check if association already exists
        existing = (
            db_session.query(UserPlayerAssociation)
            .filter(
                UserPlayerAssociation.user_id == user_id,
                UserPlayerAssociation.tenniscores_player_id
                == player.tenniscores_player_id,
            )
            .first()
        )

        if existing:
            return {"success": False, "error": "Association already exists"}

        # ⚠️ SECURITY CHECK: Verify player ID isn't already associated with another user
        other_user_association = (
            db_session.query(UserPlayerAssociation)
            .filter(
                UserPlayerAssociation.tenniscores_player_id == player.tenniscores_player_id,
                UserPlayerAssociation.user_id != user_id
            )
            .first()
        )
        
        if other_user_association:
            # Get the other user's email for security logging
            other_user = db_session.query(User).filter(
                User.id == other_user_association.user_id
            ).first()
            
            logger.warning(f"🚨 SECURITY: Player ID {player.tenniscores_player_id} already associated with {other_user.email if other_user else 'unknown user'}")
            logger.warning(f"🚨 SECURITY: Preventing user {user_id} from claiming existing player identity")
            
            return {
                "success": False, 
                "error": "Player identity is already associated with another account. If this is your player record, please contact support.",
                "security_issue": True
            }

        # If this should be primary, unset other primary associations (if column exists)
        if is_primary:
            try:
                db_session.query(UserPlayerAssociation).filter(
                    UserPlayerAssociation.user_id == user_id,
                    UserPlayerAssociation.is_primary == True,
                ).update({"is_primary": False})
            except Exception:
                # is_primary column may not exist anymore, skip this step
                logger.info("is_primary column not found, skipping primary association update")

        # Create new association
        association_data = {
            "user_id": user_id,
            "tenniscores_player_id": player.tenniscores_player_id,
        }
        
        # Only add is_primary if the column exists
        try:
            # Test if the is_primary column exists by creating a test object
            test_obj = UserPlayerAssociation(**association_data, is_primary=is_primary)
            association = test_obj
        except TypeError:
            # is_primary column doesn't exist, create without it
            association = UserPlayerAssociation(**association_data)

        db_session.add(association)
        db_session.commit()

        logger.info(f"Associated user {user.email} with player {player.full_name}")

        return {
            "success": True,
            "message": f"Successfully associated with {player.full_name}",
        }

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error associating user with player: {str(e)}")
        return {"success": False, "error": "Failed to create association"}

    finally:
        db_session.close()


def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """
    Authenticate user with simplified session management
    
    Args:
        email: User's email address
        password: User's password
        
    Returns:
        Dict with success status and session data
    """
    from app.services.session_service import get_session_data_for_user
    from database_utils import execute_query_one
    
    db_session = SessionLocal()
    
    try:
        # Find user by email
        user = db_session.query(User).filter(User.email == email).first()
        
        if not user:
            return {"success": False, "error": "Invalid email or password"}
        
        # Verify password
        if not check_password_hash(user.password_hash, password):
            return {"success": False, "error": "Invalid email or password"}
        
        # Update last login
        user.last_login = func.now()
        db_session.commit()
        
        # Try to build session data using our session service
        session_data = get_session_data_for_user(email)
        
        print(f"[AUTH_DEBUG] get_session_data_for_user returned: {session_data}")
        print(f"[AUTH_DEBUG] session_data is falsy: {not session_data}")
        
        if not session_data:
            logger.warning(f"get_session_data_for_user failed for {email}, building fallback session")
            
            # Try a simpler query to get basic player info if the complex one failed
            basic_player_query = """
                SELECT 
                    upa.tenniscores_player_id,
                    p.club_id,
                    p.series_id,
                    p.league_id,
                    c.name as club,
                    s.name as series,
                    l.league_name,
                    l.league_id as league_string_id
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = TRUE
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE u.email = %s
                LIMIT 1
            """
            
            player_info = execute_query_one(basic_player_query, [email])
            
            # Build fallback session with player data if found
            session_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_admin": user.is_admin,
                "ad_deuce_preference": user.ad_deuce_preference or "",
                "dominant_hand": user.dominant_hand or "",
                "league_context": user.league_context,
                "settings": "{}",
            }
            
            # Add player info if found
            if player_info:
                session_data.update({
                    "club": player_info.get("club") or "",
                    "series": player_info.get("series") or "",
                    "league_id": player_info.get("league_id"),
                    "league_string_id": player_info.get("league_string_id") or "",
                    "league_name": player_info.get("league_name") or "",
                    "tenniscores_player_id": player_info.get("tenniscores_player_id") or "",
                    "club_id": player_info.get("club_id"),
                    "series_id": player_info.get("series_id"),
                    "team_id": None,  # We'll skip team_id for simplicity in fallback
                })
                logger.info(f"Built fallback session with player data for {email}: {player_info.get('tenniscores_player_id')}")
            else:
                # No player associations found
                session_data.update({
                    "club": "",
                    "series": "",
                    "league_id": "",
                    "league_string_id": "",
                    "league_name": "",
                    "tenniscores_player_id": "",
                    "club_id": None,
                    "series_id": None,
                    "team_id": None,
                })
                logger.warning(f"No player associations found for {email}")
        
        # Log user activity
        log_user_activity(email, "login", details={
            "login_success": True,
            "league_context": session_data.get("league_name"),
            "player_id": session_data.get("tenniscores_player_id")
        })
        
        logger.info(f"Login successful: {email} -> {session_data.get('league_name', 'No League')} (Player: {session_data.get('tenniscores_player_id', 'None')})")
        
        return {
            "success": True,
            "message": "Login successful",
            "user": session_data
        }
        
    except Exception as e:
        logger.error(f"Authentication error for {email}: {str(e)}")
        return {"success": False, "error": "Authentication failed"}
    finally:
        db_session.close()


def get_user_with_players(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user data with all associated players
    Used for session management and profile display
    """
    db_session = SessionLocal()

    try:
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Load associated players
        associations = (
            db_session.query(UserPlayerAssociation)
            .filter(UserPlayerAssociation.user_id == user.id)
            .all()
        )

        players_data = []
        for assoc in associations:
            player = assoc.get_player(db_session)
            if player and player.league and player.club and player.series:
                # Handle is_primary gracefully for transition period
                is_primary = getattr(assoc, 'is_primary', False)
                
                players_data.append(
                    {
                        "id": player.id,
                        "name": player.full_name,
                        "league": player.league.league_name,
                        "club": player.club.name,
                        "series": player.series.name,
                        "tenniscores_player_id": player.tenniscores_player_id,
                        "is_primary": is_primary,
                    }
                )

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
            "players": players_data,
        }

    finally:
        db_session.close()


def get_clubs_list() -> List[str]:
    """Get list of all clubs for registration form"""
    db_session = SessionLocal()

    try:
        clubs = db_session.query(Club.name).order_by(Club.name).all()
        return [club.name for club in clubs]

    except Exception as e:
        logger.error(f"Error getting clubs list: {str(e)}")
        return []

    finally:
        db_session.close()


def get_leagues_list() -> List[Dict[str, str]]:
    """Get list of all leagues for registration form"""
    db_session = SessionLocal()

    try:
        leagues = db_session.query(League).order_by(League.league_name).all()
        return [
            {"id": league.league_id, "name": league.league_name} for league in leagues
        ]

    except Exception as e:
        logger.error(f"Error getting leagues list: {str(e)}")
        return []

    finally:
        db_session.close()


def get_series_list(league_id: str = None) -> List[str]:
    """Get list of series, optionally filtered by league"""
    db_session = SessionLocal()

    try:
        query = db_session.query(Series.name)

        if league_id:
            query = (
                query.join(SeriesLeague)
                .join(League)
                .filter(League.league_id == league_id)
            )

        series = query.order_by(Series.name).all()
        return [s.name for s in series]

    except Exception as e:
        logger.error(f"Error getting series list: {str(e)}")
        return []

    finally:
        db_session.close()


def create_session_data(user_data: Dict[str, Any], preserve_context: bool = False) -> Dict[str, Any]:
    """
    Create enhanced session data with context support
    Uses the new ContextService for multi-league/multi-team support
    
    Args:
        user_data: User data dictionary
        preserve_context: If True, don't auto-detect context (preserves manual selections)
    """
    from app.services.context_service import ContextService
    
    # Handle both direct user dict and the response format
    if "user" in user_data:
        user = user_data["user"]
    else:
        user = user_data

    # Get user ID
    user_id = user.get("id")
    
    if not user_id:
        # Fallback to legacy format if no user ID
        logger.warning("No user ID provided, falling back to legacy session format")
        return _create_legacy_session_data(user_data)
    
    try:
        # Create enhanced session data with context information
        enhanced_session = ContextService.create_enhanced_session_data(user, user_id, preserve_context=preserve_context)
        
        # Add legacy fields for backwards compatibility
        enhanced_session.update({
            "settings": "{}",  # Default empty settings
            "club_automation_password": "",  # Legacy field, empty for security
        })
        
        logger.info(f"Enhanced session created for user {user_id}: "
                   f"League: {enhanced_session.get('league_name', 'None')}, "
                   f"Team: {enhanced_session.get('context', {}).get('team_name', 'None')}")
        
        return enhanced_session
        
    except Exception as e:
        logger.error(f"Error creating enhanced session data for user {user_id}: {e}")
        # Fallback to legacy format
        return _create_legacy_session_data(user_data)


def _create_legacy_session_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback legacy session data creation
    Used when enhanced context system fails
    """
    # Handle both direct user dict and the response format
    if "user" in user_data:
        user = user_data["user"]
    else:
        user = user_data

    # Get primary player for legacy compatibility
    primary_player = user.get("primary_player")
    players = user.get("players", [])

    # If no primary player but have players, use the first one
    if not primary_player and players:
        primary_player = players[0]

    # Create legacy session format
    session_data = {
        "id": user.get("id"),
        "email": user.get("email"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "is_admin": user.get("is_admin", False),
        "ad_deuce_preference": user.get("ad_deuce_preference"),
        "dominant_hand": user.get("dominant_hand"),
        "settings": "{}",  # Default empty settings for legacy compatibility
    }

    # Add player-specific data if available
    if primary_player:
        session_data.update(
            {
                "club": (
                    primary_player.get("club", {}).get("name")
                    if isinstance(primary_player.get("club"), dict)
                    else primary_player.get("club")
                ),
                "series": (
                    primary_player.get("series", {}).get("name")
                    if isinstance(primary_player.get("series"), dict)
                    else primary_player.get("series")
                ),
                "league_id": (
                    primary_player.get("league", {}).get("league_id")
                    if isinstance(primary_player.get("league"), dict)
                    else None
                ),
                "league_name": (
                    primary_player.get("league", {}).get("name")
                    if isinstance(primary_player.get("league"), dict)
                    else primary_player.get("league")
                ),
                "tenniscores_player_id": primary_player.get("tenniscores_player_id"),
                "club_automation_password": "",  # Legacy field, empty for security
            }
        )
    else:
        # No player association - user has no league/club/series data
        session_data.update(
            {
                "club": "",
                "series": "",
                "league_id": "",
                "league_name": "",
                "tenniscores_player_id": "",
                "club_automation_password": "",
            }
        )

    return session_data


def update_user_league_context(user_id: int, league_id: int) -> bool:
    """
    Update user's league context for session persistence
    Called when user switches leagues to remember their choice for next login
    """
    db_session = SessionLocal()
    
    try:
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User not found for ID: {user_id}")
            return False
        
        user.league_context = league_id
        db_session.commit()
        
        logger.info(f"Updated league context for user {user.email}: League ID {league_id}")
        return True
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating league context for user {user_id}: {str(e)}")
        return False
    finally:
        db_session.close()


def fix_team_assignments_for_existing_users() -> Dict[str, Any]:
    """
    Fix team assignments for existing users who don't have teams assigned.
    This function can be called to retroactively fix the team assignment issue.

    Returns:
        Dict with success status and statistics about the fix
    """
    db_session = SessionLocal()

    try:
        logger.info("Starting team assignment fix for existing users")

        # Find all players without team assignments who have user associations
        players_without_teams = (
            db_session.query(Player)
            .join(
                UserPlayerAssociation,
                Player.tenniscores_player_id
                == UserPlayerAssociation.tenniscores_player_id,
            )
            .filter(
                Player.team_id.is_(None),
                Player.is_active == True,
            )
            .all()
        )

        logger.info(
            f"Found {len(players_without_teams)} players without team assignments"
        )

        fixed_count = 0
        failed_count = 0

        for player in players_without_teams:
            try:
                if assign_player_to_team(player, db_session):
                    fixed_count += 1
                    logger.info(f"Fixed team assignment for {player.full_name}")
                else:
                    failed_count += 1
                    logger.warning(
                        f"Could not fix team assignment for {player.full_name}"
                    )
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Error fixing team assignment for {player.full_name}: {str(e)}"
                )

        # Commit all changes
        db_session.commit()

        logger.info(
            f"Team assignment fix completed: {fixed_count} fixed, {failed_count} failed"
        )

        return {
            "success": True,
            "total_players": len(players_without_teams),
            "fixed_count": fixed_count,
            "failed_count": failed_count,
            "message": f"Fixed team assignments for {fixed_count} out of {len(players_without_teams)} players",
        }

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error in team assignment fix: {str(e)}")
        return {"success": False, "error": f"Failed to fix team assignments: {str(e)}"}

    finally:
        db_session.close()
