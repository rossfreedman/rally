#!/bin/bash
# Diagnostic script to find why match_scores.json is missing

echo "======================================================================"
echo "Diagnosing Missing match_scores.json"
echo "======================================================================"
echo ""
echo "Run these commands in your Railway SSH session:"
echo ""

echo "1. Check if CNSWPL_CRON_VARIABLE is set:"
echo "   echo \$CNSWPL_CRON_VARIABLE"
echo ""

echo "2. Check what path the scraper would use:"
echo "   python3 -c \"from data.etl.utils.league_directory_manager import get_league_file_path; print(get_league_file_path('cnswpl', 'match_scores.json'))\""
echo ""

echo "3. Check if .tmp file exists (failed atomic write):"
echo "   find /app/data/leagues/CNSWPL -name '*.tmp' -o -name 'match_scores.json.tmp'"
echo "   ls -la /app/data/leagues/CNSWPL/match_scores.json.tmp 2>/dev/null || echo 'No .tmp file found'"
echo ""

echo "4. Check for temp_match_scores directory (series temp files):"
echo "   ls -la /app/data/leagues/CNSWPL/temp_match_scores/ 2>/dev/null || echo 'No temp directory found'"
echo ""

echo "5. Check for any match_scores files with different names:"
echo "   find /app/data/leagues/CNSWPL -name '*match*score*' -o -name '*match*scores*'"
echo ""

echo "6. Check file permissions on directory:"
echo "   ls -ld /app/data/leagues/CNSWPL/"
echo "   touch /app/data/leagues/CNSWPL/.test_write && rm /app/data/leagues/CNSWPL/.test_write && echo 'Directory is writable' || echo 'Directory is NOT writable'"
echo ""

echo "7. Check recent scraper logs for save messages:"
echo "   # Look for these messages in Railway logs:"
echo "   # - '📁 Results saved to: ...'"
echo "   # - '💾 Saved final matches file: ...'"
echo "   # - Any error messages about file writing"
echo ""

echo "8. Check if the scraper actually completed the save (look at variable 'new_matches'):"
echo "   # The logs show 'New matches added: 4,632' but we need to verify"
echo "   # if the file write actually succeeded"
echo ""

echo "======================================================================"
echo "Based on your terminal output:"
echo "======================================================================"
echo "✅ Volume is accessible at /app/data/leagues/CNSWPL/"
echo "✅ Other JSON files exist (players.json, match_history, etc.)"
echo "❌ match_scores.json is MISSING"
echo ""
echo "Most likely causes:"
echo "1. Save operation failed silently (check for .tmp files)"
echo "2. File was saved to wrong location (check scraper logs for 'Results saved to:')"
echo "3. Permission issue (check directory write permissions)"
echo "4. Exception during file write (check full scraper logs)"
echo ""


