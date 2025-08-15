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
                  league_id: str, club_name: str, series_name: str,
                  ad_deuce_preference: str = None, dominant_hand: str = None, phone_number: str = None) -> Dict[str, Any]:
    """
    Register a new user with mandatory player association.
    
    Args:
        email: User's email address
        password: User's password
        first_name: User's first name
        last_name: User's last name
        league_id: League identifier (required)
        club_name: Club name (required)
        series_name: Series name (required)
        ad_deuce_preference: User's ad/deuce preference (optional)
        dominant_hand: User's dominant hand (optional)
        phone_number: User's phone number for SMS notifications (optional)
        
    Returns:
        Dict with success status and user data or error message
    """
    db_session = SessionLocal()
    
    # Import activity logging at the top to avoid circular imports
    from utils.logging import log_user_activity
    
    try:
        # Check if user already exists
        existing_user = db_session.query(User).filter(User.email == email).first()
        if existing_user:
            # Log registration failure due to existing user
            log_user_activity(
                email, 
                "registration_failed", 
                action="duplicate_email",
                first_name=first_name,
                last_name=last_name,
                details={
                    "reason": "User with this email already exists",
                    "registration_data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "league_id": league_id,
                        "club_name": club_name,
                        "series_name": series_name
                    }
                }
            )
            return {"success": False, "error": "User with this email already exists"}
        
        # Validate required fields for player association
        if not league_id or not club_name or not series_name:
            # Log registration failure due to missing required fields
            log_user_activity(
                email, 
                "registration_failed", 
                action="missing_required_fields",
                first_name=first_name,
                last_name=last_name,
                details={
                    "reason": "Missing required league/club/series information",
                    "provided_data": {
                        "league_id": league_id,
                        "club_name": club_name,
                        "series_name": series_name
                    },
                    "registration_data": {
                        "first_name": first_name,
                        "last_name": last_name
                    }
                }
            )
            return {
                "success": False, 
                "error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."
            }
        
        # Create new user (but don't commit yet)
        password_hash = hash_password(password)
        new_user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            ad_deuce_preference=ad_deuce_preference,
            dominant_hand=dominant_hand
        )
        
        db_session.add(new_user)
        db_session.flush()  # Get user ID but don't commit yet
        
        logger.info(f"Created new user (pending commit): {email}")
        
        # Mandatory player lookup - registration fails if no player is found
        try:
            # Use our player lookup service to find the specific player they registered for
            player_lookup_result = find_player_by_database_lookup(
                first_name=first_name,
                last_name=last_name,
                league_id=league_id,
                club_name=club_name,
                series_name=series_name
            )
            
            logger.info(f"Registration: Player lookup result for {email}: {player_lookup_result}")
            
            # Check if player was found
            if not player_lookup_result or not player_lookup_result.get("player"):
                logger.warning(f"Registration FAILED: No player found for {email} with provided details")
                
                # Log player ID linking failure
                log_user_activity(
                    email, 
                    "registration_failed", 
                    action="player_id_linking_failed",
                    first_name=first_name,
                    last_name=last_name,
                    details={
                        "reason": "No player found with provided details",
                        "lookup_attempt": {
                            "first_name": first_name,
                            "last_name": last_name,
                            "league_id": league_id,
                            "club_name": club_name,
                            "series_name": series_name
                        },
                        "player_lookup_result": player_lookup_result
                    }
                )
                
                db_session.rollback()
                return {
                    "success": False, 
                    "error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."
                }
            
            player_data = player_lookup_result["player"]
            player_id = player_data["tenniscores_player_id"]
            
            # Get the full player record from database
            player_record = db_session.query(Player).filter(
                Player.tenniscores_player_id == player_id,
                Player.is_active == True
            ).first()
            
            if not player_record:
                logger.warning(f"Registration FAILED: Player record not found in database for {email}, player_id: {player_id}")
                
                # Log player ID linking failure due to missing player record
                log_user_activity(
                    email, 
                    "registration_failed", 
                    action="player_record_not_found",
                    details={
                        "reason": "Player record not found in database",
                        "player_id": player_id,
                        "lookup_attempt": {
                            "first_name": first_name,
                            "last_name": last_name,
                            "league_id": league_id,
                            "club_name": club_name,
                            "series_name": series_name
                        }
                    }
                )
                
                db_session.rollback()
                return {
                    "success": False, 
                    "error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."
                }
            
            # --- BEGIN TEAM CONTEXT FIX FOR MULTI-TEAM PLAYERS ---
            # Find all teams for this player
            player_teams = db_session.query(Player).filter(
                Player.tenniscores_player_id == player_id,
                Player.is_active == True
            ).all()
            preferred_team = None
            for team_player in player_teams:
                # Fetch club and series names for this player
                club = db_session.query(Club).filter(Club.id == team_player.club_id).first()
                series = db_session.query(Series).filter(Series.id == team_player.series_id).first()
                db_club = (club.name if club else "").strip().lower()
                db_series = (series.name if series else "").strip().lower()
                reg_club = (club_name or "").strip().lower()
                reg_series = (series_name or "").strip().lower()
                if db_club == reg_club and db_series == reg_series:
                    preferred_team = team_player
                    break
            # If not found, try to match just club
            if not preferred_team:
                for team_player in player_teams:
                    club = db_session.query(Club).filter(Club.id == team_player.club_id).first()
                    db_club = (club.name if club else "").strip().lower()
                    reg_club = (club_name or "").strip().lower()
                    if db_club == reg_club:
                        preferred_team = team_player
                        break
            # If still not found, fall back to the first team
            if not preferred_team and player_teams:
                preferred_team = player_teams[0]
            # Update player_record's team_id, club_id, series_id if needed
            if preferred_team:
                # Do NOT update player_record fields—just use for context/logging
                club = db_session.query(Club).filter(Club.id == preferred_team.club_id).first()
                series = db_session.query(Series).filter(Series.id == preferred_team.series_id).first()
                logger.info(f"Registration: Set team context to {(club.name if club else '')} - {(series.name if series else '')} (team_id: {preferred_team.team_id}) for {email}")
            # --- END TEAM CONTEXT FIX ---
            
            # ENHANCEMENT: Handle existing placeholder associations
            # Check if this player is already associated with a placeholder user
            existing_association = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.tenniscores_player_id == player_id
            ).first()
            
            if existing_association:
                # Check if it's a placeholder user
                existing_user = db_session.query(User).filter(
                    User.id == existing_association.user_id
                ).first()
                
                if existing_user and existing_user.email.endswith('@placeholder.rally'):
                    logger.info(f"Registration: Removing placeholder association for player {player_id}")
                    
                    # Remove the placeholder association
                    db_session.delete(existing_association)
                    
                    # If placeholder user has no other associations, remove the user too
                    other_associations = db_session.query(UserPlayerAssociation).filter(
                        UserPlayerAssociation.user_id == existing_user.id,
                        UserPlayerAssociation.tenniscores_player_id != player_id
                    ).count()
                    
                    if other_associations == 0:
                        logger.info(f"Registration: Removing empty placeholder user {existing_user.email}")
                        
                        # Handle foreign key constraints by deleting related records first
                        try:
                            # Delete group memberships for this user
                            from app.models.database_models import GroupMember
                            group_memberships = db_session.query(GroupMember).filter(
                                GroupMember.user_id == existing_user.id
                            ).all()
                            
                            for membership in group_memberships:
                                db_session.delete(membership)
                                logger.info(f"Registration: Deleted group membership {membership.id} for placeholder user")
                            
                            # Delete activity log entries for this user
                            from app.models.database_models import ActivityLog
                            activity_logs = db_session.query(ActivityLog).filter(
                                ActivityLog.user_id == existing_user.id
                            ).all()
                            
                            for log in activity_logs:
                                db_session.delete(log)
                                logger.info(f"Registration: Deleted activity log {log.id} for placeholder user")
                            
                            # Delete player availability records for this user (if user_id column exists)
                            try:
                                from app.models.database_models import PlayerAvailability
                                availability_records = db_session.query(PlayerAvailability).filter(
                                    PlayerAvailability.user_id == existing_user.id
                                ).all()
                                
                                for record in availability_records:
                                    db_session.delete(record)
                                    logger.info(f"Registration: Deleted player availability record {record.id} for placeholder user")
                            except Exception as e:
                                logger.info(f"Registration: Skipping player availability cleanup (user_id column may not exist): {e}")
                            
                            # Now delete the user
                            db_session.delete(existing_user)
                            logger.info(f"Registration: Successfully deleted placeholder user {existing_user.email}")
                            
                        except Exception as cleanup_error:
                            logger.error(f"Registration: Error during placeholder user cleanup: {cleanup_error}")
                            # Continue with registration even if cleanup fails
                            # The placeholder user will remain but won't interfere with new user
                    
                    db_session.flush()  # Apply deletes before creating new association
                else:
                    # Real user already associated - this is a security issue, prevent registration
                    logger.warning(f"🚨 SECURITY: Player ID {player_id} already associated with real user {existing_user.email}")
                    logger.warning(f"🚨 SECURITY: Preventing registration of {email} with existing player identity")
                    
                    # Log security issue - player ID already claimed
                    log_user_activity(
                        email, 
                        "registration_failed", 
                        action="security_issue_player_id_claimed",
                        details={
                            "reason": "Player ID already associated with another account",
                            "player_id": player_id,
                            "existing_user_email": existing_user.email if existing_user else "unknown",
                            "lookup_attempt": {
                                "first_name": first_name,
                                "last_name": last_name,
                                "league_id": league_id,
                                "club_name": club_name,
                                "series_name": series_name
                            }
                        }
                    )
                    
                    # Rollback and return error - don't create the user account
                    db_session.rollback()
                    return {
                        "success": False, 
                        "error": "Player identity is already associated with another account. If this is your player record, please contact support.",
                        "security_issue": True
                    }
            
            # Create new association if no conflicts
            if not existing_association or (existing_association and existing_user and existing_user.email.endswith('@placeholder.rally')):
                association = UserPlayerAssociation(
                    user_id=new_user.id,
                    tenniscores_player_id=player_id
                )
                db_session.add(association)
            
            # CRITICAL FIX: Set league_context based on the preferred team they registered for
            # This ensures the session service will select the right team on login
            if preferred_team:
                # Use the preferred team's league_id to set the correct context
                new_user.league_context = preferred_team.league_id
                logger.info(f"Registration: Set league_context to {preferred_team.league_id} for preferred team {preferred_team.club_id} - {preferred_team.series_id}")
            else:
                # Fallback to original player record if no preferred team found
                new_user.league_context = player_record.league_id
                logger.info(f"Registration: Set league_context to {player_record.league_id} for player {player_data['club_name']} - {player_data['series_name']} (no preferred team found)")
            
            # Assign player to team for polls functionality
            team_assigned = assign_player_to_team(player_record, db_session)
            if team_assigned:
                logger.info(f"Registration: Team assignment successful for {player_record.full_name}")
            
            # Log association creation (or existing association)
            if 'association' in locals() and association:
                logger.info(f"Registration: Created association between {email} and player {player_id} ({player_data['club_name']} - {player_data['series_name']})")
            else:
                logger.info(f"Registration: Using existing association for {email} and player {player_id} ({player_data['club_name']} - {player_data['series_name']})")
            
        except Exception as e:
            logger.error(f"Registration FAILED: Player lookup error for {email}: {e}")
            
            # Log player ID linking failure due to exception
            log_user_activity(
                email, 
                "registration_failed", 
                action="player_lookup_exception",
                first_name=first_name,
                last_name=last_name,
                details={
                    "reason": "Exception during player lookup",
                    "error": str(e),
                    "lookup_attempt": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "league_id": league_id,
                        "club_name": club_name,
                        "series_name": series_name
                    }
                }
            )
            
            db_session.rollback()
            return {
                "success": False, 
                "error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."
            }
        
        # Commit the transaction - this is where the user record is actually saved
        db_session.commit()
        logger.info(f"Registration completed successfully for {email}")
        
        # Log successful player ID linking
        log_user_activity(
            email, 
            "registration_successful", 
            action="player_id_linking_successful",
            first_name=first_name,
            last_name=last_name,
            details={
                "player_id": player_id,
                "player_data": {
                    "first_name": player_data.get("first_name"),
                    "last_name": player_data.get("last_name"),
                    "club_name": player_data.get("club_name"),
                    "series_name": player_data.get("series_name"),
                    "league_id": player_data.get("league_id")
                },
                "team_assigned": team_assigned,
                "registration_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "league_id": league_id,
                    "club_name": club_name,
                    "series_name": series_name,
                    "phone_number_provided": bool(phone_number)
                }
            }
        )
        
        # Build session data using our simple service
        from app.services.session_service import get_session_data_for_user
        session_data = get_session_data_for_user(email)
        
        # Send welcome SMS notification if phone number is provided
        if phone_number:
            try:
                from app.services.notifications_service import send_sms_notification
                
                welcome_message = "You're in! Your Rally registration was successful. We'll keep you posted on pickup games, team polls, match lineups, and more. Visit: lovetorally.com/app anytime to login.\n\nLet's go!"
                
                sms_result = send_sms_notification(
                    to_number=phone_number,
                    message=welcome_message,
                    test_mode=False
                )
                
                if sms_result["success"]:
                    logger.info(f"Registration: Welcome SMS sent successfully to {phone_number}")
                else:
                    logger.warning(f"Registration: Failed to send welcome SMS to {phone_number}: {sms_result.get('error', 'Unknown error')}")
                    
            except Exception as sms_error:
                logger.error(f"Registration: Error sending welcome SMS to {phone_number}: {str(sms_error)}")
                # Don't fail registration if SMS fails - just log the error
        
        return {
            "success": True,
            "message": "Registration successful",
            "user": session_data
        }
        
    except Exception as e:
        logger.error(f"Registration failed for {email}: {str(e)}")
        
        # Log general registration failure
        log_user_activity(
            email, 
            "registration_failed", 
            action="general_registration_error",
            first_name=first_name,
            last_name=last_name,
            details={
                "reason": "General registration error",
                "error": str(e),
                "registration_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "league_id": league_id,
                    "club_name": club_name,
                    "series_name": series_name
                }
            }
        )
        
        db_session.rollback()
        return {
            "success": False, 
            "error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."
        }
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
        
        # Check if user has a temporary password
        has_temporary_password = getattr(user, 'has_temporary_password', False)
        
        # Debug logging
        print(f"[AUTH_DEBUG] User object type: {type(user)}")
        print(f"[AUTH_DEBUG] User object attributes: {dir(user)}")
        print(f"[AUTH_DEBUG] has_temporary_password attribute exists: {hasattr(user, 'has_temporary_password')}")
        print(f"[AUTH_DEBUG] has_temporary_password value: {has_temporary_password}")
        print(f"[AUTH_DEBUG] User ID: {user.id}")
        print(f"[AUTH_DEBUG] User email: {user.email}")
        
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
        
        # Add temporary password flag to session data
        session_data["has_temporary_password"] = has_temporary_password
        
        # Log user activity
        log_user_activity(email, "login", details={
            "login_success": True,
            "league_context": session_data.get("league_name"),
            "player_id": session_data.get("tenniscores_player_id"),
            "has_temporary_password": has_temporary_password
        })
        
        logger.info(f"Login successful: {email} -> {session_data.get('league_name', 'No League')} (Player: {session_data.get('tenniscores_player_id', 'None')}) - Temporary password: {has_temporary_password}")
        
        return {
            "success": True,
            "message": "Login successful",
            "user": session_data,
            "has_temporary_password": has_temporary_password
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
    Create simple session data using users.league_context
    Simplified version that works with the current registration system
    
    Args:
        user_data: User data dictionary
        preserve_context: Ignored (kept for compatibility)
    """
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
        # Use the legacy session data creation (which works)
        session_data = _create_legacy_session_data(user_data)
        
        # Add league_context from user data if available
        if user.get("league_context"):
            session_data["league_context"] = user.get("league_context")
        
        logger.info(f"Simple session created for user {user_id}: "
                   f"League: {session_data.get('league_name', 'None')}")
        
        return session_data
        
    except Exception as e:
        logger.error(f"Error creating session data for user {user_id}: {e}")
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


def register_user_id_based(email: str, password: str, first_name: str, last_name: str, 
                          league_id: str, club_name: str, series_id: int = None, 
                          series_name: str = None, series_display: str = None,
                          ad_deuce_preference: str = None, dominant_hand: str = None, 
                          phone_number: str = None) -> Dict[str, Any]:
    """
    ID-BASED REGISTRATION: Register user with bulletproof series_id matching.
    
    This function prioritizes series_id for exact matching, with series_name as fallback
    for backward compatibility.
    
    Args:
        email: User's email address
        password: User's password
        first_name: User's first name
        last_name: User's last name
        league_id: League identifier (e.g., 'APTA_CHICAGO')
        club_name: Club name
        series_id: Series database ID (preferred, bulletproof)
        series_name: Series name (fallback for backward compatibility)
        series_display: Display name for logging (e.g., "Series 13")
        ad_deuce_preference: Ad/deuce preference
        dominant_hand: Dominant hand
        phone_number: Phone number for SMS notifications
        
    Returns:
        Dict with success status and user data or error message
    """
    db_session = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db_session.query(User).filter(User.email.ilike(email)).first()
        if existing_user:
            logger.warning(f"Registration FAILED: Email {email} already exists")
            return {"success": False, "error": "Email already registered"}

        # Validate inputs
        if not series_id and not series_name:
            logger.warning(f"Registration FAILED: No series identifier provided for {email}")
            return {"success": False, "error": "Either series_id or series_name must be provided"}

        # Create user record
        hashed_password = hash_password(password)
        new_user = User(
            email=email,
            password_hash=hashed_password,
            first_name=first_name,
            last_name=last_name,
            ad_deuce_preference=ad_deuce_preference,
            dominant_hand=dominant_hand,
            is_admin=False
        )
        
        db_session.add(new_user)
        db_session.flush()  # Get user ID but don't commit yet
        
        logger.info(f"ID-BASED Registration: Created new user (pending commit): {email}")
        
        # ✅ ID-BASED PLAYER LOOKUP
        try:
            from utils.database_player_lookup import find_player_by_database_lookup_id, find_player_by_database_lookup
            
            player_lookup_result = None
            lookup_method = "unknown"
            
            # PRIORITY 1: Use series_id if provided (bulletproof approach)
            if series_id:
                logger.info(f"ID-BASED Registration: Using series_id={series_id} for {email}")
                player_lookup_result = find_player_by_database_lookup_id(
                    first_name=first_name,
                    last_name=last_name,
                    club_name=club_name,
                    series_id=series_id,
                    league_id=league_id
                )
                lookup_method = f"series_id={series_id}"
                
            # FALLBACK: Use series_name if series_id not provided or failed
            if not player_lookup_result or player_lookup_result.get("match_type") == "no_match":
                if series_name:
                    logger.info(f"ID-BASED Registration: Falling back to series_name='{series_name}' for {email}")
                    player_lookup_result = find_player_by_database_lookup(
                        first_name=first_name,
                        last_name=last_name,
                        club_name=club_name,
                        series_name=series_name,
                        league_id=league_id
                    )
                    lookup_method = f"series_name='{series_name}' (fallback)"
            
            logger.info(f"ID-BASED Registration: Player lookup result for {email} using {lookup_method}: {player_lookup_result}")
            
            # Check if player was found
            if not player_lookup_result or not player_lookup_result.get("player"):
                logger.warning(f"ID-BASED Registration FAILED: No player found for {email} with provided details")
                
                # Enhanced logging for debugging
                log_user_activity(
                    email, 
                    "registration_failed", 
                    action="id_based_player_lookup_failed",
                    first_name=first_name,
                    last_name=last_name,
                    details={
                        "reason": "No player found with provided details",
                        "lookup_method": lookup_method,
                        "lookup_attempt": {
                            "first_name": first_name,
                            "last_name": last_name,
                            "league_id": league_id,
                            "club_name": club_name,
                            "series_id": series_id,
                            "series_name": series_name,
                            "series_display": series_display
                        },
                        "player_lookup_result": player_lookup_result
                    }
                )
                
                db_session.rollback()
                return {
                    "success": False, 
                    "error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."
                }
            
            player_data = player_lookup_result["player"]
            player_id = player_data["tenniscores_player_id"]
            
            # Get the full player record from database
            player_record = db_session.query(Player).filter(
                Player.tenniscores_player_id == player_id,
                Player.is_active == True
            ).first()
            
            if not player_record:
                logger.warning(f"ID-BASED Registration FAILED: Player record not found in database for {email}, player_id: {player_id}")
                
                log_user_activity(
                    email, 
                    "registration_failed", 
                    action="player_record_not_found",
                    details={
                        "reason": "Player record not found in database",
                        "player_id": player_id,
                        "lookup_method": lookup_method,
                        "lookup_attempt": {
                            "first_name": first_name,
                            "last_name": last_name,
                            "league_id": league_id,
                            "club_name": club_name,
                            "series_id": series_id,
                            "series_name": series_name
                        }
                    }
                )
                
                db_session.rollback()
                return {
                    "success": False, 
                    "error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."
                }
            
            # Use the same team context logic as the original register_user function
            # Find all teams for this player
            player_teams = db_session.query(Player).filter(
                Player.tenniscores_player_id == player_id,
                Player.is_active == True
            ).all()
            
            preferred_team = None
            
            # ENHANCED: For ID-based registration, we can be more precise about team selection
            if series_id:
                # If we have series_id, find the exact team that matches
                for team_player in player_teams:
                    if team_player.series_id == series_id:
                        club = db_session.query(Club).filter(Club.id == team_player.club_id).first()
                        if club and club.name.strip().lower() == club_name.strip().lower():
                            preferred_team = team_player
                            logger.info(f"ID-BASED Registration: Found exact series_id + club match for {email}")
                            break
                
                # If no exact club+series match, try series-only match
                if not preferred_team:
                    for team_player in player_teams:
                        if team_player.series_id == series_id:
                            preferred_team = team_player
                            logger.info(f"ID-BASED Registration: Found series_id match (different club) for {email}")
                            break
            
            # Fallback to original club-based matching if series_id approach didn't work
            if not preferred_team:
                for team_player in player_teams:
                    club = db_session.query(Club).filter(Club.id == team_player.club_id).first()
                    series = db_session.query(Series).filter(Series.id == team_player.series_id).first()
                    db_club = (club.name if club else "").strip().lower()
                    db_series = (series.name if series else "").strip().lower()
                    reg_club = (club_name or "").strip().lower()
                    reg_series = (series_name or "").strip().lower()
                    
                    if db_club == reg_club and db_series == reg_series:
                        preferred_team = team_player
                        logger.info(f"ID-BASED Registration: Found club+series name match for {email}")
                        break
                        
                # If not found, try to match just club
                if not preferred_team:
                    for team_player in player_teams:
                        club = db_session.query(Club).filter(Club.id == team_player.club_id).first()
                        db_club = (club.name if club else "").strip().lower()
                        reg_club = (club_name or "").strip().lower()
                        if db_club == reg_club:
                            preferred_team = team_player
                            logger.info(f"ID-BASED Registration: Found club-only match for {email}")
                            break
                            
                # If still not found, fall back to the first team
                if not preferred_team and player_teams:
                    preferred_team = player_teams[0]
                    logger.info(f"ID-BASED Registration: Using first available team for {email}")
            
            # Set league context based on preferred team
            if preferred_team:
                new_user.league_context = preferred_team.league_id
                club = db_session.query(Club).filter(Club.id == preferred_team.club_id).first()
                series = db_session.query(Series).filter(Series.id == preferred_team.series_id).first()
                logger.info(f"ID-BASED Registration: Set league_context to {preferred_team.league_id} for {(club.name if club else '')} - {(series.name if series else '')} (team_id: {preferred_team.team_id}) for {email}")
                
                # ✅ CRITICAL FIX: Set active_team_id in UserContext to remember registration choice
                from app.models.database_models import UserContext
                
                user_context = UserContext(
                    user_id=new_user.id,
                    active_league_id=preferred_team.league_id,
                    active_team_id=preferred_team.team_id
                )
                db_session.add(user_context)
                logger.info(f"ID-BASED Registration: Set UserContext active_team_id={preferred_team.team_id} for {email}")
                
            else:
                new_user.league_context = player_record.league_id
                logger.info(f"ID-BASED Registration: Set league_context to {player_record.league_id} for player {player_data['club_name']} - {player_data['series_name']} (no preferred team found)")
            
            # Handle existing placeholder associations (same as original)
            existing_association = db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.tenniscores_player_id == player_id
            ).first()
            
            if existing_association:
                existing_user = db_session.query(User).filter(
                    User.id == existing_association.user_id
                ).first()
                
                if existing_user and existing_user.email.endswith('@placeholder.rally'):
                    logger.info(f"ID-BASED Registration: Removing placeholder association for player {player_id}")
                    db_session.delete(existing_association)
                    
                    # Clean up placeholder user if needed
                    other_associations = db_session.query(UserPlayerAssociation).filter(
                        UserPlayerAssociation.user_id == existing_user.id,
                        UserPlayerAssociation.tenniscores_player_id != player_id
                    ).count()
                    
                    if other_associations == 0:
                        logger.info(f"ID-BASED Registration: Removing empty placeholder user {existing_user.email}")
                        
                        # Clean up foreign key references
                        try:
                            from app.models.database_models import GroupMember, ActivityLog
                            
                            group_memberships = db_session.query(GroupMember).filter(
                                GroupMember.user_id == existing_user.id
                            ).all()
                            for membership in group_memberships:
                                db_session.delete(membership)
                            
                            activity_logs = db_session.query(ActivityLog).filter(
                                ActivityLog.user_id == existing_user.id
                            ).all()
                            for log in activity_logs:
                                db_session.delete(log)
                            
                            db_session.delete(existing_user)
                            logger.info(f"ID-BASED Registration: Successfully cleaned up placeholder user")
                            
                        except Exception as cleanup_error:
                            logger.error(f"ID-BASED Registration: Error cleaning up placeholder user: {cleanup_error}")
                            # Continue with registration despite cleanup error
                
                elif existing_user and not existing_user.email.endswith('@placeholder.rally'):
                    logger.warning(f"ID-BASED Registration FAILED: Player {player_id} already associated with real user {existing_user.email}")
                    
                    log_user_activity(
                        email, 
                        "registration_failed", 
                        action="player_already_associated",
                        details={
                            "reason": "Player identity already associated with another account",
                            "existing_user_email": existing_user.email,
                            "player_id": player_id,
                            "lookup_method": lookup_method
                        }
                    )
                    
                    db_session.rollback()
                    return {
                        "success": False, 
                        "error": "Player identity is already associated with another account. If this is your player record, please contact support.",
                        "security_issue": True
                    }
            
            # Create new association
            if not existing_association or (existing_association and existing_user and existing_user.email.endswith('@placeholder.rally')):
                association = UserPlayerAssociation(
                    user_id=new_user.id,
                    tenniscores_player_id=player_id
                )
                db_session.add(association)
            
            # Assign player to team for polls functionality
            team_assigned = assign_player_to_team(player_record, db_session)
            if team_assigned:
                logger.info(f"ID-BASED Registration: Team assignment successful for {player_record.full_name}")
            
            # Log successful association
            logger.info(f"ID-BASED Registration: Created association between {email} and player {player_id} ({player_data['club_name']} - {player_data['series_name']}) using {lookup_method}")
            
        except Exception as e:
            logger.error(f"ID-BASED Registration FAILED: Player lookup error for {email}: {e}")
            
            log_user_activity(
                email, 
                "registration_failed", 
                action="id_based_lookup_exception",
                details={
                    "reason": "Exception during player lookup",
                    "error": str(e),
                    "lookup_attempt": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "league_id": league_id,
                        "club_name": club_name,
                        "series_id": series_id,
                        "series_name": series_name
                    }
                }
            )
            
            db_session.rollback()
            return {
                "success": False, 
                "error": "Registration was not successful. Rally was unable to link your user account to a player ID. Please contact support for assistance."
            }

        # Commit all changes
        db_session.commit()
        logger.info(f"ID-BASED Registration: Successfully committed registration for {email}")
        
        # Log successful registration
        log_user_activity(
            email, 
            "registration_successful", 
            action="id_based_player_linking_successful",
            first_name=first_name,
            last_name=last_name,
            details={
                "player_id": player_id,
                "lookup_method": lookup_method,
                "player_data": {
                    "first_name": player_data.get("first_name"),
                    "last_name": player_data.get("last_name"),
                    "club_name": player_data.get("club_name"),
                    "series_name": player_data.get("series_name"),
                    "league_id": player_data.get("league_id")
                },
                "team_assigned": team_assigned,
                "registration_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "league_id": league_id,
                    "club_name": club_name,
                    "series_id": series_id,
                    "series_name": series_name,
                    "series_display": series_display,
                    "phone_number_provided": bool(phone_number)
                }
            }
        )
        
        # Build session data using session service
        from app.services.session_service import get_session_data_for_user
        session_data = get_session_data_for_user(email)
        
        # Send welcome SMS notification if phone number is provided
        if phone_number:
            try:
                from app.services.notifications_service import send_sms_notification
                
                welcome_message = "You're in! Your Rally registration was successful. We'll keep you posted on pickup games, team polls, match lineups, and more. Visit: lovetorally.com/app anytime to login.\n\nLet's go!"
                
                sms_result = send_sms_notification(
                    to_number=phone_number,
                    message=welcome_message,
                    test_mode=False
                )
                
                if sms_result["success"]:
                    logger.info(f"ID-BASED Registration: Welcome SMS sent successfully to {phone_number}")
                else:
                    logger.warning(f"ID-BASED Registration: Failed to send welcome SMS to {phone_number}: {sms_result.get('error', 'Unknown error')}")
                    
            except Exception as sms_error:
                logger.error(f"ID-BASED Registration: Error sending welcome SMS to {phone_number}: {str(sms_error)}")

        return {
            "success": True,
            "message": "Registration successful!",
            "user": session_data,
            "player_id": player_id,
            "lookup_method": lookup_method
        }

    except Exception as e:
        db_session.rollback()
        logger.error(f"ID-BASED Registration: Unexpected error for {email}: {str(e)}")
        
        log_user_activity(
            email,
            "registration_failed", 
            action="id_based_unexpected_error",
            details={
                "error": str(e),
                "registration_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "league_id": league_id,
                    "club_name": club_name,
                    "series_id": series_id,
                    "series_name": series_name
                }
            }
        )
        
        return {
            "success": False,
            "error": "An unexpected error occurred during registration. Please try again or contact support."
        }

    finally:
        db_session.close()
