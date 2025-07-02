#!/usr/bin/env python3
"""
Comprehensive Schema Comparison Script

Uses Alembic to comprehensively compare local and staging database schemas
to ensure they match 100% perfectly.
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from contextlib import contextmanager

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one
from database_config import get_db


class DatabaseEnvironment:
    def __init__(self, name, env_vars=None):
        self.name = name
        self.env_vars = env_vars or {}

    @contextmanager
    def activate(self):
        """Context manager to temporarily set environment variables"""
        old_env = {}
        for key, value in self.env_vars.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            yield
        finally:
            # Restore old environment
            for key, old_value in old_env.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value


def run_alembic_command(command, env_context=None):
    """Run an Alembic command with optional environment context"""
    if env_context:
        with env_context.activate():
            result = subprocess.run(
                ["alembic"] + command.split(),
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
    else:
        result = subprocess.run(
            ["alembic"] + command.split(),
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def get_current_revision(env_context):
    """Get the current database revision using Alembic"""
    result = run_alembic_command("current", env_context)
    
    if result["returncode"] != 0:
        print(f"❌ Error getting current revision for {env_context.name}:")
        print(f"STDERR: {result['stderr']}")
        return None
    
    stdout = result["stdout"].strip()
    if not stdout or "No current revision" in stdout:
        return "No revision"
    
    # Extract revision hash from output like "INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl."
    # followed by "INFO  [alembic.runtime.migration] Current revision for postgresql://...: 9e89c138eadd"
    lines = stdout.split('\n')
    for line in lines:
        if "Current revision" in line and ":" in line:
            return line.split(":")[-1].strip()
    
    return stdout


def get_migration_history(env_context):
    """Get the full migration history using Alembic"""
    result = run_alembic_command("history --verbose", env_context)
    
    if result["returncode"] != 0:
        print(f"❌ Error getting migration history for {env_context.name}:")
        print(f"STDERR: {result['stderr']}")
        return []
    
    return result["stdout"]


def check_pending_migrations(env_context):
    """Check if there are any pending migrations"""
    result = run_alembic_command("check", env_context)
    
    return {
        "has_pending": result["returncode"] != 0,
        "output": result["stdout"] + result["stderr"]
    }


def get_database_schema_info(env_context):
    """Get detailed schema information from the database directly"""
    
    with env_context.activate():
        try:
            # Get all tables
            tables_query = """
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """
            tables = execute_query(tables_query)
            
            # Get all columns with details
            columns_query = """
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """
            columns = execute_query(columns_query)
            
            # Get all constraints
            constraints_query = """
                SELECT 
                    tc.table_name,
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.update_rule,
                    rc.delete_rule
                FROM information_schema.table_constraints tc
                LEFT JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                LEFT JOIN information_schema.constraint_column_usage ccu 
                    ON ccu.constraint_name = tc.constraint_name
                LEFT JOIN information_schema.referential_constraints rc 
                    ON tc.constraint_name = rc.constraint_name
                WHERE tc.table_schema = 'public'
                ORDER BY tc.table_name, tc.constraint_name;
            """
            constraints = execute_query(constraints_query)
            
            # Get all indexes
            indexes_query = """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname;
            """
            indexes = execute_query(indexes_query)
            
            # Get sequences
            sequences_query = """
                SELECT sequence_name, data_type, start_value, minimum_value, maximum_value, increment
                FROM information_schema.sequences
                WHERE sequence_schema = 'public'
                ORDER BY sequence_name;
            """
            sequences = execute_query(sequences_query)
            
            return {
                "tables": tables,
                "columns": columns,
                "constraints": constraints,
                "indexes": indexes,
                "sequences": sequences
            }
            
        except Exception as e:
            print(f"❌ Error getting schema info for {env_context.name}: {e}")
            return None


def compare_schema_objects(local_schema, staging_schema):
    """Compare schema objects between local and staging"""
    differences = {
        "tables": {"missing_in_staging": [], "missing_in_local": [], "different": []},
        "columns": {"missing_in_staging": [], "missing_in_local": [], "different": []},
        "constraints": {"missing_in_staging": [], "missing_in_local": [], "different": []},
        "indexes": {"missing_in_staging": [], "missing_in_local": [], "different": []},
        "sequences": {"missing_in_staging": [], "missing_in_local": [], "different": []}
    }
    
    # Compare tables
    local_tables = {t["table_name"]: t for t in local_schema["tables"]}
    staging_tables = {t["table_name"]: t for t in staging_schema["tables"]}
    
    for table_name in local_tables:
        if table_name not in staging_tables:
            differences["tables"]["missing_in_staging"].append(table_name)
    
    for table_name in staging_tables:
        if table_name not in local_tables:
            differences["tables"]["missing_in_local"].append(table_name)
    
    # Compare columns
    local_columns = {f"{c['table_name']}.{c['column_name']}": c for c in local_schema["columns"]}
    staging_columns = {f"{c['table_name']}.{c['column_name']}": c for c in staging_schema["columns"]}
    
    for col_key in local_columns:
        if col_key not in staging_columns:
            differences["columns"]["missing_in_staging"].append(col_key)
        else:
            # Compare column details
            local_col = local_columns[col_key]
            staging_col = staging_columns[col_key]
            
            for key in ["data_type", "is_nullable", "column_default", "character_maximum_length"]:
                if local_col.get(key) != staging_col.get(key):
                    differences["columns"]["different"].append({
                        "column": col_key,
                        "property": key,
                        "local": local_col.get(key),
                        "staging": staging_col.get(key)
                    })
    
    for col_key in staging_columns:
        if col_key not in local_columns:
            differences["columns"]["missing_in_local"].append(col_key)
    
    # Compare constraints
    local_constraints = {f"{c['table_name']}.{c['constraint_name']}": c for c in local_schema["constraints"]}
    staging_constraints = {f"{c['table_name']}.{c['constraint_name']}": c for c in staging_schema["constraints"]}
    
    for const_key in local_constraints:
        if const_key not in staging_constraints:
            differences["constraints"]["missing_in_staging"].append(const_key)
    
    for const_key in staging_constraints:
        if const_key not in local_constraints:
            differences["constraints"]["missing_in_local"].append(const_key)
    
    # Compare indexes
    local_indexes = {f"{i['tablename']}.{i['indexname']}": i for i in local_schema["indexes"]}
    staging_indexes = {f"{i['tablename']}.{i['indexname']}": i for i in staging_schema["indexes"]}
    
    for idx_key in local_indexes:
        if idx_key not in staging_indexes:
            differences["indexes"]["missing_in_staging"].append(idx_key)
        else:
            # Compare index definitions
            if local_indexes[idx_key]["indexdef"] != staging_indexes[idx_key]["indexdef"]:
                differences["indexes"]["different"].append({
                    "index": idx_key,
                    "local": local_indexes[idx_key]["indexdef"],
                    "staging": staging_indexes[idx_key]["indexdef"]
                })
    
    for idx_key in staging_indexes:
        if idx_key not in local_indexes:
            differences["indexes"]["missing_in_local"].append(idx_key)
    
    # Compare sequences
    local_sequences = {s["sequence_name"]: s for s in local_schema["sequences"]}
    staging_sequences = {s["sequence_name"]: s for s in staging_schema["sequences"]}
    
    for seq_name in local_sequences:
        if seq_name not in staging_sequences:
            differences["sequences"]["missing_in_staging"].append(seq_name)
    
    for seq_name in staging_sequences:
        if seq_name not in local_sequences:
            differences["sequences"]["missing_in_local"].append(seq_name)
    
    return differences


def generate_autogenerated_migration(env_context):
    """Generate an autogenerated migration to detect schema differences"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    migration_name = f"schema_check_{timestamp}"
    
    result = run_alembic_command(f"revision --autogenerate -m '{migration_name}'", env_context)
    
    if result["returncode"] != 0:
        print(f"❌ Error generating autogeneration for {env_context.name}:")
        print(f"STDERR: {result['stderr']}")
        return None
    
    # Find the generated migration file
    migration_files = [f for f in os.listdir("alembic/versions") if migration_name in f]
    if migration_files:
        migration_file = f"alembic/versions/{migration_files[0]}"
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Clean up - remove the test migration file
        os.remove(migration_file)
        
        return {
            "migration_content": content,
            "has_changes": "def upgrade():" in content and "pass" not in content.split("def upgrade():")[1].split("def downgrade():")[0]
        }
    
    return None


