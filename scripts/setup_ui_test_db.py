#!/usr/bin/env python3
"""
Setup UI Test Database
=====================

Create the test database needed for UI tests.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and report results"""
    print(f"🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Success")
            return True
        else:
            print("❌ Failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🚀 Setting up UI Test Database")
    print("=" * 50)
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    
    # Step 1: Create test database
    create_db_cmd = [
        "createdb", "-h", "localhost", "-U", "postgres", "-p", "5432", "rally_test"
    ]
    
    if not run_command(create_db_cmd, "Creating rally_test database"):
        print("⚠️  Database might already exist, continuing...")
    
    # Step 2: Initialize database schema
    init_cmd = [
        sys.executable, "init_db.py"
    ]
    
    if not run_command(init_cmd, "Initializing database schema"):
        print("❌ Failed to initialize database schema")
        return 1
    
    # Step 3: Run migrations
    migration_cmd = [
        sys.executable, "-m", "alembic", "upgrade", "head"
    ]
    
    if not run_command(migration_cmd, "Running database migrations"):
        print("❌ Failed to run migrations")
        return 1
    
    print("\n🎉 UI Test Database Setup Complete!")
    print("\n📋 You can now run UI tests with:")
    print("  python run_ui_tests.py --availability --smoke")
    print("  python run_ui_tests.py --pickup-games --smoke")
    print("  python run_ui_tests.py --critical")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 