#!/bin/bash
# Script to move match_scores.json from wrong location to volume location

echo "======================================================================"
echo "Moving match_scores.json to Correct Volume Location"
echo "======================================================================"
echo ""
echo "This script will:"
echo "1. Create the correct directory structure"
echo "2. Move the file from /data/CNSWPL/ to /app/data/leagues/CNSWPL/"
echo "3. Verify the move was successful"
echo ""
echo "⚠️  IMPORTANT: Update CNSWPL_CRON_VARIABLE in Railway first!"
echo "   Current: /data"
echo "   New:     /app/data/leagues"
echo ""
read -p "Press Enter to continue or Ctrl+C to exit..."

echo ""
echo "Run these commands in your Railway SSH session:"
echo ""

echo "# 1. Verify the file exists at wrong location"
echo "ls -lh /data/CNSWPL/match_scores.json"
echo ""

echo "# 2. Create the correct directory (if it doesn't exist)"
echo "mkdir -p /app/data/leagues/CNSWPL"
echo ""

echo "# 3. Move the file to the correct location"
echo "mv /data/CNSWPL/match_scores.json /app/data/leagues/CNSWPL/match_scores.json"
echo ""

echo "# 4. Verify the file is now at the correct location"
echo "ls -lh /app/data/leagues/CNSWPL/match_scores.json"
echo ""

echo "# 5. Verify path resolution works correctly"
echo "python3 -c \"from data.etl.utils.league_directory_manager import get_league_file_path; print('Expected path:', get_league_file_path('cnswpl', 'match_scores.json'))\""
echo ""

echo "# 6. Check if any other files need to be moved"
echo "ls -la /data/CNSWPL/*.json 2>/dev/null || echo 'No other files at wrong location'"
echo ""

echo "======================================================================"
echo "After Moving:"
echo "======================================================================"
echo "1. Update CNSWPL_CRON_VARIABLE in Railway: /app/data/leagues"
echo "2. Run the import script to verify it can find the file:"
echo "   python3 data/etl/import/import_match_scores.py CNSWPL"
echo ""


