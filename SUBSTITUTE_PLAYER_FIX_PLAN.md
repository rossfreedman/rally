# Substitute Player Duplicate Fix Plan

## Status: Ready to Execute

## Problem Summary

The system creates **duplicate player records** when players substitute on different teams:
- **276 (S) player records** exist in production
- **106 matched pairs** (player has both regular + (S) record)
- **170 unmatched** (S) records (substitutes without regular team)

### Example: Denise Siegel
- **Player ID 871012**: Denise Siegel → Series I, Tennaqua I (her actual team)
- **Player ID 960438**: Denise Siegel(S) → Series 17, Tennaqua 17 (substitute appearance)
- Both share same `tenniscores_player_id`: `cnswpl_WkM2eHhybndqUT09`

## Root Cause

The scraper creates new player records with "(S)" suffix when it encounters substitutes, instead of:
✅ Reusing the existing player record
✅ Tracking substitute status at the match level

## Solution: Two-Part Fix

### Part 1: Clean Up Existing Data ✅ READY

**Script:** `/scripts/cleanup_substitute_duplicates.py`

**What it does:**
1. Identifies all 276 (S) player records
2. Matches them with their regular counterparts (106 pairs)
3. Updates `user_contexts` to point to regular player's team
4. Marks (S) records as `is_active = false` (preserves data for rollback)

**Dry-run completed successfully:**
- 106 pairs will be cleaned up
- 170 unmatched (S) players will remain (may be legitimate substitute-only players)

**To execute:**
```bash
python3 scripts/cleanup_substitute_duplicates.py --env production --live
```

### Part 2: Prevent Future Duplicates ✅ READY

**Location:** CNSWPL scraper already has the fix!

**File:** `data/etl/scrapers/cnswpl/cnswpl_scrape_players_detailed.py`  
**Line 1330:**
```python
if '(S↑)' in player_name or '(S)' in player_name:
    print(f"         ⚠️ Skipping sub player: {player_name}")
    continue
```

**Status:** ✅ Scraper is already filtering out (S) players!

**Why we still have (S) records:**
- Old scraped data was imported before the fix was added
- The cleanup script will remove these legacy records

## Execution Plan

### Step 1: Backup (CRITICAL)
```bash
python cb.py --env production
```

### Step 2: Run Cleanup on Production
```bash
cd /Users/rossfreedman/dev/rally
source venv/bin/activate
python3 scripts/cleanup_substitute_duplicates.py --env production --live
```

### Step 3: Verification
- Check that (S) records are marked inactive
- Verify user_contexts point to correct teams
- Test login for affected users (like Denise)

### Step 4: Monitor
- Watch for any user reports about missing teams
- Check that new scrapes don't create (S) records

## Benefits

1. **106 users** will have cleaner player records
2. **Session logic** will no longer be confused by duplicate records  
3. **Statistics** won't be split across multiple player records
4. **Future scrapes** won't create new (S) duplicates (already fixed in scraper)

## Rollback Plan

If issues arise:
1. Revert `is_active` flag for (S) players:
   ```sql
   UPDATE players SET is_active = true 
   WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)';
   ```
2. Restore from backup created in Step 1

## Technical Notes

### Why Mark Inactive Instead of Delete?
- Preserves data integrity
- Allows for easy rollback
- Maintains foreign key relationships
- Can be permanently deleted later if needed

### What About the 170 Unmatched?
These are players who:
- Only have substitute appearances (no regular team)
- OR have a naming mismatch preventing automatic matching

These will remain active and can be manually reviewed later if needed.

## Ready to Execute?

✅ Dry-run completed successfully  
✅ Scraper fix confirmed in place  
✅ Rollback plan documented  
✅ Backup procedure identified  

**Recommendation:** Execute during low-traffic period (evening/night)

