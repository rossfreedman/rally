#!/bin/bash
#
# Deploy Last Season Stats feature to staging
# This script:
# 1. Creates the match_scores_previous_seasons table on staging database
# 2. Uploads the import script and data file to staging
# 3. Runs the import on staging
# 4. Deploys code changes to staging via git
#

set -e  # Exit on error

echo "========================================================================"
echo "DEPLOYING LAST SEASON STATS FEATURE TO STAGING"
echo "========================================================================"

# Configuration
RAILWAY_SERVICE="rally-staging"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "Step 1: Creating match_scores_previous_seasons table on staging..."
echo "------------------------------------------------------------------------"

# Create table via Railway CLI
echo "Executing SQL script on staging database..."
railway run --service $RAILWAY_SERVICE psql -f "$SCRIPT_DIR/create_match_scores_previous_seasons_table.sql"

if [ $? -eq 0 ]; then
    echo "✅ Table created successfully!"
else
    echo "❌ Failed to create table. Exiting."
    exit 1
fi

echo ""
echo "Step 2: Uploading data and import script to staging..."
echo "------------------------------------------------------------------------"

# Copy files to staging using Railway's filesystem
# Note: We'll need to use Railway's shell to run the import
echo "Files to upload:"
echo "  - scripts/import_previous_season_matches.py"
echo "  - data/leagues/APTA_CHICAGO/match_history_2024_2025.json"

echo ""
echo "Step 3: Running import on staging..."
echo "------------------------------------------------------------------------"
echo "⚠️  MANUAL STEP REQUIRED:"
echo ""
echo "To import the data, SSH into staging and run:"
echo ""
echo "  railway shell --service $RAILWAY_SERVICE"
echo "  cd /app"
echo "  python scripts/import_previous_season_matches.py"
echo ""
echo "Or use Railway run:"
echo ""
echo "  railway run --service $RAILWAY_SERVICE python scripts/import_previous_season_matches.py"
echo ""

read -p "Press ENTER once you've completed the import, or Ctrl+C to exit..."

echo ""
echo "Step 4: Deploying code changes to staging via git..."
echo "------------------------------------------------------------------------"

cd "$PROJECT_ROOT"

# Check git status
if [[ -n $(git status -s) ]]; then
    echo "⚠️  You have uncommitted changes:"
    git status -s
    echo ""
    read -p "Do you want to commit and push these changes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "feat | Add Last Season Stats feature with match_scores_previous_seasons table"
        git push origin staging
        echo "✅ Changes committed and pushed to staging branch!"
    else
        echo "❌ Deployment cancelled. Please commit changes manually."
        exit 1
    fi
else
    echo "No uncommitted changes detected."
    read -p "Push current staging branch to trigger deployment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin staging
        echo "✅ Pushed to staging branch!"
    fi
fi

echo ""
echo "========================================================================"
echo "DEPLOYMENT SUMMARY"
echo "========================================================================"
echo "✅ Table created on staging database"
echo "⏳ Data import - verify manually"
echo "✅ Code deployed to staging via git push"
echo ""
echo "Next steps:"
echo "1. Verify import completed successfully on staging"
echo "2. Test the feature at: https://rally-staging.up.railway.app"
echo "3. Check any player detail page for 'Last Season Stats' card"
echo "========================================================================"

