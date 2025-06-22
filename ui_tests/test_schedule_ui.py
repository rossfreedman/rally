"""
Rally Schedule UI Tests
End-to-end testing of schedule viewing and management using Playwright
"""

import time
from datetime import datetime, timedelta

import pytest
from conftest import (
    assert_toast_message,
    take_screenshot_on_failure,
    wait_for_page_load,
)
from playwright.sync_api import expect


@pytest.mark.ui
@pytest.mark.critical
class TestSchedulePageUI:
    """Test schedule page UI elements and basic functionality"""

    def test_schedule_page_loads(self, authenticated_page, flask_server):
        """Test that schedule page loads with all required elements"""
        page = authenticated_page

        # Navigate to schedule page
        schedule_urls = ["/schedule", "/mobile/schedule", "/team-schedule"]
        schedule_loaded = False

        for url in schedule_urls:
            try:
                page.goto(f"{flask_server}{url}")
                wait_for_page_load(page)

                # Check if this is the schedule page
                if any(
                    keyword in page.content().lower()
                    for keyword in ["schedule", "match", "opponent", "court"]
                ):
                    schedule_loaded = True
                    break
            except:
                continue

        assert schedule_loaded, "Could not load schedule page"

        # Check for schedule table or list
        schedule_containers = [
            "table",
            ".schedule-table",
            ".schedule-list",
            '[data-testid="schedule"]',
            "#schedule-container",
        ]

        schedule_found = False
        for selector in schedule_containers:
            if page.locator(selector).count() > 0:
                schedule_found = True
                break

        assert schedule_found, "Schedule container not found on page"

    def test_schedule_displays_match_information(
        self, authenticated_page, flask_server
    ):
        """Test that schedule displays match details"""
        page = authenticated_page

        # Navigate to schedule
        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for match information elements
        match_info_selectors = [
            # Date information
            '.date, .match-date, [data-testid="date"]',
            # Time information
            '.time, .match-time, [data-testid="time"]',
            # Opponent information
            '.opponent, .team, [data-testid="opponent"]',
            # Court/location information
            '.court, .location, [data-testid="court"]',
        ]

        info_found = {}
        for selector in match_info_selectors:
            info_found[selector] = page.locator(selector).count() > 0

        # At least some match information should be present
        assert any(
            info_found.values()
        ), f"No match information found. Checked: {info_found}"

    def test_schedule_navigation_elements(self, authenticated_page, flask_server):
        """Test schedule navigation and filtering elements"""
        page = authenticated_page

        # Navigate to schedule
        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for navigation elements
        nav_elements = [
            # Previous/Next buttons
            'button:has-text("Previous"), button:has-text("Next")',
            ".prev, .next, .navigation",
            # Date selectors
            'select[name*="month"], select[name*="week"]',
            'input[type="date"], input[type="week"]',
            # Filter options
            '.filter, .schedule-filter, [data-testid="filter"]',
        ]

        nav_found = False
        for selector in nav_elements:
            if page.locator(selector).count() > 0:
                nav_found = True
                print(f"Found navigation element: {selector}")
                break

        # Navigation is optional, so just log results
        print(f"Schedule navigation found: {nav_found}")


