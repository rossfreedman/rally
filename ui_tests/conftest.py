"""
Rally UI Test Configuration
Playwright-based end-to-end testing setup with Flask server management
"""

import json
import os
import subprocess

# Import Rally models and test data
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database_models import Base, Club, League, Player, Series, Team, User
from app.services.auth_service_refactored import hash_password, register_user
from database_config import get_db_url

import random

# Sample of 10 real users from the player JSON (update as needed)
TEST_USERS = [
    {"first_name": "Mark", "last_name": "Cunnington", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Reece", "last_name": "Acree", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Ryan", "last_name": "Edlefsen", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Mitch", "last_name": "Granger", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Radek", "last_name": "Guzik", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Anthony", "last_name": "McPherson", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Eric", "last_name": "Pohl", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Scott", "last_name": "Rutherford", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Adam", "last_name": "Schumacher", "club": "Glen Ellyn", "series": "Series 1"},
    {"first_name": "Trey", "last_name": "Scott", "club": "Glen Ellyn", "series": "Series 1"},
]

# Test configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rally_test"
)
TEST_SERVER_URL = os.getenv("TEST_SERVER_URL", "http://localhost:8080")
TEST_SERVER_PORT = int(os.getenv("TEST_SERVER_PORT", "8080"))

# Global Flask server process
_flask_server = None
_server_ready = False


@pytest.fixture(scope="session")
def ui_test_database():
    """Set up test database for UI tests"""
    engine = create_engine(TEST_DATABASE_URL)

    # Create all tables - handle existing schema properly
    try:
        Base.metadata.drop_all(engine)
    except Exception as e:
        # If drop fails due to dependencies, drop schema entirely
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.commit()

    Base.metadata.create_all(engine)

    # Create session for seeding data
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed basic test data
    try:
        # Create test league
        league = League(
            league_id="UI_TEST_LEAGUE",
            league_name="UI Test League",
            league_url="https://test.tenniscores.com",
        )
        session.add(league)

        # Create test club
        club = Club(
            name="UI Test Club", club_address="123 Test St, Test City, TX 12345"
        )
        session.add(club)

        # Create test series
        series = Series(name="UI Test Series 1")
        session.add(series)

        session.commit()

        # Create test team
        team = Team(
            club_id=club.id,
            series_id=series.id,
            league_id=league.id,
            team_name="UI Test Club - 1",
            team_alias="UTC1",
        )
        session.add(team)
        session.commit()

        # Create test players
        players = []
        for i in range(3):
            player = Player(
                tenniscores_player_id=f"UI_TEST_PLAYER_{i:03d}",
                first_name=f"UIPlayer{i}",
                last_name=f"Test{i}",
                league_id=league.id,
                club_id=club.id,
                series_id=series.id,
                team_id=team.id,
                pti=1500.0 + (i * 100),
                wins=10 + i,
                losses=5 + i,
            )
            players.append(player)
            session.add(player)

        session.commit()

        # Create test users
        test_users = [
            {
                "email": "uitest@example.com",
                "password": "uitestpass123",
                "first_name": "UI",
                "last_name": "Tester",
                "is_admin": False,
            },
            {
                "email": "uiadmin@example.com",
                "password": "uiadminpass123",
                "first_name": "UI",
                "last_name": "Admin",
                "is_admin": True,
            },
        ]

        for user_data in test_users:
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                is_admin=user_data["is_admin"],
            )
            session.add(user)

        session.commit()

        yield {
            "league": league,
            "club": club,
            "series": series,
            "team": team,
            "players": players,
            "test_users": test_users,
        }

    finally:
        session.close()
        # Comprehensive cleanup of all test data
        cleanup_test_database(engine)
        engine.dispose()


