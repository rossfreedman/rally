#!/usr/bin/env python3
"""
Rally Codebase & Database Backup Utility

This script creates backups of both the Rally codebase and PostgreSQL database.
Backups are stored with timestamps and can be automatically cleaned up based on age.

Usage:
    python3 cb.py                                    # Create both codebase and database backups
    python3 cb.py --codebase-only                    # Create only codebase backup
    python3 cb.py --database-only                    # Create only database backup
    python3 cb.py --db-format custom                 # Use custom format for database backup
    python3 cb.py --max-backups 5                    # Keep only 5 most recent backups
    python3 cb.py --exclude __pycache__ .venv        # Exclude specific directories from codebase
    python3 cb.py --list                             # List existing backups without creating new ones
    python3 cb.py --no-confirm                       # Skip confirmation before deleting old backups

Author: Rally Team
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import psycopg2

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_database_config():
    """Get database configuration from environment"""
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rally"
    )

    if database_url:
        parsed = urlparse(database_url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/") or "rally",
            "user": parsed.username or "postgres",
            "password": parsed.password or "postgres",
            "url": database_url,
        }

    # Fallback configuration
    return {
        "host": "localhost",
        "port": 5432,
        "database": "rally",
        "user": "postgres",
        "password": "postgres",
        "url": "postgresql://postgres:postgres@localhost:5432/rally",
    }


def get_alembic_info():
    """Get current Alembic migration information"""
    try:
        # Check current Alembic revision
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )

        current_revision = (
            result.stdout.strip() if result.returncode == 0 else "unknown"
        )

        # Check if there are pending migrations
        result = subprocess.run(
            ["alembic", "check"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )

        migrations_current = result.returncode == 0

        return {
            "current_revision": current_revision,
            "migrations_current": migrations_current,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.warning(f"Could not get Alembic information: {e}")
        return {
            "current_revision": "error",
            "migrations_current": False,
            "timestamp": datetime.now().isoformat(),
        }


def get_database_stats(config):
    """Get database statistics for backup metadata"""
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
        )

        stats = {}

        with conn.cursor() as cur:
            # Get PostgreSQL version
            cur.execute("SELECT version()")
            stats["postgresql_version"] = cur.fetchone()[0]

            # Get database size
            cur.execute(
                f"SELECT pg_size_pretty(pg_database_size('{config['database']}'))"
            )
            stats["database_size"] = cur.fetchone()[0]

            # Get table count
            cur.execute(
                """
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
            )
            stats["table_count"] = cur.fetchone()[0]

            # Get record counts for major tables
            major_tables = [
                "users",
                "players",
                "match_scores",
                "leagues",
                "clubs",
                "series",
            ]
            table_counts = {}

            for table in major_tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = cur.fetchone()[0]
                except:
                    table_counts[table] = "N/A"

            stats["table_counts"] = table_counts

        conn.close()
        return stats

    except Exception as e:
        logger.warning(f"Could not get database statistics: {e}")
        return {"error": str(e)}


def create_database_backup(backup_dir, db_format="sql", max_backups=10):
    """Create a database backup using pg_dump"""
    try:
        config = get_database_config()

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M")

        # Determine file extension based on format
        extensions = {"sql": ".sql", "custom": ".dump", "tar": ".tar"}

        backup_name = f"rally_db_backup_{timestamp}"
        backup_name += extensions.get(db_format, ".sql")

        backup_path = os.path.join(backup_dir, backup_name)

        print(f"\n🗄️  Creating database backup...")
        print(f"Database: {config['host']}:{config['port']}/{config['database']}")
        print(f"Format: {db_format}")
        print(f"Backup destination: {backup_path}")

        # Build pg_dump command
        cmd = [
            "pg_dump",
            "--host",
            config["host"],
            "--port",
            str(config["port"]),
            "--username",
            config["user"],
            "--dbname",
            config["database"],
            "--file",
            backup_path,
        ]

        # Add format-specific options
        if db_format == "custom":
            cmd.extend(["--format", "custom"])
        elif db_format == "tar":
            cmd.extend(["--format", "tar"])

        # Set environment for password
        env = os.environ.copy()
        env["PGPASSWORD"] = config["password"]

        # Run pg_dump
        start_time = time.time()
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Database backup failed: {result.stderr}")
            return None

        elapsed_time = time.time() - start_time

        # Get backup file size
        backup_size = os.path.getsize(backup_path)
        backup_size_mb = backup_size / (1024 * 1024)

        # Get additional metadata
        alembic_info = get_alembic_info()
        db_stats = get_database_stats(config)

        # Create metadata file
        metadata = {
            "backup_name": backup_name,
            "backup_path": backup_path,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "duration_seconds": elapsed_time,
            "backup_size_bytes": backup_size,
            "backup_size_mb": backup_size_mb,
            "backup_format": db_format,
            "database_config": {
                "host": config["host"],
                "port": config["port"],
                "database": config["database"],
                "user": config["user"],
            },
            "alembic_info": alembic_info,
            "database_stats": db_stats,
        }

        # Save metadata
        metadata_path = backup_path + ".metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Database backup completed!")
        print(f"Database backup location: {backup_path}")
        print(f"Database backup size: {backup_size_mb:.2f} MB")
        print(f"Time taken: {elapsed_time:.2f} seconds")
        print(f"Alembic revision: {alembic_info['current_revision']}")

        return backup_path

    except Exception as e:
        print(f"❌ Error creating database backup: {e}")
        return None


