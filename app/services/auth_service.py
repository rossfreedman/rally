import hashlib
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from utils.match_utils import find_player_id_by_club_name

logger = logging.getLogger(__name__)

def convert_series_to_mapping_id(series_name, club_name, league_id=None):
    """
    Convert database series name to the format used in player data.
    APTA Chicago: 'Chicago 19' + 'Tennaqua' -> 'Tennaqua - 19'
    NSTF: 'Series 2B' + 'Tennaqua' -> 'Tennaqua S2B'
    """
    import re
    
    # For NSTF leagues, use different format
    if league_id == 'NSTF':
        # Extract series info: 'Series 2B' -> 'S2B'
        if series_name.startswith('Series '):
            series_part = series_name.replace('Series ', 'S')
            return f"{club_name} {series_part}"
        else:
            # Fallback for NSTF
            return f"{club_name} {series_name}"
    
    # For APTA leagues, use the dash format
    else:
        # Extract the series number from series name
        numbers = re.findall(r'\d+', series_name)
        if numbers:
            series_number = numbers[-1]  # Take the last number found
            return f"{club_name} - {series_number}"
        else:
            # Fallback: return the original series name
            return series_name

def hash_password(password):
    """Hash a password using Werkzeug's secure method"""
    return generate_password_hash(password, method='pbkdf2:sha256')

def verify_password(stored_password, provided_password):
    """Verify a password against its hash"""
    # Handle old-style hash (format: plain SHA-256)
    if len(stored_password) == 64:  # SHA-256 hash length
        old_hash = hashlib.sha256(provided_password.encode()).hexdigest()
        return stored_password == old_hash
    # Handle new-style Werkzeug hash
    return check_password_hash(stored_password, provided_password)

def register_user(email, password, first_name, last_name, club_name, series_name, league_id=None):
    """Register a new user with all validation and setup"""
    try:
        # Hash the password
        hashed_password = hash_password(password)

        # Get club and series IDs
        club_id = execute_query_one(
            "SELECT id FROM clubs WHERE name = %(club)s",
            {'club': club_name}
        )['id']
        
        series_id = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s",
            {'series': series_name}
        )['id']
        
        # Get league ID (default to APTA_CHICAGO if not specified)
        if not league_id:
            league_id = 'APTA_CHICAGO'
        
        league_db_id = execute_query_one(
            "SELECT id FROM leagues WHERE league_id = %(league_id)s",
            {'league_id': league_id}
        )['id']

        # Check if user already exists
        existing_user = execute_query_one(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(%(email)s)",
            {'email': email}
        )
        
        if existing_user:
            return {'success': False, 'error': 'User already exists'}

        # Attempt to find Tenniscores Player ID
        tenniscores_player_id = None
        try:
            # Convert series name to mapping ID format for player lookup
            series_mapping_id = convert_series_to_mapping_id(series_name, club_name, league_id)
            logger.info(f"Registration: Looking up player with mapping ID: {series_mapping_id}")
            
            # Convert league_id to the format used in player data
            league_filter = None
            if league_id == 'APTA_CHICAGO':
                league_filter = 'APTA_CHICAGO'
            elif league_id == 'NSTF':
                league_filter = 'NSTF'  # Player data uses NSTF
            elif league_id == 'APTA_NATIONAL':
                league_filter = 'APTA_NATIONAL'
            
            tenniscores_player_id = find_player_id_by_club_name(
                first_name=first_name,
                last_name=last_name,
                series_mapping_id=series_mapping_id,
                club_name=club_name,
                league=league_filter
            )
            if tenniscores_player_id:
                logger.info(f"Found Tenniscores Player ID for {first_name} {last_name}: {tenniscores_player_id}")
            else:
                logger.info(f"No Tenniscores Player ID found for {first_name} {last_name} ({club_name}, {series_mapping_id})")
        except Exception as match_error:
            logger.warning(f"Error matching player ID for {first_name} {last_name}: {str(match_error)}")
            # Continue with registration even if matching fails
            tenniscores_player_id = None

        # Insert new user with tenniscores_player_id and league_id
        success = execute_update(
            """
            INSERT INTO users (email, password_hash, first_name, last_name, club_id, series_id, league_id, tenniscores_player_id)
            VALUES (%(email)s, %(password_hash)s, %(first_name)s, %(last_name)s, %(club_id)s, %(series_id)s, %(league_id)s, %(tenniscores_player_id)s)
            """,
            {
                'email': email,
                'password_hash': hashed_password,
                'first_name': first_name,
                'last_name': last_name,
                'club_id': club_id,
                'series_id': series_id,
                'league_id': league_db_id,
                'tenniscores_player_id': tenniscores_player_id
            }
        )

        if not success:
            logger.error("Failed to insert new user")
            return {'success': False, 'error': 'Registration failed'}

        # Get the newly created user with club, series, and league info
        user = execute_query_one(
            """
            SELECT u.id, u.email, u.first_name, u.last_name,
                   c.name as club_name, s.name as series_name, u.tenniscores_player_id,
                   u.club_automation_password, u.is_admin,
                   l.league_id, l.league_name
            FROM users u
            JOIN clubs c ON u.club_id = c.id
            JOIN series s ON u.series_id = s.id
            JOIN leagues l ON u.league_id = l.id
            WHERE LOWER(u.email) = LOWER(%(email)s)
            """,
            {'email': email}
        )

        # Log successful registration with player ID info
        match_detail = f"Matched to Player ID: {tenniscores_player_id}" if tenniscores_player_id else "No Player ID match found"
        log_user_activity(email, 'auth', action='register', details=f'Registration successful. {match_detail}')
        
        return {
            'success': True,
            'user': user,
            'message': 'Registration successful'
        }

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return {'success': False, 'error': 'Registration failed - server error'}

