#!/usr/bin/env python3
"""
Add Unique Player Constraint to Prevent Duplicate Associations

This script adds a database constraint to ensure that each tenniscores_player_id
can only be associated with one user account.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from database_utils import execute_query, execute_query_one, execute_update

def check_existing_violations():
    """Check for existing violations before adding constraint"""
    
    print("🔍 CHECKING FOR EXISTING CONSTRAINT VIOLATIONS")
    print("=" * 50)
    
    violations_query = """
        SELECT 
            upa.tenniscores_player_id,
            COUNT(DISTINCT upa.user_id) as user_count,
            STRING_AGG(u.email, ', ') as user_emails
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        GROUP BY upa.tenniscores_player_id
        HAVING COUNT(DISTINCT upa.user_id) > 1
        ORDER BY user_count DESC
    """
    
    violations = execute_query(violations_query)
    
    if violations:
        print(f"🚨 Found {len(violations)} constraint violations:")
        for v in violations:
            print(f"   Player ID: {v['tenniscores_player_id']}")
            print(f"   Users: {v['user_count']} ({v['user_emails']})")
        
        print(f"\n❌ Cannot add constraint with existing violations!")
        print(f"   Please run fix_duplicate_player_associations.py first")
        return False
    else:
        print(f"✅ No constraint violations found - safe to add constraint")
        return True


def check_existing_constraint():
    """Check if constraint already exists"""
    
    print("\n🔍 CHECKING FOR EXISTING CONSTRAINT")
    print("=" * 50)
    
    constraint_query = """
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints 
        WHERE table_name = 'user_player_associations' 
        AND constraint_type = 'UNIQUE'
        AND constraint_name LIKE '%tenniscores_player_id%'
    """
    
    existing = execute_query(constraint_query)
    
    if existing:
        print(f"⚠️  Found existing constraint(s):")
        for c in existing:
            print(f"   {c['constraint_name']} ({c['constraint_type']})")
        return True
    else:
        print(f"✅ No existing unique constraint on tenniscores_player_id")
        return False


def add_unique_constraint(dry_run=True):
    """Add unique constraint to prevent duplicate player associations"""
    
    mode = "DRY RUN" if dry_run else "LIVE EXECUTION"
    print(f"\n🔧 ADDING UNIQUE CONSTRAINT - {mode}")
    print("=" * 50)
    
    constraint_sql = """
        ALTER TABLE user_player_associations
        ADD CONSTRAINT unique_tenniscores_player_id 
        UNIQUE (tenniscores_player_id)
    """
    
    index_sql = """
        CREATE INDEX IF NOT EXISTS idx_upa_unique_player_check 
        ON user_player_associations (tenniscores_player_id)
    """
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made to the database")
        print(f"\nWould execute:")
        print(f"1. {constraint_sql.strip()}")
        print(f"2. {index_sql.strip()}")
        return True
    else:
        print("🚨 LIVE MODE - Adding constraint to database")
        
        # Safety check
        confirmation = input("\nType 'CONFIRM' to proceed with adding constraint: ")
        if confirmation != 'CONFIRM':
            print("❌ Aborted - user did not confirm")
            return False
        
        try:
            # Add the unique constraint
            print("Adding unique constraint...")
            execute_update(constraint_sql)
            print("✅ Unique constraint added successfully")
            
            # Add performance index
            print("Adding performance index...")
            execute_update(index_sql)
            print("✅ Performance index added successfully")
            
            # Verify constraint was added
            verify_query = """
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints 
                WHERE table_name = 'user_player_associations' 
                AND constraint_name = 'unique_tenniscores_player_id'
            """
            
            verification = execute_query_one(verify_query)
            if verification:
                print(f"✅ Constraint verification successful: {verification['constraint_name']}")
                return True
            else:
                print(f"❌ Constraint verification failed - constraint not found")
                return False
                
        except Exception as e:
            print(f"❌ Error adding constraint: {e}")
            return False


def test_constraint(dry_run=True):
    """Test the constraint works by attempting to create a violation"""
    
    mode = "DRY RUN" if dry_run else "LIVE TEST"
    print(f"\n🧪 TESTING CONSTRAINT - {mode}")
    print("=" * 50)
    
    if dry_run:
        print("⚠️  DRY RUN MODE - Would test constraint functionality")
        print("   Test would attempt to create duplicate association and verify it fails")
        return True
    
    # Find an existing player association to test with
    existing_test = execute_query_one("""
        SELECT upa.tenniscores_player_id, upa.user_id
        FROM user_player_associations upa
        LIMIT 1
    """)
    
    if not existing_test:
        print("❌ No existing associations found to test with")
        return False
    
    player_id = existing_test['tenniscores_player_id']
    existing_user_id = existing_test['user_id']
    
    # Create a temporary test user
    test_email = f"constraint_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.rally"
    
    try:
        # Create test user
        create_user_sql = """
            INSERT INTO users (email, password_hash, first_name, last_name)
            VALUES (%s, 'test_hash', 'Test', 'User')
            RETURNING id
        """
        
        test_user_result = execute_query_one(create_user_sql, [test_email])
        test_user_id = test_user_result['id']
        
        print(f"Created test user {test_user_id} ({test_email})")
        
        # Attempt to create duplicate association (should fail)
        try:
            duplicate_sql = """
                INSERT INTO user_player_associations (user_id, tenniscores_player_id)
                VALUES (%s, %s)
            """
            
            execute_update(duplicate_sql, [test_user_id, player_id])
            
            # If we get here, constraint failed
            print(f"❌ CONSTRAINT FAILED - Duplicate association was allowed!")
            
            # Clean up the duplicate
            execute_update(
                "DELETE FROM user_player_associations WHERE user_id = %s AND tenniscores_player_id = %s",
                [test_user_id, player_id]
            )
            
            result = False
            
        except Exception as constraint_error:
            if "unique_tenniscores_player_id" in str(constraint_error):
                print(f"✅ CONSTRAINT WORKING - Duplicate association correctly prevented")
                print(f"   Error: {constraint_error}")
                result = True
            else:
                print(f"❌ UNEXPECTED ERROR: {constraint_error}")
                result = False
        
        # Clean up test user
        execute_update("DELETE FROM users WHERE id = %s", [test_user_id])
        print(f"Cleaned up test user {test_user_id}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test setup error: {e}")
        return False


def main():
    """Main execution function"""
    
    print("🏓 RALLY UNIQUE PLAYER CONSTRAINT SETUP")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Check environment
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "local")
    print(f"Environment: {railway_env}")
    
    if railway_env == "production":
        print("⚠️  RUNNING ON PRODUCTION - Use extreme caution!")
        
        confirmation = input("\nType 'PRODUCTION' to confirm you want to run this on production: ")
        if confirmation != 'PRODUCTION':
            print("❌ Aborted - production not confirmed")
            return
    
    # Step 1: Check for existing violations
    if not check_existing_violations():
        print("\n❌ Cannot proceed due to existing violations")
        print("   Run fix_duplicate_player_associations.py first")
        return
    
    # Step 2: Check for existing constraint
    if check_existing_constraint():
        print("\n⚠️  Constraint may already exist - proceeding with caution")
    
    # Step 3: Add constraint (dry run first)
    print("\n" + "=" * 50)
    add_unique_constraint(dry_run=True)
    
    # Step 4: Test constraint (dry run)
    test_constraint(dry_run=True)
    
    # Option to run live
    if railway_env == "production":
        print("\n" + "=" * 50)
        run_live = input("\nAdd constraint live? Type 'YES' to proceed: ")
        if run_live == 'YES':
            if add_unique_constraint(dry_run=False):
                # Test the live constraint
                print("\n" + "=" * 50)
                test_live = input("\nTest constraint functionality? Type 'YES' to test: ")
                if test_live == 'YES':
                    test_constraint(dry_run=False)
            else:
                print("❌ Failed to add constraint")
        else:
            print("Dry run completed. Constraint not added.")
    else:
        print("\nDry run completed. To add constraint live, set RAILWAY_ENVIRONMENT=production")


if __name__ == "__main__":
    main() 