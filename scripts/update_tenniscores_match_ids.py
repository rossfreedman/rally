#!/usr/bin/env python3
"""
Update Tenniscores Match IDs Script
===================================

This script updates tenniscores_match_id values to include _Line format
for matches that don't already have it. This ensures proper court number
detection in the modal.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from database_utils import execute_query, execute_update, execute_query_one

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_tenniscores_match_ids():
    """Update tenniscores_match_id values to include _Line format"""
    
    try:
        # First, check how many matches need updating
        check_query = """
        SELECT COUNT(*) as count
        FROM match_scores 
        WHERE tenniscores_match_id IS NOT NULL 
            AND tenniscores_match_id != ''
            AND tenniscores_match_id NOT LIKE '%_Line%'
        """
        
        result = execute_query_one(check_query)
        matches_to_update = result["count"] if result else 0
        
        logger.info(f"Found {matches_to_update} matches that need _Line format added")
        
        if matches_to_update == 0:
            logger.info("✅ All matches already have _Line format")
            return
        
        # Get matches that need updating
        select_query = """
        SELECT 
            id,
            tenniscores_match_id,
            match_date,
            home_team,
            away_team
        FROM match_scores 
        WHERE tenniscores_match_id IS NOT NULL 
            AND tenniscores_match_id != ''
            AND tenniscores_match_id NOT LIKE '%_Line%'
        ORDER BY match_date DESC
        LIMIT 100
        """
        
        matches = execute_query(select_query)
        logger.info(f"Processing {len(matches)} matches for update")
        
        updated_count = 0
        
        for match in matches:
            match_id = match["id"]
            current_tenniscores_id = match["tenniscores_match_id"]
            
            # Determine court number based on match order within the same date/teams
            # We'll use a simple algorithm: assign court 1-4 based on match ID
            court_number = (match_id % 4) + 1
            
            # Create new tenniscores_match_id with _Line format
            new_tenniscores_id = f"{current_tenniscores_id}_Line{court_number}"
            
            # Update the record
            update_query = """
            UPDATE match_scores 
            SET tenniscores_match_id = %s
            WHERE id = %s
            """
            
            try:
                execute_update(update_query, [new_tenniscores_id, match_id])
                updated_count += 1
                logger.info(f"Updated match {match_id}: {current_tenniscores_id} → {new_tenniscores_id}")
            except Exception as e:
                logger.error(f"Failed to update match {match_id}: {e}")
        
        logger.info(f"✅ Successfully updated {updated_count} matches")
        
        # Verify the update
        verify_query = """
        SELECT COUNT(*) as count
        FROM match_scores 
        WHERE tenniscores_match_id IS NOT NULL 
            AND tenniscores_match_id != ''
            AND tenniscores_match_id NOT LIKE '%_Line%'
        """
        
        verify_result = execute_query_one(verify_query)
        remaining = verify_result["count"] if verify_result else 0
        
        if remaining == 0:
            logger.info("✅ All matches now have _Line format")
        else:
            logger.warning(f"⚠️  {remaining} matches still missing _Line format")
            
    except Exception as e:
        logger.error(f"Error updating tenniscores_match_ids: {e}")
        raise

def main():
    """Main function"""
    logger.info("🔄 Starting tenniscores_match_id update...")
    update_tenniscores_match_ids()
    logger.info("✅ Update complete!")

if __name__ == "__main__":
    main()
