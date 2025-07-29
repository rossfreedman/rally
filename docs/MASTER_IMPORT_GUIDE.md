# 🚀 Master Import Script Guide

## Overview

The Master Import Script (`data/etl/database_import/master_import.py`) orchestrates all ETL imports in the correct order with SMS notifications to the admin (7732138911).

## 📋 Import Order

The script runs imports in this specific order:

1. **Consolidate League JSONs** (`consolidate_league_jsons_to_all.py`)
   - Consolidates all league JSON files into unified data
   - Creates backups of existing files
   - Clears and rebuilds consolidated data

2. **Import Stats** (`import_stats.py`)
   - Imports series statistics for all leagues
   - Processes: APTA_CHICAGO, NSTF, CNSWPL, CITA
   - Updates series_stats table

3. **Import Match Scores** (`import_match_scores.py`)
   - Imports match scores and results
   - Processes all match data from consolidated files
   - Updates match_scores table

4. **Import Players** (`import_players.py`)
   - Imports player data and associations
   - Processes all player records
   - Updates players table

## 📱 SMS Notifications

### Admin Phone Number
- **Phone**: 7732138911
- **Notifications**: Sent after each step completion

### Notification Types

#### ✅ Success Notifications
```
Rally ETL: [Step Name] ✅
Duration: [time]
Environment: [staging/production]
```

#### 🚨 Failure Notifications
```
🚨 Rally ETL FAILURE: [Step Name]
Error: [error details]
Environment: [staging/production]
```

#### 🎉 Final Summary
```
🎉 Rally ETL Complete!
X/Y steps successful
Duration: [total time]
Environment: [staging/production]
```

## 🔧 Usage

### Basic Usage
```bash
# Run for staging environment
python3 data/etl/database_import/master_import.py

# Run for production environment
python3 data/etl/database_import/master_import.py --environment production
```

### Test Mode
```bash
# Test the notification system without running actual imports
python3 data/etl/database_import/master_import_test.py --environment staging
```

## 📊 Features

### Error Handling
- **Immediate Failure Notifications**: SMS sent immediately when any step fails
- **Continue on Failure**: Script continues to next step even if one fails
- **Timeout Protection**: 1-hour timeout per step to prevent hanging
- **Detailed Logging**: All results saved to timestamped log files

### Performance Monitoring
- **Duration Tracking**: Each step's execution time is measured
- **Progress Reporting**: Real-time progress updates
- **Summary Statistics**: Final summary with success/failure counts

### Data Safety
- **Automatic Backups**: Existing data backed up before consolidation
- **Rollback Capability**: Detailed logs enable manual rollback if needed
- **Validation**: Each step includes built-in data validation

## 📁 Output Files

### Log Files
- **Main Log**: `logs/master_import.log`
- **Test Log**: `logs/master_import_test.log`
- **Detailed Results**: `logs/master_import_results_YYYYMMDD_HHMMSS.txt`

### Example Log Structure
```
2025-07-29 16:50:01 - INFO - 🎯 Master Import Script Starting
2025-07-29 16:50:01 - INFO - 🌍 Environment: staging
2025-07-29 16:50:01 - INFO - 📱 Admin Phone: 7732138911
2025-07-29 16:50:01 - INFO - 🕐 Start Time: 2025-07-29 16:50:01
2025-07-29 16:50:03 - INFO - ✅ Consolidate League JSONs completed successfully
2025-07-29 16:50:03 - INFO - 📱 SMS sent to admin: Rally ETL: Consolidate League JSONs ✅
```

## 🚨 Troubleshooting

### Common Issues

#### SMS Notifications Not Working
- **Check**: SMS service configuration in `app/services/notifications_service.py`
- **Verify**: Twilio credentials are set correctly
- **Test**: Use test script to validate notification system

#### Import Step Failing
- **Check**: Individual script logs for specific errors
- **Verify**: Database connectivity and permissions
- **Review**: Data file availability and format

#### Timeout Issues
- **Increase**: Timeout value in script (default: 1 hour)
- **Check**: Database performance and connection
- **Monitor**: System resources during import

### Recovery Procedures

#### Partial Failure Recovery
1. **Check**: Which steps failed in the log
2. **Review**: Error details in detailed results file
3. **Fix**: Issues with individual scripts
4. **Re-run**: Failed steps individually or full master script

#### Complete Failure Recovery
1. **Restore**: From backup created by consolidation step
2. **Investigate**: Root cause of failure
3. **Fix**: System issues
4. **Re-run**: Master import script

## 📈 Performance Tips

### Optimization
- **Database**: Ensure adequate resources for large imports
- **Network**: Stable connection for SMS notifications
- **Storage**: Sufficient disk space for logs and backups

### Monitoring
- **Watch**: SMS notifications for real-time status
- **Monitor**: Log files for detailed progress
- **Check**: Database performance during imports

## 🔒 Security Considerations

### SMS Security
- **Phone Number**: Admin phone number is hardcoded (7732138911)
- **Messages**: No sensitive data in SMS notifications
- **Rate Limiting**: Built-in delays between notifications

### Data Security
- **Backups**: Automatic backup creation before modifications
- **Logs**: Detailed logging for audit trail
- **Validation**: Built-in data validation at each step

## 📞 Support

### Emergency Contacts
- **Admin Phone**: 7732138911 (receives all notifications)
- **Logs**: Check `logs/` directory for detailed information
- **Backups**: Located in `data/backups/league_data/`

### Escalation
1. **Check**: SMS notifications for immediate status
2. **Review**: Log files for detailed error information
3. **Contact**: Admin if critical issues persist
4. **Restore**: From backup if necessary

---

**Last Updated**: July 29, 2025  
**Version**: 1.0  
**Status**: Ready for Production Use 