def cleanup_test_database(engine):
    """Comprehensive cleanup of all test data to prevent contamination"""
    try:
        with engine.connect() as conn:
            # Clean up in order to respect foreign key constraints
            cleanup_queries = [
                # Clean up pickup games data
                "DELETE FROM pickup_game_participants WHERE pickup_game_id IN (SELECT id FROM pickup_games WHERE creator_user_id IN (SELECT id FROM users WHERE email LIKE '%uitest%' OR email LIKE '%uiadmin%'))",
                "DELETE FROM pickup_games WHERE creator_user_id IN (SELECT id FROM users WHERE email LIKE '%uitest%' OR email LIKE '%uiadmin%')",
                
                # Clean up availability data
                "DELETE FROM player_availability WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%uitest%' OR email LIKE '%uiadmin%')",
                
                # Clean up user associations
                "DELETE FROM user_player_associations WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%uitest%' OR email LIKE '%uiadmin%')",
                
                # Clean up test users
                "DELETE FROM users WHERE email LIKE '%uitest%' OR email LIKE '%uiadmin%'",
                
                # Clean up test players
                "DELETE FROM players WHERE tenniscores_player_id LIKE 'UI_TEST_%'",
                
                # Clean up test teams
                "DELETE FROM teams WHERE team_name LIKE 'UI Test%'",
                
                # Clean up test series
                "DELETE FROM series WHERE name LIKE 'UI Test%'",
                
                # Clean up test clubs
                "DELETE FROM clubs WHERE name LIKE 'UI Test%'",
                
                # Clean up test leagues
                "DELETE FROM leagues WHERE league_id LIKE 'UI_TEST_%'",
            ]
            
            for query in cleanup_queries:
                try:
                    conn.execute(text(query))
                except Exception as e:
                    print(f"Warning: Cleanup query failed: {e}")
                    # Continue with other cleanup queries
            
            conn.commit()
            print("✅ Test database cleanup completed")
            
    except Exception as e:
        print(f"❌ Error during test database cleanup: {e}")
        # Fallback to schema drop if cleanup fails
        try:
            with engine.connect() as conn:
                conn.execute(text("DROP SCHEMA public CASCADE;"))
                conn.execute(text("CREATE SCHEMA public;"))
                conn.commit()
            print("✅ Fallback schema cleanup completed")
        except Exception as fallback_error:
            print(f"❌ Fallback cleanup also failed: {fallback_error}")


