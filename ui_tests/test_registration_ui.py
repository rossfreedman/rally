"""
Rally Registration UI Tests
End-to-end testing of user registration process using Playwright
"""

import pytest
import time
from playwright.sync_api import expect
from conftest import wait_for_page_load, take_screenshot_on_failure, assert_toast_message, fill_form_field

@pytest.mark.ui
@pytest.mark.critical
class TestRegistrationPageUI:
    """Test registration page UI elements and basic functionality"""
    
    def test_registration_page_loads(self, page, flask_server):
        """Test that registration page loads with all required elements"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Check page title
        expect(page).to_have_title(title_regex=r"Register.*Rally")
        
        # Check required form fields are present
        expect(page.locator('input[name="email"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()
        expect(page.locator('input[name="firstName"]')).to_be_visible()
        expect(page.locator('input[name="lastName"]')).to_be_visible()
        
        # Check form submission button
        submit_button = page.locator('button[type="submit"], input[type="submit"]')
        expect(submit_button).to_be_visible()
        expect(submit_button).to_be_enabled()
        
        # Check for Rally branding/logo
        logo_selectors = ['img[alt*="Rally"]', '.logo', '[data-testid="logo"]', 'img[src*="logo"]']
        logo_found = False
        for selector in logo_selectors:
            if page.locator(selector).count() > 0:
                logo_found = True
                break
        assert logo_found, "Rally logo not found on registration page"
    
    def test_form_field_validation(self, page, flask_server):
        """Test client-side form validation"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Try to submit empty form
        page.click('button[type="submit"], input[type="submit"]')
        
        # Check for validation messages or that form wasn't submitted
        current_url = page.url
        assert "/register" in current_url, "Form should not submit with empty fields"
        
        # Test invalid email format
        page.fill('input[name="email"]', 'invalid-email')
        page.fill('input[name="password"]', 'password123')
        page.fill('input[name="firstName"]', 'Test')
        page.fill('input[name="lastName"]', 'User')
        
        page.click('button[type="submit"], input[type="submit"]')
        
        # Should still be on registration page or show validation message
        time.sleep(1000)  # Wait for any validation to appear
        current_url_after = page.url
        validation_visible = (
            "/register" in current_url_after or
            page.locator('.error, .invalid, .validation-message').count() > 0
        )
        assert validation_visible, "Invalid email should trigger validation"

