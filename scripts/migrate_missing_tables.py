#!/usr/bin/env python3
"""
Migration script to copy missing tables from local to Railway PostgreSQL
Focuses on: player_history and user_player_associations
"""

import os
import sys
from urllib.parse import urlparse

import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"


def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",
        "connect_timeout": 10,
    }
    return psycopg2.connect(**conn_params)


def check_table_structure(conn, table_name):
    """Check the actual structure of a table"""
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
    """
    )
    return cursor.fetchall()


def migrate_player_history(local_conn, railway_conn):
    """Migrate player_history table from local to Railway"""
    print("📊 MIGRATING PLAYER_HISTORY TABLE")
    print("-" * 50)

    local_cursor = local_conn.cursor()
    railway_cursor = railway_conn.cursor()

    # Check current count on Railway
    railway_cursor.execute("SELECT COUNT(*) FROM player_history")
    current_count = railway_cursor.fetchone()[0]
    print(f"  Current Railway records: {current_count:,}")

    # Get total from local
    local_cursor.execute("SELECT COUNT(*) FROM player_history")
    total_local = local_cursor.fetchone()[0]
    print(f"  Local records to migrate: {total_local:,}")

    if current_count > 0:
        print(f"  🗑️  Clearing existing Railway data...")
        railway_cursor.execute("TRUNCATE TABLE player_history CASCADE")
        railway_conn.commit()

    # Get column structure to ensure proper mapping
    print(f"  📋 Checking table structure...")
    local_structure = check_table_structure(local_conn, "player_history")
    print(f"     Local columns: {[col[0] for col in local_structure]}")

    # Migrate in batches
    batch_size = 1000
    offset = 0
    migrated_count = 0

    print(f"  🚛 Starting migration in batches of {batch_size:,}...")

    while offset < total_local:
        # Fetch batch from local
        local_cursor.execute(
            f"""
            SELECT id, player_id, league_id, series, date, end_pti, created_at
            FROM player_history 
            ORDER BY id 
            LIMIT {batch_size} OFFSET {offset}
        """
        )
        batch_rows = local_cursor.fetchall()

        if not batch_rows:
            break

        # Insert batch to Railway (excluding id to let it auto-increment)
        insert_sql = """
            INSERT INTO player_history (player_id, league_id, series, date, end_pti, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Remove the id column from each row
        batch_data = [
            (row[1], row[2], row[3], row[4], row[5], row[6]) for row in batch_rows
        ]

        railway_cursor.executemany(insert_sql, batch_data)
        migrated_count += len(batch_rows)

        if migrated_count % 5000 == 0 or offset + batch_size >= total_local:
            print(f"    ✅ Migrated {migrated_count:,}/{total_local:,} records")

        offset += batch_size

    railway_conn.commit()

    # Verify final count
    railway_cursor.execute("SELECT COUNT(*) FROM player_history")
    final_count = railway_cursor.fetchone()[0]
    print(f"  ✅ Migration complete: {final_count:,} records in Railway")

    return migrated_count


def migrate_user_player_associations(local_conn, railway_conn):
    """Migrate user_player_associations table with ID mapping"""
    print("\n👥 MIGRATING USER_PLAYER_ASSOCIATIONS TABLE")
    print("-" * 50)

    local_cursor = local_conn.cursor()
    railway_cursor = railway_conn.cursor()

    # Check current count on Railway
    railway_cursor.execute("SELECT COUNT(*) FROM user_player_associations")
    current_count = railway_cursor.fetchone()[0]
    print(f"  Current Railway records: {current_count:,}")

    # Get associations from local
    local_cursor.execute("SELECT COUNT(*) FROM user_player_associations")
    total_local = local_cursor.fetchone()[0]
    print(f"  Local records to migrate: {total_local:,}")

    if current_count > 0:
        print(f"  🗑️  Clearing existing Railway data...")
        railway_cursor.execute("TRUNCATE TABLE user_player_associations CASCADE")
        railway_conn.commit()

    if total_local == 0:
        print("  📭 No local associations to migrate")
        return 0

    # Get user mappings (local_id -> railway_id) by email
    print("  🔗 Creating user ID mappings...")
    local_cursor.execute("SELECT id, email FROM users")
    local_users = {email: local_id for local_id, email in local_cursor.fetchall()}

    railway_cursor.execute("SELECT id, email FROM users")
    railway_users = {
        email: railway_id for railway_id, email in railway_cursor.fetchall()
    }

    # Get player mappings (local_id -> railway_id) by tenniscores_player_id
    print("  🔗 Creating player ID mappings...")
    local_cursor.execute(
        "SELECT id, tenniscores_player_id FROM players WHERE tenniscores_player_id IS NOT NULL"
    )
    local_players = {tc_id: local_id for local_id, tc_id in local_cursor.fetchall()}

    railway_cursor.execute(
        "SELECT id, tenniscores_player_id FROM players WHERE tenniscores_player_id IS NOT NULL"
    )
    railway_players = {
        tc_id: railway_id for railway_id, tc_id in railway_cursor.fetchall()
    }

    # Get local associations
    local_cursor.execute(
        """
        SELECT upa.user_id, upa.player_id, upa.is_primary, upa.created_at,
               u.email, p.tenniscores_player_id
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        JOIN players p ON upa.player_id = p.id
    """
    )
    local_associations = local_cursor.fetchall()

    migrated_count = 0
    skipped_count = 0

    print(f"  🚛 Processing {len(local_associations)} associations...")

    for (
        local_user_id,
        local_player_id,
        is_primary,
        created_at,
        user_email,
        tc_player_id,
    ) in local_associations:
        # Map user ID
        if user_email not in railway_users:
            print(f"    ⚠️  Skipping: User {user_email} not found in Railway")
            skipped_count += 1
            continue

        # Map player ID
        if not tc_player_id or tc_player_id not in railway_players:
            print(f"    ⚠️  Skipping: Player {tc_player_id} not found in Railway")
            skipped_count += 1
            continue

        railway_user_id = railway_users[user_email]
        railway_player_id = railway_players[tc_player_id]

        # Insert association
        try:
            railway_cursor.execute(
                """
                INSERT INTO user_player_associations (user_id, player_id, is_primary, created_at)
                VALUES (%s, %s, %s, %s)
            """,
                (railway_user_id, railway_player_id, is_primary, created_at),
            )
            migrated_count += 1

            primary_text = " (PRIMARY)" if is_primary else ""
            print(
                f"    ✅ Migrated: {user_email} -> Player ID {railway_player_id}{primary_text}"
            )

        except Exception as e:
            print(f"    ❌ Error migrating association: {e}")
            skipped_count += 1

    railway_conn.commit()

    # Verify final count
    railway_cursor.execute("SELECT COUNT(*) FROM user_player_associations")
    final_count = railway_cursor.fetchone()[0]
    print(f"  ✅ Migration complete: {final_count:,} records in Railway")
    print(f"  📊 Migrated: {migrated_count}, Skipped: {skipped_count}")

    return migrated_count


def main():
    """Main migration function"""
    print("🚀 MIGRATING MISSING TABLES TO RAILWAY")
    print("=" * 60)
    print("Target tables: player_history, user_player_associations")
    print("=" * 60)

    try:
        # Connect to both databases
        with get_db() as local_conn:
            railway_conn = connect_to_railway()

            try:
                # Migrate player_history
                ph_count = migrate_player_history(local_conn, railway_conn)

                # Migrate user_player_associations
                upa_count = migrate_user_player_associations(local_conn, railway_conn)

                # Final summary
                print(f"\n" + "=" * 60)
                print(f"✅ MIGRATION COMPLETED SUCCESSFULLY!")
                print(f"📊 RESULTS:")
                print(f"  • player_history: {ph_count:,} records migrated")
                print(f"  • user_player_associations: {upa_count:,} records migrated")
                print(f"  • Total: {ph_count + upa_count:,} records")
                print(f"\n🌐 Test your application at: https://www.lovetorally.com")

                return True

            finally:
                railway_conn.close()

    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
