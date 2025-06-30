#!/usr/bin/env python3
"""
Deployment Status Checker for Rally

This script helps prevent the issue where local changes aren't deployed to Railway
because they haven't been committed and pushed to git.

Usage: python scripts/check_deployment_status.py
"""

import subprocess
import sys
import json
from datetime import datetime

def run_git_command(command):
    """Run a git command and return the result"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip(), True
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), False

def check_git_status():
    """Check if there are uncommitted changes"""
    output, success = run_git_command(['git', 'status', '--porcelain'])
    if not success:
        print("❌ Error checking git status")
        return False, []
    
    if output:
        lines = output.split('\n')
        modified_files = []
        for line in lines:
            if line.strip():
                status = line[:2]
                filename = line[3:]
                modified_files.append({"status": status, "file": filename})
        return False, modified_files
    return True, []

def check_unpushed_commits():
    """Check if there are unpushed commits"""
    output, success = run_git_command(['git', 'log', 'origin/main..HEAD', '--oneline'])
    if not success:
        print("❌ Error checking unpushed commits")
        return False, []
    
    if output:
        commits = output.split('\n')
        return False, [commit for commit in commits if commit.strip()]
    return True, []

def check_current_branch():
    """Check what branch we're on"""
    output, success = run_git_command(['git', 'branch', '--show-current'])
    if success:
        return output
    return "unknown"

def get_last_commit_info():
    """Get info about the last commit"""
    output, success = run_git_command(['git', 'log', '-1', '--pretty=format:%H|%s|%an|%ad', '--date=short'])
    if success and output:
        parts = output.split('|')
        if len(parts) == 4:
            return {
                "hash": parts[0][:8],
                "message": parts[1],
                "author": parts[2], 
                "date": parts[3]
            }
    return None

def categorize_changes(modified_files):
    """Categorize changes by type"""
    categories = {
        "templates": [],
        "python": [],
        "static": [],
        "docs": [],
        "config": [],
        "other": []
    }
    
    for file_info in modified_files:
        filename = file_info["file"]
        if filename.startswith("templates/"):
            categories["templates"].append(file_info)
        elif filename.endswith(".py"):
            categories["python"].append(file_info)
        elif filename.startswith("static/"):
            categories["static"].append(file_info)
        elif filename.startswith("docs/") or filename.endswith(".md"):
            categories["docs"].append(file_info)
        elif filename in [".cursorrules", "requirements.txt", "config.py", "railway.toml"]:
            categories["config"].append(file_info)
        else:
            categories["other"].append(file_info)
    
    return categories

def print_file_changes(categories):
    """Print organized file changes"""
    status_symbols = {
        "M ": "📝",  # Modified
        " M": "📝",  # Modified
        "A ": "✨",  # Added
        " A": "✨",  # Added  
        "D ": "🗑️",  # Deleted
        " D": "🗑️",  # Deleted
        "??": "❓",  # Untracked
        "R ": "🔄",  # Renamed
        " R": "🔄",  # Renamed
    }
    
    for category, files in categories.items():
        if files:
            print(f"\n   📁 {category.title()}:")
            for file_info in files:
                symbol = status_symbols.get(file_info["status"], "📄")
                print(f"      {symbol} {file_info['file']}")

def main():
    print("🔍 Rally Deployment Status Check")
    print("=" * 50)
    
    # Check current branch
    current_branch = check_current_branch()
    print(f"📍 Current branch: {current_branch}")
    
    if current_branch != "main":
        print("⚠️  WARNING: You're not on the main branch!")
        print("   Railway deploys from 'main' branch")
    
    # Check for uncommitted changes
    print("\n📋 Checking for uncommitted changes...")
    clean_working_dir, modified_files = check_git_status()
    
    # Check for unpushed commits  
    print("📤 Checking for unpushed commits...")
    no_unpushed, unpushed_commits = check_unpushed_commits()
    
    # Get last commit info
    last_commit = get_last_commit_info()
    if last_commit:
        print(f"\n📝 Last commit: {last_commit['hash']} - {last_commit['message']}")
        print(f"   👤 {last_commit['author']} on {last_commit['date']}")
    
    print("\n" + "=" * 50)
    
    # Report status
    if clean_working_dir and no_unpushed:
        print("✅ DEPLOYMENT STATUS: IN SYNC")
        print("🚀 Railway should have your latest code!")
        if last_commit:
            print(f"   Last deployed: {last_commit['message']}")
    else:
        print("❌ DEPLOYMENT STATUS: OUT OF SYNC")
        print("🚨 Railway does NOT have your latest changes!")
        
        if not clean_working_dir:
            print(f"\n⚠️  {len(modified_files)} uncommitted file(s):")
            categories = categorize_changes(modified_files)
            print_file_changes(categories)
            
            print(f"\n📝 To commit these changes:")
            print(f"   git add .")
            print(f"   git commit -m \"Your commit message\"")
        
        if not no_unpushed:
            print(f"\n⚠️  {len(unpushed_commits)} unpushed commit(s):")
            for commit in unpushed_commits:
                print(f"   📌 {commit}")
            
            print(f"\n🚀 To deploy to Railway:")
            print(f"   git push origin main")
    
    print("\n" + "=" * 50)
    print("💡 TIP: Run this script before expecting changes on live site!")
    
    # Return exit code for scripts
    if clean_working_dir and no_unpushed:
        sys.exit(0)  # All good
    else:
        sys.exit(1)  # Issues found

if __name__ == "__main__":
    main() 