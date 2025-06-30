#!/usr/bin/env python3
"""
Test script to verify impersonation activity filtering functionality
"""

import sys
sys.path.append('.')

from database_utils import execute_query

def test_impersonation_filtering():
    """Test the impersonation filtering functionality"""
    
    print("🧪 Testing Impersonation Activity Filtering")
    print("=" * 50)
    
    # Test 1: Check for impersonation-marked activities
    print("\n1. Checking for impersonation-marked activities...")
    
    impersonation_activities = execute_query("""
        SELECT 
            id, user_email, activity_type, details, action, timestamp
        FROM user_activity_logs 
        WHERE (details LIKE '%impersonation%' OR action LIKE '%impersonation%')
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    
    print(f"Found {len(impersonation_activities)} impersonation-related activities")
    
    for activity in impersonation_activities[:5]:
        print(f"  📝 {activity['timestamp']} - {activity['user_email']}")
        print(f"     Type: {activity['activity_type']}")
        print(f"     Details: {activity['details']}")
        print()
    
    # Test 2: Compare activity counts with and without impersonation exclusion
    print("\n2. Comparing activity counts...")
    
    # Total activities
    total_count = execute_query("""
        SELECT COUNT(*) as count 
        FROM user_activity_logs ual
        LEFT JOIN users u ON ual.user_email = u.email
        WHERE ual.timestamp IS NOT NULL
        AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
        AND NOT (u.is_admin = true AND ual.user_email = 'rossfreedman@gmail.com')
    """)[0]['count']
    
    # Activities excluding impersonation
    filtered_count = execute_query("""
        SELECT COUNT(*) as count 
        FROM user_activity_logs ual
        LEFT JOIN users u ON ual.user_email = u.email
        WHERE ual.timestamp IS NOT NULL
        AND NOT (ual.page = 'admin_dashboard' AND ual.details = 'Admin accessed activity monitoring dashboard')
        AND NOT (u.is_admin = true AND ual.user_email = 'rossfreedman@gmail.com')
        AND NOT (ual.details LIKE '%impersonation%' OR ual.action LIKE '%impersonation%')
    """)[0]['count']
    
    impersonation_count = total_count - filtered_count
    
    print(f"📊 Activity Count Comparison:")
    print(f"   Total activities: {total_count}")
    print(f"   Non-impersonated: {filtered_count}")
    print(f"   Impersonated: {impersonation_count}")
    print(f"   Percentage impersonated: {(impersonation_count/total_count*100):.1f}%" if total_count > 0 else "   No activities")
    
    # Test 3: Check recent activities to see tagging
    print("\n3. Recent activities with impersonation status...")
    
    recent_activities = execute_query("""
        SELECT 
            id, user_email, activity_type, details, timestamp,
            CASE 
                WHEN details LIKE '%impersonation%' OR action LIKE '%impersonation%' 
                THEN 'IMPERSONATED' 
                ELSE 'REGULAR' 
            END as activity_source
        FROM user_activity_logs 
        WHERE timestamp >= NOW() - INTERVAL '24 hours'
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    
    for activity in recent_activities:
        source_icon = "🎭" if activity['activity_source'] == 'IMPERSONATED' else "👤"
        print(f"  {source_icon} {activity['timestamp']} - {activity['user_email']} [{activity['activity_source']}]")
        details_text = (activity['details'] or 'No details')[:80]
        print(f"     {activity['activity_type']}: {details_text}...")
        print()
    
    print("\n✅ Impersonation filtering test completed!")
    print("\n💡 To use the filtering in the admin dashboard:")
    print("   1. Go to http://localhost:8080/admin/dashboard")
    print("   2. In the filters section, check 'Hide impersonated activities'")
    print("   3. Click 'Apply Filters' to see only genuine user activities")

if __name__ == "__main__":
    test_impersonation_filtering() 