# Railway Staging ETL Cron Job Setup

## Overview
This guide explains how to use the automated ETL cron jobs on Railway staging environment to import fresh JSON data into the staging database.

## 🎯 Problem Solved
When JSON files are updated (e.g., fresh schedule data), the staging database needs to import them to reflect the changes. Previously this required manual intervention, but now it's automated via cron jobs.

## 📋 Staging Cron Jobs Configured

### 1. Regular Staging Import
- **Schedule**: `*/30 * * * *` (Every 30 minutes)
- **Command**: `python chronjobs/railway_cron_etl_staging.py`
- **Purpose**: Frequent imports for testing and immediate updates
- **Use Case**: When you've pushed fresh JSON data and want it imported quickly

### 2. Full Staging Import  
- **Schedule**: `0 */6 * * *` (Every 6 hours)
- **Command**: `python chronjobs/railway_cron_etl_staging.py --full-import`
- **Purpose**: Comprehensive refresh with full data validation
- **Use Case**: Deep data cleanup and integrity checks

## 🚀 How It Works

### Environment Isolation
- **Staging Script**: `chronjobs/railway_cron_etl_staging.py`
- **Environment**: Sets `RAILWAY_ENVIRONMENT=staging`
- **Database**: Connects to Railway staging database
- **JSON Source**: Uses fresh JSON files from `data/leagues/all/`

### Production Comparison
| Feature | Production | Staging |
|---------|------------|---------|
| Schedule | Daily (2 AM) | Every 30 min |
| Full Import | Weekly | Every 6 hours |
| Environment | Production DB | Staging DB |
| Script | `chronjobs/railway_cron_etl.py` | `chronjobs/railway_cron_etl_staging.py` |

## 📅 Deployment Process

### Step 1: Deploy Configuration
The staging cron jobs are now configured in `railway.toml`. To deploy:

```bash
# Commit the changes
git add -A
git commit -m "Add staging ETL cron jobs for automatic JSON imports"

# Deploy to staging
git push origin staging
```

### Step 2: Verify Deployment
1. Go to Railway Dashboard → Your project
2. You should see new cron job services:
   - `staging_etl_import` 
   - `staging_etl_full`
3. Both will show as "Cron Job" type with staging schedules

### Step 3: Monitor First Execution
- **Next 30-minute mark**: `staging_etl_import` should run
- **Next 6-hour mark**: `staging_etl_full` should run
- Check logs in Railway Dashboard → Cron Job Service → Logs

## 🧪 Manual Testing

### Test Staging Database Connection
```bash
# SSH into Railway staging
railway shell --environment staging

# Test connection only
python chronjobs/railway_cron_etl_staging.py --test-only
```

### Run Manual ETL Import
```bash
# SSH into Railway staging
railway shell --environment staging

# Run regular import
python chronjobs/railway_cron_etl_staging.py

# Run full import
python chronjobs/railway_cron_etl_staging.py --full-import
```

## 📊 Expected Log Output

### Success Pattern
```
🚀 RAILWAY STAGING CRON ETL JOB STARTING
✅ STAGING database connection successful!
📥 Starting ETL import process on STAGING...
🎉 STAGING ETL import completed successfully!
🏁 RAILWAY STAGING CRON ETL JOB COMPLETED - ✅ SUCCESS
```

### Failure Pattern
```
🚀 RAILWAY STAGING CRON ETL JOB STARTING
❌ STAGING database connection failed: [error details]
🏁 RAILWAY STAGING CRON ETL JOB COMPLETED - ❌ FAILED
💥 Error details: [specific error message]
```

## 🔧 Use Cases

### Case 1: Fresh Schedule Data Available
**Scenario**: You've scraped new schedule data and committed fresh JSON files

**What Happens**:
1. Push changes to staging branch
2. Wait up to 30 minutes
3. Staging cron job automatically imports new schedule data
4. Test on staging: `https://rally-staging.up.railway.app/mobile/availability`
5. Verify the Glenbrook RC Series 8 schedule now appears

### Case 2: Testing Before Production
**Scenario**: You want to test JSON import process before deploying to production

**What Happens**:
1. Stage your changes on staging environment
2. Let staging cron jobs import and process
3. Verify everything works correctly
4. Then deploy to production with confidence

### Case 3: Database Issues Fixed
**Scenario**: Database had orphaned records or data integrity issues

**What Happens**:
1. Full staging import runs every 6 hours
2. Comprehensive data validation and cleanup
3. Issues automatically resolved
4. Clean dataset ready for production deployment

## ⏰ Schedule Optimization

### Current Schedule Reasoning
- **Every 30 minutes**: Fast feedback for development/testing
- **Every 6 hours**: Regular deep cleanup without overloading system
- **Staging-only**: Doesn't interfere with production stability

### Adjusting Schedules
To modify schedules, edit `railway.toml`:

```toml
# More frequent for urgent testing
[deploy.cronJobs.staging_etl_import]
schedule = "*/15 * * * *"  # Every 15 minutes

# Less frequent full imports
[deploy.cronJobs.staging_etl_full]
schedule = "0 */12 * * *"  # Every 12 hours
```

## 🚨 Troubleshooting

### Cron Job Not Running
1. **Check Railway Dashboard**: Ensure cron jobs appear in project
2. **Verify Deployment**: Check that `railway.toml` changes were deployed
3. **Check Logs**: Look for error messages in cron job service logs

### Database Connection Issues
1. **Environment Variables**: Ensure staging has proper `DATABASE_URL`
2. **Network Issues**: Check Railway status page
3. **Script Issues**: Test manually via `railway shell --environment staging`

### Import Failures
1. **JSON File Issues**: Verify JSON files are valid and properly structured
2. **Schema Issues**: Check if database schema is up to date
3. **Data Integrity**: Look for foreign key constraint violations

## 📈 Benefits

### ✅ Advantages of Staging Cron Jobs
- **Automatic Testing**: Fresh data imported without manual intervention
- **Fast Feedback**: Know within 30 minutes if JSON changes work
- **Production Safety**: Test everything on staging first
- **Data Integrity**: Regular full imports catch and fix issues
- **Development Efficiency**: No more manual ETL runs for testing

### 🔄 Workflow Integration
1. **Developer pushes JSON changes** → Staging branch
2. **Staging cron job auto-imports** → Within 30 minutes  
3. **Developer tests staging** → Verifies functionality
4. **Deploy to production** → With confidence

## 🎯 Next Steps

1. **Deploy the configuration** (push to staging branch)
2. **Wait for first cron execution** (next 30-minute mark)
3. **Verify the availability issue is fixed** on staging
4. **Deploy to production** once staging is confirmed working

The staging cron jobs will now automatically keep your staging database in sync with fresh JSON data, making testing and validation much more efficient! 