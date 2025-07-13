#!/usr/bin/env python3
"""
Test Mass User UI Testing System
================================

This script tests the mass user UI testing system to ensure it works correctly
before running with 100 users.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_players_data_loading():
    """Test that APTA_CHICAGO players data can be loaded"""
    print("🧪 Testing players data loading...")
    
    try:
        players_file = 'data/leagues/APTA_CHICAGO/players.json'
        if not os.path.exists(players_file):
            print("❌ Players data file not found")
            return False
            
        with open(players_file, 'r') as f:
            players_data = json.load(f)
            
        print(f"✅ Loaded {len(players_data)} players from APTA_CHICAGO")
        
        # Check data structure
        if not players_data:
            print("❌ No players data found")
            return False
            
        sample_player = players_data[0]
        required_fields = ['First Name', 'Last Name', 'Player ID', 'Club', 'Series']
        
        for field in required_fields:
            if field not in sample_player:
                print(f"❌ Missing required field: {field}")
                return False
                
        print("✅ Players data structure is valid")
        return True
        
    except Exception as e:
        print(f"❌ Error loading players data: {e}")
        return False

def test_mass_user_import():
    """Test that mass user testing module can be imported"""
    print("🧪 Testing mass user module import...")
    
    try:
        from ui_tests.test_mass_user_ui import MassUserTestRunner, MassUserTestResult
        print("✅ Mass user testing module imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing mass user module: {e}")
        return False

def test_user_selection():
    """Test user selection logic"""
    print("🧪 Testing user selection logic...")
    
    try:
        from ui_tests.test_mass_user_ui import MassUserTestRunner
        
        # Create test runner with small number of users
        runner = MassUserTestRunner(num_users=5)
        
        # Load players data
        runner.load_players_data()
        
        # Select users
        runner.select_test_users()
        
        if len(runner.selected_users) != 5:
            print(f"❌ Expected 5 users, got {len(runner.selected_users)}")
            return False
            
        # Check user diversity
        clubs = set(user['Club'] for user in runner.selected_users)
        series = set(user['Series'] for user in runner.selected_users)
        
        print(f"✅ Selected {len(runner.selected_users)} users from {len(clubs)} clubs and {len(series)} series")
        return True
        
    except Exception as e:
        print(f"❌ Error in user selection: {e}")
        return False

def test_report_generation():
    """Test report generation functionality"""
    print("🧪 Testing report generation...")
    
    try:
        from ui_tests.test_mass_user_ui import MassUserTestRunner, MassUserTestResult
        
        # Create test runner
        runner = MassUserTestRunner(num_users=3)
        
        # Create mock results
        runner.selected_users = [
            {'First Name': 'Test', 'Last Name': 'User1', 'Club': 'Test Club', 'Series': 'Test Series'},
            {'First Name': 'Test', 'Last Name': 'User2', 'Club': 'Test Club', 'Series': 'Test Series'},
            {'First Name': 'Test', 'Last Name': 'User3', 'Club': 'Test Club', 'Series': 'Test Series'}
        ]
        
        # Add mock test results
        for i, user in enumerate(runner.selected_users):
            for test_type in ['registration', 'availability', 'pickup_games']:
                result = MassUserTestResult(user, test_type)
                result.complete(True if i < 2 else False, "Test error" if i == 2 else None)
                runner.results.append(result)
        
        # Generate report
        report = runner.generate_report()
        
        # Check report content
        if 'Test Summary' not in report:
            print("❌ Report missing Test Summary section")
            return False
            
        if 'Results by Test Type' not in report:
            print("❌ Report missing Results by Test Type section")
            return False
            
        print("✅ Report generation works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error in report generation: {e}")
        return False

def test_directory_structure():
    """Test that required directories exist"""
    print("🧪 Testing directory structure...")
    
    required_dirs = [
        'ui_tests/reports',
        'ui_tests/screenshots'
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"❌ Required directory missing: {dir_path}")
            return False
            
    print("✅ All required directories exist")
    return True

def test_test_environment():
    """Test that test environment is properly configured"""
    print("🧪 Testing test environment...")
    
    try:
        from ui_tests.conftest import start_flask_server, stop_flask_server
        
        # Test Flask server start
        start_flask_server()
        print("✅ Flask server start works")
        
        # Test Flask server stop
        stop_flask_server()
        print("✅ Flask server stop works")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in test environment: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Mass User UI Testing System")
    print("=" * 50)
    
    tests = [
        ("Players Data Loading", test_players_data_loading),
        ("Mass User Module Import", test_mass_user_import),
        ("User Selection Logic", test_user_selection),
        ("Report Generation", test_report_generation),
        ("Directory Structure", test_directory_structure),
        ("Test Environment", test_test_environment)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Mass user testing system is ready.")
        print("\n💡 You can now run:")
        print("   python run_ui_tests.py --mass-user")
        print("   python run_ui_tests.py --mass-user --num-users 50")
        return 0
    else:
        print("⚠️  Some tests failed. Please fix issues before running mass user testing.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 