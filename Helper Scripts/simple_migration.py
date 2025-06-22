#!/usr/bin/env python3
import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor


def simple_migrate():
    """Simple table-by-table migration"""

    # Database connection strings
    old_db_url = "postgresql://postgres:OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf@trolley.proxy.rlwy.net:34555/railway"
    new_db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

    print("🚀 Starting simple migration")
    print("=" * 50)

    try:
        # Connect to both databases
        print("📡 Connecting to databases...")
        old_conn = psycopg2.connect(old_db_url)
        new_conn = psycopg2.connect(new_db_url)

        old_cursor = old_conn.cursor(cursor_factory=RealDictCursor)
        new_cursor = new_conn.cursor()

        print("✅ Connected to both databases")

        # Define table creation order (to handle dependencies)
        tables_schema = {
            "alembic_version": """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                );
            """,
            "series": """
                CREATE TABLE IF NOT EXISTS series (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE
                );
            """,
            "clubs": """
                CREATE TABLE IF NOT EXISTS clubs (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE
                );
            """,
            "users": """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    club_id INTEGER REFERENCES clubs(id),
                    series_id INTEGER REFERENCES series(id),
                    phone VARCHAR(20),
                    club_automation_password VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_admin BOOLEAN DEFAULT false
                );
            """,
            "player_availability": """
                CREATE TABLE IF NOT EXISTS player_availability (
                    id SERIAL PRIMARY KEY,
                    player_name VARCHAR(255) NOT NULL,
                    match_date DATE NOT NULL,
                    availability_status VARCHAR(50) NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    series_id INTEGER REFERENCES series(id),
                    UNIQUE(player_name, match_date, series_id)
                );
            """,
            "user_activity_logs": """
                CREATE TABLE IF NOT EXISTS user_activity_logs (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255),
                    activity_type VARCHAR(100),
                    page VARCHAR(255),
                    action VARCHAR(255),
                    details TEXT,
                    ip_address VARCHAR(45),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
            "user_instructions": """
                CREATE TABLE IF NOT EXISTS user_instructions (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) NOT NULL,
                    instruction_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """,
        }

        # Create tables in order
        print("\n🏗️  Creating tables...")
        for table_name, create_sql in tables_schema.items():
            print(f"  Creating {table_name}...")
            new_cursor.execute(create_sql)
            new_conn.commit()

        print("✅ All tables created")

        # Migrate data table by table
        print("\n📦 Migrating data...")
        for table_name in tables_schema.keys():
            migrate_table_simple(old_cursor, new_cursor, new_conn, table_name)

        print("✅ Data migration completed")

        # Create indexes
        print("\n📋 Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_player_availability ON player_availability(player_name, match_date, series_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_activity_logs_user_email ON user_activity_logs(user_email, timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_user_instructions_email ON user_instructions(user_email);",
        ]

        for index_sql in indexes:
            try:
                new_cursor.execute(index_sql)
                new_conn.commit()
            except Exception as e:
                print(f"  Warning: Index creation failed: {str(e)}")

        print("✅ Indexes created")

        # Verify migration
        print("\n🔍 Verifying migration...")
        verify_simple(old_cursor, new_cursor, new_conn)

        # Close connections
        old_cursor.close()
        old_conn.close()
        new_cursor.close()
        new_conn.close()

        print("\n🎉 Migration completed successfully!")
        print("=" * 50)

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def migrate_table_simple(old_cursor, new_cursor, new_conn, table_name):
    """Migrate data for a single table"""
    print(f"  Migrating {table_name}...")

    try:
        # Check if transaction is in a failed state and rollback if needed
        if new_conn.status != psycopg2.extensions.STATUS_READY:
            print(f"    Rolling back failed transaction...")
            new_conn.rollback()

        # Get count
        old_cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        result = old_cursor.fetchone()
        count = result["count"]  # RealDictCursor returns dict-like objects

        if count == 0:
            print(f"    No data in {table_name}")
            return

        print(f"    Found {count} rows to migrate...")

        # Get all data
        old_cursor.execute(f"SELECT * FROM {table_name}")
        rows = old_cursor.fetchall()

        # Get column names
        column_names = [desc[0] for desc in old_cursor.description]
        print(f"    Columns: {', '.join(column_names)}")

        # Clear existing data
        new_cursor.execute(f"DELETE FROM {table_name}")

        # Insert data
        placeholders = ", ".join(["%s"] * len(column_names))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"

        data_rows = []
        for row in rows:
            # Convert RealDictRow to tuple in the correct column order
            data_rows.append(tuple(row[col] for col in column_names))

        new_cursor.executemany(insert_sql, data_rows)
        new_conn.commit()

        print(f"    ✅ Migrated {len(data_rows)} rows")

    except Exception as e:
        print(f"    ❌ Failed to migrate {table_name}: {str(e)}")
        try:
            new_conn.rollback()
            print(f"    Rolled back transaction for {table_name}")
        except:
            pass
        import traceback

        traceback.print_exc()


def verify_simple(old_cursor, new_cursor, new_conn):
    """Simple verification"""
    print("  Comparing row counts...")

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
    for table in tables:
        try:
            old_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            old_count = old_cursor.fetchone()["count"]

            new_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            new_count = new_cursor.fetchone()[0]  # Regular cursor returns tuple

            if old_count == new_count:
                print(f"    ✅ {table}: {old_count} rows (match)")
            else:
                print(f"    ❌ {table}: old={old_count}, new={new_count} (mismatch)")
                all_match = False
        except Exception as e:
            print(f"    ❌ {table}: Error checking counts - {str(e)}")
            all_match = False

    return all_match


if __name__ == "__main__":
    simple_migrate()
