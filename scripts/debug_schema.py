#!/usr/bin/env python3
import psycopg2
from psycopg2.extras import RealDictCursor

# Test local connection
print("=== Testing Local Database ===")
try:
    local_conn = psycopg2.connect("postgresql://localhost:5432/rally")
    cursor = local_conn.cursor()  # Use regular cursor for EXISTS query
    cursor.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'player_availability')"
    )
    exists = cursor.fetchone()[0]
    print(f"Local player_availability table exists: {exists}")

    if exists:
        cursor = local_conn.cursor(
            cursor_factory=RealDictCursor
        )  # Use RealDictCursor for column queries
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'player_availability' ORDER BY ordinal_position"
        )
        columns = cursor.fetchall()
        print(f'Local columns: {[col["column_name"] for col in columns]}')

    local_conn.close()
except Exception as e:
    print(f"Local connection error: {e}")
    import traceback

    traceback.print_exc()

print("\n=== Testing Railway Database ===")
# Test Railway connection
try:
    railway_conn = psycopg2.connect(
        "postgresql://postgres:ihxpdgQMcXGoMCNvYqzWWmidKTnkdsoM@metro.proxy.rlwy.net:19439/railway",
        sslmode="require",
    )
    cursor = railway_conn.cursor()  # Use regular cursor for EXISTS query
    cursor.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'player_availability')"
    )
    exists = cursor.fetchone()[0]
    print(f"Railway player_availability table exists: {exists}")

    if exists:
        cursor = railway_conn.cursor(
            cursor_factory=RealDictCursor
        )  # Use RealDictCursor for column queries
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'player_availability' ORDER BY ordinal_position"
        )
        columns = cursor.fetchall()
        print(f'Railway columns: {[col["column_name"] for col in columns]}')

    railway_conn.close()
except Exception as e:
    print(f"Railway connection error: {e}")
    import traceback

    traceback.print_exc()
