#!/bin/bash
"""
Copy JSON Files from Production via SSH

This script uses Railway SSH to copy files from production.
You'll need to be linked to production environment first.

Usage:
    bash scripts/copy_files_via_ssh.sh
"""

set -e

echo "📋 Copying JSON Files from Production via SSH"
echo "=============================================="
echo

# Check Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found"
    exit 1
fi

# Create backup directories
CNSWPL_BACKUP="data/leagues/CNSWPL/backup_$(date +%Y%m%d_%H%M%S)"
APTA_BACKUP="data/leagues/APTA_CHICAGO/backup_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$CNSWPL_BACKUP"
mkdir -p "$APTA_BACKUP"

echo "💾 Backing up existing files..."
[ -f "data/leagues/CNSWPL/series_stats.json" ] && cp "data/leagues/CNSWPL/series_stats.json" "$CNSWPL_BACKUP/" && echo "  ✅ Backed up CNSWPL/series_stats.json"
[ -f "data/leagues/CNSWPL/match_scores.json" ] && cp "data/leagues/CNSWPL/match_scores.json" "$CNSWPL_BACKUP/" && echo "  ✅ Backed up CNSWPL/match_scores.json"
[ -f "data/leagues/CNSWPL/players.json" ] && cp "data/leagues/CNSWPL/players.json" "$CNSWPL_BACKUP/" && echo "  ✅ Backed up CNSWPL/players.json"

[ -f "data/leagues/APTA_CHICAGO/series_stats.json" ] && cp "data/leagues/APTA_CHICAGO/series_stats.json" "$APTA_BACKUP/" && echo "  ✅ Backed up APTA_CHICAGO/series_stats.json"
[ -f "data/leagues/APTA_CHICAGO/match_scores.json" ] && cp "data/leagues/APTA_CHICAGO/match_scores.json" "$APTA_BACKUP/" && echo "  ✅ Backed up APTA_CHICAGO/match_scores.json"
[ -f "data/leagues/APTA_CHICAGO/players.json" ] && cp "data/leagues/APTA_CHICAGO/players.json" "$APTA_BACKUP/" && echo "  ✅ Backed up APTA_CHICAGO/players.json"

echo
echo "📤 Copying files from production..."
echo "⚠️  This will open an interactive SSH session"
echo "   Run these commands in the SSH session:"
echo
echo "CNSWPL files:"
echo "  cat /app/data/leagues/CNSWPL/series_stats.json > /tmp/series_stats.json"
echo "  cat /app/data/leagues/CNSWPL/match_history.json > /tmp/match_history.json"
echo "  cat /app/data/leagues/CNSWPL/match_scores.json > /tmp/match_scores.json"
echo "  cat /app/data/leagues/CNSWPL/schedules.json > /tmp/schedules.json"
echo "  cat /app/data/leagues/CNSWPL/players.json > /tmp/players.json"
echo
echo "APTA_CHICAGO files:"
echo "  cat /app/data/leagues/APTA_CHICAGO/series_stats.json > /tmp/apta_series_stats.json"
echo "  cat /app/data/leagues/APTA_CHICAGO/match_history.json > /tmp/apta_match_history.json"
echo "  cat /app/data/leagues/APTA_CHICAGO/match_scores.json > /tmp/apta_match_scores.json"
echo "  cat /app/data/leagues/APTA_CHICAGO/schedules.json > /tmp/apta_schedules.json"
echo "  cat /app/data/leagues/APTA_CHICAGO/players.json > /tmp/apta_players.json"
echo "  cat /app/data/leagues/APTA_CHICAGO/players_career_stats.json > /tmp/apta_players_career_stats.json"
echo "  cat /app/data/leagues/APTA_CHICAGO/player_history.json > /tmp/apta_player_history.json"
echo
echo "Then exit SSH and run this script again with --download flag"
echo

if [ "$1" != "--download" ]; then
    echo "Opening Railway SSH session..."
    railway ssh
    exit 0
fi

# Download files (this part would need to be done manually after copying to /tmp)
echo "To complete the copy, manually download files from /tmp on production"

