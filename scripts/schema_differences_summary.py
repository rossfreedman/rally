#!/usr/bin/env python3
"""
Schema Differences Summary
=========================

Analyzes the multi-environment comparison results and highlights the key differences
that need attention.
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Any

def load_latest_comparison():
    """Load the most recent comparison report"""
    import glob
    import os
    
    # Find the most recent comparison file
    files = glob.glob("multi_environment_comparison_*.json")
    if not files:
        print("❌ No comparison files found. Run compare_all_environments.py first.")
        return None
    
    # Sort by modification time and get the latest
    latest_file = max(files, key=os.path.getmtime)
    
    with open(latest_file, 'r') as f:
        return json.load(f)

def analyze_critical_differences(report: Dict[str, Any]):
    """Analyze and categorize critical differences"""
    
    print("🔍 RALLY DATABASE SCHEMA DIFFERENCES ANALYSIS")
    print("=" * 80)
    print(f"📅 Report generated: {report['timestamp']}")
    print(f"🌍 Environments compared: {', '.join(report['connected_environments'])}")
    print()
    
    # 1. MISSING TABLES ANALYSIS
    print("🚨 CRITICAL: MISSING TABLES")
    print("-" * 50)
    
    table_presence = report["schema_comparison"]["tables_by_environment"]
    all_tables = set(table_presence.keys())
    
    # Find tables missing in production (most critical)
    prod_tables = set()
    for table, presence in table_presence.items():
        if presence.get("production", False):
            prod_tables.add(table)
    
    missing_in_prod = all_tables - prod_tables
    if missing_in_prod:
        print("❌ Tables missing in PRODUCTION (CRITICAL):")
        for table in sorted(missing_in_prod):
            print(f"  • {table}")
        print()
    
    # Find tables missing in staging
    staging_tables = set()
    for table, presence in table_presence.items():
        if presence.get("staging", False):
            staging_tables.add(table)
    
    missing_in_staging = all_tables - staging_tables
    if missing_in_staging:
        print("⚠️  Tables missing in STAGING:")
        for table in sorted(missing_in_staging):
            print(f"  • {table}")
        print()
    
    # 2. COLUMN DIFFERENCES ANALYSIS
    print("📋 COLUMN DIFFERENCES")
    print("-" * 50)
    
    column_diffs = report["schema_comparison"]["column_differences"]
    if column_diffs:
        for table, diffs in column_diffs.items():
            print(f"\n📊 Table: {table}")
            
            # Missing columns by environment
            if diffs["missing_columns"]:
                for env, missing in diffs["missing_columns"].items():
                    env_name = report["environments"][env]["name"]
                    print(f"  ❌ Missing in {env_name}: {missing}")
            
            # Type differences
            if diffs["type_differences"]:
                for diff_key, diff_info in diffs["type_differences"].items():
                    print(f"  🔄 Type difference {diff_key}: {diff_info}")
    else:
        print("✅ No column differences found")
    print()
    
    # 3. DATA VOLUME ANALYSIS
    print("📊 DATA VOLUME COMPARISON")
    print("-" * 50)
    
    data_summary = report["data_comparison"]["summary"]
    for env in data_summary["environments_compared"]:
        env_name = report["environments"][env]["name"]
        row_count = data_summary["total_rows_by_environment"][env]
        print(f"{env_name}: {row_count:,} total rows")
    
    # Highlight significant data differences
    row_diffs = report["data_comparison"]["row_count_differences"]
    if row_diffs:
        print(f"\n⚠️  Tables with significant row count differences: {len(row_diffs)}")
        
        # Show the most significant differences
        significant_diffs = []
        for table, counts_info in row_diffs.items():
            counts = counts_info["counts"]
            max_count = max(counts.values())
            min_count = min(counts.values())
            if max_count > 0 and min_count > 0:
                ratio = max_count / min_count
                if ratio > 2:  # More than 2x difference
                    significant_diffs.append((table, ratio, counts))
            elif max_count > 0 and min_count == 0:
                # Handle case where one environment has data and others don't
                significant_diffs.append((table, float('inf'), counts))
        
        if significant_diffs:
            print("📈 Most significant data differences:")
            for table, ratio, counts in sorted(significant_diffs, key=lambda x: x[1], reverse=True)[:10]:
                print(f"  • {table}: {ratio:.1f}x difference")
                for env, count in counts.items():
                    env_name = report["environments"][env]["name"]
                    print(f"    {env_name}: {count:,} rows")
    print()
    
    # 4. RECOMMENDATIONS
    print("💡 RECOMMENDATIONS")
    print("-" * 50)
    
    recommendations = []
    
    # Schema recommendations
    if missing_in_prod:
        recommendations.append("🚨 CRITICAL: Deploy missing tables to production")
        recommendations.append("   - Run database migrations to add missing tables")
        recommendations.append("   - Ensure all environments have consistent schema")
    
    if column_diffs:
        recommendations.append("⚠️  Review column differences")
        recommendations.append("   - Check if missing columns are needed in all environments")
        recommendations.append("   - Verify column types are compatible")
    
    # Data recommendations
    if row_diffs:
        recommendations.append("📊 Investigate data inconsistencies")
        recommendations.append("   - Check ETL processes for data synchronization")
        recommendations.append("   - Verify data integrity across environments")
    
    # Environment-specific recommendations
    if "local" in report["connected_environments"] and "production" in report["connected_environments"]:
        local_tables = set()
        for table, presence in table_presence.items():
            if presence.get("local", False):
                local_tables.add(table)
        
        extra_local_tables = local_tables - prod_tables
        if extra_local_tables:
            recommendations.append("🧹 Clean up local development tables")
            recommendations.append("   - Remove test/backup tables from local environment")
            recommendations.append(f"   - Tables to consider removing: {list(extra_local_tables)}")
    
    if not recommendations:
        recommendations.append("✅ All environments are consistent!")
    
    for rec in recommendations:
        print(rec)
    
    print()
    print("=" * 80)

def main():
    """Main function to analyze schema differences"""
    report = load_latest_comparison()
    
    if not report:
        return 1
    
    analyze_critical_differences(report)
    
    # Determine exit code
    schema_identical = report["schema_comparison"]["summary"]["schema_identical"]
    data_identical = report["data_comparison"]["summary"]["data_identical"]
    
    if schema_identical and data_identical:
        print("✅ All environments are consistent!")
        return 0
    else:
        print("⚠️  Environment differences require attention!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 