#!/usr/bin/env python3
"""
Step 3: Test the fix script on local database to verify it works correctly
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from database_utils import execute_query, execute_query_one
import subprocess

def test_fix_locally():
    """Test the fix script on local database"""
    
    print("🧪 Step 3: Testing Fix Script on Local Database")
    print("=" * 60)
    
    # Check current state
    print("📊 Current state before fix:")
    current_state_query = """
        SELECT 
            CASE 
                WHEN tenniscores_match_id IS NULL THEN 'NULL'
                WHEN tenniscores_match_id = '' THEN 'EMPTY'
                WHEN tenniscores_match_id LIKE '%_Line%' THEN 'HAS_LINE'
                ELSE 'OTHER'
            END as id_type,
            COUNT(*) as count
        FROM match_scores
        GROUP BY 1
        ORDER BY count DESC
    """
    
    before_state = execute_query(current_state_query)
    for row in before_state:
        print(f"  {row['id_type']:<10}: {row['count']:>6} records")
    
    # Check specific records that should be updated
    sample_check_query = """
        SELECT id, tenniscores_match_id
        FROM match_scores 
        WHERE id IN (2854607, 2854608, 2854609, 2854610)
        ORDER BY id
    """
    
    print(f"\n🎯 Sample records before fix:")
    before_sample = execute_query(sample_check_query)
    for record in before_sample:
        print(f"  ID {record['id']}: {record['tenniscores_match_id']}")
    
    # Apply the fix (simulate by running the SQL file)
    print(f"\n🔧 Applying fix script...")
    
    try:
        # Use psql to run the SQL file
        result = subprocess.run([
            'psql', 
            '-d', 'rally',
            '-f', 'scripts/fix_production_tenniscores_match_id.sql'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print("✅ Fix script executed successfully")
            if result.stdout:
                print("Output:", result.stdout[-500:])  # Show last 500 chars
        else:
            print("❌ Fix script failed")
            print("Error:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Failed to run SQL script: {e}")
        return False
    
    # Check state after fix
    print(f"\n📊 State after fix:")
    after_state = execute_query(current_state_query)
    for row in after_state:
        print(f"  {row['id_type']:<10}: {row['count']:>6} records")
    
    # Check our sample records
    print(f"\n🎯 Sample records after fix:")
    after_sample = execute_query(sample_check_query)
    for record in after_sample:
        print(f"  ID {record['id']}: {record['tenniscores_match_id']}")
    
    # Verify the fix worked
    verification_query = """
        SELECT 
            COUNT(*) as total_matches,
            COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) as has_match_id,
            ROUND(COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) * 100.0 / COUNT(*), 2) as percentage
        FROM match_scores
    """
    
    verification = execute_query_one(verification_query)
    print(f"\n✅ Verification Results:")
    print(f"  Total matches: {verification['total_matches']}")
    print(f"  With match_id: {verification['has_match_id']}")
    print(f"  Percentage: {verification['percentage']}%")
    
    if verification['percentage'] >= 99.0:
        print(f"🎉 SUCCESS! Fix worked correctly - {verification['percentage']}% of records now have tenniscores_match_id")
        return True
    else:
        print(f"⚠️  WARNING: Only {verification['percentage']}% have match IDs. Expected >99%")
        return False

if __name__ == "__main__":
    success = test_fix_locally()
    
    if success:
        print(f"\n🚀 Ready for Step 4: Apply to production database")
    else:
        print(f"\n❌ Fix needs review before applying to production")
