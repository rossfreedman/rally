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
    
    # Check git status and auto-commit changes if any
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        print("📝 Uncommitted changes detected. Auto-committing for production deployment...")
        try:
            # Add all changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Generate descriptive commit message
            commit_message = generate_descriptive_commit_message("production")
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
        print("⚠️  Proceeding without staging test verification")
        return True

def get_current_branch():
    """Get the current git branch"""
    result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
    return result.stdout.strip()



def merge_staging_to_main():
    """Merge staging branch to main for production deployment"""
    print("🔄 Merging staging to main...")
    
    try:
        # Set git to non-interactive mode
        os.environ['GIT_MERGE_AUTOEDIT'] = 'no'
        os.environ['GIT_EDITOR'] = 'true'  # Use 'true' command as editor (always succeeds, no interaction)
        
        # Switch to main and pull latest
        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)
        
        # Merge staging (non-interactive)
        subprocess.run(['git', 'merge', 'staging', '--no-edit'], check=True)
        
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
    print("   python deployment/rollback.py  # Emergency rollback")
    print("   Contact users if needed")

def main():
    print("🚀 Rally Production Deployment")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        return 1
    
    # Get current branch
    current_branch = get_current_branch()
    
    if current_branch == 'main':
        print("📦 Already on main branch. Deploying current main state...")
        # Skip merge step since we're already on main, just push
        def push_main():
            try:
                subprocess.run(['git', 'push', 'origin', 'main'], check=True)
                print("✅ Successfully pushed main to Railway production")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to push main: {e}")
                return False
        merge_step = push_main
    else:
        print(f"📦 On branch '{current_branch}'. Will merge staging to main for production.")
        merge_step = merge_staging_to_main
    
    # Verify staging tests pass
    if not verify_staging_tests():
        return 1
    
    # Auto-proceed with production deployment (removed manual confirmation)
    print("✅ Proceeding with production deployment")
    
    # Deployment steps
    steps = [
        ("Merge staging to main" if current_branch != 'main' else "Push main", merge_step),
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