#!/usr/bin/env python3

"""
Fix Victor's Missing NSTF Association on Railway

Apply the same user_player_association fix that worked locally to Railway database.
"""

import sys
import os

# Add the parent directory to Python path to import from rally
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment to use Railway database
os.environ['USE_RAILWAY_DB'] = 'true'

from database_utils import execute_query, execute_query_one, execute_update

def fix_victor_nstf_railway():
    """Fix Victor's missing NSTF association on Railway"""
    
    print("🚂 Fixing Victor's NSTF Association on Railway")
    print("=" * 50)
    
    # Victor's details (same as local)
    victor_email = 'vforman@gmail.com'
    nstf_player_id = 'nndz-WlNld3libjdndz09'
    
    # 1. Find Victor's user ID on Railway
    user_check = execute_query_one("SELECT id, email FROM users WHERE email = %s", [victor_email])
    if not user_check:
        print(f"❌ Victor ({victor_email}) not found on Railway!")
        return
    
    victor_user_id = user_check['id']
    print(f"✅ Found Victor on Railway: {user_check['email']} (ID: {victor_user_id})")
    
    # 2. Verify the NSTF player record exists on Railway
    player_check = execute_query_one("""
        SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.is_active, l.league_name
        FROM players p
        JOIN leagues l ON p.league_id = l.id
        WHERE p.tenniscores_player_id = %s
    """, [nstf_player_id])
    
    if not player_check:
        print(f"❌ NSTF player record {nstf_player_id} not found on Railway!")
        return
    
    print(f"✅ NSTF player found: {player_check['first_name']} {player_check['last_name']} ({player_check['tenniscores_player_id']})")
    print(f"   League: {player_check['league_name']}")
    print(f"   Active: {player_check['is_active']}")
    
    # 3. Check if association already exists
    existing_link = execute_query_one("""
        SELECT user_id, tenniscores_player_id 
        FROM user_player_associations 
        WHERE user_id = %s AND tenniscores_player_id = %s
    """, [victor_user_id, nstf_player_id])
    
    if existing_link:
        print(f"✅ Association already exists on Railway! Victor is already linked to {nstf_player_id}")
        print("   No action needed - league switching should work.")
        return
    
    # 4. Create the missing association on Railway
    print()
    print("🔧 Creating missing user_player_association on Railway...")
    
    try:
        execute_update("""
            INSERT INTO user_player_associations (user_id, tenniscores_player_id) 
            VALUES (%s, %s)
        """, [victor_user_id, nstf_player_id])
        
        print(f"✅ Successfully linked Victor (user {victor_user_id}) to NSTF player {nstf_player_id} on Railway!")
        
        # 5. Verify the fix worked on Railway
        print()
        print("🔍 Verification - Testing league switch validation on Railway...")
        
        # Test the same query that switch_user_league uses
        nstf_league = execute_query_one("SELECT id FROM leagues WHERE league_id = 'NSTF'", [])
        if nstf_league:
            validation_query = """
                SELECT p.tenniscores_player_id 
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                WHERE u.email = %s AND p.league_id = %s AND p.is_active = true
                LIMIT 1
            """
            
            validation_result = execute_query_one(validation_query, [victor_email, nstf_league['id']])
            
            if validation_result:
                print(f"✅ SUCCESS! League switch validation now passes on Railway for Victor → NSTF")
                print(f"   Found active player: {validation_result['tenniscores_player_id']}")
                print()
                print("🎯 Victor should now be able to switch to NSTF league on the live site!")
            else:
                print("❌ Validation still fails on Railway - there may be another issue")
        
    except Exception as e:
        print(f"❌ Error creating association on Railway: {e}")

if __name__ == "__main__":
    fix_victor_nstf_railway() 