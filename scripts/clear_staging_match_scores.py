#!/usr/bin/env python3
"""
Clear Staging Match Scores Table
Removes all records from match_scores table in staging database
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_staging_match_scores():
    """Clear match_scores table in staging database"""
    
    # Connect to staging database
    staging_url = 'postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway'
    engine = create_engine(staging_url)
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Get current count
                result = conn.execute(text('SELECT COUNT(*) FROM match_scores'))
                current_count = result.fetchone()[0]
                logger.info(f"Current match_scores count: {current_count}")
                
                # Clear the table
                logger.info("Clearing match_scores table...")
                result = conn.execute(text('DELETE FROM match_scores'))
                deleted_count = result.rowcount
                logger.info(f"Deleted {deleted_count} records from match_scores")
                
                # Verify table is empty
                result = conn.execute(text('SELECT COUNT(*) FROM match_scores'))
                final_count = result.fetchone()[0]
                logger.info(f"Final match_scores count: {final_count}")
                
                # Commit transaction
                trans.commit()
                logger.info("✅ Successfully cleared staging match_scores table")
                
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "final_count": final_count
                }
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error during clear: {e}")
                raise
                
    except Exception as e:
        logger.error(f"❌ Failed to connect to staging database: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Main function"""
    logger.info("🚀 Starting staging match_scores table clear...")
    
    # Confirm before proceeding
    response = input("This will delete ALL records from staging match_scores table. Continue? (y/N): ")
    if response.lower() != 'y':
        logger.info("❌ Cancelled by user")
        return
    
    result = clear_staging_match_scores()
    
    if result["success"]:
        logger.info(f"✅ Clear completed successfully!")
        logger.info(f"   Deleted records: {result['deleted_count']}")
        logger.info(f"   Final count: {result['final_count']}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. SSH into the staging server")
        logger.info("2. Run the ETL import to populate match_scores with clean data")
        logger.info("3. Verify the analyze-me page shows correct stats")
    else:
        logger.error(f"❌ Clear failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 