#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import RealDictCursor


def check_status():
    """Check current migration status"""

    # Database connection strings
    old_db_url = "postgresql://postgres:OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf@trolley.proxy.rlwy.net:34555/railway"
    new_db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

    print("🔍 Checking migration status")
    print("=" * 50)

    try:
        # Connect to both databases
        old_conn = psycopg2.connect(old_db_url)
        new_conn = psycopg2.connect(new_db_url)

        old_cursor = old_conn.cursor(cursor_factory=RealDictCursor)
        new_cursor = new_conn.cursor(cursor_factory=RealDictCursor)

        print("✅ Connected to both databases")

        # Check tables in both databases
        print("\n📋 Tables in OLD database:")
        old_cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """
        )
        old_tables = [row["table_name"] for row in old_cursor.fetchall()]
        for table in old_tables:
            old_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = old_cursor.fetchone()["count"]
            print(f"  {table}: {count} rows")

        print("\n📋 Tables in NEW database:")
        new_cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """
        )
        new_tables = [row["table_name"] for row in new_cursor.fetchall()]
        for table in new_tables:
            new_cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = new_cursor.fetchone()["count"]
            print(f"  {table}: {count} rows")

        # Compare schemas for users table specifically
        print("\n🔍 Comparing USERS table schema:")

        print("\nOLD users table columns:")
        old_cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """
        )
        old_columns = old_cursor.fetchall()
        for col in old_columns:
            print(
                f"  {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})"
            )

        print("\nNEW users table columns:")
        new_cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """
        )
        new_columns = new_cursor.fetchall()
        for col in new_columns:
            print(
                f"  {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})"
            )

        # Close connections
        old_cursor.close()
        old_conn.close()
        new_cursor.close()
        new_conn.close()

        print("\n✅ Status check completed")

    except Exception as e:
        print(f"\n❌ Status check failed: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_status()
