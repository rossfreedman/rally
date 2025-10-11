#!/usr/bin/env python3
"""
Setup Last Season Stats feature on staging environment.

This script helps deploy the Last Season Stats feature by:
1. Showing the SQL to create the table (can be run via Railway web console)
2. Preparing the import command
3. Committing and pushing code changes

Usage:
    python scripts/staging_setup_last_season_stats.py
"""

import os
import sys
import subprocess

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def check_git_status():
    """Check if there are uncommitted changes"""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def main():
    print_section("LAST SEASON STATS - STAGING DEPLOYMENT HELPER")
    
    # Check we're in the right directory
    if not os.path.exists("scripts/import_previous_season_matches.py"):
        print("❌ Error: This script must be run from the project root directory")
        print("   Current directory:", os.getcwd())
        return 1
    
    print("This helper will guide you through deploying the Last Season Stats feature to staging.")
    print("\nThe deployment requires 3 steps:")
    print("  1. Create database table on staging")
    print("  2. Import historical match data")
    print("  3. Deploy code changes via git")
    
    input("\nPress ENTER to continue...")
    
    # Step 1: Database table creation
    print_section("STEP 1: Create Database Table")
    
    print("You need to create the match_scores_previous_seasons table on staging.\n")
    print("OPTION A - Railway Web Console (Easiest):")
    print("  1. Go to: https://railway.app/")
    print("  2. Select: rally-staging → PostgreSQL")
    print("  3. Click: 'Query' tab")
    print("  4. Copy and paste the SQL below:")
    print("\n" + "-" * 80)
    
    # Read and display SQL
    sql_file = "scripts/create_match_scores_previous_seasons_table.sql"
    if os.path.exists(sql_file):
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        print(sql_content)
    else:
        print("❌ SQL file not found:", sql_file)
        return 1
    
    print("-" * 80 + "\n")
    print("OPTION B - Railway CLI:")
    print("  railway shell --service rally-staging")
    print("  psql $DATABASE_URL -f /app/scripts/create_match_scores_previous_seasons_table.sql")
    
    input("\n✅ Press ENTER once you've created the table on staging...")
    
    # Step 2: Import data
    print_section("STEP 2: Import Historical Match Data")
    
    print("Now you need to import the match history data into staging.\n")
    print("RECOMMENDED - Run import via Railway CLI:")
    print("\n  railway run --service rally-staging python scripts/import_previous_season_matches.py")
    print("\nThis will:")
    print("  - Connect to staging database")
    print("  - Import data from data/leagues/APTA_CHICAGO/match_history_2024_2025.json")
    print("  - Should import ~5000+ matches")
    
    print("\n" + "-" * 80)
    print("ALTERNATIVE - If Railway CLI isn't working:")
    print("  1. SSH into staging: railway shell --service rally-staging")
    print("  2. Run: cd /app && python scripts/import_previous_season_matches.py")
    print("-" * 80)
    
    input("\n✅ Press ENTER once you've imported the data...")
    
    # Step 3: Deploy code
    print_section("STEP 3: Deploy Code Changes")
    
    # Check git status
    changes = check_git_status()
    
    if changes:
        print("📝 You have uncommitted changes:")
        print(changes)
        print()
        
        response = input("Do you want to commit and push these changes to staging? (y/n): ")
        if response.lower() == 'y':
            # Commit changes
            print("\n📦 Committing changes...")
            subprocess.run(["git", "add", "."])
            
            commit_message = """feat | Add Last Season Stats feature

- Created match_scores_previous_seasons table for historical data
- Added get_last_season_stats, get_last_season_partner_analysis, get_last_season_court_analysis
- Added /mobile/last-season-stats/<player_id> route
- Created last_season_stats.html with Season Summary, Best Partnerships, Court Performance
- Updated player_detail.html to show Last Season Stats card
- Import script for historical match data from previous seasons"""
            
            subprocess.run(["git", "commit", "-m", commit_message])
            
            # Push to staging
            print("\n🚀 Pushing to staging branch...")
            result = subprocess.run(["git", "push", "origin", "staging"])
            
            if result.returncode == 0:
                print("\n✅ Successfully pushed to staging!")
            else:
                print("\n❌ Failed to push to staging")
                return 1
        else:
            print("\n⚠️  Skipping commit. Please commit manually before testing.")
    else:
        print("No uncommitted changes detected.")
        response = input("Push current staging branch? (y/n): ")
        if response.lower() == 'y':
            print("\n🚀 Pushing to staging...")
            subprocess.run(["git", "push", "origin", "staging"])
    
    # Summary
    print_section("DEPLOYMENT COMPLETE!")
    
    print("✅ Database table created")
    print("✅ Historical data imported")
    print("✅ Code deployed to staging")
    
    print("\n🧪 TEST THE FEATURE:")
    print("   https://rally-staging.up.railway.app/mobile/player-detail/<player_id>_team_<team_id>")
    print("\n   Example:")
    print("   https://rally-staging.up.railway.app/mobile/player-detail/nndz-WkNPd3liejlnUT09_team_59976")
    
    print("\n📋 VERIFY:")
    print("   - 'Last Season Stats' card appears on player detail page")
    print("   - Stats show correct data (matches, win rate, W-L record)")
    print("   - 'View More Detail' button navigates to detail page")
    print("   - Detail page shows Season Summary, Best Partnerships, Court Performance")
    print("   - Substitute detection works (chips for different series)")
    
    print("\n" + "=" * 80)
    print("  Need help? See: docs/DEPLOY_LAST_SEASON_STATS_STAGING.md")
    print("=" * 80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

