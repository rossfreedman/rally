import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

def migrate_to_railway():
    # Load environment variables
    load_dotenv()
    
    # Get database URLs
    local_db_url = os.getenv('LOCAL_DATABASE_URL')
    railway_db_url = os.getenv('DATABASE_URL')
    
    if not local_db_url or not railway_db_url:
        raise Exception("Both LOCAL_DATABASE_URL and DATABASE_URL environment variables must be set")
    
    print("Connecting to databases...")
    local_conn = psycopg2.connect(local_db_url)
    railway_conn = psycopg2.connect(railway_db_url)
    
    try:
        # Get data from local database
        with local_conn.cursor(cursor_factory=DictCursor) as local_cursor:
            print("\nFetching clubs from local database...")
            local_cursor.execute("SELECT name FROM clubs ORDER BY name")
            clubs = [row['name'] for row in local_cursor.fetchall()]
            print(f"Found {len(clubs)} clubs")
            
            print("\nFetching series from local database...")
            local_cursor.execute("SELECT name FROM series ORDER BY name")
            series = [row['name'] for row in local_cursor.fetchall()]
            print(f"Found {len(series)} series")
        
        # Insert data into Railway database
        with railway_conn.cursor() as railway_cursor:
            print("\nInserting clubs into Railway database...")
            for club in clubs:
                railway_cursor.execute("""
                    INSERT INTO clubs (name) 
                    VALUES (%s) 
                    ON CONFLICT (name) DO NOTHING
                """, (club,))
            
            print("\nInserting series into Railway database...")
            for series_name in series:
                railway_cursor.execute("""
                    INSERT INTO series (name) 
                    VALUES (%s) 
                    ON CONFLICT (name) DO NOTHING
                """, (series_name,))
            
            railway_conn.commit()
            
            # Verify the data
            railway_cursor.execute("SELECT COUNT(*) FROM clubs")
            clubs_count = railway_cursor.fetchone()[0]
            railway_cursor.execute("SELECT COUNT(*) FROM series")
            series_count = railway_cursor.fetchone()[0]
            
            print(f"\nMigration complete!")
            print(f"Railway database now has {clubs_count} clubs and {series_count} series")
            
    finally:
        local_conn.close()
        railway_conn.close()

if __name__ == '__main__':
    migrate_to_railway() 