def list_backups():
    """List all existing backups (both codebase and database)"""
    try:
        # Get current directory (script is in rally/scripts/)
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Get rally root directory (parent of scripts directory)
        rally_root = os.path.dirname(current_dir)

        # Get parent directory (where rally and rally_backups should both be located)
        parent_dir = os.path.dirname(rally_root)

        # Check backup directories
        codebase_backup_dir = os.path.join(parent_dir, "rally_backups")
        db_backup_dir = os.path.join(parent_dir, "rally_db_backups")

        print(f"\n📋 RALLY BACKUP INVENTORY")
        print("=" * 60)

        # List codebase backups
        if os.path.exists(codebase_backup_dir):
            codebase_backups = [
                d
                for d in os.listdir(codebase_backup_dir)
                if os.path.isdir(os.path.join(codebase_backup_dir, d))
                and d.startswith("rally_")
            ]
            codebase_backups.sort(reverse=True)

            print(f"\n🔄 Codebase backups ({len(codebase_backups)}):")
            total_codebase_size = 0

            for i, backup in enumerate(codebase_backups[:5], 1):  # Show 5 most recent
                backup_path = os.path.join(codebase_backup_dir, backup)
                backup_time = os.path.getmtime(backup_path)
                backup_time_str = datetime.fromtimestamp(backup_time).strftime(
                    "%Y-%m-%d %I:%M %p"
                )
                backup_size = get_dir_size(backup_path)
                total_codebase_size += backup_size
                backup_size_mb = backup_size / (1024 * 1024)

                print(
                    f"{i}. {backup} (created: {backup_time_str}, size: {backup_size_mb:.2f} MB)"
                )

            if len(codebase_backups) > 5:
                print(f"... and {len(codebase_backups) - 5} more")

            print(f"Codebase backup location: {codebase_backup_dir}")
        else:
            print("\n🔄 Codebase backups: None found")

        # List database backups
        if os.path.exists(db_backup_dir):
            db_backups = []
            for item in os.listdir(db_backup_dir):
                item_path = os.path.join(db_backup_dir, item)
                if item.startswith("rally_db_backup_") and (
                    os.path.isfile(item_path) and not item.endswith(".metadata.json")
                ):

                    # Try to load metadata
                    metadata_path = item_path + ".metadata.json"
                    metadata = {}

                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, "r") as f:
                                metadata = json.load(f)
                        except:
                            pass

                    stat_info = os.stat(item_path)
                    db_backups.append(
                        {
                            "name": item,
                            "path": item_path,
                            "created": datetime.fromtimestamp(stat_info.st_mtime),
                            "size_bytes": metadata.get(
                                "backup_size_bytes", stat_info.st_size
                            ),
                            "metadata": metadata,
                        }
                    )

            db_backups.sort(key=lambda x: x["created"], reverse=True)

            print(f"\n🗄️  Database backups ({len(db_backups)}):")
            total_db_size = 0

            for i, backup in enumerate(db_backups[:5], 1):  # Show 5 most recent
                size_mb = backup["size_bytes"] / (1024 * 1024)
                total_db_size += backup["size_bytes"]

                created_str = backup["created"].strftime("%Y-%m-%d %I:%M %p")
                format_info = backup["metadata"].get("backup_format", "unknown")
                alembic_rev = (
                    backup["metadata"]
                    .get("alembic_info", {})
                    .get("current_revision", "unknown")
                )

                print(
                    f"{i}. {backup['name']} (created: {created_str}, size: {size_mb:.2f} MB)"
                )
                print(
                    f"   Format: {format_info}, Alembic: {alembic_rev[:20]}{'...' if len(str(alembic_rev)) > 20 else ''}"
                )

            if len(db_backups) > 5:
                print(f"... and {len(db_backups) - 5} more")

            print(f"Database backup location: {db_backup_dir}")
        else:
            print("\n🗄️  Database backups: None found")

        # Summary
        print(f"\n📊 BACKUP SUMMARY")
        print("-" * 30)
        codebase_count = (
            len(codebase_backups) if os.path.exists(codebase_backup_dir) else 0
        )
        db_count = len(db_backups) if os.path.exists(db_backup_dir) else 0
        print(f"Total codebase backups: {codebase_count}")
        print(f"Total database backups: {db_count}")

    except Exception as e:
        print(f"\n❌ Error listing backups: {str(e)}")
        sys.exit(1)


