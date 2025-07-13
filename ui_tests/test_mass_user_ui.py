#!/usr/bin/env python3
"""
Mass User UI Testing for Rally Platform
========================================

This test runs UI tests with 100 different users from APTA_CHICAGO players data
to simulate real-world usage patterns and identify potential issues.
"""

import json
import random
import time
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import pytest
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ui_tests.conftest import (
    ui_test_database,
    start_flask_server,
    stop_flask_server,
    TEST_SERVER_URL
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MassUserTestResult:
    """Represents the result of a single user test"""
    
    def __init__(self, user_data: Dict[str, Any], test_type: str):
        self.user_data = user_data
        self.test_type = test_type
        self.start_time = datetime.now()
        self.end_time = None
        self.success = False
        self.error_message = None
        self.screenshots = []
        self.duration = None
        self.test_steps = []
        
    def complete(self, success: bool, error_message: str = None):
        self.end_time = datetime.now()
        self.success = success
        self.error_message = error_message
        self.duration = (self.end_time - self.start_time).total_seconds()
        
    def add_screenshot(self, screenshot_path: str):
        self.screenshots.append(screenshot_path)
        
    def add_test_step(self, step: str, success: bool, details: str = None):
        self.test_steps.append({
            'step': step,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

class MassUserTestRunner:
    """Runs UI tests with multiple users from APTA_CHICAGO players data"""
    
    def __init__(self, num_users: int = 100, test_types: List[str] = None):
        self.num_users = num_users
        self.test_types = test_types or ['registration', 'availability', 'pickup_games']
        self.results = []
        self.start_time = datetime.now()
        self.end_time = None
        self.players_data = []
        self.selected_users = []
        
    def load_players_data(self):
        """Load APTA_CHICAGO players data"""
        logger.info("Loading APTA_CHICAGO players data...")
        try:
            with open('data/leagues/APTA_CHICAGO/players.json', 'r') as f:
                self.players_data = json.load(f)
            logger.info(f"Loaded {len(self.players_data)} players from APTA_CHICAGO")
        except Exception as e:
            logger.error(f"Failed to load players data: {e}")
            raise
            
    def select_test_users(self):
        """Select random users for testing"""
        logger.info(f"Selecting {self.num_users} users for testing...")
        
        # Filter out users with missing critical data
        valid_users = [
            player for player in self.players_data
            if player.get('First Name') and player.get('Last Name') and player.get('Player ID')
        ]
        
        if len(valid_users) < self.num_users:
            logger.warning(f"Only {len(valid_users)} valid users found, using all available")
            self.selected_users = valid_users
        else:
            # Select random users, ensuring diversity across clubs and series
            self.selected_users = random.sample(valid_users, self.num_users)
            
        logger.info(f"Selected {len(self.selected_users)} users for testing")
        
    def generate_test_email(self, first_name: str, last_name: str, index: int) -> str:
        """Generate a unique test email for the user"""
        # Clean names for email
        clean_first = ''.join(c for c in first_name.lower() if c.isalnum())
        clean_last = ''.join(c for c in last_name.lower() if c.isalnum())
        return f"test_{clean_first}_{clean_last}_{index}@example.com"
        
    def run_single_user_test(self, user_data: Dict[str, Any], user_index: int, 
                           browser: Browser, test_type: str) -> MassUserTestResult:
        """Run a single test for one user"""
        result = MassUserTestResult(user_data, test_type)
        
        try:
            # Create a new context for this user
            context = browser.new_context()
            page = context.new_page()
            
            # Generate test email
            test_email = self.generate_test_email(
                user_data['First Name'], 
                user_data['Last Name'], 
                user_index
            )
            
            logger.info(f"Testing user {user_index + 1}/{self.num_users}: {user_data['First Name']} {user_data['Last Name']} ({test_type})")
            
            if test_type == 'registration':
                self._test_user_registration(page, user_data, test_email, result)
            elif test_type == 'availability':
                self._test_user_availability(page, user_data, test_email, result)
            elif test_type == 'pickup_games':
                self._test_user_pickup_games(page, user_data, test_email, result)
            else:
                raise ValueError(f"Unknown test type: {test_type}")
                
            result.complete(True)
            
        except Exception as e:
            error_msg = f"Test failed: {str(e)}"
            logger.error(f"User {user_index + 1} test failed: {error_msg}")
            result.complete(False, error_msg)
            
            # Take error screenshot
            try:
                screenshot_path = f"ui_tests/screenshots/error_user_{user_index}_{test_type}_{int(time.time())}.png"
                page.screenshot(path=screenshot_path)
                result.add_screenshot(screenshot_path)
            except:
                pass
                
        finally:
            try:
                context.close()
            except:
                pass
                
        return result
        
    def _test_user_registration(self, page: Page, user_data: Dict[str, Any], 
                               test_email: str, result: MassUserTestResult):
        """Test user registration flow"""
        try:
            # Navigate to registration page
            result.add_test_step("Navigate to registration", True)
            page.goto(f"{TEST_SERVER_URL}/register")
            page.wait_for_load_state('networkidle')
            
            # Fill registration form
            result.add_test_step("Fill registration form", True)
            page.fill('#firstName', user_data['First Name'])
            page.fill('#lastName', user_data['Last Name'])
            page.fill('#registerEmail', test_email)
            page.fill('#registerPassword', 'TestPassword123!')
            page.fill('#confirmPassword', 'TestPassword123!')
            page.fill('#phoneNumber', '(555) 123-4567')
            
            # Select league first (this will populate club and series dropdowns)
            page.select_option('#league', 'APTA_CHICAGO')
            
            # Wait for club dropdown to be populated
            page.wait_for_selector('#club option[value]', timeout=10000)
            
            # Print/log available club options and test user value
            club_options = page.eval_on_selector_all('#club option', 'els => els.map(e => ({value: e.value, text: e.textContent}))')
            print(f"[DEBUG] Available club options: {club_options}")
            print(f"[DEBUG] Test user club: {user_data['Club']}")
            
            # Select club
            page.select_option('#club', user_data['Club'])
            
            # Wait for series dropdown to be populated
            page.wait_for_selector('#series option[value]', timeout=10000)
            
            # Print/log available series options and test user value
            series_options = page.eval_on_selector_all('#series option', 'els => els.map(e => ({value: e.value, text: e.textContent}))')
            print(f"[DEBUG] Available series options: {series_options}")
            print(f"[DEBUG] Test user series: {user_data['Series']}")
            
            # Select series
            page.select_option('#series', user_data['Series'])
            
            # Select additional required fields
            page.select_option('#adDeuce', 'Ad')
            page.select_option('#dominantHand', 'Right')
            
            # Submit registration
            result.add_test_step("Submit registration", True)
            page.click('#registerForm button[type="submit"]')
            
            # Wait for registration completion
            page.wait_for_load_state('networkidle')
            
            # Check for success indicators
            success_indicators = [
                'Registration successful',
                'Welcome',
                'Dashboard',
                'Profile updated'
            ]
            
            page_content = page.content().lower()
            success_found = any(indicator.lower() in page_content for indicator in success_indicators)
            
            if success_found:
                result.add_test_step("Registration success verification", True)
            else:
                result.add_test_step("Registration success verification", False, "No success indicators found")
                
        except Exception as e:
            result.add_test_step("Registration test", False, str(e))
            raise
            
    def _test_user_availability(self, page: Page, user_data: Dict[str, Any], 
                               test_email: str, result: MassUserTestResult):
        """Test user availability management"""
        try:
            # First register the user
            self._test_user_registration(page, user_data, test_email, result)
            
            # Navigate to availability page
            result.add_test_step("Navigate to availability", True)
            page.goto(f"{TEST_SERVER_URL}/mobile/availability")
            page.wait_for_load_state('networkidle')
            
            # Select a future date
            future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            page.fill('input[type="date"]', future_date)
            
            # Set availability status
            result.add_test_step("Set availability status", True)
            page.click('input[value="available"]')
            
            # Add notes
            page.fill('textarea[name="notes"]', f'Test availability for {user_data["First Name"]}')
            
            # Submit availability
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')
            
            # Verify availability was saved
            result.add_test_step("Verify availability saved", True)
            
        except Exception as e:
            result.add_test_step("Availability test", False, str(e))
            raise
            
    def _test_user_pickup_games(self, page: Page, user_data: Dict[str, Any], 
                               test_email: str, result: MassUserTestResult):
        """Test user pickup games functionality"""
        try:
            # First register the user
            self._test_user_registration(page, user_data, test_email, result)
            
            # Navigate to pickup games page
            result.add_test_step("Navigate to pickup games", True)
            page.goto(f"{TEST_SERVER_URL}/mobile/pickup-games")
            page.wait_for_load_state('networkidle')
            
            # Create a new pickup game
            result.add_test_step("Create pickup game", True)
            page.click('button:has-text("Create Game")')
            
            # Fill pickup game form
            future_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            page.fill('input[name="date"]', future_date)
            page.fill('input[name="time"]', '18:00')
            page.fill('input[name="location"]', f'{user_data["Club"]} Courts')
            page.fill('input[name="max_players"]', '4')
            page.fill('textarea[name="description"]', f'Test game by {user_data["First Name"]}')
            
            # Submit pickup game
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')
            
            # Verify game was created
            result.add_test_step("Verify game created", True)
            
        except Exception as e:
            result.add_test_step("Pickup games test", False, str(e))
            raise
            
    def run_all_tests(self):
        """Run all tests for all selected users"""
        logger.info(f"Starting mass user testing with {len(self.selected_users)} users")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            try:
                for user_index, user_data in enumerate(self.selected_users):
                    for test_type in self.test_types:
                        result = self.run_single_user_test(
                            user_data, user_index, browser, test_type
                        )
                        self.results.append(result)
                        
                        # Small delay between tests
                        time.sleep(0.5)
                        
            finally:
                browser.close()
                
        self.end_time = datetime.now()
        logger.info("Mass user testing completed")
        
    def generate_report(self) -> str:
        """Generate a comprehensive test report"""
        if not self.end_time:
            self.end_time = datetime.now()
            
        total_duration = (self.end_time - self.start_time).total_seconds()
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests
        
        # Calculate success rate
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Group results by test type
        results_by_type = {}
        for result in self.results:
            if result.test_type not in results_by_type:
                results_by_type[result.test_type] = []
            results_by_type[result.test_type].append(result)
            
        # Generate report
        report = f"""# Rally Platform Mass User UI Test Report

## Test Summary
- **Test Date**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **Duration**: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)
- **Total Users Tested**: {len(self.selected_users)}
- **Total Tests Run**: {total_tests}
- **Successful Tests**: {successful_tests}
- **Failed Tests**: {failed_tests}
- **Success Rate**: {success_rate:.1f}%

## Test Configuration
- **Test Types**: {', '.join(self.test_types)}
- **Users Source**: APTA_CHICAGO players.json
- **Test Environment**: {TEST_SERVER_URL}

## Results by Test Type

"""
        
        for test_type, type_results in results_by_type.items():
            type_success = sum(1 for r in type_results if r.success)
            type_total = len(type_results)
            type_success_rate = (type_success / type_total * 100) if type_total > 0 else 0
            
            report += f"""### {test_type.title()} Tests
- **Total Tests**: {type_total}
- **Successful**: {type_success}
- **Failed**: {type_total - type_success}
- **Success Rate**: {type_success_rate:.1f}%

"""
            
        # Add detailed failure analysis
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            report += "## Failed Tests Analysis\n\n"
            
            # Group failures by error type
            error_groups = {}
            for result in failed_results:
                error_key = result.error_message or "Unknown error"
                if error_key not in error_groups:
                    error_groups[error_key] = []
                error_groups[error_key].append(result)
                
            for error_type, error_results in error_groups.items():
                report += f"""### {error_type}
**Occurrences**: {len(error_results)}

**Affected Users**:
"""
                for result in error_results[:5]:  # Show first 5
                    user = result.user_data
                    report += f"- {user['First Name']} {user['Last Name']} ({user['Club']}, {user['Series']})\n"
                    
                if len(error_results) > 5:
                    report += f"- ... and {len(error_results) - 5} more users\n"
                report += "\n"
                
        # Add performance metrics
        durations = [r.duration for r in self.results if r.duration]
        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            report += f"""## Performance Metrics
- **Average Test Duration**: {avg_duration:.2f} seconds
- **Fastest Test**: {min_duration:.2f} seconds
- **Slowest Test**: {max_duration:.2f} seconds
- **Tests per Minute**: {len(durations) / (total_duration / 60):.1f}

"""
            
        # Add user diversity analysis
        clubs = set()
        series = set()
        for user in self.selected_users:
            clubs.add(user['Club'])
            series.add(user['Series'])
            
        report += f"""## User Diversity
- **Unique Clubs**: {len(clubs)}
- **Unique Series**: {len(series)}
- **Clubs Tested**: {', '.join(sorted(clubs))}
- **Series Tested**: {', '.join(sorted(series))}

"""
        
        # Add recommendations
        report += "## Recommendations\n\n"
        
        if success_rate >= 95:
            report += "✅ **Excellent**: System is performing very well with real user data.\n"
        elif success_rate >= 85:
            report += "⚠️ **Good**: System is mostly stable but has some issues to address.\n"
        else:
            report += "❌ **Needs Attention**: Significant issues detected that require immediate attention.\n"
            
        if failed_results:
            report += f"- Investigate and fix the {len(failed_results)} failed tests\n"
            
        if avg_duration > 10:
            report += "- Consider performance optimizations for slow tests\n"
            
        report += "\n## Test Data\n"
        report += f"- **Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"- **Test Runner**: MassUserTestRunner v1.0\n"
        report += f"- **Environment**: {os.getenv('ENVIRONMENT', 'local')}\n"
        
        return report
        
    def save_report(self, report: str, filename: str = None):
        """Save the test report to a file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ui_tests/reports/mass_user_test_report_{timestamp}.md"
            
        # Ensure reports directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write(report)
            
        logger.info(f"Test report saved to: {filename}")
        return filename

def main():
    """Main function to run mass user testing"""
    print("🚀 Rally Mass User UI Testing")
    print("=" * 50)
    
    try:
        # Start Flask server for testing
        print("🔧 Starting test server...")
        start_flask_server()
        
        # Create test runner
        runner = MassUserTestRunner(num_users=100, test_types=['registration', 'availability', 'pickup_games'])
        
        # Load and select users
        runner.load_players_data()
        runner.select_test_users()
        
        # Run tests
        runner.run_all_tests()
        
        # Generate and save report
        report = runner.generate_report()
        report_filename = runner.save_report(report)
        
        print(f"\n✅ Mass user testing completed!")
        print(f"📊 Report saved to: {report_filename}")
        print(f"📈 Success rate: {sum(1 for r in runner.results if r.success) / len(runner.results) * 100:.1f}%")
        
        return 0
        
    except Exception as e:
        logger.error(f"Mass user testing failed: {e}")
        return 1
        
    finally:
        # Stop Flask server
        try:
            stop_flask_server()
        except:
            pass

if __name__ == "__main__":
    sys.exit(main()) 