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

# Test configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rally_test"
)
TEST_SERVER_URL = os.getenv("TEST_SERVER_URL", "http://localhost:5001")
TEST_SERVER_PORT = int(os.getenv("TEST_SERVER_PORT", "5001"))

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
        # Clean up database with CASCADE to handle foreign key constraints
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.commit()
        engine.dispose()


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
def authenticated_page(page, flask_server, ui_test_database):
    """Create a page with authenticated user session"""
    test_user = ui_test_database["test_users"][0]  # Regular user

    # Navigate to login page
    page.goto(f"{flask_server}/login")

    # Fill and submit login form
    page.fill('input[name="email"]', test_user["email"])
    page.fill('input[name="password"]', test_user["password"])
    page.click('button[type="submit"]')

    # Wait for redirect to mobile page
    page.wait_for_url(url=f"{flask_server}/mobile", timeout=5000)

    yield page


@pytest.fixture
def admin_page(page, flask_server, ui_test_database):
    """Create a page with authenticated admin user session"""
    admin_user = ui_test_database["test_users"][1]  # Admin user

    # Navigate to login page
    page.goto(f"{flask_server}/login")

    # Fill and submit login form
    page.fill('input[name="email"]', admin_user["email"])
    page.fill('input[name="password"]', admin_user["password"])
    page.click('button[type="submit"]')

    # Wait for redirect
    page.wait_for_url(url=f"{flask_server}/mobile", timeout=5000)

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
