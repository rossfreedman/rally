#!/usr/bin/env python3
"""
Deploy Production Migration via Railway CLI + Alembic
====================================================

This script uses Railway CLI to run Alembic migrations on production.
Best of both worlds: proper migration tracking + easy Railway deployment.
"""

import subprocess
import sys
import os

def check_railway_cli():
    """Check if Railway CLI is installed and authenticated"""
    try:
        # Check CLI exists
        result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Railway CLI not found")
            print("   Install it with: brew install railway")
            return False
        
        # Check authentication
        result = subprocess.run(['railway', 'whoami'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Not authenticated with Railway")
            print("   Run: railway login")
            return False
            
        print(f"✅ Railway CLI ready, authenticated as: {result.stdout.strip()}")
        return True
        
    except FileNotFoundError:
        print("❌ Railway CLI not found")
        print("   Install it with: brew install railway")
        return False

def check_project_link():
    """Verify we're linked to the correct project"""
    try:
        result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Project linked:")
            print(result.stdout)
            return True
        else:
            print("❌ No project linked")
            print("   Run: railway link")
            return False
    except Exception as e:
        print(f"❌ Error checking project: {e}")
        return False

def run_production_migration():
    """Run Alembic migration on production via Railway CLI"""
    print("🔄 Running Alembic migration on production...")
    
    try:
        # Use Railway CLI to run Alembic upgrade
        cmd = ['railway', 'run', 'alembic', 'upgrade', 'head']
        
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            print("\nMigration output:")
            print(result.stdout)
            if result.stderr:
                print("\nAdditional info:")
                print(result.stderr)
            return True
        else:
            print("❌ Migration failed!")
            print("Error output:")
            print(result.stderr)
            print("Standard output:")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

def verify_production_migration():
    """Verify the migration worked on production"""
    print("🔍 Verifying production migration...")
    
    verify_sql = """
    SELECT 
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'player_availability' AND column_name = 'user_id'
        ) THEN '✅ user_id column exists' 
        ELSE '❌ user_id column missing' END as column_status,
        
        CONCAT('Total records: ', COUNT(*)) as total_count
    FROM player_availability;
    """
    
    try:
        cmd = ['railway', 'run', 'psql', '$DATABASE_URL', '-c', verify_sql]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Verification completed:")
            print(result.stdout)
            return True
        else:
            print("❌ Verification failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error running verification: {e}")
        return False

def main():
    print("🚀 Railway Production Migration Deployment")
    print("=" * 50)
    
    # Check prerequisites
    if not check_railway_cli():
        return 1
    
    if not check_project_link():
        return 1
    
    # Confirm deployment
    print("\n🚨 PRODUCTION DEPLOYMENT CONFIRMATION")
    print("This will apply the availability user_id migration to production")
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Deployment cancelled")
        return 0
    
    # Run migration
    if not run_production_migration():
        return 1
    
    # Verify migration
    if not verify_production_migration():
        print("⚠️  Migration ran but verification failed")
        print("   Please check the production availability page manually")
        return 1
    
    print("\n🎉 Production migration deployment completed!")
    print("   The availability issue should now be resolved")
    print("   Test at: https://rally.up.railway.app/mobile/availability")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 