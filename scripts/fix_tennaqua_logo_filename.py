#!/usr/bin/env python3
"""
Fix Tennaqua Logo Filename

This script fixes the Tennaqua logo filename from .jpeg to .png in the database.
The actual file is tennaqua_logo.png, but some database records may have .jpeg.
"""

import os
import sys

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db
from datetime import datetime

def fix_tennaqua_logo_filename():
    """Fix Tennaqua logo filename in database"""
    print("🔧 Fixing Tennaqua logo filename...")
    print("=" * 50)
    
    try:
        # Get database connection
        with get_db() as conn:
            with conn.cursor() as cursor:
                # Check current state
                cursor.execute("""
                    SELECT id, name, logo_filename 
                    FROM clubs 
                    WHERE name = 'Tennaqua'
                """)
                
                current = cursor.fetchone()
                if not current:
                    print("❌ Tennaqua club not found in database")
                    return False
                    
                club_id, club_name, current_logo = current
                print(f"📋 Current Tennaqua club record:")
                print(f"   ID: {club_id}")
                print(f"   Name: {club_name}")
                print(f"   Current logo: {current_logo}")
                
                # Check if fix is needed
                if current_logo == 'static/images/clubs/tennaqua_logo.png':
                    print("✅ Logo filename is already correct (.png)")
                    return True
                elif current_logo == 'static/images/clubs/tennaqua_logo.jpeg':
                    print("🔧 Fixing logo filename from .jpeg to .png...")
                    
                    # Update the logo filename
                    cursor.execute("""
                        UPDATE clubs 
                        SET logo_filename = 'static/images/clubs/tennaqua_logo.png'
                        WHERE name = 'Tennaqua'
                    """)
                    
                    conn.commit()
                    
                    # Verify the fix
                    cursor.execute("""
                        SELECT logo_filename 
                        FROM clubs 
                        WHERE name = 'Tennaqua'
                    """)
                    
                    updated_logo = cursor.fetchone()[0]
                    print(f"✅ Logo filename updated to: {updated_logo}")
                    
                else:
                    print(f"⚠️  Unexpected logo filename: {current_logo}")
                    print("🔧 Setting to correct .png filename...")
                    
                    cursor.execute("""
                        UPDATE clubs 
                        SET logo_filename = 'static/images/clubs/tennaqua_logo.png'
                        WHERE name = 'Tennaqua'
                    """)
                    
                    conn.commit()
                    print("✅ Logo filename set to correct .png filename")
        
        # Verify the file exists
        logo_path = os.path.join(project_root, 'static', 'images', 'clubs', 'tennaqua_logo.png')
        if os.path.exists(logo_path):
            print(f"✅ Logo file exists at: {logo_path}")
        else:
            print(f"❌ Logo file not found at: {logo_path}")
            return False
        
        print("🎉 Tennaqua logo filename fix completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing Tennaqua logo filename: {str(e)}")
        return False

if __name__ == "__main__":
    success = fix_tennaqua_logo_filename()
    sys.exit(0 if success else 1) 