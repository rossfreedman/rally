#!/usr/bin/env python3
"""
Fast ETL Script - No Table Clearing

This script imports data without the slow table clearing phase by using
intelligent conflict resolution and merge operations.
"""

import sys
import os
from datetime import datetime

# Add project paths
sys.path.append('data/etl/database_import')
sys.path.append('.')

def run_fast_etl():
    """Run ETL without table clearing using merge operations"""
    
    print("🚀 Starting FAST ETL (No Table Clearing)")
    print("=" * 60)
    
    try:
        from import_all_jsons_to_database import ComprehensiveETL
        
        # Create ETL instance
        etl = ComprehensiveETL()
        
        # Override the clearing method to skip it
        def skip_clearing(conn):
            print("⏭️  SKIPPING slow table clearing phase")
            print("🔄 Using merge operations instead")
            return 0, 0, 0  # Return empty counts
            
        # Monkey patch to skip clearing
        etl.clear_target_tables = skip_clearing
        
        print("🔧 ETL configured for fast merge mode")
        print("📥 Starting import process...")
        
        # Run the ETL
        result = etl.run()
        
        if result:
            print("🎉 Fast ETL completed successfully!")
        else:
            print("❌ Fast ETL failed")
            
        return result
        
    except Exception as e:
        print(f"❌ Fast ETL error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_time = datetime.now()
    success = run_fast_etl()
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("=" * 60)
    if success:
        print(f"✅ Fast ETL completed in {duration}")
    else:
        print(f"❌ Fast ETL failed after {duration}")
    print("=" * 60) 