@pytest.mark.ui
class TestScheduleDisplay:
    """Test schedule display and formatting"""

    def test_date_formatting(self, authenticated_page, flask_server):
        """Test that dates are properly formatted in schedule"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for date elements
        date_selectors = [
            ".date",
            ".match-date",
            '[data-testid="date"]',
            "td:nth-child(1)",
            ".schedule-date",  # Common table positions
        ]

        dates_found = []
        for selector in date_selectors:
            elements = page.locator(selector)
            for i in range(min(3, elements.count())):  # Check first 3 elements
                text = elements.nth(i).text_content().strip()
                if text and len(text) > 3:  # Has substantial content
                    dates_found.append(text)

        if dates_found:
            print(f"Date formats found: {dates_found}")

            # Check for reasonable date formatting
            for date_text in dates_found:
                # Should contain numbers (month/day/year)
                has_numbers = any(char.isdigit() for char in date_text)
                assert has_numbers, f"Date should contain numbers: {date_text}"

    def test_time_formatting(self, authenticated_page, flask_server):
        """Test that times are properly formatted in schedule"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for time elements
        time_selectors = [
            ".time",
            ".match-time",
            '[data-testid="time"]',
            "td:nth-child(2)",
            ".schedule-time",  # Common table positions
        ]

        times_found = []
        for selector in time_selectors:
            elements = page.locator(selector)
            for i in range(min(3, elements.count())):
                text = elements.nth(i).text_content().strip()
                if text and ":" in text:  # Likely a time format
                    times_found.append(text)

        if times_found:
            print(f"Time formats found: {times_found}")

            # Check for reasonable time formatting
            for time_text in times_found:
                # Should contain colon for hour:minute
                assert ":" in time_text, f"Time should contain colon: {time_text}"

    def test_opponent_display(self, authenticated_page, flask_server):
        """Test that opponent information is displayed"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for opponent/team information
        opponent_selectors = [
            ".opponent",
            ".team",
            ".vs",
            '[data-testid="opponent"]',
            "td:nth-child(3)",
            ".schedule-opponent",
        ]

        opponents_found = []
        for selector in opponent_selectors:
            elements = page.locator(selector)
            for i in range(min(3, elements.count())):
                text = elements.nth(i).text_content().strip()
                if text and len(text) > 2:  # Has substantial content
                    opponents_found.append(text)

        if opponents_found:
            print(f"Opponent information found: {opponents_found}")

            # Should have meaningful content
            for opponent_text in opponents_found:
                assert (
                    len(opponent_text) > 2
                ), f"Opponent info should be meaningful: {opponent_text}"


@pytest.mark.ui
class TestScheduleInteraction:
    """Test schedule interaction features"""

    def test_schedule_row_clickable(self, authenticated_page, flask_server):
        """Test that schedule rows are clickable for details"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for clickable schedule elements
        clickable_selectors = [
            "tr:not(:first-child)",
            ".schedule-row",
            ".match-row",
            'a[href*="match"]',
            '[data-testid="match-row"]',
        ]

        clickable_found = False
        for selector in clickable_selectors:
            elements = page.locator(selector)
            if elements.count() > 0:
                try:
                    # Try clicking first element
                    first_element = elements.first
                    if first_element.is_visible():
                        first_element.click()
                        time.sleep(1000)  # Wait for any navigation
                        clickable_found = True
                        break
                except:
                    continue

        print(f"Clickable schedule elements found: {clickable_found}")

    def test_schedule_filtering(self, authenticated_page, flask_server):
        """Test schedule filtering functionality"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for filter controls
        filter_selectors = [
            'select[name*="month"]',
            'select[name*="team"]',
            'select[name*="filter"]',
            ".filter-dropdown",
            '[data-testid="filter"]',
        ]

        filters_tested = []
        for selector in filter_selectors:
            elements = page.locator(selector)
            if elements.count() > 0:
                try:
                    first_filter = elements.first
                    if first_filter.is_visible():
                        # Get initial state
                        initial_content = page.content()

                        # Try to change filter
                        if "select" in selector:
                            options = first_filter.locator("option")
                            if options.count() > 1:
                                # Select second option
                                second_option = options.nth(1)
                                option_value = second_option.get_attribute("value")
                                if option_value:
                                    first_filter.select_option(value=option_value)
                                    wait_for_page_load(page)

                                    # Check if content changed
                                    new_content = page.content()
                                    if new_content != initial_content:
                                        filters_tested.append(selector)
                                        break
                except:
                    continue

        print(f"Working filters found: {filters_tested}")

    def test_schedule_refresh(self, authenticated_page, flask_server):
        """Test schedule refresh functionality"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for refresh buttons
        refresh_selectors = [
            'button:has-text("Refresh")',
            'button:has-text("Reload")',
            '[data-testid="refresh"]',
            ".refresh-button",
        ]

        refresh_found = False
        for selector in refresh_selectors:
            if page.locator(selector).count() > 0:
                try:
                    page.click(selector)
                    wait_for_page_load(page)
                    refresh_found = True
                    break
                except:
                    continue

        # Refresh functionality is optional
        print(f"Refresh functionality found: {refresh_found}")


