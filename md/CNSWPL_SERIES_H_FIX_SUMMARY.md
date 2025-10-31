# CNSWPL Series H Stats Fix Summary

## Issue Reported
Kelly reported that the 10/20 match against Wilmette was not populating into the H series stats on Rally.

## Root Cause
The investigation revealed a data integrity issue where teams were incorrectly assigned to Series H in the `series_stats` table, even though they were actually assigned to sub-series `H(1)`, `H(2)`, or `H(3)` in the `teams` table.

### Specific Issues Found:
1. **Wilmette H(2)** was showing in Series H stats but is actually in Series `H(2)`
2. **Evanston H(1)** was showing in Series H stats but is actually in Series `H(1)`
3. **Evanston H(2)** was showing in Series H stats but is actually in Series `H(2)`
4. **Wilmette H(3)** was showing in Series H stats but is actually in Series `H(3)`

### The 10/20/2025 Match:
- **Match Found**: `Westmoreland H vs Wilmette H(2)` on 2025-10-20
- **Issue**: Wilmette H(2) stats were incorrectly showing in Series H instead of Series H(2)

## Solution Implemented
Created and ran `scripts/fix_cnswpl_series_h_stats.py` which:

1. **Identified all H-series** (Series H, H(1), H(2), H(3))
2. **Recalculated stats from match_scores** based on actual team series assignments
3. **Removed incorrect stats** from the database
4. **Inserted corrected stats** using the actual series assignments from the teams table

## Results
✅ **Fixed Stats for:**
- Series H: 5 teams (correctly assigned)
- Series H(1): 1 team
- Series H(2): 2 teams (including Wilmette H(2))
- Series H(3): 1 team

✅ **The 10/20/2025 match is now correctly reflected:**
- Westmoreland H stats appear in Series H
- Wilmette H(2) stats appear in Series H(2) (not Series H)

✅ **All team stats now match their actual series assignments**

## Verification
The fix script verified that all Series H stats are now correctly assigned - no more mismatches between the stats table and the actual team series assignments.

## Files Created
- `scripts/investigate_cnswpl_series_h.py` - Investigation script
- `scripts/fix_cnswpl_series_h_stats.py` - Fix script
- `scripts/verify_wilmette_h2_stats.py` - Verification script

## Next Steps
The fix has been applied to the local database. To apply to staging/production:

1. Test on staging first
2. Run: `python3 scripts/fix_cnswpl_series_h_stats.py`
3. Verify the results
4. Apply to production if staging looks good

