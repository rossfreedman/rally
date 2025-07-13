# UI Testing for Availability and Pickup Games

## Overview

This document describes the comprehensive UI testing infrastructure added for **Availability Management** and **Pickup Games** functionality in Rally. These tests use Playwright to simulate real human interactions with the Rally frontend.

## 🧪 Test Files Added

### 1. `ui_tests/test_availability_ui.py` (774 lines)
Comprehensive testing of availability management functionality:

- **Availability Page UI**: Loading, form elements, button states
- **Availability Updates**: Setting available/unavailable/not sure status
- **Calendar Interface**: Date selection, month navigation
- **Team Switching**: Multi-team user support
- **Notes Functionality**: Adding and editing availability notes
- **Error Handling**: Network errors, validation failures
- **Accessibility**: Keyboard navigation, ARIA attributes
- **Integration**: Mobile home navigation, persistence

### 2. `ui_tests/test_pickup_games_ui.py` (799 lines)
Complete testing of pickup games functionality:

- **Pickup Games Page UI**: Loading, game listings, filters
- **Game Creation**: Simple and advanced game creation with PTI/series restrictions
- **Game Joining**: Joining and leaving games
- **Game Management**: Editing and deleting games (for creators)
- **Game Finding**: Browsing, filtering, searching
- **Error Handling**: Validation errors, full games
- **Accessibility**: Form accessibility, keyboard navigation
- **Integration**: Mobile home navigation, notifications

## 👥 Users Being Simulated

### Test User Profiles

#### **Regular User** (`uitest@example.com`)
```python
{
    "email": "uitest@example.com",
    "password": "uitestpass123", 
    "first_name": "UI",
    "last_name": "Tester",
    "is_admin": False
}
```
- **Simulates**: Average Rally user
- **Tests**: Availability updates, joining pickup games, basic functionality
- **Permissions**: Standard user access

#### **Admin User** (`uiadmin@example.com`)
```python
{
    "email": "uiadmin@example.com",
    "password": "uiadminpass123",
    "first_name": "UI", 
    "last_name": "Admin",
    "is_admin": True
}
```
- **Simulates**: Rally administrator
- **Tests**: Game management, admin features
- **Permissions**: Full admin access

#### **Test Players** (3 generated players)
```python
# Generated test players with realistic data
{
    "first_name": "UIPlayer0/1/2",
    "last_name": "Test0/1/2", 
    "pti": 1500.0 + (i * 100),  # 1500, 1600, 1700
    "wins": 10 + i,             # 10, 11, 12
    "losses": 5 + i,            # 5, 6, 7
    "team": "UI Test Club - 1"
}
```
- **Simulates**: Real paddle tennis players
- **Tests**: Player association, PTI-based game matching
- **Data**: Realistic PTI ratings, win/loss records

## 🛡️ Safety Features

### 1. **No Real User Notifications**
```python
env.update({
    "TESTING_MODE": "true",           # Enable testing mode
    "DISABLE_NOTIFICATIONS": "true",  # Disable all notifications
    "DISABLE_SMS": "true",           # Disable SMS notifications
    "DISABLE_EMAIL": "true",         # Disable email notifications
})
```

### 2. **Comprehensive Database Cleanup**
```python
def cleanup_test_database(engine):
    """Comprehensive cleanup of all test data"""
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
        
        # Clean up test teams/series/clubs/leagues
        "DELETE FROM teams WHERE team_name LIKE 'UI Test%'",
        "DELETE FROM series WHERE name LIKE 'UI Test%'",
        "DELETE FROM clubs WHERE name LIKE 'UI Test%'",
        "DELETE FROM leagues WHERE league_id LIKE 'UI_TEST_%'",
    ]
```

### 3. **Isolated Test Environment**
- **Test Database**: `rally_test` (separate from production)
- **Test Server**: Runs on port 5001 (separate from main app)
- **Test Data**: All data prefixed with "UI Test" or "uitest"
- **Session Isolation**: Fresh browser context for each test

## 🚀 Running the Tests

### Setup (First Time Only)
```bash
# Create test database
python scripts/setup_ui_test_db.py

# Verify setup
python run_ui_tests.py --check-setup
```

### Test Commands

#### **Availability Tests**
```bash
# Run all availability tests
python run_ui_tests.py --availability

# Run availability smoke tests only
python run_ui_tests.py --availability --smoke

# Run availability critical tests only
python run_ui_tests.py --availability --critical
```

#### **Pickup Games Tests**
```bash
# Run all pickup games tests
python run_ui_tests.py --pickup-games

# Run pickup games smoke tests only
python run_ui_tests.py --pickup-games --smoke

# Run pickup games critical tests only
python run_ui_tests.py --pickup-games --critical
```

#### **Combined Tests**
```bash
# Run all new feature tests
python run_ui_tests.py --availability --pickup-games

# Run critical tests for both features
python run_ui_tests.py --critical --test-pattern "availability or pickup"

# Run smoke tests for both features
python run_ui_tests.py --smoke --test-pattern "availability or pickup"
```

#### **Debug Mode**
```bash
# Run with visible browser for debugging
python run_ui_tests.py --availability --headed --debug

# Run specific test
python run_ui_tests.py --availability -k "test_update_availability_to_available"
```

