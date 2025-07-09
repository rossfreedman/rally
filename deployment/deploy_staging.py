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
            
            # Generate descriptive commit message
            commit_message = generate_descriptive_commit_message("staging")
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            print("✅ Changes committed automatically")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to auto-commit changes: {e}")
            return False
    
    print("✅ Prerequisites checked")
    return True

def generate_descriptive_commit_message(environment):
    """Generate a descriptive commit message based on changed files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    try:
        # Get list of changed files
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if not result.stdout.strip():
            return f"Deploy to {environment} - {timestamp}"
        
        # Analyze changed files
        changed_files = []
        file_categories = {
            "templates": [],
            "routes": [],
            "services": [],
            "static": [],
            "config": [],
            "docs": [],
            "deployment": [],
            "other": []
        }
        
        for line in result.stdout.strip().split('\n'):
            if len(line) >= 3:
                filename = line[3:].strip()
                changed_files.append(filename)
                
                # Categorize file
                if filename.startswith('templates/'):
                    file_categories["templates"].append(filename)
                elif '/routes/' in filename or filename.startswith('routes/'):
                    file_categories["routes"].append(filename)
                elif '/services/' in filename or filename.startswith('services/'):
                    file_categories["services"].append(filename)
                elif filename.startswith('static/'):
                    file_categories["static"].append(filename)
                elif filename.startswith('deployment/'):
                    file_categories["deployment"].append(filename)
                elif filename in ['config.py', 'requirements.txt', 'railway.toml', '.cursorrules']:
                    file_categories["config"].append(filename)
                elif filename.startswith('docs/') or filename.endswith('.md'):
                    file_categories["docs"].append(filename)
                else:
                    file_categories["other"].append(filename)
        
        # Build descriptive message
        parts = []
        
        if file_categories["routes"]:
            parts.append(f"routes({len(file_categories['routes'])})")
        if file_categories["templates"]:
            parts.append(f"templates({len(file_categories['templates'])})")
        if file_categories["services"]:
            parts.append(f"services({len(file_categories['services'])})")
        if file_categories["static"]:
            parts.append(f"UI({len(file_categories['static'])})")
        if file_categories["deployment"]:
            parts.append(f"deploy({len(file_categories['deployment'])})")
        if file_categories["config"]:
            parts.append(f"config({len(file_categories['config'])})")
        if file_categories["docs"]:
            parts.append(f"docs({len(file_categories['docs'])})")
        if file_categories["other"]:
            parts.append(f"other({len(file_categories['other'])})")
        
        if parts:
            changes_summary = ", ".join(parts)
            commit_message = f"Deploy to {environment}: {changes_summary} - {timestamp}"
        else:
            commit_message = f"Deploy to {environment} - {len(changed_files)} files updated - {timestamp}"
        
        # Keep message under reasonable length (increased from 72 to 100)
        if len(commit_message) > 100:
            commit_message = f"Deploy to {environment}: {len(changed_files)} files updated - {timestamp}"
        
        return commit_message
        
    except Exception as e:
        print(f"⚠️  Could not analyze changes: {e}")
        return f"Deploy to {environment} - {timestamp}"

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