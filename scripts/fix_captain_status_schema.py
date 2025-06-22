#!/usr/bin/env python3
"""
Fix captain_status column type mismatch on Railway
"""

import logging
from urllib.parse import urlparse

import psycopg2

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


def fix_captain_status_column():
    """Fix the captain_status column type mismatch"""
    logger.info("🔧 FIXING CAPTAIN_STATUS COLUMN TYPE MISMATCH")
    logger.info("=" * 60)

    try:
        conn = connect_to_railway()
        cursor = conn.cursor()

        # Check current column type
        logger.info("Checking current column type...")
        cursor.execute(
            """
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'players' AND column_name = 'captain_status'
        """
        )
        current_type = cursor.fetchone()[0]
        logger.info(f"  Current type: {current_type}")

        if current_type == "boolean":
            logger.info("Converting captain_status from boolean to TEXT...")

            # Convert boolean to TEXT to match local data format
            cursor.execute(
                """
                ALTER TABLE players 
                ALTER COLUMN captain_status TYPE TEXT 
                USING CASE 
                    WHEN captain_status = true THEN 'C'
                    WHEN captain_status = false THEN ''
                    ELSE NULL
                END;
            """
            )

            logger.info("  ✅ Successfully converted captain_status to TEXT")

            # Update column comment
            cursor.execute(
                """
                COMMENT ON COLUMN players.captain_status IS 'Captain status: C=Captain, CC=Co-Captain, empty=Regular Player';
            """
            )

            logger.info("  ✅ Updated column comment")

        elif current_type in ["text", "character varying"]:
            logger.info(
                f"  ✅ Column is already TEXT type ({current_type}) - no changes needed"
            )
        else:
            logger.warning(f"  ⚠️  Unexpected column type: {current_type}")

        # Verify the change
        cursor.execute(
            """
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'players' AND column_name = 'captain_status'
        """
        )
        new_type = cursor.fetchone()[0]
        logger.info(f"  Final type: {new_type}")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("\n✅ CAPTAIN_STATUS COLUMN FIX COMPLETED!")
        return True

    except Exception as e:
        logger.error(f"❌ Error fixing captain_status column: {e}")
        if "conn" in locals():
            conn.rollback()
        return False


if __name__ == "__main__":
    success = fix_captain_status_column()

    if success:
        logger.info("\n🎯 READY FOR MIGRATION!")
        logger.info("  The schema mismatch has been resolved.")
        logger.info("  You can now safely run the migration:")
        logger.info("  python scripts/test_migration_preview.py")
    else:
        logger.error("\n❌ Fix failed - manual intervention required")

    exit(0 if success else 1)
