#!/usr/bin/env python3
"""
Sync data from local database to Railway database.
Schema should already be aligned via Alembic migrations.
"""

import os
import time

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def connect_local():
    """Connect to local database"""
    return psycopg2.connect(
        dbname="rally",
        user="postgres",
        password="password",
        host="localhost",
        port=5432,
        sslmode="prefer",
    )


def connect_railway():
    """Connect to Railway database using environment variables"""
    # Get Railway database URL from environment
    railway_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")

    if not railway_url:
        print("❌ No Railway database URL found!")
        print("Set DATABASE_PUBLIC_URL or DATABASE_URL environment variable.")
        return None

    # Convert postgres:// to postgresql://
    if railway_url.startswith("postgres://"):
        railway_url = railway_url.replace("postgres://", "postgresql://", 1)

    import urllib.parse as urlparse

    parsed = urlparse.urlparse(railway_url)

    return psycopg2.connect(
        dbname=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        sslmode="require",
    )


def clear_table_data(railway_conn, table_name):
    """Clear data from a Railway table"""
    try:
        cur = railway_conn.cursor()
        cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        railway_conn.commit()
        print(f"   ✅ Cleared {table_name}")
        cur.close()
    except Exception as e:
        print(f"   ⚠️  Could not clear {table_name}: {e}")


def transfer_table_data(local_conn, railway_conn, table_name, id_column=None):
    """Transfer data from local to Railway for a specific table"""
    try:
        local_cur = local_conn.cursor()
        railway_cur = railway_conn.cursor()

        # Get column names
        local_cur.execute(
            f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position
        """
        )
        columns = [row[0] for row in local_cur.fetchall()]

        if not columns:
            print(f"   ⚠️  No columns found for {table_name}")
            return 0

        # Get all data from local
        column_list = ", ".join(columns)
        local_cur.execute(f"SELECT {column_list} FROM {table_name}")
        rows = local_cur.fetchall()

        if not rows:
            print(f"   📭 {table_name}: No data to transfer")
            return 0

        # Insert into Railway
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"

        # Insert in batches
        batch_size = 1000
        total_inserted = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            railway_cur.executemany(insert_sql, batch)
            total_inserted += len(batch)

            if len(rows) > batch_size:
                print(
                    f"      📦 Inserted batch {i//batch_size + 1}: {len(batch)} records"
                )

        railway_conn.commit()

        # Fix sequence if table has an ID column
        if id_column and total_inserted > 0:
            railway_cur.execute(f"SELECT MAX({id_column}) FROM {table_name}")
            max_id = railway_cur.fetchone()[0]
            if max_id:
                railway_cur.execute(
                    f"""
                    SELECT setval(pg_get_serial_sequence('{table_name}', '{id_column}'), {max_id}, true)
                """
                )
                railway_conn.commit()

        print(f"   ✅ {table_name}: {total_inserted:,} records transferred")

        local_cur.close()
        railway_cur.close()
        return total_inserted

    except Exception as e:
        print(f"   ❌ Error transferring {table_name}: {e}")
        return 0


def main():
    print("🚀 SYNCING DATA: LOCAL → RAILWAY")
    print("=" * 50)

    # Connect to databases
    try:
        local_conn = connect_local()
        print("✅ Connected to local database")
    except Exception as e:
        print(f"❌ Could not connect to local database: {e}")
        return False

    try:
        railway_conn = connect_railway()
        if not railway_conn:
            return False
        print("✅ Connected to Railway database")
    except Exception as e:
        print(f"❌ Could not connect to Railway database: {e}")
        return False

    # Tables to transfer in dependency order
    tables_to_sync = [
        ("leagues", "id"),
        ("clubs", "id"),
        ("series", "id"),
        ("users", "id"),
        ("players", "id"),
        ("player_history", None),  # No single ID column
        ("user_player_associations", None),
        ("match_scores", "id"),
        ("schedule", "id"),
        ("series_stats", "id"),
        ("player_availability", "id"),
        ("user_activity_logs", "id"),
        ("user_instructions", "id"),
        ("series_leagues", None),
        ("club_leagues", None),
    ]

    print("\n🗑️  Clearing Railway data...")
    # Clear in reverse order to handle foreign keys
    for table_name, _ in reversed(tables_to_sync):
        clear_table_data(railway_conn, table_name)

    print("\n📥 Transferring data...")
    total_transferred = 0

    for table_name, id_column in tables_to_sync:
        transferred = transfer_table_data(
            local_conn, railway_conn, table_name, id_column
        )
        total_transferred += transferred
        time.sleep(0.1)  # Small delay between tables

    print(f"\n✅ DATA SYNC COMPLETE!")
    print(f"📊 Total records transferred: {total_transferred:,}")

    # Verify key tables
    print(f"\n🔍 Verifying Railway data...")
    railway_cur = railway_conn.cursor()

    key_tables = ["users", "players", "match_scores", "leagues"]
    for table in key_tables:
        railway_cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = railway_cur.fetchone()[0]
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {table}: {count:,} records")

    railway_cur.close()
    local_conn.close()
    railway_conn.close()

    print(f"\n🎉 Railway database should now have all data from local!")
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🌐 Try accessing your Railway application now - it should show data!")
    else:
        print(f"\n❌ Data sync failed. Check the errors above.")
