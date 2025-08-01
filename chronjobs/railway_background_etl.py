#!/usr/bin/env python3
"""
Railway Background ETL Script

This script runs ETL imports as a background process, bypassing HTTP timeout limits.
Can be triggered via Railway's cron jobs or run manually.
Player validation is ALWAYS enabled for data integrity.

Usage:
    python chronjobs/railway_background_etl.py
    python chronjobs/railway_background_etl.py --environment staging
    python chronjobs/railway_background_etl.py --environment production
"""

import argparse
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

def run_etl_background(force_environment=None):
    """Run ETL import as a background process"""
    print("=" * 60, flush=True)
    print("🚀 RAILWAY BACKGROUND ETL PROCESS", flush=True)
    print("=" * 60, flush=True)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    if force_environment:
        print(f"🎯 Forced environment: {force_environment}", flush=True)
    
    print("🛡️ Player validation ALWAYS enabled for data integrity", flush=True)
    
    # Setup signal handlers
    setup_signal_handlers()
    
    try:
        # Import the ETL class
        from data.etl.database_import.OLD.import_all_jsons_to_database import ComprehensiveETL
        
        # Create and run ETL with environment settings
        etl = ComprehensiveETL(force_environment=force_environment)
        
        print("📋 Starting comprehensive ETL process...", flush=True)
        success = etl.run()
        
        if success:
            print("\n" + "=" * 60, flush=True)
            print("✅ ETL PROCESS COMPLETED SUCCESSFULLY", flush=True)
            print("=" * 60, flush=True)
            return True
        else:
            print("\n" + "=" * 60, flush=True)
            print("❌ ETL PROCESS FAILED", flush=True)
            print("=" * 60, flush=True)
            return False
            
    except Exception as e:
        print(f"\n❌ Critical error in background ETL: {str(e)}", flush=True)
        import traceback
        print(f"Traceback: {traceback.format_exc()}", flush=True)
        return False
    
    finally:
        end_time = datetime.now()
        print(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Railway Background ETL Process')
    parser.add_argument('--environment', '-e', 
                       choices=['local', 'railway_staging', 'railway_production'],
                       help='Force specific environment (overrides auto-detection)')
    
    args = parser.parse_args()
    
    success = run_etl_background(force_environment=args.environment)
    sys.exit(0 if success else 1) 