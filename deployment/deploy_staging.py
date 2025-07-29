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
        print("📝 Uncommitted changes detected. Preparing to commit for staging deployment...")
        try:
            # Add all changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Prompt for a custom commit message
            print("\nPlease enter a short commit message for this deployment (leave blank to auto-generate):")
            user_message = input('> ').strip()
            if user_message:
                commit_message = user_message
            else:
                commit_message = generate_descriptive_commit_message("staging")
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            print("✅ Changes committed automatically")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to auto-commit changes: {e}")
            return False
    
    print("✅ Prerequisites checked")
    return True

def analyze_file_changes():
    """Analyze the nature of file changes (additions, modifications, deletions)"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if not result.stdout.strip():
            return {"additions": 0, "modifications": 0, "deletions": 0}
        
        additions = 0
        modifications = 0
        deletions = 0
        
        for line in result.stdout.strip().split('\n'):
            if len(line) >= 2:
                status = line[:2].strip()
                if status == 'A' or status == '??':
                    additions += 1
                elif status == 'M':
                    modifications += 1
                elif status == 'D':
                    deletions += 1
        
        return {"additions": additions, "modifications": modifications, "deletions": deletions}
    except Exception:
        return {"additions": 0, "modifications": 0, "deletions": 0}

def detect_critical_changes():
    """Detect critical changes that need special attention"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if not result.stdout.strip():
            return []
        
        critical_changes = []
        
        for line in result.stdout.strip().split('\n'):
            if len(line) >= 3:
                filename = line[3:].strip()
                
                # Check for critical file changes
                if filename in ['requirements.txt', 'config.py', 'railway.toml']:
                    critical_changes.append("config")
                elif 'database' in filename.lower() and ('migration' in filename.lower() or 'schema' in filename.lower()):
                    critical_changes.append("schema")
                elif 'security' in filename.lower() or 'auth' in filename.lower():
                    critical_changes.append("security")
                elif 'etl' in filename.lower():
                    critical_changes.append("data")
                elif filename.startswith('static/') and ('js' in filename or 'css' in filename):
                    critical_changes.append("frontend")
        
        return list(set(critical_changes))  # Remove duplicates
    except Exception:
        return []

