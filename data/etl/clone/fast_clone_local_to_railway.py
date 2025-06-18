#!/usr/bin/env python3
"""
Fast Clone Local Database to Railway
Uses pg_dump/pg_restore for fastest complete database cloning
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

class FastDatabaseCloner:
    def __init__(self):
        self.local_url = "postgresql://postgres:postgres@localhost:5432/rally"
        self.railway_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        self.backup_file = None
        self.dump_file = None
        
    def backup_railway_database(self):
        """Create a backup of Railway database before making changes"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_file = f"railway_backup_before_fast_clone_{timestamp}.sql"
        
        logger.info("🔄 Creating backup of Railway database...")
        
        try:
            result = subprocess.run([
                'pg_dump', 
                self.railway_url,
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                '-f', self.backup_file
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Railway database backup created: {self.backup_file}")
                # Get file size for info
                size = os.path.getsize(self.backup_file)
                logger.info(f"   Backup size: {size:,} bytes")
                return True
            else:
                logger.error(f"❌ Backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backup error: {e}")
            return False
    
    def dump_local_database(self):
        """Create a dump of the local database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.dump_file = f"local_database_dump_{timestamp}.sql"
        
        logger.info("📦 Creating dump of local database...")
        
        try:
            result = subprocess.run([
                'pg_dump',
                self.local_url,
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                '--disable-triggers',
                '-f', self.dump_file
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Local database dump created: {self.dump_file}")
                # Get file size for info
                size = os.path.getsize(self.dump_file)
                logger.info(f"   Dump size: {size:,} bytes")
                return True
            else:
                logger.error(f"❌ Dump failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Dump error: {e}")
            return False
    
    def restore_to_railway(self):
        """Restore the local dump to Railway database"""
        logger.info("🔄 Restoring local dump to Railway database...")
        
        if not self.dump_file:
            logger.error("❌ No dump file available for restore")
            return False
        
        try:
            # Use psql to restore the dump
            result = subprocess.run([
                'psql',
                self.railway_url,
                '-f', self.dump_file,
                '--quiet'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Database restored to Railway successfully!")
                if result.stdout:
                    logger.info(f"   Restore output: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"❌ Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Restore error: {e}")
            return False
    
    def update_alembic_version(self):
        """Ensure Alembic version is correctly set"""
        logger.info("🔧 Updating Alembic version table...")
        
        try:
            # Get current local Alembic version
            local_result = subprocess.run([
                'psql', self.local_url, '-t', '-c',
                'SELECT version_num FROM alembic_version LIMIT 1;'
            ], capture_output=True, text=True)
            
            if local_result.returncode != 0:
                logger.warning("Could not get local Alembic version")
                return True  # Not critical
            
            local_version = local_result.stdout.strip()
            logger.info(f"   Local Alembic version: {local_version}")
            
            # Set the same version in Railway
            railway_result = subprocess.run([
                'psql', self.railway_url, '-c',
                f"UPDATE alembic_version SET version_num = '{local_version}';"
            ], capture_output=True, text=True)
            
            if railway_result.returncode == 0:
                logger.info("✅ Alembic version synchronized")
                return True
            else:
                logger.warning(f"Could not update Railway Alembic version: {railway_result.stderr}")
                return True  # Not critical
                
        except Exception as e:
            logger.warning(f"Alembic version update error: {e}")
            return True  # Not critical
    
    def verify_clone_success(self):
        """Verify that Railway database now matches local database"""
        logger.info("🔍 Verifying clone success...")
        
        try:
            # Run our comparison script
            result = subprocess.run([
                sys.executable, "compare_databases.py"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Clone verification: Databases are identical!")
                return True
            else:
                logger.warning("⚠️  Clone verification: Some differences remain")
                print(result.stdout)
                return False
                
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
    
    def cleanup_temp_files(self):
        """Clean up temporary dump files"""
        logger.info("🧹 Cleaning up temporary files...")
        
        files_to_remove = []
        if self.dump_file and os.path.exists(self.dump_file):
            files_to_remove.append(self.dump_file)
        
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
                logger.info(f"   Removed: {file_path}")
            except Exception as e:
                logger.warning(f"Could not remove {file_path}: {e}")
        
        if files_to_remove:
            logger.info("✅ Cleanup completed")
    
    def run_fast_clone(self):
        """Run the fast cloning process"""
        logger.info("🚀 Starting FAST database clone: Local → Railway")
        logger.info("=" * 60)
        
        steps = [
            ("Creating Railway backup", self.backup_railway_database),
            ("Dumping local database", self.dump_local_database),
            ("Restoring to Railway", self.restore_to_railway),
            ("Updating Alembic version", self.update_alembic_version),
            ("Verifying clone success", self.verify_clone_success)
        ]
        
        success = True
        
        for step_name, step_func in steps:
            logger.info(f"\n📋 Step: {step_name}")
            if not step_func():
                logger.error(f"❌ FAILED: {step_name}")
                logger.error("🛑 Clone process stopped due to error")
                success = False
                break
            else:
                logger.info(f"✅ SUCCESS: {step_name}")
        
        if success:
            logger.info("\n" + "=" * 60)
            logger.info("🎉 FAST DATABASE CLONE COMPLETED SUCCESSFULLY!")
            logger.info("✅ Railway database now perfectly matches local database")
            
            # Clean up temporary files
            self.cleanup_temp_files()
        
        if self.backup_file:
            logger.info(f"💾 Railway backup saved at: {self.backup_file}")
            if not success:
                logger.info("You can restore Railway database using:")
                logger.info(f"psql {self.railway_url} < {self.backup_file}")
        
        return success

def main():
    """Main function with user confirmation"""
    print("🏓 RALLY FAST DATABASE CLONE: Local → Railway")
    print("=" * 60)
    print("This uses pg_dump/pg_restore for fastest complete database cloning.")
    print("⚠️  WARNING: This will COMPLETELY REPLACE Railway database!")
    print()
    print("📋 Process Overview:")
    print("1. Backup Railway database")
    print("2. Dump local database to file")
    print("3. Restore dump to Railway database")
    print("4. Update Alembic version")
    print("5. Verify clone success")
    print("6. Clean up temporary files")
    print()
    print("⚡ This method is MUCH FASTER than row-by-row copying!")
    print()
    
    # Get user confirmation
    response = input("🤔 Do you want to proceed? (type 'YES' to confirm): ").strip()
    
    if response != 'YES':
        print("👍 Clone cancelled. No changes made.")
        return 0
    
    print("\n🚀 Starting fast clone process...")
    
    cloner = FastDatabaseCloner()
    success = cloner.run_fast_clone()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 