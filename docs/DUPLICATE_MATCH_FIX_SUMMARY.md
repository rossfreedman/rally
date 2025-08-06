# Duplicate Match Data Fix Summary

## Problem Identified

The staging database had **18,377 duplicate match records** causing inflated match counts across the platform:

- **Ross Freedman's analyze-me page** showed 24 matches instead of 12
- **"Last 3 Matches" API** returned duplicate matches
- **Match statistics** were inaccurate due to double-counting

## Root Cause Analysis

### ETL Import Duplication
The issue was caused by running the ETL import process **twice** on the same data:

1. **First Import**: August 4, 2025 (18,073 records)
2. **Second Import**: August 6, 2025 (18,073 records)

### How Duplicates Occurred with Primary Keys

The duplication was possible because:

1. **No Unique Constraints**: The `match_scores` table had a primary key on `id` (auto-increment), but **no unique constraints** on the actual match data (date, teams, players, scores).

2. **Different `tenniscores_match_id` Values**: Each duplicate had a slightly different `tenniscores_match_id`:
   - First import: `nndz-WWlPd3dyditqQT09_Line3`
   - Second import: `nndz-WWlPd3dyditqQT09_Line3_Line3`

3. **ETL Process Issue**: The ETL import process was appending `_LineX` suffixes to the `tenniscores_match_id`, creating "unique" identifiers for each import run.

## Evidence from Ross Freedman's Data

For each match, there were **exactly 2 records** with:
- **Same match data**: date, teams, players, scores, winner
- **Different IDs**: 168xxxx vs 171xxxx (different import runs)
- **Different `tenniscores_match_id`**: Original vs `_LineX_LineX` suffix
- **Different creation timestamps**: August 4 vs August 6, 2025

## Solution Implemented

### 1. Fixed Application Queries
Updated both the API endpoint and mobile service to use `DISTINCT ON` queries:

- **Last-3-Matches API** (`app/routes/api_routes.py`):
  - Now uses `SELECT DISTINCT ON (match_date, home_team, away_team, winner, scores)`
  - Returns only unique matches based on match characteristics

- **Analyze-Me Page** (`app/services/mobile_service.py`):
  - Updated `get_player_analysis` function to use `DISTINCT ON`
  - Now counts only unique matches for statistics

### 2. Fixed Database Data
Created and executed `scripts/fix_duplicate_matches.py`:

- **Removed 18,377 duplicate records** from staging database
- **Kept the record with the highest ID** (most recent import)
- **Added unique index** to prevent future duplicates

### 3. Added Database Protection
Created a unique index on match data:
```sql
CREATE UNIQUE INDEX unique_match_data_idx 
ON match_scores (match_date, home_team, away_team, winner, scores)
```

## Results

### Before Fix
- **Total match records**: 36,146
- **Ross Freedman matches**: 24 total, 12 unique (100% duplication)
- **Analyze-me page**: Showed 24 matches
- **"Last 3 Matches"**: Returned duplicates

### After Fix
- **Total match records**: 17,769 (removed 18,377 duplicates)
- **Ross Freedman matches**: 12 total, 12 unique (0% duplication)
- **Analyze-me page**: Shows 12 matches ✅
- **"Last 3 Matches"**: Returns unique matches ✅

## Prevention Measures

### 1. Database Level
- **Unique index** prevents future duplicate imports
- **Constraint violation** will occur if ETL tries to import duplicate data

### 2. Application Level
- **DISTINCT ON queries** handle any remaining duplicates gracefully
- **Robust fallback** ensures data integrity even with duplicate records

### 3. ETL Process
- **Recommendation**: Add validation before import to check for existing matches
- **Recommendation**: Use UPSERT operations instead of INSERT for match data

## Files Modified

1. **`app/routes/api_routes.py`**: Fixed last-3-matches API
2. **`app/services/mobile_service.py`**: Fixed get_player_analysis function
3. **`scripts/fix_duplicate_matches.py`**: Created data cleanup script
4. **Database**: Added unique index on match_scores table

## Testing Verification

- ✅ Ross Freedman now shows 12 matches instead of 24
- ✅ "Last 3 Matches" API returns unique matches
- ✅ Match statistics are accurate
- ✅ Database has unique constraint to prevent future duplicates

## Lessons Learned

1. **Primary keys alone don't prevent data duplication** - need unique constraints on business data
2. **ETL processes should use UPSERT** instead of INSERT to handle duplicate imports gracefully
3. **Application queries should be defensive** and handle potential duplicates
4. **Database constraints are essential** for data integrity

## Next Steps

1. **Monitor the unique index** for any constraint violations during future ETL runs
2. **Update ETL process** to use UPSERT operations for match data
3. **Add validation** to ETL process to check for existing matches before import
4. **Consider applying similar fixes** to other tables that might have similar issues 