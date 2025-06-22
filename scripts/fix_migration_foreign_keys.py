#!/usr/bin/env python3
"""
Fix foreign key mapping issues and complete the migration
"""

import logging
import os
import sys
from urllib.parse import urlparse

import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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


def create_club_mapping():
    """Create mapping between local and Railway club names to IDs"""
    logger.info("🔍 Creating club ID mapping...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Get local clubs
        local_cursor.execute("SELECT id, name FROM clubs")
        local_clubs = {name: local_id for local_id, name in local_cursor.fetchall()}

        # Get Railway clubs
        railway_cursor.execute("SELECT id, name FROM clubs")
        railway_clubs = {
            name: railway_id for railway_id, name in railway_cursor.fetchall()
        }

        # Create mapping for common clubs
        club_mapping = {}
        missing_clubs = []

        for name, local_id in local_clubs.items():
            if name in railway_clubs:
                club_mapping[local_id] = railway_clubs[name]
                logger.info(
                    f"  ✅ {name}: local_id {local_id} → railway_id {railway_clubs[name]}"
                )
            else:
                missing_clubs.append((local_id, name))
                logger.warning(
                    f"  ❌ Missing in Railway: {name} (local_id: {local_id})"
                )

        railway_conn.close()
        return club_mapping, missing_clubs


def create_series_mapping():
    """Create mapping between local and Railway series names to IDs"""
    logger.info("\n🔍 Creating series ID mapping...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Get local series
        local_cursor.execute("SELECT id, name FROM series")
        local_series = {name: local_id for local_id, name in local_cursor.fetchall()}

        # Get Railway series
        railway_cursor.execute("SELECT id, name FROM series")
        railway_series = {
            name: railway_id for railway_id, name in railway_cursor.fetchall()
        }

        # Create mapping for common series
        series_mapping = {}
        missing_series = []

        for name, local_id in local_series.items():
            if name in railway_series:
                series_mapping[local_id] = railway_series[name]
                logger.info(
                    f"  ✅ {name}: local_id {local_id} → railway_id {railway_series[name]}"
                )
            else:
                missing_series.append((local_id, name))
                logger.warning(
                    f"  ❌ Missing in Railway: {name} (local_id: {local_id})"
                )

        railway_conn.close()
        return series_mapping, missing_series


def add_missing_clubs_to_railway(missing_clubs):
    """Add missing clubs to Railway database"""
    if not missing_clubs:
        return {}

    logger.info(f"\n🔧 Adding {len(missing_clubs)} missing clubs to Railway...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        new_club_mapping = {}

        for local_id, club_name in missing_clubs:
            # Get full club data from local (excluding id)
            local_cursor.execute(
                """
                SELECT name, updated_at 
                FROM clubs 
                WHERE id = %s
            """,
                (local_id,),
            )
            club_data = local_cursor.fetchone()

            if club_data:
                name, updated_at = club_data

                # Insert into Railway without specifying id (let it auto-generate)
                railway_cursor.execute(
                    """
                    INSERT INTO clubs (name, updated_at) 
                    VALUES (%s, %s) 
                    RETURNING id
                """,
                    (name, updated_at),
                )

                new_railway_id = railway_cursor.fetchone()[0]
                new_club_mapping[local_id] = new_railway_id

                logger.info(
                    f"  ✅ Added {name}: local_id {local_id} → new railway_id {new_railway_id}"
                )

        railway_conn.commit()
        railway_conn.close()

        return new_club_mapping


def add_missing_series_to_railway(missing_series):
    """Add missing series to Railway database"""
    if not missing_series:
        return {}

    logger.info(f"\n🔧 Adding {len(missing_series)} missing series to Railway...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        new_series_mapping = {}

        for local_id, series_name in missing_series:
            # Get full series data from local (excluding id)
            local_cursor.execute(
                """
                SELECT name, updated_at 
                FROM series 
                WHERE id = %s
            """,
                (local_id,),
            )
            series_data = local_cursor.fetchone()

            if series_data:
                name, updated_at = series_data

                # Insert into Railway without specifying id (let it auto-generate)
                railway_cursor.execute(
                    """
                    INSERT INTO series (name, updated_at) 
                    VALUES (%s, %s) 
                    RETURNING id
                """,
                    (name, updated_at),
                )

                new_railway_id = railway_cursor.fetchone()[0]
                new_series_mapping[local_id] = new_railway_id

                logger.info(
                    f"  ✅ Added {name}: local_id {local_id} → new railway_id {new_railway_id}"
                )

        railway_conn.commit()
        railway_conn.close()

        return new_series_mapping


def migrate_players_with_mapping(club_mapping, series_mapping):
    """Migrate players with proper ID mapping"""
    logger.info(f"\n🔄 Migrating players with corrected foreign key mappings...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Get all players from local
        local_cursor.execute("SELECT * FROM players ORDER BY id")
        players = local_cursor.fetchall()

        # Get column names
        local_cursor.execute("SELECT * FROM players LIMIT 1")
        columns = [desc[0] for desc in local_cursor.description]

        # Exclude 'id' column to let Railway auto-generate new IDs
        columns_without_id = [col for col in columns if col != "id"]

        migrated_count = 0
        skipped_count = 0

        for player_row in players:
            player_dict = dict(zip(columns, player_row))

            # Map foreign keys
            original_club_id = player_dict["club_id"]
            original_series_id = player_dict["series_id"]

            # Update club_id if mapping exists
            if original_club_id in club_mapping:
                player_dict["club_id"] = club_mapping[original_club_id]
            elif original_club_id is not None:
                logger.warning(
                    f"  ⚠️  Skipping player {player_dict['first_name']} {player_dict['last_name']}: unmapped club_id {original_club_id}"
                )
                skipped_count += 1
                continue

            # Update series_id if mapping exists
            if original_series_id in series_mapping:
                player_dict["series_id"] = series_mapping[original_series_id]
            elif original_series_id is not None:
                logger.warning(
                    f"  ⚠️  Skipping player {player_dict['first_name']} {player_dict['last_name']}: unmapped series_id {original_series_id}"
                )
                skipped_count += 1
                continue

            # Insert player into Railway (excluding original id)
            try:
                placeholders = ", ".join(["%s"] * len(columns_without_id))
                column_names = ", ".join(columns_without_id)
                values = [player_dict[col] for col in columns_without_id]

                railway_cursor.execute(
                    f"""
                    INSERT INTO players ({column_names}) 
                    VALUES ({placeholders})
                """,
                    values,
                )

                migrated_count += 1

                if migrated_count % 500 == 0:
                    logger.info(f"    ✅ Migrated {migrated_count} players...")

            except Exception as e:
                logger.error(
                    f"  ❌ Failed to migrate player {player_dict['first_name']} {player_dict['last_name']}: {e}"
                )
                skipped_count += 1

        railway_conn.commit()
        railway_conn.close()

        logger.info(
            f"  ✅ Players migration completed: {migrated_count} migrated, {skipped_count} skipped"
        )
        return migrated_count


def complete_remaining_migrations():
    """Complete player_history and user_player_associations migrations"""
    logger.info(f"\n🔄 Completing remaining table migrations...")

    # Now that players exist, retry player_history and user_player_associations
    tables_to_retry = ["player_history", "user_player_associations"]

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        for table_name in tables_to_retry:
            try:
                local_cursor = local_conn.cursor()
                railway_cursor = railway_conn.cursor()

                # Get total count
                local_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                total_rows = local_cursor.fetchone()[0]

                if total_rows == 0:
                    logger.info(f"  📭 {table_name}: No data to migrate")
                    continue

                logger.info(f"  📊 {table_name}: Migrating {total_rows} records...")

                # Get column names
                local_cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                columns = [desc[0] for desc in local_cursor.description]

                # Migrate in batches
                batch_size = 1000
                offset = 0
                migrated_count = 0

                while offset < total_rows:
                    # Fetch batch
                    local_cursor.execute(
                        f"""
                        SELECT * FROM {table_name} 
                        ORDER BY {columns[0]} 
                        LIMIT {batch_size} OFFSET {offset}
                    """
                    )
                    batch_rows = local_cursor.fetchall()

                    if not batch_rows:
                        break

                    # Insert batch
                    placeholders = ", ".join(["%s"] * len(columns))
                    column_names = ", ".join(columns)

                    insert_sql = f"""
                        INSERT INTO {table_name} ({column_names}) 
                        VALUES ({placeholders})
                        ON CONFLICT DO NOTHING
                    """

                    railway_cursor.executemany(insert_sql, batch_rows)
                    migrated_count += len(batch_rows)

                    logger.info(
                        f"    ✅ Migrated {migrated_count}/{total_rows} records"
                    )
                    offset += batch_size

                railway_conn.commit()
                logger.info(
                    f"  ✅ {table_name}: Migration completed ({migrated_count} records)"
                )

            except Exception as e:
                logger.error(f"  ❌ {table_name}: Migration failed - {e}")

        railway_conn.close()


def main():
    """Fix foreign key issues and complete migration"""
    logger.info("🔧 FIXING FOREIGN KEY ISSUES & COMPLETING MIGRATION")
    logger.info("=" * 80)

    # Step 1: Create mappings
    club_mapping, missing_clubs = create_club_mapping()
    series_mapping, missing_series = create_series_mapping()

    # Step 2: Add missing clubs/series to Railway
    new_club_mapping = add_missing_clubs_to_railway(missing_clubs)
    new_series_mapping = add_missing_series_to_railway(missing_series)

    # Step 3: Combine mappings
    complete_club_mapping = {**club_mapping, **new_club_mapping}
    complete_series_mapping = {**series_mapping, **new_series_mapping}

    logger.info(f"\n📊 MAPPING SUMMARY:")
    logger.info(f"  • Club mappings: {len(complete_club_mapping)}")
    logger.info(f"  • Series mappings: {len(complete_series_mapping)}")

    # Step 4: Migrate players with corrected mappings
    player_count = migrate_players_with_mapping(
        complete_club_mapping, complete_series_mapping
    )

    # Step 5: Complete remaining migrations
    complete_remaining_migrations()

    logger.info(f"\n✅ MIGRATION FIX COMPLETED!")
    logger.info(
        f"🎯 Railway now has your complete dataset with proper foreign key relationships"
    )

    return player_count > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
