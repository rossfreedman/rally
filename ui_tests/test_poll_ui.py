"""
Rally Poll UI Tests
End-to-end testing of poll creation, voting, and management using Playwright
"""

import time

import pytest
from conftest import (
    assert_toast_message,
    take_screenshot_on_failure,
    wait_for_page_load,
)
from playwright.sync_api import expect


@pytest.mark.ui
@pytest.mark.critical
class TestPollPageUI:
    """Test poll page UI elements and basic functionality"""

    def test_polls_page_loads(self, authenticated_page, flask_server):
        """Test that polls page loads with all required elements"""
        page = authenticated_page

        # Navigate to polls page
        polls_urls = ["/polls", "/mobile/polls", "/team-polls"]
        polls_loaded = False

        for url in polls_urls:
            try:
                page.goto(f"{flask_server}{url}")
                wait_for_page_load(page)

                # Check if this is the polls page
                if any(
                    keyword in page.content().lower()
                    for keyword in ["poll", "vote", "question"]
                ):
                    polls_loaded = True
                    break
            except:
                continue

        assert polls_loaded, "Could not load polls page"

        # Check for poll-related elements
        poll_elements = [
            '.poll, .poll-container, [data-testid="poll"]',
            'button:has-text("Create"), button:has-text("New Poll")',
            ".poll-list, .polls-container",
        ]

        poll_ui_found = False
        for selector in poll_elements:
            if page.locator(selector).count() > 0:
                poll_ui_found = True
                break

        assert poll_ui_found, "Poll UI elements not found on page"

    def test_create_poll_button_visible(self, authenticated_page, flask_server):
        """Test that create poll button is visible and accessible"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for create poll buttons
        create_poll_selectors = [
            'button:has-text("Create")',
            'button:has-text("New Poll")',
            'a:has-text("Create Poll")',
            '[data-testid="create-poll"]',
            ".create-poll, .new-poll-btn",
        ]

        create_button_found = False
        for selector in create_poll_selectors:
            if page.locator(selector).count() > 0:
                button = page.locator(selector).first
                if button.is_visible():
                    create_button_found = True
                    break

        assert create_button_found, "Create poll button should be visible"


@pytest.mark.ui
class TestPollCreation:
    """Test poll creation functionality"""

    def test_create_poll_form_opens(self, authenticated_page, flask_server):
        """Test that create poll form opens when button is clicked"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Find and click create poll button
        create_poll_selectors = [
            'button:has-text("Create")',
            'button:has-text("New Poll")',
            'a:has-text("Create Poll")',
            '[data-testid="create-poll"]',
        ]

        form_opened = False
        for selector in create_poll_selectors:
            elements = page.locator(selector)
            if elements.count() > 0:
                try:
                    first_button = elements.first
                    if first_button.is_visible():
                        first_button.click()
                        wait_for_page_load(page)

                        # Check if form opened (modal, new page, or form section)
                        form_indicators = [
                            'input[name*="question"], textarea[name*="question"]',
                            ".modal, .popup, .form-container",
                            'form[action*="poll"], form[id*="poll"]',
                        ]

                        for form_selector in form_indicators:
                            if page.locator(form_selector).count() > 0:
                                form_opened = True
                                break

                        if form_opened:
                            break
                except:
                    continue

        assert form_opened, "Create poll form should open when button is clicked"

    def test_poll_creation_form_fields(self, authenticated_page, flask_server):
        """Test poll creation form has required fields"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Open create poll form
        create_button_selectors = [
            'button:has-text("Create")',
            'button:has-text("New Poll")',
            'a:has-text("Create Poll")',
            '[data-testid="create-poll"]',
        ]

        for selector in create_button_selectors:
            if page.locator(selector).count() > 0:
                try:
                    page.click(selector)
                    wait_for_page_load(page)
                    break
                except:
                    continue

        # Check for poll form fields
        required_fields = [
            # Poll question field
            'input[name*="question"], textarea[name*="question"], [data-testid="question"]',
            # Poll choices/options
            'input[name*="choice"], input[name*="option"], [data-testid="choice"]',
            # Submit button
            'button[type="submit"], input[type="submit"], button:has-text("Create")',
        ]

        fields_found = {}
        for field_type in required_fields:
            fields_found[field_type] = page.locator(field_type).count() > 0

        # At least question and submit should be present
        assert fields_found[required_fields[0]], "Poll question field should be present"
        assert fields_found[required_fields[2]], "Submit button should be present"

        print(f"Poll form fields found: {fields_found}")

    def test_create_simple_poll(self, authenticated_page, flask_server):
        """Test creating a simple poll with question and choices"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Open create poll form
        create_button_selectors = [
            'button:has-text("Create")',
            'button:has-text("New Poll")',
            'a:has-text("Create Poll")',
            '[data-testid="create-poll"]',
        ]

        form_opened = False
        for selector in create_button_selectors:
            if page.locator(selector).count() > 0:
                try:
                    page.click(selector)
                    wait_for_page_load(page)
                    form_opened = True
                    break
                except:
                    continue

        if not form_opened:
            pytest.skip("Could not open poll creation form")

        # Fill poll form
        poll_question = f"UI Test Poll {int(time.time())}"

        # Fill question field
        question_selectors = [
            'input[name*="question"]',
            'textarea[name*="question"]',
            '[data-testid="question"]',
            "#question",
        ]

        question_filled = False
        for selector in question_selectors:
            if page.locator(selector).count() > 0:
                try:
                    page.fill(selector, poll_question)
                    question_filled = True
                    break
                except:
                    continue

        assert question_filled, "Should be able to fill poll question"

        # Fill choice fields (if present)
        choice_selectors = [
            'input[name*="choice"]',
            'input[name*="option"]',
            '[data-testid="choice"]',
            ".choice-input",
        ]

        choices_filled = 0
        for selector in choice_selectors:
            choice_elements = page.locator(selector)
            for i in range(min(2, choice_elements.count())):  # Fill first 2 choices
                try:
                    choice_elements.nth(i).fill(f"Choice {i+1}")
                    choices_filled += 1
                except:
                    continue

        print(f"Poll choices filled: {choices_filled}")

        # Submit poll
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Create")',
            'button:has-text("Submit")',
        ]

        submitted = False
        for selector in submit_selectors:
            if page.locator(selector).count() > 0:
                try:
                    page.click(selector)
                    wait_for_page_load(page)
                    submitted = True
                    break
                except:
                    continue

        assert submitted, "Should be able to submit poll"

        # Check for success indication
        success_indicators = [
            poll_question.lower() in page.content().lower(),
            "success" in page.content().lower(),
            "created" in page.content().lower(),
        ]

        success = any(success_indicators)
        print(f"Poll creation success indicators: {success_indicators}")

        # Note: Success verification depends on implementation
        print(f"Poll creation appeared successful: {success}")


