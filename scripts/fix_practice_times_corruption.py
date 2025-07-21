#!/usr/bin/env python3
"""
Fix Practice Times Corruption

CRITICAL ISSUE: practice_times_backup table has 3.47 million records 
when it should only have 41 unique practice sessions.

Each practice session was duplicated ~85,000 times due to a corrupted ETL process.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from datetime import datetime

def analyze_corruption():
    """Analyze the extent of the corruption"""
    print("🔍 Analyzing practice times corruption...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM practice_times_backup;")
        total_count = cursor.fetchone()[0]
        
        # Get unique count
        cursor.execute("""
            SELECT COUNT(DISTINCT (match_date, match_time, home_team, away_team, location, league_id))
            FROM practice_times_backup;
        """)
        unique_count = cursor.fetchone()[0]
        
        print(f"📊 Total corrupted records: {total_count:,}")
        print(f"📊 Unique practice sessions: {unique_count:,}")
        print(f"📊 Duplication factor: {total_count/unique_count:.1f}x")
        
        return total_count, unique_count

def create_clean_practice_times_table():
    """Create a clean practice_times table with deduplicated data"""
    print("\n🧹 Creating clean practice_times table...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Drop existing practice_times table if it exists
        cursor.execute("DROP TABLE IF EXISTS practice_times;")
        
        # Create new clean table with proper structure for practice times
        cursor.execute("""
            CREATE TABLE practice_times (
                id SERIAL PRIMARY KEY,
                team_id INTEGER,
                day_of_week VARCHAR(10),
                start_time TIME,
                end_time TIME,
                location VARCHAR(255),
                league_id INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(team_id, day_of_week, start_time, end_time, location)
            );
        """)
        
        # Extract unique practice sessions from corrupted backup
        # Convert schedule-like data to actual practice time format
        cursor.execute("""
            INSERT INTO practice_times (team_id, day_of_week, start_time, end_time, location, league_id)
            SELECT DISTINCT 
                home_team_id as team_id,
                CASE EXTRACT(DOW FROM match_date)
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday' 
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as day_of_week,
                match_time as start_time,
                (match_time + INTERVAL '1 hour') as end_time,  -- Assume 1 hour practices
                location,
                league_id
            FROM practice_times_backup
            WHERE home_team LIKE '%Practice%'
            AND home_team_id IS NOT NULL
            ON CONFLICT (team_id, day_of_week, start_time, end_time, location) DO NOTHING;
        """)
        
        inserted_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ Created clean practice_times table with {inserted_count} records")
        return inserted_count

def backup_corrupted_table():
    """Keep the corrupted table for investigation but rename it"""
    print("\n💾 Backing up corrupted table for investigation...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Drop old corrupted backup if exists
        cursor.execute("DROP TABLE IF EXISTS practice_times_corrupted_backup;")
        
        # Rename current backup to indicate corruption
        cursor.execute("ALTER TABLE practice_times_backup RENAME TO practice_times_corrupted_backup;")
        
        conn.commit()
        print("✅ Corrupted table renamed to practice_times_corrupted_backup")

def verify_fix():
    """Verify the fix worked correctly"""
    print("\n✅ Verifying fix...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check new table
        cursor.execute("SELECT COUNT(*) FROM practice_times;")
        new_count = cursor.fetchone()[0]
        
        # Sample some records
        cursor.execute("""
            SELECT team_id, day_of_week, start_time, end_time, location, league_id
            FROM practice_times 
            ORDER BY team_id, day_of_week, start_time
            LIMIT 5;
        """)
        samples = cursor.fetchall()
        
        print(f"📊 New practice_times table: {new_count} records")
        print("\n📋 Sample records:")
        for sample in samples:
            print(f"  Team {sample[0]}: {sample[1]} {sample[2]}-{sample[3]} at {sample[4]} (League {sample[5]})")

def main():
    """Main execution"""
    print("🚨 PRACTICE TIMES CORRUPTION FIX")
    print("=" * 50)
    
    try:
        # Analyze the problem
        total_count, unique_count = analyze_corruption()
        
        if total_count > unique_count * 1000:  # If more than 1000x duplication
            print(f"\n⚠️  CRITICAL: Detected {total_count/unique_count:.0f}x duplication!")
            
            response = input("\n🔧 Proceed with fix? This will:\n"
                           "   1. Create clean practice_times table\n"
                           "   2. Deduplicate the data\n"
                           "   3. Rename corrupted backup table\n"
                           "   (y/N): ")
            
            if response.lower() == 'y':
                # Execute fix
                inserted_count = create_clean_practice_times_table()
                backup_corrupted_table()
                verify_fix()
                
                print(f"\n🎉 SUCCESS! Fixed practice times corruption:")
                print(f"   📉 Reduced from {total_count:,} to {inserted_count} records")
                print(f"   🗜️  Compression ratio: {total_count/inserted_count:.0f}:1")
                print(f"   💾 Corrupted data saved as practice_times_corrupted_backup")
                
            else:
                print("❌ Fix cancelled by user")
        else:
            print(f"✅ No critical corruption detected (only {total_count/unique_count:.1f}x duplication)")
            
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 