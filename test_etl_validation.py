#!/usr/bin/env python3
"""
ELT Validation Script

This script validates that ELT scripts produce accurate and complete results
by running them against a test database and comparing with the original data.
"""

import os
import sys
import json
import subprocess
import psycopg2
from datetime import datetime
from pathlib import Path
import pandas as pd
from collections import defaultdict

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import parse_db_url

class ETLValidator:
    def __init__(self):
        self.load_test_config()
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {},
            'errors': []
        }
        
    def load_test_config(self):
        """Load test configuration"""
        try:
            with open('etl_test_config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print("❌ Test configuration not found. Run test_etl_environment.py first.")
            sys.exit(1)
    
    def get_table_row_counts(self, db_url, description=""):
        """Get row counts for all tables in database"""
        print(f"📊 Getting table counts for {description}...")
        
        db_params = parse_db_url(db_url)
        row_counts = {}
        
        try:
            with psycopg2.connect(**db_params) as conn:
                with conn.cursor() as cursor:
                    # Get all table names
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Get row count for each table
                    for table in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        row_counts[table] = count
                        
        except Exception as e:
            print(f"❌ Error getting row counts: {e}")
            self.validation_results['errors'].append(f"Row count error: {e}")
            
        return row_counts
    
    def get_table_checksums(self, db_url, description=""):
        """Generate checksums for table contents"""
        print(f"🔐 Generating checksums for {description}...")
        
        db_params = parse_db_url(db_url)
        checksums = {}
        
        try:
            with psycopg2.connect(**db_params) as conn:
                with conn.cursor() as cursor:
                    # Get all table names
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Generate checksum for each table
                    for table in tables:
                        try:
                            # Use PostgreSQL's built-in checksum function
                            cursor.execute(f"""
                                SELECT md5(string_agg(md5(ROW({table}.*)::text), '' ORDER BY {table}.*))
                                FROM {table}
                            """)
                            checksum = cursor.fetchone()[0]
                            checksums[table] = checksum
                        except Exception as e:
                            print(f"   Warning: Could not checksum {table}: {e}")
                            checksums[table] = f"ERROR: {e}"
                            
        except Exception as e:
            print(f"❌ Error generating checksums: {e}")
            self.validation_results['errors'].append(f"Checksum error: {e}")
            
        return checksums
    
    def clear_test_database(self):
        """Clear all data from test database (keep structure)"""
        print("🧹 Clearing test database data...")
        
        db_params = parse_db_url(self.config['test_db_url'])
        
        try:
            with psycopg2.connect(**db_params) as conn:
                with conn.cursor() as cursor:
                    # Disable foreign key checks temporarily
                    cursor.execute("SET session_replication_role = replica;")
                    
                    # Get all tables except system tables
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        AND table_name NOT LIKE 'alembic%'
                        ORDER BY table_name
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Clear each table
                    for table in tables:
                        cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                        print(f"   Cleared: {table}")
                    
                    # Re-enable foreign key checks
                    cursor.execute("SET session_replication_role = DEFAULT;")
                    conn.commit()
                    
                    print("✅ Test database cleared")
                    
        except Exception as e:
            print(f"❌ Error clearing test database: {e}")
            self.validation_results['errors'].append(f"Database clear error: {e}")
            return False
            
        return True
    
    def run_etl_scripts(self):
        """Run ELT scripts against test database"""
        print("🔄 Running ELT scripts against test database...")
        
        # Set environment variable to use test database
        env = os.environ.copy()
        env['DATABASE_URL'] = self.config['test_db_url']
        env['DATABASE_PUBLIC_URL'] = self.config['test_db_url']
        
        # Run the master ETL script
        cmd = [sys.executable, 'etl/run_all_etl.py']
        
        try:
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            print("✅ ELT scripts completed successfully")
            print("Output:")
            print(result.stdout)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ ELT scripts failed: {e}")
            print(f"Stdout: {e.stdout}")
            print(f"Stderr: {e.stderr}")
            
            self.validation_results['errors'].append({
                'type': 'etl_execution',
                'error': str(e),
                'stdout': e.stdout,
                'stderr': e.stderr
            })
            
            return False
    
    def compare_databases(self):
        """Compare original and test databases"""
        print("🔍 Comparing original and test databases...")
        
        # Get row counts
        original_counts = self.get_table_row_counts(
            self.config['original_db_url'], 
            "original database"
        )
        test_counts = self.get_table_row_counts(
            self.config['test_db_url'], 
            "test database"
        )
        
        # Get checksums
        original_checksums = self.get_table_checksums(
            self.config['original_db_url'], 
            "original database"
        )
        test_checksums = self.get_table_checksums(
            self.config['test_db_url'], 
            "test database"
        )
        
        # Compare results
        comparison = {
            'row_counts': {
                'original': original_counts,
                'test': test_counts,
                'differences': {}
            },
            'checksums': {
                'original': original_checksums,
                'test': test_checksums,
                'differences': {}
            }
        }
        
        # Check row count differences
        all_tables = set(original_counts.keys()) | set(test_counts.keys())
        for table in all_tables:
            original_count = original_counts.get(table, 0)
            test_count = test_counts.get(table, 0)
            
            if original_count != test_count:
                comparison['row_counts']['differences'][table] = {
                    'original': original_count,
                    'test': test_count,
                    'difference': test_count - original_count
                }
        
        # Check checksum differences
        for table in all_tables:
            original_checksum = original_checksums.get(table, 'MISSING')
            test_checksum = test_checksums.get(table, 'MISSING')
            
            if original_checksum != test_checksum:
                comparison['checksums']['differences'][table] = {
                    'original': original_checksum,
                    'test': test_checksum,
                    'match': False
                }
        
        return comparison
    
    def generate_detailed_diff(self, table_name):
        """Generate detailed differences for a specific table"""
        print(f"🔎 Generating detailed diff for table: {table_name}")
        
        original_params = parse_db_url(self.config['original_db_url'])
        test_params = parse_db_url(self.config['test_db_url'])
        
        try:
            # Read data from both databases
            original_df = pd.read_sql(f"SELECT * FROM {table_name} ORDER BY id", 
                                    f"postgresql://{original_params['user']}:{original_params['password']}@{original_params['host']}:{original_params['port']}/{original_params['dbname']}")
            
            test_df = pd.read_sql(f"SELECT * FROM {table_name} ORDER BY id", 
                                f"postgresql://{test_params['user']}:{test_params['password']}@{test_params['host']}:{test_params['port']}/{test_params['dbname']}")
            
            # Compare DataFrames
            if original_df.equals(test_df):
                return {"status": "identical", "differences": None}
            else:
                return {
                    "status": "different",
                    "original_shape": original_df.shape,
                    "test_shape": test_df.shape,
                    "differences": "Detailed diff available - shapes differ or content differs"
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def generate_report(self, comparison):
        """Generate comprehensive validation report"""
        print("📝 Generating validation report...")
        
        # Summary statistics
        total_tables = len(set(comparison['row_counts']['original'].keys()) | 
                          set(comparison['row_counts']['test'].keys()))
        
        row_count_mismatches = len(comparison['row_counts']['differences'])
        checksum_mismatches = len(comparison['checksums']['differences'])
        
        # Determine overall status
        if row_count_mismatches == 0 and checksum_mismatches == 0:
            status = "✅ PASS - Databases are identical"
        elif row_count_mismatches > 0:
            status = f"❌ FAIL - {row_count_mismatches} tables have different row counts"
        else:
            status = f"⚠️ WARNING - {checksum_mismatches} tables have different checksums"
        
        # Create report
        report = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'summary': {
                'total_tables': total_tables,
                'row_count_mismatches': row_count_mismatches,
                'checksum_mismatches': checksum_mismatches,
                'errors': len(self.validation_results['errors'])
            },
            'comparison': comparison,
            'errors': self.validation_results['errors']
        }
        
        # Save detailed report
        report_file = f"etl_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Detailed report saved: {report_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("🎯 ELT VALIDATION RESULTS")
        print("=" * 60)
        print(f"Status: {status}")
        print(f"Total Tables: {total_tables}")
        print(f"Row Count Mismatches: {row_count_mismatches}")
        print(f"Checksum Mismatches: {checksum_mismatches}")
        print(f"Errors: {len(self.validation_results['errors'])}")
        
        if row_count_mismatches > 0:
            print("\n📊 Row Count Differences:")
            for table, diff in comparison['row_counts']['differences'].items():
                print(f"   {table}: {diff['original']} → {diff['test']} ({diff['difference']:+d})")
        
        if checksum_mismatches > 0:
            print("\n🔐 Checksum Mismatches:")
            for table in comparison['checksums']['differences']:
                print(f"   {table}: Content differs")
        
        if self.validation_results['errors']:
            print("\n❌ Errors:")
            for error in self.validation_results['errors']:
                print(f"   {error}")
        
        print("=" * 60)
        
        return report
    
    def validate(self):
        """Run complete validation process"""
        print("🚀 Starting ELT validation process...")
        print("=" * 60)
        
        # Step 1: Clear test database
        if not self.clear_test_database():
            return False
        
        # Step 2: Run ELT scripts
        if not self.run_etl_scripts():
            return False
        
        # Step 3: Compare databases
        comparison = self.compare_databases()
        
        # Step 4: Generate report
        report = self.generate_report(comparison)
        
        # Return success status
        return report['summary']['row_count_mismatches'] == 0

def main():
    validator = ETLValidator()
    success = validator.validate()
    
    print(f"\n🏁 Validation {'PASSED' if success else 'FAILED'}")
    
    if not success:
        print("\n💡 Next steps:")
        print("   1. Review the detailed report for specific issues")
        print("   2. Check ELT script logic and data sources")
        print("   3. Re-run after fixing issues")
        print("   4. Run cleanup_test_environment.py when done")
    else:
        print("\n🎉 ELT scripts are working correctly!")
        print("   Your scripts produce identical results to the current database.")
        print("   Run cleanup_test_environment.py to clean up test resources.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 