#!/usr/bin/env python3
"""
Add Missing NSFT Clubs to Railway and Re-run Migration
This script adds the 4 missing NSFT clubs to Railway and re-runs the safe migration
"""

import logging
import os
import sys
from datetime import datetime
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


def add_missing_nsft_clubs():
    """Add the missing NSFT clubs to Railway database"""
    logger.info("🏢 Adding missing NSFT clubs to Railway...")

    # The 4 missing NSFT clubs identified in our investigation
    missing_nsft_clubs = [
        {"local_id": 94, "name": "Wilmette", "players": 111},
        {"local_id": 91, "name": "Midtown", "players": 92},
        {"local_id": 93, "name": "Ravinia Green", "players": 51},
        {"local_id": 92, "name": "Old Willow", "players": 35},
    ]

    railway_conn = connect_to_railway()
    railway_cursor = railway_conn.cursor()

    # Fix sequence issue first
    logger.info("  🔧 Fixing clubs sequence...")
    railway_cursor.execute("SELECT MAX(id) FROM clubs")
    max_id = railway_cursor.fetchone()[0]
    railway_cursor.execute(f"SELECT setval('clubs_id_seq', {max_id})")
    logger.info(f"  ✅ Set clubs sequence to {max_id}")

    new_club_mappings = {}
    added_count = 0
    existing_count = 0

    try:
        for club_info in missing_nsft_clubs:
            local_id = club_info["local_id"]
            club_name = club_info["name"]
            expected_players = club_info["players"]

            # Check if club already exists in Railway (exact match)
            railway_cursor.execute("SELECT id FROM clubs WHERE name = %s", (club_name,))
            existing_club = railway_cursor.fetchone()

            # Special case: Check if "Midtown" should map to "Midtown - Chicago"
            if not existing_club and club_name == "Midtown":
                railway_cursor.execute(
                    "SELECT id FROM clubs WHERE name = %s", ("Midtown - Chicago",)
                )
                existing_club = railway_cursor.fetchone()
                if existing_club:
                    logger.info(
                        f"  🔗 Mapping {club_name} to existing 'Midtown - Chicago' (ID: {existing_club[0]})"
                    )

            if existing_club:
                railway_id = existing_club[0]
                logger.info(
                    f"  ✅ {club_name} already exists in Railway (ID: {railway_id})"
                )
                new_club_mappings[local_id] = railway_id
                existing_count += 1
            else:
                # Add the club to Railway
                railway_cursor.execute(
                    """
                    INSERT INTO clubs (name) 
                    VALUES (%s) 
                    RETURNING id
                """,
                    (club_name,),
                )

                railway_id = railway_cursor.fetchone()[0]
                new_club_mappings[local_id] = railway_id
                added_count += 1

                logger.info(
                    f"  ✅ Added {club_name} to Railway: local_id {local_id} → railway_id {railway_id} ({expected_players} players)"
                )

        railway_conn.commit()
        logger.info(
            f"  🎯 Successfully processed {len(missing_nsft_clubs)} clubs: {added_count} added, {existing_count} already existed"
        )

    except Exception as e:
        railway_conn.rollback()
        logger.error(f"  ❌ Error adding clubs: {e}")
        raise
    finally:
        railway_conn.close()

    return new_club_mappings


