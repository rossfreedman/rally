#!/usr/bin/env python3
"""
Fix team 56007 series mismatch in production database

ISSUE: Team 56007 has inconsistent data:
- team_name: "Midt-Bannockburn - 18" (suggests Chicago 18)  
- series_id: points to "Series 13" (WRONG!)

FIX: Update team 56007 to point to correct "Chicago 18" series
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import execute_query, execute_query_one

def diagnose_team_56007():
    """Diagnose the current state of team 56007"""
    print("🔍 DIAGNOSING TEAM 56007")
    print("=" * 50)
    
    # Check current team data
    team_query = """
        SELECT 
            t.id as team_id,
            t.team_name,
            t.series_id,
            s.name as current_series_name,
            c.name as club_name,
            l.league_name
        FROM teams t
        LEFT JOIN series s ON t.series_id = s.id
        LEFT JOIN clubs c ON t.club_id = c.id  
        LEFT JOIN leagues l ON t.league_id = l.id
        WHERE t.id = 56007
    """
    
    team = execute_query_one(team_query)
    if team:
        print(f"📊 CURRENT TEAM 56007 DATA:")
        print(f"   Team Name: {team['team_name']}")
        print(f"   Current Series: {team['current_series_name']} (ID: {team['series_id']})")
        print(f"   Club: {team['club_name']}")
        print(f"   League: {team['league_name']}")
        print()
        
        # Check if this is the problem
        if "18" in team['team_name'] and "13" in team['current_series_name']:
            print("🚨 MISMATCH CONFIRMED!")
            print("   Team name suggests '18' but series is '13'")
            return True
        else:
            print("✅ No mismatch detected")
            return False
    else:
        print("❌ Team 56007 not found")
        return False

def find_correct_chicago18_series():
    """Find the correct Chicago 18 series ID"""
    print("🔍 FINDING CORRECT CHICAGO 18 SERIES")
    print("=" * 50)
    
    # Look for Chicago 18 series in same league
    chicago18_query = """
        SELECT s.id, s.name, l.league_name
        FROM series s
        JOIN leagues l ON s.league_id = l.id
        WHERE s.name = 'Chicago 18' AND l.id = 4783
        LIMIT 1
    """
    
    series = execute_query_one(chicago18_query)
    if series:
        print(f"✅ FOUND CORRECT SERIES:")
        print(f"   Series: {series['name']} (ID: {series['id']})")
        print(f"   League: {series['league_name']}")
        return series['id']
    else:
        print("❌ Chicago 18 series not found in league 4783")
        return None

def fix_team_series():
    """Fix team 56007 to point to correct series"""
    print("🔧 FIXING TEAM 56007 SERIES")
    print("=" * 50)
    
    correct_series_id = find_correct_chicago18_series()
    if not correct_series_id:
        return False
    
    print(f"🔄 Updating team 56007 to series_id: {correct_series_id}")
    
    try:
        update_query = """
            UPDATE teams 
            SET series_id = %s
            WHERE id = 56007
        """
        
        execute_query(update_query, [correct_series_id])
        print("✅ Team 56007 updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Update failed: {e}")
        return False

def verify_fix():
    """Verify the fix worked"""
    print("✅ VERIFYING FIX")
    print("=" * 50)
    
    # Check updated team data
    verify_query = """
        SELECT 
            t.team_name,
            s.name as series_name
        FROM teams t
        JOIN series s ON t.series_id = s.id
        WHERE t.id = 56007
    """
    
    result = execute_query_one(verify_query)
    if result:
        print(f"📊 UPDATED TEAM DATA:")
        print(f"   Team: {result['team_name']}")
        print(f"   Series: {result['series_name']}")
        
        # Check if names now match
        if "18" in result['team_name'] and "18" in result['series_name']:
            print("✅ SUCCESS! Team and series now match!")
            return True
        else:
            print("❌ Still mismatched")
            return False
    else:
        print("❌ Could not verify - team not found")
        return False

def main():
    print("🚀 TEAM 56007 SERIES FIX")
    print("=" * 50)
    print()
    
    # Step 1: Diagnose
    if not diagnose_team_56007():
        print("❌ No issue detected or team not found")
        return
    
    print()
    
    # Step 2: Ask for confirmation
    print("🤔 READY TO FIX TEAM 56007?")
    response = input("Update team 56007 to point to Chicago 18 series? (y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ Fix cancelled")
        return
    
    print()
    
    # Step 3: Apply fix
    if not fix_team_series():
        print("❌ Fix failed")
        return
    
    print()
    
    # Step 4: Verify
    if verify_fix():
        print()
        print("🎉 SUCCESS!")
        print("Aaron should now see 'Series 18 @ Midt-Bannockburn' correctly!")
    else:
        print()
        print("❌ Verification failed")

if __name__ == "__main__":
    main()