def cleanup_old_backups(backup_dir, max_backups, no_confirm=False):
    """
    Clean up old codebase backups, keeping only the most recent ones

    Args:
        backup_dir (str): Backup directory path
        max_backups (int): Maximum number of backups to keep
        no_confirm (bool): Skip confirmation before deleting
    """
    try:
        # List all backup directories
        backups = [
            d
            for d in os.listdir(backup_dir)
            if os.path.isdir(os.path.join(backup_dir, d)) and d.startswith("rally_")
        ]

        # Sort by modification time (newest first)
        backups.sort(
            key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True
        )

        # If we have more backups than the maximum, delete the oldest ones
        if len(backups) > max_backups:
            backups_to_delete = backups[max_backups:]

            # Get confirmation before deleting unless --no-confirm flag is set
            if not no_confirm:
                confirm = input(
                    f"Delete {len(backups_to_delete)} old codebase backup(s)? [y/N]: "
                )
                if confirm.lower() != "y":
                    print("Skipping cleanup of old codebase backups.")
                    return

            print(
                f"🔄 Cleaning up {len(backups_to_delete)} old codebase backups (keeping {max_backups} most recent)..."
            )

            for backup in backups_to_delete:
                backup_path = os.path.join(backup_dir, backup)
                print(f"Deleting old codebase backup: {backup}")
                shutil.rmtree(backup_path)

            print(
                f"Codebase backup cleanup complete. {len(backups_to_delete)} old backups removed."
            )

    except Exception as e:
        print(f"Warning: Error during codebase backup cleanup: {str(e)}")


def create_backup(
    max_backups=10,
    exclude_patterns=None,
    no_confirm=False,
    codebase_only=False,
    database_only=False,
    db_format="sql",
):
    """
    Create backups of codebase and/or database

    Args:
        max_backups (int): Maximum number of backups to keep
        exclude_patterns (list): List of patterns to exclude from codebase backup
        no_confirm (bool): Skip confirmation before deleting old backups
        codebase_only (bool): Create only codebase backup
        database_only (bool): Create only database backup
        db_format (str): Database backup format (sql, custom, tar)
    """
    try:
        start_time = time.time()

        # Get current directory (script is in rally/scripts/)
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Get rally root directory (parent of scripts directory)
        rally_root = os.path.dirname(current_dir)
        rally_dir_name = os.path.basename(rally_root)

        # Get parent directory (where rally and rally_backups should both be located)
        parent_dir = os.path.dirname(rally_root)

        # Create backup directories
        codebase_backup_dir = os.path.join(parent_dir, "rally_backups")
        db_backup_dir = os.path.join(parent_dir, "rally_db_backups")

        if not database_only:
            os.makedirs(codebase_backup_dir, exist_ok=True)
        if not codebase_only:
            os.makedirs(db_backup_dir, exist_ok=True)

        print(f"\n🚀 RALLY BACKUP UTILITY")
        print("=" * 50)

        if codebase_only:
            print("🔄 Creating CODEBASE backup only")
        elif database_only:
            print("🗄️  Creating DATABASE backup only")
        else:
            print("🔄 Creating BOTH codebase and database backups")

        codebase_backup_path = None
        database_backup_path = None

        # Create codebase backup
        if not database_only:
            # Get current timestamp in desired format (YYYY_MM_DD_HHMM)
            timestamp = datetime.now().strftime("%Y_%m_%d_%H%M")

            # Create backup folder name
            backup_name = f"rally_backup_{timestamp}"
            codebase_backup_path = os.path.join(codebase_backup_dir, backup_name)

            # Default exclude patterns if none provided
            if exclude_patterns is None:
                exclude_patterns = [
                    "__pycache__",
                    ".git",
                    ".venv",
                    "node_modules",
                    "*.pyc",
                    ".DS_Store",
                    "*.log",
                ]

            # Create the codebase backup
            print(f"\n🔄 Creating codebase backup: {backup_name}")
            print(f"Rally folder: {rally_root}")
            print(f"Backup destination: {codebase_backup_path}")
            print(f"Excluding patterns: {exclude_patterns}")

            # Custom ignore function to ignore specified directories
            def ignore_patterns(path, names):
                ignored = set()
                for name in names:
                    # Check if the name matches any of the exclude patterns
                    for pattern in exclude_patterns:
                        if pattern.startswith("*"):
                            # Handle file extension patterns
                            if name.endswith(pattern[1:]):
                                ignored.add(name)
                        elif name == pattern:
                            # Handle exact match patterns
                            ignored.add(name)
                return ignored

            # Copy the entire directory
            shutil.copytree(rally_root, codebase_backup_path, ignore=ignore_patterns)

            # Calculate the backup size
            codebase_backup_size = get_dir_size(codebase_backup_path)
            codebase_backup_size_mb = codebase_backup_size / (1024 * 1024)

            print(f"✅ Codebase backup completed!")
            print(f"Codebase backup location: {codebase_backup_path}")
            print(f"Codebase backup size: {codebase_backup_size_mb:.2f} MB")

        # Create database backup
        if not codebase_only:
            database_backup_path = create_database_backup(
                db_backup_dir, db_format, max_backups
            )

        # Calculate total time
        elapsed_time = time.time() - start_time
        print(f"\n🎉 BACKUP PROCESS COMPLETED!")
        print(f"Total time taken: {elapsed_time:.2f} seconds")

        # Cleanup old backups if needed
        if not database_only:
            cleanup_old_backups(codebase_backup_dir, max_backups, no_confirm)
        if not codebase_only:
            cleanup_old_database_backups(db_backup_dir, max_backups, no_confirm)

        return codebase_backup_path, database_backup_path

    except Exception as e:
        print(f"\n❌ Error creating backup: {str(e)}")
        sys.exit(1)


