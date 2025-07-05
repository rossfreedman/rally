#!/usr/bin/env python3
"""
DEPRECATED: Fix missing series_name_mappings table on staging environment

This script is DEPRECATED as of the series.display_name migration.
The series_name_mappings table has been replaced with series.display_name column.
This script is kept for historical reference only.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_series_mappings_table():
    """Create the series_name_mappings table with default data"""
    
    # Use Railway internal database connection
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return False
    
    try:
        logger.info("🔗 Connecting to staging database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'series_name_mappings'
            )
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            logger.info("✅ series_name_mappings table already exists")
            return True
        
        logger.info("🔧 Creating series_name_mappings table...")
        
        # Create the table
        cursor.execute("""
            CREATE TABLE series_name_mappings (
                id SERIAL PRIMARY KEY,
                user_facing_name VARCHAR(100) NOT NULL,
                database_name VARCHAR(100) NOT NULL,
                league_id VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_facing_name, league_id)
            )
        """)
        
        logger.info("📊 Inserting default series mappings...")
        
        # Define default mappings for each league
        default_mappings = [
            # NSTF mappings: "Series 2B" -> "S2B"
            ("NSTF", "Series 1", "S1"),
            ("NSTF", "Series 2A", "S2A"),
            ("NSTF", "Series 2B", "S2B"),
            ("NSTF", "Series 3", "S3"),
            ("NSTF", "Series 4", "S4"),
            
            # APTA_CHICAGO mappings: "Chicago 22" -> "22"
            ("APTA_CHICAGO", "Chicago 1", "1"),
            ("APTA_CHICAGO", "Chicago 2", "2"),
            ("APTA_CHICAGO", "Chicago 3", "3"),
            ("APTA_CHICAGO", "Chicago 11", "11"),
            ("APTA_CHICAGO", "Chicago 12", "12"),
            ("APTA_CHICAGO", "Chicago 13", "13"),
            ("APTA_CHICAGO", "Chicago 21", "21"),
            ("APTA_CHICAGO", "Chicago 22", "22"),
            ("APTA_CHICAGO", "Chicago 23", "23"),
            ("APTA_CHICAGO", "Chicago 31", "31"),
            ("APTA_CHICAGO", "Chicago 32", "32"),
            ("APTA_CHICAGO", "Chicago 33", "33"),
            
            # CNSWPL mappings: "Division 1" -> "1"
            ("CNSWPL", "Division 1", "1"),
            ("CNSWPL", "Division 1a", "1a"),
            ("CNSWPL", "Division 2", "2"),
            ("CNSWPL", "Division 2a", "2a"),
            ("CNSWPL", "Division 3", "3"),
        ]
        
        # Insert default mappings
        for league_id, user_facing, database_name in default_mappings:
            cursor.execute("""
                INSERT INTO series_name_mappings (user_facing_name, database_name, league_id)
                VALUES (%s, %s, %s)
            """, (user_facing, database_name, league_id))
        
        conn.commit()
        
        # Verify the data was inserted
        cursor.execute("SELECT COUNT(*) FROM series_name_mappings")
        count = cursor.fetchone()[0]
        
        logger.info(f"✅ Successfully created series_name_mappings table with {count} default mappings")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create series_name_mappings table: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting staging series_name_mappings table fix...")
    
    success = create_series_mappings_table()
    
    if success:
        logger.info("✅ Staging series_name_mappings table fix completed successfully!")
        logger.info("🎯 You can now run the ETL script again")
        sys.exit(0)
    else:
        logger.error("❌ Failed to fix staging series_name_mappings table")
        sys.exit(1) 