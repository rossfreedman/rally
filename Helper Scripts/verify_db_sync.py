import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from tabulate import tabulate

def get_all_tables(cursor):
    """Get all table names from the database"""
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
    """)
    return [row[0] for row in cursor.fetchall()]

def get_primary_key(cursor, table_name):
    """Get the primary key column for a table"""
    cursor.execute("""
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_attribute a ON a.attrelid = i.indrelid
                             AND a.attnum = ANY(i.indkey)
        WHERE  i.indrelid = %s::regclass
        AND    i.indisprimary;
    """, (table_name,))
    result = cursor.fetchone()
    return result[0] if result else 'id'

def get_table_data(cursor, table_name, order_by='id'):
    """Get all data from a table"""
    cursor.execute(f"SELECT * FROM {table_name} ORDER BY {order_by}")
    return cursor.fetchall()

def get_table_columns(cursor, table_name):
    """Get column names for a table"""
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = '{table_name}'
    """)
    return [row[0] for row in cursor.fetchall()]

def compare_databases():
    # Load environment variables
    load_dotenv()
    
    # Get database URLs
    local_db_url = os.getenv('LOCAL_DATABASE_URL')
    railway_db_url = os.getenv('DATABASE_URL')
    
    if not local_db_url or not railway_db_url:
        print("Error: Both LOCAL_DATABASE_URL and DATABASE_URL environment variables must be set")
        return
    
    try:
        # Connect to both databases
        local_conn = psycopg2.connect(local_db_url)
        railway_conn = psycopg2.connect(railway_db_url)
        
        # Get all tables from both databases
        with local_conn.cursor() as local_cursor:
            local_tables = set(get_all_tables(local_cursor))
        
        with railway_conn.cursor() as railway_cursor:
            railway_tables = set(get_all_tables(railway_cursor))
        
        # Compare table presence
        print("\nComparing database structure:")
        print("-" * 50)
        if local_tables != railway_tables:
            print("\nTable differences found:")
            only_local = local_tables - railway_tables
            only_railway = railway_tables - local_tables
            if only_local:
                print(f"Tables only in local: {', '.join(sorted(only_local))}")
            if only_railway:
                print(f"Tables only in Railway: {', '.join(sorted(only_railway))}")
        else:
            print(f"Both databases have the same tables: {', '.join(sorted(local_tables))}")
        
        # Compare data in common tables
        common_tables = local_tables & railway_tables
        for table in sorted(common_tables):
            print(f"\nComparing {table} table:")
            print("-" * 50)
            
            try:
                # Get primary key and columns for the table
                with local_conn.cursor() as cursor:
                    primary_key = get_primary_key(cursor, table)
                    columns = get_table_columns(cursor, table)
                
                # Get data from both databases
                with local_conn.cursor(cursor_factory=DictCursor) as local_cursor:
                    local_data = get_table_data(local_cursor, table, primary_key)
                    local_dict = {str(row[primary_key]): dict(row) for row in local_data}
                
                with railway_conn.cursor(cursor_factory=DictCursor) as railway_cursor:
                    railway_data = get_table_data(railway_cursor, table, primary_key)
                    railway_dict = {str(row[primary_key]): dict(row) for row in railway_data}
                
                # Get all unique IDs
                all_ids = sorted(set(local_dict.keys()) | set(railway_dict.keys()))
                
                # Compare each record
                differences = []
                for record_id in all_ids:
                    local_record = local_dict.get(record_id)
                    railway_record = railway_dict.get(record_id)
                    
                    if local_record is None:
                        differences.append([record_id, "Missing in Local", "Present in Railway"])
                    elif railway_record is None:
                        differences.append([record_id, "Present in Local", "Missing in Railway"])
                    else:
                        # Compare all fields
                        diff_fields = []
                        for col in columns:
                            if local_record[col] != railway_record[col]:
                                diff_fields.append(col)
                        
                        if diff_fields:
                            local_vals = {k: local_record[k] for k in diff_fields}
                            railway_vals = {k: railway_record[k] for k in diff_fields}
                            differences.append([
                                record_id,
                                f"Values: {local_vals}",
                                f"Values: {railway_vals}"
                            ])
                
                # Print summary
                print(f"Total records in local: {len(local_dict)}")
                print(f"Total records in Railway: {len(railway_dict)}")
                
                if differences:
                    print(f"\nFound {len(differences)} differences:")
                    print(tabulate(differences, headers=['ID', 'Local Database', 'Railway Database']))
                else:
                    print("\nAll records match exactly! ✓")
            
            except Exception as e:
                print(f"Error comparing table {table}: {str(e)}")
                # Rollback any failed transaction
                local_conn.rollback()
                railway_conn.rollback()
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        local_conn.close()
        railway_conn.close()

if __name__ == '__main__':
    compare_databases() 