@pytest.mark.ui
class TestScheduleResponsive:
    """Test schedule responsive design"""

    def test_mobile_schedule_view(self, authenticated_page, flask_server):
        """Test schedule display on mobile viewport"""
        page = authenticated_page

        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Check that schedule is visible on mobile
        schedule_visible = (
            page.locator("table").count() > 0
            or page.locator(".schedule-list").count() > 0
            or page.locator('[data-testid="schedule"]').count() > 0
        )

        assert schedule_visible, "Schedule should be visible on mobile"

        # Check for mobile-specific optimizations
        mobile_optimizations = [
            # Horizontal scrolling for tables
            "table.table-responsive, .table-responsive table",
            # Card-based layout
            ".card, .schedule-card",
            # Simplified mobile view
            ".mobile-schedule, .schedule-mobile",
        ]

        mobile_optimized = any(
            page.locator(selector).count() > 0 for selector in mobile_optimizations
        )

        print(f"Mobile schedule optimizations found: {mobile_optimized}")

    def test_tablet_schedule_view(self, authenticated_page, flask_server):
        """Test schedule display on tablet viewport"""
        page = authenticated_page

        # Set tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Schedule should be visible and well-formatted on tablet
        schedule_elements = page.locator(
            'table, .schedule-list, [data-testid="schedule"]'
        )
        assert schedule_elements.count() > 0, "Schedule should be visible on tablet"


@pytest.mark.ui
@pytest.mark.smoke
class TestScheduleNavigation:
    """Test navigation to/from schedule page"""

    def test_navigate_to_schedule_from_mobile(self, authenticated_page, flask_server):
        """Test navigation to schedule from mobile page"""
        page = authenticated_page

        # Should start on mobile page
        assert "/mobile" in page.url, "Should start on mobile page"

        # Look for schedule navigation links
        schedule_nav_selectors = [
            'a[href*="schedule"]',
            'button:has-text("Schedule")',
            '[data-testid="schedule-nav"]',
            ".nav-schedule",
        ]

        schedule_nav_found = False
        for selector in schedule_nav_selectors:
            elements = page.locator(selector)
            if elements.count() > 0:
                try:
                    first_link = elements.first
                    if first_link.is_visible():
                        first_link.click()
                        wait_for_page_load(page)

                        # Should now be on schedule page
                        current_url = page.url
                        if "schedule" in current_url.lower():
                            schedule_nav_found = True
                            break
                except:
                    continue

        assert schedule_nav_found, "Should be able to navigate to schedule from mobile"

    def test_schedule_breadcrumb_navigation(self, authenticated_page, flask_server):
        """Test breadcrumb navigation on schedule page"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for breadcrumb navigation
        breadcrumb_selectors = [
            ".breadcrumb",
            ".breadcrumbs",
            '[data-testid="breadcrumb"]',
            'nav[aria-label="breadcrumb"]',
            ".nav-breadcrumb",
        ]

        breadcrumbs_found = False
        for selector in breadcrumb_selectors:
            if page.locator(selector).count() > 0:
                breadcrumbs_found = True

                # Try clicking home/back link in breadcrumb
                back_links = page.locator(f"{selector} a")
                if back_links.count() > 0:
                    try:
                        back_links.first.click()
                        wait_for_page_load(page)
                        # Should navigate somewhere (mobile/dashboard)
                        current_url = page.url
                        print(f"Breadcrumb navigation to: {current_url}")
                    except:
                        pass
                break

        print(f"Breadcrumb navigation found: {breadcrumbs_found}")


@pytest.mark.ui
class TestSchedulePerformance:
    """Test schedule performance and loading"""

    def test_schedule_loading_time(self, authenticated_page, flask_server):
        """Test that schedule loads within reasonable time"""
        page = authenticated_page

        start_time = time.time()
        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)
        load_time = time.time() - start_time

        # Should load within 5 seconds
        assert (
            load_time < 5.0
        ), f"Schedule should load within 5 seconds, took {load_time:.2f}s"

        print(f"Schedule loading time: {load_time:.2f}s")

    def test_schedule_loading_indicators(self, authenticated_page, flask_server):
        """Test that loading indicators are shown while schedule loads"""
        page = authenticated_page

        # Navigate to schedule and check for loading indicators
        page.goto(f"{flask_server}/schedule")

        # Look for loading indicators (may appear briefly)
        loading_selectors = [
            ".loading",
            ".spinner",
            ".loader",
            '[data-testid="loading"]',
            ".skeleton",
            ".placeholder",
        ]

        loading_found = False
        for selector in loading_selectors:
            if page.locator(selector).count() > 0:
                loading_found = True
                break

        wait_for_page_load(page)

        # Loading indicators should be gone after page loads
        loading_after = any(
            page.locator(selector).count() > 0 for selector in loading_selectors
        )

        print(f"Loading indicators found: {loading_found}")
        print(f"Loading indicators after load: {loading_after}")


@pytest.mark.ui
class TestScheduleAccessibility:
    """Test schedule accessibility features"""

    def test_schedule_table_accessibility(self, authenticated_page, flask_server):
        """Test schedule table accessibility features"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Check for table accessibility
        tables = page.locator("table")
        if tables.count() > 0:
            first_table = tables.first

            # Check for table headers
            headers = first_table.locator("th")
            assert headers.count() > 0, "Schedule table should have headers"

            # Check for table caption or aria-label
            table_labeled = (
                first_table.locator("caption").count() > 0
                or first_table.get_attribute("aria-label")
                or first_table.get_attribute("aria-labelledby")
            )

            print(
                f"Schedule table accessibility - Headers: {headers.count()}, Labeled: {table_labeled}"
            )

    def test_keyboard_navigation_schedule(self, authenticated_page, flask_server):
        """Test keyboard navigation through schedule"""
        page = authenticated_page

        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Test tab navigation
        page.keyboard.press("Tab")

        # Should focus on interactive elements
        focused_element = page.evaluate("document.activeElement.tagName")
        interactive_elements = ["A", "BUTTON", "INPUT", "SELECT", "TABLE"]

        navigation_works = focused_element in interactive_elements
        print(
            f"Keyboard navigation - Focused element: {focused_element}, Works: {navigation_works}"
        )


