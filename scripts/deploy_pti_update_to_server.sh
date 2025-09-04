#!/bin/bash

# Deploy PTI Update Script to Production Server
# This script uploads the necessary files to run the PTI update on the production server

echo "🚀 Deploying PTI Update Script to Production Server"

# Configuration
SERVER_HOST="your-production-server.com"  # Update with your server details
SERVER_USER="your-username"              # Update with your username
SERVER_PATH="/home/your-username/pti_update"  # Update with your desired path

# Files to upload
REFERENCE_FILE="data/leagues/APTA_CHICAGO/players_reference.json"
UPDATE_SCRIPT="scripts/ssh_production_pti_update.py"

echo "📁 Uploading files to production server..."

# Create directory on server
ssh $SERVER_USER@$SERVER_HOST "mkdir -p $SERVER_PATH"

# Upload reference file
echo "📤 Uploading players_reference.json..."
scp $REFERENCE_FILE $SERVER_USER@$SERVER_HOST:$SERVER_PATH/players_reference.json

# Upload update script
echo "📤 Uploading PTI update script..."
scp $UPDATE_SCRIPT $SERVER_USER@$SERVER_HOST:$SERVER_PATH/ssh_production_pti_update.py

# Make script executable
ssh $SERVER_USER@$SERVER_HOST "chmod +x $SERVER_PATH/ssh_production_pti_update.py"

echo "✅ Deployment complete!"
echo ""
echo "🔧 To run the update on the production server:"
echo "1. SSH into the server:"
echo "   ssh $SERVER_USER@$SERVER_HOST"
echo ""
echo "2. Navigate to the script directory:"
echo "   cd $SERVER_PATH"
echo ""
echo "3. Run dry-run first:"
echo "   python3 ssh_production_pti_update.py --dry-run"
echo ""
echo "4. If dry-run looks good, execute:"
echo "   python3 ssh_production_pti_update.py --execute"
echo ""
echo "⚠️  Make sure to install required Python packages on the server:"
echo "   pip3 install psycopg2-binary"
