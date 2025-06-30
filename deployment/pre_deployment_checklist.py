#!/usr/bin/env python3
"""
Pre-Deployment Checklist for Rally
==================================

Run this before every deployment to production for sustainable development.
"""

import subprocess
import sys
import os
from datetime import datetime

def check_git_status():
    """Verify git state is clean and ready for deployment"""
    print("🔍 Checking Git Status...")
    
    # Check for uncommitted changes
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        print("❌ You have uncommitted changes:")
        print(result.stdout)
        return False
    
    # Check current branch
    result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
    current_branch = result.stdout.strip()
    
    if current_branch != 'main':
        print(f"⚠️  You're on '{current_branch}', not 'main'")
        print("   Consider: git checkout main && git merge {current_branch}")
        return False
    
    print("✅ Git status clean and on main branch")
    return True

def check_local_tests():
    """Check if local tests pass"""
    print("🧪 Checking Local Tests...")
    
    # Check if our session refresh test passes locally
    if os.path.exists('scripts/test_session_refresh.py'):
        result = subprocess.run([sys.executable, 'scripts/test_session_refresh.py'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Local session refresh test failed")
            print(result.stdout)
            print(result.stderr)
            return False
        print("✅ Local session refresh test passed")
    
    # Add more tests here as needed
    print("✅ Local tests passed")
    return True

def check_migration_files():
    """Check if there are any new migration files that need to be applied"""
    print("🗄️  Checking Database Migrations...")
    
    migration_files = []
    if os.path.exists('migrations'):
        for file in os.listdir('migrations'):
            if file.endswith('.sql') and 'add_system_settings' not in file:
                # Check if this is a new migration (simple heuristic)
                migration_files.append(file)
    
    if migration_files:
        print(f"⚠️  Found {len(migration_files)} migration files:")
        for file in migration_files:
            print(f"   📝 {file}")
        print("   Remember to apply these to production after deployment!")
        
        response = input("Continue with deployment? (y/n): ")
        return response.lower() == 'y'
    
    print("✅ No new migrations detected")
    return True

def verify_production_readiness():
    """Final checks before deployment"""
    print("🚀 Production Readiness Check...")
    
    checks = [
        "Database migration plan ready (if needed)",
        "Rollback plan defined",
        "Monitoring/alerts ready",
        "No breaking changes for existing users",
        "ETL compatibility verified"
    ]
    
    print("Manual verification checklist:")
    for i, check in enumerate(checks, 1):
        print(f"   {i}. {check}")
    
    response = input("All checks verified? (y/n): ")
    return response.lower() == 'y'

def main():
    print("🏗️  Rally Pre-Deployment Checklist")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    checks = [
        ("Git Status", check_git_status),
        ("Local Tests", check_local_tests), 
        ("Migration Files", check_migration_files),
        ("Production Readiness", verify_production_readiness),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        try:
            if not check_func():
                all_passed = False
                print(f"❌ {check_name} check failed")
            else:
                print(f"✅ {check_name} check passed")
        except Exception as e:
            print(f"❌ {check_name} check error: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 All checks passed! Ready for deployment.")
        print("\nNext steps:")
        print("1. git push origin main")
        print("2. Apply database migrations (if any)")
        print("3. python scripts/test_production_session_refresh.py")
        print("4. Monitor production for issues")
        return 0
    else:
        print("❌ Some checks failed. Please resolve before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 