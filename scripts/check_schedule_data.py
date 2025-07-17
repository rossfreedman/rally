#!/usr/bin/env python3
"""
Check schedule table data to understand why team IDs are NULL
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_schedule_data():
    """Check schedule table structure and data"""
    
    print("🔍 Checking Schedule Table Data")
    print("=" * 50)
    
    # Staging database URL
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        # Parse and connect to staging database
        parsed = urlparse(staging_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port
        )
        
        cursor = conn.cursor()
        
        # Check table structure
        print("1. 📋 Schedule Table Structure:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'schedule' 
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f"   - {col[0]}: {col[1]} (nullable: {col[1]})")
        
        print()
        
        # Check sample data
        print("2. 📊 Sample Schedule Data:")
        cursor.execute("""
            SELECT id, match_date, match_time, home_team, away_team, home_team_id, away_team_id
            FROM schedule 
            WHERE match_date >= CURRENT_DATE
            ORDER BY match_date ASC
            LIMIT 10
        """)
        rows = cursor.fetchall()
        
        if rows:
            for row in rows:
                print(f"   - ID: {row[0]}, Date: {row[1]}, Time: {row[2]}")
                print(f"     Home: '{row[3]}' (ID: {row[5]})")
                print(f"     Away: '{row[4]}' (ID: {row[6]})")
                print()
        else:
            print("   No upcoming schedule entries found")
        
        print()
        
        # Check if we can match team names to IDs
        print("3. 🔗 Team Name to ID Matching:")
        cursor.execute("""
            SELECT DISTINCT home_team, away_team 
            FROM schedule 
            WHERE match_date >= CURRENT_DATE
            LIMIT 5
        """)
        team_names = cursor.fetchall()
        
        for home, away in team_names:
            if home:
                cursor.execute("SELECT id, team_name FROM teams WHERE team_name ILIKE %s", [f"%{home}%"])
                home_match = cursor.fetchone()
                print(f"   '{home}' -> {home_match[1] if home_match else 'No match'} (ID: {home_match[0] if home_match else 'N/A'})")
            
            if away:
                cursor.execute("SELECT id, team_name FROM teams WHERE team_name ILIKE %s", [f"%{away}%"])
                away_match = cursor.fetchone()
                print(f"   '{away}' -> {away_match[1] if away_match else 'No match'} (ID: {away_match[0] if away_match else 'N/A'})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_schedule_data() 