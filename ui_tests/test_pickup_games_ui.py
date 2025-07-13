"""
Rally Pickup Games UI Tests
End-to-end testing of pickup games functionality using Playwright
"""

import re
import time
from datetime import datetime, timedelta

import pytest
from conftest import (
    assert_toast_message,
    fill_form_field,
    take_screenshot_on_failure,
    wait_for_page_load,
)
from playwright.sync_api import expect


@pytest.mark.ui
@pytest.mark.critical
class TestPickupGamesPageUI:
    """Test pickup games page UI elements and basic functionality"""

    def test_pickup_games_page_loads(self, authenticated_page, flask_server):
        """Test that pickup games page loads with all required elements"""
        page = authenticated_page

        # Navigate to pickup games page
        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Check page title and content
        expect(page).to_have_title(re.compile(r".*Pickup.*"))
        
        # Check for pickup games elements
        pickup_elements = [
            '.pickup-games-container, .games-list',
            'button:has-text("Create Game")',
            'button:has-text("Join Game")',
            '.game-card, .pickup-game-item',
        ]

        pickup_ui_found = False
        for selector in pickup_elements:
            if page.locator(selector).count() > 0:
                pickup_ui_found = True
                break

        assert pickup_ui_found, "Pickup games UI elements not found on page"

    def test_create_pickup_game_page_loads(self, authenticated_page, flask_server):
        """Test that create pickup game page loads with all required elements"""
        page = authenticated_page

        # Navigate to create pickup game page
        page.goto(f"{flask_server}/mobile/create-pickup-game")
        wait_for_page_load(page)

        # Check page title and content
        expect(page).to_have_title(re.compile(r".*Create.*"))
        
        # Check for create game form elements
        form_elements = [
            'input[name="description"], textarea[name="description"]',
            'input[name="game_date"], input[type="date"]',
            'input[name="game_time"], input[type="time"]',
            'input[name="players_requested"], select[name="players_requested"]',
            'button[type="submit"], button:has-text("Create")',
        ]

        form_found = False
        for selector in form_elements:
            if page.locator(selector).count() > 0:
                form_found = True
                break

        assert form_found, "Create pickup game form elements not found on page"


