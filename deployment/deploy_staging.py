#!/usr/bin/env python3
"""
Deploy to Staging Environment
============================

Deploy feature branch to staging for testing before production deployment.
This script handles the staging deployment workflow safely.
"""

import subprocess
import sys
import os
from datetime import datetime

def check_prerequisites():
    """Check that we're ready for staging deployment"""
    print("🔍 Checking Prerequisites...")
    
    # Check if we're in Rally project directory
    if not os.path.exists('requirements.txt') or not os.path.exists('server.py'):
        print("❌ Not in Rally project directory")
        return False
    
    # Check git status and auto-commit changes if any
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        print("📝 Uncommitted changes detected. Auto-committing for staging deployment...")
        try:
            # Add all changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Commit with timestamp message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_message = f"Auto-commit for staging deployment - {timestamp}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            print("✅ Changes committed automatically")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to auto-commit changes: {e}")
            return False
    
    print("✅ Prerequisites checked")
    return True

def get_current_branch():
    """Get the current git branch"""
    result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
    return result.stdout.strip()

def merge_to_staging(feature_branch):
    """Merge feature branch to staging"""
    print(f"🔄 Merging {feature_branch} to staging...")
    
    try:
        # Set git to non-interactive mode
        os.environ['GIT_MERGE_AUTOEDIT'] = 'no'
        os.environ['GIT_EDITOR'] = 'true'  # Use 'true' command as editor (always succeeds, no interaction)
        # Switch to staging and pull latest
        subprocess.run(['git', 'checkout', 'staging'], check=True)
        subprocess.run(['git', 'pull', 'origin', 'staging'], check=True)
        
        # Merge feature branch (non-interactive)
        subprocess.run(['git', 'merge', feature_branch, '--no-edit'], check=True)
        
        # Push to staging
        subprocess.run(['git', 'push', 'origin', 'staging'], check=True)
        
        print("✅ Successfully merged to staging")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to merge to staging: {e}")
        return False

def check_staging_deployment():
    """Check if staging deployment was successful"""
    print("🌐 Checking staging deployment...")
    
    try:
        import requests
        response = requests.get("https://rally-staging.up.railway.app/mobile", 
                              allow_redirects=False, timeout=10)
        
        if response.status_code in [200, 302]:
            print("✅ Staging environment is responding")
            return True
        else:
            print(f"⚠️  Staging returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check staging: {e}")
        return False

def run_staging_tests():
    """Run automated tests against staging"""
    print("🧪 Running staging tests...")
    
    if os.path.exists('deployment/test_staging_session_refresh.py'):
        try:
            result = subprocess.run([sys.executable, 'deployment/test_staging_session_refresh.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Staging tests passed")
                return True
            else:
                print("❌ Staging tests failed:")
                print(result.stdout)
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ Error running staging tests: {e}")
            return False
    else:
        print("⚠️  No staging tests found, skipping automated testing")
        return True

def provide_staging_info():
    """Provide information about testing on staging"""
    print("\n📋 STAGING DEPLOYMENT COMPLETE")
    print("=" * 60)
    print("🌐 Staging URL: https://rally-staging.up.railway.app")
    print("🗄️  Database: Railway staging database")
    print("🧪 Status: Ready for testing")
    print()
    print("📝 Manual Testing Checklist:")
    print("   □ Login functionality works")
    print("   □ Key user workflows function properly")
    print("   □ No console errors in browser")
    print("   □ Mobile functionality works")
    print("   □ ETL processes work (if applicable)")
    print("   □ Performance is acceptable")
    print()
    print("✅ When staging tests pass, deploy to production with:")
    print("   python deployment/deploy_production.py")

def main():
    print("🚀 Rally Staging Deployment")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        return 1
    
    # Get current branch (this should be the feature branch)
    current_branch = get_current_branch()
    
    if current_branch == 'staging':
        print("📦 Already on staging branch. Deploying current staging state...")
        # Skip merge step since we're already on staging, just push
        def push_staging():
            try:
                subprocess.run(['git', 'push', 'origin', 'staging'], check=True)
                print("✅ Successfully pushed staging to Railway")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to push staging: {e}")
                return False
        merge_step = push_staging
    else:
        merge_step = lambda: merge_to_staging(current_branch)
    
    if current_branch == 'main':
        print("⚠️  You're on main branch. Deploying main directly to staging...")
        # Allow main→staging deployment for quick testing
    
    print(f"📦 Deploying feature branch: {current_branch}")
    
    # Auto-proceed with deployment (removed manual confirmation)
    print(f"✅ Proceeding with deployment of '{current_branch}' to staging")
    
    # Deployment steps
    steps = [
        ("Merge to staging" if current_branch != 'staging' else "Push staging", merge_step),
        ("Check deployment", check_staging_deployment),
        ("Run staging tests", run_staging_tests),
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}:")
        if not step_func():
            print(f"❌ {step_name} failed. Stopping deployment.")
            return 1
    
    # Provide staging information
    provide_staging_info()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 