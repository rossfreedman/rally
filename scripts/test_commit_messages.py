#!/usr/bin/env python3
"""
Test Commit Message Generation
=============================

This script demonstrates the improved commit message generation
by showing examples of different types of changes.
"""

import sys
import os
import subprocess
from datetime import datetime

# Add the deployment directory to the path so we can import the functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'deployment'))

from deploy_staging import (
    analyze_file_changes, 
    detect_critical_changes, 
    generate_descriptive_commit_message
)

def test_commit_message_generation():
    """Test the commit message generation with current changes"""
    print("🧪 Testing Commit Message Generation")
    print("=" * 50)
    
    # Test file change analysis
    print("\n📊 File Change Analysis:")
    change_analysis = analyze_file_changes()
    print(f"  Additions: {change_analysis['additions']}")
    print(f"  Modifications: {change_analysis['modifications']}")
    print(f"  Deletions: {change_analysis['deletions']}")
    
    # Test critical changes detection
    print("\n🚨 Critical Changes Detection:")
    critical_changes = detect_critical_changes()
    if critical_changes:
        print(f"  Critical changes: {', '.join(critical_changes)}")
    else:
        print("  No critical changes detected")
    
    # Test full commit message generation
    print("\n📝 Generated Commit Message:")
    commit_message = generate_descriptive_commit_message("staging")
    print(f"  '{commit_message}'")
    print(f"  Length: {len(commit_message)} characters")
    
    # Show git status for context
    print("\n📋 Current Git Status:")
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print("  Changed files:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"    {line}")
        else:
            print("  No changes detected")
    except Exception as e:
        print(f"  Error getting git status: {e}")

def show_example_messages():
    """Show examples of different types of commit messages"""
    print("\n📚 Example Commit Messages")
    print("=" * 50)
    
    examples = [
        {
            "scenario": "Auth and mobile updates",
            "description": "Authentication system improvements and mobile UI updates",
            "expected": "Deploy to staging from feature/auth: auth, mobile updates [+2, ~5] - routes(3), templates(2), static(2) - 2024-01-15 14:30"
        },
        {
            "scenario": "Database schema changes",
            "description": "Database migration and schema updates",
            "expected": "Deploy to staging from main: schema, database updates [+1, ~3] - DB(2), scripts(1) - 2024-01-15 14:30"
        },
        {
            "scenario": "ETL and API improvements",
            "description": "Data processing and API endpoint enhancements",
            "expected": "Deploy to staging from feature/etl: ETL, API updates [+4, ~2] - services(3), routes(2), scripts(1) - 2024-01-15 14:30"
        },
        {
            "scenario": "Security fixes",
            "description": "Security-related updates and fixes",
            "expected": "Deploy to staging from hotfix/security: security updates [+1, ~2] - routes(1), services(1), config(1) - 2024-01-15 14:30"
        },
        {
            "scenario": "Frontend UI changes",
            "description": "User interface improvements and styling updates",
            "expected": "Deploy to staging from feature/ui: frontend updates [+3, ~1] - UI(4) - 2024-01-15 14:30"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['scenario']}")
        print(f"   Description: {example['description']}")
        print(f"   Expected: {example['expected']}")

if __name__ == "__main__":
    print("🚀 Commit Message Generation Test")
    print(f"📅 {datetime.now()}")
    
    test_commit_message_generation()
    show_example_messages()
    
    print("\n✅ Test completed!") 