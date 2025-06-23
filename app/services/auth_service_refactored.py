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


def register_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    league_name: str = None,
    club_name: str = None,
    series_name: str = None,
    selected_player_id: int = None,
) -> Dict[str, Any]:
    """
    Register a new user with optional player association and automatic team assignment

    Flow:
    1. Create user account
    2. If player details provided, search for matching players
    3. If single match or player_id provided, create association
    4. If player found, ensure they have a team assignment
    5. If multiple matches, return them for user selection
    6. If no matches, user can register without player association
    """
    db_session = SessionLocal()

    try:
        # Hash the password
        hashed_password = hash_password(password)

        # Check if user already exists
        existing_user = db_session.query(User).filter(User.email.ilike(email)).first()

        if existing_user:
            return {"success": False, "error": "User with this email already exists"}

        # Get or create league, club, and series records for player lookup
        league_record = None
        club_record = None
        series_record = None

        if league_name:
            league_record = get_or_create_league(league_name, db_session)

        if club_name:
            club_record = get_or_create_club(club_name, db_session)

        if series_name:
            series_record = get_or_create_series(series_name, db_session)

        # Create new user (clean authentication data only)
        new_user = User(
            email=email,
            password_hash=hashed_password,
            first_name=first_name,
            last_name=last_name,
        )

        db_session.add(new_user)
        db_session.flush()  # Get the user ID

        user_data = {
            "id": new_user.id,
            "email": new_user.email,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "is_admin": new_user.is_admin,
            "players": [],
        }

        # Handle player association
        player_association_result = None

        if selected_player_id:
            # User selected a specific player from previous search
            player = (
                db_session.query(Player)
                .filter(Player.id == selected_player_id, Player.is_active == True)
                .first()
            )

            if player:
                # Check if association already exists
                existing = (
                    db_session.query(UserPlayerAssociation)
                    .filter(
                        UserPlayerAssociation.user_id == new_user.id,
                        UserPlayerAssociation.tenniscores_player_id
                        == player.tenniscores_player_id,
                    )
                    .first()
                )

                if not existing:
                    association = UserPlayerAssociation(
                        user_id=new_user.id,
                        tenniscores_player_id=player.tenniscores_player_id,
                        is_primary=True,
                    )
                    db_session.add(association)
                    player_association_result = "associated"

                    # ✅ NEW: Ensure player has team assignment
                    team_assigned = assign_player_to_team(player, db_session)
                    if team_assigned:
                        logger.info(
                            f"Registration: Team assignment successful for {player.full_name}"
                        )
                    else:
                        logger.warning(
                            f"Registration: Could not assign team to {player.full_name}"
                        )

                    if player.league and player.club and player.series:
                        user_data["players"] = [
                            {
                                "id": player.id,
                                "name": player.full_name,
                                "league": player.league.league_name,
                                "club": player.club.name,
                                "series": player.series.name,
                                "tenniscores_player_id": player.tenniscores_player_id,
                                "is_primary": True,
                            }
                        ]

                    logger.info(
                        f"Registration: Created association between user {email} and player {player.full_name} (ID: {player.id})"
                    )
                else:
                    player_association_result = "already_associated"
                    logger.info(
                        f"Registration: User {email} already associated with player {player.full_name}"
                    )
            else:
                logger.warning(
                    f"Registration: Selected player ID {selected_player_id} not found"
                )
                player_association_result = "no_matches"

        elif all([first_name, last_name, league_name]):
            # Use enhanced database lookup with confidence-based matching
            try:
                logger.info(
                    f"Registration: Looking up player via enhanced database matching for {first_name} {last_name}"
                )

                # Use enhanced lookup function that returns structured results with confidence levels
                lookup_result = find_player_by_database_lookup(
                    first_name=first_name,
                    last_name=last_name,
                    club_name=club_name,
                    series_name=series_name,
                    league_id=league_name,
                )

                # Handle results based on confidence level from enhanced lookup
                match_type = lookup_result.get("match_type", "no_match")
                player_data = lookup_result.get("player")
                message = lookup_result.get("message", "")

                logger.info(f"Registration: Lookup result - {match_type}: {message}")

                if match_type in ["exact", "high_confidence"] and player_data:
                    # High confidence matches - auto-associate
                    tenniscores_player_id = player_data["tenniscores_player_id"]

                    logger.info(
                        f"Registration: Found {match_type} match - {player_data['first_name']} {player_data['last_name']} ({player_data['club_name']}, {player_data['series_name']})"
                    )

                    # Find the actual Player record in the database
                    # CRITICAL FIX: When multiple players exist for same tenniscores_player_id,
                    # prioritize the one that matches the registration data
                    all_players = (
                        db_session.query(Player)
                        .filter(
                            Player.tenniscores_player_id == tenniscores_player_id,
                            Player.is_active == True,
                        )
                        .all()
                    )

                    player = None
                    if len(all_players) == 1:
                        # Single player - use it
                        player = all_players[0]
                        logger.info(
                            f"Registration: Single player found for {tenniscores_player_id}"
                        )
                    elif len(all_players) > 1:
                        # Multiple players - prioritize the one that matches registration data
                        logger.info(
                            f"Registration: Found {len(all_players)} players for {tenniscores_player_id}, selecting best match"
                        )

                        # First try: exact club and series match
                        for p in all_players:
                            if (
                                p.club
                                and p.series
                                and p.club.name == player_data["club_name"]
                                and p.series.name == player_data["series_name"]
                            ):
                                player = p
                                logger.info(
                                    f"Registration: Selected player {p.id} - exact club+series match"
                                )
                                break

                        # Second try: club match only
                        if not player:
                            for p in all_players:
                                if p.club and p.club.name == player_data["club_name"]:
                                    player = p
                                    logger.info(
                                        f"Registration: Selected player {p.id} - club match ({p.club.name})"
                                    )
                                    break

                        # Third try: series match only
                        if not player:
                            for p in all_players:
                                if (
                                    p.series
                                    and p.series.name == player_data["series_name"]
                                ):
                                    player = p
                                    logger.info(
                                        f"Registration: Selected player {p.id} - series match ({p.series.name})"
                                    )
                                    break

                        # Fallback: use first player but log warning
                        if not player:
                            player = all_players[0]
                            logger.warning(
                                f"Registration: No club/series match found, using first player {player.id}"
                            )
                            logger.warning(
                                f"Registration: Selected {player.first_name} {player.last_name} at {player.club.name if player.club else 'No club'} in {player.series.name if player.series else 'No series'}"
                            )
                            for i, p in enumerate(all_players):
                                logger.warning(
                                    f"Registration: Option {i+1}: {p.first_name} {p.last_name} at {p.club.name if p.club else 'No club'} in {p.series.name if p.series else 'No series'}"
                                )

                    if player:
                        # Create proper user-player association for high confidence matches
                        existing = (
                            db_session.query(UserPlayerAssociation)
                            .filter(
                                UserPlayerAssociation.user_id == new_user.id,
                                UserPlayerAssociation.tenniscores_player_id
                                == player.tenniscores_player_id,
                            )
                            .first()
                        )

                        if not existing:
                            association = UserPlayerAssociation(
                                user_id=new_user.id,
                                tenniscores_player_id=player.tenniscores_player_id,
                                is_primary=True,
                            )
                            db_session.add(association)
                            player_association_result = "associated"

                            # ✅ NEW: Ensure player has team assignment
                            team_assigned = assign_player_to_team(player, db_session)
                            if team_assigned:
                                logger.info(
                                    f"Registration: Team assignment successful for {player.full_name}"
                                )
                            else:
                                logger.warning(
                                    f"Registration: Could not assign team to {player.full_name}"
                                )

                            if player.league and player.club and player.series:
                                user_data["players"] = [
                                    {
                                        "id": player.id,
                                        "name": player.full_name,
                                        "league": player.league.league_name,
                                        "club": player.club.name,
                                        "series": player.series.name,
                                        "tenniscores_player_id": player.tenniscores_player_id,
                                        "is_primary": True,
                                    }
                                ]

                            logger.info(
                                f"Registration: Created association between user {email} and {match_type} match {player.full_name} (ID: {player.id})"
                            )
                        else:
                            player_association_result = "already_associated"
                    else:
                        player_association_result = "no_active_player"
                        logger.warning(
                            f"Registration: Found {match_type} match but no active Player record for {tenniscores_player_id}"
                        )

                elif match_type in ["probable", "possible"] and player_data:
                    # Good matches but not high confidence - avoid auto-association
                    logger.info(
                        f"Registration: Found {match_type} match but skipping auto-association to preserve user registration intent"
                    )
                    logger.info(
                        f"Registration: User registered: {first_name} {last_name} at {club_name} in {series_name}"
                    )
                    logger.info(
                        f"Registration: Match found: {player_data['first_name']} {player_data['last_name']} at {player_data['club_name']} in {player_data['series_name']}"
                    )
                    logger.info(
                        f"Registration: User can manually link to player later in settings"
                    )

                    player_association_result = "probable_matches_available"

                elif match_type == "risky" and player_data:
                    # Risky matches - definitely skip auto-association
                    logger.warning(
                        f"Registration: Found risky match (last name only) - SKIPPING auto-association"
                    )
                    logger.warning(
                        f"Registration: User registered: {first_name} {last_name} at {club_name} in {series_name}"
                    )
                    logger.warning(
                        f"Registration: Risky match: {player_data['first_name']} {player_data['last_name']} at {player_data['club_name']} in {player_data['series_name']}"
                    )
                    logger.info(
                        f"Registration: User can manually review and link to correct player in settings"
                    )

                    player_association_result = "risky_matches_skipped"

                else:
                    # No matches found or error
                    logger.info(
                        f"Registration: No player matches found for {first_name} {last_name} (result: {match_type})"
                    )
                    player_association_result = "no_matches"

            except Exception as match_error:
                logger.warning(
                    f"Registration: Error in enhanced player lookup for {first_name} {last_name}: {str(match_error)}"
                )
                player_association_result = "no_matches"

        # Commit the transaction
        db_session.commit()

        # Log successful registration
        association_detail = {
            "associated": "Player association created with exact match and team assignment verified",
            "associated_legacy": "Player ID found but stored in legacy format - no association record created",
            "no_matches": "No player matches found - registered without association",
            "probable_matches_available": "Probable player matches found but skipped auto-association - user can link manually",
            "risky_matches_skipped": "Risky player matches found but skipped to avoid incorrect association",
            None: "Registered without player search",
        }.get(player_association_result, "Unknown association result")

        # Log legacy activity
        log_user_activity(
            email,
            "auth",
            action="register",
            details=f"Registration successful. {association_detail}",
        )

        # Log comprehensive activity (new system)
        try:
            primary_player = user_data["players"][0] if user_data["players"] else None
            log_activity(
                action_type="user_registration",
                action_description=f"New user {first_name} {last_name} registered successfully",
                user_id=new_user.id,
                player_id=primary_player["id"] if primary_player else None,
                team_id=None,
                related_id=None,
                related_type=None,
                extra_data={
                    "association_result": player_association_result,
                    "association_detail": association_detail,
                    "provided_league": league_name,
                    "provided_club": club_name,
                    "provided_series": series_name,
                    "player_auto_linked": player_association_result == "associated",
                    "team_auto_assigned": player_association_result == "associated",
                },
            )
        except Exception as e:
            # Don't fail registration if activity logging fails
            logger.warning(
                f"Failed to log comprehensive activity for registration: {str(e)}"
            )

        return {
            "success": True,
            "user": user_data,
            "player_association": player_association_result,
            "message": "Registration successful",
        }

    except IntegrityError as e:
        db_session.rollback()
        logger.error(f"Database integrity error during registration: {str(e)}")
        return {"success": False, "error": "Registration failed due to data conflict"}

    except Exception as e:
        db_session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return {"success": False, "error": "Registration failed - server error"}

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

        # If this should be primary, unset other primary associations
        if is_primary:
            db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_id,
                UserPlayerAssociation.is_primary == True,
            ).update({"is_primary": False})

        # Create new association
        association = UserPlayerAssociation(
            user_id=user_id,
            tenniscores_player_id=player.tenniscores_player_id,
            is_primary=is_primary,
        )

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
    Authenticate user and load associated player data
    """
    db_session = SessionLocal()

    try:
        # Get user with all associated player data
        user = db_session.query(User).filter(User.email.ilike(email)).first()

        if not user:
            logger.warning(f"Login attempt failed - user not found: {email}")
            return {"success": False, "error": "Invalid email or password"}

        if not verify_password(user.password_hash, password):
            logger.warning(f"Login attempt failed - invalid password: {email}")
            return {"success": False, "error": "Invalid email or password"}

        # Update last login
        user.last_login = func.now()
        db_session.commit()

        # Load associated players
        associations = (
            db_session.query(UserPlayerAssociation)
            .filter(UserPlayerAssociation.user_id == user.id)
            .all()
        )

        players_data = []
        primary_player = None

        for assoc in associations:
            player = assoc.get_player(db_session)
            if player and player.league and player.club and player.series:
                player_data = {
                    "id": player.id,
                    "name": player.full_name,
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "league": {
                        "id": player.league.id,
                        "league_id": player.league.league_id,
                        "name": player.league.league_name,
                    },
                    "club": {"id": player.club.id, "name": player.club.name},
                    "series": {"id": player.series.id, "name": player.series.name},
                    "tenniscores_player_id": player.tenniscores_player_id,
                    "pti": float(player.pti) if player.pti else None,
                    "wins": player.wins,
                    "losses": player.losses,
                    "win_percentage": (
                        float(player.win_percentage) if player.win_percentage else None
                    ),
                    "captain_status": player.captain_status,
                    "is_primary": assoc.is_primary,
                    "is_active": player.is_active,
                }

                players_data.append(player_data)

                if assoc.is_primary:
                    primary_player = player_data

        user_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
            "ad_deuce_preference": user.ad_deuce_preference,
            "dominant_hand": user.dominant_hand,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "players": players_data,
            "primary_player": primary_player,
        }

        # Log successful login (legacy system)
        log_user_activity(
            email,
            "auth",
            action="login",
            details=f"Login successful. {len(players_data)} associated players",
        )

        # Log comprehensive activity (new system)
        try:
            log_activity(
                action_type="login",
                action_description=f"User {user.first_name} {user.last_name} logged in successfully",
                user_id=user.id,
                player_id=primary_player["id"] if primary_player else None,
                team_id=None,  # We don't have team context during login
                related_id=None,
                related_type=None,
                extra_data={
                    "associated_players_count": len(players_data),
                    "has_primary_player": primary_player is not None,
                    "primary_player_club": (
                        primary_player["club"]["name"] if primary_player else None
                    ),
                    "primary_player_series": (
                        primary_player["series"]["name"] if primary_player else None
                    ),
                },
            )
        except Exception as e:
            # Don't fail login if activity logging fails
            logger.warning(f"Failed to log comprehensive activity for login: {str(e)}")

        return {"success": True, "user": user_data, "message": "Login successful"}

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {"success": False, "error": "Login failed - server error"}

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
                players_data.append(
                    {
                        "id": player.id,
                        "name": player.full_name,
                        "league": player.league.league_name,
                        "club": player.club.name,
                        "series": player.series.name,
                        "tenniscores_player_id": player.tenniscores_player_id,
                        "is_primary": assoc.is_primary,
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


def create_session_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create session data from user record for compatibility with legacy session format
    Converts new schema user data to legacy session format
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

        # Debug logging to verify tenniscores_player_id is properly set
        logger.info(
            f"Session data: tenniscores_player_id = {primary_player.get('tenniscores_player_id')}"
        )
    else:
        # No player association - user has no league/club/series data
        # With normalized schema, all player data comes from associations
        league_name = league_id = club_name = series_name = tenniscores_player_id = ""

        session_data.update(
            {
                "club": club_name,
                "series": series_name,
                "league_id": league_id,  # This will now be 'APTA_CHICAGO' instead of None
                "league_name": league_name,
                "tenniscores_player_id": tenniscores_player_id,  # Use loaded player ID instead of None
                "club_automation_password": "",
            }
        )

    return session_data


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
                UserPlayerAssociation.is_primary == True,
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
