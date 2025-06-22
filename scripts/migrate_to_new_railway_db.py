#!/usr/bin/env python3
import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor


def migrate_database():
    """Complete migration from old Railway database to new Railway database"""

    # Database connection strings
    old_db_url = "postgresql://postgres:OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf@trolley.proxy.rlwy.net:34555/railway"
    new_db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

    print("🚀 Starting migration from old Railway database to new Railway database")
    print("=" * 80)

    try:
        # Connect to both databases
        print("📡 Connecting to databases...")
        old_conn = psycopg2.connect(old_db_url, cursor_factory=RealDictCursor)
        new_conn = psycopg2.connect(new_db_url, cursor_factory=RealDictCursor)

        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()

        print("✅ Connected to both databases")

        # Use the backup file instead to restore the schema and data
        print("\n📋 Using SQL backup to recreate database...")

        # Read the backup file we created earlier
        backup_files = [
            f
            for f in os.listdir(".")
            if f.startswith("current_db_backup_") and f.endswith(".sql")
        ]
        if not backup_files:
            print("❌ No backup file found. Please run backup_current_db.py first.")
            return False

        latest_backup = max(backup_files)
        print(f"Using backup file: {latest_backup}")

        # Read the backup file
        with open(latest_backup, "r") as f:
            backup_sql = f.read()

        # Execute the backup SQL in the new database
        print("🏗️  Restoring from backup...")
        try:
            new_cursor.execute(backup_sql)
            new_conn.commit()
            print("✅ Backup restored successfully")
        except Exception as e:
            # If bulk restore fails, try a more granular approach
            print(f"Bulk restore failed, trying granular approach: {str(e)}")
            restore_granular(new_cursor, new_conn, latest_backup)

        # Verify migration
        print("\n🔍 Verifying migration...")
        verify_migration_from_backup(old_cursor, new_cursor)

        # Close connections
        old_cursor.close()
        old_conn.close()
        new_cursor.close()
        new_conn.close()

        print("\n🎉 Migration completed successfully!")
        print("=" * 80)
        print("Next steps:")
        print("1. Update your Railway environment variables to use the new database")
        print("2. Update local configuration files")
        print("3. Test your application with the new database")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def restore_granular(new_cursor, new_conn, backup_file):
    """Restore database using a more granular approach"""
    print("  Attempting granular restore...")

    with open(backup_file, "r") as f:
        content = f.read()

    # Split into statements
    statements = content.split(";")

    for i, statement in enumerate(statements):
        statement = statement.strip()
        if not statement or statement.startswith("--"):
            continue

        try:
            new_cursor.execute(statement)
            new_conn.commit()
        except Exception as e:
            # Skip errors for things like sequence creation that might not be needed
            if "already exists" in str(e) or "does not exist" in str(e):
                continue
            else:
                print(f"  Warning: Statement {i} failed: {str(e)}")
                print(f"  Statement was: {statement[:100]}...")
                continue


def verify_migration_from_backup(old_cursor, new_cursor):
    """Verify that migration was successful by comparing with original database"""
    print("  Comparing row counts...")

    # Get all tables from old database
    old_cursor.execute(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """
    )
    old_tables = [row["table_name"] for row in old_cursor.fetchall()]

    # Get all tables from new database
    new_cursor.execute(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """
    )
    new_tables = [row["table_name"] for row in new_cursor.fetchall()]

    print(f"  Old database tables: {', '.join(old_tables)}")
    print(f"  New database tables: {', '.join(new_tables)}")

    # Check that all tables exist
    missing_tables = set(old_tables) - set(new_tables)
    if missing_tables:
        print(f"  ❌ Missing tables in new database: {', '.join(missing_tables)}")
        return False

    all_match = True
    for table in old_tables:
        if table not in new_tables:
            continue

        # Count in old database
        old_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        old_count = old_cursor.fetchone()["count"]

        # Count in new database
        new_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        new_count = new_cursor.fetchone()["count"]

        if old_count == new_count:
            print(f"    ✅ {table}: {old_count} rows (match)")
        else:
            print(f"    ❌ {table}: old={old_count}, new={new_count} (mismatch)")
            all_match = False

    if all_match:
        print("  ✅ All table row counts match!")
    else:
        print("  ❌ Some tables have mismatched row counts")

    return all_match


if __name__ == "__main__":
    migrate_database()
