#!/usr/bin/env python3
"""
ETL Master Import with Verbose SMS Option
=======================================

Runs the master ETL import. By default sends only start/end SMS notifications.
Use --verbose-sms to get notifications for each step.

Usage:
    python scripts/run_etl_summary_sms.py  # Summary only (default)
    python scripts/run_etl_summary_sms.py --verbose-sms  # Step-by-step notifications
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
    parser.add_argument(
        '--verbose-sms',
        action='store_true',
        help='Send SMS notification for each step (default: summary only at start/end)'
    )
    
    args = parser.parse_args()
    
    # Build command
    cmd = [
        'python', 
        'data/etl/database_import/master_import.py',
        '--environment', args.environment
    ]
    
    if args.league:
        cmd.extend(['--league', args.league])
    
    if args.verbose_sms:
        cmd.append('--verbose-sms')
    
    print("🚀 Running ETL Import")
    print("=" * 60)
    print(f"Environment: {args.environment}")
    print(f"League: {args.league if args.league else 'All leagues'}")
    print(f"SMS Mode: {'Step-by-step notifications' if args.verbose_sms else 'Summary only (start + end)'}")
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
