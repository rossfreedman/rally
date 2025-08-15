#!/usr/bin/env python3
"""
Quick fix for Aaron Walsh series mismatch issue
Run this on Railway production to fix the 'Series 13 @ Midt-Bannockburn' issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import execute_query, execute_query_one

def fix_aaron_series():
    print("🔧 FIXING AARON WALSH SERIES MISMATCH")
    
    # Step 1: Find Chicago 18 series ID
    chicago18_query = """
        SELECT s.id, s.name
        FROM series s
        JOIN leagues l ON s.league_id = l.id
        WHERE s.name = 'Chicago 18' AND l.id = 4783
        LIMIT 1
    """
    chicago18 = execute_query_one(chicago18_query)
    
    if not chicago18:
        print("❌ Could not find 'Chicago 18' series")
        return False
        
    print(f"✅ Found series: {chicago18['name']} (ID: {chicago18['id']})")
    
    # Step 2: Update Aaron's player record
    update_query = """
        UPDATE players 
        SET series_id = %s
        WHERE tenniscores_player_id = 'nndz-WkNHeHg3M3dnUT09' 
        AND team_id = 56007
        AND is_active = true
    """
    
    try:
        result = execute_query(update_query, [chicago18['id']])
        print(f"✅ Updated Aaron's player record to series_id: {chicago18['id']}")
        
        # Step 3: Verify fix
        verify_query = """
            SELECT s.name as series_name, t.team_name
            FROM players p
            JOIN series s ON p.series_id = s.id
            JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = 'nndz-WkNHeHg3M3dnUT09'
            AND p.team_id = 56007
        """
        
        verification = execute_query_one(verify_query)
        if verification:
            print(f"✅ Verification: {verification['series_name']} @ {verification['team_name']}")
            return True
        else:
            print("❌ Could not verify fix")
            return False
            
    except Exception as e:
        print(f"❌ Update failed: {e}")
        return False

if __name__ == "__main__":
    fix_aaron_series()
