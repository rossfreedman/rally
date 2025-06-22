#!/usr/bin/env python3
import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor


def final_migrate():
    """Final migration with exact schema matching"""

    # Database connection strings
    old_db_url = "postgresql://postgres:OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf@trolley.proxy.rlwy.net:34555/railway"
    new_db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

    print("🚀 Starting final migration")
    print("=" * 50)

    try:
        # Connect to both databases
        old_conn = psycopg2.connect(old_db_url)
        new_conn = psycopg2.connect(new_db_url)

        old_cursor = old_conn.cursor(cursor_factory=RealDictCursor)
        new_cursor = new_conn.cursor()

        print("✅ Connected to both databases")

        # Fix users table schema first
        print("\n🔧 Fixing users table schema...")
        try:
            # Add missing columns to users table
            new_cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS club_automation_password VARCHAR(255);"
            )
            new_cursor.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;"
            )
            new_cursor.execute(
                "ALTER TABLE users DROP COLUMN IF EXISTS phone;"
            )  # Remove column that doesn't exist in old
            new_conn.commit()
            print("  ✅ Users table schema updated")
        except Exception as e:
            print(f"  ❌ Schema update failed: {str(e)}")
            new_conn.rollback()

        # Fix player_availability table schema
        print("\n🔧 Fixing player_availability table schema...")
        try:
            # Rename column to match old schema
            new_cursor.execute(
                "ALTER TABLE player_availability RENAME COLUMN availability_status TO availability;"
            )
            new_cursor.execute(
                "ALTER TABLE player_availability RENAME COLUMN updated_at TO submitted_at;"
            )
            new_conn.commit()
            print("  ✅ Player_availability table schema updated")
        except Exception as e:
            print(f"  ❌ Schema update failed: {str(e)}")
            new_conn.rollback()

        # Now migrate the remaining tables
        remaining_tables = ["users", "player_availability"]

        print("\n📦 Migrating remaining tables...")
        for table_name in remaining_tables:
            migrate_table_final(old_cursor, new_cursor, new_conn, table_name)

        print("✅ Final migration completed")

        # Final verification
        print("\n🔍 Final verification...")
        verify_final(old_cursor, new_cursor, new_conn)

        # Close connections
        old_cursor.close()
        old_conn.close()
        new_cursor.close()
        new_conn.close()

        print("\n🎉 Migration completed successfully!")
        print("=" * 50)
        print("Your new Railway database is ready!")
        print("\n📝 Next steps:")
        print("1. Update your Railway environment variables")
        print("2. Test your application with the new database")
        print("3. Update local configuration files")

        return True

    except Exception as e:
        print(f"\n❌ Final migration failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def migrate_table_final(old_cursor, new_cursor, new_conn, table_name):
    """Migrate data for remaining tables"""
    print(f"  Migrating {table_name}...")

    try:
        # Ensure clean transaction state
        if new_conn.status != psycopg2.extensions.STATUS_READY:
            new_conn.rollback()

        # Get count
        old_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        result = old_cursor.fetchone()
        count = result["count"]

        if count == 0:
            print(f"    No data in {table_name}")
            return

        print(f"    Found {count} rows to migrate...")

        # Get all data
        old_cursor.execute(f"SELECT * FROM {table_name}")
        rows = old_cursor.fetchall()

        # Get column names from old table
        old_column_names = [desc[0] for desc in old_cursor.description]

        # Get column names from new table
        new_cursor.execute(
            f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position
        """
        )
        new_column_names = [row[0] for row in new_cursor.fetchall()]

        # Find common columns (intersection)
        common_columns = [col for col in old_column_names if col in new_column_names]
        print(f"    Using columns: {', '.join(common_columns)}")

        # Clear existing data
        new_cursor.execute(f"DELETE FROM {table_name}")

        # Insert data using only common columns
        placeholders = ", ".join(["%s"] * len(common_columns))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(common_columns)}) VALUES ({placeholders})"

        data_rows = []
        for row in rows:
            # Only include values for common columns
            row_data = tuple(row[col] for col in common_columns)
            data_rows.append(row_data)

        new_cursor.executemany(insert_sql, data_rows)
        new_conn.commit()

        print(f"    ✅ Migrated {len(data_rows)} rows")

    except Exception as e:
        print(f"    ❌ Failed to migrate {table_name}: {str(e)}")
        try:
            new_conn.rollback()
        except:
            pass
        import traceback

        traceback.print_exc()


def verify_final(old_cursor, new_cursor, new_conn):
    """Final verification"""
    print("  Comparing final row counts...")

    # Ensure clean transaction state
    if new_conn.status != psycopg2.extensions.STATUS_READY:
        new_conn.rollback()

    tables = [
        "alembic_version",
        "clubs",
        "series",
        "users",
        "player_availability",
        "user_activity_logs",
        "user_instructions",
    ]

    all_match = True
    total_old = 0
    total_new = 0

    for table in tables:
        try:
            old_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            old_count = old_cursor.fetchone()["count"]

            new_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            new_count = new_cursor.fetchone()[0]

            total_old += old_count
            total_new += new_count

            if old_count == new_count:
                print(f"    ✅ {table}: {old_count} rows (match)")
            else:
                print(f"    ❌ {table}: old={old_count}, new={new_count} (mismatch)")
                all_match = False
        except Exception as e:
            print(f"    ❌ {table}: Error - {str(e)}")
            all_match = False

    print(f"\n  📊 Total rows: Old={total_old}, New={total_new}")

    if all_match:
        print("  🎉 All tables migrated successfully!")
    else:
        print("  ⚠️  Some tables have mismatched counts")

    return all_match


if __name__ == "__main__":
    final_migrate()
