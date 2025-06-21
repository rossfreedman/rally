#!/usr/bin/env python3
"""
Rally Quick Test Script
Fast validation script for development workflow
"""

import sys
import os
import argparse
import subprocess
import json
from pathlib import Path

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_registration_tests():
    """Run registration tests quickly"""
    print("🧪 Running registration tests...")
    result = subprocess.run([
        'pytest', 'tests/test_registration.py', '-v', '--tb=short'
    ], capture_output=False)
    return result.returncode == 0

def run_security_tests():
    """Run security tests"""
    print("🔒 Running security tests...")
    result = subprocess.run([
        'pytest', 'tests/test_security.py', '-v', '--tb=short'
    ], capture_output=False)
    return result.returncode == 0

def run_schedule_tests():
    """Run schedule tests"""
    print("📅 Running schedule tests...")
    result = subprocess.run([
        'pytest', 'tests/test_schedule.py', '-v', '--tb=short'
    ], capture_output=False)
    return result.returncode == 0

def run_polls_tests():
    """Run polls tests"""
    print("🗳️ Running polls tests...")
    result = subprocess.run([
        'pytest', 'tests/test_polls.py', '-v', '--tb=short'
    ], capture_output=False)
    return result.returncode == 0

def scrape_fresh_data():
    """Scrape fresh test data"""
    print("🕷️ Scraping fresh test data...")
    result = subprocess.run([
        'python', 'tests/scrapers/random_league_scraper.py'
    ], capture_output=False)
    return result.returncode == 0

def validate_test_data():
    """Validate scraped test data"""
    print("✅ Validating test data...")
    
    fixtures_dir = Path('tests/fixtures')
    scraped_file = fixtures_dir / 'scraped_players.json'
    
    if not scraped_file.exists():
        print("❌ No scraped test data found")
        return False
    
    try:
        with open(scraped_file, 'r') as f:
            data = json.load(f)
        
        # Validate structure
        required_keys = ['metadata', 'valid_players', 'invalid_players']
        if not all(key in data for key in required_keys):
            print(f"❌ Missing required keys in test data: {required_keys}")
            return False
        
        valid_count = len(data['valid_players'])
        invalid_count = len(data['invalid_players'])
        
        print(f"✅ Test data validated:")
        print(f"   📊 {valid_count} valid players")
        print(f"   ❌ {invalid_count} invalid players")
        print(f"   🏆 Leagues: {', '.join(data['metadata'].get('leagues_scraped', []))}")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ Invalid JSON in scraped test data")
        return False
    except Exception as e:
        print(f"❌ Error validating test data: {e}")
        return False

def run_load_test():
    """Run a quick load test"""
    print("🚀 Running quick load test...")
    
    # Start Flask app in background
    import threading
    import time
    import requests
    
    def start_app():
        os.environ['FLASK_ENV'] = 'testing'
        subprocess.run(['python', 'server.py'], capture_output=True)
    
    app_thread = threading.Thread(target=start_app)
    app_thread.daemon = True
    app_thread.start()
    
    # Wait for app to start
    time.sleep(5)
    
    # Check if app is running
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code == 200:
            print("✅ Flask app started successfully")
            
            # Run quick load test
            result = subprocess.run([
                'locust', '-f', 'tests/load/load_test_registration.py',
                '--host', 'http://localhost:8080',
                '--users', '5',
                '--spawn-rate', '1',
                '--run-time', '30s',
                '--headless'
            ], capture_output=False, cwd='tests/load')
            
            return result.returncode == 0
        else:
            print("❌ Flask app health check failed")
            return False
    except requests.RequestException:
        print("❌ Could not connect to Flask app")
        return False

def check_test_environment():
    """Check if test environment is properly set up"""
    print("🔍 Checking test environment...")
    
    # Check Python packages
    required_packages = ['pytest', 'flask', 'sqlalchemy', 'psycopg2-binary']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Install with: pip install " + ' '.join(missing_packages))
        return False
    
    # Check PostgreSQL connection
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            database='postgres'
        )
        conn.close()
        print("✅ PostgreSQL connection successful")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False
    
    # Check test database
    test_db_url = os.getenv('TEST_DATABASE_URL', 'postgresql://postgres@localhost:5432/rally_test')
    print(f"✅ Test database URL: {test_db_url}")
    
    print("✅ Test environment looks good!")
    return True

def main():
    parser = argparse.ArgumentParser(description='Rally Quick Test Script')
    parser.add_argument('--registration', action='store_true', help='Run registration tests')
    parser.add_argument('--security', action='store_true', help='Run security tests')
    parser.add_argument('--schedule', action='store_true', help='Run schedule tests')
    parser.add_argument('--polls', action='store_true', help='Run polls tests')
    parser.add_argument('--scrape', action='store_true', help='Scrape fresh test data')
    parser.add_argument('--validate', action='store_true', help='Validate test data')
    parser.add_argument('--load', action='store_true', help='Run quick load test')
    parser.add_argument('--check-env', action='store_true', help='Check test environment')
    parser.add_argument('--all', action='store_true', help='Run all quick tests')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    success = True
    
    if args.check_env or args.all:
        success &= check_test_environment()
    
    if args.scrape or args.all:
        success &= scrape_fresh_data()
    
    if args.validate or args.all:
        success &= validate_test_data()
    
    if args.registration or args.all:
        success &= run_registration_tests()
    
    if args.security or args.all:
        success &= run_security_tests()
    
    if args.schedule or args.all:
        success &= run_schedule_tests()
    
    if args.polls or args.all:
        success &= run_polls_tests()
    
    if args.load:  # Not included in --all due to time
        success &= run_load_test()
    
    if success:
        print("\n🎉 All selected tests passed!")
    else:
        print("\n❌ Some tests failed. Check output above.")
        sys.exit(1)

if __name__ == '__main__':
    main() 