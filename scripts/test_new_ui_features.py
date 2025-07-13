#!/usr/bin/env python3
"""
Test New UI Features
===================

Quick test script to verify that the new availability and pickup games UI tests work correctly.
This script runs a subset of the new tests to ensure they're properly integrated.
"""

import subprocess
import sys
import os

def run_test_command(cmd, description):
    """Run a test command and report results"""
    print(f"\n🧪 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Test passed")
            return True
        else:
            print("❌ Test failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Test timed out")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    print("🚀 Testing New UI Features")
    print("=" * 50)
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    
    # Test 1: Check if new test files exist
    print("\n📁 Checking test files...")
    test_files = [
        "ui_tests/test_availability_ui.py",
        "ui_tests/test_pickup_games_ui.py"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"✅ {test_file} exists")
        else:
            print(f"❌ {test_file} missing")
            return 1
    
    # Test 2: Run availability tests (smoke only)
    availability_cmd = [
        sys.executable, "run_ui_tests.py",
        "--availability",
        "--smoke",
        "--browser", "chromium",
        "--headless",
        "-v"
    ]
    
    availability_success = run_test_command(availability_cmd, "Running Availability Smoke Tests")
    
    # Test 3: Run pickup games tests (smoke only)
    pickup_cmd = [
        sys.executable, "run_ui_tests.py",
        "--pickup-games",
        "--smoke",
        "--browser", "chromium",
        "--headless",
        "-v"
    ]
    
    pickup_success = run_test_command(pickup_cmd, "Running Pickup Games Smoke Tests")
    
    # Test 4: Run critical tests for both features
    critical_cmd = [
        sys.executable, "run_ui_tests.py",
        "--critical",
        "--test-pattern", "availability or pickup",
        "--browser", "chromium",
        "--headless",
        "-v"
    ]
    
    critical_success = run_test_command(critical_cmd, "Running Critical Tests for New Features")
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"Availability Tests: {'✅ PASS' if availability_success else '❌ FAIL'}")
    print(f"Pickup Games Tests: {'✅ PASS' if pickup_success else '❌ FAIL'}")
    print(f"Critical Tests: {'✅ PASS' if critical_success else '❌ FAIL'}")
    
    all_passed = availability_success and pickup_success and critical_success
    
    if all_passed:
        print("\n🎉 All new UI feature tests passed!")
        print("\n📋 Available test commands:")
        print("  python run_ui_tests.py --availability     # Run all availability tests")
        print("  python run_ui_tests.py --pickup-games     # Run all pickup games tests")
        print("  python run_ui_tests.py --availability --smoke  # Run availability smoke tests")
        print("  python run_ui_tests.py --pickup-games --smoke  # Run pickup games smoke tests")
        print("  python run_ui_tests.py --critical         # Run all critical tests")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 