#!/bin/bash
# Populate starting_pti on Railway staging environment via SSH
# This script should be run in an interactive terminal

set -e

echo "=========================================="
echo "Populate starting_pti on Railway Staging"
echo "=========================================="
echo ""

# Check if we're in the rally directory
if [ ! -f "scripts/populate_starting_pti.py" ]; then
    echo "❌ Error: Must run from rally project root directory"
    exit 1
fi

echo "🔗 Linking to Railway staging environment..."
echo "   (You may need to select: rossfreedman's Projects > rally > staging)"
echo ""

# Link to project (interactive - user must select)
railway link

echo ""
echo "✅ Linked to Railway project"
echo ""
echo "🚀 Opening Railway shell to run populate script..."
echo "   Once in the shell, the populate script will run automatically"
echo ""
echo "---"
echo ""

# Connect to Railway shell and run the populate script
railway shell -c "python scripts/populate_starting_pti.py"

echo ""
echo "=========================================="
echo "✅ Population Complete!"
echo "=========================================="
echo ""
echo "Next step: Verify on staging analyze-me page"