def start_flask_server():
    """Start Flask server for UI testing"""
    global _flask_server, _server_ready

    # Set environment variables for test mode
    env = os.environ.copy()
    env.update(
        {
            "FLASK_ENV": "testing",
            "PORT": str(TEST_SERVER_PORT),
            "DATABASE_URL": TEST_DATABASE_URL,
            "SECRET_KEY": "ui-test-secret-key",
            "WTF_CSRF_ENABLED": "False",  # Disable CSRF for UI tests
            "TESTING_MODE": "true",  # Enable testing mode to prevent real notifications
            "DISABLE_NOTIFICATIONS": "true",  # Disable all notifications during tests
            "DISABLE_SMS": "true",  # Disable SMS notifications
            "DISABLE_EMAIL": "true",  # Disable email notifications
        }
    )

    try:
        _flask_server = subprocess.Popen(
            [sys.executable, "server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )

        # Wait for server to start
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                import requests

                response = requests.get(f"{TEST_SERVER_URL}/health", timeout=1)
                if response.status_code == 200:
                    _server_ready = True
                    print(f"✅ Flask server started on {TEST_SERVER_URL}")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(1)
                continue

        print("❌ Flask server failed to start within 30 seconds")
        return False

    except Exception as e:
        print(f"❌ Error starting Flask server: {e}")
        return False


def stop_flask_server():
    """Stop Flask server"""
    global _flask_server, _server_ready

    if _flask_server:
        _flask_server.terminate()
        _flask_server.wait(timeout=10)
        _flask_server = None
        _server_ready = False
        print("🛑 Flask server stopped")


@pytest.fixture(scope="session")
def flask_server(ui_test_database):
    """Manage Flask server lifecycle for UI tests"""
    # Check if server is already running
    try:
        import requests
        response = requests.get(f"{TEST_SERVER_URL}/health", timeout=2)
        if response.status_code == 200:
            print(f"✅ Using existing Flask server at {TEST_SERVER_URL}")
            yield TEST_SERVER_URL
            return
    except:
        pass
    
    # Start new server if none exists
    if not start_flask_server():
        pytest.skip("Flask server failed to start")

    yield TEST_SERVER_URL

    stop_flask_server()


@pytest.fixture(scope="session")
def playwright():
    """Initialize Playwright"""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser_type(playwright):
    """Get browser type from environment or default to chromium"""
    browser_name = os.getenv("BROWSER", "chromium").lower()

    if browser_name == "firefox":
        return playwright.firefox
    elif browser_name == "webkit":
        return playwright.webkit
    else:
        return playwright.chromium


@pytest.fixture(scope="session")
def browser(browser_type):
    """Launch browser for the test session"""
    # Check if running in CI or headless mode
    headless = os.getenv("HEADLESS", "true").lower() == "true"

    browser = browser_type.launch(
        headless=headless,
        slow_mo=50 if not headless else 0,  # Slow down for debugging
        args=(
            [
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--no-sandbox",
                "--disable-gpu",
            ]
            if headless
            else []
        ),
    )

    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    """Create a fresh browser context for each test"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
        permissions=["clipboard-read", "clipboard-write"],
    )

    yield context
    context.close()


@pytest.fixture
def page(context):
    """Create a fresh page for each test"""
    page = context.new_page()

    # Set longer timeout for UI operations
    page.set_default_timeout(10000)

    yield page


@pytest.fixture
def parameterized_authenticated_page(page, flask_server, request):
    user = request.param
    email = f"{user['first_name'].lower()}.{user['last_name'].lower()}+ui-test@lovetorally.com"
    password = "TestPassword123!"
    # Step 1: Register the user via UI
    page.goto(f"{flask_server}/login")
    page.click('text=Register')
    page.wait_for_selector('#registerForm.active', timeout=10000)
    page.fill('#registerEmail', email)
    page.fill('#registerPassword', password)
    page.fill('#confirmPassword', password)
    page.fill('#firstName', user["first_name"])
    page.fill('#lastName', user["last_name"])
    page.fill('#phoneNumber', '555-123-4567')
    page.wait_for_load_state('networkidle', timeout=10000)
    page.wait_for_function('document.querySelector("#league").options.length > 1', timeout=10000)
    page.select_option('#league', 'APTA_CHICAGO')
    page.wait_for_timeout(1000)
    page.wait_for_function('document.querySelector("#club").options.length > 1', timeout=10000)
    page.select_option('#club', user["club"])
    page.wait_for_timeout(1000)
    page.wait_for_function('document.querySelector("#series").options.length > 1', timeout=10000)
    options = page.eval_on_selector_all('#series option', 'els => els.map(e => ({value: e.value, text: e.textContent}))')
    print('Available series options:', options)
    page.select_option('#series', user["series"])
    page.select_option('#adDeuce', 'Ad')
    page.select_option('#dominantHand', 'Righty')
    page.check('#textNotifications')
    page.wait_for_selector('#registerForm.active button[type="submit"]:not([disabled])', timeout=10000)
    page.click('#registerForm.active button[type="submit"]')
    try:
        page.wait_for_url(url=lambda url: url.endswith('/mobile') or url.endswith('/welcome') or url.endswith('/'), timeout=15000)
    except Exception as e:
        page.screenshot(path='registration_failure.png')
        print('📸 Screenshot saved as registration_failure.png')
        try:
            error_text = page.inner_text('#registerErrorMessage')
            print('Registration error message:', error_text)
        except Exception:
            print('No #registerErrorMessage found. Printing page content:')
            print(page.content())
        raise
    # Step 2: Log out to test login flow
    page.goto(f"{flask_server}/logout")
    # Step 3: Login with the newly registered user
    page.goto(f"{flask_server}/login")
    page.fill('#loginEmail', email)
    page.fill('#loginPassword', password)
    page.click('button[type="submit"]')
    page.wait_for_url(url=lambda url: url.endswith('/mobile') or url.endswith('/welcome') or url.endswith('/'), timeout=10000)
    yield page

@pytest.fixture
def authenticated_page(page, flask_server):
    user = {
        "first_name": "Tom",
        "last_name": "Morton",
        "club": "Wilmette PD I",
        "series": "Series 2"
    }
    email = f"{user['first_name'].lower()}.{user['last_name'].lower()}+ui-test@lovetorally.com"
    password = "TestPassword123!"
    # Step 1: Register the user via UI
    page.goto(f"{flask_server}/login")
    page.click('text=Register')
    page.wait_for_selector('#registerForm.active', timeout=10000)
    page.fill('#registerEmail', email)
    page.fill('#registerPassword', password)
    page.fill('#confirmPassword', password)
    page.fill('#firstName', user["first_name"])
    page.fill('#lastName', user["last_name"])
    page.fill('#phoneNumber', '555-123-4567')
    page.wait_for_load_state('networkidle', timeout=10000)
    page.wait_for_function('document.querySelector("#league").options.length > 1', timeout=10000)
    page.select_option('#league', 'APTA_CHICAGO')
    page.wait_for_timeout(1000)
    page.wait_for_function('document.querySelector("#club").options.length > 1', timeout=10000)
    page.select_option('#club', user["club"])
    page.wait_for_timeout(1000)
    page.wait_for_function('document.querySelector("#series").options.length > 1', timeout=10000)
    options = page.eval_on_selector_all('#series option', 'els => els.map(e => ({value: e.value, text: e.textContent}))')
    print('Available series options:', options)
    page.select_option('#series', user["series"])
    page.select_option('#adDeuce', 'Ad')
    page.select_option('#dominantHand', 'Righty')
    page.check('#textNotifications')
    page.wait_for_selector('#registerForm.active button[type="submit"]:not([disabled])', timeout=10000)
    page.click('#registerForm.active button[type="submit"]')
    try:
        page.wait_for_url(url=lambda url: url.endswith('/mobile') or url.endswith('/welcome') or url.endswith('/'), timeout=15000)
    except Exception as e:
        page.screenshot(path='registration_failure.png')
        print('📸 Screenshot saved as registration_failure.png')
        try:
            error_text = page.inner_text('#registerErrorMessage')
            print('Registration error message:', error_text)
        except Exception:
            print('No #registerErrorMessage found. Printing page content:')
            print(page.content())
        raise
    # Step 2: Log out to test login flow
    page.goto(f"{flask_server}/logout")
    # Step 3: Login with the newly registered user
    page.goto(f"{flask_server}/login")
    page.fill('#loginEmail', email)
    page.fill('#loginPassword', password)
    page.click('button[type="submit"]')
    page.wait_for_url(url=lambda url: url.endswith('/mobile') or url.endswith('/welcome') or url.endswith('/'), timeout=10000)
    yield page


@pytest.fixture
def admin_page(page, flask_server, ui_test_database):
    """Create a page with authenticated admin user session via UI registration and login"""
    admin_user = ui_test_database["test_users"][1]  # Admin user
    # Step 1: Register the admin user via UI
    page.goto(f"{flask_server}/login")
    # Switch to registration tab
    page.click('text=Register')
    
    # Wait for registration form to be visible
    page.wait_for_selector('#registerForm.active', timeout=10000)
    
    # Fill registration form
    page.fill('#registerEmail', admin_user["email"])
    page.fill('#registerPassword', admin_user["password"])
    page.fill('#confirmPassword', admin_user["password"])
    page.fill('#firstName', admin_user["first_name"])
    page.fill('#lastName', admin_user["last_name"])
    page.fill('#phoneNumber', '555-987-6543')  # Default test phone
    # Wait for leagues to load and select a real league
    # Wait for the API call to complete by waiting for network idle
    page.wait_for_load_state('networkidle', timeout=10000)
    # Wait for the league dropdown to be populated (check for more than just the default option)
    page.wait_for_function('document.querySelector("#league").options.length > 1', timeout=10000)
    page.select_option('#league', 'APTA_CHICAGO')
    page.wait_for_timeout(1000)
    # Wait for clubs to load and select a real club
    page.wait_for_function('document.querySelector("#club").options.length > 1', timeout=10000)
    page.select_option('#club', 'Tennaqua')
    page.wait_for_timeout(1000)
    # Wait for series to load and select a real series
    page.wait_for_function('document.querySelector("#series").options.length > 1', timeout=10000)
    page.select_option('#series', 'Series 7')
    # Select preferences
    page.select_option('#adDeuce', 'Ad')
    page.select_option('#dominantHand', 'Righty')
    # Check the text notifications checkbox
    page.check('#textNotifications')
    # Wait for the submit button to be visible and enabled
    page.wait_for_selector('#registerForm.active button[type="submit"]:not([disabled])', timeout=10000)
    # Submit registration form
    page.click('#registerForm.active button[type="submit"]')
    # Wait for registration to complete and redirect
    try:
        page.wait_for_url(url=lambda url: url.endswith('/mobile') or url.endswith('/welcome') or url.endswith('/'), timeout=15000)
    except Exception as e:
        # Capture screenshot
        page.screenshot(path='registration_failure.png')
        print('📸 Screenshot saved as registration_failure.png')
        # Try to print error message if present
        try:
            error_text = page.inner_text('#registerErrorMessage')
            print('Registration error message:', error_text)
        except Exception:
            print('No #registerErrorMessage found. Printing page content:')
            print(page.content())
        raise
    # Step 2: Log out to test login flow
    page.goto(f"{flask_server}/logout")
    # Step 3: Login with the newly registered admin user
    page.goto(f"{flask_server}/login")
    # Fill and submit login form
    page.fill('#loginEmail', admin_user["email"])
    page.fill('#loginPassword', admin_user["password"])
    page.click('button[type="submit"]')
    # Wait for the JavaScript redirect to happen
    page.wait_for_url(url=lambda url: url.endswith('/mobile') or url.endswith('/welcome') or url.endswith('/'), timeout=10000)
    yield page


@pytest.fixture
def test_player_data():
    """Load test player data from scraped fixtures"""
    fixtures_path = Path(__file__).parent.parent / "tests" / "fixtures"
    scraped_file = fixtures_path / "scraped_players.json"

    if scraped_file.exists():
        with open(scraped_file, "r") as f:
            return json.load(f)

    # Fallback mock data
    return {
        "valid_players": [
            {
                "first_name": "UI",
                "last_name": "TestPlayer1",
                "club": "UI Test Club",
                "series": "UI Test Series 1",
                "league": "UI_TEST_LEAGUE",
                "pti": 1600.0,
            },
            {
                "first_name": "UI",
                "last_name": "TestPlayer2",
                "club": "UI Test Club",
                "series": "UI Test Series 1",
                "league": "UI_TEST_LEAGUE",
                "pti": 1500.0,
            },
        ],
        "invalid_players": [
            {
                "first_name": "Nonexistent",
                "last_name": "Player",
                "club": "Fake Club",
                "series": "Fake Series",
                "league": "FAKE_LEAGUE",
            }
        ],
    }


# Utility functions for UI tests
def wait_for_page_load(page, timeout=5000):
    """Wait for page to fully load"""
    page.wait_for_load_state("networkidle", timeout=timeout)


def take_screenshot_on_failure(page, test_name):
    """Take screenshot when test fails"""
    screenshot_dir = Path(__file__).parent / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)

    screenshot_path = screenshot_dir / f"{test_name}_{int(time.time())}.png"
    page.screenshot(path=str(screenshot_path))
    print(f"📸 Screenshot saved: {screenshot_path}")


def assert_toast_message(page, expected_message, timeout=3000):
    """Assert that a toast/notification message appears"""
    toast_selectors = [
        ".toast",
        ".alert",
        ".notification",
        ".message",
        '[data-testid="toast"]',
        '[data-testid="alert"]',
    ]

    for selector in toast_selectors:
        try:
            toast = page.wait_for_selector(selector, timeout=timeout)
            if toast and expected_message.lower() in toast.text_content().lower():
                return True
        except:
            continue

    return False


def fill_form_field(page, field_name, value):
    """Fill form field using multiple selector strategies"""
    selectors = [
        f'input[name="{field_name}"]',
        f"#{field_name}",
        f'[data-testid="{field_name}"]',
        f'[placeholder*="{field_name}"]',
    ]

    for selector in selectors:
        try:
            if page.is_visible(selector):
                page.fill(selector, str(value))
                return True
        except:
            continue

    raise Exception(f"Could not find form field: {field_name}")


# Pytest hooks for better UI test reporting
def pytest_runtest_makereport(item, call):
    """Take screenshot on test failure"""
    if call.when == "call" and call.excinfo is not None:
        # Get page fixture if available
        if hasattr(item, "funcargs") and "page" in item.funcargs:
            page = item.funcargs["page"]
            take_screenshot_on_failure(page, item.name)


# Custom markers for UI tests
pytest.mark.ui = pytest.mark.ui
pytest.mark.smoke = pytest.mark.smoke
pytest.mark.critical = pytest.mark.critical
