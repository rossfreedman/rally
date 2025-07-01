#!/bin/bash

# Automated ETL Runner for Railway
# Usage: ./scripts/run_etl.sh [railway_run|ssh] [--full-import]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Parse arguments
METHOD="railway_run"
FULL_IMPORT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        railway_run|ssh)
            METHOD="$1"
            shift
            ;;
        --full-import)
            FULL_IMPORT="--full-import"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [railway_run|ssh] [--full-import]"
            echo ""
            echo "Methods:"
            echo "  railway_run  - Run locally with Railway env vars (default)"
            echo "  ssh         - Run on Railway servers via SSH (faster)"
            echo ""
            echo "Options:"
            echo "  --full-import  - Run full import instead of incremental"
            echo "  --help         - Show this help message"
            exit 0
            ;;
        *)
            error "Unknown argument: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

log "🤖 Starting automated ETL process..."
log "📊 Method: $METHOD"
log "🎯 Full import: ${FULL_IMPORT:-false}"

# Step 1: Check Railway connection
log "🔍 Checking Railway connection..."
if ! railway status > /dev/null 2>&1; then
    error "Railway CLI not connected. Please run 'railway login' first."
    exit 1
fi

# Show Railway status
log "✅ Railway CLI connected"
railway status

# Step 2: Test database connection
log "🔍 Testing Railway database connection..."
if ! railway run python chronjobs/railway_cron_etl.py --test-only; then
    error "Database connection test failed"
    exit 1
fi

success "Database connection test passed"

# Step 3: Run ETL
start_time=$(date +%s)

log "🚀 Starting ETL process..."

if [ "$METHOD" = "ssh" ]; then
    log "🌐 Running ETL on Railway servers via SSH..."
    
    # Create temporary script for SSH
    SSH_SCRIPT="
    set -e
    echo '🔗 Connected to Railway server'
    echo '📁 Current directory: \$(pwd)'
    echo '🐍 Python version: \$(python --version)'
    echo '🚀 Starting ETL process...'
    python chronjobs/railway_cron_etl.py $FULL_IMPORT
    echo '✅ ETL process completed'
    "
    
    if railway ssh -c "$SSH_SCRIPT"; then
        success "ETL via SSH completed successfully!"
        ETL_SUCCESS=true
    else
        error "ETL via SSH failed"
        ETL_SUCCESS=false
    fi
    
elif [ "$METHOD" = "railway_run" ]; then
    log "💻 Running ETL locally with Railway environment..."
    
    if railway run python chronjobs/railway_cron_etl.py $FULL_IMPORT; then
        success "ETL via railway run completed successfully!"
        ETL_SUCCESS=true
    else
        error "ETL via railway run failed"
        ETL_SUCCESS=false
    fi
else
    error "Unknown method: $METHOD"
    exit 1
fi

# Step 4: Report results
end_time=$(date +%s)
duration=$((end_time - start_time))
duration_formatted=$(printf '%02d:%02d:%02d' $((duration/3600)) $((duration%3600/60)) $((duration%60)))

if [ "$ETL_SUCCESS" = true ]; then
    success "🎊 Automated ETL completed successfully in $duration_formatted"
    log "🎉 ETL process finished!"
    exit 0
else
    error "💥 Automated ETL failed after $duration_formatted"
    exit 1
fi 