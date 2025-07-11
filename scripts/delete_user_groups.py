#!/usr/bin/env python3
"""
Delete Groups Script
Deletes all groups created by a specific user
"""

import os
import sys

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update

def delete_user_groups(user_email):
    """
    Delete all groups created by a specific user
    
    Args:
        user_email: Email of the user whose groups to delete
    """
    try:
        # First, find the user
        user_query = "SELECT id, first_name, last_name FROM users WHERE email = %s"
        user_result = execute_query(user_query, [user_email])
        
        if not user_result:
            print(f"❌ User with email '{user_email}' not found")
            return False
        
        user = user_result[0]
        user_id = user['id']
        user_name = f"{user['first_name']} {user['last_name']}"
        
        print(f"👤 Found user: {user_name} (ID: {user_id})")
        
        # Find all groups created by this user
        groups_query = "SELECT id, name, description, created_at FROM groups WHERE creator_user_id = %s ORDER BY created_at DESC"
        groups_result = execute_query(groups_query, [user_id])
        
        if not groups_result:
            print(f"✅ No groups found for user {user_name}")
            return True
        
        print(f"\n🔍 Found {len(groups_result)} groups created by {user_name}:")
        for group in groups_result:
            print(f"  - {group['name']} (ID: {group['id']}) - Created: {group['created_at']}")
            if group['description']:
                print(f"    Description: {group['description']}")
        
        # Ask for confirmation
        print(f"\n⚠️  This will delete ALL {len(groups_result)} groups and their members!")
        confirmation = input("Type 'DELETE' to confirm: ")
        
        if confirmation != 'DELETE':
            print("❌ Deletion cancelled")
            return False
        
        # Delete the groups (this will cascade delete group_members due to foreign key constraints)
        deleted_count = 0
        for group in groups_result:
            try:
                # Delete the group (members will be deleted automatically due to CASCADE)
                rows_affected = execute_update("DELETE FROM groups WHERE id = %s", [group['id']])
                if rows_affected > 0:
                    print(f"✅ Deleted group: {group['name']}")
                    deleted_count += 1
                else:
                    print(f"⚠️  Failed to delete group: {group['name']}")
            except Exception as e:
                print(f"❌ Error deleting group {group['name']}: {str(e)}")
        
        print(f"\n🎉 Successfully deleted {deleted_count} out of {len(groups_result)} groups")
        
        # Verify deletion
        remaining_groups = execute_query(groups_query, [user_id])
        if remaining_groups:
            print(f"⚠️  Warning: {len(remaining_groups)} groups still remain")
            return False
        else:
            print("✅ All groups successfully deleted")
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def list_all_groups():
    """List all groups in the system"""
    try:
        query = """
            SELECT g.id, g.name, g.description, g.created_at,
                   u.first_name, u.last_name, u.email,
                   COUNT(gm.id) as member_count
            FROM groups g
            JOIN users u ON g.creator_user_id = u.id
            LEFT JOIN group_members gm ON g.id = gm.group_id
            GROUP BY g.id, g.name, g.description, g.created_at, u.first_name, u.last_name, u.email
            ORDER BY g.created_at DESC
        """
        
        groups = execute_query(query)
        
        if not groups:
            print("✅ No groups found in the system")
            return
        
        print(f"📋 Found {len(groups)} groups in the system:\n")
        
        for group in groups:
            creator_name = f"{group['first_name']} {group['last_name']}"
            print(f"🏷️  Group: {group['name']} (ID: {group['id']})")
            print(f"   👤 Creator: {creator_name} ({group['email']})")
            print(f"   👥 Members: {group['member_count']}")
            print(f"   📅 Created: {group['created_at']}")
            if group['description']:
                print(f"   📝 Description: {group['description']}")
            print()
        
    except Exception as e:
        print(f"❌ Error listing groups: {str(e)}")

def main():
    if len(sys.argv) < 2:
        print("🗑️  Group Deletion Script")
        print("\nUsage:")
        print("  python scripts/delete_user_groups.py <user_email>")
        print("  python scripts/delete_user_groups.py --list")
        print("\nExamples:")
        print("  python scripts/delete_user_groups.py rossfreedman@gmail.com")
        print("  python scripts/delete_user_groups.py --list")
        return
    
    if sys.argv[1] == "--list":
        list_all_groups()
    else:
        user_email = sys.argv[1]
        delete_user_groups(user_email)

if __name__ == "__main__":
    main() 