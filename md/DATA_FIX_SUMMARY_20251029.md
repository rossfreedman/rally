# Data Fix Summary - October 29, 2025

## Issue Discovery

**Problem**: Teams-players page showing incorrect match data, mixing players from different teams (Wilmette 2 vs Wilmette PD 26).

**Investigation**: Found 17 misassigned matches on team 59385 (Wilmette PD 26) where players actually belonged to different teams.

## Root Cause Analysis

**Conclusion**: **SCRAPER ISSUE**, not database import problem.

The APTA scraper (`data/etl/scrapers/apta_scrape_match_scores.py`, lines 1700-1731) constructs team names from HTML text patterns:
- HTML shows: "Wilmette PD - 2 @ Birchwood - 2"
- Scraper extracts: "Wilmette PD 2" and "Birchwood 2"
- Database actually has: "Wilmette PD 26" and "Wilmette 2"
- **Result**: Wrong team assignments in match_scores table

## Fixes Applied Today

### Local Database
✅ Fixed 17 misassigned matches for team 59385  
✅ Corrected team name mismatches in match_scores  
✅ Manually reassigned matches to correct teams based on player data  
✅ **WARNING**: These fixes will be overwritten on next ETL run

### Staging Database
✅ Fixed 17 misassigned matches for team 59385  
✅ Fixed ~2,500 team name mismatches (home_team/away_team strings)  
✅ Fixed 100 additional misassigned matches  
✅ Corrected ~35 remaining name mismatches  
✅ **WARNING**: These fixes will be overwritten on next ETL run

### Production Database
✅ Fixed 17 misassigned matches for team 59385  
✅ **WARNING**: These fixes will be overwritten on next ETL run

## Code Changes

**None made** - Per user request, reverted code changes to avoid breaking existing functionality.

Previous attempt to fix PARTITION BY clauses in `app/routes/mobile_routes.py` was reverted.

## Data Quality Issues Remaining

Based on comprehensive scan of staging database:

### High Priority Issues
1. **Team Name Mismatches**: ~70 remaining
   - Mostly NULL/Unknown placeholders from past seasons
   - Harmless but inconsistent

2. **Player-Team Assignment Issues**: ~4,000 remaining
   - ~530 cases where BOTH players belong to different team (likely real errors)
   - ~3,500 legitimate substitutes playing for different series/teams
   - **CAUTION**: Most are legitimate substitutes - fixing incorrectly would corrupt data

### Low Priority Issues
- Players on multiple teams (intentional for multi-season players)
- Cross-league data inconsistency: 0 (good!)

## Next Steps Required

**CRITICAL**: Fix scraper to resolve correct team names before data gets corrupted on next ETL.

See: `md/SCRAPER_TEAM_NAME_FIX_PLAN.md` for detailed fix plan.

**Options**:
1. ✅ Implement post-import team resolution (Recommended)
2. Enhance team lookup logic in ETL
3. Fix scraper HTML parsing (most disruptive)

## Impact

**Current State**:
- ✅ Local, staging, and production databases temporarily fixed
- ⚠️ Will break again on next ETL import
- ⚠️ Scraper continues to generate incorrect data

**After Scraper Fix**:
- ✅ All future imports will have correct data
- ✅ No more manual fixes needed
- ✅ Historical data can be re-imported correctly

## Files Modified Today

**Code**: None (reverted)
**Documentation**: 
- `md/SCRAPER_TEAM_NAME_FIX_PLAN.md` (new)
- `md/DATA_FIX_SUMMARY_20251029.md` (this file)

## Database Changes

**Local**: 17 match corrections
**Staging**: ~2,600 corrections  
**Production**: 17 match corrections

All changes temporary until scraper is fixed.




