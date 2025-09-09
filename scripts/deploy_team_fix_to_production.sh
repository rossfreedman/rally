#!/bin/bash
"""
Deploy Team Association Fix to Production
========================================

This script uploads the necessary files to Railway production and runs the team association fix.
"""

echo "🚀 Deploying Team Association Fix to Production"
echo "=============================================="

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

echo "📁 Preparing files for upload..."

# Create a temporary directory for files to upload
TEMP_DIR=$(mktemp -d)
echo "   Temp directory: $TEMP_DIR"

# Copy the SSH script
cp scripts/ssh_fix_team_associations.py "$TEMP_DIR/"
echo "   ✅ Copied SSH script"

# Copy the players JSON file
cp data/leagues/APTA_CHICAGO/players.json "$TEMP_DIR/players.json"
echo "   ✅ Copied players data ($(wc -l < data/leagues/APTA_CHICAGO/players.json) lines)"

echo ""
echo "📤 Uploading files to Railway production..."

# Upload files to Railway production
cd "$TEMP_DIR"

# First, run a dry run to preview changes
echo "🔍 Running DRY RUN to preview changes..."
railway run --service rally-production "python3 - <<EOF
$(cat ssh_fix_team_associations.py)
EOF" -- --dry-run

echo ""
echo "⚠️  DRY RUN COMPLETE"
echo ""
read -p "Do you want to proceed with the actual fix? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔧 Running ACTUAL FIX..."
    railway run --service rally-production "python3 - <<EOF
$(cat ssh_fix_team_associations.py)
EOF" -- --execute
    
    echo ""
    echo "✅ Team association fix completed!"
else
    echo "❌ Fix cancelled by user"
fi

# Cleanup
cd - > /dev/null
rm -rf "$TEMP_DIR"
echo "🧹 Cleaned up temporary files"

echo ""
echo "🎉 Deployment complete!"