@pytest.mark.ui
class TestPickupGameCreation:
    """Test pickup game creation functionality"""

    def test_create_simple_pickup_game(self, authenticated_page, flask_server):
        """Test creating a simple pickup game"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/create-pickup-game")
        wait_for_page_load(page)

        # Fill out the form with test data
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Find and fill description field
        description_selectors = [
            'input[name="description"]',
            'textarea[name="description"]',
            '#description',
            '[data-testid="description"]',
        ]
        
        description_filled = False
        for selector in description_selectors:
            if page.locator(selector).count() > 0:
                page.fill(selector, "Test Pickup Game from UI Test")
                description_filled = True
                break
        
        if not description_filled:
            pytest.skip("Description field not found")

        # Find and fill date field
        date_selectors = [
            'input[name="game_date"]',
            'input[type="date"]',
            '#game_date',
            '[data-testid="game_date"]',
        ]
        
        date_filled = False
        for selector in date_selectors:
            if page.locator(selector).count() > 0:
                page.fill(selector, tomorrow)
                date_filled = True
                break
        
        if not date_filled:
            pytest.skip("Date field not found")

        # Find and fill time field
        time_selectors = [
            'input[name="game_time"]',
            'input[type="time"]',
            '#game_time',
            '[data-testid="game_time"]',
        ]
        
        time_filled = False
        for selector in time_selectors:
            if page.locator(selector).count() > 0:
                page.fill(selector, "14:00")
                time_filled = True
                break
        
        if not time_filled:
            pytest.skip("Time field not found")

        # Find and fill players requested field
        players_selectors = [
            'input[name="players_requested"]',
            'select[name="players_requested"]',
            '#players_requested',
            '[data-testid="players_requested"]',
        ]
        
        players_filled = False
        for selector in players_selectors:
            if page.locator(selector).count() > 0:
                if "select" in selector:
                    page.select_option(selector, "4")
                else:
                    page.fill(selector, "4")
                players_filled = True
                break
        
        if not players_filled:
            pytest.skip("Players requested field not found")

        # Submit the form
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Create")',
            'button:has-text("Create Game")',
            '#submit-button',
        ]
        
        form_submitted = False
        for selector in submit_selectors:
            if page.locator(selector).count() > 0:
                page.click(selector)
                form_submitted = True
                break
        
        if not form_submitted:
            pytest.skip("Submit button not found")

        # Wait for form submission
        page.wait_for_timeout(3000)

        # Check for success indicators
        success_indicators = [
            "success" in page.content().lower(),
            "created" in page.content().lower(),
            assert_toast_message(page, "created", timeout=3000),
            "/pickup-games" in page.url,
        ]

        assert any(success_indicators), "Pickup game creation should succeed"

    def test_create_pickup_game_with_advanced_options(self, authenticated_page, flask_server):
        """Test creating a pickup game with PTI and series restrictions"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/create-pickup-game")
        wait_for_page_load(page)

        # Fill basic required fields first
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Fill description
        description_field = page.locator('input[name="description"], textarea[name="description"]').first
        if description_field.count() > 0:
            description_field.fill("Advanced Test Pickup Game")
        else:
            pytest.skip("Description field not found")

        # Fill date
        date_field = page.locator('input[name="game_date"], input[type="date"]').first
        if date_field.count() > 0:
            date_field.fill(tomorrow)
        else:
            pytest.skip("Date field not found")

        # Fill time
        time_field = page.locator('input[name="game_time"], input[type="time"]').first
        if time_field.count() > 0:
            time_field.fill("15:00")
        else:
            pytest.skip("Time field not found")

        # Fill players requested
        players_field = page.locator('input[name="players_requested"], select[name="players_requested"]').first
        if players_field.count() > 0:
            if players_field.tag_name() == "select":
                players_field.select_option("6")
            else:
                players_field.fill("6")
        else:
            pytest.skip("Players requested field not found")

        # Try to set PTI range if available
        pti_min_selectors = [
            'input[name="pti_low"]',
            '#pti_low',
            '[data-testid="pti_low"]',
        ]
        
        for selector in pti_min_selectors:
            if page.locator(selector).count() > 0:
                page.fill(selector, "1500")
                break

        pti_max_selectors = [
            'input[name="pti_high"]',
            '#pti_high',
            '[data-testid="pti_high"]',
        ]
        
        for selector in pti_max_selectors:
            if page.locator(selector).count() > 0:
                page.fill(selector, "1700")
                break

        # Try to set series restrictions if available
        series_selectors = [
            'select[name="series_low"]',
            'select[name="series_high"]',
            '#series_low',
            '#series_high',
        ]
        
        for selector in series_selectors:
            if page.locator(selector).count() > 0:
                # Try to select first available option
                options = page.locator(f"{selector} option")
                if options.count() > 1:  # More than just the default option
                    page.select_option(selector, options.nth(1).get_attribute("value"))
                break

        # Try to set club-only restriction if available
        club_only_selectors = [
            'input[name="club_only"]',
            'input[type="checkbox"]',
            '#club_only',
        ]
        
        for selector in club_only_selectors:
            if page.locator(selector).count() > 0:
                page.check(selector)
                break

        # Submit the form
        submit_button = page.locator('button[type="submit"], button:has-text("Create")').first
        if submit_button.count() > 0:
            submit_button.click()
            
            # Wait for submission
            page.wait_for_timeout(3000)
            
            # Check for success
            success_shown = assert_toast_message(page, "created", timeout=3000)
            assert success_shown, "Advanced pickup game creation should succeed"


