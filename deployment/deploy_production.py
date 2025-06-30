#!/usr/bin/env python3
"""
Deploy to Production Environment
===============================

Deploy staging to production after thorough testing.
This script handles the production deployment workflow safely.
"""

import subprocess
import sys
import os
from datetime import datetime

def check_prerequisites():
    """Check that we're ready for production deployment"""
    print("🔍 Checking Prerequisites...")
    
    # Check if we're in Rally project directory
    if not os.path.exists('requirements.txt') or not os.path.exists('server.py'):
        print("❌ Not in Rally project directory")
        return False
    
    # Check git status
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        print("❌ You have uncommitted changes. Please commit or stash them.")
        return False
    
    print("✅ Prerequisites checked")
    return True

def verify_staging_tests():
    """Verify that staging has been tested"""
    print("🧪 Verifying Staging Tests...")
    
    # Run staging tests to ensure they pass
    if os.path.exists('deployment/test_staging_session_refresh.py'):
        try:
            result = subprocess.run([sys.executable, 'deployment/test_staging_session_refresh.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Staging tests passing")
                return True
            else:
                print("❌ Staging tests failing. Do not deploy to production!")
                print("Fix issues on staging first.")
                return False
        except Exception as e:
            print(f"❌ Error running staging tests: {e}")
            return False
    else:
        print("⚠️  No staging tests found")
        response = input("Continue without staging test verification? (y/n): ")
        return response.lower() == 'y'

def confirm_production_deployment():
    """Get explicit confirmation for production deployment"""
    print("\n🚨 PRODUCTION DEPLOYMENT CONFIRMATION")
    print("=" * 60)
    print("This will deploy staging changes to the LIVE production environment")
    print("where real users will be affected.")
    print()
    print("Pre-flight checklist:")
    print("□ Staging has been thoroughly tested")
    print("□ All functionality works as expected")
    print("□ Database migrations are ready (if needed)")
    print("□ No breaking changes for existing users")
    print("□ Rollback plan is ready if needed")
    print()
    
    response = input("Are you sure you want to deploy to PRODUCTION? (yes/no): ")
    return response.lower() == 'yes'

def merge_staging_to_main():
    """Merge staging branch to main for production deployment"""
    print("🔄 Merging staging to main...")
    
    try:
        # Switch to main and pull latest
        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
        
        # Merge staging
        subprocess.run(['git', 'merge', 'staging'], check=True)
        
        # Push to main (triggers Railway production deployment)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        
        print("✅ Successfully merged staging to main")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to merge staging to main: {e}")
        return False

def check_production_deployment():
    """Check if production deployment was successful"""
    print("🌐 Checking production deployment...")
    
    try:
        import requests
        response = requests.get("https://rally.up.railway.app/mobile", 
                              allow_redirects=False, timeout=10)
        
        if response.status_code in [200, 302]:
            print("✅ Production environment is responding")
            return True
        else:
            print(f"⚠️  Production returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check production: {e}")
        return False

def run_production_verification():
    """Run verification tests against production"""
    print("🔍 Running production verification...")
    
    if os.path.exists('deployment/test_production_session_refresh.py'):
        try:
            result = subprocess.run([sys.executable, 'deployment/test_production_session_refresh.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Production verification passed")
                return True
            else:
                print("❌ Production verification failed:")
                print(result.stdout)
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ Error running production verification: {e}")
            return False
    else:
        print("⚠️  No production verification tests found")
        return True

def provide_production_info():
    """Provide information about the production deployment"""
    print("\n🎉 PRODUCTION DEPLOYMENT COMPLETE")
    print("=" * 60)
    print("🌐 Production URL: https://rally.up.railway.app")
    print("🗄️  Database: Railway production database")
    print("✅ Status: Live for users")
    print()
    print("📊 Post-deployment monitoring:")
    print("   □ Monitor error rates in logs")
    print("   □ Check user feedback")
    print("   □ Verify key functionality works")
    print("   □ Monitor performance metrics")
    print()
    print("🔧 If issues arise:")
    print("   python scripts/rollback.py  # Emergency rollback")
    print("   Contact users if needed")

def main():
    print("🚀 Rally Production Deployment")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        return 1
    
    # Verify staging tests pass
    if not verify_staging_tests():
        return 1
    
    # Get explicit confirmation
    if not confirm_production_deployment():
        print("Production deployment cancelled")
        return 0
    
    # Deployment steps
    steps = [
        ("Merge staging to main", merge_staging_to_main),
        ("Check deployment", check_production_deployment),
        ("Run verification", run_production_verification),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}:")
        if not step_func():
            print(f"❌ {step_name} failed!")
            print("🚨 PRODUCTION DEPLOYMENT FAILED")
            print("Check logs and consider rollback if needed")
            return 1
    
    # Provide production information
    provide_production_info()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 