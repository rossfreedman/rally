#!/usr/bin/env python3
"""
Step 1: Verify current production database state before applying fix
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from database_utils import execute_query

def verify_production_state():
    """Check current state of tenniscores_match_id in database"""
    
    print("🔍 Step 1: Verifying Current Database State")
    print("=" * 60)
    
    # Check overall distribution
    distribution_query = """
        SELECT 
            CASE 
                WHEN tenniscores_match_id IS NULL THEN 'NULL'
                WHEN tenniscores_match_id = '' THEN 'EMPTY'
                WHEN tenniscores_match_id LIKE '%_Line%' THEN 'HAS_LINE'
                ELSE 'OTHER'
            END as id_type,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM match_scores), 2) as percentage
        FROM match_scores
        GROUP BY 1
        ORDER BY count DESC
    """
    
    print("📊 Current tenniscores_match_id distribution:")
    distribution = execute_query(distribution_query)
    
    total_matches = sum(row['count'] for row in distribution)
    print(f"Total matches: {total_matches}")
    
    for row in distribution:
        print(f"  {row['id_type']:<10}: {row['count']:>6} records ({row['percentage']:>5}%)")
    
    # Check specific IDs that we plan to update
    check_sample_query = """
        SELECT id, tenniscores_match_id
        FROM match_scores 
        WHERE id IN (2854607, 2854608, 2854609, 2854610, 2836983)
        ORDER BY id
    """
    
    print(f"\n🎯 Sample of records we plan to update:")
    sample_records = execute_query(check_sample_query)
    
    for record in sample_records:
        print(f"  ID {record['id']}: {record['tenniscores_match_id']}")
    
    # Count NULL records that will be updated
    null_count_query = """
        SELECT COUNT(*) as null_count
        FROM match_scores 
        WHERE tenniscores_match_id IS NULL OR tenniscores_match_id = ''
    """
    
    null_result = execute_query(null_count_query)
    null_count = null_result[0]['null_count'] if null_result else 0
    
    print(f"\n📊 Records that need fixing: {null_count}")
    
    if null_count == 0:
        print("✅ All records already have tenniscores_match_id values!")
        return False
    elif null_count > 500:
        print("⚠️  WARNING: More than 500 records need fixing. Please verify this is expected.")
        return True
    else:
        print(f"✅ Ready to fix {null_count} records.")
        return True

if __name__ == "__main__":
    needs_fix = verify_production_state()
    
    if needs_fix:
        print("\n🚀 Next step: Run the SQL fix script")
        print("Command: Apply scripts/fix_production_tenniscores_match_id.sql to production")
    else:
        print("\n✅ No action needed - database is already in good state")
