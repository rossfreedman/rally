# Railway Background Jobs Setup

## Overview
This guide sets up background ETL processing to bypass Railway's HTTP timeout limits.

## Background Job Options on Railway

### Option A: Railway Cron Jobs (Recommended)
Railway supports cron jobs for scheduled background tasks.

**Setup:**
1. In Railway dashboard: Add a new service
2. Set as "Cron Job" type
3. Configure schedule (e.g., daily at 2 AM)
4. Use command: `python chronjobs/railway_background_etl.py`

### Option B: Manual Background Execution
Run ETL manually via Railway's shell access.

**Commands:**
```bash
# SSH into Railway container
railway shell

# Run background ETL
python chronjobs/railway_background_etl.py
```

### Option C: API-Triggered Background Jobs
Use Railway's deployment hooks or API webhooks to trigger ETL.

## Environment Variables Required
- `DATABASE_URL` (automatically set by Railway)
- `RAILWAY_ENVIRONMENT` (automatically set)
- All existing Rally environment variables

## Monitoring
- Railway logs will capture all ETL output
- Background jobs can run for hours without HTTP timeouts
- Process can be monitored via Railway dashboard

## Deployment Steps
1. Deploy the background job script
2. Configure Railway cron job service
3. Test manual execution first
4. Set up automated scheduling 