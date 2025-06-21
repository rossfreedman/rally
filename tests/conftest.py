"""
Rally Test Configuration
Pytest fixtures and test database setup for comprehensive testing
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from faker import Faker
import json

# Import Flask app and database models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app
from app.models.database_models import Base, User, Player, League, Club, Series, Team, UserPlayerAssociation
from app.services.auth_service_refactored import hash_password
from database_config import get_db_url

fake = Faker()

# Test database configuration
TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/rally_test')

@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine for the entire test session"""
    engine = create_engine(TEST_DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Clean up after all tests
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a fresh database session for each test with automatic rollback"""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client():
    """Create a Flask test client"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture(scope="function")
def authenticated_client(client, test_user):
    """Create an authenticated test client with a logged-in user"""
    with client.session_transaction() as sess:
        sess['user'] = {
            'id': test_user.id,
            'email': test_user.email,
            'first_name': test_user.first_name,
            'last_name': test_user.last_name,
            'is_admin': test_user.is_admin
        }
    return client

@pytest.fixture
def test_league(db_session):
    """Create a test league"""
    league = League(
        league_id='TEST_LEAGUE',
        league_name='Test League',
        league_url='https://test.tenniscores.com'
    )
    db_session.add(league)
    db_session.commit()
    return league

@pytest.fixture
def test_club(db_session):
    """Create a test club"""
    club = Club(
        name='Test Club',
        club_address='123 Test St, Test City, TX 12345'
    )
    db_session.add(club)
    db_session.commit()
    return club

@pytest.fixture
def test_series(db_session):
    """Create a test series"""
    series = Series(name='Test Series 1')
    db_session.add(series)
    db_session.commit()
    return series

@pytest.fixture
def test_team(db_session, test_club, test_series, test_league):
    """Create a test team"""
    team = Team(
        club_id=test_club.id,
        series_id=test_series.id,
        league_id=test_league.id,
        team_name='Test Club - 1',
        team_alias='TC1'
    )
    db_session.add(team)
    db_session.commit()
    return team

@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        email='test@example.com',
        password_hash=hash_password('testpassword123'),
        first_name='Test',
        last_name='User',
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def admin_user(db_session):
    """Create an admin test user"""
    user = User(
        email='admin@example.com',
        password_hash=hash_password('adminpassword123'),
        first_name='Admin',
        last_name='User',
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_player(db_session, test_league, test_club, test_series, test_team):
    """Create a test player"""
    player = Player(
        tenniscores_player_id='TEST_PLAYER_001',
        first_name='Test',
        last_name='Player',
        league_id=test_league.id,
        club_id=test_club.id,
        series_id=test_series.id,
        team_id=test_team.id,
        pti=1500.50,
        wins=10,
        losses=5,
        win_percentage=66.67
    )
    db_session.add(player)
    db_session.commit()
    return player

@pytest.fixture
def linked_user_player(db_session, test_user, test_player):
    """Create a user-player association"""
    association = UserPlayerAssociation(
        user_id=test_user.id,
        tenniscores_player_id=test_player.tenniscores_player_id,
        is_primary=True
    )
    db_session.add(association)
    db_session.commit()
    return association

@pytest.fixture
def multiple_players(db_session, test_league, test_club, test_series, test_team):
    """Create multiple test players for bulk testing"""
    players = []
    for i in range(5):
        player = Player(
            tenniscores_player_id=f'TEST_PLAYER_{i:03d}',
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            league_id=test_league.id,
            club_id=test_club.id,
            series_id=test_series.id,
            team_id=test_team.id,
            pti=fake.random_int(min=1000, max=2000),
            wins=fake.random_int(min=0, max=20),
            losses=fake.random_int(min=0, max=20)
        )
        players.append(player)
        db_session.add(player)
    
    db_session.commit()
    return players

@pytest.fixture
def scraped_test_data():
    """Load test data scraped from TennisScores"""
    test_data_file = os.path.join(os.path.dirname(__file__), 'fixtures', 'scraped_players.json')
    
    if os.path.exists(test_data_file):
        with open(test_data_file, 'r') as f:
            return json.load(f)
    
    # Return mock data if scraped data not available
    return {
        'valid_players': [
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'club': 'Tennaqua',
                'series': 'Chicago 22',
                'league': 'APTA_CHICAGO',
                'pti': 1650.25,
                'wins': 12,
                'losses': 8
            },
            {
                'first_name': 'Jane',
                'last_name': 'Doe',
                'club': 'Birchwood',
                'series': 'Chicago 15',
                'league': 'APTA_CHICAGO',
                'pti': 1425.75,
                'wins': 8,
                'losses': 12
            }
        ],
        'invalid_players': [
            {
                'first_name': 'Invalid',
                'last_name': 'Player',
                'club': 'NonExistentClub',
                'series': 'InvalidSeries',
                'league': 'FAKE_LEAGUE'
            }
        ]
    }

@pytest.fixture
def mock_security_payloads():
    """Common security test payloads"""
    return {
        'sql_injection': [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "'; SELECT * FROM users WHERE '1'='1",
            "admin'--",
            "admin' /*",
            "' OR 1=1--",
            "' UNION SELECT password FROM users--"
        ],
        'xss_payloads': [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg/onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ],
        'path_traversal': [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd"
        ]
    }

@pytest.fixture
def performance_test_data():
    """Generate large dataset for performance testing"""
    users = []
    players = []
    
    for i in range(100):
        users.append({
            'email': fake.email(),
            'password': 'testpass123',
            'first_name': fake.first_name(),
            'last_name': fake.last_name()
        })
        
        players.append({
            'tenniscores_player_id': f'PERF_TEST_{i:04d}',
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'pti': fake.random_int(min=1000, max=2000),
            'wins': fake.random_int(min=0, max=30),
            'losses': fake.random_int(min=0, max=30)
        })
    
    return {'users': users, 'players': players}

# Utility functions for tests
def create_test_file(content, suffix='.json'):
    """Create a temporary test file"""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'w') as tmp:
            if isinstance(content, dict):
                json.dump(content, tmp, indent=2)
            else:
                tmp.write(content)
        return path
    except:
        os.unlink(path)
        raise

def cleanup_test_files(*paths):
    """Clean up test files"""
    for path in paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except:
            pass

# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration  
pytest.mark.security = pytest.mark.security
pytest.mark.performance = pytest.mark.performance
pytest.mark.regression = pytest.mark.regression 