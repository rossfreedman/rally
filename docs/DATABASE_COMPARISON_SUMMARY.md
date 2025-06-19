# 🏓 Rally Database Comparison Summary

## 📊 Comparison Results (Generated: 2025-06-13)

Your Railway and local databases have **significant differences** in both schema and data:

### 🔍 **Schema Differences (7 tables affected):**

| Table | Issue | Details |
|-------|-------|---------|
| `match_scores` | Missing columns in Local | Railway has: `away_score`, `home_score` |
| `player_history` | Missing columns in Local | Railway has: `start_pti` |
| `user_player_associations` | Different columns | Local: `tenniscores_player_id` vs Railway: `player_id` |
| `users` | Multiple differences | Railway has: `league_id`, `tenniscores_player_id`, `club_id`, `series_id`<br/>Type differences: `first_name`, `last_name` (VARCHAR(255) vs VARCHAR(100)) |
| `player_availability` | Missing columns in Local | Railway has: `tenniscores_player_id` |
| `user_instructions` | Missing columns in Local | Railway has: `updated_at` |
| `series_stats` | Missing columns in Local | Railway has: `matches_played`, `losses`, `wins`, `points_for`, `points_against` |

### 📈 **Data Differences:**

- **Local Database**: 131,030 total rows
- **Railway Database**: 122,051 total rows
- **Difference**: 8,979 more rows in local

#### Tables with Row Count Differences:
| Table | Local Rows | Railway Rows | Difference |
|-------|------------|--------------|------------|
| `series_leagues` | 23 | 0 | +23 |
| `match_scores` | 6,446 | 0 | +6,446 |
| `schedule` | 1,857 | 0 | +1,857 |
| `series_stats` | 573 | 0 | +573 |
| `user_activity_logs` | 167 | 76 | +91 |
| `player_availability` | 3 | 0 | +3 |
| `user_player_associations` | 3 | 2 | +1 |
| `clubs` | 46 | 54 | -8 |
| `series` | 24 | 29 | -5 |
| `club_leagues` | 53 | 54 | -1 |
| `leagues` | 2 | 3 | -1 |

## 🛠️ **Tools Created**

I've created several tools to help you manage database comparisons and synchronization:

### 1. `check_alembic_status.py`
**Purpose**: Check current Alembic migration status on both databases

```bash
python check_alembic_status.py
```

**Output**: Shows current migration revision and history for both local and Railway databases.

### 2. `compare_databases.py`
**Purpose**: Comprehensive schema and data comparison between databases

```bash
python compare_databases.py
```

**Features**:
- Schema comparison (tables, columns, types, constraints)
- Data comparison (row counts)
- Detailed JSON report generation
- Console summary report

### 3. `generate_sync_migration.py`
**Purpose**: Generate Alembic migrations to sync database differences

```bash
python generate_sync_migration.py
```

**Features**:
- Interactive migration generation
- Shows current status of both databases
- Generates autogenerate migrations based on differences

## 🚀 **Recommended Actions**

Based on the comparison results, here are your options:

### Option 1: Sync Railway to Match Local (Recommended)
If your local database has the most up-to-date schema and data:

1. **Generate sync migration**:
   ```bash
   python generate_sync_migration.py
   ```

2. **Review the generated migration** before applying

3. **Apply to Railway**:
   ```bash
   SYNC_RAILWAY=true alembic upgrade head
   ```

### Option 2: Sync Local to Match Railway
If Railway database is the source of truth:

1. **Generate reverse migration by temporarily switching the comparison logic**
2. **Apply to local database**:
   ```bash
   alembic upgrade head
   ```

### Option 3: Manual Data Migration
For the data differences, you may need to:

1. **Export data from source database**
2. **Import specific tables/records**
3. **Use ETL scripts for data transformation**

## ⚠️ **Important Considerations**

### Before Making Changes:
- [ ] **Backup both databases** before any migration
- [ ] **Test migrations on staging/development environment first**
- [ ] **Review generated migration code** for correctness
- [ ] **Consider data migration strategy** for missing records

### Schema Migration Notes:
- The `user_player_associations` table has fundamentally different column names (`tenniscores_player_id` vs `player_id`)
- Column type changes in `users` table may require data validation
- Some tables are completely empty in Railway (`match_scores`, `schedule`, `series_leagues`, `series_stats`)

### Data Migration Notes:
- Large tables like `match_scores` (6,446 rows) and `schedule` (1,857 rows) are missing from Railway
- Some reference data differs (`clubs`, `series`, `leagues`)
- User activity logs are significantly different (167 vs 76 rows)

## 🔧 **Using Alembic for Synchronization**

### Check Current Status:
```bash
# Local database
alembic current -v

# Railway database  
SYNC_RAILWAY=true alembic current -v
```

### Generate Migration:
```bash
# For Railway → Local sync
SYNC_RAILWAY=true alembic revision --autogenerate -m "sync_railway_to_local"
```

### Apply Migration:
```bash
# To Railway database
SYNC_RAILWAY=true alembic upgrade head

# To Local database
alembic upgrade head
```

## 📋 **Next Steps**

1. **Review this summary** and decide on synchronization strategy
2. **Run the comparison tools** periodically to monitor differences
3. **Use generated migrations** to synchronize schemas
4. **Develop data migration strategy** for missing records
5. **Set up automated synchronization** if needed

## 🔍 **Additional Analysis**

To get more detailed information about specific tables or data differences, you can:

1. **Run SQL queries** directly on both databases to compare specific records
2. **Use the detailed JSON report** generated by `compare_databases.py`
3. **Modify the comparison script** to focus on specific tables or data patterns

---

*Generated by Rally Database Comparison Tools*
*Last updated: 2025-06-13* 