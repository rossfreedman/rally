#!/usr/bin/env python3
"""
Sync Staging Database from Local
Replaces staging match_scores table with local data to fix corruption
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database_config import get_db_engine

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sync_staging_from_local():
    """Sync staging match_scores table from local database"""
    
    # Connect to both databases
    local_engine = get_db_engine()
    staging_url = 'postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway'
    staging_engine = create_engine(staging_url)
    
    try:
        # Get local match_scores data
        logger.info("Extracting match_scores data from local database...")
        with local_engine.connect() as local_conn:
            result = local_conn.execute(text('''
                SELECT 
                    id,
                    tenniscores_match_id,
                    match_date,
                    home_team,
                    away_team,
                    home_team_id,
                    away_team_id,
                    winner,
                    scores,
                    home_player_1_id,
                    home_player_2_id,
                    away_player_1_id,
                    away_player_2_id,
                    league_id,
                    created_at
                FROM match_scores
                ORDER BY id
            '''))
            
            local_matches = [dict(row) for row in result]
            logger.info(f"Extracted {len(local_matches)} matches from local database")
        
        # Replace staging match_scores table
        logger.info("Replacing staging match_scores table...")
        with staging_engine.connect() as staging_conn:
            # Start transaction
            trans = staging_conn.begin()
            
            try:
                # Clear existing match_scores table
                staging_conn.execute(text('DELETE FROM match_scores'))
                logger.info("Cleared existing match_scores table")
                
                # Insert local data into staging
                if local_matches:
                    # Insert in batches
                    batch_size = 1000
                    for i in range(0, len(local_matches), batch_size):
                        batch = local_matches[i:i + batch_size]
                        
                        # Build INSERT statement
                        columns = list(batch[0].keys())
                        placeholders = ','.join(['%s'] * len(columns))
                        column_names = ','.join(columns)
                        
                        insert_sql = f'''
                            INSERT INTO match_scores ({column_names})
                            VALUES ({placeholders})
                        '''
                        
                        # Prepare batch data
                        batch_data = []
                        for match in batch:
                            row_data = tuple(match[col] for col in columns)
                            batch_data.append(row_data)
                        
                        # Execute batch insert
                        staging_conn.execute(text(insert_sql), batch_data)
                        logger.info(f"Inserted batch of {len(batch)} matches")
                
                # Verify the sync
                result = staging_conn.execute(text('SELECT COUNT(*) FROM match_scores'))
                staging_count = result.fetchone()[0]
                logger.info(f"Staging now has {staging_count} matches")
                
                # Commit transaction
                trans.commit()
                logger.info("✅ Successfully synced staging database from local")
                
                return {
                    "success": True,
                    "matches_synced": len(local_matches),
                    "staging_count": staging_count
                }
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error during sync: {e}")
                raise
                
    except Exception as e:
        logger.error(f"❌ Failed to sync staging database: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Main function"""
    logger.info("🚀 Starting staging database sync from local...")
    
    # Confirm before proceeding
    response = input("This will replace staging match_scores table with local data. Continue? (y/N): ")
    if response.lower() != 'y':
        logger.info("❌ Cancelled by user")
        return
    
    result = sync_staging_from_local()
    
    if result["success"]:
        logger.info(f"✅ Sync completed successfully!")
        logger.info(f"   Matches synced: {result['matches_synced']}")
        logger.info(f"   Staging count: {result['staging_count']}")
    else:
        logger.error(f"❌ Sync failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 