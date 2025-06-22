#!/usr/bin/env python3
"""
Multi-Environment Schema Synchronization
Keeps local and Railway databases in sync with schema changes
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

import psycopg2
from schema_sync_manager import SchemaSyncManager
from schema_workflow import SchemaWorkflow

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MultiEnvSchemaSync:
    """Manages schema synchronization across multiple environments"""

    def __init__(self):
        self.environments = {
            "local": {
                "name": "Local Development",
                "url": os.getenv(
                    "DATABASE_URL",
                    "postgresql://postgres:postgres@localhost:5432/rally",
                ),
                "alembic_env": {},
            },
            "railway": {
                "name": "Railway Production",
                "url": "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway",
                "alembic_env": {"SYNC_RAILWAY": "true"},
            },
        }

    def run_command_with_env(self, cmd: list, env_vars: dict = None) -> tuple:
        """Run a command with specific environment variables"""
        try:
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def test_connection(self, env_name: str) -> bool:
        """Test database connection for an environment"""
        logger.info(f"🔌 Testing {env_name} database connection...")

        url = self.environments[env_name]["url"]

        try:
            # Parse URL and connect
            parsed = urlparse(url)
            conn_params = {
                "dbname": parsed.path[1:],
                "user": parsed.username,
                "password": parsed.password,
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "sslmode": "require" if "railway" in parsed.hostname else "prefer",
                "connect_timeout": 10,
            }

            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            logger.info(f"✅ {env_name} connection successful")
            logger.info(f"   PostgreSQL: {version.split(',')[0]}")
            return True

        except Exception as e:
            logger.error(f"❌ {env_name} connection failed: {e}")
            return False

    def get_environment_status(self, env_name: str) -> dict:
        """Get comprehensive status for an environment"""
        logger.info(f"🔍 Checking {env_name} environment status...")

        env_vars = self.environments[env_name]["alembic_env"]

        # Get current migration revision
        stdout, stderr, returncode = self.run_command_with_env(
            ["alembic", "current"], env_vars
        )

        current_revision = None
        if returncode == 0:
            for line in stdout.split("\n"):
                if line.strip() and not line.startswith("INFO"):
                    current_revision = line.strip().split()[0]
                    break

        # Check if migrations are pending
        stdout, stderr, returncode = self.run_command_with_env(
            ["alembic", "check"], env_vars
        )
        migrations_current = returncode == 0

        # Get table count
        try:
            url = self.environments[env_name]["url"]
            parsed = urlparse(url)
            conn = psycopg2.connect(
                dbname=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port or 5432,
                sslmode="require" if "railway" in parsed.hostname else "prefer",
                connect_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not get table count for {env_name}: {e}")
            table_count = "Unknown"

        return {
            "env_name": env_name,
            "display_name": self.environments[env_name]["name"],
            "connection_ok": self.test_connection(env_name),
            "current_revision": current_revision,
            "migrations_current": migrations_current,
            "table_count": table_count,
            "url_host": parsed.hostname if "parsed" in locals() else "unknown",
        }

    def compare_environments(self) -> dict:
        """Compare schema state between environments"""
        logger.info("🔄 Comparing environments...")

        local_status = self.get_environment_status("local")
        railway_status = self.get_environment_status("railway")

        comparison = {
            "local": local_status,
            "railway": railway_status,
            "synchronized": False,
            "issues": [],
        }

        # Check if revisions match
        if local_status["current_revision"] != railway_status["current_revision"]:
            comparison["issues"].append(
                f"Migration mismatch: Local({local_status['current_revision']}) vs Railway({railway_status['current_revision']})"
            )

        # Check if both have pending migrations
        if not local_status["migrations_current"]:
            comparison["issues"].append("Local has pending migrations")

        if not railway_status["migrations_current"]:
            comparison["issues"].append("Railway has pending migrations")

        # Check connectivity
        if not local_status["connection_ok"]:
            comparison["issues"].append("Cannot connect to local database")

        if not railway_status["connection_ok"]:
            comparison["issues"].append("Cannot connect to Railway database")

        comparison["synchronized"] = len(comparison["issues"]) == 0

        return comparison

    def backup_environment(self, env_name: str) -> Optional[str]:
        """Create a backup of an environment's database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_{env_name}_{timestamp}.sql"

        logger.info(f"📦 Creating {env_name} backup: {backup_file}")

        url = self.environments[env_name]["url"]

        cmd = ["pg_dump", url, "-f", backup_file, "--no-owner", "--no-privileges"]
        stdout, stderr, returncode = self.run_command_with_env(cmd)

        if returncode != 0:
            logger.error(f"❌ Backup failed: {stderr}")
            return None

        # Check file size
        try:
            size = os.path.getsize(backup_file)
            logger.info(f"✅ Backup created: {backup_file} ({size:,} bytes)")
            return backup_file
        except Exception as e:
            logger.error(f"❌ Backup verification failed: {e}")
            return None

    def apply_migrations_to_env(self, env_name: str, dry_run: bool = True) -> bool:
        """Apply pending migrations to a specific environment"""
        logger.info(
            f"🚀 {'[DRY RUN] ' if dry_run else ''}Applying migrations to {env_name}..."
        )

        env_vars = self.environments[env_name]["alembic_env"]

        if dry_run:
            # Show what would be applied
            cmd = ["alembic", "upgrade", "head", "--sql"]
            stdout, stderr, returncode = self.run_command_with_env(cmd, env_vars)

            if stdout.strip():
                logger.info(f"📋 Migrations that would be applied to {env_name}:")
                print(stdout)
                return True
            else:
                logger.info(f"✅ No pending migrations for {env_name}")
                return True
        else:
            # Actually apply migrations
            cmd = ["alembic", "upgrade", "head"]
            stdout, stderr, returncode = self.run_command_with_env(cmd, env_vars)

            if returncode != 0:
                logger.error(f"❌ Migration failed for {env_name}: {stderr}")
                return False

            logger.info(f"✅ Migrations applied to {env_name}")
            return True

    def sync_to_railway(self, backup: bool = True, dry_run: bool = False) -> bool:
        """Synchronize local changes to Railway production"""
        logger.info("🌍 Starting local → Railway synchronization...")

        # Step 1: Verify local environment
        local_status = self.get_environment_status("local")
        if not local_status["connection_ok"]:
            logger.error("❌ Cannot connect to local database")
            return False

        if not local_status["migrations_current"]:
            logger.error(
                "❌ Local database has pending migrations. Apply them first with:"
            )
            logger.error("   python scripts/schema_workflow.py --apply-migrations")
            return False

        # Step 2: Check Railway connectivity
        railway_status = self.get_environment_status("railway")
        if not railway_status["connection_ok"]:
            logger.error("❌ Cannot connect to Railway database")
            return False

        # Step 3: Create Railway backup (if not dry run)
        if backup and not dry_run:
            backup_file = self.backup_environment("railway")
            if not backup_file:
                logger.error("❌ Failed to create Railway backup. Aborting for safety.")
                return False

        # Step 4: Show what would be applied to Railway
        logger.info("📋 Checking migrations for Railway...")
        success = self.apply_migrations_to_env("railway", dry_run=True)
        if not success:
            return False

        # Step 5: Confirm with user (if not dry run)
        if not dry_run:
            print("\n" + "=" * 60)
            print("🚨 PRODUCTION DEPLOYMENT CONFIRMATION")
            print("=" * 60)
            print(f"Environment: Railway Production")
            print(f"Current Revision: {railway_status['current_revision']}")
            print(f"Target Revision: {local_status['current_revision']}")
            if backup:
                print(f"Backup Created: {backup_file}")
            print("\nThis will apply the above migrations to PRODUCTION.")

            response = input("\nContinue with production deployment? (yes/NO): ")
            if response.lower() != "yes":
                logger.info("❌ Deployment cancelled by user")
                return False

        # Step 6: Apply migrations to Railway
        if not dry_run:
            success = self.apply_migrations_to_env("railway", dry_run=False)
            if not success:
                logger.error("❌ Railway deployment failed!")
                if backup:
                    logger.info(f"💡 You can restore from backup: {backup_file}")
                return False

        # Step 7: Verify synchronization
        if not dry_run:
            comparison = self.compare_environments()
            if comparison["synchronized"]:
                logger.info("🎉 Environments are now synchronized!")
            else:
                logger.warning("⚠️  Post-deployment verification detected issues:")
                for issue in comparison["issues"]:
                    logger.warning(f"   - {issue}")

        return True

    def sync_from_railway(self) -> bool:
        """Pull Railway schema state to local (for new deployments/team sync)"""
        logger.info("🌍 Starting Railway → local synchronization...")

        # Step 1: Check Railway status
        railway_status = self.get_environment_status("railway")
        if not railway_status["connection_ok"]:
            logger.error("❌ Cannot connect to Railway database")
            return False

        # Step 2: Backup local
        local_backup = self.backup_environment("local")
        if not local_backup:
            logger.warning("⚠️  Could not create local backup")

        # Step 3: Get Railway revision and apply to local
        railway_revision = railway_status["current_revision"]
        if not railway_revision:
            logger.error("❌ Could not determine Railway migration revision")
            return False

        logger.info(f"🔄 Syncing local to Railway revision: {railway_revision}")

        # Set local to same revision as Railway
        cmd = ["alembic", "stamp", railway_revision]
        stdout, stderr, returncode = self.run_command_with_env(cmd)

        if returncode != 0:
            logger.error(f"❌ Failed to sync local to Railway revision: {stderr}")
            return False

        logger.info("✅ Local database synced to Railway revision")
        return True

    def generate_sync_report(self) -> str:
        """Generate comprehensive multi-environment sync report"""
        comparison = self.compare_environments()

        report = [
            "",
            "🌍 MULTI-ENVIRONMENT SYNC REPORT",
            "=" * 50,
            f"Generated: {datetime.now().isoformat()}",
            "",
            "📊 ENVIRONMENT STATUS:",
        ]

        for env_name in ["local", "railway"]:
            env = comparison[env_name]
            status_icon = "✅" if env["connection_ok"] else "❌"
            migration_icon = "✅" if env["migrations_current"] else "⚠️"

            report.extend(
                [
                    f"  🏷️  {env['display_name']}:",
                    f"    {status_icon} Connection: {'OK' if env['connection_ok'] else 'FAILED'}",
                    f"    📍 Host: {env['url_host']}",
                    f"    🏷️  Revision: {env['current_revision'] or 'None'}",
                    f"    {migration_icon} Migrations: {'Current' if env['migrations_current'] else 'Pending'}",
                    f"    📊 Tables: {env['table_count']}",
                    "",
                ]
            )

        # Synchronization status
        if comparison["synchronized"]:
            report.extend(["🎯 SYNCHRONIZATION: ✅ IN SYNC", ""])
        else:
            report.extend(["🎯 SYNCHRONIZATION: ⚠️  ISSUES DETECTED", ""])
            for issue in comparison["issues"]:
                report.append(f"  ❗ {issue}")
            report.append("")

        # Recommendations
        report.extend(
            [
                "💡 RECOMMENDATIONS:",
            ]
        )

        if not comparison["synchronized"]:
            if "Local has pending migrations" in comparison["issues"]:
                report.append(
                    "  1. Apply local migrations: python scripts/schema_workflow.py --apply-migrations"
                )

            if "Migration mismatch" in str(comparison["issues"]):
                report.append(
                    "  2. Sync to Railway: python scripts/multi_env_schema_sync.py --sync-to-railway"
                )

            if "Railway has pending migrations" in comparison["issues"]:
                report.append("  3. Check Railway manually or sync from Railway")
        else:
            report.append("  ✅ Environments are synchronized - no action needed!")

        report.extend(
            [
                "",
                "🔧 AVAILABLE COMMANDS:",
                "  python scripts/multi_env_schema_sync.py --status",
                "  python scripts/multi_env_schema_sync.py --sync-to-railway --dry-run",
                "  python scripts/multi_env_schema_sync.py --sync-to-railway",
                "  python scripts/multi_env_schema_sync.py --sync-from-railway",
                "  python scripts/multi_env_schema_sync.py --backup railway",
            ]
        )

        return "\n".join(report)


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Multi-Environment Schema Synchronization"
    )
    parser.add_argument("--status", action="store_true", help="Show environment status")
    parser.add_argument(
        "--sync-to-railway", action="store_true", help="Deploy local changes to Railway"
    )
    parser.add_argument(
        "--sync-from-railway", action="store_true", help="Pull Railway state to local"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    parser.add_argument(
        "--backup", metavar="ENV", help="Create backup of environment (local/railway)"
    )
    parser.add_argument("--compare", action="store_true", help="Compare environments")
    parser.add_argument(
        "--test-connections",
        action="store_true",
        help="Test all environment connections",
    )

    args = parser.parse_args()

    sync_manager = MultiEnvSchemaSync()

    try:
        if args.status or args.compare:
            report = sync_manager.generate_sync_report()
            print(report)

        elif args.sync_to_railway:
            success = sync_manager.sync_to_railway(backup=True, dry_run=args.dry_run)
            if args.dry_run:
                logger.info(
                    "💡 This was a dry run. Use --sync-to-railway without --dry-run to actually deploy"
                )
            sys.exit(0 if success else 1)

        elif args.sync_from_railway:
            success = sync_manager.sync_from_railway()
            sys.exit(0 if success else 1)

        elif args.backup:
            env_name = args.backup.lower()
            if env_name not in sync_manager.environments:
                logger.error(f"❌ Unknown environment: {env_name}")
                sys.exit(1)

            backup_file = sync_manager.backup_environment(env_name)
            sys.exit(0 if backup_file else 1)

        elif args.test_connections:
            logger.info("🔌 Testing all environment connections...")
            all_ok = True
            for env_name in sync_manager.environments:
                if not sync_manager.test_connection(env_name):
                    all_ok = False
            sys.exit(0 if all_ok else 1)

        else:
            # Default: show status
            report = sync_manager.generate_sync_report()
            print(report)

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
