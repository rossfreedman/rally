#!/usr/bin/env python3
"""
Schema Management Workflow
Complete toolkit for keeping SQLAlchemy models and database schema in sync
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import argparse
import logging
from datetime import datetime
from schema_sync_manager import SchemaSyncManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchemaWorkflow:
    """Automated workflow for schema management"""
    
    def __init__(self):
        self.sync_manager = SchemaSyncManager()
    
    def run_command(self, cmd: list) -> tuple:
        """Run a shell command and return output"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1
    
    def status_check(self) -> dict:
        """Comprehensive status check"""
        logger.info("🔍 Running comprehensive schema status check...")
        
        # Check Alembic status
        alembic_status = self.sync_manager.check_alembic_status()
        
        # Check schema differences
        differences = self.sync_manager.full_schema_comparison()
        
        # Check if database is up to date with migrations
        stdout, stderr, returncode = self.run_command(["alembic", "check"])
        migrations_current = returncode == 0
        
        return {
            'alembic_initialized': alembic_status['status'] == 'initialized',
            'current_revision': alembic_status.get('current_revision'),
            'migrations_current': migrations_current,
            'schema_differences': differences,
            'timestamp': datetime.now().isoformat()
        }
    
    def create_migration(self, message: str = None) -> bool:
        """Create a new migration for schema changes"""
        if not message:
            message = f"schema_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🔄 Creating migration: {message}")
        
        # Generate migration
        cmd = ["alembic", "revision", "--autogenerate", "-m", message]
        stdout, stderr, returncode = self.run_command(cmd)
        
        if returncode != 0:
            logger.error(f"Failed to create migration: {stderr}")
            return False
        
        logger.info("✅ Migration created successfully")
        logger.info("📝 Please review the generated migration file before applying")
        return True
    
    def apply_migrations(self) -> bool:
        """Apply pending migrations"""
        logger.info("🚀 Applying pending migrations...")
        
        # Check what migrations will be applied
        cmd = ["alembic", "upgrade", "head", "--sql"]
        stdout, stderr, returncode = self.run_command(cmd)
        
        if stdout.strip():
            logger.info("📋 Migrations to apply:")
            print(stdout)
            
            response = input("Continue with migration? (y/N): ")
            if response.lower() != 'y':
                logger.info("Migration cancelled by user")
                return False
        
        # Apply migrations
        cmd = ["alembic", "upgrade", "head"]
        stdout, stderr, returncode = self.run_command(cmd)
        
        if returncode != 0:
            logger.error(f"Migration failed: {stderr}")
            return False
        
        logger.info("✅ Migrations applied successfully")
        return True
    
    def sync_schema(self, auto_apply: bool = False) -> bool:
        """Complete schema synchronization workflow"""
        logger.info("🔄 Starting schema synchronization workflow...")
        
        # Step 1: Check current status
        status = self.status_check()
        
        if not status['alembic_initialized']:
            logger.error("❌ Alembic not initialized. Run 'python scripts/schema_sync_manager.py --init-baseline' first")
            return False
        
        # Step 2: Check for differences
        differences = status['schema_differences']
        has_differences = (
            differences['summary']['tables_missing_in_db'] > 0 or
            differences['summary']['tables_missing_in_models'] > 0 or
            bool(differences['column_differences'])
        )
        
        if not has_differences:
            logger.info("✅ Schema is already in sync!")
            return True
        
        # Step 3: Create migration for differences
        logger.info("📝 Schema differences detected, creating migration...")
        if not self.create_migration("sync_schema_differences"):
            return False
        
        # Step 4: Apply migration
        if auto_apply:
            return self.apply_migrations()
        else:
            logger.info("💡 Migration created. Review it and run 'alembic upgrade head' to apply")
            return True
    
    def pre_commit_check(self) -> bool:
        """Pre-commit hook to check schema consistency"""
        logger.info("🔍 Running pre-commit schema check...")
        
        status = self.status_check()
        
        # Check if migrations are up to date
        if not status['migrations_current']:
            logger.error("❌ Database is not up to date with migrations!")
            logger.error("Run 'alembic upgrade head' to apply pending migrations")
            return False
        
        # Check for uncommitted schema changes
        differences = status['schema_differences']
        has_model_changes = (
            differences['summary']['tables_missing_in_db'] > 0 or
            bool(differences['column_differences'])
        )
        
        if has_model_changes:
            logger.error("❌ Model changes detected that aren't in migrations!")
            logger.error("Run 'python scripts/schema_workflow.py --create-migration' to create a migration")
            return False
        
        logger.info("✅ Schema check passed")
        return True
    
    def validate_models(self) -> bool:
        """Validate that all models can be imported and are consistent"""
        logger.info("🔍 Validating SQLAlchemy models...")
        
        try:
            from app.models.database_models import Base
            logger.info(f"✅ Successfully imported {len(Base.metadata.tables)} model tables")
            
            # Check for common issues
            for table_name, table in Base.metadata.tables.items():
                if not table.primary_key.columns:
                    logger.warning(f"⚠️  Table {table_name} has no primary key")
                
                for column in table.columns:
                    if column.foreign_keys and not any(fk.constraint for fk in column.foreign_keys):
                        logger.warning(f"⚠️  Column {table_name}.{column.name} has invalid foreign key")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Model validation failed: {e}")
            return False
    
    def backup_database(self) -> str:
        """Create a database backup before schema changes"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"backup_before_migration_{timestamp}.sql"
        
        logger.info(f"📦 Creating database backup: {backup_file}")
        
        # Get database URL from config
        from database_config import get_db_url
        db_url = get_db_url()
        
        cmd = ["pg_dump", db_url, "-f", backup_file]
        stdout, stderr, returncode = self.run_command(cmd)
        
        if returncode != 0:
            logger.error(f"❌ Backup failed: {stderr}")
            return None
        
        logger.info(f"✅ Backup created: {backup_file}")
        return backup_file

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='Schema Management Workflow')
    parser.add_argument('--status', action='store_true', help='Show comprehensive status')
    parser.add_argument('--create-migration', metavar='MESSAGE', help='Create new migration')
    parser.add_argument('--apply-migrations', action='store_true', help='Apply pending migrations')
    parser.add_argument('--sync', action='store_true', help='Complete sync workflow')
    parser.add_argument('--sync-auto', action='store_true', help='Complete sync workflow with auto-apply')
    parser.add_argument('--pre-commit', action='store_true', help='Pre-commit hook check')
    parser.add_argument('--validate', action='store_true', help='Validate models')
    parser.add_argument('--backup', action='store_true', help='Create database backup')
    
    args = parser.parse_args()
    
    workflow = SchemaWorkflow()
    
    try:
        if args.status:
            status = workflow.status_check()
            
            print("\n🔍 SCHEMA STATUS REPORT")
            print("=" * 30)
            print(f"Alembic Initialized: {'✅' if status['alembic_initialized'] else '❌'}")
            print(f"Current Revision: {status['current_revision'] or 'None'}")
            print(f"Migrations Current: {'✅' if status['migrations_current'] else '❌'}")
            print(f"Tables in Sync: {status['schema_differences']['summary']['tables_in_sync']}")
            
            if status['schema_differences']['column_differences']:
                print(f"Column Differences: {len(status['schema_differences']['column_differences'])} tables")
            else:
                print("Column Differences: None ✅")
        
        elif args.create_migration:
            workflow.create_migration(args.create_migration)
        
        elif args.apply_migrations:
            workflow.apply_migrations()
        
        elif args.sync:
            workflow.sync_schema(auto_apply=False)
        
        elif args.sync_auto:
            workflow.sync_schema(auto_apply=True)
        
        elif args.pre_commit:
            success = workflow.pre_commit_check()
            sys.exit(0 if success else 1)
        
        elif args.validate:
            success = workflow.validate_models()
            sys.exit(0 if success else 1)
        
        elif args.backup:
            workflow.backup_database()
        
        else:
            # Default: show status
            status = workflow.status_check()
            report = workflow.sync_manager.generate_sync_report()
            print(report)
    
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 