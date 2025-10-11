#!/bin/bash
#
# Import previous season data to staging via Railway SSH
# This runs the import directly on the staging server for better performance
#

set -e

echo "========================================================================"
echo "IMPORTING PREVIOUS SEASON DATA TO STAGING VIA SSH"
echo "========================================================================"
echo ""
echo "This will:"
echo "  1. Ensure the import script and data file are in the git repo"
echo "  2. SSH into Railway staging environment"
echo "  3. Run the import script directly on the server"
echo ""

# Check files exist
if [ ! -f "scripts/import_previous_season_matches.py" ]; then
    echo "❌ Error: scripts/import_previous_season_matches.py not found"
    exit 1
fi

if [ ! -f "data/leagues/APTA_CHICAGO/match_history_2024_2025.json" ]; then
    echo "❌ Error: data/leagues/APTA_CHICAGO/match_history_2024_2025.json not found"
    exit 1
fi

echo "✅ Import script and data file found locally"
echo ""

# Check if files are committed
if ! git ls-files --error-unmatch scripts/import_previous_season_matches.py > /dev/null 2>&1; then
    echo "⚠️  Warning: scripts/import_previous_season_matches.py is not tracked by git"
    echo "   Adding it now..."
    git add scripts/import_previous_season_matches.py
fi

if ! git ls-files --error-unmatch data/leagues/APTA_CHICAGO/match_history_2024_2025.json > /dev/null 2>&1; then
    echo "⚠️  Warning: data/leagues/APTA_CHICAGO/match_history_2024_2025.json is not tracked by git"
    echo "   Adding it now..."
    git add data/leagues/APTA_CHICAGO/match_history_2024_2025.json
fi

# Check for uncommitted changes
if [[ -n $(git status -s | grep -E "(import_previous_season_matches|match_history_2024_2025)") ]]; then
    echo ""
    echo "📝 Files need to be committed to be available on staging:"
    git status -s | grep -E "(import_previous_season_matches|match_history_2024_2025)"
    echo ""
    read -p "Commit these files? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git commit -m "feat | Add previous season import script and data for staging deployment"
        echo "✅ Files committed"
    fi
    
    echo ""
    read -p "Push to staging branch? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin staging
        echo "✅ Pushed to staging - waiting 10 seconds for Railway to deploy..."
        sleep 10
    else
        echo "⚠️  You'll need to push to staging before the files are available on the server"
        exit 1
    fi
fi

echo ""
echo "========================================================================"
echo "RUNNING IMPORT ON STAGING"
echo "========================================================================"
echo ""
echo "Connecting to Railway staging and running import..."
echo ""

# Run the import via Railway CLI
railway run --service rally-staging python scripts/import_previous_season_matches.py

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "✅ IMPORT COMPLETE!"
    echo "========================================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Verify data: railway run --service rally-staging psql -c \"SELECT COUNT(*) FROM match_scores_previous_seasons;\""
    echo "  2. Test the feature at: https://rally-staging.up.railway.app"
    echo ""
else
    echo ""
    echo "❌ Import failed. Check the error messages above."
    exit 1
fi