### Test Categories

#### **Smoke Tests** (Fast, critical functionality)
- Availability page loading
- Basic availability updates
- Pickup games page loading
- Simple game creation
- **~2-3 minutes runtime**

#### **Critical Tests** (Core functionality)
- All availability UI tests
- All pickup games UI tests
- Form validation
- Error handling
- **~5-8 minutes runtime**

#### **Full Test Suite** (Complete coverage)
- All test categories
- Accessibility testing
- Integration testing
- Edge cases
- **~10-15 minutes runtime**

## 🧪 Test Scenarios

### Availability Management

#### **1. Basic Availability Updates**
```python
def test_update_availability_to_available(self, authenticated_page, flask_server):
    """Test updating availability to 'available' status"""
    # Navigate to availability page
    # Click "Count Me In!" button
    # Verify button shows selected state
    # Check for success message
```

#### **2. Calendar Interface**
```python
def test_calendar_day_click(self, authenticated_page, flask_server):
    """Test clicking on a calendar day to update availability"""
    # Navigate to calendar page
    # Click on a calendar day
    # Verify availability options appear
```

#### **3. Team Switching**
```python
def test_availability_with_team_parameter(self, authenticated_page, flask_server):
    """Test accessing availability with team_id parameter"""
    # Access availability with team parameter
    # Verify team context is maintained
    # Check availability data is filtered correctly
```

### Pickup Games

#### **1. Game Creation**
```python
def test_create_simple_pickup_game(self, authenticated_page, flask_server):
    """Test creating a simple pickup game"""
    # Fill out game creation form
    # Submit form
    # Verify success indicators
    # Check game appears in listings
```

#### **2. Game Joining**
```python
def test_join_existing_pickup_game(self, authenticated_page, flask_server):
    """Test joining an existing pickup game"""
    # Create a game to join
    # Navigate to games list
    # Click join button
    # Verify success message
    # Check button changes to "Leave Game"
```

#### **3. Advanced Game Creation**
```python
def test_create_pickup_game_with_advanced_options(self, authenticated_page, flask_server):
    """Test creating a pickup game with PTI and series restrictions"""
    # Fill basic required fields
    # Set PTI range (1500-1700)
    # Set series restrictions
    # Set club-only restriction
    # Submit and verify success
```

## 🔧 Configuration

### Environment Variables
```bash
# Test database
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rally_test

# Test server
TEST_SERVER_URL=http://localhost:5001
TEST_SERVER_PORT=5001

# Testing mode
TESTING_MODE=true
DISABLE_NOTIFICATIONS=true
DISABLE_SMS=true
DISABLE_EMAIL=true
```

### Browser Configuration
```bash
# Default browser (chromium)
BROWSER=chromium

# Headless mode (default)
HEADLESS=true

# Headed mode for debugging
HEADLESS=false
```

## 📊 Test Results

### Success Indicators
- ✅ All tests pass
- ✅ No real user notifications sent
- ✅ Database properly cleaned up
- ✅ Screenshots captured on failures
- ✅ Detailed error reporting

### Failure Handling
- 📸 Screenshots automatically captured
- 🔍 Detailed error messages
- 🧹 Database cleanup still runs
- 📋 Test summary report generated

## 🛠️ Maintenance

### Adding New Tests
1. Add test methods to appropriate test class
2. Use `@pytest.mark.ui` decorator
3. Use `@pytest.mark.smoke` for critical tests
4. Use `@pytest.mark.critical` for core functionality
5. Include proper cleanup in test methods

### Updating Test Data
1. Modify test user data in `conftest.py`
2. Update cleanup queries if needed
3. Test with `--check-setup` flag
4. Verify no real data is affected

### Debugging Failed Tests
1. Run with `--headed` flag to see browser
2. Check screenshots in `ui_tests/screenshots/`
3. Use `--debug` flag for verbose output
4. Check test database state

## 🎯 Best Practices

### Test Design
- **Isolation**: Each test is independent
- **Realism**: Simulate real user behavior
- **Completeness**: Test happy path and error cases
- **Performance**: Keep tests fast and efficient

### Data Management
- **Cleanup**: Always clean up test data
- **Isolation**: Use separate test database
- **Safety**: Never affect real user data
- **Consistency**: Use predictable test data

### Error Handling
- **Graceful**: Handle expected failures
- **Informative**: Provide clear error messages
- **Recovery**: Ensure cleanup runs even on failure
- **Debugging**: Capture screenshots and logs

## 📈 Future Enhancements

### Planned Improvements
1. **Performance Testing**: Load testing for availability updates
2. **Mobile Testing**: Device-specific test scenarios
3. **Accessibility Testing**: Screen reader compatibility
4. **Visual Testing**: UI regression testing
5. **API Integration**: End-to-end workflow testing

### Monitoring
1. **Test Metrics**: Success rates, execution times
2. **Coverage Reports**: Code coverage analysis
3. **Performance Baselines**: Response time tracking
4. **Error Tracking**: Failure pattern analysis

---

This comprehensive UI testing infrastructure ensures that Rally's availability management and pickup games features work reliably and provide a great user experience across all scenarios. 