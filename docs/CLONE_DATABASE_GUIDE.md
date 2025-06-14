# 🏓 Rally Database Cloning Guide

## 🎯 **Your Goal**
Clone your local Rally database to Railway **without losing any local data**, making Railway perfectly match your local database in both schema and data.

## 📊 **Current Situation**
Based on the database comparison:
- **Local Database**: 131,030 rows (more complete)
- **Railway Database**: 122,051 rows (missing data)
- **Schema Differences**: 7 tables have column differences
- **Data Differences**: Several tables empty in Railway (`match_scores`, `schedule`, `series_stats`)

## 🚀 **Recommended Approach: Fast Clone (BEST)**

### Option 1: `fast_clone_local_to_railway.py` ⭐ **RECOMMENDED**

**Why this is best:**
- ⚡ **Fastest**: Uses `pg_dump` and `pg_restore` (native PostgreSQL tools)
- 🔒 **Safest**: Creates backup before any changes
- 🎯 **Complete**: Handles both schema and data in one operation
- 🧹 **Clean**: Automatically cleans up temporary files

**Time estimate**: 2-5 minutes (vs 15-30 minutes for row-by-row)

```bash
python fast_clone_local_to_railway.py
```

**What it does:**
1. Backs up Railway database
2. Creates a complete dump of local database
3. Restores the dump to Railway
4. Syncs Alembic version
5. Verifies success
6. Cleans up temporary files

---

## 🔧 **Alternative Approach: Gradual Clone**

### Option 2: `clone_local_to_railway.py` 

**When to use:**
- If you want more granular control
- If you want to see each table being copied
- If you prefer Alembic-first approach

**Time estimate**: 15-30 minutes

```bash
python clone_local_to_railway.py
```

**What it does:**
1. Backs up Railway database
2. Generates Alembic migration for schema differences
3. Applies schema migration
4. Truncates Railway tables
5. Copies data table by table
6. Verifies success

---

## 🔍 **Before You Start**

### Prerequisites Check:
```bash
# Check that you have PostgreSQL tools installed
which pg_dump
which psql

# Verify database connections
python check_alembic_status.py

# Review current differences
python compare_databases.py
```

### Safety Checklist:
- [ ] **Local data is already safe** (you're not modifying local database)
- [ ] **Railway will be backed up** (both scripts create backups automatically)
- [ ] **You have confirmed the differences** (ran comparison script)
- [ ] **PostgreSQL tools are available** (`pg_dump`, `psql`)

---

## 📋 **Step-by-Step Instructions**

### **RECOMMENDED: Fast Clone Method**

1. **Review the differences** (if you haven't):
   ```bash
   python compare_databases.py
   ```

2. **Run the fast clone**:
   ```bash
   python fast_clone_local_to_railway.py
   ```

3. **Type 'YES' when prompted** to confirm

4. **Wait for completion** (2-5 minutes)

5. **Verify success** by running:
   ```bash
   python compare_databases.py
   ```

### Expected Output:
```
🏓 RALLY FAST DATABASE CLONE: Local → Railway
============================================================
✅ SUCCESS: Creating Railway backup
✅ SUCCESS: Dumping local database  
✅ SUCCESS: Restoring to Railway
✅ SUCCESS: Updating Alembic version
✅ SUCCESS: Verifying clone success
🎉 FAST DATABASE CLONE COMPLETED SUCCESSFULLY!
✅ Railway database now perfectly matches local database
```

---

## 🛠️ **Troubleshooting**

### Common Issues:

#### 1. **"pg_dump: command not found"**
**Solution**: Install PostgreSQL tools
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client
```

#### 2. **Connection timeout to Railway**
**Solution**: Check Railway database URL and network connection
```bash
# Test connection manually
psql "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway" -c "SELECT 1;"
```

#### 3. **"Permission denied" or access errors**
**Solution**: Verify Railway database credentials are current

#### 4. **Clone verification fails**
**Solution**: Run comparison again and check specific differences
```bash
python compare_databases.py
```

### Recovery Options:

If something goes wrong, you can restore Railway database:
```bash
# The backup file will be shown in the output, e.g.:
psql "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway" < railway_backup_before_fast_clone_TIMESTAMP.sql
```

---

## ✅ **Post-Clone Verification**

After cloning, verify everything worked:

1. **Check databases are identical**:
   ```bash
   python compare_databases.py
   ```

2. **Check Alembic status**:
   ```bash
   python check_alembic_status.py
   ```

3. **Test your Railway application** to ensure it works correctly

---

## 🔄 **Future Synchronization**

After the initial clone, for future updates:

1. **For schema changes**: Use Alembic migrations
   ```bash
   # Generate migration
   alembic revision --autogenerate -m "your_change"
   
   # Apply to Railway
   SYNC_RAILWAY=true alembic upgrade head
   ```

2. **For data sync**: You can run the comparison and clone scripts periodically

3. **For automated sync**: Consider setting up a scheduled job

---

## 📊 **Summary**

| Method | Time | Complexity | Safety | Best For |
|--------|------|------------|--------|----------|
| **Fast Clone** ⭐ | 2-5 min | Low | High | Complete database replacement |
| **Gradual Clone** | 15-30 min | Medium | High | Granular control, learning |
| **Manual Alembic** | 1+ hour | High | Medium | Schema-only changes |

## 🚀 **Ready to Go?**

**Recommended command:**
```bash
python fast_clone_local_to_railway.py
```

This will make your Railway database **perfectly match** your local database safely and efficiently!

---

*Generated by Rally Database Management Tools*  
*Last updated: 2025-06-13* 