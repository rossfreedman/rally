#!/usr/bin/env python3
"""
Generate Alembic Sync Migration
Creates migration files to sync Railway and local databases
"""

import os
import sys
import subprocess
import tempfile
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sync_migrations():
    """Generate Alembic migrations to sync Railway with local"""
    
    print("🔄 GENERATING SYNC MIGRATIONS")
    print("=" * 60)
    
    # Step 1: Generate migration for Railway → Local sync
    print("\n📝 Step 1: Generating migration to sync Railway to match Local schema...")
    
    try:
        # Set environment to use Railway database
        os.environ['SYNC_RAILWAY'] = 'true'
        
        # Generate autogenerate migration
        result = subprocess.run([
            sys.executable, "-m", "alembic", "revision", "--autogenerate",
            "--message", f"sync_railway_to_local_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration generated successfully!")
            print("Migration output:")
            print(result.stdout)
            
            # Extract migration file name from output
            lines = result.stdout.strip().split('\n')
            migration_file = None
            for line in lines:
                if 'Generating' in line and '.py' in line:
                    migration_file = line.split()[-1]
                    break
            
            if migration_file:
                print(f"\n📄 Migration file created: {migration_file}")
                
                # Read and display the migration content
                try:
                    with open(migration_file, 'r') as f:
                        content = f.read()
                    
                    print(f"\n📋 Migration Content Preview:")
                    print("-" * 50)
                    # Show just the upgrade function
                    lines = content.split('\n')
                    in_upgrade = False
                    preview_lines = []
                    for line in lines:
                        if 'def upgrade():' in line:
                            in_upgrade = True
                        elif 'def downgrade():' in line:
                            break
                        
                        if in_upgrade:
                            preview_lines.append(line)
                    
                    # Show first 30 lines of upgrade function
                    for line in preview_lines[:30]:
                        print(line)
                    
                    if len(preview_lines) > 30:
                        print("... (truncated)")
                    
                except Exception as e:
                    logger.warning(f"Could not preview migration content: {e}")
            
        else:
            print("❌ Migration generation failed!")
            print("Error output:")
            print(result.stderr)
            return False
            
    except Exception as e:
        logger.error(f"❌ Error generating migration: {e}")
        return False
    finally:
        os.environ.pop('SYNC_RAILWAY', None)
    
    print("\n" + "=" * 60)
    print("✅ Migration generation complete!")
    print("\n🔧 Next Steps:")
    print("1. Review the generated migration file")
    print("2. Test the migration on a backup/staging environment first")
    print("3. Run 'alembic upgrade head' with SYNC_RAILWAY=true to apply to Railway")
    print("4. Or run 'alembic upgrade head' normally to apply to local")
    
    return True

def show_current_status():
    """Show current migration status of both databases"""
    print("\n📊 CURRENT MIGRATION STATUS")
    print("-" * 40)
    
    # Check local
    try:
        os.environ.pop('SYNC_RAILWAY', None)
        result = subprocess.run([
            sys.executable, "-m", "alembic", "current"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Local: {result.stdout.strip()}")
        else:
            print(f"Local: Error - {result.stderr.strip()}")
    except Exception as e:
        print(f"Local: Error - {e}")
    
    # Check Railway
    try:
        os.environ['SYNC_RAILWAY'] = 'true'
        result = subprocess.run([
            sys.executable, "-m", "alembic", "current"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Railway: {result.stdout.strip()}")
        else:
            print(f"Railway: Error - {result.stderr.strip()}")
    except Exception as e:
        print(f"Railway: Error - {e}")
    finally:
        os.environ.pop('SYNC_RAILWAY', None)

def check_pending_migrations():
    """Check if there are pending migrations"""
    print("\n🔍 CHECKING FOR PENDING MIGRATIONS")
    print("-" * 40)
    
    try:
        # Check Railway for pending migrations
        os.environ['SYNC_RAILWAY'] = 'true'
        result = subprocess.run([
            sys.executable, "-m", "alembic", "heads"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Available heads: {result.stdout.strip()}")
        
        # Show history
        result = subprocess.run([
            sys.executable, "-m", "alembic", "history", "--verbose"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            print("Recent migration history:")
            for line in lines[:10]:  # Show last 10 lines
                print(f"  {line}")
        
    except Exception as e:
        logger.error(f"Error checking migrations: {e}")
    finally:
        os.environ.pop('SYNC_RAILWAY', None)

def main():
    """Main function"""
    show_current_status()
    check_pending_migrations()
    
    print("\n" + "=" * 60)
    response = input("🤔 Do you want to generate a sync migration? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        success = generate_sync_migrations()
        return 0 if success else 1
    else:
        print("👍 No migration generated. Run again when ready.")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 