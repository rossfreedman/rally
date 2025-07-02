# ETL Multi-Environment Execution Guide

This guide covers how to run the Rally ETL script across all three environments with optimal performance and configuration.

## 🌍 **Environments**

| Environment | Description | Database | Performance | Validation Default |
|-------------|-------------|----------|-------------|-------------------|
| **Local** | Development environment | Local PostgreSQL | Fast (~2-3 min) | ✅ Enabled |
| **Railway Staging** | Testing environment | Railway staging DB | Medium (optimized) | ❌ Disabled (speed) |
| **Railway Production** | Live environment | Railway production DB | Medium (optimized) | ✅ Enabled (safety) |

## 🚀 **Quick Commands**

### **Fastest Speed (Staging with validation disabled)**
```bash
# Option 1: Direct SSH (runs on Railway servers)
railway ssh python chronjobs/railway_background_etl.py --environment railway_staging --disable-validation

# Option 2: Via automation script
python scripts/run_etl_on_railway.py --method ssh --environment railway_staging --disable-validation
```

### **Production Safety (validation enabled)**
```bash
# For production with full validation
railway ssh python chronjobs/railway_background_etl.py --environment railway_production --enable-validation
```

### **Local Development**
```bash
# Local execution (auto-detects environment)
python chronjobs/railway_background_etl.py

# Force local settings explicitly
python chronjobs/railway_background_etl.py --environment local --enable-validation
```

## 📊 **Command Reference**

### **Direct ETL Script**
```bash
python chronjobs/railway_background_etl.py [OPTIONS]

Options:
  --environment, -e     Force environment: local, railway_staging, railway_production
  --disable-validation  Skip player validation (faster imports)
  --enable-validation   Enable player validation (safer imports)
```

### **Automation Script**
```bash
python scripts/run_etl_on_railway.py [OPTIONS]

Options:
  --method             Execution method: railway_run, ssh, cron
  --environment, -e    Force environment: local, railway_staging, railway_production
  --disable-validation Skip player validation (faster imports)
  --enable-validation  Enable player validation (safer imports)
  --test-only         Only test connection, don't run ETL
```

## ⚙️ **Environment-Specific Optimizations**

### **Local Environment**
- **Batch Size**: 1000 records
- **Commit Frequency**: Every 100 operations
- **Retries**: 5 attempts
- **Validation**: Enabled by default
- **Performance**: ~2-3 minutes

### **Railway Staging**
- **Batch Size**: 200 records (memory optimized)
- **Commit Frequency**: Every 50 operations (frequent commits)
- **Retries**: 8 attempts
- **Validation**: **Disabled by default** (speed priority)
- **Performance**: Optimized for speed testing

### **Railway Production**
- **Batch Size**: 500 records (balanced)
- **Commit Frequency**: Every 100 operations
- **Retries**: 10 attempts (maximum reliability)
- **Validation**: **Enabled by default** (safety priority)
- **Performance**: Balanced speed and safety

## 🎯 **Best Practices by Use Case**

### **Development Testing**
```bash
# Local with full validation
python chronjobs/railway_background_etl.py --environment local
```

### **Staging Speed Tests**
```bash
# Fastest possible execution
railway ssh python chronjobs/railway_background_etl.py --environment railway_staging --disable-validation
```

### **Production Deployment**
```bash
# Safe production import
railway ssh python chronjobs/railway_background_etl.py --environment railway_production --enable-validation
```

### **Emergency Speed Import**
```bash
# Production with speed optimization (use carefully)
railway ssh python chronjobs/railway_background_etl.py --environment railway_production --disable-validation
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

2. **Disable validation for speed**:
   ```bash
   railway ssh python chronjobs/railway_background_etl.py --disable-validation
   ```

3. **Check Railway environment**:
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

### **Validation Errors**
Enable validation to catch data issues:
```bash
railway ssh python chronjobs/railway_background_etl.py --enable-validation
```

## 📈 **Performance Comparison**

| Method | Location | Speed | Validation | Best For |
|--------|----------|-------|------------|----------|
| Local direct | Local machine | ⚡⚡⚡ Fast | ✅ Yes | Development |
| Railway SSH + staging | Railway servers | ⚡⚡ Medium | ❌ No | Speed testing |
| Railway SSH + production | Railway servers | ⚡⚡ Medium | ✅ Yes | Production |
| Railway run | Local with remote DB | ⚡ Slow | Varies | Debugging |

## 🚨 **Safety Notes**

1. **Always test in staging first** before running in production
2. **Use validation in production** unless you need emergency speed
3. **Monitor Railway quotas** when running frequent imports
4. **Use SSH method** for best performance on Railway
5. **Commit changes** before running ETL to ensure latest code

## 🔄 **Automated Workflows**

### **Full Testing Workflow**
```bash
# 1. Test connection
python scripts/run_etl_on_railway.py --test-only

# 2. Run on staging with speed
python scripts/run_etl_on_railway.py --method ssh --environment railway_staging --disable-validation

# 3. Run on production with safety
python scripts/run_etl_on_railway.py --method ssh --environment railway_production --enable-validation
```

### **Quick Speed Test**
```bash
# Fastest possible execution
railway ssh python chronjobs/railway_background_etl.py --environment railway_staging --disable-validation
``` 