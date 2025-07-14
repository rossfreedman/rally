#!/usr/bin/env python3
"""
Test script to verify admin users sorting by recent activity
"""

import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.admin_service import get_all_users

def test_admin_users_sorting():
    """Test that users are sorted by most recent activity"""
    print("🧪 Testing admin users sorting by recent activity...")
    
    try:
        # Get all users
        users = get_all_users()
        
        if not users:
            print("❌ No users found")
            return False
        
        print(f"✅ Found {len(users)} users")
        
        # Check if users are sorted by most_recent_activity (newest first)
        print("\n📊 Checking sorting order:")
        for i, user in enumerate(users[:10]):  # Show first 10 users
            most_recent = user.get('most_recent_activity')
            if most_recent:
                if isinstance(most_recent, str):
                    most_recent = datetime.fromisoformat(most_recent.replace('Z', '+00:00'))
                formatted_time = most_recent.strftime('%Y-%m-%d %H:%M:%S')
            else:
                formatted_time = "No activity"
            
            print(f"  {i+1}. {user['first_name']} {user['last_name']} ({user['email']})")
            print(f"      Most Recent Activity: {formatted_time}")
            print(f"      Recent Activity Count: {user.get('recent_activity_count', 0)}")
            print()
        
        # Verify sorting
        most_recent_activities = []
        for user in users:
            most_recent = user.get('most_recent_activity')
            if most_recent:
                if isinstance(most_recent, str):
                    most_recent = datetime.fromisoformat(most_recent.replace('Z', '+00:00'))
                most_recent_activities.append(most_recent)
            else:
                most_recent_activities.append(datetime.min)
        
        # Check if sorted in descending order (newest first)
        is_sorted = all(most_recent_activities[i] >= most_recent_activities[i+1] 
                       for i in range(len(most_recent_activities)-1))
        
        if is_sorted:
            print("✅ Users are correctly sorted by most recent activity (newest first)")
        else:
            print("❌ Users are NOT correctly sorted by most recent activity")
            
        # Show some statistics
        active_users = [u for u in users if u.get('has_recent_activity', False)]
        print(f"\n📈 Statistics:")
        print(f"  Total users: {len(users)}")
        print(f"  Active users (24h): {len(active_users)}")
        print(f"  Inactive users: {len(users) - len(active_users)}")
        
        return is_sorted
        
    except Exception as e:
        print(f"❌ Error testing admin users sorting: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_admin_users_sorting()
    sys.exit(0 if success else 1) 