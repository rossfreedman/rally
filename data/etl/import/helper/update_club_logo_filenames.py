#!/usr/bin/env python3
"""
Script to update club logo_filename column with standardized filenames.
Format: static/images/clubs/{clubname}_logo.png
"""

import os
import psycopg2
import re
from dotenv import load_dotenv

def clean_club_name(name):
    """Convert club name to filename-safe format"""
    # Convert to lowercase
    name = name.lower()
    
    # Remove or replace special characters
    name = re.sub(r'[^a-z0-9]', '', name)  # Keep only alphanumeric
    
    return name

def generate_logo_filename(club_name):
    """Generate logo filename for club"""
    clean_name = clean_club_name(club_name)
    return f"static/images/clubs/{clean_name}_logo.png"

def main():
    # Load environment variables
    load_dotenv()
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable is not set")
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # Get all clubs
        cursor.execute('SELECT id, name FROM clubs ORDER BY id')
        clubs = cursor.fetchall()
        
        print("Club logo filename updates:")
        print("=" * 50)
        
        # Execute UPDATE statements for each club
        updated_count = 0
        for club_id, name in clubs:
            logo_filename = generate_logo_filename(name)
            try:
                cursor.execute(
                    "UPDATE clubs SET logo_filename = %s WHERE id = %s",
                    (logo_filename, club_id)
                )
                updated_count += 1
                print(f"✅ Updated: {name} -> {logo_filename}")
            except Exception as e:
                print(f"❌ Failed to update {name}: {e}")
        
        # Commit the changes
        conn.commit()
        
        print("\n" + "=" * 50)
        print(f"Successfully updated {updated_count} clubs with logo filenames")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
