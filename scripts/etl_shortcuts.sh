#!/bin/bash

# ETL Shortcuts and Aliases
# Source this file to add convenient ETL commands to your shell
# Usage: source scripts/etl_shortcuts.sh

# Colors
alias log_info='echo -e "\033[0;34m[INFO]\033[0m"'
alias log_success='echo -e "\033[0;32m[SUCCESS]\033[0m"'
alias log_error='echo -e "\033[0;31m[ERROR]\033[0m"'

# Basic ETL aliases
alias etl='python scripts/run_etl_on_railway.py'
alias etl-test='railway run python chronjobs/railway_cron_etl.py --test-only'
alias etl-local='railway run python chronjobs/railway_cron_etl.py'
alias etl-ssh='python scripts/run_etl_on_railway.py --method ssh'
alias etl-full='python scripts/run_etl_on_railway.py --full-import'
alias etl-full-ssh='python scripts/run_etl_on_railway.py --method ssh --full-import'

# Railway shortcuts
alias r-status='railway status'
alias r-logs='railway logs --follow'
alias r-ssh='railway ssh'
alias r-run='railway run'

# ETL monitoring aliases
alias etl-logs='railway logs --follow | grep -E "(ETL|Import|Error|Success)"'

# Quick functions
etl_quick() {
    log_info "🚀 Running quick ETL (railway_run method)..."
    python scripts/run_etl_on_railway.py
}

etl_fast() {
    log_info "⚡ Running fast ETL (SSH method)..."
    python scripts/run_etl_on_railway.py --method ssh
}

etl_full_fast() {
    log_info "🔥 Running full ETL on Railway servers..."
    python scripts/run_etl_on_railway.py --method ssh --full-import
}

etl_status() {
    log_info "📊 Checking ETL system status..."
    echo "Railway Status:"
    railway status
    echo ""
    echo "Database Connection Test:"
    railway run python chronjobs/railway_cron_etl.py --test-only
}

etl_help() {
    echo "🤖 ETL Automation Commands:"
    echo ""
    echo "Quick Commands:"
    echo "  etl              - Run ETL with default settings"
    echo "  etl-test         - Test database connection only"
    echo "  etl-quick        - Run ETL locally with Railway env vars"
    echo "  etl-fast         - Run ETL on Railway servers (SSH)"
    echo "  etl-full-fast    - Run full ETL on Railway servers"
    echo ""
    echo "Detailed Commands:"
    echo "  etl-local        - Run ETL locally with Railway environment"
    echo "  etl-ssh          - Run ETL on Railway servers via SSH"
    echo "  etl-full         - Run full import locally"
    echo "  etl-full-ssh     - Run full import on Railway servers"
    echo ""
    echo "Monitoring:"
    echo "  etl-status       - Check Railway connection and database"
    echo "  etl-logs         - Stream Railway logs with ETL filtering"
    echo "  r-logs           - Stream all Railway logs"
    echo ""
    echo "Railway Shortcuts:"
    echo "  r-status         - Show Railway project status"
    echo "  r-ssh            - SSH into Railway servers"
    echo "  r-run            - Run command with Railway environment"
    echo ""
    echo "Examples:"
    echo "  etl-fast                    # Fastest option (Railway SSH)"
    echo "  etl-full-fast              # Full import on Railway"
    echo "  etl --method ssh           # ETL via SSH with options"
    echo ""
}

# Show help on source
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    log_success "🎯 ETL shortcuts loaded! Type 'etl_help' for available commands."
fi 