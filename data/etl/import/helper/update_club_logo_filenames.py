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
        
        # Generate UPDATE statements for each club
        for club_id, name in clubs:
            logo_filename = generate_logo_filename(name)
            print(f"UPDATE clubs SET logo_filename = '{logo_filename}' WHERE id = {club_id};")
        
        print("\n" + "=" * 50)
        print(f"Generated {len(clubs)} UPDATE statements")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
