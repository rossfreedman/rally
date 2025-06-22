#!/usr/bin/env python3
from urllib.parse import urlparse

import psycopg2


def test_new_database():
    """Test connection to the new Railway database"""

    # Complete DATABASE_URL provided by user
    new_db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

    parsed = urlparse(new_db_url)

    print(f"🔍 Testing connection to new Rally Database...")
    print(f"Host: {parsed.hostname}")
    print(f"Port: {parsed.port}")
    print(f"Database: {parsed.path[1:]}")
    print(f"User: {parsed.username}")

    try:
        # Test connection
        print(f"\n📡 Attempting connection...")
        conn = psycopg2.connect(new_db_url, connect_timeout=15, sslmode="require")

        cursor = conn.cursor()

        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\n✅ Connection successful!")
        print(f"PostgreSQL version: {version}")

        # Check current database info
        cursor.execute("SELECT current_database(), current_user;")
        db, user_result = cursor.fetchone()
        print(f"Connected to database: {db}")
        print(f"Connected as user: {user_result}")

        # List existing tables
        print("\n📋 Existing tables:")
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        )
        tables = cursor.fetchall()

        if tables:
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("  No tables found (empty database)")

        cursor.close()
        conn.close()

        print(f"\n🎉 Successfully connected!")
        return True, new_db_url

    except psycopg2.OperationalError as e:
        if "authentication" in str(e).lower():
            print(f"❌ Authentication failed")
        elif "timeout" in str(e).lower():
            print(f"❌ Connection timeout")
        else:
            print(f"❌ Connection failed: {str(e)}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False, None


if __name__ == "__main__":
    test_new_database()
