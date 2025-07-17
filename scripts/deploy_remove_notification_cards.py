#!/usr/bin/env python3
"""
Deploy Remove Unwanted Notification Cards
"""

import os
import sys
import subprocess
from datetime import datetime

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def check_git_status():
    """Check git status and ensure we're on the right branch"""
    print("=== Checking Git Status ===")
    
    # Check current branch
    result = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True)
    current_branch = result.stdout.strip()
    print(f"Current branch: {current_branch}")
    
    # Check for uncommitted changes
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  Uncommitted changes detected:")
        print(result.stdout)
        return False
    else:
        print("✅ No uncommitted changes")
        return True

def deploy_remove_notification_cards():
    """Deploy removal of unwanted notification cards"""
    print("=== Deploying Remove Unwanted Notification Cards ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check git status
    if not check_git_status():
        print("❌ Please commit or stash your changes before deploying")
        return False
    
    # Create deployment commit
    commit_message = "feat: Remove unwanted notification cards"
    commit_body = """
Removed unwanted notification cards from fallback notifications:

- Removed "Welcome back, [Name]!" card
- Removed "Team Overview" card
- Kept only "Stay Connected" notification for team engagement

This eliminates redundant/generic notifications and provides a cleaner
user experience with only relevant, actionable notifications.
"""
    
    # Add modified files
    files_to_add = [
        "app/routes/api_routes.py",
        "scripts/test_removed_notifications.py"
    ]
    
    for file_path in files_to_add:
        if os.path.exists(file_path):
            if not run_command(f"git add {file_path}", f"Adding {file_path}"):
                return False
    
    # Commit changes
    if not run_command(f'git commit -m "{commit_message}" -m "{commit_body.strip()}"', "Creating deployment commit"):
        return False
    
    # Push to staging
    if not run_command("git push origin staging", "Pushing to staging branch"):
        return False
    
    print("\n🎉 Unwanted notification cards removed and deployed to staging!")
    print("\nChanges made:")
    print("✅ Removed 'Welcome back, [Name]!' notification card")
    print("✅ Removed 'Team Overview' notification card")
    print("✅ Kept 'Stay Connected' notification for team engagement")
    print("✅ Cleaner, more focused notification experience")
    
    print("\nNext steps:")
    print("1. Monitor staging environment for any issues")
    print("2. Test notification display on staging")
    print("3. Deploy to production when ready")
    
    return True

def main():
    """Main deployment function"""
    print("Remove Unwanted Notification Cards Deployment")
    print("=" * 50)
    
    # Confirm deployment
    response = input("Deploy removal of unwanted notification cards to staging? (y/N): ")
    if response.lower() != 'y':
        print("Deployment cancelled")
        return
    
    # Run deployment
    success = deploy_remove_notification_cards()
    
    if success:
        print("\n✅ Deployment completed successfully!")
    else:
        print("\n❌ Deployment failed. Check the output above for details.")

if __name__ == "__main__":
    main() 