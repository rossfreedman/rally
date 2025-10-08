#!/usr/bin/env python3
"""
Import missing SW series for APTA_CHICAGO
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database_config import get_db

def import_missing_sw_series():
    """Import the missing SW series for APTA_CHICAGO."""
    print("🔧 Importing Missing SW Series for APTA_CHICAGO")
    print("=" * 50)
    
    # Missing SW series that need to be imported
    missing_series = [
        'Series 15 SW',
        'Series 17 SW', 
        'Series 19 SW',
        'Series 21 SW',
        'Series 23 SW',
        'Series 25 SW',
        'Series 27 SW',
        'Series 29 SW',
        'Series 31 SW'
    ]
    
    league_id = 4783  # APTA_CHICAGO league ID
    
    try:
        with get_db() as db:
            cursor = db.cursor()
            
            print(f"Importing {len(missing_series)} missing SW series...")
            
            for series_name in missing_series:
                # Check if series already exists
                cursor.execute('SELECT id FROM series WHERE league_id = %s AND name = %s', (league_id, series_name))
                existing = cursor.fetchone()
                
                if existing:
                    print(f"  ✅ {series_name}: Already exists (ID: {existing[0]})")
                else:
                    # Insert new series
                    cursor.execute("""
                        INSERT INTO series (name, league_id, display_name, updated_at)
                        VALUES (%s, %s, %s, NOW())
                        RETURNING id
                    """, (series_name, league_id, series_name,))
                    
                    series_id = cursor.fetchone()[0]
                    print(f"  ✅ {series_name}: Created (ID: {series_id})")
            
            # Commit the changes
            db.commit()
            print(f"\n✅ Successfully imported {len(missing_series)} SW series!")
            
            # Verify the import
            print("\n🔍 Verifying import...")
            cursor.execute('SELECT COUNT(*) FROM series WHERE league_id = %s AND name LIKE %s', (league_id, '%SW%'))
            total_sw_series = cursor.fetchone()[0]
            print(f"Total SW series in database: {total_sw_series}")
            
            # Show all SW series
            cursor.execute('SELECT id, name FROM series WHERE league_id = %s AND name LIKE %s ORDER BY name', (league_id, '%SW%'))
            all_sw_series = cursor.fetchall()
            print(f"\nAll SW series:")
            for series_id, series_name in all_sw_series:
                print(f"  {series_id}: {series_name}")
            
    except Exception as e:
        print(f"❌ Error importing SW series: {e}")
        raise

if __name__ == "__main__":
    import_missing_sw_series()
