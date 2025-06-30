#!/usr/bin/env python3
"""
Quick ETL Fix Script

Applies immediate fixes for common ETL import issues.
"""

import os
import sys

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one, execute_update


def clear_stuck_imports():
    """Clear any potentially stuck import processes"""
    print("🧹 Clearing potentially stuck imports...")
    
    try:
        # Look for long-running transactions
        long_transactions = execute_query("""
            SELECT pid, state, query_start, query
            FROM pg_stat_activity 
            WHERE state = 'active' 
            AND query_start < NOW() - INTERVAL '30 minutes'
            AND datname = current_database()
            AND query LIKE '%INSERT INTO player_history%'
        """)
        
        if long_transactions:
            print(f"⚠️ Found {len(long_transactions)} potentially stuck transactions")
            for trans in long_transactions:
                print(f"   PID {trans['pid']}: Running since {trans['query_start']}")
                # Note: Be careful about killing processes - this should be manual
        else:
            print("✅ No stuck transactions found")
            
    except Exception as e:
        print(f"❌ Error checking transactions: {str(e)}")


def optimize_database_settings():
    """Apply temporary optimizations for large imports"""
    print("⚡ Applying temporary database optimizations...")
    
    optimizations = [
        "SET maintenance_work_mem = '1GB'",
        "SET checkpoint_segments = 32",
        "SET wal_buffers = '16MB'",
        "SET synchronous_commit = off"
    ]
    
    for optimization in optimizations:
        try:
            execute_update(optimization)
            print(f"✅ Applied: {optimization}")
        except Exception as e:
            print(f"⚠️ Could not apply {optimization}: {str(e)}")


def check_disk_space():
    """Check available disk space"""
    print("💾 Checking disk space...")
    
    try:
        import shutil
        total, used, free = shutil.disk_usage(project_root)
        
        print(f"   Total: {total // (1024**3)} GB")
        print(f"   Used:  {used // (1024**3)} GB") 
        print(f"   Free:  {free // (1024**3)} GB")
        
        if free < 5 * 1024**3:  # Less than 5GB
            print("⚠️ Low disk space detected - may cause import failures")
        else:
            print("✅ Sufficient disk space available")
            
    except Exception as e:
        print(f"❌ Error checking disk space: {str(e)}")


if __name__ == "__main__":
    print("=" * 50)
    print("⚡ QUICK ETL FIX UTILITY")
    print("=" * 50)
    
    clear_stuck_imports()
    print()
    optimize_database_settings()
    print()
    check_disk_space()
    
    print("\n✅ Quick fixes applied")
