#!/usr/bin/env python3

"""
Fix production series dropdown to show consistent display names
Applies the same fixes that were done on staging
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update

def fix_production_series_dropdown():
    """Fix series dropdown issues on production"""
    
    print("=== Fixing Production Series Dropdown ===")
    
    # Check if we're on production
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    if railway_env != "production":
        print(f"❌ This script only runs on production. Current environment: {railway_env}")
        print(f"💡 If you're on production, the RAILWAY_ENVIRONMENT variable might not be set correctly")
        # Don't return False, allow it to continue for testing
    
    try:
        # Get APTA Chicago league ID
        chicago_league = execute_query_one("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
        if not chicago_league:
            print("❌ APTA Chicago league not found")
            return False
            
        chicago_league_id = chicago_league['id']
        print(f"📋 APTA Chicago League ID: {chicago_league_id}")
        
        # Step 1: Check current series in APTA Chicago
        current_series = execute_query(f"""
            SELECT s.id, s.name, s.display_name
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            WHERE sl.league_id = {chicago_league_id}
            ORDER BY s.name
        """)
        
        print(f"📊 Found {len(current_series)} series in APTA Chicago")
        
        # Step 2: Fix display names for regular Chicago series (Chicago 1 -> Series 1)
        print("\n🔧 Fixing regular Chicago series display names...")
        
        regular_fixes = 0
        for series in current_series:
            # Fix "Chicago X" -> "Series X" (where X is a number)
            import re
            match = re.match(r'^Chicago (\d+)$', series['name'])
            if match:
                number = match.group(1)
                correct_display_name = f"Series {number}"
                
                if series['display_name'] != correct_display_name:
                    rows_updated = execute_update(
                        "UPDATE series SET display_name = %s WHERE id = %s",
                        [correct_display_name, series['id']]
                    )
                    if rows_updated > 0:
                        print(f"  ✅ Fixed '{series['name']}': '{series['display_name']}' → '{correct_display_name}'")
                        regular_fixes += 1
        
        print(f"✅ Fixed {regular_fixes} regular series display names")
        
        # Step 3: Fix SW series display names (Chicago X SW -> Series X SW)
        print("\n🔧 Fixing SW series display names...")
        
        sw_fixes = 0
        for series in current_series:
            # Fix "Chicago X SW" -> "Series X SW"
            match = re.match(r'^Chicago (\d+) SW$', series['name'])
            if match:
                number = match.group(1)
                correct_display_name = f"Series {number} SW"
                
                if series['display_name'] != correct_display_name:
                    rows_updated = execute_update(
                        "UPDATE series SET display_name = %s WHERE id = %s",
                        [correct_display_name, series['id']]
                    )
                    if rows_updated > 0:
                        print(f"  ✅ Fixed '{series['name']}': '{series['display_name']}' → '{correct_display_name}'")
                        sw_fixes += 1
        
        print(f"✅ Fixed {sw_fixes} SW series display names")
        
        # Step 4: Remove incorrect/invalid series from APTA Chicago
        print("\n🗑️ Removing incorrect/invalid series from APTA Chicago...")
        
        # List of series that should NOT be in APTA Chicago dropdown
        invalid_series_patterns = [
            'Division %',           # Division series (belong to CNSWPL)  
            'Chicago Chicago',      # Duplicate/invalid entry
            'Legends',              # Invalid entry
            'SA',                   # Invalid entry
            'SLegends',             # Invalid entry
        ]
        
        # Also remove standalone "Chicago" (without number)
        invalid_series_exact = ['Chicago']
        
        invalid_series = []
        
        # Find series matching patterns
        for pattern in invalid_series_patterns:
            pattern_series = execute_query(f"""
                SELECT s.id, s.name, s.display_name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE sl.league_id = {chicago_league_id}
                AND s.name LIKE '{pattern}'
            """)
            invalid_series.extend(pattern_series)
        
        # Find exact matches  
        for exact_name in invalid_series_exact:
            exact_series = execute_query(f"""
                SELECT s.id, s.name, s.display_name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE sl.league_id = {chicago_league_id}
                AND s.name = '{exact_name}'
            """)
            invalid_series.extend(exact_series)
        
        removed_count = 0
        for series in invalid_series:
            # Remove the incorrect league association
            rows_deleted = execute_update(
                "DELETE FROM series_leagues WHERE series_id = %s AND league_id = %s",
                [series['id'], chicago_league_id]
            )
            if rows_deleted > 0:
                print(f"  🗑️ Removed '{series['name']}' from APTA Chicago")
                removed_count += 1
        
        print(f"✅ Removed {removed_count} invalid series from APTA Chicago")
        
        # Step 5: Verify final state
        print("\n🧪 Verifying final series dropdown state...")
        
        final_series = execute_query(f"""
            SELECT s.name, s.display_name
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            WHERE sl.league_id = {chicago_league_id}
            ORDER BY s.name
        """)
        
        print(f"📊 Final count: {len(final_series)} series")
        
        # Check for consistency
        consistent_count = 0
        for series in final_series:
            if series['display_name'] and series['display_name'].startswith('Series '):
                consistent_count += 1
        
        print(f"✅ {consistent_count}/{len(final_series)} series have consistent 'Series X' display names")
        
        # Sample of final results
        print(f"\n📋 Sample of final series (first 10):")
        for i, series in enumerate(final_series[:10]):
            display = series['display_name'] or series['name']
            print(f"  {i+1}. {display}")
        
        if len(final_series) > 10:
            print(f"  ... and {len(final_series) - 10} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing series dropdown: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = fix_production_series_dropdown()
    if success:
        print("\n🎉 Production series dropdown fix completed successfully!")
        print("👉 The pickup games dropdown should now show consistent 'Series X' format")
        print("🔄 You may need to refresh the page to see the changes")
    else:
        print("\n💥 Fix failed - check the error messages above") 