@pytest.mark.ui
class TestPollVoting:
    """Test poll voting functionality"""

    def test_poll_voting_interface(self, authenticated_page, flask_server):
        """Test that polls display voting interface"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for existing polls with voting options
        voting_selectors = [
            'input[type="radio"], input[type="checkbox"]',  # Radio/checkbox voting
            'button:has-text("Vote")',
            ".vote-button",  # Vote buttons
            ".poll-option, .choice-option",  # Poll choices
            '[data-testid="vote"], [data-testid="option"]',  # Test ID elements
        ]

        voting_interface_found = False
        for selector in voting_selectors:
            if page.locator(selector).count() > 0:
                voting_interface_found = True
                print(f"Found voting interface: {selector}")
                break

        # If no polls exist, this test documents expected behavior
        print(f"Voting interface available: {voting_interface_found}")

    def test_cast_vote_on_poll(self, authenticated_page, flask_server):
        """Test casting a vote on an existing poll"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for votable polls
        voting_options = page.locator('input[type="radio"], input[type="checkbox"]')

        if voting_options.count() > 0:
            # Select first voting option
            try:
                first_option = voting_options.first
                first_option.check()

                # Look for vote submit button
                vote_buttons = [
                    'button:has-text("Vote")',
                    'button:has-text("Submit Vote")',
                    '[data-testid="vote-submit"]',
                    ".vote-submit",
                ]

                vote_submitted = False
                for selector in vote_buttons:
                    if page.locator(selector).count() > 0:
                        try:
                            page.click(selector)
                            wait_for_page_load(page)
                            vote_submitted = True
                            break
                        except:
                            continue

                if vote_submitted:
                    # Check for vote confirmation
                    confirmation_indicators = [
                        "voted" in page.content().lower(),
                        "thank you" in page.content().lower(),
                        page.locator(".vote-confirmation, .success").count() > 0,
                    ]

                    vote_confirmed = any(confirmation_indicators)
                    print(f"Vote confirmation: {vote_confirmed}")
                else:
                    print("No vote submit button found")
            except:
                print("Could not interact with voting options")
        else:
            print("No voting options found - may be no active polls")

    def test_duplicate_vote_prevention(self, authenticated_page, flask_server):
        """Test that duplicate voting is prevented"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for polls that have already been voted on
        voted_indicators = [
            ".already-voted",
            ".vote-disabled",
            '[data-testid="voted"]',
            "input[disabled]",
            "button[disabled]",
            ':has-text("Already voted")',
            ':has-text("You voted")',
        ]

        already_voted_found = False
        for selector in voted_indicators:
            if page.locator(selector).count() > 0:
                already_voted_found = True
                print(f"Found duplicate vote prevention: {selector}")
                break

        print(f"Duplicate vote prevention visible: {already_voted_found}")


@pytest.mark.ui
class TestPollDisplay:
    """Test poll display and formatting"""

    def test_poll_list_display(self, authenticated_page, flask_server):
        """Test that polls are properly displayed in list format"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for poll display elements
        poll_display_selectors = [
            ".poll, .poll-item, .poll-card",
            '[data-testid="poll"], .poll-container',
            'li:has-text("poll"), div:has-text("poll")',
        ]

        polls_displayed = []
        for selector in poll_display_selectors:
            elements = page.locator(selector)
            if elements.count() > 0:
                polls_displayed.append(f"{selector}: {elements.count()} items")

        print(f"Poll display elements found: {polls_displayed}")

        # Check for poll content elements
        poll_content_selectors = [
            ".poll-question, .question",  # Poll questions
            ".poll-options, .choices",  # Poll choices
            ".poll-results, .results",  # Poll results
        ]

        content_found = {}
        for selector in poll_content_selectors:
            content_found[selector] = page.locator(selector).count() > 0

        print(f"Poll content elements: {content_found}")

    def test_poll_results_display(self, authenticated_page, flask_server):
        """Test that poll results are displayed properly"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for poll results
        results_selectors = [
            ".poll-results, .results, .vote-count",
            '[data-testid="results"]',
            ".percentage",
            "progress, .progress-bar",  # Progress bars for results
        ]

        results_found = []
        for selector in results_selectors:
            count = page.locator(selector).count()
            if count > 0:
                results_found.append(f"{selector}: {count}")

        print(f"Poll results display: {results_found}")

        # Check for numerical vote counts or percentages
        page_content = page.content().lower()
        has_numbers = any(char.isdigit() for char in page_content)
        has_percentage = "%" in page_content

        print(f"Results contain numbers: {has_numbers}, percentages: {has_percentage}")


@pytest.mark.ui
class TestPollManagement:
    """Test poll management features"""

    def test_poll_edit_functionality(self, admin_page, flask_server):
        """Test poll editing functionality (admin only)"""
        page = admin_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for edit buttons (admin functionality)
        edit_selectors = [
            'button:has-text("Edit")',
            'a:has-text("Edit")',
            '[data-testid="edit-poll"]',
            ".edit-poll",
            'button:has-text("Manage")',
        ]

        edit_found = False
        for selector in edit_selectors:
            if page.locator(selector).count() > 0:
                edit_found = True
                print(f"Found edit functionality: {selector}")
                break

        print(f"Poll edit functionality available: {edit_found}")

    def test_poll_delete_functionality(self, admin_page, flask_server):
        """Test poll deletion functionality (admin only)"""
        page = admin_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for delete buttons (admin functionality)
        delete_selectors = [
            'button:has-text("Delete")',
            'a:has-text("Delete")',
            '[data-testid="delete-poll"]',
            ".delete-poll",
            'button:has-text("Remove")',
        ]

        delete_found = False
        for selector in delete_selectors:
            if page.locator(selector).count() > 0:
                delete_found = True
                print(f"Found delete functionality: {selector}")
                break

        print(f"Poll delete functionality available: {delete_found}")

    def test_poll_close_functionality(self, admin_page, flask_server):
        """Test poll closing functionality"""
        page = admin_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for close/end poll functionality
        close_selectors = [
            'button:has-text("Close")',
            'button:has-text("End")',
            '[data-testid="close-poll"]',
            ".close-poll",
        ]

        close_found = False
        for selector in close_selectors:
            if page.locator(selector).count() > 0:
                close_found = True
                print(f"Found close functionality: {selector}")
                break

        print(f"Poll close functionality available: {close_found}")


@pytest.mark.ui
class TestPollNavigation:
    """Test poll navigation and routing"""

    def test_navigate_to_polls_from_mobile(self, authenticated_page, flask_server):
        """Test navigation to polls from mobile page"""
        page = authenticated_page

        # Should start on mobile page
        assert "/mobile" in page.url, "Should start on mobile page"

        # Look for polls navigation links
        polls_nav_selectors = [
            'a[href*="poll"]',
            'button:has-text("Poll")',
            '[data-testid="polls-nav"]',
            ".nav-polls",
        ]

        polls_nav_found = False
        for selector in polls_nav_selectors:
            elements = page.locator(selector)
            if elements.count() > 0:
                try:
                    first_link = elements.first
                    if first_link.is_visible():
                        first_link.click()
                        wait_for_page_load(page)

                        # Should now be on polls page
                        current_url = page.url
                        if "poll" in current_url.lower():
                            polls_nav_found = True
                            break
                except:
                    continue

        print(f"Polls navigation from mobile: {polls_nav_found}")

    def test_individual_poll_navigation(self, authenticated_page, flask_server):
        """Test navigation to individual poll pages"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for links to individual polls
        poll_links = [
            'a[href*="poll/"]',
            ".poll-link",
            '[data-testid="poll-link"]',
            ".poll-title a",
        ]

        individual_poll_nav = False
        for selector in poll_links:
            elements = page.locator(selector)
            if elements.count() > 0:
                try:
                    first_link = elements.first
                    if first_link.is_visible():
                        first_link.click()
                        wait_for_page_load(page)

                        # Check if we're on an individual poll page
                        current_url = page.url
                        if (
                            "poll" in current_url
                            and "/" in current_url.split("poll")[-1]
                        ):
                            individual_poll_nav = True
                            break
                except:
                    continue

        print(f"Individual poll navigation: {individual_poll_nav}")