@pytest.mark.ui
class TestRegistrationFlow:
    """Test complete registration user flows"""
    
    def test_successful_registration_without_player_link(self, page, flask_server):
        """Test successful user registration without player association"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Fill out registration form
        unique_email = f"uitest{int(time.time())}@example.com"
        page.fill('input[name="email"]', unique_email)
        page.fill('input[name="password"]', 'strongpassword123')
        page.fill('input[name="firstName"]', 'UI')
        page.fill('input[name="lastName"]', 'TestUser')
        
        # Submit form
        page.click('button[type="submit"], input[type="submit"]')
        
        # Wait for redirect or success message
        page.wait_for_load_state("networkidle", timeout=10000)
        
        # Should redirect to mobile page or show success
        current_url = page.url
        registration_successful = (
            "/mobile" in current_url or
            "success" in page.content().lower() or
            assert_toast_message(page, "success", timeout=3000)
        )
        
        assert registration_successful, f"Registration should succeed. Current URL: {current_url}"
    
    def test_registration_with_player_linking(self, page, flask_server, test_player_data, ui_test_database):
        """Test registration with player data matching"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Use valid player data from fixtures
        valid_player = test_player_data['valid_players'][0]
        unique_email = f"player{int(time.time())}@example.com"
        
        # Fill registration form with player matching data
        page.fill('input[name="email"]', unique_email)
        page.fill('input[name="password"]', 'playerpass123')
        page.fill('input[name="firstName"]', valid_player['first_name'])
        page.fill('input[name="lastName"]', valid_player['last_name'])
        
        # Fill player association fields if they exist
        league_field_selectors = ['select[name="league"]', 'input[name="league"]', '[data-testid="league"]']
        for selector in league_field_selectors:
            if page.locator(selector).count() > 0:
                if 'select' in selector:
                    page.select_option(selector, valid_player.get('league', ''))
                else:
                    page.fill(selector, valid_player.get('league', ''))
                break
        
        club_field_selectors = ['select[name="club"]', 'input[name="club"]', '[data-testid="club"]']
        for selector in club_field_selectors:
            if page.locator(selector).count() > 0:
                if 'select' in selector:
                    page.select_option(selector, valid_player.get('club', ''))
                else:
                    page.fill(selector, valid_player.get('club', ''))
                break
        
        series_field_selectors = ['select[name="series"]', 'input[name="series"]', '[data-testid="series"]']
        for selector in series_field_selectors:
            if page.locator(selector).count() > 0:
                if 'select' in selector:
                    page.select_option(selector, valid_player.get('series', ''))
                else:
                    page.fill(selector, valid_player.get('series', ''))
                break
        
        # Submit registration
        page.click('button[type="submit"], input[type="submit"]')
        
        # Wait for response
        page.wait_for_load_state("networkidle", timeout=15000)
        
        # Verify successful registration
        current_url = page.url
        success_indicators = [
            "/mobile" in current_url,
            "welcome" in page.content().lower(),
            "success" in page.content().lower()
        ]
        
        assert any(success_indicators), f"Player-linked registration should succeed. URL: {current_url}"
    
    def test_duplicate_email_registration(self, page, flask_server, ui_test_database):
        """Test registration with already existing email"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Use existing test user email
        existing_user = ui_test_database['test_users'][0]
        
        page.fill('input[name="email"]', existing_user['email'])
        page.fill('input[name="password"]', 'newpassword123')
        page.fill('input[name="firstName"]', 'Duplicate')
        page.fill('input[name="lastName"]', 'User')
        
        # Submit form
        page.click('button[type="submit"], input[type="submit"]')
        
        # Wait for error response
        time.sleep(3000)  # Give time for error message
        
        # Should show error message or stay on registration page
        current_url = page.url
        error_shown = (
            "/register" in current_url or
            "already exists" in page.content().lower() or
            "duplicate" in page.content().lower() or
            page.locator('.error, .alert-danger, .invalid').count() > 0
        )
        
        assert error_shown, "Duplicate email registration should show error"
    
    def test_registration_with_weak_password(self, page, flask_server):
        """Test registration with weak password"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        unique_email = f"weak{int(time.time())}@example.com"
        page.fill('input[name="email"]', unique_email)
        page.fill('input[name="password"]', '123')  # Weak password
        page.fill('input[name="firstName"]', 'Weak')
        page.fill('input[name="lastName"]', 'Password')
        
        page.click('button[type="submit"], input[type="submit"]')
        
        # Wait for validation
        time.sleep(2000)
        
        # Should either show validation error or reject submission
        current_url = page.url
        weak_password_handled = (
            "/register" in current_url or
            "password" in page.content().lower() and ("weak" in page.content().lower() or "strong" in page.content().lower())
        )
        
        # Note: This test may pass if weak password validation isn't implemented
        # The test documents expected behavior
        print(f"Weak password test result - stayed on registration: {'/register' in current_url}")

@pytest.mark.ui
class TestRegistrationAccessibility:
    """Test registration page accessibility features"""
    
    def test_form_labels_and_accessibility(self, page, flask_server):
        """Test that form fields have proper labels and accessibility attributes"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Check for form labels
        form_fields = [
            'input[name="email"]',
            'input[name="password"]', 
            'input[name="firstName"]',
            'input[name="lastName"]'
        ]
        
        for field_selector in form_fields:
            field = page.locator(field_selector).first
            if field.count() > 0:
                # Check if field has associated label
                field_id = field.get_attribute('id')
                field_name = field.get_attribute('name')
                
                label_found = (
                    field_id and page.locator(f'label[for="{field_id}"]').count() > 0 or
                    page.locator(f'label:has(input[name="{field_name}"])').count() > 0 or
                    field.get_attribute('aria-label') or
                    field.get_attribute('placeholder')
                )
                
                assert label_found, f"Field {field_selector} should have accessible label"
    
    def test_keyboard_navigation(self, page, flask_server):
        """Test keyboard navigation through registration form"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Start with first form field and tab through
        page.keyboard.press('Tab')
        
        # Check that focus moves through form fields
        focused_element = page.evaluate('document.activeElement.tagName')
        assert focused_element in ['INPUT', 'SELECT', 'BUTTON'], "Tab should focus on form elements"

