#!/usr/bin/env python3
"""
Check and fix phone_number column in users table
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one, execute_update


def check_and_fix_phone_number_column():
    """Check if phone_number column exists and add it if missing"""
    
    print("🔍 Checking phone_number column in users table...")
    
    try:
        # Check if phone_number column exists
        column_check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'phone_number'
        """
        
        column_exists = execute_query_one(column_check_query)
        
        if column_exists:
            print("✅ phone_number column already exists in users table")
            return True
        else:
            print("❌ phone_number column missing from users table")
            print("🔧 Adding phone_number column...")
            
            # Add the phone_number column
            add_column_query = """
                ALTER TABLE users 
                ADD COLUMN phone_number VARCHAR(20)
            """
            
            result = execute_update(add_column_query)
            
            if result is not None:
                print("✅ phone_number column added successfully")
                
                # Create index for performance
                index_query = """
                    CREATE INDEX IF NOT EXISTS idx_users_phone_number 
                    ON users(phone_number) 
                    WHERE phone_number IS NOT NULL
                """
                
                execute_update(index_query)
                print("✅ Index created for phone_number column")
                return True
            else:
                print("❌ Failed to add phone_number column")
                return False
                
    except Exception as e:
        print(f"❌ Error checking/fixing phone_number column: {str(e)}")
        return False


if __name__ == "__main__":
    success = check_and_fix_phone_number_column()
    if success:
        print("\n✅ Phone number column check/fix completed successfully")
    else:
        print("\n❌ Phone number column check/fix failed")
        sys.exit(1) 