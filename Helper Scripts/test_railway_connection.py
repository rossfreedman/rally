import logging
import os
from urllib.parse import urlparse, urlunparse

import psycopg2
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def mask_password(url):
    """Mask the password in the URL for safe logging"""
    parsed = urlparse(url)
    # Create a new netloc with masked password
    if parsed.password:
        safe_netloc = parsed.netloc.replace(parsed.password, "****")
        # Reconstruct the URL with masked password
        return urlunparse(
            (
                parsed.scheme,
                safe_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
    return url


def test_connection():
    # Construct the URL using Railway's proxy domain and exact credentials
    url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

    # Log the URL with masked password
    logger.info(f"Using database URL: {mask_password(url)}")
    logger.info("Attempting to connect to Railway database...")

    try:
        # Try with a short timeout first
        conn = psycopg2.connect(url, connect_timeout=5, sslmode="require")

        logger.info("Successfully connected to database!")

        # Test a simple query
        with conn.cursor() as cur:
            logger.info("Testing simple query...")
            cur.execute("SELECT current_database(), current_user, version();")
            db, user, version = cur.fetchone()
            logger.info(f"Connected to database: {db}")
            logger.info(f"Connected as user: {user}")
            logger.info(f"PostgreSQL version: {version}")

            # List all tables
            logger.info("\nListing all tables:")
            cur.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """
            )
            tables = cur.fetchall()
            for table in tables:
                logger.info(f"- {table[0]}")

    except psycopg2.OperationalError as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        logger.error("Common issues:")
        logger.error("1. Check if the proxy domain and port are correct")
        logger.error("2. Verify the host is accessible (no firewall blocking)")
        logger.error("3. Verify SSL/TLS connection is properly configured")
        raise
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise
    finally:
        if "conn" in locals():
            conn.close()
            logger.info("Database connection closed.")


if __name__ == "__main__":
    test_connection()