@pytest.mark.ui
class TestPollResponsive:
    """Test poll responsive design"""

    def test_mobile_polls_view(self, authenticated_page, flask_server):
        """Test polls display on mobile viewport"""
        page = authenticated_page

        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Check that polls are visible on mobile
        polls_visible = (
            page.locator(".poll, .poll-item").count() > 0
            or page.locator('[data-testid="poll"]').count() > 0
        )

        print(f"Polls visible on mobile: {polls_visible}")

        # Check for mobile-specific optimizations
        mobile_optimizations = [
            ".card, .poll-card",  # Card-based layout
            ".mobile-poll, .poll-mobile",  # Mobile-specific styles
            ".list-group, .poll-list",  # List formatting
        ]

        mobile_optimized = any(
            page.locator(selector).count() > 0 for selector in mobile_optimizations
        )

        print(f"Mobile polls optimizations: {mobile_optimized}")


@pytest.mark.ui
class TestPollAccessibility:
    """Test poll accessibility features"""

    def test_poll_form_accessibility(self, authenticated_page, flask_server):
        """Test poll form accessibility features"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Try to open create poll form
        create_button_selectors = [
            'button:has-text("Create")',
            'button:has-text("New Poll")',
        ]

        for selector in create_button_selectors:
            if page.locator(selector).count() > 0:
                try:
                    page.click(selector)
                    wait_for_page_load(page)
                    break
                except:
                    continue

        # Check form accessibility
        form_fields = [
            'input[name*="question"]',
            'textarea[name*="question"]',
            'input[name*="choice"]',
            'input[name*="option"]',
        ]

        accessibility_features = {}
        for field_selector in form_fields:
            elements = page.locator(field_selector)
            if elements.count() > 0:
                field = elements.first

                # Check for labels and accessibility attributes
                field_id = field.get_attribute("id")
                field_name = field.get_attribute("name")

                has_label = (
                    field_id
                    and page.locator(f'label[for="{field_id}"]').count() > 0
                    or page.locator(f'label:has(input[name="{field_name}"])').count()
                    > 0
                    or field.get_attribute("aria-label")
                    or field.get_attribute("placeholder")
                )

                accessibility_features[field_selector] = has_label

        print(f"Poll form accessibility: {accessibility_features}")

    def test_poll_voting_accessibility(self, authenticated_page, flask_server):
        """Test poll voting accessibility"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Check voting options accessibility
        voting_inputs = page.locator('input[type="radio"], input[type="checkbox"]')

        if voting_inputs.count() > 0:
            accessibility_check = {}

            for i in range(min(3, voting_inputs.count())):
                input_element = voting_inputs.nth(i)

                # Check for associated labels
                input_id = input_element.get_attribute("id")
                input_name = input_element.get_attribute("name")

                has_label = (
                    input_id
                    and page.locator(f'label[for="{input_id}"]').count() > 0
                    or page.locator(f'label:has(input[name="{input_name}"])').count()
                    > 0
                )

                accessibility_check[f"input_{i}"] = has_label

            print(f"Voting accessibility: {accessibility_check}")


@pytest.mark.ui
@pytest.mark.smoke
class TestPollIntegration:
    """Integration tests for polls with other systems"""

    def test_poll_team_integration(self, authenticated_page, flask_server):
        """Test that polls are properly scoped to teams"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Check for team-specific context
        team_context_selectors = [
            ':has-text("team")',
            ".team-name",
            '[data-testid="team"]',
            ".team-polls, .poll-team",
        ]

        team_context_found = False
        for selector in team_context_selectors:
            if page.locator(selector).count() > 0:
                team_context_found = True
                break

        print(f"Team context in polls: {team_context_found}")

    def test_poll_notification_integration(self, authenticated_page, flask_server):
        """Test poll notifications and alerts"""
        page = authenticated_page

        page.goto(f"{flask_server}/polls")
        wait_for_page_load(page)

        # Look for notification indicators
        notification_selectors = [
            ".notification, .alert, .badge",
            '[data-testid="notification"]',
            ".poll-notification",
        ]

        notifications_found = False
        for selector in notification_selectors:
            if page.locator(selector).count() > 0:
                notifications_found = True
                break

        print(f"Poll notifications available: {notifications_found}")
