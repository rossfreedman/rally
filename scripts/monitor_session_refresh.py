#!/usr/bin/env python3
"""
Session Refresh Monitoring Script
=================================

Simple script to monitor the session refresh system status.
Use this to check if the system is working properly in production.

Usage:
    python scripts/monitor_session_refresh.py
    python scripts/monitor_session_refresh.py --watch
"""

import sys
import os
import argparse
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.etl.database_import.session_refresh_service import SessionRefreshService

def print_status():
    """Print current session refresh system status"""
    try:
        print(f"🔄 SESSION REFRESH SYSTEM STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Get system status
        status = SessionRefreshService.get_refresh_status()
        
        if status.get("signals_table_exists", False):
            print(f"📊 Signals Table: ✅ EXISTS")
            print(f"📈 Total Signals: {status.get('total_signals', 0)}")
            print(f"⏳ Pending Refreshes: {status.get('pending_refreshes', 0)}")
            print(f"✅ Completed Refreshes: {status.get('completed_refreshes', 0)}")
            
            # Show recent signals if any exist
            recent_signals = status.get("recent_signals", [])
            if recent_signals:
                print(f"\n📋 Recent Signals ({len(recent_signals)}):")
                for i, signal in enumerate(recent_signals[:5], 1):
                    status_icon = "✅" if signal.get("is_refreshed") else "⏳"
                    print(f"  {i}. {status_icon} {signal.get('email', 'Unknown')} - {signal.get('league_name', 'Unknown')}")
                    print(f"     Created: {signal.get('created_at', 'Unknown')}")
                    if signal.get("refreshed_at"):
                        print(f"     Refreshed: {signal.get('refreshed_at')}")
                    print()
            else:
                print("\n📋 No recent signals found")
        else:
            print(f"📊 Signals Table: ❌ DOES NOT EXIST")
            print("ℹ️  This is normal if no ETL has run recently with league ID changes")
        
        # Check for any errors
        if "error" in status:
            print(f"\n❌ ERROR: {status['error']}")
        
        print("\n" + "=" * 70)
        
        # Show health assessment
        if status.get("signals_table_exists", False):
            pending = status.get("pending_refreshes", 0)
            if pending > 0:
                print(f"🚨 ATTENTION: {pending} users need session refresh")
                print("   👉 These users will get automatic refresh on next page visit")
            else:
                print("✅ HEALTHY: No pending session refreshes")
        else:
            print("✅ HEALTHY: No ETL league changes detected")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR checking session refresh status: {str(e)}")
        return False

def watch_mode():
    """Watch mode - continuously monitor the system"""
    print("👀 WATCH MODE: Monitoring session refresh system...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            print_status()
            print("\n⏰ Next check in 30 seconds...\n")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")

def main():
    parser = argparse.ArgumentParser(description='Monitor session refresh system')
    parser.add_argument('--watch', action='store_true',
                       help='Watch mode - continuously monitor every 30 seconds')
    
    args = parser.parse_args()
    
    if args.watch:
        watch_mode()
    else:
        success = print_status()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 