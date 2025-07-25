# Upsert System Implementation Plan

## 🎯 **Goal**: Production-Ready Incremental ETL with Upsert Capability

## 📋 **Phase 1: Database Cleanup & Preparation**
**Timeline**: 1-2 days | **Priority**: HIGH

### 1.1 Re-scrape Match Data with Proper Match IDs
```bash
# Clear existing match_scores data (backup first!)
python3 scripts/backup_current_match_scores.py

# Re-run match scores scraper to get all matches with real match_ids
python3 data/etl/scrapers/scraper_match_scores.py --all-leagues --include-match-ids

# Import fresh data with proper tenniscores_match_id generation
python3 data/etl/database_import/modernized_import_filterable.py
```

### 1.2 Validate Scraper Output
```bash
# Verify scraper is capturing match_id field
python3 -c "
import json
with open('data/leagues/APTA_CHICAGO/match_history.json') as f:
    data = json.load(f)
    with_ids = sum(1 for r in data if r.get('match_id'))
    print(f'Records with match_id: {with_ids}/{len(data)}')
"

# Check consolidation preserves match_ids
python3 data/etl/database_import/consolidate_league_jsons_to_all.py
```

### 1.3 Clean Database Import
```bash
# Backup current database
pg_dump $DATABASE_URL > backups/pre_upsert_backup.sql

# Clear match_scores table for clean re-import
psql $DATABASE_URL -c "TRUNCATE TABLE match_scores CASCADE;"

# Import all match data with proper tenniscores_match_id
python3 data/etl/database_import/modernized_import_filterable.py
```

**✅ Success Criteria**: 
- All match_scores records have `tenniscores_match_id`
- No duplicate records remain
- All foreign key relationships intact

---

## 📋 **Phase 2: ETL System Enhancement**
**Timeline**: 2-3 days | **Priority**: HIGH

### 2.1 Verify All Import Scripts Updated
- ✅ `modernized_import_filterable.py` 
- ✅ `quick_import_matches.py`
- ✅ `quick_import_matches_fixed.py`
- ✅ `import_all_jsons_to_database.py`

### 2.2 Enhanced Error Handling
```python
# Add comprehensive logging for upsert operations
# Track INSERT vs UPDATE counts
# Monitor duplicate prevention
```

### 2.3 Performance Optimization
```python
# Batch size tuning for large datasets
# Connection pooling for Railway
# Memory usage optimization
```

**✅ Success Criteria**:
- All ETL scripts use consistent `tenniscores_match_id` generation
- Comprehensive logging and monitoring
- Performance optimized for production loads

---

## 📋 **Phase 3: Testing & Validation**
**Timeline**: 1-2 days | **Priority**: CRITICAL

### 3.1 End-to-End Testing
```bash
# Test complete pipeline
python3 test_end_to_end_upsert.py

# Test with different data scenarios:
# - New records (INSERT)
# - Existing records (UPDATE) 
# - Mixed datasets
# - Large datasets (1000+ records)
```

### 3.2 Performance Testing
```bash
# Test import speed
time python3 data/etl/database_import/modernized_import_filterable.py

# Memory usage monitoring
# Database connection handling
```

### 3.3 Rollback Testing
```bash
# Test failure scenarios
# Verify rollback mechanisms work
# Test recovery procedures
```

**✅ Success Criteria**:
- All test scenarios pass
- Performance meets requirements
- Rollback procedures validated

---

## 📋 **Phase 4: Production Deployment**
**Timeline**: 1 day | **Priority**: HIGH

### 4.1 Staging Environment
```bash
# Deploy to staging first
git push origin staging

# Run full test suite on staging
python3 test_end_to_end_upsert.py

# Performance validation on staging
```

### 4.2 Production Deployment
```bash
# Database backup before deployment
python3 scripts/backup_production_database.py

# Deploy schema changes first
python3 data/dbschema/dbschema_workflow.py --auto

# Deploy application code
git push origin main

# Run backfill on production
python3 scripts/backfill_tenniscores_match_id.py
```