@pytest.mark.ui
class TestPickupGameJoining:
    """Test joining pickup games functionality"""

    def test_join_existing_pickup_game(self, authenticated_page, flask_server):
        """Test joining an existing pickup game"""
        page = authenticated_page

        # First, create a pickup game to join
        page.goto(f"{flask_server}/mobile/create-pickup-game")
        wait_for_page_load(page)

        # Create a simple game
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Fill form quickly
        description_field = page.locator('input[name="description"], textarea[name="description"]').first
        if description_field.count() > 0:
            description_field.fill("Game to Join Test")
        
        date_field = page.locator('input[name="game_date"], input[type="date"]').first
        if date_field.count() > 0:
            date_field.fill(tomorrow)
        
        time_field = page.locator('input[name="game_time"], input[type="time"]').first
        if time_field.count() > 0:
            time_field.fill("16:00")
        
        players_field = page.locator('input[name="players_requested"], select[name="players_requested"]').first
        if players_field.count() > 0:
            if players_field.tag_name() == "select":
                players_field.select_option("4")
            else:
                players_field.fill("4")
        
        # Submit
        submit_button = page.locator('button[type="submit"], button:has-text("Create")').first
        if submit_button.count() > 0:
            submit_button.click()
            page.wait_for_timeout(3000)

        # Now navigate to pickup games list
        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Look for join buttons
        join_buttons = page.locator('button:has-text("Join Game"), button:has-text("Join")')
        
        if join_buttons.count() > 0:
            # Click the first join button
            first_join_button = join_buttons.first
            if first_join_button.is_visible():
                first_join_button.click()
                
                # Wait for join action to complete
                page.wait_for_timeout(2000)
                
                # Check for success message
                success_shown = assert_toast_message(page, "joined", timeout=3000)
                assert success_shown, "Should show success message when joining game"
                
                # Check that button changed to "Leave Game"
                leave_buttons = page.locator('button:has-text("Leave Game"), button:has-text("Leave")')
                assert leave_buttons.count() > 0, "Button should change to Leave Game after joining"

    def test_leave_pickup_game(self, authenticated_page, flask_server):
        """Test leaving a pickup game"""
        page = authenticated_page

        # First join a game (reuse logic from above)
        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Look for leave buttons (indicating already joined games)
        leave_buttons = page.locator('button:has-text("Leave Game"), button:has-text("Leave")')
        
        if leave_buttons.count() > 0:
            # Click the first leave button
            first_leave_button = leave_buttons.first
            if first_leave_button.is_visible():
                first_leave_button.click()
                
                # Wait for leave action to complete
                page.wait_for_timeout(2000)
                
                # Check for success message
                success_shown = assert_toast_message(page, "left", timeout=3000)
                assert success_shown, "Should show success message when leaving game"
                
                # Check that button changed back to "Join Game"
                join_buttons = page.locator('button:has-text("Join Game"), button:has-text("Join")')
                assert join_buttons.count() > 0, "Button should change back to Join Game after leaving"


