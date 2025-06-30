# Cron Jobs Directory

This directory contains all cron job and background task scripts for the Rally platform.

## 📋 Scripts Overview

### Production ETL Scripts
- **`railway_cron_etl.py`** - Production ETL cron job script
  - Runs daily at 2 AM UTC (via Railway cron job)
  - Imports fresh JSON data into production database
  - Full logging and error handling for production reliability

### Staging ETL Scripts  
- **`railway_cron_etl_staging.py`** - Staging ETL cron job script
  - Runs every 30 minutes for testing (via Railway cron job)
  - Full import runs every 6 hours
  - Connects specifically to staging database for safe testing

### Background Job Scripts
- **`railway_background_etl.py`** - Background ETL execution script
  - Runs ETL imports as background processes (no HTTP timeout limits)
  - Can be triggered manually or via Railway cron jobs
  - Used for bypassing web interface timeout constraints

### Monitoring & Setup
- **`setup_cron_monitoring.sh`** - Cron job monitoring setup script
  - Configures monitoring and alerting for cron job execution
  - Sets up logging and health checks

## 🚀 Usage

### Railway Cron Jobs (Automatic)
The scripts are automatically executed by Railway based on schedules defined in `railway.toml`:

```toml
# Production cron jobs
[deploy.cronJobs.etl_import]
schedule = "0 2 * * *"  # Daily at 2 AM UTC
command = "python chronjobs/railway_cron_etl.py"

# Staging cron jobs  
[deploy.cronJobs.staging_etl_import]
schedule = "*/30 * * * *"  # Every 30 minutes
command = "python chronjobs/railway_cron_etl_staging.py"
```

### Manual Execution
You can also run these scripts manually:

```bash
# SSH into Railway environment
railway shell

# Test database connection
python chronjobs/railway_cron_etl.py --test-only

# Run production ETL
python chronjobs/railway_cron_etl.py

# Run staging ETL with full import
python chronjobs/railway_cron_etl_staging.py --full-import

# Run background ETL (no timeout limits)
python chronjobs/railway_background_etl.py
```

## 🎯 Environment Targeting

### Production Scripts
- **Target**: Production Railway database
- **Environment**: `RAILWAY_ENVIRONMENT=production` (default)
- **Schedule**: Conservative (daily/weekly) for stability
- **Scripts**: `railway_cron_etl.py`, `railway_background_etl.py`

### Staging Scripts  
- **Target**: Staging Railway database
- **Environment**: `RAILWAY_ENVIRONMENT=staging`
- **Schedule**: Frequent (every 30 min) for testing
- **Scripts**: `railway_cron_etl_staging.py`

## 📊 Command Line Options

All ETL scripts support these common options:

- `--test-only` - Test database connection without running ETL
- `--full-import` - Run comprehensive full import instead of incremental
- No arguments - Run regular incremental import

## 🔧 Development

### Adding New Cron Jobs
1. Create script in `chronjobs/` directory
2. Add cron job configuration to `railway.toml`
3. Update this README with script description
4. Test manually before deploying

### Script Structure
All cron job scripts should follow this pattern:
- Comprehensive logging with timestamps
- Signal handlers for graceful shutdown
- Database connection testing
- Error handling and cleanup
- Environment-specific configuration

## 📚 Related Documentation

- **Railway Cron ETL Setup**: `docs/RAILWAY_CRON_ETL_SETUP.md`
- **Staging ETL Setup**: `docs/STAGING_ETL_CRON_SETUP.md`
- **Background Jobs**: `deployment/railway_background_jobs.md`

## 🚨 Important Notes

- **Never run production scripts against staging** - Each script is environment-specific
- **Test on staging first** - Always verify changes work on staging before production
- **Monitor Railway logs** - All cron job output appears in Railway dashboard logs
- **Respect schedules** - Avoid manual runs during scheduled execution times 