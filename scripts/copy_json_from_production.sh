#!/bin/bash
"""
Copy JSON Files from Production to Local

This script copies CNSWPL JSON files from Railway production to local
so you can test fixes locally with production data.
"""

set -e  # Exit on error

echo "📋 Copying CNSWPL JSON files from Production to Local"
echo "=" * 80
echo

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install it first:"
    echo "   npm install -g @railway/cli"
    exit 1
fi

# Check if we're logged into Railway
if ! railway status &> /dev/null; then
    echo "❌ Not logged into Railway. Please run:"
    echo "   railway login"
    exit 1
fi

# Define the league
LEAGUE="CNSWPL"
PRODUCTION_PATH="/app/data/leagues/${LEAGUE}"
LOCAL_PATH="data/leagues/${LEAGUE}"

# Files to copy
FILES=(
    "series_stats.json"
    "match_history.json"
    "match_scores.json"
    "schedules.json"
    "players.json"
)

echo "📁 Production path: ${PRODUCTION_PATH}"
echo "📁 Local path: ${LOCAL_PATH}"
echo

# Create backup directory
BACKUP_DIR="${LOCAL_PATH}/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"
echo "📦 Created backup directory: ${BACKUP_DIR}"
echo

# Backup existing files
echo "💾 Backing up existing local files..."
for file in "${FILES[@]}"; do
    if [ -f "${LOCAL_PATH}/${file}" ]; then
        cp "${LOCAL_PATH}/${file}" "${BACKUP_DIR}/${file}"
        echo "   ✅ Backed up: ${file}"
    else
        echo "   ⚠️  File not found (will be created): ${file}"
    fi
done
echo

# Copy files from production
echo "📤 Copying files from production..."
COPIED=0
FAILED=0

for file in "${FILES[@]}"; do
    echo "   Copying ${file}..."
    
    # Use Railway CLI to download file
    if railway run --environment production --service rally-production cat "${PRODUCTION_PATH}/${file}" > "${LOCAL_PATH}/${file}" 2>/dev/null; then
        # Check if file was created and has content
        if [ -f "${LOCAL_PATH}/${file}" ] && [ -s "${LOCAL_PATH}/${file}" ]; then
            FILE_SIZE=$(wc -c < "${LOCAL_PATH}/${file}" | tr -d ' ')
            echo "      ✅ Copied ${file} (${FILE_SIZE} bytes)"
            COPIED=$((COPIED + 1))
        else
            echo "      ⚠️  File created but appears empty: ${file}"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "      ❌ Failed to copy: ${file}"
        FAILED=$((FAILED + 1))
    fi
done

echo
echo "=" * 80
echo "📊 Summary"
echo "=" * 80
echo "✅ Successfully copied: ${COPIED} files"
echo "❌ Failed: ${FAILED} files"
echo "💾 Backup location: ${BACKUP_DIR}"
echo

if [ ${COPIED} -gt 0 ]; then
    echo "✅ Files are ready for local testing!"
    echo
    echo "You can now run:"
    echo "   python3 scripts/fix_cnswpl_series_h_stats.py"
fi

if [ ${FAILED} -gt 0 ]; then
    echo "⚠️  Some files failed to copy. They may not exist on production."
    echo "   Check which files are actually available on production."
fi

