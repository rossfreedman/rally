#!/usr/bin/env python3
"""
Check clubs table structure
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db

def check_clubs_table():
    """Check clubs table structure"""
    print("=== Checking Clubs Table Structure ===")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'clubs' 
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("Clubs table columns:")
        for col in columns:
            print(f"  {col[0]} ({col[1]}) - Nullable: {col[2]}")
        
        # Get sample data
        cursor.execute("SELECT * FROM clubs LIMIT 3")
        rows = cursor.fetchall()
        
        print(f"\nSample club data ({len(rows)} rows):")
        for row in rows:
            print(f"  {row}")

if __name__ == "__main__":
    check_clubs_table() 