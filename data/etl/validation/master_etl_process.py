#!/usr/bin/env python3
"""
Master ETL Process
==================

Orchestrates the complete ETL workflow with integrated validation and monitoring:
1. Run data import (ETL)
2. Execute validation pipeline
3. Run integration tests
4. Generate data quality monitoring report
5. Alert on critical issues

This is the main script to run after any data import to ensure system reliability.
"""

import sys
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, List
import traceback

def run_script(script_path: str, description: str) -> Dict[str, Any]:
    """Run a Python script and return results"""
    print(f"\n🚀 RUNNING: {description}")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'),  # Run from project root
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return {
            'success': result.returncode == 0,
            'return_code': result.returncode,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'description': description
        }
        
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT: {description} took longer than 5 minutes")
        return {
            'success': False,
            'return_code': -1,
            'duration': datetime.now() - start_time,
            'error': 'Timeout',
            'description': description
        }
        
    except Exception as e:
        print(f"❌ ERROR running {description}: {str(e)}")
        return {
            'success': False,
            'return_code': -1,
            'duration': datetime.now() - start_time,
            'error': str(e),
            'description': description
        }

def run_master_etl_process():
    """Run the complete ETL process with validation and monitoring"""
    
    print("🎯 MASTER ETL PROCESS")
    print("=" * 80)
    print(f"Started at: {datetime.now()}")
    print("=" * 80)
    
    overall_start = datetime.now()
    results = []
    
    # Phase 1: Data Quality Pre-Check (Optional)
    print("\n📋 PHASE 1: PRE-IMPORT DATA QUALITY CHECK")
    pre_check = run_script('data/etl/validation/data_quality_monitor.py', 'Pre-import data quality baseline')
    results.append(pre_check)
    
    # Phase 2: ETL Import Process
    print("\n📥 PHASE 2: ETL IMPORT PROCESS")
    
    # Step 2a: Consolidate league JSON files
    consolidate_result = run_script(
        'data/etl/database_import/consolidate_league_jsons_to_all.py', 
        'Consolidate league JSON files to all/ directory'
    )
    results.append(consolidate_result)
    
    # Step 2b: Import consolidated data to database  
    if consolidate_result['success']:
        import_result = run_script(
            'data/etl/database_import/import_all_jsons_to_database.py',
            'Import all JSON data to database'
        )
        results.append(import_result)
    else:
        print("❌ Skipping database import due to consolidation failure")
        import_result = {
            'success': False,
            'return_code': -1,
            'duration': datetime.now() - datetime.now(),
            'description': 'Import all JSON data to database (skipped)',
            'error': 'Consolidation failed'
        }
        results.append(import_result)
    
    # Phase 3: Post-Import Validation
    print("\n🔍 PHASE 3: POST-IMPORT VALIDATION")
    validation_result = run_script('data/etl/validation/etl_validation_pipeline.py', 'ETL validation pipeline')
    results.append(validation_result)
    
    # Phase 4: Integration Testing
    print("\n🧪 PHASE 4: INTEGRATION TESTING")  
    integration_result = run_script('data/etl/validation/integration_tests.py', 'User-facing feature integration tests')
    results.append(integration_result)
    
    # Phase 5: Final Data Quality Monitoring
    print("\n📊 PHASE 5: FINAL DATA QUALITY MONITORING")
    monitoring_result = run_script('data/etl/validation/data_quality_monitor.py', 'Comprehensive data quality monitoring')
    results.append(monitoring_result)
    
    # Generate Master Report
    print_master_report(results, overall_start)
    
    # Determine overall success
    critical_failures = [r for r in results if not r['success'] and 'validation' in r['description'].lower()]
    integration_failures = [r for r in results if not r['success'] and 'integration' in r['description'].lower()]
    
    if critical_failures:
        print("\n🚨 CRITICAL ETL FAILURES DETECTED!")
        print("❌ DO NOT DEPLOY - Data quality issues found")
        return False
    elif integration_failures:
        print("\n⚠️  INTEGRATION TEST FAILURES DETECTED")
        print("⚠️  Review user-facing feature issues before deploying")
        return False
    else:
        print("\n🎉 ETL PROCESS COMPLETED SUCCESSFULLY!")
        print("✅ All validations passed - safe to deploy")
        return True

def print_master_report(results: List[Dict[str, Any]], start_time: datetime):
    """Print comprehensive master report"""
    
    end_time = datetime.now()
    total_duration = end_time - start_time
    
    print("\n" + "=" * 80)
    print("📊 MASTER ETL PROCESS REPORT")
    print("=" * 80)
    
    print(f"\n⏱️  TIMING SUMMARY:")
    print(f"   Started: {start_time}")
    print(f"   Completed: {end_time}")
    print(f"   Total Duration: {total_duration}")
    
    print(f"\n📋 PHASE SUMMARY:")
    successful_phases = 0
    failed_phases = 0
    
    for i, result in enumerate(results, 1):
        status_icon = "✅" if result['success'] else "❌"
        duration = result.get('duration', 'Unknown')
        print(f"   Phase {i}: {status_icon} {result['description']} ({duration})")
        
        if result['success']:
            successful_phases += 1
        else:
            failed_phases += 1
    
    # Overall Status
    print(f"\n🎯 OVERALL STATUS:")
    print(f"   ✅ Successful phases: {successful_phases}")
    print(f"   ❌ Failed phases: {failed_phases}")
    
    if failed_phases == 0:
        print(f"   🎉 STATUS: ALL PHASES PASSED")
        overall_status = "SUCCESS"
    else:
        print(f"   🚨 STATUS: {failed_phases} PHASE(S) FAILED")
        overall_status = "FAILURE"
    
    # Failure Details
    if failed_phases > 0:
        print(f"\n❌ FAILURE DETAILS:")
        for result in results:
            if not result['success']:
                print(f"   • {result['description']}: {result.get('error', 'Unknown error')}")
                if result.get('stderr'):
                    # Show first few lines of stderr
                    stderr_lines = result['stderr'].split('\n')[:3]
                    for line in stderr_lines:
                        if line.strip():
                            print(f"     {line}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if overall_status == "SUCCESS":
        print("   ✅ All phases completed successfully")
        print("   🚀 Safe to deploy to production")
        print("   📈 Consider scheduling regular monitoring")
        print("   🔄 Set up automated ETL validation pipeline")
    else:
        print("   🛑 DO NOT DEPLOY until issues are resolved")
        print("   🔧 Review failed phases and fix underlying issues")
        print("   📞 Alert development team about critical failures")
        print("   🔄 Re-run master ETL process after fixes")
    
    # Next Steps
    print(f"\n📋 NEXT STEPS:")
    print("   1. Review detailed logs from each phase")
    print("   2. Check logs/ directory for detailed metrics files")
    print("   3. Address any critical issues before deploying")
    if overall_status == "SUCCESS":
        print("   4. Set up monitoring dashboard for ongoing health checks")
        print("   5. Schedule regular ETL validation runs")
    else:
        print("   4. Fix critical data quality issues")
        print("   5. Re-run this master process")
        
    # File Locations
    print(f"\n📁 DETAILED REPORTS:")
    print("   📊 Data quality metrics: logs/data_quality_metrics_*.json")
    print("   🔍 Validation logs: Check console output above")
    print("   🧪 Integration test results: Check console output above")

def main():
    """Main entry point"""
    try:
        success = run_master_etl_process()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        return 2
    except Exception as e:
        print(f"\n❌ MASTER PROCESS ERROR: {str(e)}")
        print(traceback.format_exc())
        return 3

if __name__ == '__main__':
    sys.exit(main()) 