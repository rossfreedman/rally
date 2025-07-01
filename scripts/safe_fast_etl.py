#!/usr/bin/env python3
"""
Safe Fast ETL Script

This script optimizes the table clearing phase while preserving
all user protection mechanisms from the original ETL.
"""

import sys
import os
from datetime import datetime

# Add project paths
sys.path.append('data/etl/database_import')
sys.path.append('.')

def run_safe_fast_etl():
    """Run ETL with optimized clearing but full user protection"""
    
    print("🛡️  Starting SAFE Fast ETL (Optimized Clearing + User Protection)")
    print("=" * 70)
    
    try:
        from import_all_jsons_to_database import ComprehensiveETL
        
        # Create ETL instance
        etl = ComprehensiveETL()
        
        # Override ONLY the slow clearing method, keep user protection
        original_clear = etl.clear_target_tables
        
        def optimized_clear_tables(conn):
            """Optimized table clearing with user protection"""
            print("💾 Backing up user data (PRESERVED)...")
            
            # Step 1: Keep original backup logic
            associations_backup_count, contexts_backup_count, availability_backup_count = etl.backup_user_associations(conn)
            
            print("🚀 Using optimized table clearing...")
            
            # Step 2: Fast clearing with proper order
            cursor = conn.cursor()
            
            try:
                # Disable foreign key checks temporarily for faster clearing
                cursor.execute("SET session_replication_role = replica;")
                
                # Clear in dependency order, but use TRUNCATE for speed
                tables_to_clear = [
                    "schedule", "series_stats", "match_scores", "player_history",
                    "user_player_associations", "players", "teams", "series_leagues", 
                    "club_leagues", "series", "clubs", "leagues"
                ]
                
                for table in tables_to_clear:
                    print(f"   🗑️  Fast clearing {table}...")
                    try:
                        cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY")
                    except Exception as e:
                        # Fallback to DELETE if TRUNCATE fails
                        print(f"   ⚠️  TRUNCATE failed for {table}, using DELETE...")
                        cursor.execute(f"DELETE FROM {table}")
                    
                # Re-enable foreign key checks
                cursor.execute("SET session_replication_role = DEFAULT;")
                conn.commit()
                
                print("✅ Optimized clearing completed")
                
            except Exception as e:
                print(f"❌ Optimized clearing failed: {e}")
                # Rollback and use original method
                conn.rollback()
                cursor.execute("SET session_replication_role = DEFAULT;")
                print("🔄 Falling back to original clearing method...")
                return original_clear(conn)
            
            return associations_backup_count, contexts_backup_count, availability_backup_count
            
        # Replace only the clearing method
        etl.clear_target_tables = optimized_clear_tables
        
        print("🔧 ETL configured for safe fast mode")
        print("📥 Starting import process with full user protection...")
        
        # Run the ETL with user protection intact
        result = etl.run()
        
        if result:
            print("🎉 Safe Fast ETL completed successfully!")
        else:
            print("❌ Safe Fast ETL failed")
            
        return result
        
    except Exception as e:
        print(f"❌ Safe Fast ETL error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_time = datetime.now()
    success = run_safe_fast_etl()
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("=" * 70)
    if success:
        print(f"✅ Safe Fast ETL completed in {duration}")
        print("🛡️  User data preserved and protected!")
    else:
        print(f"❌ Safe Fast ETL failed after {duration}")
    print("=" * 70) 