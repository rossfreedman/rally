#!/usr/bin/env python3
"""
Script to remove February and March 2025 match scores from the local database
for testing the cronjob's delta scraping and import functionality.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db_engine

def remove_february_march_database_data():
    """Remove all February and March 2025 match scores from the database."""
    
    print("🗄️ Removing February and March 2025 data from database...")
    
    # Get database connection
    engine = get_db_engine()
    
    try:
        with engine.connect() as conn:
            # First, let's see what we have
            print("📊 Checking current match data...")
            
            # Count total matches
            result = conn.execute(text("SELECT COUNT(*) FROM match_scores"))
            total_matches = result.scalar()
            print(f"   Total matches in database: {total_matches}")
            
            # Count February and March 2025 matches
            feb_mar_query = """
            SELECT COUNT(*) FROM match_scores 
            WHERE DATE(match_date) >= '2025-02-01' 
            AND DATE(match_date) <= '2025-03-31'
            """
            result = conn.execute(text(feb_mar_query))
            feb_mar_count = result.scalar()
            print(f"   February/March 2025 matches: {feb_mar_count}")
            
            if feb_mar_count == 0:
                print("✅ No February/March 2025 data found in database")
                return
            
            # Show some examples of what we're removing
            sample_query = """
            SELECT match_date, home_team, away_team, league_id 
            FROM match_scores 
            WHERE DATE(match_date) >= '2025-02-01' 
            AND DATE(match_date) <= '2025-03-31'
            ORDER BY match_date DESC 
            LIMIT 5
            """
            result = conn.execute(text(sample_query))
            samples = result.fetchall()
            
            print("📋 Sample matches to be removed:")
            for sample in samples:
                print(f"   {sample[0]} - {sample[1]} vs {sample[2]} ({sample[3]})")
            
            # Confirm deletion
            print(f"\n⚠️ About to delete {feb_mar_count} February/March 2025 matches")
            response = input("Continue? (y/N): ")
            
            if response.lower() != 'y':
                print("❌ Cancelled by user")
                return
            
            # Delete February and March 2025 matches
            delete_query = """
            DELETE FROM match_scores 
            WHERE DATE(match_date) >= '2025-02-01' 
            AND DATE(match_date) <= '2025-03-31'
            """
            
            print("🗑️ Deleting February/March 2025 matches...")
            result = conn.execute(text(delete_query))
            deleted_count = result.rowcount
            
            # Commit the transaction
            conn.commit()
            
            print(f"✅ Successfully deleted {deleted_count} February/March 2025 matches")
            
            # Verify deletion
            result = conn.execute(text(feb_mar_query))
            remaining_count = result.scalar()
            print(f"   Remaining February/March 2025 matches: {remaining_count}")
            
            # Show updated total
            result = conn.execute(text("SELECT COUNT(*) FROM match_scores"))
            new_total = result.scalar()
            print(f"   Updated total matches: {new_total}")
            
    except Exception as e:
        print(f"❌ Error removing database data: {e}")
        raise

if __name__ == "__main__":
    remove_february_march_database_data() 