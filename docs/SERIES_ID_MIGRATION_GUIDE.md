# Series ID Migration Guide

## Overview

This guide details the implementation of proper foreign key relationships in the `series_stats` table by adding a `series_id` column that references `series.id`, replacing fragile string-based series matching with robust ID-based queries.

## Background

**Problem:** The `series_stats` table was using string-based series name matching, leading to:
- Series name mismatches causing "No Series Data" issues
- Fragile queries that break when series names have format variations
- Poor performance due to string comparisons instead of integer FK lookups

**Solution:** Add `series_id` foreign key column to `series_stats` table for direct ID-based relationships.

## Implementation Steps

### Step 1: Apply Database Migration

Add the `series_id` column to the `series_stats` table:

```bash
# Apply the migration
psql $DATABASE_URL -f migrations/add_series_id_to_series_stats.sql
```

**Migration file:** `migrations/add_series_id_to_series_stats.sql`
- Adds `series_id` INTEGER column with foreign key to `series(id)`
- Creates index for performance
- Uses `IF NOT EXISTS` for safe re-execution

### Step 2: Populate Series ID Values

Run the population script to match existing series names to series IDs:

```bash
python scripts/populate_series_id_in_series_stats.py
```

**Features:**
- Multiple matching strategies (exact, case-insensitive, format conversion)
- Handles common naming variations (Division ↔ Series ↔ Chicago)
- Comprehensive logging and match strategy reporting
- Safe to re-run multiple times

**Expected Output:**
```
✅ Updated 1,247 records
📊 Match strategies used:
   exact_match: 1,189 records
   converted_match (Division → Series): 58 records
```

### Step 3: Test Implementation

Run comprehensive tests to ensure everything works:

```bash
python scripts/test_series_id_implementation.py
```

**Tests Include:**
- Column existence verification
- Series ID population coverage
- Foreign key relationship integrity
- API functionality with series_id lookups
- Fallback to series name matching
- Data consistency checks

### Step 4: Verify API Functionality

Test that the API now uses series_id for lookups:

1. **Direct Series ID Lookup** (primary method):
   ```sql
   SELECT * FROM series_stats 
   WHERE series_id = 15 AND league_id = 4489
   ```

2. **Fallback Series Name Lookup** (backward compatibility):
   ```sql
   SELECT * FROM series_stats 
   WHERE series = 'Chicago 22' AND league_id = 4489
   ```

### Step 5: Update ETL Scripts (Already Implemented)

The ETL import script now:
- Gets `series_id` when inserting new `series_stats` records
- Includes `series_id` in INSERT statements
- Has fallback logic for series ID resolution

### Step 6: Monitor and Validate

After deployment:

1. **Check API Logs** for series_id usage:
   ```
   [DEBUG] Direct series_id lookup found 24 teams
   [DEBUG] Series name fallback found 0 teams
   ```

2. **Monitor Performance** - queries should be faster with integer FK lookups

3. **Verify Series Data** displays correctly on `/mobile/my-series` page

## Database Schema Changes

### New Column Added

```sql
ALTER TABLE series_stats ADD COLUMN series_id INTEGER REFERENCES series(id);
CREATE INDEX idx_series_stats_series_id ON series_stats(series_id);
```

### Updated Model Relationships

```python
class SeriesStats(Base):
    # Existing columns...
    series_id = Column(Integer, ForeignKey("series.id"))  # NEW
    
    # New relationship
    series_obj = relationship("Series", back_populates="series_stats")

class Series(Base):
    # New back-reference
    series_stats = relationship("SeriesStats", back_populates="series_obj")
```

## API Changes

### Before (String-based)
```python
# Fragile string matching
series_stats_query = """
    WHERE s.series = %s AND s.league_id = %s
"""
db_results = execute_query(series_stats_query, [resolved_series_name, user_league_id])
```

### After (ID-based with fallback)
```python
# Primary: Direct ID lookup
series_stats_query = """
    WHERE s.series_id = %s AND s.league_id = %s
"""
db_results = execute_query(series_stats_query, [user_series_id, user_league_id])

# Fallback: String matching (for backward compatibility)
if not db_results:
    # ... fallback to series name matching
```

## Benefits

1. **Reliability:** Eliminates series name mismatch issues
2. **Performance:** Integer FK lookups are faster than string comparisons
3. **Maintainability:** Proper relational database design
4. **Consistency:** Same pattern as existing `team_id` FK
5. **Future-proof:** Scales for multiple seasons per series

## Team ID Analysis

**Question:** Should we keep `team_id` in `series_stats`?

**Current Usage Analysis:**
- `team_id` is populated during ETL but **rarely used in SELECT queries**
- Most queries use `team` string matching: `s.team = t.team_name`
- Only used in population/migration scripts, not core application logic

**Recommendation:** Keep `team_id` for now because:
- Already populated and working
- Provides referential integrity
- May be useful for future team-specific queries
- No performance impact if unused in queries

## Rollback Plan

If issues arise, the changes can be safely rolled back:

1. **Revert API Service:**
   ```bash
   git checkout HEAD~1 app/services/api_service.py
   ```

2. **Remove Column** (if needed):
   ```sql
   ALTER TABLE series_stats DROP COLUMN IF EXISTS series_id;
   ```

3. **Revert Database Models:**
   ```bash
   git checkout HEAD~1 app/models/database_models.py
   ```

## Testing Checklist

- [ ] Migration applies successfully
- [ ] Series ID population completes with >90% success rate
- [ ] No orphaned series_id values
- [ ] API uses series_id for direct lookups
- [ ] Fallback to series name matching works
- [ ] `/mobile/my-series` page displays data correctly
- [ ] Performance improved (check query timing)
- [ ] ETL script works with series_id

## Future Improvements

After successful deployment, consider:

1. **Remove Series String Column** (Phase 2):
   - Once series_id is fully stable and tested
   - Will require updating all remaining string-based queries

2. **Optimize Team Lookups**:
   - Similar approach for team_id in other tables
   - Replace string-based team matching with ID lookups

3. **Add Series Validation**:
   - Ensure all new series_stats records have valid series_id
   - Add database constraints for data integrity

## Troubleshooting

### Series ID Population Issues

**Problem:** Low population rate (<90%)
**Solution:** Check series name format mismatches:
```sql
SELECT DISTINCT series FROM series_stats WHERE series_id IS NULL;
```

**Problem:** Orphaned series_id values  
**Solution:** Check series table for missing entries:
```sql
SELECT ss.series_id, COUNT(*) 
FROM series_stats ss 
LEFT JOIN series s ON ss.series_id = s.id 
WHERE s.id IS NULL 
GROUP BY ss.series_id;
```

### API Issues

**Problem:** No data returned from series_id lookup
**Solution:** Check user session data has valid series_id:
```sql
SELECT series_id FROM session_data WHERE user_id = ?;
```

**Problem:** Fallback not working
**Solution:** Verify series names match exactly in both tables:
```sql
SELECT DISTINCT ss.series, s.name 
FROM series_stats ss 
FULL OUTER JOIN series s ON ss.series = s.name 
WHERE ss.series IS NULL OR s.name IS NULL;
```

## Support

For issues or questions about this migration:
1. Check the test script output for specific failure details
2. Review API debug logs for lookup strategy used
3. Verify database foreign key relationships are intact
4. Contact the development team with specific error messages 