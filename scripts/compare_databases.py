#!/usr/bin/env python3
"""
Database Comparison Script
Compares Railway database with local database for schema and data differences
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.schema import CreateTable

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from database_config import get_db_engine, get_db_url

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseComparator:
    def __init__(self):
        self.local_url = self._get_local_url()
        self.railway_url = self._get_railway_url()
        self.local_engine = None
        self.railway_engine = None

    def _get_local_url(self):
        """Get local database URL"""
        # Temporarily set environment to ensure we get local URL
        original_sync = os.environ.get("SYNC_RAILWAY")
        os.environ.pop("SYNC_RAILWAY", None)

        try:
            url = get_db_url()
            logger.info(
                f"Local database URL: {url.split('@')[1] if '@' in url else 'unknown'}"
            )
            return url
        finally:
            if original_sync:
                os.environ["SYNC_RAILWAY"] = original_sync

    def _get_railway_url(self):
        """Get Railway database URL"""
        # Use the same hardcoded Railway URL from alembic/env.py
        url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        logger.info(
            f"Railway database URL: {url.split('@')[1] if '@' in url else 'unknown'}"
        )
        return url

    def connect_databases(self):
        """Create database connections"""
        try:
            self.local_engine = create_engine(self.local_url)
            self.railway_engine = create_engine(self.railway_url)

            # Test connections
            with self.local_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Local database connection successful")

            with self.railway_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Railway database connection successful")

        except Exception as e:
            logger.error(f"❌ Failed to connect to databases: {e}")
            raise

    def get_schema_info(self, engine, db_name):
        """Get schema information from a database"""
        inspector = inspect(engine)

        schema_info = {"tables": {}, "indexes": {}, "foreign_keys": {}, "sequences": []}

        # Get table information
        table_names = inspector.get_table_names()
        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            indexes = inspector.get_indexes(table_name)
            unique_constraints = inspector.get_unique_constraints(table_name)

            schema_info["tables"][table_name] = {
                "columns": columns,
                "primary_keys": primary_keys,
                "foreign_keys": foreign_keys,
                "indexes": indexes,
                "unique_constraints": unique_constraints,
            }

        logger.info(f"📊 {db_name} schema: {len(table_names)} tables")
        return schema_info

    def compare_schemas(self):
        """Compare schemas between local and Railway databases"""
        logger.info("🔍 Comparing database schemas...")

        local_schema = self.get_schema_info(self.local_engine, "Local")
        railway_schema = self.get_schema_info(self.railway_engine, "Railway")

        differences = {
            "tables_only_in_local": [],
            "tables_only_in_railway": [],
            "column_differences": {},
            "constraint_differences": {},
            "summary": {},
        }

        # Compare tables
        local_tables = set(local_schema["tables"].keys())
        railway_tables = set(railway_schema["tables"].keys())

        differences["tables_only_in_local"] = list(local_tables - railway_tables)
        differences["tables_only_in_railway"] = list(railway_tables - local_tables)

        # Compare columns for common tables
        common_tables = local_tables & railway_tables
        for table in common_tables:
            local_cols = {
                col["name"]: col for col in local_schema["tables"][table]["columns"]
            }
            railway_cols = {
                col["name"]: col for col in railway_schema["tables"][table]["columns"]
            }

            local_col_names = set(local_cols.keys())
            railway_col_names = set(railway_cols.keys())

            if local_col_names != railway_col_names:
                differences["column_differences"][table] = {
                    "only_in_local": list(local_col_names - railway_col_names),
                    "only_in_railway": list(railway_col_names - local_col_names),
                    "type_differences": [],
                }

                # Check for type differences in common columns
                common_cols = local_col_names & railway_col_names
                for col in common_cols:
                    local_type = str(local_cols[col]["type"])
                    railway_type = str(railway_cols[col]["type"])
                    if local_type != railway_type:
                        differences["column_differences"][table][
                            "type_differences"
                        ].append(
                            {
                                "column": col,
                                "local_type": local_type,
                                "railway_type": railway_type,
                            }
                        )

        # Create summary
        differences["summary"] = {
            "total_tables_local": len(local_tables),
            "total_tables_railway": len(railway_tables),
            "common_tables": len(common_tables),
            "tables_with_differences": len(differences["column_differences"]),
            "schema_identical": (
                len(differences["tables_only_in_local"]) == 0
                and len(differences["tables_only_in_railway"]) == 0
                and len(differences["column_differences"]) == 0
            ),
        }

        return differences

    def get_table_row_counts(self, engine, db_name):
        """Get row counts for all tables"""
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        row_counts = {}
        with engine.connect() as conn:
            for table in table_names:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    row_counts[table] = count
                except Exception as e:
                    logger.warning(f"Could not count rows in {table}: {e}")
                    row_counts[table] = "ERROR"

        logger.info(f"📊 {db_name} data: {len(table_names)} tables analyzed")
        return row_counts

    def compare_data(self):
        """Compare data between local and Railway databases"""
        logger.info("🔍 Comparing database data...")

        local_counts = self.get_table_row_counts(self.local_engine, "Local")
        railway_counts = self.get_table_row_counts(self.railway_engine, "Railway")

        data_differences = {
            "row_count_differences": {},
            "tables_only_in_local": [],
            "tables_only_in_railway": [],
            "summary": {},
        }

        # Find tables that exist in only one database
        local_tables = set(local_counts.keys())
        railway_tables = set(railway_counts.keys())

        data_differences["tables_only_in_local"] = list(local_tables - railway_tables)
        data_differences["tables_only_in_railway"] = list(railway_tables - local_tables)

        # Compare row counts for common tables
        common_tables = local_tables & railway_tables
        for table in common_tables:
            local_count = local_counts[table]
            railway_count = railway_counts[table]

            if local_count != railway_count:
                data_differences["row_count_differences"][table] = {
                    "local_count": local_count,
                    "railway_count": railway_count,
                    "difference": (
                        local_count - railway_count
                        if isinstance(local_count, int)
                        and isinstance(railway_count, int)
                        else "N/A"
                    ),
                }

        # Create summary
        total_local_rows = sum(
            count for count in local_counts.values() if isinstance(count, int)
        )
        total_railway_rows = sum(
            count for count in railway_counts.values() if isinstance(count, int)
        )

        data_differences["summary"] = {
            "total_tables_local": len(local_tables),
            "total_tables_railway": len(railway_tables),
            "common_tables": len(common_tables),
            "total_rows_local": total_local_rows,
            "total_rows_railway": total_railway_rows,
            "tables_with_count_differences": len(
                data_differences["row_count_differences"]
            ),
            "data_identical": len(data_differences["row_count_differences"]) == 0,
        }

        return data_differences

    def generate_alembic_diff(self):
        """Generate Alembic migration diff between databases"""
        logger.info("🔍 Generating Alembic schema diff...")

        try:
            # Create temporary alembic config for comparison
            alembic_cfg = Config("alembic.ini")

            # Compare Railway to Local (what changes are needed to make Railway match Local)
            logger.info(
                "Comparing Railway → Local (changes needed for Railway to match Local)"
            )
            os.environ["SYNC_RAILWAY"] = "true"

            # Generate a revision to see what changes would be needed
            with tempfile.TemporaryDirectory() as temp_dir:
                # This will show us what Alembic thinks needs to change
                revision_output = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "alembic",
                        "revision",
                        "--autogenerate",
                        "--message",
                        "temp_comparison",
                        "--head",
                        "head",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=".",
                )

                if revision_output.returncode == 0:
                    logger.info("✅ Alembic diff generated successfully")
                    return revision_output.stdout
                else:
                    logger.error(f"❌ Alembic diff failed: {revision_output.stderr}")
                    return f"Error generating diff: {revision_output.stderr}"

        except Exception as e:
            logger.error(f"❌ Error generating Alembic diff: {e}")
            return f"Error: {e}"
        finally:
            os.environ.pop("SYNC_RAILWAY", None)

    def run_full_comparison(self):
        """Run complete database comparison"""
        logger.info("🚀 Starting comprehensive database comparison...")

        try:
            self.connect_databases()

            # Schema comparison
            schema_diff = self.compare_schemas()

            # Data comparison
            data_diff = self.compare_data()

            # Generate report
            report = {
                "timestamp": datetime.now().isoformat(),
                "schema_comparison": schema_diff,
                "data_comparison": data_diff,
                "databases": {
                    "local": (
                        self.local_url.split("@")[1]
                        if "@" in self.local_url
                        else "unknown"
                    ),
                    "railway": (
                        self.railway_url.split("@")[1]
                        if "@" in self.railway_url
                        else "unknown"
                    ),
                },
            }

            return report

        except Exception as e:
            logger.error(f"❌ Comparison failed: {e}")
            raise
        finally:
            if self.local_engine:
                self.local_engine.dispose()
            if self.railway_engine:
                self.railway_engine.dispose()

    def print_report(self, report):
        """Print a formatted comparison report"""
        print("\n" + "=" * 80)
        print("🏓 RALLY DATABASE COMPARISON REPORT")
        print("=" * 80)
        print(f"📅 Generated: {report['timestamp']}")
        print(f"🗄️  Local DB: {report['databases']['local']}")
        print(f"🚂 Railway DB: {report['databases']['railway']}")
        print()

        # Schema Summary
        schema = report["schema_comparison"]["summary"]
        print("📋 SCHEMA COMPARISON SUMMARY")
        print("-" * 40)
        print(f"Local tables: {schema['total_tables_local']}")
        print(f"Railway tables: {schema['total_tables_railway']}")
        print(f"Common tables: {schema['common_tables']}")
        print(f"Tables with differences: {schema['tables_with_differences']}")
        print(
            f"Schema identical: {'✅ YES' if schema['schema_identical'] else '❌ NO'}"
        )
        print()

        # Schema Details
        if not schema["schema_identical"]:
            print("📋 SCHEMA DIFFERENCES")
            print("-" * 40)

            if report["schema_comparison"]["tables_only_in_local"]:
                print(
                    f"Tables only in LOCAL: {report['schema_comparison']['tables_only_in_local']}"
                )

            if report["schema_comparison"]["tables_only_in_railway"]:
                print(
                    f"Tables only in RAILWAY: {report['schema_comparison']['tables_only_in_railway']}"
                )

            if report["schema_comparison"]["column_differences"]:
                print("Column differences:")
                for table, diffs in report["schema_comparison"][
                    "column_differences"
                ].items():
                    print(f"  {table}:")
                    if diffs["only_in_local"]:
                        print(f"    Columns only in local: {diffs['only_in_local']}")
                    if diffs["only_in_railway"]:
                        print(
                            f"    Columns only in railway: {diffs['only_in_railway']}"
                        )
                    if diffs["type_differences"]:
                        print(f"    Type differences: {diffs['type_differences']}")
            print()

        # Data Summary
        data = report["data_comparison"]["summary"]
        print("📊 DATA COMPARISON SUMMARY")
        print("-" * 40)
        print(f"Local tables: {data['total_tables_local']}")
        print(f"Railway tables: {data['total_tables_railway']}")
        print(f"Common tables: {data['common_tables']}")
        print(f"Total rows (local): {data['total_rows_local']:,}")
        print(f"Total rows (railway): {data['total_rows_railway']:,}")
        print(f"Tables with count differences: {data['tables_with_count_differences']}")
        print(f"Data identical: {'✅ YES' if data['data_identical'] else '❌ NO'}")
        print()

        # Data Details
        if not data["data_identical"]:
            print("📊 DATA DIFFERENCES")
            print("-" * 40)

            if report["data_comparison"]["row_count_differences"]:
                print("Row count differences:")
                for table, counts in report["data_comparison"][
                    "row_count_differences"
                ].items():
                    print(
                        f"  {table}: Local={counts['local_count']}, Railway={counts['railway_count']}, Diff={counts['difference']}"
                    )
            print()

        print("=" * 80)


def main():
    """Main function to run database comparison"""
    comparator = DatabaseComparator()

    try:
        report = comparator.run_full_comparison()

        # Print report to console
        comparator.print_report(report)

        # Save detailed report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_comparison_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"📄 Detailed report saved to: {filename}")

        # Determine exit code based on differences
        schema_identical = report["schema_comparison"]["summary"]["schema_identical"]
        data_identical = report["data_comparison"]["summary"]["data_identical"]

        if schema_identical and data_identical:
            print("✅ Databases are identical!")
            return 0
        else:
            print("⚠️  Databases have differences!")
            return 1

    except Exception as e:
        logger.error(f"❌ Database comparison failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