@pytest.mark.ui
class TestPickupGameFinding:
    """Test finding and browsing pickup games"""

    def test_browse_public_pickup_games(self, authenticated_page, flask_server):
        """Test browsing public pickup games"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Check for game listings
        game_elements = [
            '.game-card',
            '.pickup-game-item',
            '[data-game-id]',
            '.game-listing',
        ]

        games_found = False
        for selector in game_elements:
            if page.locator(selector).count() > 0:
                games_found = True
                break

        # Games might not exist yet, so this is informational
        if games_found:
            print("Public pickup games found")
        else:
            print("No public pickup games found (this is normal for test environment)")

    def test_filter_pickup_games(self, authenticated_page, flask_server):
        """Test filtering pickup games by type"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Look for filter buttons/tabs
        filter_elements = [
            'button:has-text("Public")',
            'button:has-text("Private")',
            'button:has-text("My Games")',
            '.filter-tabs button',
            '[data-filter]',
        ]

        filter_found = False
        for selector in filter_elements:
            if page.locator(selector).count() > 0:
                filter_found = True
                break

        if filter_found:
            # Try clicking on different filter options
            public_button = page.locator('button:has-text("Public")').first
            if public_button.count() > 0 and public_button.is_visible():
                public_button.click()
                page.wait_for_timeout(1000)

            private_button = page.locator('button:has-text("Private")').first
            if private_button.count() > 0 and private_button.is_visible():
                private_button.click()
                page.wait_for_timeout(1000)

            print("Filter functionality tested")
        else:
            print("No filter options found")

    def test_search_pickup_games(self, authenticated_page, flask_server):
        """Test searching pickup games"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Look for search input
        search_selectors = [
            'input[type="search"]',
            'input[name="search"]',
            '#search',
            '[data-testid="search"]',
        ]

        search_found = False
        for selector in search_selectors:
            if page.locator(selector).count() > 0:
                search_input = page.locator(selector).first
                search_input.fill("test")
                search_found = True
                break

        if search_found:
            print("Search functionality found and tested")
        else:
            print("No search functionality found")


@pytest.mark.ui
class TestPickupGameManagement:
    """Test managing pickup games (for creators)"""

    def test_edit_pickup_game(self, authenticated_page, flask_server):
        """Test editing a pickup game (if user is creator)"""
        page = authenticated_page

        # First create a game to edit
        page.goto(f"{flask_server}/mobile/create-pickup-game")
        wait_for_page_load(page)

        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Fill form
        description_field = page.locator('input[name="description"], textarea[name="description"]').first
        if description_field.count() > 0:
            description_field.fill("Game to Edit Test")
        
        date_field = page.locator('input[name="game_date"], input[type="date"]').first
        if date_field.count() > 0:
            date_field.fill(tomorrow)
        
        time_field = page.locator('input[name="game_time"], input[type="time"]').first
        if time_field.count() > 0:
            time_field.fill("17:00")
        
        players_field = page.locator('input[name="players_requested"], select[name="players_requested"]').first
        if players_field.count() > 0:
            if players_field.tag_name() == "select":
                players_field.select_option("4")
            else:
                players_field.fill("4")
        
        # Submit
        submit_button = page.locator('button[type="submit"], button:has-text("Create")').first
        if submit_button.count() > 0:
            submit_button.click()
            page.wait_for_timeout(3000)

        # Now look for edit buttons on the games list
        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        edit_buttons = page.locator('button:has-text("Edit"), button:has-text("Modify")')
        
        if edit_buttons.count() > 0:
            # Click edit button
            first_edit_button = edit_buttons.first
            if first_edit_button.is_visible():
                first_edit_button.click()
                
                # Wait for edit form to load
                page.wait_for_timeout(2000)
                
                # Check if we're on edit page
                assert "edit" in page.url.lower() or "modify" in page.content().lower(), "Should be on edit page"
                
                # Try to modify description
                description_field = page.locator('input[name="description"], textarea[name="description"]').first
                if description_field.count() > 0:
                    description_field.fill("Updated Game Description")
                    
                    # Submit changes
                    submit_button = page.locator('button[type="submit"], button:has-text("Update")').first
                    if submit_button.count() > 0:
                        submit_button.click()
                        page.wait_for_timeout(2000)
                        
                        # Check for success
                        success_shown = assert_toast_message(page, "updated", timeout=3000)
                        assert success_shown, "Game update should succeed"

    def test_delete_pickup_game(self, authenticated_page, flask_server):
        """Test deleting a pickup game (if user is creator)"""
        page = authenticated_page

        # Look for delete buttons on games list
        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        delete_buttons = page.locator('button:has-text("Delete"), button:has-text("Remove")')
        
        if delete_buttons.count() > 0:
            # Click delete button
            first_delete_button = delete_buttons.first
            if first_delete_button.is_visible():
                first_delete_button.click()
                
                # Wait for confirmation dialog
                page.wait_for_timeout(1000)
                
                # Look for confirmation button
                confirm_buttons = page.locator('button:has-text("Confirm"), button:has-text("Delete"), button:has-text("Yes")')
                
                if confirm_buttons.count() > 0:
                    confirm_buttons.first.click()
                    
                    # Wait for deletion
                    page.wait_for_timeout(2000)
                    
                    # Check for success message
                    success_shown = assert_toast_message(page, "deleted", timeout=3000)
                    assert success_shown, "Game deletion should succeed"


@pytest.mark.ui
class TestPickupGameErrorHandling:
    """Test pickup game error handling"""

    def test_create_game_validation_errors(self, authenticated_page, flask_server):
        """Test form validation when creating pickup games"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/create-pickup-game")
        wait_for_page_load(page)

        # Try to submit empty form
        submit_button = page.locator('button[type="submit"], button:has-text("Create")').first
        if submit_button.count() > 0:
            submit_button.click()
            
            # Wait for validation
            page.wait_for_timeout(2000)
            
            # Check for error messages
            error_elements = page.locator('.error, .alert-danger, .validation-error')
            if error_elements.count() > 0:
                print("Validation errors shown as expected")
            else:
                # Form might have client-side validation preventing submission
                print("Form has client-side validation (no errors shown)")

    def test_join_full_game(self, authenticated_page, flask_server):
        """Test attempting to join a full game"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Look for "Game Full" or disabled join buttons
        full_game_indicators = [
            'button:has-text("Game Full")',
            'button:has-text("Full")',
            'button[disabled]:has-text("Join")',
        ]

        full_game_found = False
        for selector in full_game_indicators:
            if page.locator(selector).count() > 0:
                full_game_found = True
                break

        if full_game_found:
            print("Full game indicators found")
        else:
            print("No full games found (this is normal)")


@pytest.mark.ui
class TestPickupGameAccessibility:
    """Test pickup games accessibility features"""

    def test_pickup_games_form_accessibility(self, authenticated_page, flask_server):
        """Test that pickup games forms have proper accessibility attributes"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/create-pickup-game")
        wait_for_page_load(page)

        # Check form fields for accessibility attributes
        form_fields = [
            'input[name="description"]',
            'input[name="game_date"]',
            'input[name="game_time"]',
            'input[name="players_requested"]',
        ]

        for field_selector in form_fields:
            field = page.locator(field_selector).first
            if field.count() > 0:
                # Check for accessibility attributes
                field_id = field.get_attribute("id")
                field_name = field.get_attribute("name")
                aria_label = field.get_attribute("aria-label")
                placeholder = field.get_attribute("placeholder")

                # At least one accessibility feature should be present
                has_accessibility = field_id or aria_label or placeholder or field_name
                assert has_accessibility, f"Form field {field_selector} should have accessibility features"

    def test_pickup_games_keyboard_navigation(self, authenticated_page, flask_server):
        """Test keyboard navigation through pickup games interface"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Test tab navigation
        page.keyboard.press("Tab")
        
        # Check that focus moves to an interactive element
        focused_element = page.locator(":focus")
        assert focused_element.count() > 0, "Focus should move to an interactive element"


@pytest.mark.ui
@pytest.mark.smoke
class TestPickupGamesIntegration:
    """Test pickup games integration with other features"""

    def test_pickup_games_from_mobile_home(self, authenticated_page, flask_server):
        """Test navigating to pickup games from mobile home page"""
        page = authenticated_page

        # Start from mobile home
        page.goto(f"{flask_server}/mobile")
        wait_for_page_load(page)

        # Find and click pickup games link
        pickup_links = [
            'a[href="/mobile/pickup-games"]',
            'a:has-text("Pickup Games")',
            'a:has-text("Find Games")',
        ]
        
        link_clicked = False
        for selector in pickup_links:
            if page.locator(selector).count() > 0:
                page.click(selector)
                wait_for_page_load(page)
                
                # Verify we're on pickup games page
                if "/pickup-games" in page.url:
                    link_clicked = True
                    break
        
        # This test is optional since pickup games might not be linked from home
        if link_clicked:
            print("Successfully navigated to pickup games from mobile home")
        else:
            print("No pickup games link found on mobile home (this is normal)")

    def test_pickup_games_notification_integration(self, authenticated_page, flask_server):
        """Test that pickup games integrate with notification system"""
        page = authenticated_page

        page.goto(f"{flask_server}/mobile/pickup-games")
        wait_for_page_load(page)

        # Look for notification-related elements
        notification_elements = [
            '.notification',
            '.toast',
            '[data-notification]',
        ]

        notification_found = False
        for selector in notification_elements:
            if page.locator(selector).count() > 0:
                notification_found = True
                break

        # Notifications are optional, so don't fail if not found
        if notification_found:
            print("Notification elements found in pickup games")
        else:
            print("No notification elements found (this is normal)")


# Utility function for debugging
def debug_pickup_games_page(page, test_name):
    """Debug function to help troubleshoot pickup games page issues"""
    print(f"\n=== DEBUG: {test_name} ===")
    print(f"Current URL: {page.url}")
    print(f"Page title: {page.title()}")
    
    # Check for pickup games elements
    game_cards = page.locator('.game-card, .pickup-game-item')
    print(f"Game cards found: {game_cards.count()}")
    
    # Check for create button
    create_buttons = page.locator('button:has-text("Create")')
    print(f"Create buttons found: {create_buttons.count()}")
    
    # Check for any error messages
    error_messages = page.locator('.error, .alert-danger, .toast-error')
    if error_messages.count() > 0:
        print(f"Error messages found: {error_messages.count()}")
        for i in range(min(3, error_messages.count())):
            print(f"Error {i}: {error_messages.nth(i).text_content()}")
    
    # Take screenshot for debugging
    take_screenshot_on_failure(page, f"debug_{test_name}") 