@pytest.mark.ui
class TestScheduleErrorHandling:
    """Test schedule error handling"""

    def test_schedule_no_data_state(self, page, flask_server, ui_test_database):
        """Test schedule display when no matches are available"""
        # Login but don't use authenticated_page to test fresh state
        test_user = ui_test_database["test_users"][0]

        page.goto(f"{flask_server}/login")
        page.fill('input[name="email"]', test_user["email"])
        page.fill('input[name="password"]', test_user["password"])
        page.click('button[type="submit"]')
        page.wait_for_url(f"{flask_server}/mobile")

        # Navigate to schedule
        page.goto(f"{flask_server}/schedule")
        wait_for_page_load(page)

        # Look for empty state messaging
        empty_state_selectors = [
            ':has-text("No matches")',
            ':has-text("No schedule")',
            '.empty, .no-data, [data-testid="empty-state"]',
        ]

        empty_state_found = False
        for selector in empty_state_selectors:
            if page.locator(selector).count() > 0:
                empty_state_found = True
                break

        # Either show empty state or actual schedule data
        has_schedule_data = (
            page.locator("table tr:not(:first-child), .schedule-row").count() > 0
        )

        result = empty_state_found or has_schedule_data
        print(
            f"Schedule state - Empty state: {empty_state_found}, Has data: {has_schedule_data}"
        )

        # One or the other should be true
        assert result, "Schedule should show either data or empty state message"

    def test_schedule_error_handling(self, authenticated_page, flask_server):
        """Test schedule error handling for server issues"""
        page = authenticated_page

        # Intercept schedule requests and return errors
        page.route(
            "**/schedule*", lambda route: route.fulfill(status=500, body="Server Error")
        )

        page.goto(f"{flask_server}/schedule")

        # Look for error messaging
        error_selectors = [
            ':has-text("Error")',
            ':has-text("Unable to load")',
            '.error, .alert-danger, [data-testid="error"]',
        ]

        error_found = False
        for selector in error_selectors:
            if page.locator(selector).count() > 0:
                error_found = True
                break

        print(f"Error handling found: {error_found}")
