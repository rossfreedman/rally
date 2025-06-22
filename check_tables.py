#!/usr/bin/env python3
import os
import sys

sys.path.append(".")
import psycopg2

from database_config import parse_db_url

try:
    params = parse_db_url("postgresql://postgres:postgres@localhost:5432/rally")
    conn = psycopg2.connect(**params)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        )
        tables = [row[0] for row in cursor.fetchall()]
        print("Available tables:")
        for table in tables:
            print(f"  - {table}")

        # Also get row counts
        print("\nTable row counts:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} rows")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