def authenticate_user(email, password):
    """Authenticate a user with email and password"""
    try:
        # Get user with club, series, and league info
        user = execute_query_one(
            """
            SELECT u.id, u.email, u.password_hash, u.first_name, u.last_name,
                   c.name as club_name, s.name as series_name, u.tenniscores_player_id,
                   u.club_automation_password, u.is_admin,
                   l.league_id, l.league_name
            FROM users u
            JOIN clubs c ON u.club_id = c.id
            JOIN series s ON u.series_id = s.id
            LEFT JOIN leagues l ON u.league_id = l.id
            WHERE LOWER(u.email) = LOWER(%(email)s)
            """,
            {'email': email}
        )

        if not user:
            logger.warning(f"Login attempt failed - user not found: {email}")
            return {'success': False, 'error': 'Invalid email or password'}

        if not verify_password(user['password_hash'], password):
            logger.warning(f"Login attempt failed - invalid password: {email}")
            return {'success': False, 'error': 'Invalid email or password'}

        # Log successful login
        log_user_activity(email, 'auth', action='login', details='Login successful')

        return {
            'success': True,
            'user': user,
            'message': 'Login successful'
        }

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {'success': False, 'error': 'Login failed - server error'}

def create_session_data(user):
    """Create session data from user record"""
    return {
        'id': user['id'],
        'email': user['email'],
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'club': user['club_name'],
        'series': user['series_name'],
        'league_id': user.get('league_id'),
        'league_name': user.get('league_name'),
        'club_automation_password': user.get('club_automation_password', ''),
        'is_admin': user.get('is_admin', False),
        'tenniscores_player_id': user['tenniscores_player_id'],
        'settings': '{}'  # Default empty settings
    }

def get_clubs_list():
    """Get list of all clubs for registration"""
    try:
        clubs_data = execute_query("SELECT name FROM clubs ORDER BY name")
        return [club['name'] for club in clubs_data]
    except Exception as e:
        logger.error(f"Error getting clubs: {str(e)}")
        raise 