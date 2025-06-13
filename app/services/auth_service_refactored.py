"""
Rally Authentication Service - Refactored for New Schema
Clean separation between user authentication and player data
"""
import hashlib
import logging
import re
from typing import Dict, List, Optional, Any
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func

from app.models.database_models import (
    User, Player, League, Club, Series, UserPlayerAssociation,
    ClubLeague, SeriesLeague
)
from database_config import get_db_engine
from utils.logging import log_user_activity
from utils.database_player_lookup import find_player_by_database_lookup

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
    logger.warning("convert_series_to_mapping_id is deprecated - database lookups use series names directly")
    return series_name  # Database lookups use the series name as-is

def hash_password(password: str) -> str:
    """Hash a password using Werkzeug's secure method"""
    return generate_password_hash(password, method='pbkdf2:sha256')

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a password against its hash"""
    # Handle old-style hash (format: plain SHA-256)
    if len(stored_password) == 64:  # SHA-256 hash length
        old_hash = hashlib.sha256(provided_password.encode()).hexdigest()
        return stored_password == old_hash
    # Handle new-style Werkzeug hash
    return check_password_hash(stored_password, provided_password)

def find_player_matches(
    first_name: str, 
    last_name: str, 
    league_name: str = None,
    club_name: str = None, 
    series_name: str = None,
    db_session=None
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
                Player.is_active == True
            )
        )
        
        # Add league filter if provided
        if league_name:
            query = query.join(League).filter(
                or_(
                    League.league_name.ilike(f"%{league_name}%"),
                    League.league_id.ilike(f"%{league_name}%")
                )
            )
        
        # Add club filter if provided
        if club_name:
            query = query.join(Club).filter(
                Club.name.ilike(f"%{club_name}%")
            )
        
        # Add series filter if provided
        if series_name:
            query = query.join(Series).filter(
                Series.name.ilike(f"%{series_name}%")
            )
        
        # Include related data for display
        query = query.options(
            db_session.query(Player)
            .join(League)
            .join(Club) 
            .join(Series)
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
        league = db_session.query(League).filter(
            or_(
                League.league_name.ilike(league_name),
                League.league_id.ilike(league_name.upper().replace(' ', '_'))
            )
        ).first()
        
        if not league:
            # Create new league
            league_id = league_name.upper().replace(' ', '_')
            league = League(
                league_id=league_id,
                league_name=league_name
            )
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
        club = db_session.query(Club).filter(
            Club.name.ilike(club_name)
        ).first()
        
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
        series = db_session.query(Series).filter(
            Series.name.ilike(series_name)
        ).first()
        
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
    selected_player_id: int = None
) -> Dict[str, Any]:
    """
    Register a new user with optional player association
    
    Flow:
    1. Create user account 
    2. If player details provided, search for matching players
    3. If single match or player_id provided, create association
    4. If multiple matches, return them for user selection
    5. If no matches, user can register without player association
    """
    db_session = SessionLocal()
    
    try:
        # Hash the password
        hashed_password = hash_password(password)
        
        # Check if user already exists
        existing_user = db_session.query(User).filter(
            User.email.ilike(email)
        ).first()
        
        if existing_user:
            return {
                'success': False, 
                'error': 'User with this email already exists'
            }
        
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
            last_name=last_name
        )
        
        db_session.add(new_user)
        db_session.flush()  # Get the user ID
        
        user_data = {
            'id': new_user.id,
            'email': new_user.email,
            'first_name': new_user.first_name,
            'last_name': new_user.last_name,
            'is_admin': new_user.is_admin,
            'players': []
        }
        
        # Handle player association
        player_association_result = None
        
        if selected_player_id:
            # User selected a specific player from previous search
            player = db_session.query(Player).filter(
                Player.id == selected_player_id,
                Player.is_active == True
            ).first()
            
            if player:
                # Check if association already exists
                existing = db_session.query(UserPlayerAssociation).filter(
                    UserPlayerAssociation.user_id == new_user.id,
                    UserPlayerAssociation.player_id == player.id
                ).first()
                
                if not existing:
                    association = UserPlayerAssociation(
                        user_id=new_user.id,
                        player_id=player.id,
                        is_primary=True
                    )
                    db_session.add(association)
                    player_association_result = 'associated'
                    
                    if player.league and player.club and player.series:
                        user_data['players'] = [{
                            'id': player.id,
                            'name': player.full_name,
                            'league': player.league.league_name,
                            'club': player.club.name,
                            'series': player.series.name,
                            'tenniscores_player_id': player.tenniscores_player_id,
                            'is_primary': True
                        }]
                    
                    logger.info(f"Registration: Created association between user {email} and player {player.full_name} (ID: {player.id})")
                else:
                    player_association_result = 'already_associated'
                    logger.info(f"Registration: User {email} already associated with player {player.full_name}")
            else:
                logger.warning(f"Registration: Selected player ID {selected_player_id} not found")
                player_association_result = 'no_matches'
        
        elif all([first_name, last_name, league_name]):
            # Use database-only player lookup - same as settings update
            try:
                logger.info(f"Registration: Looking up player via database for {first_name} {last_name}")
                
                # Use pure database lookup - NO MORE JSON FILES
                tenniscores_player_id = find_player_by_database_lookup(
                    first_name=first_name,
                    last_name=last_name,
                    club_name=club_name,
                    series_name=series_name,
                    league_id=league_name
                )
                
                if tenniscores_player_id:
                    # Find the actual Player record in the database
                    player = db_session.query(Player).filter(
                        Player.tenniscores_player_id == tenniscores_player_id,
                        Player.is_active == True
                    ).first()
                    
                    if player:
                        # Check if association already exists
                        existing = db_session.query(UserPlayerAssociation).filter(
                            UserPlayerAssociation.user_id == new_user.id,
                            UserPlayerAssociation.player_id == player.id
                        ).first()
                        
                        if not existing:
                            # Create proper user-player association
                            association = UserPlayerAssociation(
                                user_id=new_user.id,
                                player_id=player.id,
                                is_primary=True
                            )
                            db_session.add(association)
                            player_association_result = 'associated'
                            
                            if player.league and player.club and player.series:
                                user_data['players'] = [{
                                    'id': player.id,
                                    'name': player.full_name,
                                    'league': player.league.league_name,
                                    'club': player.club.name,
                                    'series': player.series.name,
                                    'tenniscores_player_id': player.tenniscores_player_id,
                                    'is_primary': True
                                }]
                            
                            logger.info(f"Registration: Created association between user {email} and player {player.full_name} (ID: {player.id})")
                        else:
                            player_association_result = 'already_associated'
                            logger.info(f"Registration: User {email} already associated with player {player.full_name}")
                    else:
                        # Player ID found but no active player record
                        player_association_result = 'no_active_player'
                        logger.warning(f"Registration: Found player ID {tenniscores_player_id} but no active Player record in database")
                else:
                    # No matches found using the database lookup
                    player_association_result = 'no_matches'
                    logger.info(f"Registration: No player matches found for {first_name} {last_name} using database lookup")
                    
            except Exception as match_error:
                logger.warning(f"Registration: Error matching player ID for {first_name} {last_name}: {str(match_error)}")
                player_association_result = 'no_matches'
        
        # Commit the transaction
        db_session.commit()
        
        # Log successful registration
        association_detail = {
            'associated': 'Player association created',
            'associated_legacy': 'Player ID found but stored in legacy format - no association record created',
            'no_matches': 'No player matches found - registered without association', 
            None: 'Registered without player search'
        }.get(player_association_result, 'Unknown association result')
        
        log_user_activity(
            email, 
            'auth', 
            action='register', 
            details=f'Registration successful. {association_detail}'
        )
        
        return {
            'success': True,
            'user': user_data,
            'player_association': player_association_result,
            'message': 'Registration successful'
        }
        
    except IntegrityError as e:
        db_session.rollback()
        logger.error(f"Database integrity error during registration: {str(e)}")
        return {
            'success': False,
            'error': 'Registration failed due to data conflict'
        }
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return {
            'success': False,
            'error': 'Registration failed - server error'
        }
        
    finally:
        db_session.close()

def associate_user_with_player(user_id: int, player_id: int, is_primary: bool = False) -> Dict[str, Any]:
    """
    Associate an existing user with a player record
    Used after registration when user selects from multiple matches
    """
    db_session = SessionLocal()
    
    try:
        # Verify user and player exist
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        player = db_session.query(Player).filter(
            Player.id == player_id,
            Player.is_active == True
        ).first()
        if not player:
            return {'success': False, 'error': 'Player not found or inactive'}
        
        # Check if association already exists
        existing = db_session.query(UserPlayerAssociation).filter(
            UserPlayerAssociation.user_id == user_id,
            UserPlayerAssociation.player_id == player_id
        ).first()
        
        if existing:
            return {'success': False, 'error': 'Association already exists'}
        
        # If this should be primary, unset other primary associations
        if is_primary:
            db_session.query(UserPlayerAssociation).filter(
                UserPlayerAssociation.user_id == user_id,
                UserPlayerAssociation.is_primary == True
            ).update({'is_primary': False})
        
        # Create new association
        association = UserPlayerAssociation(
            user_id=user_id,
            player_id=player_id,
            is_primary=is_primary
        )
        
        db_session.add(association)
        db_session.commit()
        
        logger.info(f"Associated user {user.email} with player {player.full_name}")
        
        return {
            'success': True,
            'message': f'Successfully associated with {player.full_name}'
        }
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error associating user with player: {str(e)}")
        return {
            'success': False,
            'error': 'Failed to create association'
        }
        
    finally:
        db_session.close()

def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """
    Authenticate user and load associated player data
    """
    db_session = SessionLocal()
    
    try:
        # Get user with all associated player data
        user = db_session.query(User).filter(
            User.email.ilike(email)
        ).first()
        
        if not user:
            logger.warning(f"Login attempt failed - user not found: {email}")
            return {'success': False, 'error': 'Invalid email or password'}
        
        if not verify_password(user.password_hash, password):
            logger.warning(f"Login attempt failed - invalid password: {email}")
            return {'success': False, 'error': 'Invalid email or password'}
        
        # Update last login
        user.last_login = func.now()
        db_session.commit()
        
        # Load associated players
        associations = db_session.query(UserPlayerAssociation).filter(
            UserPlayerAssociation.user_id == user.id
        ).all()
        
        players_data = []
        primary_player = None
        
        for assoc in associations:
            player = assoc.player
            if player and player.league and player.club and player.series:
                player_data = {
                    'id': player.id,
                    'name': player.full_name,
                    'first_name': player.first_name,
                    'last_name': player.last_name,
                    'league': {
                        'id': player.league.id,
                        'league_id': player.league.league_id,
                        'name': player.league.league_name
                    },
                    'club': {
                        'id': player.club.id,
                        'name': player.club.name
                    },
                    'series': {
                        'id': player.series.id,
                        'name': player.series.name
                    },
                    'tenniscores_player_id': player.tenniscores_player_id,
                    'pti': float(player.pti) if player.pti else None,
                    'wins': player.wins,
                    'losses': player.losses,
                    'win_percentage': float(player.win_percentage) if player.win_percentage else None,
                    'captain_status': player.captain_status,
                    'is_primary': assoc.is_primary,
                    'is_active': player.is_active
                }
                
                players_data.append(player_data)
                
                if assoc.is_primary:
                    primary_player = player_data
        
        user_data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_admin': user.is_admin,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'players': players_data,
            'primary_player': primary_player
        }
        
        # Log successful login
        log_user_activity(
            email, 
            'auth', 
            action='login', 
            details=f'Login successful. {len(players_data)} associated players'
        )
        
        return {
            'success': True,
            'user': user_data,
            'message': 'Login successful'
        }
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {'success': False, 'error': 'Login failed - server error'}
        
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
        associations = db_session.query(UserPlayerAssociation).filter(
            UserPlayerAssociation.user_id == user.id
        ).all()
        
        players_data = []
        for assoc in associations:
            player = assoc.player
            if player and player.league and player.club and player.series:
                players_data.append({
                    'id': player.id,
                    'name': player.full_name,
                    'league': player.league.league_name,
                    'club': player.club.name,
                    'series': player.series.name,
                    'is_primary': assoc.is_primary
                })
        
        return {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_admin': user.is_admin,
            'players': players_data
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
            {
                'id': league.league_id,
                'name': league.league_name
            }
            for league in leagues
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
            query = query.join(SeriesLeague).join(League).filter(
                League.league_id == league_id
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
    if 'user' in user_data:
        user = user_data['user']
    else:
        user = user_data
    
    # Get primary player for legacy compatibility
    primary_player = user.get('primary_player')
    players = user.get('players', [])
    
    # If no primary player but have players, use the first one
    if not primary_player and players:
        primary_player = players[0]
    
    # Create legacy session format
    session_data = {
        'id': user.get('id'),
        'email': user.get('email'),
        'first_name': user.get('first_name'),
        'last_name': user.get('last_name'),
        'is_admin': user.get('is_admin', False),
        'settings': '{}'  # Default empty settings for legacy compatibility
    }
    
    # Add player-specific data if available
    if primary_player:
        session_data.update({
            'club': primary_player.get('club', {}).get('name') if isinstance(primary_player.get('club'), dict) else primary_player.get('club'),
            'series': primary_player.get('series', {}).get('name') if isinstance(primary_player.get('series'), dict) else primary_player.get('series'),
            'league_id': primary_player.get('league', {}).get('league_id') if isinstance(primary_player.get('league'), dict) else None,
            'league_name': primary_player.get('league', {}).get('name') if isinstance(primary_player.get('league'), dict) else primary_player.get('league'),
            'tenniscores_player_id': primary_player.get('tenniscores_player_id'),
            'club_automation_password': ''  # Legacy field, empty for security
        })
        
        # Debug logging to verify tenniscores_player_id is properly set
        logger.info(f"Session data: tenniscores_player_id = {primary_player.get('tenniscores_player_id')}")
    else:
        # No player association - check if user has direct league/club/series data
        # This handles users who registered but no player was found
        try:
            db_session = SessionLocal()
            user_record = db_session.query(User).filter(User.id == user.get('id')).first()
            
            if user_record:
                league_name = user_record.league.league_name if user_record.league else ''
                league_id = user_record.league.league_id if user_record.league else None  # This will be 'APTA_CHICAGO'
                club_name = user_record.club.name if user_record.club else ''
                series_name = user_record.series.name if user_record.series else ''
                tenniscores_player_id = user_record.tenniscores_player_id  # Load player ID from user record
            else:
                league_name = league_id = club_name = series_name = tenniscores_player_id = ''
            
            db_session.close()
        except Exception as e:
            logger.warning(f"Error loading user league/club/series data: {str(e)}")
            league_name = league_id = club_name = series_name = tenniscores_player_id = ''
        
        session_data.update({
            'club': club_name,
            'series': series_name,
            'league_id': league_id,  # This will now be 'APTA_CHICAGO' instead of None
            'league_name': league_name,
            'tenniscores_player_id': tenniscores_player_id,  # Use loaded player ID instead of None
            'club_automation_password': ''
        })
    
    return session_data 