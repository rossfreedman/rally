#!/usr/bin/env python3
"""
Schema Comparison Script for DbSchema
Compares database schemas between local and Railway environments to ensure synchronization.
"""

import os
import sys
import psycopg2
import json
from datetime import datetime
from dotenv import load_dotenv

# Add root directory to path for imports (go up two levels from data/dbschema)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_config import parse_db_url

load_dotenv()

def get_schema_info(connection_params, environment_name):
    """Extract comprehensive schema information for DbSchema comparison"""
    try:
        conn = psycopg2.connect(**connection_params)
        schema_info = {
            "environment": environment_name,
            "timestamp": datetime.now().isoformat(),
            "tables": {},
            "indexes": {},
            "constraints": {},
            "sequences": {},
            "functions": {}
        }
        
        with conn.cursor() as cursor:
            print(f"   📋 Extracting schema from {environment_name}...")
            
            # Get table and column information
            cursor.execute("""
                SELECT 
                    t.table_name,
                    t.table_type,
                    c.column_name,
                    c.data_type,
                    c.character_maximum_length,
                    c.is_nullable,
                    c.column_default,
                    c.ordinal_position
                FROM information_schema.tables t
                LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
                WHERE t.table_schema = 'public'
                AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name, c.ordinal_position
            """)
            
            for row in cursor.fetchall():
                table_name, table_type, col_name, data_type, max_length, nullable, default, position = row
                
                if table_name not in schema_info["tables"]:
                    schema_info["tables"][table_name] = {
                        "type": table_type,
                        "columns": {},
                        "row_count": None
                    }
                
                if col_name:  # Skip if no columns
                    schema_info["tables"][table_name]["columns"][col_name] = {
                        "data_type": data_type,
                        "max_length": max_length,
                        "nullable": nullable,
                        "default": default,
                        "position": position
                    }
            
            print(f"   📊 Found {len(schema_info['tables'])} tables")
            
            # Get foreign key constraints
            cursor.execute("""
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                ORDER BY tc.table_name, kcu.column_name
            """)
            
            for row in cursor.fetchall():
                table, column, ref_table, ref_column, constraint_name = row
                constraint_key = f"{table}.{column} -> {ref_table}.{ref_column}"
                schema_info["constraints"][constraint_key] = {
                    "type": "FOREIGN KEY",
                    "constraint_name": constraint_name,
                    "table": table,
                    "column": column,
                    "referenced_table": ref_table,
                    "referenced_column": ref_column
                }
            
            print(f"   🔗 Found {len(schema_info['constraints'])} foreign key constraints")
            
            # Get indexes
            cursor.execute("""
                SELECT 
                    i.relname as index_name,
                    t.relname as table_name,
                    ix.indisunique,
                    ix.indisprimary,
                    a.attname as column_name
                FROM pg_class i
                JOIN pg_index ix ON i.oid = ix.indexrelid
                JOIN pg_class t ON ix.indrelid = t.oid
                JOIN pg_attribute a ON t.oid = a.attrelid
                WHERE t.relkind = 'r'
                AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND a.attnum = ANY(ix.indkey)
                ORDER BY t.relname, i.relname
            """)
            
            for row in cursor.fetchall():
                index_name, table_name, is_unique, is_primary, column_name = row
                index_key = f"{table_name}.{index_name}"
                
                if index_key not in schema_info["indexes"]:
                    schema_info["indexes"][index_key] = {
                        "table": table_name,
                        "name": index_name,
                        "unique": is_unique,
                        "primary": is_primary,
                        "columns": []
                    }
                
                schema_info["indexes"][index_key]["columns"].append(column_name)
            
            print(f"   📇 Found {len(schema_info['indexes'])} indexes")
            
            # Get sequences
            cursor.execute("""
                SELECT sequence_name, data_type, start_value, increment
                FROM information_schema.sequences
                WHERE sequence_schema = 'public'
                ORDER BY sequence_name
            """)
            
            for row in cursor.fetchall():
                seq_name, data_type, start_value, increment = row
                schema_info["sequences"][seq_name] = {
                    "data_type": data_type,
                    "start_value": start_value,
                    "increment": increment
                }
            
            print(f"   🔢 Found {len(schema_info['sequences'])} sequences")
            
            # Get rough row counts for data comparison (sample only)
            key_tables = ['users', 'leagues', 'clubs', 'series', 'teams', 'players']
            for table in key_tables:
                if table in schema_info["tables"]:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        schema_info["tables"][table]["row_count"] = count
                    except Exception:
                        schema_info["tables"][table]["row_count"] = "error"
        
        conn.close()
        print(f"   ✅ Schema extraction complete for {environment_name}")
        return schema_info
        
    except Exception as e:
        print(f"   ❌ Error getting schema for {environment_name}: {str(e)}")
        return None

