# APTA Chicago Database Cleanup Strategy

## Executive Summary

The APTA Chicago database has significant discrepancies compared to the source JSON data:
- **713 extra players** in database (7,645 vs 6,932)
- **12 invalid series** not in JSON source
- **1 missing series** (Series 99) in database
- **575 missing clubs** in database (JSON has 615, DB has 57)
- **52 series with count discrepancies**

## Root Cause Analysis

### 1. Series Naming Inconsistencies
- **Legacy formats**: "10", "11", "13", "17", "32", "I" (numeric/letter only)
- **Cross-league contamination**: Series A-F from CNSWPL leaked into APTA
- **Missing series**: Series 99 not imported to database

### 2. Club Structure Differences
- **JSON**: 615 unique clubs (team-specific names like "Briarwood 38", "Exmoor 6")
- **Database**: 57 consolidated clubs (generic names like "Briarwood", "Exmoor")
- **Data normalization**: Database consolidated team-specific clubs into generic clubs

### 3. Player Count Discrepancies
- Most series have MORE players in database than JSON
- Suggests duplicate players or players from wrong series
- Only Series 1 and Series 7 SW have FEWER players in database

## Cleanup Strategy

### Phase 1: Remove Invalid Series (HIGH PRIORITY)
```sql
-- Remove 12 invalid series with 212 players
DELETE FROM players WHERE series_id IN (
    SELECT id FROM series WHERE name IN (
        '10', '11', '13', '17', '32', 'I',
        'Series A', 'Series B', 'Series C', 'Series D', 'Series E', 'Series F'
    ) AND league_id = 4783
);
```

### Phase 2: Add Missing Series
```sql
-- Add missing Series 99
INSERT INTO series (name, display_name, league_id) 
VALUES ('Series 99', 'Series 99', 4783);
```

### Phase 3: Fix Club Structure
**Option A: Match JSON exactly (Recommended)**
- Create 615 clubs to match JSON exactly
- Update player club assignments to use team-specific club names

**Option B: Keep current structure**
- Update JSON import to consolidate clubs during import
- Modify player matching to use generic club names

### Phase 4: Fix Player Counts
- Identify duplicate players across series
- Remove players not in JSON source
- Ensure 1:1 match with JSON data

### Phase 5: Data Validation
- Verify all 6,932 players from JSON exist in database
- Verify all 54 series from JSON exist in database
- Verify all 615 clubs from JSON exist in database

## Implementation Plan

### Step 1: Backup Current Data
```bash
# Create full backup before cleanup
pg_dump rally > backup_apta_before_cleanup_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Remove Invalid Series
- Remove 212 players from 12 invalid series
- Delete the invalid series records
- Verify removal

### Step 3: Add Missing Series
- Add Series 99 to database
- Import 135 players for Series 99

### Step 4: Fix Club Structure
- Create missing 558 clubs (615 - 57 existing)
- Update player club assignments to match JSON exactly

### Step 5: Fix Player Discrepancies
- Identify and remove 713 extra players
- Ensure exact match with JSON player counts per series

### Step 6: Validation
- Run comparison script to verify 1:1 match
- Test find-people-to-play functionality
- Verify series dropdown shows correct options

## Expected Results

After cleanup:
- **6,932 players** (exact match with JSON)
- **54 series** (exact match with JSON)
- **615 clubs** (exact match with JSON)
- **0 invalid series** in dropdown
- **Consistent data** across all APTA Chicago features

## Risk Mitigation

1. **Full database backup** before any changes
2. **Staged implementation** with validation at each step
3. **Rollback plan** if issues arise
4. **Testing** on staging environment first
5. **Monitoring** of user impact during cleanup

## Success Criteria

- [ ] Database has exactly 6,932 players
- [ ] Database has exactly 54 series (matching JSON)
- [ ] Database has exactly 615 clubs (matching JSON)
- [ ] Series dropdown shows only valid series
- [ ] All APTA Chicago features work correctly
- [ ] No user data loss or corruption

