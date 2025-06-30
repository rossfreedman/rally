#!/usr/bin/env python3
"""
Resume ETL Import Script

This script can resume a failed ETL import from where it left off,
particularly useful for player_history imports that failed partway through.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one


def check_import_status():
    """Check what has been imported so far"""
    print("🔍 Checking current import status...")
    
    tables = ['leagues', 'clubs', 'series', 'teams', 'players', 'player_history', 'match_scores', 'series_stats']
    
    for table in tables:
        try:
            count = execute_query_one(f"SELECT COUNT(*) as count FROM {table}")
            print(f"  {table}: {count['count']:,} records")
        except Exception as e:
            print(f"  {table}: ERROR - {str(e)}")
    
    # Check latest player_history import
    try:
        latest = execute_query_one("""
            SELECT MAX(created_at) as latest_import, COUNT(*) as total_records
            FROM player_history
        """)
        
        if latest['latest_import']:
            print(f"\n📅 Latest player_history import: {latest['latest_import']}")
            print(f"📊 Total player_history records: {latest['total_records']:,}")
        else:
            print("\n📅 No player_history imports found")
            
    except Exception as e:
        print(f"\n❌ Error checking player_history: {str(e)}")


def resume_player_history_import():
    """Resume player history import with better error handling"""
    print("\n🔄 Resuming player history import...")
    
    # Load player history data
    player_history_path = os.path.join(project_root, "data", "leagues", "all", "player_history.json")
    
    if not os.path.exists(player_history_path):
        print(f"❌ Player history file not found: {player_history_path}")
        return False
    
    try:
        with open(player_history_path, 'r', encoding='utf-8') as f:
            player_history_data = json.load(f)
        
        print(f"📋 Loaded {len(player_history_data):,} player history records from JSON")
        
        # Check what's already imported
        existing_count = execute_query_one("SELECT COUNT(*) as count FROM player_history")['count']
        print(f"📊 Already imported: {existing_count:,} records")
        
        if existing_count >= len(player_history_data):
            print("✅ Player history import appears to be complete")
            return True
        
        print(f"🎯 Need to import approximately {len(player_history_data) - existing_count:,} more records")
        
        # Suggest running the main import script with resilience patches
        print("\n💡 RECOMMENDATION:")
        print("   1. Run the diagnostic script first: python scripts/diagnose_etl_failure.py")
        print("   2. Clear any stuck processes via admin interface")
        print("   3. Retry the import via admin ETL interface")
        print("   4. The patched import script will be more resilient to errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during resume analysis: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🔄 ETL IMPORT RESUME UTILITY")
    print("=" * 60)
    
    check_import_status()
    resume_player_history_import()
    
    print("\n" + "=" * 60)
    print("✅ Resume analysis complete")
    print("=" * 60)