def create_complete_club_mapping():
    """Create complete club mapping including the newly added NSFT clubs"""
    logger.info("🗺️ Creating complete club mapping...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Get all clubs from both databases
        local_cursor.execute("SELECT id, name FROM clubs ORDER BY name")
        local_clubs = local_cursor.fetchall()

        railway_cursor.execute("SELECT id, name FROM clubs ORDER BY name")
        railway_clubs = railway_cursor.fetchall()

        # Create name-based mappings
        railway_by_name = {name.strip().lower(): id for id, name in railway_clubs}
        complete_mapping = {}

        mapped_count = 0
        missing_count = 0

        for local_id, local_name in local_clubs:
            name_key = local_name.strip().lower()

            if name_key in railway_by_name:
                railway_id = railway_by_name[name_key]
                complete_mapping[local_id] = railway_id
                mapped_count += 1
                logger.info(
                    f"  ✅ {local_name}: local_id {local_id} → railway_id {railway_id}"
                )
            else:
                missing_count += 1
                logger.warning(
                    f"  ❌ Still missing: {local_name} (local_id: {local_id})"
                )

        railway_conn.close()

        logger.info(
            f"  📊 Complete mapping: {mapped_count} mapped, {missing_count} still missing"
        )
        return complete_mapping


def create_complete_series_mapping():
    """Create complete series mapping"""
    logger.info("🏆 Creating complete series mapping...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Get all series from both databases
        local_cursor.execute("SELECT id, name FROM series ORDER BY name")
        local_series = local_cursor.fetchall()

        railway_cursor.execute("SELECT id, name FROM series ORDER BY name")
        railway_series = railway_cursor.fetchall()

        # Create name-based mappings
        railway_by_name = {name.strip().lower(): id for id, name in railway_series}
        complete_mapping = {}

        mapped_count = 0
        missing_count = 0

        for local_id, local_name in local_series:
            name_key = local_name.strip().lower()

            if name_key in railway_by_name:
                railway_id = railway_by_name[name_key]
                complete_mapping[local_id] = railway_id
                mapped_count += 1
                logger.info(
                    f"  ✅ {local_name}: local_id {local_id} → railway_id {railway_id}"
                )
            else:
                complete_mapping[local_id] = None  # Mark as unmappable
                missing_count += 1
                logger.warning(
                    f"  ❌ Still missing: {local_name} (local_id: {local_id})"
                )

        railway_conn.close()

        logger.info(
            f"  📊 Complete mapping: {mapped_count} mapped, {missing_count} still missing"
        )
        return complete_mapping


def migrate_players_with_updated_mappings(club_mapping, series_mapping):
    """Migrate players using the updated mappings"""
    logger.info("🏃 Migrating players with updated club mappings...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Clear existing players to start fresh
        logger.info("  🗑️ Clearing existing players from Railway...")
        railway_cursor.execute("DELETE FROM players")
        railway_conn.commit()

        # Get all players
        local_cursor.execute("SELECT * FROM players ORDER BY id")
        players = local_cursor.fetchall()

        # Get column names
        local_cursor.execute("SELECT * FROM players LIMIT 1")
        columns = [desc[0] for desc in local_cursor.description]
        columns_without_id = [col for col in columns if col != "id"]

        migration_stats = {"attempted": 0, "migrated": 0, "skipped": 0, "errors": []}
        migration_stats["attempted"] = len(players)

        for player_row in players:
            player_dict = dict(zip(columns, player_row))

            # Check if we can map the foreign keys
            original_club_id = player_dict["club_id"]
            original_series_id = player_dict["series_id"]

            skip_reasons = []

            # Map club_id
            if original_club_id is not None:
                if original_club_id in club_mapping:
                    player_dict["club_id"] = club_mapping[original_club_id]
                else:
                    skip_reasons.append(f"unmapped_club_id_{original_club_id}")

            # Map series_id
            if original_series_id is not None:
                if original_series_id in series_mapping:
                    mapped_series_id = series_mapping[original_series_id]
                    if mapped_series_id is not None:
                        player_dict["series_id"] = mapped_series_id
                    else:
                        skip_reasons.append(
                            f"null_mapped_series_id_{original_series_id}"
                        )
                else:
                    skip_reasons.append(f"unmapped_series_id_{original_series_id}")

            # Skip if we can't map required foreign keys
            if skip_reasons:
                migration_stats["skipped"] += 1
                continue

            # Attempt to insert player
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

                migration_stats["migrated"] += 1

                if migration_stats["migrated"] % 500 == 0:
                    logger.info(
                        f"    ✅ Migrated {migration_stats['migrated']} players..."
                    )

            except Exception as e:
                migration_stats["errors"].append(
                    {
                        "player": f"{player_dict['first_name']} {player_dict['last_name']}",
                        "error": str(e),
                    }
                )
                logger.error(
                    f"  ❌ Failed to migrate {player_dict['first_name']} {player_dict['last_name']}: {e}"
                )

        railway_conn.commit()
        railway_conn.close()

        logger.info(
            f"  ✅ Migration complete: {migration_stats['migrated']} migrated, {migration_stats['skipped']} skipped"
        )
        return migration_stats


def verify_migration_results():
    """Verify the migration results"""
    logger.info("📊 Verifying migration results...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Get counts
        local_cursor.execute("SELECT COUNT(*) FROM players")
        local_count = local_cursor.fetchone()[0]

        railway_cursor.execute("SELECT COUNT(*) FROM players")
        railway_count = railway_cursor.fetchone()[0]

        # Get NSFT specific counts
        local_cursor.execute("SELECT COUNT(*) FROM players WHERE league_id = 3")
        local_nsft_count = local_cursor.fetchone()[0]

        railway_cursor.execute("SELECT COUNT(*) FROM players WHERE league_id = 3")
        railway_nsft_count = railway_cursor.fetchone()[0]

        railway_conn.close()

        print("\n" + "=" * 80)
        print("📊 MIGRATION RESULTS VERIFICATION")
        print("=" * 80)
        print(f"📋 OVERALL RESULTS:")
        print(f"  • Local players: {local_count:,}")
        print(f"  • Railway players: {railway_count:,}")
        print(f"  • Coverage: {(railway_count / local_count * 100):.1f}%")
        print(f"  • Improvement: +{railway_count - 2431} players")

        print(f"\n🏁 NSFT LEAGUE RESULTS:")
        print(f"  • Local NSFT players: {local_nsft_count:,}")
        print(f"  • Railway NSFT players: {railway_nsft_count:,}")
        print(
            f"  • NSFT Coverage: {(railway_nsft_count / local_nsft_count * 100):.1f}%"
        )
        print(f"  • NSFT Improvement: +{railway_nsft_count - 423} players")

        return {
            "local_total": local_count,
            "railway_total": railway_count,
            "coverage_percent": (railway_count / local_count * 100),
            "improvement": railway_count - 2431,
            "local_nsft": local_nsft_count,
            "railway_nsft": railway_nsft_count,
            "nsft_coverage": (railway_nsft_count / local_nsft_count * 100),
            "nsft_improvement": railway_nsft_count - 423,
        }


def main():
    """Main execution function"""
    logger.info("🚀 ADDING MISSING NSFT CLUBS AND RE-RUNNING MIGRATION")
    logger.info("=" * 80)

    try:
        # Step 1: Add missing NSFT clubs to Railway
        logger.info("\n📋 STEP 1: Adding Missing NSFT Clubs")
        new_club_mappings = add_missing_nsft_clubs()

        # Step 2: Create complete mappings
        logger.info("\n📋 STEP 2: Creating Complete Mappings")
        complete_club_mapping = create_complete_club_mapping()
        complete_series_mapping = create_complete_series_mapping()

        # Step 3: Re-run migration with updated mappings
        logger.info("\n📋 STEP 3: Re-running Migration")
        migration_stats = migrate_players_with_updated_mappings(
            complete_club_mapping, complete_series_mapping
        )

        # Step 4: Verify results
        logger.info("\n📋 STEP 4: Verifying Results")
        results = verify_migration_results()

        # Step 5: Summary
        print(f"\n🎉 MIGRATION ENHANCEMENT COMPLETE!")
        print(f"📈 IMPROVEMENTS:")
        print(
            f"  • Overall coverage increased from 82.0% to {results['coverage_percent']:.1f}%"
        )
        print(f"  • Added {results['improvement']} additional players")
        print(
            f"  • NSFT coverage increased from 58.3% to {results['nsft_coverage']:.1f}%"
        )
        print(f"  • Added {results['nsft_improvement']} additional NSFT players")

        if results["coverage_percent"] > 95:
            print(f"🏆 EXCELLENT: Achieved >95% coverage!")
        elif results["coverage_percent"] > 90:
            print(f"✅ GREAT: Achieved >90% coverage!")
        else:
            print(f"📊 GOOD: Significant improvement achieved!")

        return True

    except Exception as e:
        logger.error(f"❌ Migration enhancement failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    logger.info(f"\n🎯 NEXT STEPS:")
    logger.info(f"  1. Test Railway application: https://www.lovetorally.com")
    logger.info(f"  2. Verify NSFT players are accessible")
    logger.info(f"  3. Check player data integrity")
    sys.exit(0 if success else 1)
