#!/usr/bin/env python3
"""
Database migration runner for Railway deployment.

This script ensures the database is properly set up before application startup.
It works with both new Alembic-managed databases and legacy setups.
"""

import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

# Add the app directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_database_state():
    """Check if database is already properly set up"""
    try:
        from database_config import get_db
        
        with get_db() as conn:
            with conn.cursor() as cursor:
                # Check if key tables exist and have data
                cursor.execute("SELECT COUNT(*) FROM players WHERE id IS NOT NULL")
                player_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM match_scores WHERE id IS NOT NULL") 
                match_count = cursor.fetchone()[0]
                
                print(f"📊 Database status check:")
                print(f"   Players: {player_count:,}")
                print(f"   Match Scores: {match_count:,}")
                
                # If we have substantial data, database is already set up
                if player_count > 2000 and match_count > 5000:
                    print("✅ Database is already fully populated and ready!")
                    return True
                    
                return False
                
    except Exception as e:
        print(f"⚠️  Could not check database state: {e}")
        return False

def run_alembic_migrations():
    """Run Alembic migrations if needed"""
    print("📋 Checking Alembic migration state...")
    
    try:
        # Check current migration state
        result = subprocess.run(
            ['alembic', 'current'], 
            capture_output=True, 
            text=True,
            check=True
        )
        
        current_migration = result.stdout.strip()
        print(f"Current migration: {current_migration}")
        
        # If we're at head, no migration needed
        if 'head' in current_migration or 'fddbba0e1328' in current_migration:
            print("✅ Database is at latest migration - no upgrade needed")
            return True
            
        # Run migration to head
        print("📋 Running Alembic upgrade to head...")
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'], 
            capture_output=True, 
            text=True,
            check=True
        )
        
        print("✅ Alembic migrations completed successfully")
        if result.stdout:
            print(f"Migration output: {result.stdout}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Alembic migration error: {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        # Don't fail deployment for migration issues
        print("⚠️  Continuing with application startup...")
        return True
        
    except FileNotFoundError:
        print("⚠️  Alembic not found - skipping migrations")
        return True

def run_legacy_migrations():
    """Run legacy migrations only if database is not already set up"""
    print("📋 Running legacy table creation migrations...")
    
    try:
        from migrations.create_leagues_tables import run_migration as run_leagues_migration
        from migrations.add_missing_user_columns import run_migration as run_columns_migration
        
        print("📋 Creating leagues tables...")
        run_leagues_migration()
        print("✅ Leagues tables migration completed")
        
        print("📋 Adding missing user columns...")
        run_columns_migration()
        print("✅ User columns migration completed")
        
        return True
        
    except ImportError as e:
        print(f"⚠️  Legacy migration modules not found: {e}")
        print("⚠️  Skipping legacy migrations - assuming Alembic-managed database")
        return True
    except Exception as e:
        print(f"⚠️  Legacy migration error: {str(e)}")
        print("⚠️  Continuing with application startup...")
        return True

def run_all_migrations():
    """Run all necessary migrations to bring the database up to date"""
    
    load_dotenv()
    print("🚀 Starting database migration check...")
    
    # First check if database is already properly set up
    if check_database_state():
        print("🎉 Database is already ready - skipping migrations!")
        return True
    
    print("📋 Database needs setup - running migrations...")
    
    try:
        # Try Alembic migrations first
        alembic_success = run_alembic_migrations()
        
        # If Alembic didn't set up the database, try legacy migrations
        if alembic_success and not check_database_state():
            print("📋 Database still needs setup - trying legacy migrations...")
            run_legacy_migrations()
        
        # Final check
        if check_database_state():
            print("🎉 Database is now ready for application startup!")
            return True
        else:
            print("⚠️  Database setup incomplete but continuing startup...")
            return True
            
    except Exception as e:
        print(f"❌ Migration error: {str(e)}")
        print("⚠️  Continuing with application startup anyway...")
        return True

if __name__ == '__main__':
    success = run_all_migrations()
    if not success:
        print("⚠️  Migration issues detected but allowing startup to continue...")
    print("✅ Database migration check completed!") 