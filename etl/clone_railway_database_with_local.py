#!/usr/bin/env python3
"""
Clone Railway Database with Local - ETL Tool
Completely replaces Railway database with exact copy of local database
Located in: etl/ directory for database management operations
"""

import os
import sys
import subprocess
from datetime import datetime
import logging

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RailwayDatabaseCloner:
    def __init__(self):
        self.local_url = "postgresql://postgres:postgres@localhost:5432/rally"
        self.railway_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        self.dump_file = None
        
    def completely_clear_railway(self):
        """Completely clear Railway database - drop all tables"""
        logger.info("🗑️  Completely clearing Railway database...")
        
        try:
            # Get all table names
            result = subprocess.run([
                'psql', self.railway_url, '-t', '-c',
                """
                SELECT 'DROP TABLE IF EXISTS "' || tablename || '" CASCADE;'
                FROM pg_tables 
                WHERE schemaname = 'public';
                """
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to get table list: {result.stderr}")
                return False
            
            drop_commands = result.stdout.strip().split('\n')
            drop_commands = [cmd.strip() for cmd in drop_commands if cmd.strip()]
            
            logger.info(f"   Found {len(drop_commands)} tables to drop")
            
            # Execute drop commands
            for drop_cmd in drop_commands:
                if drop_cmd:
                    logger.info(f"   Executing: {drop_cmd}")
                    subprocess.run([
                        'psql', self.railway_url, '-c', drop_cmd
                    ], capture_output=True, text=True)
            
            # Also drop sequences
            seq_result = subprocess.run([
                'psql', self.railway_url, '-t', '-c',
                """
                SELECT 'DROP SEQUENCE IF EXISTS "' || sequencename || '" CASCADE;'
                FROM pg_sequences 
                WHERE schemaname = 'public';
                """
            ], capture_output=True, text=True)
            
            if seq_result.returncode == 0:
                seq_commands = seq_result.stdout.strip().split('\n')
                seq_commands = [cmd.strip() for cmd in seq_commands if cmd.strip()]
                
                for seq_cmd in seq_commands:
                    if seq_cmd:
                        logger.info(f"   Executing: {seq_cmd}")
                        subprocess.run([
                            'psql', self.railway_url, '-c', seq_cmd
                        ], capture_output=True, text=True)
            
            logger.info("✅ Railway database completely cleared!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to clear Railway database: {e}")
            return False
    
    def create_fresh_local_dump(self):
        """Create a fresh dump of local database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.dump_file = f"local_database_fresh_dump_{timestamp}.sql"
        
        logger.info("📦 Creating fresh dump of local database...")
        
        try:
            # Use PostgreSQL 16 path
            env = os.environ.copy()
            env['PATH'] = '/opt/homebrew/opt/postgresql@16/bin:' + env.get('PATH', '')
            
            result = subprocess.run([
                'pg_dump',
                self.local_url,
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                '--disable-triggers',
                '-f', self.dump_file
            ], capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                logger.info(f"✅ Fresh local dump created: {self.dump_file}")
                size = os.path.getsize(self.dump_file)
                logger.info(f"   Dump size: {size:,} bytes")
                return True
            else:
                logger.error(f"❌ Fresh dump failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Fresh dump error: {e}")
            return False
    
    def restore_to_empty_railway(self):
        """Restore local dump to now-empty Railway database"""
        logger.info("🔄 Restoring local dump to empty Railway database...")
        
        if not self.dump_file:
            logger.error("❌ No dump file available")
            return False
        
        try:
            # Use PostgreSQL 16 path
            env = os.environ.copy()
            env['PATH'] = '/opt/homebrew/opt/postgresql@16/bin:' + env.get('PATH', '')
            
            result = subprocess.run([
                'psql',
                self.railway_url,
                '-f', self.dump_file,
                '--quiet'
            ], capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                logger.info("✅ Database restored to Railway successfully!")
                return True
            else:
                logger.error(f"❌ Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Restore error: {e}")
            return False
    
    def verify_exact_match(self):
        """Verify Railway now exactly matches local"""
        logger.info("🔍 Verifying exact match...")
        
        try:
            # Run comparison script from project root
            result = subprocess.run([
                sys.executable, "../compare_databases.py"
            ], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            if result.returncode == 0:
                logger.info("✅ PERFECT! Databases are now identical!")
                return True
            else:
                logger.warning("⚠️  Some differences still remain:")
                print(result.stdout)
                return False
                
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.dump_file and os.path.exists(self.dump_file):
            try:
                os.remove(self.dump_file)
                logger.info(f"🧹 Cleaned up: {self.dump_file}")
            except Exception as e:
                logger.warning(f"Could not clean up {self.dump_file}: {e}")
    
    def run_clone(self):
        """Run the complete cloning process"""
        logger.info("🔧 CLONING LOCAL DATABASE TO RAILWAY - Complete Replacement")
        logger.info("=" * 60)
        
        steps = [
            ("Completely clearing Railway database", self.completely_clear_railway),
            ("Creating fresh local dump", self.create_fresh_local_dump),
            ("Restoring to empty Railway", self.restore_to_empty_railway),
            ("Verifying exact match", self.verify_exact_match)
        ]
        
        success = True
        
        for step_name, step_func in steps:
            logger.info(f"\n📋 Step: {step_name}")
            if not step_func():
                logger.error(f"❌ FAILED: {step_name}")
                success = False
                break
            else:
                logger.info(f"✅ SUCCESS: {step_name}")
        
        if success:
            logger.info("\n" + "=" * 60)
            logger.info("🎉 RAILWAY DATABASE PERFECTLY CLONED!")
            logger.info("✅ Railway now exactly matches your local database")
            self.cleanup()
        else:
            logger.error("\n🛑 Clone process failed")
        
        return success

def main():
    print("🏓 RALLY ETL: Clone Railway Database with Local")
    print("=" * 50)
    print("This ETL tool completely replaces Railway database with local copy.")
    print("⚠️  WARNING: This will COMPLETELY REPLACE Railway database!")
    print()
    print("📋 Process:")
    print("1. Drop all Railway tables/sequences")
    print("2. Create fresh local database dump")
    print("3. Restore local dump to Railway")
    print("4. Verify databases are identical")
    print()
    
    response = input("🤔 Proceed with complete Railway replacement? (type 'YES'): ").strip()
    
    if response != 'YES':
        print("👍 Clone cancelled.")
        return 0
    
    cloner = RailwayDatabaseCloner()
    success = cloner.run_clone()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 