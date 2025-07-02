# ETL Multi-Environment Execution Guide

This guide covers how to run the Rally ETL script across all three environments with optimal performance and configuration.

## 🌍 **Environments**

| Environment | Description | Database | Performance | Validation |
|-------------|-------------|----------|-------------|-----------|
| **Local** | Development environment | Local PostgreSQL | Fast (~2-3 min) | ✅ Always Enabled |
| **Railway Staging** | Testing environment | Railway staging DB | Medium (optimized) | ✅ Always Enabled |
| **Railway Production** | Live environment | Railway production DB | Medium (optimized) | ✅ Always Enabled |

## 🛡️ **Data Integrity First**

**Player validation is ALWAYS enabled across all environments for data integrity.** This ensures:
- ✅ Accurate player ID resolution and fallback matching
- ✅ Consistent data quality across environments  
- ✅ Prevention of orphaned or invalid player references
- ✅ Comprehensive error detection and reporting

## 🚀 **Quick Commands**

### **Railway Staging (Testing Environment)**
```bash
# Option 1: Direct SSH (runs on Railway servers)
railway ssh python chronjobs/railway_background_etl.py --environment railway_staging

# Option 2: Via automation script
python scripts/run_etl_on_railway.py --method ssh --environment railway_staging
```

### **Railway Production (Live Environment)**
```bash
# Production with full safety and validation
railway ssh python chronjobs/railway_background_etl.py --environment railway_production
```

### **Local Development**
```bash
# Local execution (auto-detects environment)
python chronjobs/railway_background_etl.py

# Force local settings explicitly
python chronjobs/railway_background_etl.py --environment local
```

## 📊 **Command Reference**

### **Direct ETL Script**
```bash
python chronjobs/railway_background_etl.py [OPTIONS]

Options:
  --environment, -e     Force environment: local, railway_staging, railway_production
```

### **Automation Script**
```bash
python scripts/run_etl_on_railway.py [OPTIONS]

Options:
  --method             Execution method: railway_run, ssh, cron
  --environment, -e    Force environment: local, railway_staging, railway_production
  --test-only         Only test connection, don't run ETL
```

## ⚙️ **Environment-Specific Optimizations**

### **Local Environment**
- **Batch Size**: 1000 records
- **Commit Frequency**: Every 100 operations
- **Retries**: 5 attempts
- **Validation**: ✅ Always enabled
- **Performance**: ~2-3 minutes

### **Railway Staging**
- **Batch Size**: 200 records (memory optimized)
- **Commit Frequency**: Every 50 operations (frequent commits)
- **Retries**: 8 attempts
- **Validation**: ✅ Always enabled (data integrity priority)
- **Connection Management**: Rotation every 2k ops, max 5 min age
- **Performance**: Optimized for reliable testing

### **Railway Production**
- **Batch Size**: 500 records (balanced)
- **Commit Frequency**: Every 100 operations
- **Retries**: 10 attempts (maximum reliability)
- **Validation**: ✅ Always enabled (safety and integrity priority)
- **Connection Management**: Rotation every 5k ops, max 10 min age
- **Performance**: Balanced speed and safety

## 🎯 **Best Practices by Use Case**

### **Development Testing**
```bash
# Local with full validation (always enabled)
python chronjobs/railway_background_etl.py --environment local
```

### **Staging Testing**
```bash
# Staging with optimized performance and validation
railway ssh python chronjobs/railway_background_etl.py --environment railway_staging
```

### **Production Deployment**
```bash
# Safe production import with full validation
railway ssh python chronjobs/railway_background_etl.py --environment railway_production
```

## 🔧 **Troubleshooting**

### **Slow Performance on Railway**
1. **Use SSH method** instead of `railway run`:
   ```bash
   # Faster (runs on Railway servers)
   railway ssh python chronjobs/railway_background_etl.py
   
   # Slower (runs locally with remote DB)
   railway run python chronjobs/railway_background_etl.py
   ```

2. **Check Railway environment**:
   ```bash
   railway status
   railway environment
   ```

### **Environment Detection Issues**
Force the environment explicitly:
```bash
# Force staging
python chronjobs/railway_background_etl.py --environment railway_staging

# Force production
python chronjobs/railway_background_etl.py --environment railway_production
```

### **Data Quality Issues**
Player validation is always enabled and will:
- Automatically resolve missing player IDs through fallback matching
- Provide detailed validation summaries in logs
- Catch and report data inconsistencies

## 📈 **Performance Comparison**

| Method | Location | Speed | Validation | Best For |
|--------|----------|-------|------------|----------|
| Local direct | Local machine | ⚡⚡⚡ Fast | ✅ Always | Development |
| Railway SSH + staging | Railway servers | ⚡⚡ Medium | ✅ Always | Speed testing |
| Railway SSH + production | Railway servers | ⚡⚡ Medium | ✅ Always | Production |
| Railway run | Local with remote DB | ⚡ Slow | ✅ Always | Debugging |

## 🔗 **Connection Management**

The ETL system now includes intelligent **database connection management** to prevent timeouts and optimize performance on Railway:

### **Connection Limits by Environment**
| Environment | Max Connection Age | Rotation Frequency | Max Operations |
|-------------|-------------------|--------------------|----------------|
| **Local** | 30 minutes | Every 10k operations | 50k operations |
| **Railway Staging** | 5 minutes | Every 2k operations | 10k operations |
| **Railway Production** | 10 minutes | Every 5k operations | 25k operations |

### **How It Works**
1. **Automatic Rotation**: Connections are automatically rotated before hitting Railway's timeout limits
2. **Operation Tracking**: System counts database operations and rotates proactively
3. **Age Monitoring**: Connections are refreshed based on time limits
4. **Graceful Handling**: Rotation happens at safe commit points to prevent data loss

### **Benefits**
- ✅ **Prevents connection timeouts** on Railway
- ✅ **Reduces memory accumulation** during long imports
- ✅ **Maintains consistent performance** throughout the ETL process
- ✅ **Automatic optimization** for each environment

## 🚨 **Safety Notes**

1. **Always test in staging first** before running in production
2. **Player validation is always enabled** for data integrity across all environments
3. **Monitor Railway quotas** when running frequent imports
4. **Use SSH method** for best performance on Railway
5. **Commit changes** before running ETL to ensure latest code
6. **Connection management is automatic** - no manual intervention needed

## 🔄 **Automated Workflows**

### **Full Testing Workflow**
```bash
# 1. Test connection
python scripts/run_etl_on_railway.py --test-only

# 2. Run on staging with optimized performance
python scripts/run_etl_on_railway.py --method ssh --environment railway_staging

# 3. Run on production with full safety
python scripts/run_etl_on_railway.py --method ssh --environment railway_production
```

### **Quick Development Test**
```bash
# Optimized execution with full validation
railway ssh python chronjobs/railway_background_etl.py --environment railway_staging
``` 