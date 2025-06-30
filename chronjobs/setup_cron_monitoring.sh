#!/bin/bash

# Setup Cron Monitoring for Rally Database Integrity
# This script sets up automated daily monitoring of database integrity

set -e

# Get the absolute path to the Rally project
RALLY_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$RALLY_PATH/logs"
CRON_SCRIPT="$RALLY_PATH/scripts/daily_integrity_monitor.py"

echo "🔧 SETTING UP AUTOMATED DATABASE MONITORING"
echo "=============================================="
echo "Rally path: $RALLY_PATH"
echo "Log directory: $LOG_DIR"
echo "Monitor script: $CRON_SCRIPT"
echo

# Create logs directory if it doesn't exist
if [ ! -d "$LOG_DIR" ]; then
    echo "📁 Creating logs directory..."
    mkdir -p "$LOG_DIR"
    echo "   ✅ Created: $LOG_DIR"
fi

# Check if monitor script exists
if [ ! -f "$CRON_SCRIPT" ]; then
    echo "❌ Error: Monitor script not found at $CRON_SCRIPT"
    exit 1
fi

# Make the script executable
echo "🔧 Making monitor script executable..."
chmod +x "$CRON_SCRIPT"
echo "   ✅ Script is now executable"

# Create a wrapper script for cron (handles environment variables)
WRAPPER_SCRIPT="$RALLY_PATH/scripts/cron_wrapper.sh"
echo "📝 Creating cron wrapper script..."

cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
# Cron wrapper for Rally integrity monitor
# This ensures proper environment setup for cron execution

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="$PYTHONPATH"

# Get the absolute path to the Rally project
RALLY_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Change to the Rally directory
cd "$RALLY_PATH"

# Run the integrity monitor
python3 scripts/daily_integrity_monitor.py
EOF

chmod +x "$WRAPPER_SCRIPT"
echo "   ✅ Created wrapper script: $WRAPPER_SCRIPT"

# Test the monitor script
echo "🧪 Testing monitor script..."
if python3 "$CRON_SCRIPT"; then
    echo "   ✅ Monitor script test successful"
else
    echo "   ❌ Monitor script test failed"
    exit 1
fi

# Show current crontab
echo "📋 Current crontab entries:"
crontab -l 2>/dev/null || echo "   (no crontab entries found)"

echo
echo "🕐 CRON SETUP OPTIONS:"
echo "======================="
echo "Choose how you want to schedule the monitoring:"
echo
echo "1. Daily at 8:00 AM"
echo "2. Daily at 6:00 AM" 
echo "3. Twice daily (8:00 AM and 8:00 PM)"
echo "4. Custom schedule"
echo "5. Show commands only (don't install)"
echo

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        CRON_SCHEDULE="0 8 * * *"
        CRON_DESCRIPTION="Daily at 8:00 AM"
        ;;
    2)
        CRON_SCHEDULE="0 6 * * *"
        CRON_DESCRIPTION="Daily at 6:00 AM"
        ;;
    3)
        CRON_SCHEDULE="0 8,20 * * *"
        CRON_DESCRIPTION="Twice daily (8:00 AM and 8:00 PM)"
        ;;
    4)
        read -p "Enter custom cron schedule (e.g., '0 9 * * 1-5' for weekdays at 9 AM): " CRON_SCHEDULE
        CRON_DESCRIPTION="Custom schedule: $CRON_SCHEDULE"
        ;;
    5)
        echo
        echo "📋 MANUAL CRON SETUP COMMANDS:"
        echo "==============================="
        echo "To set up monitoring manually, run:"
        echo
        echo "# Add to crontab (daily at 8 AM):"
        echo "echo '0 8 * * * $WRAPPER_SCRIPT >> $LOG_DIR/cron.log 2>&1' | crontab -"
        echo
        echo "# Or edit crontab manually:"
        echo "crontab -e"
        echo
        echo "# Add this line:"
        echo "0 8 * * * $WRAPPER_SCRIPT >> $LOG_DIR/cron.log 2>&1"
        echo
        echo "# View logs:"
        echo "tail -f $LOG_DIR/integrity_monitor.log"
        echo "tail -f $LOG_DIR/cron.log"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

# Install the cron job
echo
echo "📅 Installing cron job: $CRON_DESCRIPTION"
echo "   Schedule: $CRON_SCHEDULE"
echo "   Command: $WRAPPER_SCRIPT"
echo "   Logs: $LOG_DIR/cron.log"
echo

# Create the cron entry
CRON_ENTRY="$CRON_SCHEDULE $WRAPPER_SCRIPT >> $LOG_DIR/cron.log 2>&1"

# Add to crontab
(crontab -l 2>/dev/null; echo "# Rally Database Integrity Monitor - $CRON_DESCRIPTION"; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job installed successfully!"
echo
echo "📋 Updated crontab:"
crontab -l | tail -2

echo
echo "🎉 MONITORING SETUP COMPLETE!"
echo "=============================="
echo "✅ Database integrity monitoring is now automated"
echo "✅ Monitor runs: $CRON_DESCRIPTION"
echo "✅ Logs saved to: $LOG_DIR/integrity_monitor.log"
echo "✅ Cron logs saved to: $LOG_DIR/cron.log"
echo
echo "📊 USEFUL COMMANDS:"
echo "==================="
echo "# View integrity monitor logs:"
echo "tail -f $LOG_DIR/integrity_monitor.log"
echo
echo "# View cron execution logs:"
echo "tail -f $LOG_DIR/cron.log"
echo
echo "# Run monitor manually:"
echo "cd $RALLY_PATH && python3 scripts/daily_integrity_monitor.py"
echo
echo "# Remove cron job:"
echo "crontab -e  # then delete the Rally lines"
echo
echo "# Test that cron job will work:"
echo "$WRAPPER_SCRIPT" 