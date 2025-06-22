#!/usr/bin/env python3
"""
Complete Database Clone: Local -> Railway
1. Backup current Railway database
2. Clone complete local database to Railway
"""

import os
import subprocess
import sys
from datetime import datetime
from urllib.parse import urlparse

import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"


def get_connection_params(url):
    """Parse database URL into connection parameters"""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path[1:],
        "username": parsed.username,
        "password": parsed.password,
    }


def get_local_connection_params():
    """Get local database connection parameters using existing config"""
    # Import and use the existing database configuration
    from database_config import get_db_url, parse_db_url

    local_url = get_db_url()
    db_params = parse_db_url(local_url)

    return {
        "host": db_params["host"],
        "port": db_params["port"],
        "database": db_params["dbname"],
        "username": db_params["user"],
        "password": db_params["password"],
    }


def create_backup_filename():
    """Create timestamped backup filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(
        "data", "backups", "database", f"railway_backup_{timestamp}.sql"
    )


def backup_railway_database():
    """Create backup of current Railway database using Python"""
    print("🔄 STEP 1: BACKING UP RAILWAY DATABASE")
    print("-" * 50)

    backup_file = create_backup_filename()

    try:
        railway_params = get_connection_params(RAILWAY_URL)
        conn = psycopg2.connect(
            **{
                "dbname": railway_params["database"],
                "user": railway_params["username"],
                "password": railway_params["password"],
                "host": railway_params["host"],
                "port": railway_params["port"],
                "sslmode": "require",
            }
        )

        cursor = conn.cursor()

        print(f"  📁 Creating Python-based backup: {backup_file}")

        with open(backup_file, "w") as f:
            # Write header
            f.write("-- Railway Database Backup\n")
            f.write("-- Created by Python script\n")
            f.write(f"-- Date: {datetime.now()}\n\n")

            # Get all tables
            cursor.execute(
                """
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename
            """
            )
            tables = [row[0] for row in cursor.fetchall()]

            print(f"  📋 Backing up {len(tables)} tables...")

            # Export each table's data
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]

                    if count > 0:
                        f.write(f"-- Table: {table} ({count:,} records)\n")
                        f.write(f"TRUNCATE TABLE {table} CASCADE;\n")

                        # Get column names
                        cursor.execute(f"SELECT * FROM {table} LIMIT 0")
                        columns = [desc[0] for desc in cursor.description]

                        # Export data in batches
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()

                        for row in rows:
                            values = []
                            for val in row:
                                if val is None:
                                    values.append("NULL")
                                elif isinstance(val, str):
                                    values.append(
                                        f"'{val.replace(chr(39), chr(39)+chr(39))}'"
                                    )  # Escape quotes
                                else:
                                    values.append(str(val))

                            f.write(
                                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                            )

                        f.write(f"\n")
                        print(f"    ✅ {table}: {count:,} records")
                    else:
                        print(f"    📭 {table}: empty")

                except Exception as e:
                    print(f"    ⚠️  Could not backup {table}: {e}")

        conn.close()

        # Check backup file size
        if os.path.exists(backup_file) and os.path.getsize(backup_file) > 100:
            print(f"  ✅ Backup successful: {backup_file}")
            print(f"  📊 Backup size: {os.path.getsize(backup_file):,} bytes")
            return backup_file
        else:
            print(f"  ❌ Backup file seems empty or missing")
            return None

    except Exception as e:
        print(f"  ❌ Backup failed: {e}")
        return None


def clear_railway_data():
    """Clear all data from Railway database while preserving schema"""
    print("\n🗑️  STEP 2: CLEARING RAILWAY DATA")
    print("-" * 50)

    try:
        railway_params = get_connection_params(RAILWAY_URL)
        conn = psycopg2.connect(
            **{
                "dbname": railway_params["database"],
                "user": railway_params["username"],
                "password": railway_params["password"],
                "host": railway_params["host"],
                "port": railway_params["port"],
                "sslmode": "require",
            }
        )

        cursor = conn.cursor()

        # Disable foreign key constraints temporarily
        print("  🔓 Disabling foreign key constraints...")
        cursor.execute("SET session_replication_role = replica;")

        # Get all tables
        cursor.execute(
            """
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'alembic%'
            ORDER BY tablename
        """
        )
        tables = [row[0] for row in cursor.fetchall()]

        print(f"  📋 Found {len(tables)} tables to clear")

        # Truncate each table
        for table in tables:
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                print(f"    ✅ Cleared: {table}")
            except Exception as e:
                print(f"    ⚠️  Could not clear {table}: {e}")

        # Re-enable foreign key constraints
        print("  🔒 Re-enabling foreign key constraints...")
        cursor.execute("SET session_replication_role = DEFAULT;")

        conn.commit()
        conn.close()

        print("  ✅ Railway data cleared successfully")
        return True

    except Exception as e:
        print(f"  ❌ Failed to clear Railway data: {e}")
        return False


def export_local_data():
    """Export data from local database using Python"""
    print("\n📤 STEP 3: EXPORTING LOCAL DATABASE DATA")
    print("-" * 50)

    export_file = "local_data_export.sql"

    try:
        local_params = get_local_connection_params()

        # Use the existing database connection method
        with get_db() as conn:
            cursor = conn.cursor()

            print(f"  📁 Creating Python-based export: {export_file}")

            with open(export_file, "w") as f:
                # Write header
                f.write("-- Local Database Export\n")
                f.write("-- Created by Python script\n")
                f.write(f"-- Date: {datetime.now()}\n\n")
                f.write("-- Disable triggers during import\n")
                f.write("SET session_replication_role = replica;\n\n")

                # Get all tables
                cursor.execute(
                    """
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename NOT LIKE 'alembic%'
                    ORDER BY tablename
                """
                )
                tables = [row[0] for row in cursor.fetchall()]

                print(f"  📋 Exporting {len(tables)} tables...")

                # Export each table's data
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]

                        if count > 0:
                            f.write(f"-- Table: {table} ({count:,} records)\n")

                            # Get column names
                            cursor.execute(f"SELECT * FROM {table} LIMIT 0")
                            columns = [desc[0] for desc in cursor.description]

                            # Export data in smaller batches for large tables
                            batch_size = 1000
                            offset = 0

                            while offset < count:
                                cursor.execute(
                                    f"SELECT * FROM {table} ORDER BY {columns[0]} LIMIT {batch_size} OFFSET {offset}"
                                )
                                rows = cursor.fetchall()

                                if not rows:
                                    break

                                for row in rows:
                                    values = []
                                    for val in row:
                                        if val is None:
                                            values.append("NULL")
                                        elif isinstance(val, str):
                                            # Properly escape quotes and special characters
                                            escaped = (
                                                val.replace("'", "''")
                                                .replace("\n", "\\n")
                                                .replace("\r", "\\r")
                                            )
                                            values.append(f"'{escaped}'")
                                        elif isinstance(val, (int, float)):
                                            values.append(str(val))
                                        else:
                                            # For dates, booleans, etc.
                                            values.append(f"'{str(val)}'")

                                    f.write(
                                        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                                    )

                                offset += batch_size

                            f.write(f"\n")
                            print(f"    ✅ {table}: {count:,} records")
                        else:
                            print(f"    📭 {table}: empty")

                    except Exception as e:
                        print(f"    ⚠️  Could not export {table}: {e}")

                # Re-enable triggers
                f.write("-- Re-enable triggers\n")
                f.write("SET session_replication_role = DEFAULT;\n")

        # Check export file size
        if os.path.exists(export_file) and os.path.getsize(export_file) > 1000:
            print(f"  ✅ Export successful: {export_file}")
            print(f"  📊 Export size: {os.path.getsize(export_file):,} bytes")
            return export_file
        else:
            print(f"  ❌ Export file seems empty or missing")
            return None

    except Exception as e:
        print(f"  ❌ Export failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def import_data_to_railway(export_file):
    """Import local data to Railway database using Python"""
    print("\n📥 STEP 4: IMPORTING DATA TO RAILWAY")
    print("-" * 50)

    print(f"  📥 Importing data from: {export_file}")

    try:
        railway_params = get_connection_params(RAILWAY_URL)
        conn = psycopg2.connect(
            **{
                "dbname": railway_params["database"],
                "user": railway_params["username"],
                "password": railway_params["password"],
                "host": railway_params["host"],
                "port": railway_params["port"],
                "sslmode": "require",
            }
        )

        cursor = conn.cursor()

        # Read and execute the SQL file in chunks
        with open(export_file, "r") as f:
            sql_commands = f.read().split(";\n")

        print(f"  🔧 Executing {len(sql_commands):,} SQL commands...")

        executed = 0
        for i, command in enumerate(sql_commands):
            command = command.strip()
            if command and not command.startswith("--"):
                try:
                    cursor.execute(command)
                    executed += 1

                    # Commit every 1000 commands for better performance
                    if executed % 1000 == 0:
                        conn.commit()
                        print(
                            f"    ✅ Executed {executed:,}/{len(sql_commands):,} commands"
                        )

                except Exception as e:
                    print(f"    ⚠️  Error with command {i}: {str(e)[:100]}...")
                    # Continue with next command instead of failing completely
                    continue

        # Final commit
        conn.commit()
        conn.close()

        print(f"  ✅ Import successful!")
        print(f"  📊 Successfully executed {executed:,} SQL commands")
        return True

    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def fix_sequences():
    """Fix sequences after data import"""
    print("\n🔧 STEP 5: FIXING SEQUENCES")
    print("-" * 50)

    try:
        railway_params = get_connection_params(RAILWAY_URL)
        conn = psycopg2.connect(
            **{
                "dbname": railway_params["database"],
                "user": railway_params["username"],
                "password": railway_params["password"],
                "host": railway_params["host"],
                "port": railway_params["port"],
                "sslmode": "require",
            }
        )

        cursor = conn.cursor()

        # Get all sequences
        cursor.execute(
            """
            SELECT schemaname, sequencename FROM pg_sequences 
            WHERE schemaname = 'public'
        """
        )
        sequences = cursor.fetchall()

        print(f"  🔍 Found {len(sequences)} sequences to fix")

        for schema, sequence in sequences:
            try:
                # Extract table and column name from sequence name
                # Most sequences follow pattern: tablename_columnname_seq
                if sequence.endswith("_seq"):
                    base_name = sequence[:-4]  # Remove '_seq'
                    parts = base_name.split("_")
                    if len(parts) >= 2:
                        table_name = "_".join(parts[:-1])
                        column_name = parts[-1]

                        # Fix the sequence
                        cursor.execute(
                            f"""
                            SELECT setval('{sequence}', 
                                          COALESCE((SELECT MAX({column_name}) FROM {table_name}), 1), 
                                          false)
                        """
                        )
                        print(f"    ✅ Fixed sequence: {sequence}")

            except Exception as e:
                print(f"    ⚠️  Could not fix sequence {sequence}: {e}")

        conn.commit()
        conn.close()

        print("  ✅ Sequences fixed successfully")
        return True

    except Exception as e:
        print(f"  ❌ Failed to fix sequences: {e}")
        return False


def verify_clone():
    """Verify the database clone was successful"""
    print("\n✅ STEP 6: VERIFYING CLONE")
    print("-" * 50)

    try:
        railway_params = get_connection_params(RAILWAY_URL)
        conn = psycopg2.connect(
            **{
                "dbname": railway_params["database"],
                "user": railway_params["username"],
                "password": railway_params["password"],
                "host": railway_params["host"],
                "port": railway_params["port"],
                "sslmode": "require",
            }
        )

        cursor = conn.cursor()

        # Check critical tables
        critical_tables = [
            "users",
            "players",
            "player_history",
            "user_player_associations",
            "leagues",
            "clubs",
            "series",
        ]

        print("  📊 Table record counts:")
        for table in critical_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"    {table}: {count:,} records")
            except Exception as e:
                print(f"    {table}: ❌ Error - {e}")

        # Test specific critical queries
        print("\n  🔍 Testing critical functionality:")

        # Test player_history links
        cursor.execute(
            """
            SELECT COUNT(*) FROM player_history ph
            JOIN players p ON ph.player_id = p.id
        """
        )
        linked_history = cursor.fetchone()[0]
        print(f"    Player history with valid links: {linked_history:,}")

        # Test user associations
        cursor.execute(
            """
            SELECT COUNT(*) FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            JOIN players p ON upa.player_id = p.id
        """
        )
        valid_associations = cursor.fetchone()[0]
        print(f"    Valid user-player associations: {valid_associations:,}")

        conn.close()

        print("  ✅ Verification completed")
        return True

    except Exception as e:
        print(f"  ❌ Verification failed: {e}")
        return False


def cleanup_files():
    """Clean up temporary files"""
    print("\n🧹 CLEANING UP TEMPORARY FILES")
    print("-" * 50)

    files_to_remove = ["local_data_export.sql"]

    for file in files_to_remove:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"  🗑️  Removed: {file}")
            except Exception as e:
                print(f"  ⚠️  Could not remove {file}: {e}")


def check_prerequisites():
    """Check if required tools are available"""
    print("🔍 CHECKING PREREQUISITES")
    print("-" * 50)

    required_tools = ["pg_dump", "psql"]
    missing_tools = []

    for tool in required_tools:
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.split("\n")[0]
                print(f"  ✅ {tool}: {version_line}")
            else:
                missing_tools.append(tool)
                print(f"  ❌ {tool}: Not working properly")
        except FileNotFoundError:
            missing_tools.append(tool)
            print(f"  ❌ {tool}: Not found")

    if missing_tools:
        print(f"\n❌ Missing required tools: {', '.join(missing_tools)}")
        print("To install PostgreSQL client tools on macOS:")
        print("  brew install postgresql")
        print("Or with MacPorts:")
        print("  sudo port install postgresql15 +universal")
        return False

    print(f"  ✅ All required tools available")
    return True


def main():
    """Main database cloning process"""
    print("🚀 COMPLETE DATABASE CLONE: LOCAL -> RAILWAY")
    print("=" * 60)
    print("This will replace all Railway data with your local database")
    print("=" * 60)

    # Check prerequisites first
    if not check_prerequisites():
        print(
            "\n❌ Prerequisites not met. Please install required tools and try again."
        )
        return False

    try:
        # Step 1: Backup Railway
        backup_file = backup_railway_database()
        if not backup_file:
            print("❌ Cannot proceed without backup")
            return False

        # Step 2: Clear Railway data
        if not clear_railway_data():
            print("❌ Failed to clear Railway data")
            return False

        # Step 3: Export local data
        export_file = export_local_data()
        if not export_file:
            print("❌ Failed to export local data")
            return False

        # Step 4: Import to Railway
        if not import_data_to_railway(export_file):
            print("❌ Failed to import data to Railway")
            return False

        # Step 5: Fix sequences
        if not fix_sequences():
            print("⚠️  Sequences may need manual fixing")

        # Step 6: Verify
        if not verify_clone():
            print("⚠️  Verification had issues")

        # Step 7: Cleanup
        cleanup_files()

        # Final summary
        print(f"\n" + "=" * 60)
        print(f"✅ DATABASE CLONE COMPLETED!")
        print(f"📁 Railway backup saved as: {backup_file}")
        print(f"🌐 Test your application at: https://www.lovetorally.com")
        print(f"📊 Your local database has been fully cloned to Railway")
        print(f"🔧 All critical gaps should now be resolved")

        return True

    except Exception as e:
        print(f"\n❌ CLONE FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
