#!/usr/bin/env python3
"""
Update user_contexts table schema to match production.
Rename columns from active_team_id/active_league_id to team_id/league_id.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import execute_query, execute_update

def update_user_contexts_schema():
    """Update user_contexts table schema to match production"""
    
    print("🔄 Updating user_contexts table schema to match production...")
    
    try:
        # Check current schema
        current_columns_result = execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_contexts' 
            ORDER BY ordinal_position
        """)
        
        current_columns = [row['column_name'] for row in current_columns_result]
        print(f"Current columns: {current_columns}")
        
        # Check if we need to update
        if 'active_team_id' in current_columns and 'team_id' not in current_columns:
            print("✅ Updating columns to match production schema...")
            
            # Rename active_team_id to team_id
            success1 = execute_update("ALTER TABLE user_contexts RENAME COLUMN active_team_id TO team_id")
            if success1:
                print("  ✅ Renamed active_team_id → team_id")
            else:
                print("  ❌ Failed to rename active_team_id")
                return False
            
            # Rename active_league_id to league_id  
            success2 = execute_update("ALTER TABLE user_contexts RENAME COLUMN active_league_id TO league_id")
            if success2:
                print("  ✅ Renamed active_league_id → league_id")
            else:
                print("  ❌ Failed to rename active_league_id")
                return False
            
        elif 'team_id' in current_columns:
            print("✅ Schema already matches production (team_id/league_id columns exist)")
            
        else:
            print("❌ Unexpected schema state")
            return False
            
        # Verify final schema
        final_columns_result = execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_contexts' 
            ORDER BY ordinal_position
        """)
        
        final_columns = [row['column_name'] for row in final_columns_result]
        print(f"Final columns: {final_columns}")
        
        # Show sample data
        sample_data = execute_query("SELECT * FROM user_contexts LIMIT 3")
        if sample_data:
            print(f"Sample data ({len(sample_data)} records):")
            for row in sample_data:
                print(f"  {row}")
        
        print("🎉 Schema update completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        return False

if __name__ == "__main__":
    success = update_user_contexts_schema()
    if not success:
        sys.exit(1)
