#!/usr/bin/env python3

"""
Rally UI Test Runner
Command-line interface for running Playwright-based UI tests
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Colors for output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color


def print_status(message):
    print(f"{BLUE}[UI-INFO]{NC} {message}")


def print_success(message):
    print(f"{GREEN}[UI-SUCCESS]{NC} {message}")


def print_warning(message):
    print(f"{YELLOW}[UI-WARNING]{NC} {message}")


def print_error(message):
    print(f"{RED}[UI-ERROR]{NC} {message}")


def check_playwright_installation():
    """Check if Playwright is installed and browsers are available"""
    try:
        import playwright

        print_success("Playwright package found")

        # Check if browsers are installed
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print_success("Playwright browsers are installed")
            return True
        else:
            print_warning("Some Playwright browsers may not be installed")
            return False

    except ImportError:
        print_error("Playwright not installed. Install with: pip install playwright")
        return False


def install_playwright_browsers():
    """Install Playwright browsers"""
    print_status("Installing Playwright browsers...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install"], check=True
        )
        print_success("Playwright browsers installed successfully")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to install Playwright browsers")
        return False


def check_flask_server():
    """Check if Flask server is running"""
    try:
        import requests

        test_url = os.getenv("TEST_SERVER_URL", "http://localhost:5000")
        response = requests.get(f"{test_url}/health", timeout=2)
        if response.status_code == 200:
            print_success(f"Flask server is running at {test_url}")
            return True
        else:
            print_warning(f"Flask server responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print_warning("Flask server is not running - tests will start their own server")
        return False


def run_ui_tests(args):
    """Run UI tests with specified configuration"""

    # Set environment variables
    env = os.environ.copy()
    env.update(
        {
            "HEADLESS": "true" if args.headless else "false",
            "BROWSER": args.browser,
            "TEST_SERVER_PORT": str(args.port),
            "TEST_SERVER_URL": f"http://localhost:{args.port}",
        }
    )

    if args.database_url:
        env["TEST_DATABASE_URL"] = args.database_url

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest", "ui_tests/"]

    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    if args.verbose > 1:
        cmd.append("-s")

    # Add specific test selection
    if args.test_pattern:
        cmd.extend(["-k", args.test_pattern])

    # Add markers
    if args.smoke:
        cmd.extend(["-m", "smoke"])
    elif args.critical:
        cmd.extend(["-m", "critical"])
    elif args.marker:
        cmd.extend(["-m", args.marker])

    # Add specific test files
    if args.registration:
        cmd.append("ui_tests/test_registration_ui.py")
    elif args.schedule:
        cmd.append("ui_tests/test_schedule_ui.py")
    elif args.polls:
        cmd.append("ui_tests/test_poll_ui.py")

    # Add reporting options
    if args.html_report:
        cmd.extend(["--html", args.html_report])

    if args.junit_xml:
        cmd.extend(["--junit-xml", args.junit_xml])

    # Add screenshot options
    if args.screenshot_dir:
        env["SCREENSHOT_DIR"] = args.screenshot_dir

    # Add parallel execution
    if args.parallel > 1:
        cmd.extend(["-n", str(args.parallel)])

    # Add timeout
    if args.timeout:
        cmd.extend(["--timeout", str(args.timeout)])

    print_status(f"Running UI tests with command: {' '.join(cmd)}")
    print_status(f"Browser: {args.browser}, Headless: {args.headless}")

    try:
        result = subprocess.run(cmd, env=env, cwd=os.getcwd())
        return result.returncode == 0
    except KeyboardInterrupt:
        print_warning("UI tests interrupted by user")
        return False
    except Exception as e:
        print_error(f"Error running UI tests: {e}")
        return False


def run_quick_ui_check(args):
    """Run a quick UI test check"""
    print_status("Running quick UI test check...")

    env = os.environ.copy()
    env.update(
        {"HEADLESS": "true", "BROWSER": "chromium", "TEST_SERVER_PORT": str(args.port)}
    )

    # Run just the critical smoke tests
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "ui_tests/",
        "-m",
        "critical",
        "-v",
        "--tb=short",
    ]

    try:
        result = subprocess.run(cmd, env=env, timeout=300)  # 5 minute timeout
        if result.returncode == 0:
            print_success("Quick UI check passed!")
            return True
        else:
            print_warning("Quick UI check found issues")
            return False
    except subprocess.TimeoutExpired:
        print_error("Quick UI check timed out")
        return False
    except Exception as e:
        print_error(f"Quick UI check failed: {e}")
        return False


def debug_ui_test(args):
    """Run UI tests in debug mode"""
    print_status("Running UI tests in debug mode...")

    env = os.environ.copy()
    env.update(
        {
            "HEADLESS": "false",  # Always run in headed mode for debugging
            "BROWSER": args.browser,
            "TEST_SERVER_PORT": str(args.port),
            "PYTEST_CURRENT_TEST": "1",  # Enable pytest debugging
        }
    )

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "ui_tests/",
        "-v",
        "-s",
        "--tb=long",
        "--capture=no",  # Don't capture output
    ]

    if args.test_pattern:
        cmd.extend(["-k", args.test_pattern])

    print_status("Debug mode: Browser will be visible, tests will run slowly")
    print_status("Press Ctrl+C to stop debugging")

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print_warning("Debug session interrupted")


def generate_test_report(args):
    """Generate a comprehensive UI test report"""
    print_status("Generating UI test report...")

    report_dir = Path(args.report_dir)
    report_dir.mkdir(exist_ok=True)

    # Run tests with multiple browsers if requested
    browsers = ["chromium"]
    if args.all_browsers:
        browsers = ["chromium", "firefox", "webkit"]

    results = {}

    for browser in browsers:
        print_status(f"Testing with {browser}...")

        env = os.environ.copy()
        env.update(
            {"HEADLESS": "true", "BROWSER": browser, "TEST_SERVER_PORT": str(args.port)}
        )

        html_report = report_dir / f"ui_test_report_{browser}.html"
        junit_xml = report_dir / f"ui_test_results_{browser}.xml"

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "ui_tests/",
            "-v",
            "--html",
            str(html_report),
            "--junit-xml",
            str(junit_xml),
        ]

        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            results[browser] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.returncode == 0:
                print_success(f"{browser} tests passed")
            else:
                print_warning(f"{browser} tests had failures")

        except Exception as e:
            print_error(f"Error testing with {browser}: {e}")
            results[browser] = {"error": str(e)}

    # Generate summary report
    summary_file = report_dir / "ui_test_summary.json"
    with open(summary_file, "w") as f:
        json.dump(results, f, indent=2)

    print_success(f"UI test report generated in {report_dir}")
    print_status(f"Summary: {summary_file}")

    return all(r.get("returncode") == 0 for r in results.values() if "returncode" in r)


def main():
    parser = argparse.ArgumentParser(
        description="Rally UI Test Runner - Playwright-based end-to-end testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --quick                          # Quick smoke test
  %(prog)s --registration --headed          # Test registration with visible browser
  %(prog)s --all --browser firefox          # Run all tests with Firefox
  %(prog)s --debug -k "test_login"          # Debug specific test
  %(prog)s --report --all-browsers          # Generate cross-browser report
        """,
    )

    # Test selection
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--all", action="store_true", help="Run all UI tests")
    test_group.add_argument(
        "--quick", action="store_true", help="Run quick smoke tests only"
    )
    test_group.add_argument(
        "--registration", action="store_true", help="Run registration UI tests"
    )
    test_group.add_argument(
        "--schedule", action="store_true", help="Run schedule UI tests"
    )
    test_group.add_argument("--polls", action="store_true", help="Run polls UI tests")
    test_group.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode (headed browser, verbose output)",
    )
    test_group.add_argument(
        "--report", action="store_true", help="Generate comprehensive test report"
    )

    # Test filtering
    parser.add_argument("-k", "--test-pattern", help="Run tests matching this pattern")
    parser.add_argument(
        "-m", "--marker", help="Run tests with this marker (ui, critical, smoke)"
    )
    parser.add_argument("--smoke", action="store_true", help="Run smoke tests only")
    parser.add_argument(
        "--critical", action="store_true", help="Run critical tests only"
    )

    # Browser configuration
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser to use for testing",
    )
    parser.add_argument(
        "--headed", action="store_true", help="Run browser in headed mode (visible)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default)",
    )

    # Server configuration
    parser.add_argument(
        "--port", type=int, default=5000, help="Port for test Flask server"
    )
    parser.add_argument("--database-url", help="Test database URL (optional)")

    # Execution options
    parser.add_argument(
        "--parallel", type=int, default=1, help="Number of parallel test processes"
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Test timeout in seconds"
    )

    # Output options
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose output (use -vv for extra verbose)",
    )
    parser.add_argument("--html-report", help="Generate HTML report at specified path")
    parser.add_argument(
        "--junit-xml", help="Generate JUnit XML report at specified path"
    )
    parser.add_argument(
        "--screenshot-dir",
        default="ui_tests/screenshots",
        help="Directory for failure screenshots",
    )

    # Report generation
    parser.add_argument(
        "--report-dir", default="ui_test_reports", help="Directory for test reports"
    )
    parser.add_argument(
        "--all-browsers",
        action="store_true",
        help="Test with all browsers (chromium, firefox, webkit)",
    )

    # Setup options
    parser.add_argument(
        "--install-browsers",
        action="store_true",
        help="Install Playwright browsers and exit",
    )
    parser.add_argument(
        "--check-setup", action="store_true", help="Check UI test setup and exit"
    )

    args = parser.parse_args()

    # Handle special setup commands
    if args.install_browsers:
        install_playwright_browsers()
        return

    if args.check_setup:
        print_status("Checking UI test setup...")
        playwright_ok = check_playwright_installation()
        server_ok = check_flask_server()

        if playwright_ok:
            print_success("✅ Playwright setup OK")
        else:
            print_error("❌ Playwright setup issues")

        if server_ok:
            print_success("✅ Flask server OK")
        else:
            print_warning("⚠️  Flask server not running (tests will start their own)")

        return

    # Override headless if headed is specified
    if args.headed:
        args.headless = False

    # Check prerequisites
    if not check_playwright_installation():
        print_error("Playwright setup incomplete. Run with --install-browsers first")
        sys.exit(1)

    # Run tests based on mode
    success = False

    if args.quick:
        success = run_quick_ui_check(args)
    elif args.debug:
        debug_ui_test(args)
        return  # Debug mode doesn't return success/failure
    elif args.report:
        success = generate_test_report(args)
    else:
        # Default to running all tests if no specific selection
        if not any([args.registration, args.schedule, args.polls]):
            args.all = True
        success = run_ui_tests(args)

    if success:
        print_success("🎉 UI tests completed successfully!")
        sys.exit(0)
    else:
        print_error("❌ UI tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