def cleanup_old_database_backups(backup_dir, max_backups, no_confirm=False):
    """Clean up old database backups, keeping only the most recent ones"""
    try:
        # Find all database backup files
        backups = []
        for item in os.listdir(backup_dir):
            if item.startswith("rally_db_backup_") and not item.endswith(
                ".metadata.json"
            ):
                item_path = os.path.join(backup_dir, item)
                backups.append((item, os.path.getmtime(item_path)))

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x[1], reverse=True)

        # Remove old backups if we exceed the limit
        if len(backups) > max_backups:
            backups_to_delete = backups[max_backups:]

            if not no_confirm:
                confirm = input(
                    f"Delete {len(backups_to_delete)} old database backup(s)? [y/N]: "
                )
                if confirm.lower() != "y":
                    print("Skipping cleanup of old database backups.")
                    return

            print(f"🗄️  Cleaning up {len(backups_to_delete)} old database backups...")

            for backup_name, _ in backups_to_delete:
                backup_path = os.path.join(backup_dir, backup_name)
                metadata_path = backup_path + ".metadata.json"

                try:
                    os.remove(backup_path)
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                    print(f"Deleted old database backup: {backup_name}")
                except Exception as e:
                    print(f"Warning: Failed to delete {backup_name}: {e}")

            print(
                f"Database backup cleanup complete. {len(backups_to_delete)} old backups removed."
            )

    except Exception as e:
        print(f"Warning: Error during database backup cleanup: {str(e)}")


def get_dir_size(path):
    """
    Calculate the total size of a directory in bytes

    Args:
        path (str): Directory path

    Returns:
        int: Directory size in bytes
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size


def main():
    """Main entry point for backup script"""
    parser = argparse.ArgumentParser(
        description="Create backups of Rally codebase and/or database"
    )
    parser.add_argument(
        "--max-backups",
        type=int,
        default=10,
        help="Maximum number of backups to keep (default: 10)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        help="Patterns to exclude from codebase backup (space separated)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing backups without creating new ones",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip confirmation before deleting old backups",
    )
    parser.add_argument(
        "--codebase-only",
        action="store_true",
        help="Create only codebase backup (skip database)",
    )
    parser.add_argument(
        "--database-only",
        action="store_true",
        help="Create only database backup (skip codebase)",
    )
    parser.add_argument(
        "--db-format",
        choices=["sql", "custom", "tar"],
        default="sql",
        help="Database backup format (default: sql)",
    )
    args = parser.parse_args()

    if args.list:
        list_backups()
    else:
        if args.codebase_only and args.database_only:
            print("❌ Cannot use both --codebase-only and --database-only")
            sys.exit(1)

        create_backup(
            max_backups=args.max_backups,
            exclude_patterns=args.exclude,
            no_confirm=args.no_confirm,
            codebase_only=args.codebase_only,
            database_only=args.database_only,
            db_format=args.db_format,
        )


if __name__ == "__main__":
    main()
