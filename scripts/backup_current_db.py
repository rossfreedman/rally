#!/usr/bin/env python3
import psycopg2
import os
from datetime import datetime

def backup_database():
    """Create a backup of the current Railway database"""
    
    # Current database connection
    current_db_url = "postgresql://postgres:OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf@trolley.proxy.rlwy.net:34555/railway"
    
    print("Connecting to current database...")
    conn = psycopg2.connect(current_db_url)
    cursor = conn.cursor()
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = os.path.join("data", "backups", "database", f"current_db_backup_{timestamp}.sql")
    
    print(f"Creating backup: {backup_filename}")
    
    with open(backup_filename, 'w') as backup_file:
        # Write header
        backup_file.write("-- Railway Database Backup\n")
        backup_file.write(f"-- Created: {datetime.now()}\n")
        backup_file.write(f"-- Source: trolley.proxy.rlwy.net:34555/railway\n\n")
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # For each table, create the CREATE TABLE and INSERT statements
        for table in tables:
            print(f"Backing up table: {table}")
            
            # Get table schema
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = '{table}' 
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            # Create basic CREATE TABLE statement
            backup_file.write(f"\n-- Table: {table}\n")
            backup_file.write(f"DROP TABLE IF EXISTS {table} CASCADE;\n")
            create_stmt = f"CREATE TABLE {table} (\n"
            
            col_defs = []
            for col_name, data_type, is_nullable, default in columns:
                col_def = f"    {col_name} {data_type}"
                if is_nullable == 'NO':
                    col_def += " NOT NULL"
                if default:
                    col_def += f" DEFAULT {default}"
                col_defs.append(col_def)
            
            create_stmt += ",\n".join(col_defs)
            create_stmt += "\n);\n\n"
            backup_file.write(create_stmt)
            
            # Get data
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"  Exporting {count} rows from {table}")
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                if rows:
                    # Get column names for INSERT
                    col_names = [col[0] for col in columns]
                    
                    backup_file.write(f"-- Data for {table}\n")
                    for row in rows:
                        # Convert row data to string format for SQL
                        values = []
                        for val in row:
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, str):
                                # Escape single quotes
                                escaped = val.replace("'", "''")
                                values.append(f"'{escaped}'")
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            else:
                                values.append(f"'{str(val)}'")
                        
                        insert_stmt = f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({', '.join(values)});\n"
                        backup_file.write(insert_stmt)
                    
                    backup_file.write("\n")
            else:
                print(f"  Table {table} is empty")
    
    cursor.close()
    conn.close()
    
    print(f"✅ Backup completed: {backup_filename}")
    return backup_filename

if __name__ == "__main__":
    backup_database() 