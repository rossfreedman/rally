# Database Schema Comparison Report

**Generated:** August 4, 2025  
**Environments Compared:** Local, Staging, Production

## Executive Summary

The comprehensive database schema comparison across all three environments (Local, Staging, Production) has revealed significant differences that require immediate attention. The analysis shows:

- **6 tables missing in Production** (Critical)
- **5 tables missing in Staging** 
- **4 tables with column differences**
- **25 tables with data volume differences**

## 🚨 Critical Issues

### Missing Tables in Production
The following tables are present in Local but missing in Production (and most in Staging):

1. **`user_session_refresh_signals`** - Missing in Production only
2. **`user_contexts`** - Missing in Staging and Production
3. **`practice_times`** - Missing in Staging and Production
4. **`test_etl_runs`** - Missing in Staging and Production
5. **`practice_times_corrupted_backup`** - Missing in Staging and Production
6. **`enhanced_league_contexts_backup`** - Missing in Staging and Production

**Impact:** These missing tables could cause application failures if the code expects them to exist in production.

## 📋 Schema Differences

### Column Differences by Table

#### `lineup_escrow` Table
- **Missing in Staging & Production:** `recipient_team_id`, `initiator_team_id`
- **Impact:** Lineup escrow functionality may not work properly in staging/production

#### `user_player_associations` Table
- **Missing in Local:** `is_primary`
- **Impact:** Primary association logic may not work in local development

#### `match_scores` Table
- **Missing in Staging:** `match_id`
- **Missing in Production:** `tenniscores_match_id`, `match_id`
- **Impact:** Match score tracking may be incomplete in staging/production

#### `users` Table
- **Missing in Local:** `team_id`
- **Missing in Staging:** `notifications_hidden`
- **Missing in Production:** `team_id`, `notifications_hidden`
- **Impact:** User team assignments and notification preferences may not work consistently

## 📊 Data Volume Analysis

### Environment Totals
- **Local:** 3,911,680 total rows
- **Staging:** 462,689 total rows  
- **Production:** 445,057 total rows

### Significant Data Differences

#### Tables with Infinite Differences (Data in Local only)
1. **`user_instructions`** - Local: 2 rows, Others: 0 rows
2. **`lineup_escrow`** - Local: 22 rows, Others: 0 rows
3. **`lineup_escrow_views`** - Local: 37 rows, Others: 0 rows
4. **`saved_lineups`** - Local: 1 row, Staging: 0, Production: 1

#### Tables with 2x+ Volume Differences
1. **`polls`** - 3.0x difference (Local: 2, Staging: 6, Production: 5)
2. **`poll_choices`** - 3.0x difference (Local: 4, Staging: 12, Production: 10)
3. **`user_player_associations`** - 2.9x difference (Local: 18, Staging: 45, Production: 53)
4. **`user_activity_logs`** - 2.7x difference (Local: 9,102, Staging: 3,407, Production: 3,851)
5. **`pickup_game_participants`** - 2.7x difference (Local: 6, Staging: 14, Production: 16)

## 💡 Recommendations

### Immediate Actions (Critical)

1. **Deploy Missing Tables to Production**
   - Run database migrations to add the 6 missing tables
   - Ensure all environments have consistent schema
   - Priority: `user_session_refresh_signals` (missing only in production)

2. **Synchronize Column Differences**
   - Add missing columns to all environments
   - Verify column types are compatible across environments
   - Test functionality that depends on these columns

### Data Synchronization

3. **Investigate Data Inconsistencies**
   - Check ETL processes for data synchronization issues
   - Verify data integrity across environments
   - Identify why some tables have vastly different row counts

### Environment Cleanup

4. **Clean Up Local Development Tables**
   - Remove test/backup tables from local environment
   - Tables to consider removing:
     - `test_etl_runs`
     - `practice_times_corrupted_backup`
     - `enhanced_league_contexts_backup`
     - `user_contexts`
     - `practice_times`

## 🔧 Technical Details

### Environment Connectivity
- ✅ **Local:** Connected successfully (41 tables, 33 sequences)
- ✅ **Staging:** Connected successfully (36 tables, 31 sequences)  
- ✅ **Production:** Connected successfully (35 tables, 31 sequences)

### Schema Comparison Summary
- **Local:** 41 tables
- **Staging:** 36 tables
- **Production:** 35 tables
- **Tables with differences:** 4
- **Schema identical:** ❌ NO

### Data Comparison Summary
- **Tables with count differences:** 25
- **Data identical:** ❌ NO

## 📝 Next Steps

1. **Immediate (This Week)**
   - Deploy missing tables to production
   - Add missing columns to all environments
   - Test critical functionality in all environments

2. **Short Term (Next 2 Weeks)**
   - Investigate data synchronization issues
   - Clean up local development environment
   - Implement automated schema validation

3. **Long Term (Next Month)**
   - Set up automated schema comparison in CI/CD
   - Implement database migration testing
   - Create environment synchronization procedures

## 🛠️ Tools Created

1. **`scripts/compare_all_environments.py`** - Comprehensive multi-environment comparison
2. **`scripts/schema_differences_summary.py`** - Focused analysis of key differences
3. **Detailed JSON reports** - Saved for historical tracking

## 📞 Contact

For questions about this report or to discuss implementation of recommendations, please contact the development team.

---

**Report generated by:** Database Schema Comparison Tool  
**Last updated:** August 4, 2025 