def compare_table_structures(local_tables, railway_tables):
    """Compare table structures between environments"""
    differences = {
        "missing_in_railway": [],
        "missing_in_local": [],
        "column_differences": {},
        "row_count_differences": {}
    }
    
    local_table_names = set(local_tables.keys())
    railway_table_names = set(railway_tables.keys())
    
    # Find missing tables
    differences["missing_in_railway"] = list(local_table_names - railway_table_names)
    differences["missing_in_local"] = list(railway_table_names - local_table_names)
    
    # Compare common tables
    common_tables = local_table_names & railway_table_names
    
    for table_name in common_tables:
        local_table = local_tables[table_name]
        railway_table = railway_tables[table_name]
        
        # Compare columns
        local_columns = set(local_table["columns"].keys())
        railway_columns = set(railway_table["columns"].keys())
        
        missing_columns_railway = local_columns - railway_columns
        missing_columns_local = railway_columns - local_columns
        
        if missing_columns_railway or missing_columns_local:
            differences["column_differences"][table_name] = {
                "missing_in_railway": list(missing_columns_railway),
                "missing_in_local": list(missing_columns_local)
            }
        
        # Compare row counts (if available)
        local_count = local_table.get("row_count")
        railway_count = railway_table.get("row_count")
        
        if local_count is not None and railway_count is not None:
            if isinstance(local_count, int) and isinstance(railway_count, int):
                if abs(local_count - railway_count) > 0:  # Any difference is notable
                    differences["row_count_differences"][table_name] = {
                        "local": local_count,
                        "railway": railway_count,
                        "difference": railway_count - local_count
                    }
    
    return differences

def print_comparison_report(local_schema, railway_schema, differences):
    """Print a detailed comparison report"""
    print("\n📊 SCHEMA COMPARISON REPORT")
    print("=" * 50)
    
    # Table summary
    local_tables = len(local_schema["tables"])
    railway_tables = len(railway_schema["tables"])
    
    print(f"\n📋 TABLE SUMMARY:")
    print(f"   Local tables: {local_tables}")
    print(f"   Railway tables: {railway_tables}")
    
    if differences["missing_in_railway"]:
        print(f"\n⚠️  TABLES MISSING IN RAILWAY ({len(differences['missing_in_railway'])}):")
        for table in differences["missing_in_railway"]:
            print(f"   - {table}")
    
    if differences["missing_in_local"]:
        print(f"\n⚠️  TABLES MISSING IN LOCAL ({len(differences['missing_in_local'])}):")
        for table in differences["missing_in_local"]:
            print(f"   - {table}")
    
    # Column differences
    if differences["column_differences"]:
        print(f"\n🔧 COLUMN DIFFERENCES ({len(differences['column_differences'])} tables):")
        for table, diff in differences["column_differences"].items():
            print(f"\n   Table: {table}")
            if diff["missing_in_railway"]:
                print(f"      Missing in Railway: {diff['missing_in_railway']}")
            if diff["missing_in_local"]:
                print(f"      Missing in Local: {diff['missing_in_local']}")
    
    # Row count differences
    if differences["row_count_differences"]:
        print(f"\n📊 ROW COUNT DIFFERENCES ({len(differences['row_count_differences'])} tables):")
        for table, diff in differences["row_count_differences"].items():
            print(f"   {table}: Local={diff['local']}, Railway={diff['railway']} (Δ{diff['difference']:+d})")
    
    # Constraint summary
    local_constraints = len(local_schema["constraints"])
    railway_constraints = len(railway_schema["constraints"])
    
    print(f"\n🔗 CONSTRAINT SUMMARY:")
    print(f"   Local constraints: {local_constraints}")
    print(f"   Railway constraints: {railway_constraints}")
    
    # Index summary
    local_indexes = len(local_schema["indexes"])
    railway_indexes = len(railway_schema["indexes"])
    
    print(f"\n📇 INDEX SUMMARY:")
    print(f"   Local indexes: {local_indexes}")
    print(f"   Railway indexes: {railway_indexes}")
    
    # Overall assessment
    print(f"\n🎯 SYNC ASSESSMENT:")
    if not differences["missing_in_railway"] and not differences["missing_in_local"] and not differences["column_differences"]:
        print("   ✅ Schemas are synchronized")
        print("   💚 Ready for DbSchema visual comparison")
    else:
        print("   ⚠️  Schemas have differences")
        print("   💛 Review differences before DbSchema setup")
        if differences["missing_in_railway"] or differences["missing_in_local"]:
            print("   🔧 Consider running Alembic migrations")

