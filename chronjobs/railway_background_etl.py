#!/usr/bin/env python3
"""
Railway Background ETL Script

This script runs ETL imports as a background process, bypassing HTTP timeout limits.
Can be triggered via Railway's cron jobs or run manually.
"""

import os
import sys
import signal
import time
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def run_etl_background():
    """Run ETL import as a background process"""
    print("=" * 60)
    print("🚀 RAILWAY BACKGROUND ETL PROCESS")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    try:
        # Import the ETL class
        from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
        
        # Create and run ETL
        etl = ComprehensiveETL()
        
        print("📋 Starting comprehensive ETL process...")
        success = etl.run()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ ETL PROCESS COMPLETED SUCCESSFULLY")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ ETL PROCESS FAILED")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n❌ Critical error in background ETL: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        end_time = datetime.now()
        print(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    success = run_etl_background()
    sys.exit(0 if success else 1) 