# ETL Validation & Monitoring Tools

This directory contains all the ETL reliability, validation, and monitoring tools for the Rally system.

## **🛠️ Available Tools**

### **Core Tools**
- `master_etl_process.py` - **Main orchestrator** - Runs complete ETL pipeline with validation
- `etl_validation_pipeline.py` - Post-import data validation and integrity checks  
- `integration_tests.py` - End-to-end testing of user-facing features
- `data_quality_monitor.py` - Health monitoring with scoring and historical tracking

### **Documentation**
- `etl_tools_guide.md` - Quick reference guide for using all tools
- `README.md` - This file

## **🚀 Quick Start**

### **Complete ETL Pipeline (Recommended)**
```bash
# Run everything: consolidation → import → validation → testing → monitoring
python data/etl/validation/master_etl_process.py
```

### **Individual Tools**
```bash
# Validation only
python data/etl/validation/etl_validation_pipeline.py

# User feature testing
python data/etl/validation/integration_tests.py

# Health monitoring  
python data/etl/validation/data_quality_monitor.py
```

## **📊 What These Tools Prevent**

These tools were created in response to the **my-series page issue** where only 1 team was displayed instead of 10 due to 99% data loss during ETL that went undetected.

### **Protection Against:**
- ❌ Silent ETL failures (99% data loss undetected)
- ❌ Series stats coverage gaps (teams missing from standings)
- ❌ User feature breakage (pages loading with incomplete data)
- ❌ Data quality degradation over time
- ❌ Deployment of broken data

### **Provides:**
- ✅ Comprehensive validation of data completeness and quality
- ✅ Health scoring (0-100) for deployment confidence
- ✅ Integration testing of user-facing features
- ✅ Historical tracking and trend analysis
- ✅ Clear go/no-go deployment decisions

## **🔄 Tool Relationships**

```
master_etl_process.py
├── Runs data/etl/database_import/consolidate_league_jsons_to_all.py
├── Runs data/etl/database_import/import_all_jsons_to_database.py
├── Runs etl_validation_pipeline.py
├── Runs integration_tests.py
└── Runs data_quality_monitor.py
```

## **📈 Success Metrics**

- **Health Score**: Target 90+ for deployment
- **Series Coverage**: 95%+ of teams must have statistics  
- **Feature Tests**: 100% user features must pass
- **Data Integrity**: Zero orphaned records

## **📞 For More Information**

- **Detailed Guide**: `etl_tools_guide.md` in this directory
- **Implementation Roadmap**: `docs/ETL_SYSTEM_ROADMAP.md` 
- **Root Cause Analysis**: `docs/ETL_RELIABILITY_FIXES.md`

These tools transform Rally's ETL from **"hope it works"** to **"know it works"** with comprehensive validation, testing, and monitoring. 