### 4.3 Post-Deployment Validation
```bash
# Verify production functionality
python3 scripts/validate_production_upsert.py

# Monitor for issues
# Check error logs
```

**✅ Success Criteria**:
- Staging tests pass completely
- Production deployment successful
- No data loss or corruption
- Upsert functionality working in production

---

## 📋 **Phase 5: Monitoring & Documentation**
**Timeline**: 1 day | **Priority**: MEDIUM

### 5.1 Monitoring Setup
```python
# ETL success/failure alerts
# Duplicate detection alerts  
# Performance monitoring
# Database health checks
```

### 5.2 Documentation
- ✅ Update ETL documentation
- ✅ Create upsert troubleshooting guide
- ✅ Document new processes for team

### 5.3 Team Training
- Demo new upsert capabilities
- Train team on troubleshooting
- Update operational procedures

**✅ Success Criteria**:
- Comprehensive monitoring in place
- Team trained on new system
- Documentation complete

---

## 🚨 **Immediate Action Items** (Next 24 Hours)

### 1. **Re-scrape Match Data** (60 minutes)
```bash
# Backup current database
pg_dump $DATABASE_URL > backups/pre_scraper_backup.sql

# Re-run match scores scraper with match IDs
python3 data/etl/scrapers/scraper_match_scores.py --all-leagues

# Verify match_id coverage in scraped data
python3 -c "
import json
with open('data/leagues/APTA_CHICAGO/match_history.json') as f:
    data = json.load(f)
    with_ids = sum(1 for r in data if r.get('match_id'))
    print(f'APTA records with match_id: {with_ids}/{len(data)}')
"
```

### 2. **Run Fresh Import** (30 minutes)
```bash
# Consolidate scraped data
python3 data/etl/database_import/consolidate_league_jsons_to_all.py

# Clear and re-import database with proper tenniscores_match_id
psql $DATABASE_URL -c "TRUNCATE TABLE match_scores CASCADE;"
python3 data/etl/database_import/modernized_import_filterable.py
```

### 3. **Validate Results** (15 minutes)
```bash
# Check that all records have tenniscores_match_id
psql $DATABASE_URL -c "
SELECT 
    COUNT(*) as total_records,
    COUNT(tenniscores_match_id) as with_match_id,
    COUNT(tenniscores_match_id)::float / COUNT(*) * 100 as coverage_percent
FROM match_scores;
"
```

### 4. **Test Upsert Functionality** (30 minutes)
```bash
# Run end-to-end test
python3 test_end_to_end_upsert.py

# Or run the complete implementation guide
python3 scripts/implement_upsert_system.py
```

---

## 🎯 **Success Metrics**

| Metric | Target | Current |
|--------|--------|---------|
| Records with `tenniscores_match_id` | 100% | ~15% |
| Duplicate records | 0 | Unknown |
| ETL scripts updated | 100% | 100% ✅ |
| Upsert success rate | >99% | 100% ✅ |
| Import speed | <10 min for full dataset | TBD |

---

## 🚀 **Long-term Benefits**

1. **✅ Reliable ETL**: Safe to re-run imports without duplicates
2. **✅ Real-time Updates**: Score corrections flow through immediately  
3. **✅ Data Integrity**: No more orphaned or duplicate records
4. **✅ Performance**: Faster incremental updates vs full rebuilds
5. **✅ Scalability**: System handles growing data volumes
6. **✅ Maintainability**: Cleaner, more predictable data operations

---

## 🆘 **Rollback Plan**

If issues arise during deployment:

1. **Immediate**: Restore from database backup
2. **ETL**: Revert to previous import scripts  
3. **Validation**: Run integrity checks
4. **Communication**: Notify team of rollback
5. **Analysis**: Identify and fix issues before re-deployment

---

**🎉 Ready to start? Begin with Phase 1, Step 1.1!** 