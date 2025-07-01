# ETL Automation Guide

This guide covers all the automated ways to run ETL processes locally while leveraging Railway's infrastructure for optimal performance.

## 🚀 Quick Start (TL;DR)

**Fastest and Most Reliable Option:**
```bash
# One-time setup
source scripts/etl_shortcuts.sh

# Run ETL on Railway servers (fastest)
etl-fast
```

## 📋 Available Automation Methods

### **Method 1: Python Automation Script (Recommended)**

**File:** `scripts/run_etl_on_railway.py`

**Basic Usage:**
```bash
# Default: Run locally with Railway env vars
python scripts/run_etl_on_railway.py

# Run on Railway servers via SSH (fastest)
python scripts/run_etl_on_railway.py --method ssh

# Full import on Railway servers
python scripts/run_etl_on_railway.py --method ssh --full-import

# Test connection only
python scripts/run_etl_on_railway.py --test-only
```

**Features:**
- ✅ Automatic Railway connection checking
- ✅ Database connection testing
- ✅ Real-time output streaming
- ✅ Error handling and reporting
- ✅ Duration tracking
- ✅ Support for SSH and local execution

### **Method 2: Bash Script**

**File:** `scripts/run_etl.sh`

**Basic Usage:**
```bash
# Default: Run locally with Railway env vars
./scripts/run_etl.sh

# Run on Railway servers via SSH (fastest)
./scripts/run_etl.sh ssh

# Full import on Railway servers
./scripts/run_etl.sh ssh --full-import

# Help
./scripts/run_etl.sh --help
```

**Features:**
- ✅ Colorized output
- ✅ Automatic validation
- ✅ Simple command-line interface
- ✅ Duration formatting (HH:MM:SS)

### **Method 3: Convenient Aliases**

**File:** `scripts/etl_shortcuts.sh`

**Setup (one-time):**
```bash
# Load shortcuts into your shell
source scripts/etl_shortcuts.sh

# Add to your ~/.bashrc or ~/.zshrc for permanent use
echo "source $(pwd)/scripts/etl_shortcuts.sh" >> ~/.bashrc
```

**Usage:**
```bash
# Quick commands
etl-fast         # Fastest option (Railway SSH)
etl-full-fast    # Full import on Railway
etl-test         # Test connection only
etl-status       # Check system status

# Monitoring
etl-logs         # Stream ETL-specific logs
r-logs           # Stream all Railway logs

# Help
etl_help         # Show all available commands
```

## 🎯 Execution Methods Comparison

| Method | Speed | Location | Connection | Best For |
|--------|-------|----------|------------|----------|
| `railway_run` | Medium | Local | Railway env vars | Development, Testing |
| `ssh` | **Fastest** | Railway servers | Internal Railway | **Production, Large datasets** |
| `cron` | Fastest | Railway servers | Internal Railway | Scheduled runs |

## 🔧 Complete Usage Examples

### **Standard ETL Run (Recommended)**
```bash
# Most reliable for production
python scripts/run_etl_on_railway.py --method ssh
```

### **Full Import (Heavy Operation)**
```bash
# For complete data refresh
python scripts/run_etl_on_railway.py --method ssh --full-import
```

### **Quick Test**
```bash
# Verify everything is working
python scripts/run_etl_on_railway.py --test-only
```

### **Using Bash Script**
```bash
# Simple one-liner
./scripts/run_etl.sh ssh
```

### **Using Aliases (After Setup)**
```bash
# Load shortcuts first
source scripts/etl_shortcuts.sh

# Then use simple commands
etl-fast          # Standard ETL on Railway
etl-full-fast     # Full import on Railway
etl-status        # Check system health
```

## 📊 Expected Performance

### **Local Execution (`railway_run`)**
- **Duration**: 2-6 hours (depending on network)
- **Risk**: Connection timeouts possible
- **Resource Usage**: Local CPU/memory

### **Railway SSH Execution (`ssh`)**
- **Duration**: 30 minutes - 2 hours (much faster)
- **Risk**: Minimal (internal Railway network)
- **Resource Usage**: Railway's dedicated resources

## 🛠️ Troubleshooting

### **Railway Connection Issues**
```bash
# Check Railway status
railway status

# Login if needed
railway login

# Test connection
python scripts/run_etl_on_railway.py --test-only
```

### **ETL Failures**
```bash
# Check Railway logs
railway logs --follow

# Monitor specific ETL logs
etl-logs  # (if using shortcuts)
```

### **SSH Issues**
```bash
# Ensure you're linked to the correct service
railway service

# Try manual SSH first
railway ssh
```

## 🔄 Automation Workflows

### **Daily Development Workflow**
```bash
# Morning: Check status
etl-status

# Run ETL when needed
etl-fast

# Monitor if issues
etl-logs
```

### **Production Deployment Workflow**
```bash
# 1. Test connection
python scripts/run_etl_on_railway.py --test-only

# 2. Run full ETL
python scripts/run_etl_on_railway.py --method ssh --full-import

# 3. Monitor results
railway logs --follow
```

### **Weekly Maintenance Workflow**
```bash
# Full refresh with monitoring
./scripts/run_etl.sh ssh --full-import
```

## 🎪 Advanced Options

### **Custom Environment Variables**
```bash
# Run with specific Railway environment
railway environment  # Select staging/production
python scripts/run_etl_on_railway.py --method ssh
```

### **Background Execution**
```bash
# Run in background with logging
nohup python scripts/run_etl_on_railway.py --method ssh > etl.log 2>&1 &

# Monitor progress
tail -f etl.log
```

### **Scheduled Local Automation**
```bash
# Add to crontab for scheduled runs
# Daily at 2 AM: 0 2 * * * cd /path/to/rally && python scripts/run_etl_on_railway.py --method ssh
```

## 🚨 Best Practices

1. **Always test connection first** before long ETL runs
2. **Use SSH method for production** - it's faster and more reliable
3. **Monitor Railway logs** during execution
4. **Run full imports during low-traffic periods**
5. **Keep scripts up to date** with bug fixes

## 📈 Success Indicators

**Successful ETL Output:**
```
✅ Railway CLI connected
✅ Database connection test passed
🚀 Starting ETL process...
📈 Progress: 1,000/18,095 players (5.5%) - 2,450 records imported
...
🎉 ETL completed successfully!
🎊 Automated ETL completed successfully in 01:23:45
```

## 🆘 Getting Help

1. **Command help**: Most scripts support `--help`
2. **Shortcuts help**: `etl_help` (after sourcing shortcuts)
3. **Railway help**: `railway --help`
4. **Check logs**: `railway logs --follow`

---

**Quick Reference Card:**
```bash
# Setup (one-time)
source scripts/etl_shortcuts.sh

# Most common commands
etl-test      # Test connection
etl-fast      # Run ETL (fastest)
etl-status    # Check health
etl_help      # Show all options
``` 