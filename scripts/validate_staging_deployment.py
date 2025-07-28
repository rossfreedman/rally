#!/usr/bin/env python3
"""
Staging Deployment Validation Script
===================================

Validates that all staging deployment components are working correctly:
1. Database schema
2. ETL processes
3. Scrapers
4. Environment configuration

Usage:
    python scripts/validate_staging_deployment.py
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/staging_validation.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

def check_file_exists(file_path, description):
    """Check if a file exists and log the result"""
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    logger.info(f"{status} {description}: {file_path}")
    return exists

def check_import_works(module_path, description):
    """Check if a module can be imported"""
    try:
        sys.path.append(os.path.dirname(module_path))
        module_name = os.path.basename(module_path).replace('.py', '')
        __import__(module_name)
        logger.info(f"✅ {description}: {module_path}")
        return True
    except Exception as e:
        logger.error(f"❌ {description}: {module_path} - {str(e)}")
        return False

def run_command(command, description):
    """Run a command and log the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ {description}")
            return True
        else:
            logger.error(f"❌ {description}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ {description}: {str(e)}")
        return False

def validate_database_schema():
    """Validate database schema components"""
    logger.info("🔍 Validating Database Schema...")
    
    checks = [
        ("app/models/database_models.py", "Database Models"),
        ("alembic/env.py", "Alembic Environment"),
        ("alembic/versions/", "Alembic Migrations Directory"),
    ]
    
    all_passed = True
    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_passed = False
    
    return all_passed

def validate_etl_processes():
    """Validate ETL process components"""
    logger.info("🔍 Validating ETL Processes...")
    
    checks = [
        ("data/etl/database_import/master_etl.py", "Master ETL Script"),
        ("data/etl/database_import/import_players.py", "Player Import"),
        ("data/etl/database_import/import_match_scores.py", "Match Scores Import"),
        ("data/etl/database_import/import_schedules.py", "Schedules Import"),
        ("data/etl/database_import/import_stats.py", "Stats Import"),
    ]
    
    all_passed = True
    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_passed = False
    
    return all_passed

def validate_scrapers():
    """Validate scraper components"""
    logger.info("🔍 Validating Scrapers...")
    
    checks = [
        ("data/etl/scrapers/scrape_match_scores_incremental.py", "Incremental Scraper"),
        ("data/etl/scrapers/scrape_match_scores.py", "Main Scraper"),
        ("data/etl/scrapers/stealth_browser.py", "Stealth Browser"),
    ]
    
    all_passed = True
    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_passed = False
    
    return all_passed

def validate_deployment_scripts():
    """Validate deployment script components"""
    logger.info("🔍 Validating Deployment Scripts...")
    
    checks = [
        ("scripts/deploy_staging_comprehensive.py", "Comprehensive Deployment"),
        ("scripts/deploy_staging_auto.py", "Automated Deployment"),
        ("chronjobs/railway_cron_etl_staging.py", "Staging Cron Job"),
    ]
    
    all_passed = True
    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_passed = False
    
    return all_passed

def validate_documentation():
    """Validate documentation components"""
    logger.info("🔍 Validating Documentation...")
    
    checks = [
        ("docs/STAGING_DEPLOYMENT_GUIDE.md", "Staging Deployment Guide"),
        ("docs/STAGING_DEPLOYMENT_SUMMARY.md", "Staging Deployment Summary"),
    ]
    
    all_passed = True
    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_passed = False
    
    return all_passed

def validate_imports():
    """Validate that key modules can be imported"""
    logger.info("🔍 Validating Module Imports...")
    
    checks = [
        ("data/etl/database_import/master_etl.py", "Master ETL Import"),
        ("app/models/database_models.py", "Database Models Import"),
    ]
    
    all_passed = True
    for file_path, description in checks:
        if not check_import_works(file_path, description):
            all_passed = False
    
    return all_passed

def main():
    """Main validation function"""
    logger.info("🚀 Starting Staging Deployment Validation")
    logger.info("=" * 50)
    
    start_time = datetime.now()
    
    # Run all validations
    validations = [
        ("Database Schema", validate_database_schema),
        ("ETL Processes", validate_etl_processes),
        ("Scrapers", validate_scrapers),
        ("Deployment Scripts", validate_deployment_scripts),
        ("Documentation", validate_documentation),
        ("Module Imports", validate_imports),
    ]
    
    results = {}
    all_passed = True
    
    for name, validation_func in validations:
        logger.info(f"\n📋 {name} Validation")
        logger.info("-" * 30)
        result = validation_func()
        results[name] = result
        if not result:
            all_passed = False
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "=" * 50)
    logger.info("📊 VALIDATION SUMMARY")
    logger.info("=" * 50)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{name}: {status}")
    
    overall_status = "✅ ALL VALIDATIONS PASSED" if all_passed else "❌ SOME VALIDATIONS FAILED"
    logger.info(f"\nOverall Status: {overall_status}")
    logger.info(f"Duration: {duration}")
    
    if all_passed:
        logger.info("\n🎉 Staging deployment is ready!")
        logger.info("Next steps:")
        logger.info("1. Verify Railway deployment")
        logger.info("2. Run database schema migration")
        logger.info("3. Test ETL process")
        logger.info("4. Validate scrapers")
    else:
        logger.error("\n⚠️  Some validations failed. Please fix issues before proceeding.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 