#!/usr/bin/env python3
import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor

def fix_player_availability():
    """Fix the player_availability table migration"""
    
    # Database connection strings
    old_db_url = "postgresql://postgres:OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf@trolley.proxy.rlwy.net:34555/railway"
    new_db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
    
    print("🔧 Fixing player_availability table")
    print("=" * 50)
    
    try:
        # Connect to both databases
        old_conn = psycopg2.connect(old_db_url)
        new_conn = psycopg2.connect(new_db_url)
        
        old_cursor = old_conn.cursor(cursor_factory=RealDictCursor)
        new_cursor = new_conn.cursor()
        
        print("✅ Connected to both databases")
        
        # Check the schema differences first
        print("\n🔍 Checking schema differences...")
        
        print("OLD player_availability columns:")
        old_cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'player_availability' 
            ORDER BY ordinal_position
        """)
        old_columns = [row['column_name'] for row in old_cursor.fetchall()]
        print(f"  {', '.join(old_columns)}")
        
        print("NEW player_availability columns:")
        new_cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'player_availability' 
            ORDER BY ordinal_position
        """)
        new_columns = [row[0] for row in new_cursor.fetchall()]
        print(f"  {', '.join(new_columns)}")
        
        # Fix the schema by adding the missing column mapping
        print("\n🔧 Fixing column mapping...")
        
        # Get sample data to see the structure
        old_cursor.execute("SELECT * FROM player_availability LIMIT 1")
        sample_row = old_cursor.fetchone()
        if sample_row:
            print("Sample old data:")
            for key, value in sample_row.items():
                print(f"  {key}: {value}")
        
        # Now migrate with proper column mapping
        print("\n📦 Migrating player_availability with column mapping...")
        
        # Get all data from old table
        old_cursor.execute("SELECT * FROM player_availability")
        rows = old_cursor.fetchall()
        
        print(f"Found {len(rows)} rows to migrate")
        
        # Clear existing data
        new_cursor.execute("DELETE FROM player_availability")
        
        # Manual mapping based on what we know:
        # OLD: id, player_name, match_date, availability_status, updated_at, series_id
        # NEW: id, player_name, match_date, series_id, availability, submitted_at
        
        migrated_count = 0
        for row in rows:
            try:
                # Map old column names to new column names
                insert_sql = """
                    INSERT INTO player_availability 
                    (id, player_name, match_date, series_id, availability, submitted_at) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                values = (
                    row['id'],
                    row['player_name'], 
                    row['match_date'],
                    row['series_id'],
                    row['availability_status'],  # OLD column name -> NEW availability
                    row['updated_at']           # OLD column name -> NEW submitted_at
                )
                
                new_cursor.execute(insert_sql, values)
                migrated_count += 1
                
            except Exception as e:
                print(f"  Error migrating row {row['id']}: {str(e)}")
        
        new_conn.commit()
        print(f"✅ Migrated {migrated_count} rows successfully")
        
        # Verify the migration
        print("\n🔍 Verifying migration...")
        old_cursor.execute("SELECT COUNT(*) as count FROM player_availability")
        old_count = old_cursor.fetchone()['count']
        
        new_cursor.execute("SELECT COUNT(*) as count FROM player_availability")
        new_count = new_cursor.fetchone()[0]
        
        if old_count == new_count:
            print(f"✅ Verification successful: {old_count} rows in both databases")
        else:
            print(f"❌ Count mismatch: old={old_count}, new={new_count}")
        
        # Close connections
        old_cursor.close()
        old_conn.close()
        new_cursor.close()
        new_conn.close()
        
        print("\n🎉 Player availability migration completed!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_player_availability() 