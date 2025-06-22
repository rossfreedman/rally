"""Import missing critical data from local database

Revision ID: import_missing_data
Revises: e8296dc0df71
Create Date: 2025-06-12 09:00:00.000000

"""

import os
import sys

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from alembic import op

# Add the project root to the Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from database_config import get_db

# revision identifiers, used by Alembic.
revision = "import_missing_data"
down_revision = "e8296dc0df71"
branch_labels = None
depends_on = None


def get_local_data():
    """Get data from local database that needs to be imported"""
    print("📥 Fetching data from local database...")

    local_data = {
        "player_history": [],
        "user_player_associations": [],
        "player_mappings": {},
    }

    try:
        with get_db() as local_conn:
            local_cursor = local_conn.cursor()

            # Get player ID mappings (tenniscores_player_id -> local_id)
            local_cursor.execute(
                "SELECT tenniscores_player_id, id FROM players WHERE tenniscores_player_id IS NOT NULL"
            )
            local_tc_to_id = dict(local_cursor.fetchall())

            # Get Railway player mappings
            railway_conn = op.get_bind()
            railway_cursor = railway_conn.execute(
                sa.text(
                    "SELECT tenniscores_player_id, id FROM players WHERE tenniscores_player_id IS NOT NULL"
                )
            )
            railway_tc_to_id = dict(railway_cursor.fetchall())

            # Create local_id -> railway_id mapping
            for tc_id, local_id in local_tc_to_id.items():
                if tc_id in railway_tc_to_id:
                    local_data["player_mappings"][local_id] = railway_tc_to_id[tc_id]

            print(
                f"   ✅ Created mappings for {len(local_data['player_mappings']):,} players"
            )

            # Get player_history data that can be mapped
            if local_data["player_mappings"]:
                local_cursor.execute(
                    """
                    SELECT player_id, league_id, series, date, end_pti, created_at
                    FROM player_history 
                    WHERE player_id IN %s
                    ORDER BY id
                """,
                    (tuple(local_data["player_mappings"].keys()),),
                )

                for row in local_cursor.fetchall():
                    local_player_id = row[0]
                    if local_player_id in local_data["player_mappings"]:
                        railway_player_id = local_data["player_mappings"][
                            local_player_id
                        ]
                        local_data["player_history"].append(
                            {
                                "player_id": railway_player_id,
                                "league_id": row[1],
                                "series": row[2],
                                "date": row[3],
                                "end_pti": row[4],
                                "created_at": row[5],
                            }
                        )

                print(
                    f"   ✅ Found {len(local_data['player_history']):,} player_history records to import"
                )

            # Get user_player_associations data with proper mapping
            local_cursor.execute(
                """
                SELECT u.email, upa.player_id, upa.is_primary, upa.created_at
                FROM user_player_associations upa
                JOIN users u ON upa.user_id = u.id
            """
            )

            for row in local_cursor.fetchall():
                user_email, local_player_id, is_primary, created_at = row
                if local_player_id in local_data["player_mappings"]:
                    railway_player_id = local_data["player_mappings"][local_player_id]
                    local_data["user_player_associations"].append(
                        {
                            "user_email": user_email,
                            "player_id": railway_player_id,
                            "is_primary": is_primary,
                            "created_at": created_at,
                        }
                    )

            print(
                f"   ✅ Found {len(local_data['user_player_associations']):,} user_player_associations to import"
            )

    except Exception as e:
        print(f"   ❌ Error fetching local data: {e}")
        raise

    return local_data


def upgrade():
    """Import missing critical data"""
    print("🚀 IMPORTING MISSING CRITICAL DATA VIA ALEMBIC")
    print("=" * 60)

    # Get connection to Railway database
    connection = op.get_bind()

    # Check current counts
    current_ph = connection.execute(
        sa.text("SELECT COUNT(*) FROM player_history")
    ).scalar()
    current_upa = connection.execute(
        sa.text("SELECT COUNT(*) FROM user_player_associations")
    ).scalar()

    print(f"📊 Current Railway counts:")
    print(f"   player_history: {current_ph:,} records")
    print(f"   user_player_associations: {current_upa:,} records")

    if current_ph > 100000 and current_upa > 0:
        print("✅ Data already appears to be imported. Skipping.")
        return

    # Get local data
    local_data = get_local_data()

    if not local_data["player_history"] and not local_data["user_player_associations"]:
        print("❌ No data to import")
        return

    # Clear existing data (to avoid duplicates)
    print("🗑️  Clearing existing data...")
    connection.execute(sa.text("TRUNCATE TABLE player_history CASCADE"))
    connection.execute(sa.text("TRUNCATE TABLE user_player_associations CASCADE"))

    # Import player_history data
    if local_data["player_history"]:
        print(
            f"📊 Importing {len(local_data['player_history']):,} player_history records..."
        )

        # Use bulk insert for better performance
        player_history_table = sa.table(
            "player_history",
            sa.column("player_id", sa.Integer),
            sa.column("league_id", sa.Integer),
            sa.column("series", sa.String),
            sa.column("date", sa.Date),
            sa.column("end_pti", sa.Numeric),
            sa.column("created_at", sa.DateTime),
        )

        # Insert in batches
        batch_size = 1000
        for i in range(0, len(local_data["player_history"]), batch_size):
            batch = local_data["player_history"][i : i + batch_size]
            op.bulk_insert(player_history_table, batch)
            print(f"   ✅ Imported batch {i//batch_size + 1}: {len(batch)} records")

    # Import user_player_associations data
    if local_data["user_player_associations"]:
        print(
            f"👥 Importing {len(local_data['user_player_associations']):,} user_player_associations..."
        )

        # Get user mappings from Railway
        user_mappings = {}
        users_result = connection.execute(sa.text("SELECT id, email FROM users"))
        for user_id, email in users_result:
            user_mappings[email] = user_id

        # Prepare association data with proper user IDs
        association_data = []
        for assoc in local_data["user_player_associations"]:
            user_email = assoc["user_email"]
            if user_email in user_mappings:
                association_data.append(
                    {
                        "user_id": user_mappings[user_email],
                        "player_id": assoc["player_id"],
                        "is_primary": assoc["is_primary"],
                        "created_at": assoc["created_at"],
                    }
                )

        if association_data:
            user_player_assoc_table = sa.table(
                "user_player_associations",
                sa.column("user_id", sa.Integer),
                sa.column("player_id", sa.Integer),
                sa.column("is_primary", sa.Boolean),
                sa.column("created_at", sa.DateTime),
            )

            op.bulk_insert(user_player_assoc_table, association_data)
            print(f"   ✅ Imported {len(association_data)} associations")

    # Verify import
    final_ph = connection.execute(
        sa.text("SELECT COUNT(*) FROM player_history")
    ).scalar()
    final_upa = connection.execute(
        sa.text("SELECT COUNT(*) FROM user_player_associations")
    ).scalar()

    print(f"\n✅ IMPORT COMPLETED!")
    print(f"📊 Final Railway counts:")
    print(f"   player_history: {final_ph:,} records (+{final_ph - current_ph:,})")
    print(
        f"   user_player_associations: {final_upa:,} records (+{final_upa - current_upa:,})"
    )


def downgrade():
    """Remove imported data"""
    print("⏪ REMOVING IMPORTED DATA")

    connection = op.get_bind()

    # Clear the imported data
    connection.execute(sa.text("TRUNCATE TABLE player_history CASCADE"))
    connection.execute(sa.text("TRUNCATE TABLE user_player_associations CASCADE"))

    print("✅ Imported data removed")
