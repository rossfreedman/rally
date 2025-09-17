#!/bin/bash

# APTA Import Wrapper Script
# This script provides a simple interface to run the APTA master import process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"
}

# Function to show usage
show_usage() {
    echo "APTA Import Wrapper Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run          Show what would be done without executing"
    echo "  --skip-validation  Skip final validation step"
    echo "  --league LEAGUE    League to process (default: APTA_CHICAGO)"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run full import"
    echo "  $0 --dry-run                         # Show what would be done"
    echo "  $0 --skip-validation                 # Skip validation step"
    echo "  $0 --league APTA_CHICAGO --dry-run   # Dry run for specific league"
    echo ""
}

# Parse command line arguments
DRY_RUN=""
SKIP_VALIDATION=""
LEAGUE="APTA_CHICAGO"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION="--skip-validation"
            shift
            ;;
        --league)
            LEAGUE="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Change to project root directory
cd "$(dirname "$0")/.."

print_status "Starting APTA Import Process"
print_status "League: $LEAGUE"
print_status "Dry Run: $([ -n "$DRY_RUN" ] && echo "Yes" || echo "No")"
print_status "Skip Validation: $([ -n "$SKIP_VALIDATION" ] && echo "Yes" || echo "No")"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    exit 1
fi

# Check if the master script exists
if [ ! -f "scripts/apta_master_import.py" ]; then
    print_error "Master import script not found: scripts/apta_master_import.py"
    exit 1
fi

# Run the master import script
print_status "Executing master import script..."
echo ""

if python3 scripts/apta_master_import.py --league "$LEAGUE" $DRY_RUN $SKIP_VALIDATION; then
    print_success "APTA Import Process completed successfully!"
    exit 0
else
    print_error "APTA Import Process failed!"
    exit 1
fi
