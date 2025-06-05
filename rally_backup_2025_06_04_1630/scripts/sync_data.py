#!/usr/bin/env python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import urlparse, urlunparse

def get_railway_url(url):
    """Convert Railway internal URL to public URL"""
    if not url:
        return None
    
    parsed = urlparse(url)
    if parsed.hostname == "postgres.railway.internal":
        # Replace internal hostname with public hostname
        parts = list(parsed)
        parts[1] = parts[1].replace("postgres.railway.internal", "postgres-production-0931.up.railway.app")
        return urlunparse(parts)
    return url

def get_connection(url):
    """Create a database connection"""
    return psycopg2.connect(url, cursor_factory=RealDictCursor)

def get_table_data(conn, table_name):
    """Get all data from a table"""
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {table_name}")
        return cur.fetchall()

def sync_table(source_conn, dest_conn, table_name, primary_key='id'):
    """Sync data between source and destination tables"""
    print(f"\n🔄 Syncing table: {table_name}")
    
    # Get data from both databases
    with source_conn.cursor() as source_cur, dest_conn.cursor() as dest_cur:
        # Get source data
        source_cur.execute(f"SELECT * FROM {table_name}")
        source_data = {str(row[primary_key]): row for row in source_cur.fetchall()}
        
        # Get destination data
        dest_cur.execute(f"SELECT * FROM {table_name}")
        dest_data = {str(row[primary_key]): row for row in dest_cur.fetchall()}
        
        # Find records to insert, update, and delete
        source_ids = set(source_data.keys())
        dest_ids = set(dest_data.keys())
        
        to_insert = source_ids - dest_ids
        to_update = source_ids & dest_ids
        to_delete = dest_ids - source_ids
        
        # Handle inserts
        for id_ in to_insert:
            row = source_data[id_]
            columns = row.keys()
            values = [row[col] for col in columns]
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({', '.join(['%s'] * len(columns))})
            """
            dest_cur.execute(query, values)
            print(f"➕ Inserted record {id_}")
        
        # Handle updates
        for id_ in to_update:
            source_row = source_data[id_]
            dest_row = dest_data[id_]
            
            if source_row != dest_row:
                columns = [k for k in source_row.keys() if k != primary_key]
                values = [source_row[col] for col in columns]
                values.append(id_)
                
                query = f"""
                    UPDATE {table_name}
                    SET {', '.join(f'{col} = %s' for col in columns)}
                    WHERE {primary_key} = %s
                """
                dest_cur.execute(query, values)
                print(f"📝 Updated record {id_}")
        
        # Handle deletes (optional, comment out if you don't want to delete)
        for id_ in to_delete:
            query = f"DELETE FROM {table_name} WHERE {primary_key} = %s"
            dest_cur.execute(query, [id_])
            print(f"❌ Deleted record {id_}")
        
        dest_conn.commit()
        print(f"✅ Synced {table_name}: {len(to_insert)} inserts, {len(to_update)} updates, {len(to_delete)} deletes")

def main():
    """Main sync function"""
    load_dotenv()
    
    # Get database URLs
    source_url = os.getenv('DATABASE_URL')
    dest_url = get_railway_url(os.getenv('RAILWAY_POSTGRES_URL'))
    
    if not all([source_url, dest_url]):
        print("❌ Error: Both DATABASE_URL and RAILWAY_POSTGRES_URL must be set")
        return
    
    try:
        # Connect to both databases
        print("🔌 Connecting to databases...")
        print(f"Source DB: {source_url}")
        print(f"Destination DB: {dest_url}")
        
        source_conn = get_connection(source_url)
        dest_conn = get_connection(dest_url)
        
        # Create backup of destination database first
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"backup_railway_{timestamp}.sql"
        os.system(f"pg_dump {dest_url} > {backup_file}")
        print(f"📦 Created backup: {backup_file}")
        
        # Tables to sync in order (respecting foreign key constraints)
        tables = [
            'series',
            'clubs',
            'users',
            'player_availability',
            'user_activity_logs',
            'user_instructions'
        ]
        
        # Sync each table
        for table in tables:
            sync_table(source_conn, dest_conn, table)
        
        print("\n✅ Database sync completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during sync: {str(e)}")
        print("Please check your database URLs and ensure they are correct.")
        print("Railway URL should use 'postgres-production-0931.up.railway.app' as the hostname.")
        
    finally:
        # Close connections
        if 'source_conn' in locals():
            source_conn.close()
        if 'dest_conn' in locals():
            dest_conn.close()

if __name__ == "__main__":
    main() 