def main():
    """Main function to run comprehensive schema comparison"""
    print("🔍 Starting Comprehensive Schema Comparison")
    print("=" * 60)
    
    # Define environments
    local_env = DatabaseEnvironment("LOCAL", {})
    staging_env = DatabaseEnvironment("STAGING", {"SYNC_RAILWAY_STAGING": "true"})
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "environments": {},
        "comparison": {},
        "summary": {}
    }
    
    environments = [
        ("local", local_env),
        ("staging", staging_env)
    ]
    
    # 1. Check current revisions
    print("\n📋 Step 1: Checking Current Migration Revisions")
    print("-" * 50)
    
    for env_name, env_context in environments:
        print(f"\n🔍 Checking {env_name.upper()} database...")
        
        current_rev = get_current_revision(env_context)
        pending = check_pending_migrations(env_context)
        
        results["environments"][env_name] = {
            "current_revision": current_rev,
            "has_pending_migrations": pending["has_pending"],
            "pending_output": pending["output"]
        }
        
        print(f"   Current revision: {current_rev}")
        print(f"   Has pending migrations: {pending['has_pending']}")
        if pending["has_pending"]:
            print(f"   Pending details: {pending['output']}")
    
    # 2. Compare revisions
    local_rev = results["environments"]["local"]["current_revision"]
    staging_rev = results["environments"]["staging"]["current_revision"]
    
    print(f"\n📊 Revision Comparison:")
    print(f"   Local:   {local_rev}")
    print(f"   Staging: {staging_rev}")
    print(f"   Match:   {'✅ YES' if local_rev == staging_rev else '❌ NO'}")
    
    results["comparison"]["revisions_match"] = local_rev == staging_rev
    
    # 3. Get detailed schema information
    print("\n📋 Step 2: Extracting Detailed Schema Information")
    print("-" * 50)
    
    schema_info = {}
    for env_name, env_context in environments:
        print(f"\n🔍 Extracting {env_name.upper()} schema...")
        schema_info[env_name] = get_database_schema_info(env_context)
        
        if schema_info[env_name]:
            tables_count = len(schema_info[env_name]["tables"])
            columns_count = len(schema_info[env_name]["columns"])
            constraints_count = len(schema_info[env_name]["constraints"])
            indexes_count = len(schema_info[env_name]["indexes"])
            
            print(f"   Tables: {tables_count}")
            print(f"   Columns: {columns_count}")
            print(f"   Constraints: {constraints_count}")
            print(f"   Indexes: {indexes_count}")
            
            results["environments"][env_name].update({
                "tables_count": tables_count,
                "columns_count": columns_count,
                "constraints_count": constraints_count,
                "indexes_count": indexes_count
            })
    
    # 4. Compare schemas
    print("\n📋 Step 3: Comparing Schema Objects")
    print("-" * 50)
    
    if schema_info["local"] and schema_info["staging"]:
        differences = compare_schema_objects(schema_info["local"], schema_info["staging"])
        results["comparison"]["schema_differences"] = differences
        
        # Calculate total differences
        total_diffs = sum([
            len(differences["tables"]["missing_in_staging"]),
            len(differences["tables"]["missing_in_local"]),
            len(differences["columns"]["missing_in_staging"]),
            len(differences["columns"]["missing_in_local"]),
            len(differences["columns"]["different"]),
            len(differences["constraints"]["missing_in_staging"]),
            len(differences["constraints"]["missing_in_local"]),
            len(differences["indexes"]["missing_in_staging"]),
            len(differences["indexes"]["missing_in_local"]),
            len(differences["indexes"]["different"]),
            len(differences["sequences"]["missing_in_staging"]),
            len(differences["sequences"]["missing_in_local"])
        ])
        
        print(f"\n📊 Schema Differences Summary:")
        print(f"   Total differences found: {total_diffs}")
        
        if total_diffs == 0:
            print("   ✅ SCHEMAS MATCH PERFECTLY!")
        else:
            print("   ❌ Schemas have differences:")
            
            # Tables
            if differences["tables"]["missing_in_staging"]:
                print(f"      • Tables missing in staging: {differences['tables']['missing_in_staging']}")
            if differences["tables"]["missing_in_local"]:
                print(f"      • Tables missing in local: {differences['tables']['missing_in_local']}")
            
            # Columns
            if differences["columns"]["missing_in_staging"]:
                print(f"      • Columns missing in staging: {len(differences['columns']['missing_in_staging'])} columns")
            if differences["columns"]["missing_in_local"]:
                print(f"      • Columns missing in local: {len(differences['columns']['missing_in_local'])} columns")
            if differences["columns"]["different"]:
                print(f"      • Column definition differences: {len(differences['columns']['different'])} columns")
            
            # Constraints
            if differences["constraints"]["missing_in_staging"]:
                print(f"      • Constraints missing in staging: {len(differences['constraints']['missing_in_staging'])} constraints")
            if differences["constraints"]["missing_in_local"]:
                print(f"      • Constraints missing in local: {len(differences['constraints']['missing_in_local'])} constraints")
            
            # Indexes
            if differences["indexes"]["missing_in_staging"]:
                print(f"      • Indexes missing in staging: {len(differences['indexes']['missing_in_staging'])} indexes")
            if differences["indexes"]["missing_in_local"]:
                print(f"      • Indexes missing in local: {len(differences['indexes']['missing_in_local'])} indexes")
            if differences["indexes"]["different"]:
                print(f"      • Index definition differences: {len(differences['indexes']['different'])} indexes")
        
        results["comparison"]["schemas_match"] = total_diffs == 0
        results["comparison"]["total_differences"] = total_diffs
    
    # 5. Generate autogenerated migrations for each environment
    print("\n📋 Step 4: Testing Autogenerated Migrations")
    print("-" * 50)
    
    for env_name, env_context in environments:
        print(f"\n🔍 Testing autogeneration for {env_name.upper()}...")
        auto_migration = generate_autogenerated_migration(env_context)
        
        if auto_migration:
            has_changes = auto_migration["has_changes"]
            print(f"   Autogenerated migration has changes: {'❌ YES' if has_changes else '✅ NO'}")
            
            results["environments"][env_name]["autogeneration_has_changes"] = has_changes
            if has_changes:
                # Store a snippet of the migration content
                content = auto_migration["migration_content"]
                upgrade_section = content.split("def upgrade():")[1].split("def downgrade():")[0] if "def upgrade():" in content else "No upgrade section"
                results["environments"][env_name]["autogeneration_preview"] = upgrade_section[:500] + "..." if len(upgrade_section) > 500 else upgrade_section
        else:
            print(f"   ❌ Could not generate autogenerated migration")
            results["environments"][env_name]["autogeneration_has_changes"] = None
    
    # 6. Final Summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE SCHEMA COMPARISON SUMMARY")
    print("=" * 60)
    
    revisions_match = results["comparison"].get("revisions_match", False)
    schemas_match = results["comparison"].get("schemas_match", False)
    
    local_auto_clean = not results["environments"]["local"].get("autogeneration_has_changes", True)
    staging_auto_clean = not results["environments"]["staging"].get("autogeneration_has_changes", True)
    
    all_perfect = revisions_match and schemas_match and local_auto_clean and staging_auto_clean
    
    print(f"✅ Migration revisions match: {'YES' if revisions_match else 'NO'}")
    print(f"✅ Schema objects match: {'YES' if schemas_match else 'NO'}")
    print(f"✅ Local autogeneration clean: {'YES' if local_auto_clean else 'NO'}")
    print(f"✅ Staging autogeneration clean: {'YES' if staging_auto_clean else 'NO'}")
    print()
    print(f"🎯 OVERALL RESULT: {'✅ SCHEMAS MATCH 100% PERFECTLY!' if all_perfect else '❌ SCHEMAS HAVE DIFFERENCES'}")
    
    results["summary"] = {
        "revisions_match": revisions_match,
        "schemas_match": schemas_match,
        "autogeneration_clean": local_auto_clean and staging_auto_clean,
        "overall_perfect_match": all_perfect
    }
    
    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"schema_comparison_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📁 Detailed results saved to: {results_file}")
    
    return all_perfect


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 