def main():
    """Main comparison function"""
    print("🔍 DbSchema Schema Comparison Tool")
    print("=" * 50)
    print("Comparing database schemas between environments...\n")
    
    # Get local schema
    print("1️⃣ ANALYZING LOCAL DATABASE")
    try:
        local_params = {
            "host": "localhost",
            "port": 5432,
            "dbname": "rally",
            "user": "rossfreedman"
        }
        local_schema = get_schema_info(local_params, "local")
    except Exception as e:
        print(f"   ❌ Failed to connect to local database: {e}")
        print("   💡 Make sure PostgreSQL is running locally")
        return
    
    if not local_schema:
        print("   ❌ Could not extract local schema")
        return
    
    print("\n2️⃣ ANALYZING RAILWAY DATABASE")
    railway_url = os.getenv("DATABASE_PUBLIC_URL")
    if not railway_url:
        print("   ⚠️  DATABASE_PUBLIC_URL not configured")
        print("   💡 Set this environment variable to compare with Railway")
        return
    
    try:
        railway_params = parse_db_url(railway_url)
        railway_schema = get_schema_info(railway_params, "railway")
    except Exception as e:
        print(f"   ❌ Failed to connect to Railway database: {e}")
        print("   💡 Check Railway database URL and connectivity")
        return
    
    if not railway_schema:
        print("   ❌ Could not extract Railway schema")
        return
    
    # Compare schemas
    print("\n3️⃣ COMPARING SCHEMAS")
    differences = compare_table_structures(
        local_schema["tables"], 
        railway_schema["tables"]
    )
    
    # Print report
    print_comparison_report(local_schema, railway_schema, differences)
    
    # Save detailed comparison
    comparison_file = f"schema_comparison_dbschema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    comparison_data = {
        "local": local_schema,
        "railway": railway_schema,
        "differences": differences,
        "comparison_timestamp": datetime.now().isoformat()
    }
    
    try:
        with open(comparison_file, 'w') as f:
            json.dump(comparison_data, f, indent=2, default=str)
        print(f"\n📄 Detailed comparison saved: {comparison_file}")
    except Exception as e:
        print(f"\n❌ Failed to save comparison file: {e}")
    
    # DbSchema recommendations
    print(f"\n🎯 DBSCHEMA RECOMMENDATIONS:")
    if not differences["missing_in_railway"] and not differences["missing_in_local"]:
        print("   ✅ Proceed with DbSchema setup")
        print("   📋 Both environments have same table structure")
        print("   💡 Use DbSchema visual comparison to verify relationships")
    else:
        print("   ⚠️  Fix schema differences first")
        print("   🔧 Run pending Alembic migrations")
        print("   📋 Ensure both environments are up to date")
    
    print(f"\n🔗 Next Steps:")
    print("   1. Review differences above")
    print("   2. Fix any schema synchronization issues")
    print("   3. Run: python scripts/validate_dbschema_connections.py")
    print("   4. Set up DbSchema connections")
    print("   5. Import schemas and compare visually")

if __name__ == "__main__":
    main() 