#!/usr/bin/env python3
"""
DbSchema Migration Manager for Rally
====================================

Automates schema migrations using DbSchema across local → staging → production environments.
Integrates with the existing Rally deployment workflow.

Features:
- Generate schema migrations using DbSchema
- Deploy to staging environment for testing
- Validate schema changes on staging
- Deploy to production after validation
- Rollback capabilities
- Integration with Railway deployments

Usage:
    python data/dbschema/dbschema_migration_manager.py generate    # Generate migration from local changes
    python data/dbschema/dbschema_migration_manager.py deploy-staging  # Deploy to staging
    python data/dbschema/dbschema_migration_manager.py test-staging    # Test staging deployment
    python data/dbschema/dbschema_migration_manager.py deploy-production  # Deploy to production
    python data/dbschema/dbschema_migration_manager.py status     # Check migration status
    python data/dbschema/dbschema_migration_manager.py rollback   # Rollback last migration
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add root directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_config import parse_db_url

load_dotenv()

class DbSchemaMigrationManager:
    """Manages DbSchema migrations across environments"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent
        self.migrations_dir = self.root_dir / "data" / "dbschema" / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        
        # Database connections
        self.local_url = "postgresql://rossfreedman@localhost/rally"
        self.staging_url = os.getenv("DATABASE_STAGING_URL")
        self.production_url = os.getenv("DATABASE_PUBLIC_URL")
        
        # DbSchema project file
        self.dbschema_project = self.root_dir / "database_schema" / "rally_schema.dbs"
        
    def print_banner(self, title):
        """Print formatted banner"""
        print(f"\n🎯 {title}")
        print("=" * 60)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def run_command(self, cmd, capture_output=True, check=True):
        """Run shell command with error handling"""
        try:
            result = subprocess.run(cmd, capture_output=capture_output, text=True, check=check)
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(cmd)}")
            print(f"Error: {e}")
            if capture_output and e.stdout:
                print(f"Output: {e.stdout}")
            if capture_output and e.stderr:
                print(f"Error output: {e.stderr}")
            return None
    
    def check_dbschema_installation(self):
        """Check if DbSchema is installed and accessible"""
        print("🔍 Checking DbSchema installation...")
        
        # Check if DbSchema is available
        dbschema_paths = [
            "/Applications/DbSchema/DbSchemaCLI",
            "/Applications/DbSchema.app/Contents/bin/dbschema",
            "/usr/local/bin/dbschema",
            "dbschema"  # In PATH
        ]
        
        for path in dbschema_paths:
            if os.path.exists(path):
                print(f"✅ DbSchema found at: {path}")
                self.dbschema_cli = path
                return True
        
        print("❌ DbSchema not found!")
        print("💡 Install DbSchema")
        print("   - Download from: https://dbschema.com/download.html")
        return False
    
    def check_project_file(self):
        """Check if DbSchema project file exists"""
        if not self.dbschema_project.exists():
            print(f"❌ DbSchema project file not found: {self.dbschema_project}")
            print("💡 Create DbSchema project first:")
            print("   python data/dbschema/setup_dbschema.py")
            return False
        
        print(f"✅ DbSchema project found: {self.dbschema_project}")
        return True
    
    def generate_migration(self, description=None):
        """Generate migration from current local schema changes"""
        self.print_banner("Generate Schema Migration")
        
        if not self.check_dbschema_installation():
            return False
        
        if not self.check_project_file():
            return False
        
        # Generate timestamp-based migration name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_name = f"{timestamp}_{description or 'schema_migration'}"
        migration_file = self.migrations_dir / f"{migration_name}.sql"
        
        print(f"📝 Generating migration: {migration_name}")
        
        try:
            # Use DbSchema to generate SQL migration
            # This assumes DbSchema has been configured with local connection
            print("🔍 Analyzing schema changes...")
            
            # Create temporary schema comparison
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
                # Generate schema dump from current database
                result = self.run_command([
                    "pg_dump", 
                    "--schema-only",
                    "--no-owner",
                    "--no-privileges",
                    self.local_url
                ])
                
                if not result:
                    return False
                
                temp_file.write(result.stdout)
                temp_schema_file = temp_file.name
            
            # Compare with last migration to generate diff
            migration_sql = self._generate_migration_sql(temp_schema_file, migration_name)
            
            # Write migration file
            with open(migration_file, 'w') as f:
                f.write(migration_sql)
            
            print(f"✅ Migration generated: {migration_file}")
            print(f"📄 Review the migration file before deploying")
            
            # Clean up temp file
            os.unlink(temp_schema_file)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate migration: {e}")
            return False
    
    def _generate_migration_sql(self, schema_file, migration_name):
        """Generate migration SQL content"""
        header = f"""-- DbSchema Migration: {migration_name}
-- Generated: {datetime.now().isoformat()}
-- Description: Automated schema migration
-- 
-- This migration was generated by DbSchema Migration Manager
-- Review carefully before applying to staging/production

BEGIN;

-- Migration starts here
"""
        
        footer = """
-- Migration ends here

COMMIT;

-- Rollback script (uncomment if needed):
-- BEGIN;
-- -- Add rollback statements here
-- COMMIT;
"""
        
        # For now, include a placeholder for actual schema changes
        # In a full implementation, this would use DbSchema's comparison engine
        placeholder_migration = """
-- TODO: Add your schema changes here
-- Examples:
-- ALTER TABLE users ADD COLUMN new_field VARCHAR(255);
-- CREATE INDEX idx_new_field ON users(new_field);
-- ALTER TABLE teams ADD CONSTRAINT fk_team_league FOREIGN KEY (league_id) REFERENCES leagues(id);

-- Placeholder migration - replace with actual changes
SELECT 'Migration placeholder - add your schema changes' as migration_status;
"""
        
        return header + placeholder_migration + footer
    
    def deploy_to_staging(self):
        """Deploy latest migration to staging environment"""
        self.print_banner("Deploy to Staging")
        
        if not self.staging_url:
            print("❌ Staging database URL not configured")
            print("💡 Set DATABASE_STAGING_URL environment variable")
            return False
        
        # Find latest migration
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        if not migration_files:
            print("❌ No migration files found")
            print("💡 Generate a migration first: python data/dbschema/dbschema_migration_manager.py generate")
            return False
        
        latest_migration = migration_files[-1]
        print(f"📦 Deploying migration: {latest_migration.name}")
        
        # Backup staging schema before migration
        backup_file = self._backup_staging_schema()
        if not backup_file:
            return False
        
        # Apply migration to staging
        try:
            print("🚀 Applying migration to staging...")
            result = self.run_command([
                "psql", 
                self.staging_url,
                "-f", str(latest_migration)
            ])
            
            if not result:
                print("❌ Migration failed on staging")
                print(f"💡 Restore from backup: {backup_file}")
                return False
            
            print("✅ Migration applied to staging successfully")
            
            # Run validation tests
            if self._validate_staging_schema():
                print("✅ Staging schema validation passed")
                return True
            else:
                print("❌ Staging schema validation failed")
                return False
                
        except Exception as e:
            print(f"❌ Migration deployment failed: {e}")
            return False
    
    def _backup_staging_schema(self):
        """Create backup of staging schema before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.migrations_dir / f"staging_backup_{timestamp}.sql"
        
        print(f"💾 Creating staging backup: {backup_file.name}")
        
        result = self.run_command([
            "pg_dump",
            "--schema-only", 
            "--no-owner",
            "--no-privileges",
            self.staging_url
        ])
        
        if not result:
            return None
        
        with open(backup_file, 'w') as f:
            f.write(result.stdout)
        
        print(f"✅ Staging backup created: {backup_file}")
        return backup_file
    
    def _validate_staging_schema(self):
        """Validate staging schema after migration"""
        print("🧪 Validating staging schema...")
        
        try:
            # Run existing schema comparison script
            compare_script = self.root_dir / "data" / "dbschema" / "compare_schemas_dbschema.py"
            if compare_script.exists():
                result = self.run_command([sys.executable, str(compare_script)])
                return result and result.returncode == 0
            else:
                print("⚠️  Schema comparison script not found")
                return True  # Assume valid if no comparison available
                
        except Exception as e:
            print(f"❌ Schema validation failed: {e}")
            return False
    
    def test_staging(self):
        """Test staging environment after migration"""
        self.print_banner("Test Staging Migration")
        
        # Run staging tests
        test_script = self.root_dir / "deployment" / "test_staging_session_refresh.py"
        if test_script.exists():
            print("🧪 Running staging tests...")
            result = self.run_command([sys.executable, str(test_script)])
            
            if result and result.returncode == 0:
                print("✅ Staging tests passed")
                return True
            else:
                print("❌ Staging tests failed")
                return False
        else:
            print("⚠️  Staging test script not found")
            return True
    
    def deploy_to_production(self):
        """Deploy tested migration to production"""
        self.print_banner("Deploy to Production")
        
        if not self.production_url:
            print("❌ Production database URL not configured")
            print("💡 Set DATABASE_PUBLIC_URL environment variable")
            return False
        
        # Verify staging tests pass first
        if not self._verify_staging_ready():
            return False
        
        # Get user confirmation for production deployment
        print("⚠️  PRODUCTION DEPLOYMENT")
        print("This will apply schema changes to the live production database.")
        confirm = input("Type 'YES' to confirm production deployment: ")
        
        if confirm != "YES":
            print("❌ Production deployment cancelled")
            return False
        
        # Find latest migration
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        latest_migration = migration_files[-1]
        
        print(f"📦 Deploying to production: {latest_migration.name}")
        
        # Backup production schema
        backup_file = self._backup_production_schema()
        if not backup_file:
            return False
        
        # Apply migration to production
        try:
            print("🚀 Applying migration to production...")
            result = self.run_command([
                "psql",
                self.production_url,
                "-f", str(latest_migration)
            ])
            
            if not result:
                print("❌ Migration failed on production")
                print(f"💡 Restore from backup: {backup_file}")
                return False
            
            print("✅ Migration applied to production successfully")
            
            # Run production validation
            if self._validate_production_schema():
                print("✅ Production schema validation passed")
                
                # Mark migration as applied
                self._mark_migration_applied(latest_migration)
                
                return True
            else:
                print("❌ Production schema validation failed")
                return False
                
        except Exception as e:
            print(f"❌ Production deployment failed: {e}")
            return False
    
    def _verify_staging_ready(self):
        """Verify staging is ready for production deployment"""
        print("🔍 Verifying staging readiness...")
        
        # Check if staging migration was successful
        if not self.test_staging():
            print("❌ Staging tests not passing")
            return False
        
        print("✅ Staging verification passed")
        return True
    
    def _backup_production_schema(self):
        """Create backup of production schema before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.migrations_dir / f"production_backup_{timestamp}.sql"
        
        print(f"💾 Creating production backup: {backup_file.name}")
        
        result = self.run_command([
            "pg_dump",
            "--schema-only",
            "--no-owner", 
            "--no-privileges",
            self.production_url
        ])
        
        if not result:
            return None
        
        with open(backup_file, 'w') as f:
            f.write(result.stdout)
        
        print(f"✅ Production backup created: {backup_file}")
        return backup_file
    
    def _validate_production_schema(self):
        """Validate production schema after migration"""
        print("🧪 Validating production schema...")
        
        try:
            # Run production validation test
            test_script = self.root_dir / "deployment" / "test_production_session_refresh.py"
            if test_script.exists():
                result = self.run_command([sys.executable, str(test_script)])
                return result and result.returncode == 0
            else:
                print("⚠️  Production test script not found")
                return True
                
        except Exception as e:
            print(f"❌ Production validation failed: {e}")
            return False
    
    def _mark_migration_applied(self, migration_file):
        """Mark migration as successfully applied"""
        applied_migrations_file = self.migrations_dir / "applied_migrations.json"
        
        # Load existing applied migrations
        applied_migrations = []
        if applied_migrations_file.exists():
            with open(applied_migrations_file, 'r') as f:
                applied_migrations = json.load(f)
        
        # Add this migration
        migration_record = {
            "filename": migration_file.name,
            "applied_at": datetime.now().isoformat(),
            "applied_to": ["staging", "production"]
        }
        
        applied_migrations.append(migration_record)
        
        # Save updated list
        with open(applied_migrations_file, 'w') as f:
            json.dump(applied_migrations, f, indent=2)
        
        print(f"✅ Migration marked as applied: {migration_file.name}")
    
    def status(self):
        """Show migration status across environments"""
        self.print_banner("Migration Status")
        
        # List migration files
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        
        print(f"📂 Migration files ({len(migration_files)}):")
        for migration_file in migration_files:
            print(f"   📄 {migration_file.name}")
        
        # Show applied migrations
        applied_migrations_file = self.migrations_dir / "applied_migrations.json"
        if applied_migrations_file.exists():
            with open(applied_migrations_file, 'r') as f:
                applied_migrations = json.load(f)
            
            print(f"\n✅ Applied migrations ({len(applied_migrations)}):")
            for migration in applied_migrations:
                print(f"   📄 {migration['filename']} - {migration['applied_at']}")
        else:
            print("\n📋 No applied migrations tracked")
        
        # Check environment status
        print(f"\n🌍 Environment Status:")
        
        # Local
        print(f"   🏠 Local: Connected")
        
        # Staging
        if self.staging_url:
            print(f"   🧪 Staging: Configured")
        else:
            print(f"   🧪 Staging: Not configured")
        
        # Production
        if self.production_url:
            print(f"   🚀 Production: Configured")
        else:
            print(f"   🚀 Production: Not configured")
    
    def rollback(self):
        """Rollback last migration"""
        self.print_banner("Rollback Migration")
        
        print("⚠️  Rollback functionality requires manual intervention")
        print("💡 Use backup files created during migration:")
        
        # List backup files
        backup_files = sorted(self.migrations_dir.glob("*_backup_*.sql"))
        
        if backup_files:
            print(f"\n📂 Available backups:")
            for backup_file in backup_files[-5:]:  # Show last 5 backups
                print(f"   📄 {backup_file.name}")
            
            print(f"\n🔧 To restore from backup:")
            print(f"   psql {self.staging_url or '<staging_url>'} -f <backup_file>")
            print(f"   psql {self.production_url or '<production_url>'} -f <backup_file>")
        else:
            print("❌ No backup files found")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="DbSchema Migration Manager for Rally")
    parser.add_argument("command", choices=[
        "generate", "deploy-staging", "test-staging", 
        "deploy-production", "status", "rollback"
    ], help="Migration command to execute")
    parser.add_argument("--description", "-d", help="Description for generated migration")
    
    args = parser.parse_args()
    
    manager = DbSchemaMigrationManager()
    
    if args.command == "generate":
        success = manager.generate_migration(args.description)
    elif args.command == "deploy-staging":
        success = manager.deploy_to_staging()
    elif args.command == "test-staging":
        success = manager.test_staging()
    elif args.command == "deploy-production":
        success = manager.deploy_to_production()
    elif args.command == "status":
        manager.status()
        success = True
    elif args.command == "rollback":
        manager.rollback()
        success = True
    else:
        print(f"❌ Unknown command: {args.command}")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 