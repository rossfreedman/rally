#!/usr/bin/env python3
"""
ETL Master Import with Summary-Only SMS
=====================================

Runs the master ETL import with only start and end SMS notifications.
Reduces SMS spam while maintaining critical status updates.

Usage:
    python scripts/run_etl_summary_sms.py
    python scripts/run_etl_summary_sms.py --environment staging
    python scripts/run_etl_summary_sms.py --league CNSWPL
"""

import subprocess
import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run ETL import with summary-only SMS notifications')
    parser.add_argument(
        '--environment',
        choices=['staging', 'production', 'local'],
        default='local',
        help='Target environment (default: local)'
    )
    parser.add_argument(
        '--league',
        choices=['APTA_CHICAGO', 'CNSWPL', 'NSTF'],
        help='Specific league to import (if not specified, imports all leagues)'
    )
    
    args = parser.parse_args()
    
    # Build command
    cmd = [
        'python', 
        'data/etl/database_import/master_import.py',
        '--environment', args.environment,
        '--summary-only'  # Key flag to reduce SMS notifications
    ]
    
    if args.league:
        cmd.extend(['--league', args.league])
    
    print("🚀 Running ETL Import with Summary-Only SMS Notifications")
    print("=" * 60)
    print(f"Environment: {args.environment}")
    print(f"League: {args.league if args.league else 'All leagues'}")
    print("SMS Mode: Start + End notifications only")
    print("=" * 60)
    print()
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ ETL import completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ETL import failed with exit code {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n⚠️ ETL import interrupted by user")
        return 1

if __name__ == '__main__':
    sys.exit(main())
