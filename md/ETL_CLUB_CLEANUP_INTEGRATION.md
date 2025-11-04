# ETL Club Cleanup Integration

## Overview
The post-ETL club cleanup script has been integrated into all APTA cron runner scripts to automatically consolidate duplicate clubs after each ETL import.

## Script Location
- **Path**: `data/etl/import/post_etl_club_cleanup.py`
- **Location**: ETL import directory (alongside other import scripts)

## Integration Points

### 1. `data/cron/apta_pti_runner.py`
- **Purpose**: Scrapes and imports PTI player data only
- **Steps**: 3 steps total
  1. Scrape APTA Players
  2. Import APTA Players
  3. **Post-ETL Club Cleanup** ← NEW

### 2. `data/cron/apta_scraper_runner_all.py`
- **Purpose**: Scrapes and imports all APTA data (players, scores, stats)
- **Steps**: 7 steps total
  1. Scrape APTA Players
  2. Import APTA Players
  3. Scrape APTA Match Scores
  4. Import APTA Match Scores
  5. Scrape APTA Series Stats
  6. Import APTA Series Stats
  7. **Post-ETL Club Cleanup** ← NEW

### 3. `data/cron/apta_scraper_runner_stats_scores.py`
- **Purpose**: Scrapes and imports scores and stats only (no players)
- **Steps**: 5 steps total
  1. Scrape APTA Match Scores
  2. Import APTA Match Scores
  3. Scrape APTA Series Stats
  4. Import APTA Series Stats
  5. **Post-ETL Club Cleanup** ← NEW

## What It Does

After each ETL import completes, the cleanup script:
1. Checks for duplicate clubs defined in `CLUB_CONSOLIDATION_MAPPINGS`
2. Consolidates all data from duplicate clubs to target clubs
3. Deletes duplicate clubs after consolidation
4. Verifies no orphaned records remain

## Current Mappings

- `"Lifesport Lshire"` → `"Lifesportlshire"`

## Benefits

1. **Automatic**: Runs automatically after every ETL import
2. **Idempotent**: Safe to run multiple times (won't break if no duplicates exist)
3. **Prevents regressions**: Ensures duplicate clubs don't persist after imports
4. **SMS notifications**: Included in the cron job notification flow

## Testing

The cleanup script has been tested and verified:
- ✅ Dry run mode works correctly
- ✅ Live mode consolidates successfully
- ✅ Handles cases where no duplicates exist
- ✅ Verifies consolidation before deleting source club

## Notes

- The cleanup runs with `--live` flag in cron jobs (automatic execution)
- If cleanup fails, the cron job will report it via SMS notification
- The cleanup step is non-blocking for the ETL process (continues even if cleanup finds no duplicates)

