#!/usr/bin/env python3
"""
Apply Migration to Staging
==========================

This script applies the latest Alembic migration to the staging environment.
It handles the Railway database connection properly.
"""

import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_staging_database_url():
    """Get the staging database URL from environment variables"""
    # Check for Railway staging environment variables
    staging_db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
    
    if not staging_db_url:
        logger.error("No staging database URL found. Please set DATABASE_PUBLIC_URL or DATABASE_URL")
        return None
    
    # Handle Railway's postgres:// URLs
    if staging_db_url.startswith("postgres://"):
        staging_db_url = staging_db_url.replace("postgres://", "postgresql://", 1)
    
    return staging_db_url

def check_migration_status():
    """Check current migration status"""
    print("📊 Checking current migration status...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'alembic', 'current'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            current_revision = result.stdout.strip().split('\n')[-1]
            print(f"✅ Current migration: {current_revision}")
            return current_revision
        else:
            print(f"❌ Error checking migration status: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("⏰ Migration status check timed out")
        return None
    except Exception as e:
        print(f"❌ Error checking migration status: {e}")
        return None

def apply_migration():
    """Apply the migration to staging"""
    print("🔄 Applying migration to staging...")
    
    try:
        # Set environment to use Railway database
        env = os.environ.copy()
        
        # Force use of public URL for external connections
        staging_url = get_staging_database_url()
        if staging_url:
            env['DATABASE_URL'] = staging_url
            print(f"🔗 Using staging database: {staging_url.split('@')[1].split('/')[0] if '@' in staging_url else 'unknown host'}")
        
        result = subprocess.run([
            sys.executable, '-m', 'alembic', 'upgrade', 'head'
        ], capture_output=True, text=True, timeout=120, env=env)
        
        if result.returncode == 0:
            print("✅ Migration applied successfully!")
            print(result.stdout)
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Migration timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        return False

def verify_constraint_exists():
    """Verify the unique constraint was applied"""
    print("🔍 Verifying constraint was applied...")
    
    try:
        # Create a simple verification script
        verification_script = """
import sys
import os
sys.path.append('.')
from database_utils import execute_query_one

try:
    result = execute_query_one('''
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'user_player_associations' 
        AND constraint_type = 'UNIQUE'
        AND constraint_name = 'unique_tenniscores_player_id'
    ''')
    
    if result:
        print("✅ Constraint exists:", result['constraint_name'])
        exit(0)
    else:
        print("❌ Constraint not found")
        exit(1)
except Exception as e:
    print(f"❌ Error checking constraint: {e}")
    exit(1)
"""
        
        # Write verification script to temp file
        with open('/tmp/verify_constraint.py', 'w') as f:
            f.write(verification_script)
        
        # Set environment for staging database
        env = os.environ.copy()
        staging_url = get_staging_database_url()
        if staging_url:
            env['DATABASE_URL'] = staging_url
        
        result = subprocess.run([
            sys.executable, '/tmp/verify_constraint.py'
        ], capture_output=True, text=True, timeout=30, env=env)
        
        if result.returncode == 0:
            print(result.stdout.strip())
            return True
        else:
            print(result.stdout.strip())
            print(result.stderr.strip())
            return False
            
    except Exception as e:
        print(f"❌ Error verifying constraint: {e}")
        return False
    finally:
        # Clean up temp file
        try:
            os.remove('/tmp/verify_constraint.py')
        except:
            pass

def main():
    """Main function"""
    print("🚀 Applying Registration Fix Migration to Staging")
    print("=" * 60)
    
    # Check if we have the necessary environment variables
    if not get_staging_database_url():
        print("❌ Cannot proceed without staging database URL")
        return 1
    
    # Check current migration status
    current_revision = check_migration_status()
    if current_revision and 'add_unique_player_constraint' in current_revision:
        print("ℹ️  Migration already applied!")
        # Still verify the constraint exists
        if verify_constraint_exists():
            print("✅ All checks passed - staging is ready!")
            return 0
        else:
            print("⚠️  Migration applied but constraint verification failed")
            return 1
    
    # Apply the migration
    if not apply_migration():
        print("❌ Failed to apply migration")
        return 1
    
    # Verify the constraint was created
    if not verify_constraint_exists():
        print("⚠️  Migration completed but constraint verification failed")
        return 1
    
    print("\n🎉 Registration fix successfully applied to staging!")
    print("=" * 60)
    print("✅ Unique constraint added: unique_tenniscores_player_id")
    print("✅ Database integrity protection active")
    print("✅ Registration transaction fix deployed")
    print()
    print("📝 Next steps:")
    print("   1. Test registration functionality on staging")
    print("   2. Verify duplicate prevention works")
    print("   3. Deploy to production when ready")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 