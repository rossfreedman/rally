#!/usr/bin/env python3
"""
Migration script with proper ID mapping from local to Railway PostgreSQL
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


def create_player_id_mapping(local_conn, railway_conn):
    """Create mapping from local player IDs to Railway player IDs"""
    print("🗺️  CREATING PLAYER ID MAPPING")
    print("-" * 50)

    local_cursor = local_conn.cursor()
    railway_cursor = railway_conn.cursor()

    # Local: tenniscores_player_id -> local_id
    local_cursor.execute(
        "SELECT tenniscores_player_id, id FROM players WHERE tenniscores_player_id IS NOT NULL"
    )
    local_tc_to_id = dict(local_cursor.fetchall())
    print(f"  Local players with TC IDs: {len(local_tc_to_id):,}")

    # Railway: tenniscores_player_id -> railway_id
    railway_cursor.execute(
        "SELECT tenniscores_player_id, id FROM players WHERE tenniscores_player_id IS NOT NULL"
    )
    railway_tc_to_id = dict(railway_cursor.fetchall())
    print(f"  Railway players with TC IDs: {len(railway_tc_to_id):,}")

    # Create local_id -> railway_id mapping
    local_to_railway_mapping = {}
    unmapped_count = 0

    for tc_id in local_tc_to_id:
        local_id = local_tc_to_id[tc_id]
        if tc_id in railway_tc_to_id:
            railway_id = railway_tc_to_id[tc_id]
            local_to_railway_mapping[local_id] = railway_id
        else:
            unmapped_count += 1

    print(f"  Successfully mapped players: {len(local_to_railway_mapping):,}")
    print(f"  Unmapped players: {unmapped_count:,}")

    return local_to_railway_mapping


def migrate_player_history_with_mapping(local_conn, railway_conn, player_mapping):
    """Migrate player_history table with proper ID mapping"""
    print("\n📊 MIGRATING PLAYER_HISTORY TABLE WITH ID MAPPING")
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

    # Check how many records can be mapped
    local_cursor.execute(
        """
        SELECT COUNT(*) FROM player_history 
        WHERE player_id IN %s
    """,
        (tuple(player_mapping.keys()),),
    )
    mappable_count = local_cursor.fetchone()[0]
    print(f"  Records that can be mapped: {mappable_count:,}/{total_local:,}")

    # Migrate in batches
    batch_size = 1000
    offset = 0
    migrated_count = 0
    skipped_count = 0

    print(f"  🚛 Starting migration in batches of {batch_size:,}...")

    while offset < total_local:
        # Fetch batch from local with only mappable player_ids
        local_cursor.execute(
            f"""
            SELECT id, player_id, league_id, series, date, end_pti, created_at
            FROM player_history 
            WHERE player_id IN %s
            ORDER BY id 
            LIMIT {batch_size} OFFSET {offset}
        """,
            (tuple(player_mapping.keys()),),
        )
        batch_rows = local_cursor.fetchall()

        if not batch_rows:
            # Check if there are more records to process
            local_cursor.execute(
                f"""
                SELECT COUNT(*) FROM player_history 
                WHERE id > (SELECT COALESCE(MAX(id), 0) FROM (
                    SELECT id FROM player_history 
                    WHERE player_id IN %s 
                    ORDER BY id 
                    LIMIT {offset}
                ) subq)
            """,
                (tuple(player_mapping.keys()),),
            )
            remaining = local_cursor.fetchone()[0]
            if remaining == 0:
                break
            else:
                offset += batch_size
                continue

        # Process batch with ID mapping
        batch_data = []
        for row in batch_rows:
            local_player_id = row[1]
            if local_player_id in player_mapping:
                railway_player_id = player_mapping[local_player_id]
                # Map: player_id, league_id, series, date, end_pti, created_at
                mapped_row = (railway_player_id, row[2], row[3], row[4], row[5], row[6])
                batch_data.append(mapped_row)
            else:
                skipped_count += 1

        if batch_data:
            # Insert batch to Railway
            insert_sql = """
                INSERT INTO player_history (player_id, league_id, series, date, end_pti, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            railway_cursor.executemany(insert_sql, batch_data)
            migrated_count += len(batch_data)

            if migrated_count % 5000 == 0 or offset + batch_size >= mappable_count:
                print(f"    ✅ Migrated {migrated_count:,}/{mappable_count:,} records")

        offset += batch_size

    railway_conn.commit()

    # Verify final count
    railway_cursor.execute("SELECT COUNT(*) FROM player_history")
    final_count = railway_cursor.fetchone()[0]
    print(f"  ✅ Migration complete: {final_count:,} records in Railway")
    print(f"  📊 Migrated: {migrated_count:,}, Skipped: {skipped_count:,}")

    return migrated_count


def migrate_user_player_associations_with_mapping(
    local_conn, railway_conn, player_mapping
):
    """Migrate user_player_associations table with proper ID mapping"""
    print("\n👥 MIGRATING USER_PLAYER_ASSOCIATIONS TABLE WITH ID MAPPING")
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

    # Get user mappings by email
    print("  🔗 Creating user ID mappings...")
    local_cursor.execute("SELECT id, email FROM users")
    local_users = {email: local_id for local_id, email in local_cursor.fetchall()}

    railway_cursor.execute("SELECT id, email FROM users")
    railway_users = {
        email: railway_id for railway_id, email in railway_cursor.fetchall()
    }

    # Get local associations
    local_cursor.execute(
        """
        SELECT upa.user_id, upa.player_id, upa.is_primary, upa.created_at,
               u.email
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
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
    ) in local_associations:
        # Map user ID
        if user_email not in railway_users:
            print(f"    ⚠️  Skipping: User {user_email} not found in Railway")
            skipped_count += 1
            continue

        # Map player ID
        if local_player_id not in player_mapping:
            print(f"    ⚠️  Skipping: Local player ID {local_player_id} not in mapping")
            skipped_count += 1
            continue

        railway_user_id = railway_users[user_email]
        railway_player_id = player_mapping[local_player_id]

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
    print("🚀 MIGRATING MISSING TABLES TO RAILWAY WITH ID MAPPING")
    print("=" * 70)
    print("Target tables: player_history, user_player_associations")
    print("=" * 70)

    try:
        # Connect to both databases
        with get_db() as local_conn:
            railway_conn = connect_to_railway()

            try:
                # Create player ID mapping
                player_mapping = create_player_id_mapping(local_conn, railway_conn)

                if not player_mapping:
                    print("❌ No player mapping available - cannot proceed")
                    return False

                # Migrate player_history with mapping
                ph_count = migrate_player_history_with_mapping(
                    local_conn, railway_conn, player_mapping
                )

                # Migrate user_player_associations with mapping
                upa_count = migrate_user_player_associations_with_mapping(
                    local_conn, railway_conn, player_mapping
                )

                # Final summary
                print(f"\n" + "=" * 70)
                print(f"✅ MIGRATION COMPLETED SUCCESSFULLY!")
                print(f"📊 RESULTS:")
                print(f"  • player_history: {ph_count:,} records migrated")
                print(f"  • user_player_associations: {upa_count:,} records migrated")
                print(f"  • Total: {ph_count + upa_count:,} records")
                print(f"  • Player mappings used: {len(player_mapping):,}")
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
