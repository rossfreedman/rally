#!/usr/bin/env python3
"""
Deploy Weather Integration for Rally Platform
Sets up the weather cache table and validates the integration
"""

import os
import sys
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"   stdout: {e.stdout}")
        if e.stderr:
            print(f"   stderr: {e.stderr}")
        return False

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment configuration...")
    
    # Check for API key
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        print("⚠️  OPENWEATHER_API_KEY not found in environment")
        print("   Please set this environment variable with your OpenWeatherMap API key")
        print("   Get a free key from: https://openweathermap.org/api")
        return False
    
    print(f"✅ OpenWeather API key found")
    return True

def deploy_database_migration():
    """Deploy the weather cache table"""
    print("🗄️  Deploying database migration...")
    
    # Check if migration file exists
    migration_file = "data/dbschema/migrations/20250115_140000_add_weather_cache_table.sql"
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    # Run the migration using dbschema
    return run_command(
        "python data/dbschema/dbschema_workflow.py --auto",
        "Deploying weather cache table"
    )

def test_integration():
    """Test the weather integration"""
    print("🧪 Testing weather integration...")
    
    return run_command(
        "python scripts/test_weather_integration.py",
        "Running weather integration tests"
    )

def main():
    """Main deployment function"""
    print("🌤️ Rally Weather Integration Deployment")
    print("=" * 50)
    
    # Step 1: Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please configure OPENWEATHER_API_KEY.")
        return False
    
    # Step 2: Deploy database migration
    if not deploy_database_migration():
        print("\n❌ Database migration failed.")
        return False
    
    # Step 3: Test integration
    if not test_integration():
        print("\n❌ Integration test failed.")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Weather integration deployed successfully!")
    print("\n📋 Next steps:")
    print("   1. Verify weather data appears in notifications")
    print("   2. Monitor API usage in OpenWeatherMap dashboard")
    print("   3. Check logs for any weather-related errors")
    print("\n📚 Documentation: docs/WEATHER_INTEGRATION_GUIDE.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 