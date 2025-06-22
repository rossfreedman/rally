#!/usr/bin/env python3
"""
Check if local and Railway databases have the same schema for player_availability table
"""

import os
import sys
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()


def get_table_schema(cursor, table_name):
    """Get detailed schema for a table"""
    cursor.execute(
        """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position;
    """,
        (table_name,),
    )
    return cursor.fetchall()


def get_table_indexes(cursor, table_name):
    """Get indexes for a table"""
    cursor.execute(
        """
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes 
        WHERE tablename = %s AND schemaname = 'public'
        ORDER BY indexname;
    """,
        (table_name,),
    )
    return cursor.fetchall()


def connect_to_database(db_type="local"):
    """Connect to database based on type"""
    if db_type == "local":
        # Connect to local database
        url = "postgresql://localhost:5432/rally"
        print(f"🔗 Connecting to LOCAL database: localhost:5432/rally")
    else:
        # Connect to Railway database - use the actual Railway URL
        url = "postgresql://postgres:ihxpdgQMcXGoMCNvYqzWWmidKTnkdsoM@metro.proxy.rlwy.net:19439/railway"
        print(f"🔗 Connecting to RAILWAY database: metro.proxy.rlwy.net:19439")

    try:
        # Parse URL
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        sslmode = (
            "require"
            if (
                "railway.app" in hostname
                or "rlwy.net" in hostname
                or "railway.internal" in hostname
            )
            else "prefer"
        )

        conn = psycopg2.connect(url, sslmode=sslmode, connect_timeout=30)
        print(f"✅ Connected to {db_type} database successfully")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to {db_type} database: {str(e)}")
        return None


def check_availability_schema():
    """Check player_availability table schema between local and Railway"""
    print("=== Player Availability Table Schema Comparison ===\n")

    # Connect to both databases
    print("1. Connecting to databases...")
    local_conn = connect_to_database("local")
    if not local_conn:
        print("❌ Cannot proceed without local database connection")
        return False

    railway_conn = connect_to_database("railway")
    if not railway_conn:
        print("❌ Cannot proceed without Railway database connection")
        local_conn.close()
        return False

    try:
        local_cursor = local_conn.cursor(cursor_factory=RealDictCursor)
        railway_cursor = railway_conn.cursor(cursor_factory=RealDictCursor)

        print("\n2. Checking if player_availability table exists...")

        # Check if table exists in both databases
        for cursor, db_name in [(local_cursor, "LOCAL"), (railway_cursor, "RAILWAY")]:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'player_availability'
                );
            """
            )
            exists = cursor.fetchone()[0]
            print(f"  - {db_name}: {'✅ EXISTS' if exists else '❌ MISSING'}")

            if not exists:
                print(f"❌ player_availability table missing in {db_name} database!")
                return False

        print("\n3. Comparing table schemas...")

        # Get schemas for both databases
        local_schema = get_table_schema(local_cursor, "player_availability")
        railway_schema = get_table_schema(railway_cursor, "player_availability")

        print("\n📋 LOCAL DATABASE - player_availability schema:")
        for col in local_schema:
            nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
            default = (
                f" DEFAULT {col['column_default']}" if col["column_default"] else ""
            )
            print(f"  {col['column_name']}: {col['data_type']} {nullable}{default}")

        print("\n📋 RAILWAY DATABASE - player_availability schema:")
        for col in railway_schema:
            nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
            default = (
                f" DEFAULT {col['column_default']}" if col["column_default"] else ""
            )
            print(f"  {col['column_name']}: {col['data_type']} {nullable}{default}")

        # Compare schemas
        print("\n4. Analyzing differences...")

        local_cols = {col["column_name"]: col for col in local_schema}
        railway_cols = {col["column_name"]: col for col in railway_schema}

        only_local = set(local_cols.keys()) - set(railway_cols.keys())
        only_railway = set(railway_cols.keys()) - set(local_cols.keys())

        schema_issues = []

        if only_local:
            schema_issues.append(f"Columns only in LOCAL: {', '.join(only_local)}")
            print(f"\n❌ Columns only in LOCAL:")
            for col_name in only_local:
                col = local_cols[col_name]
                nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                print(f"    - {col_name}: {col['data_type']} {nullable}")

        if only_railway:
            schema_issues.append(f"Columns only in RAILWAY: {', '.join(only_railway)}")
            print(f"\n❌ Columns only in RAILWAY:")
            for col_name in only_railway:
                col = railway_cols[col_name]
                nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                print(f"    - {col_name}: {col['data_type']} {nullable}")

        # Check for differences in common columns
        common_cols = set(local_cols.keys()) & set(railway_cols.keys())
        differences = []

        for col_name in common_cols:
            local_col = local_cols[col_name]
            railway_col = railway_cols[col_name]

            if (
                local_col["data_type"] != railway_col["data_type"]
                or local_col["is_nullable"] != railway_col["is_nullable"]
                or local_col["column_default"] != railway_col["column_default"]
            ):
                differences.append(
                    {
                        "column": col_name,
                        "local": f"{local_col['data_type']} {'NULL' if local_col['is_nullable'] == 'YES' else 'NOT NULL'} DEFAULT {local_col['column_default'] or 'None'}",
                        "railway": f"{railway_col['data_type']} {'NULL' if railway_col['is_nullable'] == 'YES' else 'NOT NULL'} DEFAULT {railway_col['column_default'] or 'None'}",
                    }
                )

        if differences:
            schema_issues.append(f"Different column definitions: {len(differences)}")
            print(f"\n❌ Differences in common columns:")
            for diff in differences:
                print(f"    - {diff['column']}:")
                print(f"      Local:   {diff['local']}")
                print(f"      Railway: {diff['railway']}")

        # Check indexes
        print("\n5. Comparing indexes...")
        local_indexes = get_table_indexes(local_cursor, "player_availability")
        railway_indexes = get_table_indexes(railway_cursor, "player_availability")

        print(f"\n📋 LOCAL INDEXES ({len(local_indexes)}):")
        for idx in local_indexes:
            print(f"  - {idx['indexname']}")

        print(f"\n📋 RAILWAY INDEXES ({len(railway_indexes)}):")
        for idx in railway_indexes:
            print(f"  - {idx['indexname']}")

        # Final assessment
        print(f"\n6. Final Assessment:")

        if schema_issues:
            print(f"\n❌ SCHEMAS ARE NOT IDENTICAL")
            for issue in schema_issues:
                print(f"  - {issue}")
            print(f"\n🔧 RECOMMENDED ACTIONS:")
            print(f"  1. Run schema migration/sync scripts")
            print(f"  2. Check if availability functionality uses correct column names")
            print(f"  3. Test availability updates on both environments")
            return False
        else:
            print(f"\n✅ SCHEMAS ARE IDENTICAL")
            print(f"  - Column definitions match")
            print(f"  - Data types are consistent")
            print(f"  - Nullability constraints match")
            print(f"\n🎉 Your availability functionality should work consistently!")
            return True

    except Exception as e:
        print(f"❌ Error during schema comparison: {str(e)}")
        return False
    finally:
        local_conn.close()
        railway_conn.close()


if __name__ == "__main__":
    print("Checking Rally Availability Table Schema Sync")
    print("=" * 50)

    success = check_availability_schema()

    if success:
        print(f"\n✅ Schema check completed - databases are in sync!")
    else:
        print(f"\n❌ Schema differences detected - see recommendations above")
        sys.exit(1)
