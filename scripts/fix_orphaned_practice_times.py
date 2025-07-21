#!/usr/bin/env python3
"""
Fix Orphaned Practice Times
===========================

This script fixes orphaned practice times that have team_id references
pointing to non-existent teams after ETL imports.

Usage:
    python scripts/fix_orphaned_practice_times.py [--dry-run]
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.etl.database_import.bulletproof_team_id_preservation import BulletproofTeamPreservation

def fix_orphaned_practice_times(dry_run=False):
    """Fix orphaned practice times using the bulletproof system"""
    
    print("🔧 FIXING ORPHANED PRACTICE TIMES")
    print("=" * 50)
    
    with BulletproofTeamPreservation() as preservation:
        try:
            # Run health check first
            print("🔍 Running health check...")
            health = preservation.validate_health()
            
            practice_times_issues = health['stats'].get('orphaned_practice_times_total', 0)
            
            if practice_times_issues == 0:
                print("✅ No orphaned practice times found - system is healthy!")
                return True
            
            print(f"🚨 Found {practice_times_issues} orphaned practice times:")
            print(f"   • Schedule table: {health['stats'].get('orphaned_practice_times_schedule', 0)}")
            print(f"   • Practice times table: {health['stats'].get('orphaned_practice_times_table', 0)}")
            
            if dry_run:
                print("\n🧪 DRY RUN MODE - No changes will be made")
                print("Would fix orphaned practice times using:")
                print("   1. Team mapping backup (if available)")
                print("   2. Pattern-based matching by location and league")
                return True
            
            # Apply fixes
            print("\n🔧 Applying fixes...")
            repair_stats = preservation.auto_repair_orphans()
            
            practice_times_fixed = repair_stats.get('practice_times_fixed', 0)
            
            if practice_times_fixed > 0:
                print(f"✅ Fixed {practice_times_fixed} orphaned practice times")
            else:
                print("⚠️  No practice times were fixed automatically")
            
            # Run health check again
            print("\n🔍 Running final health check...")
            final_health = preservation.validate_health()
            final_issues = final_health['stats'].get('orphaned_practice_times_total', 0)
            
            if final_issues == 0:
                print("✅ All practice times successfully fixed!")
            elif final_issues < practice_times_issues:
                print(f"✅ Partially fixed: {practice_times_issues - final_issues} practice times fixed, {final_issues} remain")
            else:
                print(f"❌ No improvement: {final_issues} practice times still orphaned")
            
            return final_issues == 0
            
        except Exception as e:
            print(f"❌ Error fixing practice times: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Fix orphaned practice times')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test run without making changes')
    
    args = parser.parse_args()
    
    success = fix_orphaned_practice_times(dry_run=args.dry_run)
    
    if success:
        print("\n🎉 Practice times fix completed successfully!")
    else:
        print("\n❌ Practice times fix failed or incomplete")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 