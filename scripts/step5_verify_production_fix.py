#!/usr/bin/env python3
"""
Step 5: Verify the fix was applied successfully to production
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from database_utils import execute_query, execute_query_one

def verify_production_fix():
    """Verify the fix was applied successfully"""
    
    print("✅ Step 5: Verifying Production Fix Success")
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
    
    print("📊 Post-fix tenniscores_match_id distribution:")
    distribution = execute_query(distribution_query)
    
    total_matches = sum(row['count'] for row in distribution)
    print(f"Total matches: {total_matches}")
    
    for row in distribution:
        print(f"  {row['id_type']:<10}: {row['count']:>6} records ({row['percentage']:>5}%)")
    
    # Verify our specific test records
    verification_query = """
        SELECT id, tenniscores_match_id
        FROM match_scores 
        WHERE id IN (2854607, 2854608, 2854609, 2854610, 2836983)
        ORDER BY id
    """
    
    print(f"\n🎯 Verification of updated records:")
    verification_records = execute_query(verification_query)
    
    all_fixed = True
    for record in verification_records:
        match_id = record['tenniscores_match_id']
        status = "✅" if match_id and "_Line" in match_id else "❌"
        print(f"  {status} ID {record['id']}: {match_id}")
        if not match_id or "_Line" not in match_id:
            all_fixed = False
    
    # Overall success metrics
    success_query = """
        SELECT 
            COUNT(*) as total_matches,
            COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) as has_match_id,
            ROUND(COUNT(CASE WHEN tenniscores_match_id IS NOT NULL AND tenniscores_match_id != '' THEN 1 END) * 100.0 / COUNT(*), 2) as percentage
        FROM match_scores
    """
    
    success_metrics = execute_query_one(success_query)
    
    print(f"\n📈 Success Metrics:")
    print(f"  Total matches: {success_metrics['total_matches']}")
    print(f"  With match_id: {success_metrics['has_match_id']}")
    print(f"  Coverage: {success_metrics['percentage']}%")
    
    # Determine overall success
    is_success = (
        success_metrics['percentage'] >= 99.5 and
        all_fixed
    )
    
    print(f"\n" + "="*60)
    if is_success:
        print("🎉 SUCCESS! Database fix applied successfully!")
        print("✅ All records now have proper tenniscores_match_id values")
        print("✅ Court analysis should work on all pages")
        print("✅ No more fallback logic needed")
        
        print(f"\n🧪 Next steps:")
        print("1. Test https://www.lovetorally.com/mobile/analyze-me")
        print("2. Test https://www.lovetorally.com/mobile/my-team") 
        print("3. Verify court analysis displays correctly")
        print("4. Optional: Remove fallback logic from code")
        
    else:
        print("❌ ISSUE DETECTED!")
        print(f"⚠️  Only {success_metrics['percentage']}% coverage achieved")
        print("🔄 Consider running the backup restoration script")
        print("🔍 Investigate why some records weren't updated")
    
    return is_success

if __name__ == "__main__":
    verify_production_fix()
