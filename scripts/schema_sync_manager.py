#!/usr/bin/env python3
"""
Schema Synchronization Manager
Ensures SQLAlchemy models and database schema stay in sync
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, MetaData, text
from sqlalchemy.orm import sessionmaker
from database_config import get_db_url
from app.models.database_models import Base
import logging
from typing import Dict, List, Set, Tuple
import subprocess
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SchemaSyncManager:
    """Manages synchronization between SQLAlchemy models and database schema"""
    
    def __init__(self):
        self.engine = create_engine(get_db_url())
        self.inspector = inspect(self.engine)
        self.model_metadata = Base.metadata
        
    def get_database_tables(self) -> Set[str]:
        """Get all table names from the database"""
        return set(self.inspector.get_table_names())
    
    def get_model_tables(self) -> Set[str]:
        """Get all table names from SQLAlchemy models"""
        return set(self.model_metadata.tables.keys())
    
    def get_database_columns(self, table_name: str) -> Dict[str, dict]:
        """Get column information for a table from the database"""
        try:
            columns = self.inspector.get_columns(table_name)
            return {col['name']: col for col in columns}
        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {e}")
            return {}
    
    def get_model_columns(self, table_name: str) -> Dict[str, dict]:
        """Get column information for a table from SQLAlchemy models"""
        if table_name not in self.model_metadata.tables:
            return {}
        
        table = self.model_metadata.tables[table_name]
        columns = {}
        
        for col in table.columns:
            columns[col.name] = {
                'name': col.name,
                'type': str(col.type),
                'nullable': col.nullable,
                'default': str(col.default) if col.default else None,
                'primary_key': col.primary_key
            }
        
        return columns
    
    def compare_tables(self) -> Dict[str, List[str]]:
        """Compare tables between database and models"""
        db_tables = self.get_database_tables()
        model_tables = self.get_model_tables()
        
        return {
            'missing_in_db': list(model_tables - db_tables),
            'missing_in_models': list(db_tables - model_tables),
            'common': list(db_tables & model_tables)
        }
    
    def compare_table_columns(self, table_name: str) -> Dict[str, List[str]]:
        """Compare columns for a specific table"""
        db_columns = self.get_database_columns(table_name)
        model_columns = self.get_model_columns(table_name)
        
        db_col_names = set(db_columns.keys())
        model_col_names = set(model_columns.keys())
        
        differences = {
            'missing_in_db': list(model_col_names - db_col_names),
            'missing_in_models': list(db_col_names - model_col_names),
            'common': list(db_col_names & model_col_names),
            'type_mismatches': []
        }
        
        # Check for type mismatches in common columns
        for col_name in differences['common']:
            db_col = db_columns[col_name]
            model_col = model_columns[col_name]
            
            # Simple type comparison (this could be enhanced)
            db_type = str(db_col['type']).lower()
            model_type = str(model_col['type']).lower()
            
            if db_type != model_type:
                differences['type_mismatches'].append({
                    'column': col_name,
                    'db_type': db_type,
                    'model_type': model_type
                })
        
        return differences
    
    def full_schema_comparison(self) -> Dict:
        """Perform a full comparison between database and models"""
        logger.info("🔍 Performing full schema comparison...")
        
        table_comparison = self.compare_tables()
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_db_tables': len(self.get_database_tables()),
                'total_model_tables': len(self.get_model_tables()),
                'tables_in_sync': len(table_comparison['common']),
                'tables_missing_in_db': len(table_comparison['missing_in_db']),
                'tables_missing_in_models': len(table_comparison['missing_in_models'])
            },
            'table_differences': table_comparison,
            'column_differences': {}
        }
        
        # Check column differences for common tables
        for table_name in table_comparison['common']:
            col_diff = self.compare_table_columns(table_name)
            if any([col_diff['missing_in_db'], col_diff['missing_in_models'], col_diff['type_mismatches']]):
                results['column_differences'][table_name] = col_diff
        
        return results
    
    def generate_migration_from_differences(self, differences: Dict) -> str:
        """Generate an Alembic migration script based on differences"""
        migration_content = []
        
        # Tables missing in database (need to create)
        for table in differences['table_differences']['missing_in_db']:
            migration_content.append(f"    # Create table: {table}")
            migration_content.append(f"    # TODO: Add op.create_table() for {table}")
        
        # Columns missing in database (need to add)
        for table_name, col_diff in differences['column_differences'].items():
            if col_diff['missing_in_db']:
                for col in col_diff['missing_in_db']:
                    migration_content.append(f"    # Add column {col} to table {table_name}")
                    migration_content.append(f"    # TODO: Add op.add_column() for {table_name}.{col}")
        
        # Tables missing in models (need to remove or add models)
        for table in differences['table_differences']['missing_in_models']:
            migration_content.append(f"    # Table {table} exists in DB but not in models")
            migration_content.append(f"    # TODO: Either create model or drop table for {table}")
        
        return "\n".join(migration_content)
    
    def check_alembic_status(self) -> Dict[str, str]:
        """Check current Alembic migration status"""
        try:
            # Check if alembic_version table exists
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"))
                table_exists = result.scalar()
                
                if not table_exists:
                    return {'status': 'not_initialized', 'current_revision': None}
                
                # Get current revision
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current_revision = result.scalar()
                
                return {'status': 'initialized', 'current_revision': current_revision}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def initialize_alembic_baseline(self) -> bool:
        """Initialize Alembic with current database state as baseline"""
        try:
            logger.info("🚀 Initializing Alembic baseline...")
            
            # Create a baseline migration that represents current state
            cmd = ["alembic", "revision", "--autogenerate", "-m", "baseline_existing_schema"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to create baseline migration: {result.stderr}")
                return False
            
            logger.info("✅ Baseline migration created")
            
            # Mark it as applied (since database already exists)
            cmd = ["alembic", "stamp", "head"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to stamp migration: {result.stderr}")
                return False
            
            logger.info("✅ Baseline migration marked as applied")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Alembic baseline: {e}")
            return False
    
    def generate_sync_report(self) -> str:
        """Generate a comprehensive sync status report"""
        differences = self.full_schema_comparison()
        alembic_status = self.check_alembic_status()
        
        report = [
            "",
            "🔍 SCHEMA SYNCHRONIZATION REPORT",
            "=" * 50,
            f"Generated: {differences['timestamp']}",
            "",
            "📊 SUMMARY:",
            f"  Database Tables: {differences['summary']['total_db_tables']}",
            f"  Model Tables: {differences['summary']['total_model_tables']}",
            f"  Tables in Sync: {differences['summary']['tables_in_sync']}",
            f"  Missing in DB: {differences['summary']['tables_missing_in_db']}",
            f"  Missing in Models: {differences['summary']['tables_missing_in_models']}",
            "",
            f"🗂️  ALEMBIC STATUS: {alembic_status['status'].upper()}",
        ]
        
        if alembic_status['current_revision']:
            report.append(f"  Current Revision: {alembic_status['current_revision']}")
        
        # Table differences
        if differences['table_differences']['missing_in_db']:
            report.extend([
                "",
                "❌ TABLES MISSING IN DATABASE:",
                *[f"  - {table}" for table in differences['table_differences']['missing_in_db']]
            ])
        
        if differences['table_differences']['missing_in_models']:
            report.extend([
                "",
                "⚠️  TABLES MISSING IN MODELS:",
                *[f"  - {table}" for table in differences['table_differences']['missing_in_models']]
            ])
        
        # Column differences
        if differences['column_differences']:
            report.append("")
            report.append("🔧 COLUMN DIFFERENCES:")
            
            for table_name, col_diff in differences['column_differences'].items():
                report.append(f"  📋 Table: {table_name}")
                
                if col_diff['missing_in_db']:
                    report.append(f"    ❌ Missing in DB: {', '.join(col_diff['missing_in_db'])}")
                
                if col_diff['missing_in_models']:
                    report.append(f"    ⚠️  Missing in Models: {', '.join(col_diff['missing_in_models'])}")
                
                if col_diff['type_mismatches']:
                    report.append("    🔄 Type Mismatches:")
                    for mismatch in col_diff['type_mismatches']:
                        report.append(f"      - {mismatch['column']}: DB({mismatch['db_type']}) vs Model({mismatch['model_type']})")
        
        # Recommendations
        report.extend([
            "",
            "💡 RECOMMENDATIONS:",
        ])
        
        if alembic_status['status'] == 'not_initialized':
            report.append("  1. Run: python scripts/schema_sync_manager.py --init-baseline")
        
        if differences['column_differences'] or differences['table_differences']['missing_in_db']:
            report.append("  2. Run: alembic revision --autogenerate -m 'sync_schema_changes'")
            report.append("  3. Review the generated migration carefully")
            report.append("  4. Run: alembic upgrade head")
        
        if differences['table_differences']['missing_in_models']:
            report.append("  5. Create SQLAlchemy models for missing tables or drop unused tables")
        
        return "\n".join(report)

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Schema Synchronization Manager')
    parser.add_argument('--init-baseline', action='store_true', help='Initialize Alembic with current database as baseline')
    parser.add_argument('--check', action='store_true', help='Check schema synchronization status')
    parser.add_argument('--report', action='store_true', help='Generate detailed sync report')
    
    args = parser.parse_args()
    
    manager = SchemaSyncManager()
    
    if args.init_baseline:
        success = manager.initialize_alembic_baseline()
        if success:
            logger.info("🎉 Alembic baseline initialization completed!")
        else:
            logger.error("❌ Alembic baseline initialization failed!")
            sys.exit(1)
    
    elif args.check:
        differences = manager.full_schema_comparison()
        
        if (differences['summary']['tables_missing_in_db'] == 0 and 
            differences['summary']['tables_missing_in_models'] == 0 and
            not differences['column_differences']):
            logger.info("✅ Schema is in sync!")
        else:
            logger.warning("⚠️  Schema differences detected. Use --report for details.")
    
    elif args.report:
        report = manager.generate_sync_report()
        print(report)
    
    else:
        # Default: show status
        report = manager.generate_sync_report()
        print(report)

if __name__ == "__main__":
    main() 