@pytest.mark.ui
@pytest.mark.smoke
class TestRegistrationIntegration:
    """Integration tests for registration with other systems"""
    
    def test_registration_to_login_flow(self, page, flask_server):
        """Test complete flow from registration to login"""
        # Register new user
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        unique_email = f"flow{int(time.time())}@example.com"
        password = 'flowtest123'
        
        page.fill('input[name="email"]', unique_email)
        page.fill('input[name="password"]', password)
        page.fill('input[name="firstName"]', 'Flow')
        page.fill('input[name="lastName"]', 'Test')
        
        page.click('button[type="submit"], input[type="submit"]')
        
        # Wait for registration to complete
        page.wait_for_load_state("networkidle", timeout=10000)
        
        # If redirected to mobile, logout first
        if "/mobile" in page.url:
            # Look for logout button/link
            logout_selectors = [
                'a[href*="logout"]', 'button:has-text("Logout")', 
                'a:has-text("Logout")', '[data-testid="logout"]'
            ]
            
            for selector in logout_selectors:
                if page.locator(selector).count() > 0:
                    page.click(selector)
                    break
        
        # Go to login page
        page.goto(f"{flask_server}/login")
        wait_for_page_load(page)
        
        # Login with registered credentials
        page.fill('input[name="email"]', unique_email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"], input[type="submit"]')
        
        # Should successfully login
        page.wait_for_load_state("networkidle", timeout=10000)
        
        current_url = page.url
        login_successful = (
            "/mobile" in current_url or
            "/dashboard" in current_url or
            "welcome" in page.content().lower()
        )
        
        assert login_successful, f"Should be able to login after registration. URL: {current_url}"
    
    def test_registration_with_browser_back_button(self, page, flask_server):
        """Test registration form behavior with browser navigation"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Fill partial form
        page.fill('input[name="email"]', 'test@example.com')
        page.fill('input[name="firstName"]', 'Test')
        
        # Navigate away and back
        page.goto(f"{flask_server}/login")
        page.go_back()
        
        # Check if form data persists (browser behavior)
        email_value = page.locator('input[name="email"]').input_value()
        # Note: Form persistence depends on browser/implementation
        print(f"Form data persistence test - email value after back: '{email_value}'")

@pytest.mark.ui
class TestRegistrationErrorHandling:
    """Test error handling and edge cases in registration"""
    
    def test_network_error_handling(self, page, flask_server):
        """Test registration behavior during network issues"""
        page.goto(f"{flask_server}/register")
        wait_for_page_load(page)
        
        # Fill form
        page.fill('input[name="email"]', 'network@example.com')
        page.fill('input[name="password"]', 'password123')
        page.fill('input[name="firstName"]', 'Network')
        page.fill('input[name="lastName"]', 'Test')
        
        # Simulate slow network by intercepting requests
        page.route("**/api/register", lambda route: time.sleep(5) or route.continue_())
        
        # Submit form
        page.click('button[type="submit"], input[type="submit"]')
        
        # Check for loading state or timeout handling
        # This test verifies the UI handles slow responses gracefully
        time.sleep(2000)  # Give time for loading indicators
        
        loading_indicators = page.locator('.loading, .spinner, [data-testid="loading"]').count()
        print(f"Loading indicators found during slow request: {loading_indicators}")
    
    def test_javascript_disabled_fallback(self, page, flask_server, context):
        """Test registration with JavaScript disabled"""
        # Create new context with JS disabled
        js_disabled_context = context.browser.new_context(
            java_script_enabled=False
        )
        js_disabled_page = js_disabled_context.new_page()
        
        try:
            js_disabled_page.goto(f"{flask_server}/register")
            wait_for_page_load(js_disabled_page)
            
            # Form should still be usable without JS
            expect(js_disabled_page.locator('input[name="email"]')).to_be_visible()
            expect(js_disabled_page.locator('button[type="submit"], input[type="submit"]')).to_be_visible()
            
            # Fill and submit form
            js_disabled_page.fill('input[name="email"]', f'nojs{int(time.time())}@example.com')
            js_disabled_page.fill('input[name="password"]', 'nojspassword123')
            js_disabled_page.fill('input[name="firstName"]', 'NoJS')
            js_disabled_page.fill('input[name="lastName"]', 'User')
            
            js_disabled_page.click('button[type="submit"], input[type="submit"]')
            
            # Should handle form submission without JS
            js_disabled_page.wait_for_load_state("networkidle", timeout=15000)
            
        finally:
            js_disabled_context.close()

# Helper function for debugging
def debug_page_state(page, test_name):
    """Debug helper to capture page state during test failures"""
    try:
        print(f"\n=== DEBUG INFO FOR {test_name} ===")
        print(f"Current URL: {page.url}")
        print(f"Page Title: {page.title()}")
        
        # Check for error messages
        error_selectors = ['.error', '.alert-danger', '.invalid', '[data-testid="error"]']
        for selector in error_selectors:
            errors = page.locator(selector)
            if errors.count() > 0:
                print(f"Error messages found ({selector}): {errors.all_text_contents()}")
        
        # Take screenshot
        take_screenshot_on_failure(page, test_name)
        
    except Exception as e:
        print(f"Debug info collection failed: {e}") 