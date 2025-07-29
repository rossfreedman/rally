# 🌍 Environment Usage Guide for Master Import Script

## Overview

The master import script automatically detects and adapts to different environments based on environment variables and deployment context. This guide explains how to use it across local, staging, and production environments.

## 🔧 Environment Detection

The script uses these environment variables to determine which environment it's running in:

### **Database Environment**
- `RALLY_DATABASE`: Controls which database to use
  - `"test"` → Uses test database (rally_test)
  - `"main"` → Uses main database (rally)
  - Default: `"test"` (for safety)

### **Railway Environment**
- `RAILWAY_ENVIRONMENT`: Detects if running on Railway
- `DATABASE_URL`: Railway's internal database URL
- `DATABASE_PUBLIC_URL`: Railway's public database URL

### **SMS Notifications**
- `TWILIO_ACCOUNT_SID`: Twilio account identifier
- `TWILIO_AUTH_TOKEN`: Twilio authentication token
- `TWILIO_MESSAGING_SERVICE_SID`: Twilio messaging service

## 🏠 Local Development

### **Setup**
```bash
# Set environment variables in .env file
RALLY_DATABASE=test  # Use test database for safety
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_MESSAGING_SERVICE_SID=your_messaging_service_sid
```

### **Usage**
```bash
# Test mode (recommended for local development)
python3 data/etl/database_import/master_import_test.py --environment staging

# Full import with test database
python3 data/etl/database_import/master_import.py --environment staging

# Single league import
python3 data/etl/database_import/master_import.py --environment staging --league APTA_CHICAGO

# Switch to main database (be careful!)
export RALLY_DATABASE=main
python3 data/etl/database_import/master_import.py --environment staging
```

### **Database Options**
```bash
# Use test database (safe, won't affect production data)
export RALLY_DATABASE=test

# Use main database (affects real data - use with caution)
export RALLY_DATABASE=main

# Check current database mode
python3 -c "from database_config import get_database_mode; print(get_database_mode())"
```

## 🚀 Staging Environment

### **Railway Staging**
The script automatically detects when running on Railway staging and uses the appropriate database.

### **Usage**
```bash
# All leagues (default)
python3 data/etl/database_import/master_import.py --environment staging

# Single league
python3 data/etl/database_import/master_import.py --environment staging --league APTA_CHICAGO

# Test mode
python3 data/etl/database_import/master_import_test.py --environment staging
```

### **Environment Variables**
Railway staging automatically provides:
- `RAILWAY_ENVIRONMENT=staging`
- `DATABASE_URL` (staging database)
- `DATABASE_PUBLIC_URL` (staging database)
- Twilio credentials for SMS notifications

## 🏭 Production Environment

### **Railway Production**
The script automatically detects when running on Railway production and uses the production database.

### **Usage**
```bash
# All leagues (be very careful!)
python3 data/etl/database_import/master_import.py --environment production

# Single league (safer approach)
python3 data/etl/database_import/master_import.py --environment production --league APTA_CHICAGO

# Test mode first (recommended)
python3 data/etl/database_import/master_import_test.py --environment production
```

### **Safety Considerations**
- **Always test first**: Use test mode before running production imports
- **Single league imports**: Process one league at a time to minimize risk
- **Backup verification**: Ensure backups are current before production imports
- **SMS notifications**: Monitor notifications for immediate feedback

## 🔄 Environment Switching

### **Local to Staging**
```bash
# 1. Test locally first
python3 data/etl/database_import/master_import_test.py --environment staging

# 2. Deploy to staging
git push origin staging

# 3. Run on staging (via Railway)
# The script will automatically detect staging environment
```

### **Staging to Production**
```bash
# 1. Test on staging
python3 data/etl/database_import/master_import_test.py --environment production

# 2. Deploy to production
git push origin main

# 3. Run on production (via Railway)
# The script will automatically detect production environment
```

## 📱 SMS Notifications by Environment

### **Local Development**
- **Status**: Mock notifications (logged only)
- **Reason**: SMS service not available locally
- **Output**: `📱 SMS notification (mock): [message]`

### **Staging**
- **Status**: Real SMS notifications
- **Recipient**: 7732138911
- **Purpose**: Test notification system

### **Production**
- **Status**: Real SMS notifications
- **Recipient**: 7732138911
- **Purpose**: Monitor production imports

## 🛡️ Safety Features

### **Database Protection**
- **Default**: Uses test database (`RALLY_DATABASE=test`)
- **Explicit**: Must set `RALLY_DATABASE=main` for production data
- **Detection**: Automatically detects Railway environment

### **Error Handling**
- **Validation**: Invalid leagues rejected with helpful messages
- **Graceful failures**: Continues processing even if one step fails
- **Detailed logging**: All operations logged with timestamps

### **Testing**
- **Test mode**: Simulates imports without actual data changes
- **Single league**: Process one league at a time
- **Validation**: Comprehensive error checking

## 🔍 Troubleshooting

### **Common Issues**

#### **Database Connection Errors**
```bash
# Check database configuration
python3 -c "from database_config import get_db_url; print(get_db_url())"

# Test database connection
python3 -c "from database_config import test_db_connection; test_db_connection()"
```

#### **SMS Notifications Not Working**
```bash
# Check Twilio configuration
python3 -c "from config import TwilioConfig; print(TwilioConfig.validate_config())"
```

#### **Environment Detection Issues**
```bash
# Check current environment
python3 -c "from database_config import is_local_development; print('Local:', is_local_development())"
python3 -c "import os; print('Railway:', os.getenv('RAILWAY_ENVIRONMENT'))"
```

### **Debug Mode**
```bash
# Enable verbose logging
export PYTHONPATH=.
python3 -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python3 data/etl/database_import/master_import.py --environment staging
```

## 📋 Best Practices

### **Before Running Imports**
1. **Test locally**: Always test with test database first
2. **Check backups**: Ensure data is backed up
3. **Verify environment**: Confirm correct environment variables
4. **Single league**: Start with single league imports
5. **Monitor notifications**: Watch SMS notifications for status

### **During Imports**
1. **Monitor logs**: Watch for errors and warnings
2. **Check SMS**: Verify notifications are being sent
3. **Validate data**: Check database after each step
4. **Be patient**: Large imports can take time

### **After Imports**
1. **Verify results**: Check that data was imported correctly
2. **Review logs**: Examine detailed logs for any issues
3. **Test functionality**: Verify application features work
4. **Document changes**: Note any issues or improvements

## 🚨 Emergency Procedures

### **Stop Import in Progress**
```bash
# If running locally, use Ctrl+C
# If running on Railway, stop the deployment
```

### **Rollback Changes**
```bash
# Restore from backup
# Check logs for what was imported
# Manually revert if necessary
```

### **Contact Admin**
- **Phone**: 7732138911 (receives all SMS notifications)
- **Logs**: Check `logs/master_import_results_*.txt`
- **Railway**: Check Railway deployment logs

---

**Last Updated**: July 29, 2025  
**Version**: 1.0  
**Status**: Production Ready 