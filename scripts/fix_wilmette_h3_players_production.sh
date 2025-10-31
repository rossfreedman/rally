#!/bin/bash
# Script to fix Wilmette H(3) player assignments in production
# Run this via Railway SSH after deploying code changes

echo "=================================================================================="
echo "Fixing Wilmette H(3) Player Assignments in Production"
echo "=================================================================================="
echo ""
echo "This script will:"
echo "  1. Create missing player records for Wilmette H(3)"
echo "  2. Reassign players who are on wrong teams to correct team_id (60050)"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "Running fix script..."
python3 scripts/fix_wilmette_h3_players.py

echo ""
echo "=================================================================================="
echo "✅ Player assignment fix complete!"
echo "=================================================================================="
echo ""
echo "Next steps:"
echo "  1. Re-run CNSWPL scraper to capture 10/20 match with fixes"
echo "  2. Import match scores to update database"
echo ""