def generate_descriptive_commit_message(environment):
    """Generate a descriptive commit message based on changed files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    current_branch = get_current_branch()
    
    try:
        # Get list of changed files
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        if not result.stdout.strip():
            return f"Deploy to {environment} from {current_branch} - {timestamp}"
        
        # Analyze change types
        change_analysis = analyze_file_changes()
        critical_changes = detect_critical_changes()
        
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
            "database": [],
            "scripts": [],
            "tests": [],
            "other": []
        }
        
        # Track specific important files for better descriptions
        important_files = {
            "auth": [],
            "api": [],
            "mobile": [],
            "admin": [],
            "etl": [],
            "database": [],
            "security": []
        }
        
        for line in result.stdout.strip().split('\n'):
            if len(line) >= 3:
                filename = line[3:].strip()
                changed_files.append(filename)
                # Categorize file
                if filename.startswith('templates/'):
                    file_categories["templates"].append(filename)
                    if 'auth' in filename.lower() or 'login' in filename.lower():
                        important_files["auth"].append(filename)
                    elif 'mobile' in filename.lower():
                        important_files["mobile"].append(filename)
                    elif 'admin' in filename.lower():
                        important_files["admin"].append(filename)
                elif '/routes/' in filename or filename.startswith('routes/'):
                    file_categories["routes"].append(filename)
                    if 'auth' in filename.lower() or 'login' in filename.lower():
                        important_files["auth"].append(filename)
                    elif 'api' in filename.lower():
                        important_files["api"].append(filename)
                    elif 'mobile' in filename.lower():
                        important_files["mobile"].append(filename)
                    elif 'admin' in filename.lower():
                        important_files["admin"].append(filename)
                elif '/services/' in filename or filename.startswith('services/'):
                    file_categories["services"].append(filename)
                    if 'auth' in filename.lower() or 'association' in filename.lower():
                        important_files["auth"].append(filename)
                    elif 'api' in filename.lower():
                        important_files["api"].append(filename)
                    elif 'etl' in filename.lower():
                        important_files["etl"].append(filename)
                elif filename.startswith('static/'):
                    file_categories["static"].append(filename)
                    if 'mobile' in filename.lower():
                        important_files["mobile"].append(filename)
                elif filename.startswith('deployment/'):
                    file_categories["deployment"].append(filename)
                elif filename.startswith('scripts/'):
                    file_categories["scripts"].append(filename)
                    if 'etl' in filename.lower():
                        important_files["etl"].append(filename)
                    elif 'database' in filename.lower():
                        important_files["database"].append(filename)
                elif filename.startswith('tests/'):
                    file_categories["tests"].append(filename)
                elif filename.startswith('data/') or filename.startswith('migrations/'):
                    file_categories["database"].append(filename)
                    important_files["database"].append(filename)
                elif filename in ['config.py', 'requirements.txt', 'railway.toml', '.cursorrules']:
                    file_categories["config"].append(filename)
                elif filename.startswith('docs/') or filename.endswith('.md'):
                    file_categories["docs"].append(filename)
                elif 'security' in filename.lower() or 'auth' in filename.lower():
                    important_files["security"].append(filename)
                    file_categories["other"].append(filename)
                else:
                    file_categories["other"].append(filename)
        
        # Build descriptive message with priority features
        priority_features = []
        # Check for critical changes first (these take precedence)
        if critical_changes:
            priority_features.extend(critical_changes)
        # Check for high-impact changes
        if important_files["auth"]:
            priority_features.append("auth")
        if important_files["mobile"]:
            priority_features.append("mobile")
        if important_files["api"]:
            priority_features.append("API")
        if important_files["admin"]:
            priority_features.append("admin")
        if important_files["etl"]:
            priority_features.append("ETL")
        if important_files["database"]:
            priority_features.append("database")
        if important_files["security"]:
            priority_features.append("security")
        # Build category summary
        parts = []
        if file_categories["routes"]:
            parts.append(f"routes({len(file_categories['routes'])})")
        if file_categories["templates"]:
            parts.append(f"templates({len(file_categories['templates'])})")
        if file_categories["services"]:
            parts.append(f"services({len(file_categories['services'])})")
        if file_categories["static"]:
            parts.append(f"UI({len(file_categories['static'])})")
        if file_categories["database"]:
            parts.append(f"DB({len(file_categories['database'])})")
        if file_categories["scripts"]:
            parts.append(f"scripts({len(file_categories['scripts'])})")
        if file_categories["tests"]:
            parts.append(f"tests({len(file_categories['tests'])})")
        if file_categories["deployment"]:
            parts.append(f"deploy({len(file_categories['deployment'])})")
        if file_categories["config"]:
            parts.append(f"config({len(file_categories['config'])})")
        if file_categories["docs"]:
            parts.append(f"docs({len(file_categories['docs'])})")
        if file_categories["other"]:
            parts.append(f"other({len(file_categories['other'])})")
        # Construct the commit message with change analysis
        change_summary = []
        if change_analysis["additions"] > 0:
            change_summary.append(f"+{change_analysis['additions']}")
        if change_analysis["modifications"] > 0:
            change_summary.append(f"~{change_analysis['modifications']}")
        if change_analysis["deletions"] > 0:
            change_summary.append(f"-{change_analysis['deletions']}")
        change_info = f"[{', '.join(change_summary)}]" if change_summary else ""
        # --- Always show a prefix ---
        prefix = None
        if priority_features:
            prefix = ", ".join(priority_features)
        else:
            # Use the first non-empty category as prefix
            for part in parts:
                # Extract the category name (before '(')
                cat = part.split('(')[0]
                if cat:
                    prefix = cat.strip()
                    break
        if prefix:
            if parts:
                changes_summary = ", ".join(parts)
                commit_message = f"{prefix} | Deploy to {environment} from {current_branch}: {changes_summary} {change_info} - {timestamp}"
            else:
                commit_message = f"{prefix} | Deploy to {environment} from {current_branch} {change_info} - {timestamp}"
        else:
            commit_message = f"Deploy to {environment} from {current_branch} - {len(changed_files)} files {change_info} - {timestamp}"
        # Keep message under reasonable length (increased to 120 for more descriptive messages)
        if len(commit_message) > 120:
            if prefix:
                commit_message = f"{prefix} | Deploy to {environment} from {current_branch} {change_info} - {len(changed_files)} files - {timestamp}"
            else:
                commit_message = f"Deploy to {environment} from {current_branch}: {len(changed_files)} files {change_info} - {timestamp}"
        return commit_message
    except Exception as e:
        print(f"⚠️  Could not analyze changes: {e}")
        return f"Deploy to {environment} from {current_branch} - {timestamp}"

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
        
        # Try health endpoint first (more reliable)
        try:
            response = requests.get("https://rally-staging.up.railway.app/health", 
                                  timeout=15)
            if response.status_code == 200:
                print("✅ Staging environment is responding (health check)")
                return True
        except Exception as health_error:
            print(f"⚠️  Health check failed: {health_error}")
        
        # Fallback to mobile endpoint
        try:
            response = requests.get("https://rally-staging.up.railway.app/mobile", 
                                  allow_redirects=False, timeout=15)
            
            if response.status_code in [200, 302]:
                print("✅ Staging environment is responding (mobile endpoint)")
                return True
            else:
                print(f"⚠️  Staging returned status code: {response.status_code}")
                return False
                
        except Exception as mobile_error:
            print(f"⚠️  Mobile endpoint check failed: {mobile_error}")
            
    except Exception as e:
        print(f"❌ Failed to check staging: {e}")
    
    # If we get here, both checks failed but don't fail the deployment
    print("⚠️  Staging health check failed, but deployment may still be successful")
    print("🌐 Check manually: https://rally-staging.up.railway.app")
    return True  # Don't fail deployment for health check issues

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