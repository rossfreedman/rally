# Railway Cron Job ETL Setup Guide

## Overview
This guide walks you through setting up automated ETL imports using Railway's cron job system. This is the most reliable method for scheduled data imports with no timeout limits.

## 🕐 Cron Job Schedules Configured

### Daily Import (Default)
- **Schedule**: `0 2 * * *` (Daily at 2:00 AM UTC)
- **Command**: `python scripts/railway_cron_etl.py`
- **Purpose**: Regular daily data updates

### Weekly Full Import (Optional)
- **Schedule**: `0 3 * * 0` (Sunday at 3:00 AM UTC)  
- **Command**: `python scripts/railway_cron_etl.py --full-import`
- **Purpose**: Comprehensive weekly refresh

## 📋 Step-by-Step Setup

### Step 1: Deploy Cron Job Configuration
The cron jobs are already configured in `railway.toml`. When you deploy, Railway will automatically:
1. Create two cron job services
2. Schedule them according to the specified times
3. Run them with the same environment as your main app

### Step 2: Verify Deployment
1. **Push the changes to Railway:**
   ```bash
   git add -A
   git commit -m "Add Railway cron job ETL configuration"
   git push origin main
   ```

2. **Check Railway Dashboard:**
   - Go to Railway dashboard → Your project
   - You should see new services: `etl_import` and `weekly_etl`
   - Each will show as "Cron Job" type

### Step 3: Test Cron Job Manually (Recommended)
Before waiting for the scheduled time, test the cron job:

1. **SSH into Railway:**
   ```bash
   railway shell
   ```

2. **Test database connection:**
   ```bash
   python scripts/railway_cron_etl.py --test-only
   ```

3. **Run full ETL test:**
   ```bash
   python scripts/railway_cron_etl.py
   ```

### Step 4: Monitor Cron Job Execution
Railway provides several ways to monitor cron jobs:

1. **Railway Logs:**
   - Dashboard → Cron Job Service → Logs
   - All output from the script appears here

2. **Cron Job Status:**
   - Dashboard shows last execution time
   - Success/failure status
   - Execution duration

3. **Log Patterns to Watch For:**
   ```
   🚀 RAILWAY CRON ETL JOB STARTING
   ✅ Database connection successful!
   📥 Starting ETL import process...
   🎉 ETL import completed successfully!
   🏁 RAILWAY CRON ETL JOB COMPLETED - ✅ SUCCESS
   ```

## ⚙️ Advanced Configuration

### Custom Schedule
To change the schedule, edit `railway.toml`:
```toml
[deploy.cronJobs.etl_import]
schedule = "0 */6 * * *"  # Every 6 hours
command = "python scripts/railway_cron_etl.py"
```

### Cron Schedule Format
```
* * * * *
│ │ │ │ │
│ │ │ │ └── Day of week (0-7, Sunday = 0 or 7)
│ │ │ └──── Month (1-12)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)
```

### Common Schedules
- `0 2 * * *` - Daily at 2 AM
- `0 */6 * * *` - Every 6 hours
- `0 2 * * 1` - Weekly on Monday at 2 AM
- `0 2 1 * *` - Monthly on 1st at 2 AM

## 🔧 Command Line Options

### Basic Usage
```bash
python scripts/railway_cron_etl.py
```

### Full Import Mode
```bash
python scripts/railway_cron_etl.py --full-import
```

### Test Connection Only
```bash
python scripts/railway_cron_etl.py --test-only
```

## 🚨 Troubleshooting

### Common Issues

1. **Cron Job Not Appearing in Dashboard**
   - Check `railway.toml` syntax
   - Redeploy: `git push origin main`
   - Wait 2-3 minutes for Railway to process

2. **Cron Job Fails to Start**
   - Check Railway logs for Python import errors
   - Verify all dependencies are in `requirements.txt`
   - Test manually: `railway shell` → run command

3. **Database Connection Failures**
   - Ensure `DATABASE_URL` environment variable is set
   - Check Railway PostgreSQL service is running
   - Test connection: `--test-only` flag

4. **ETL Import Errors**
   - Check Railway logs for detailed error messages
   - Verify JSON data files exist in correct locations
   - Test import process manually via Railway shell

### Log Analysis

**Success Indicators:**
```
✅ Database connection successful!
🎉 ETL import completed successfully!
🏁 RAILWAY CRON ETL JOB COMPLETED - ✅ SUCCESS
```

**Failure Indicators:**
```
❌ Database connection failed
❌ ETL import failed!
🏁 RAILWAY CRON ETL JOB COMPLETED - ❌ FAILED
💥 Error details: [specific error]
```

## 📊 Benefits of Cron Job ETL

### ✅ Advantages
- **No timeout limits** - Can run for hours
- **Automatic scheduling** - Runs without manual intervention
- **Independent execution** - Not tied to web requests
- **Full Railway logging** - Complete execution history
- **Resource isolation** - Dedicated compute resources
- **Failure handling** - Automatic retries and error reporting

### 🔄 vs. Other Methods

| Method | Timeout Limit | Manual Trigger | Auto Schedule | Resource Usage |
|--------|---------------|----------------|---------------|----------------|
| Web Interface | 15 minutes | ✅ Required | ❌ No | Shared |
| Background Jobs | No limit | ✅ Required | ❌ No | Shared |
| **Cron Jobs** | **No limit** | **🔧 Optional** | **✅ Yes** | **Dedicated** |

## 🎯 Next Steps

1. **Deploy Configuration**: Push the cron job setup to Railway
2. **Test Manually**: Verify the script works via Railway shell
3. **Monitor First Run**: Watch logs when the scheduled time arrives
4. **Adjust Schedule**: Modify timing based on your data update frequency
5. **Set Up Alerts**: Consider adding notification webhooks for failures

## 🔔 Optional: Set Up Failure Notifications

You can enhance the cron job with failure notifications:

1. **Slack Webhook** (future enhancement)
2. **Email Alerts** (via Railway webhooks)
3. **Dashboard Monitoring** (Railway built-in)

The cron job system is now ready for production use! 