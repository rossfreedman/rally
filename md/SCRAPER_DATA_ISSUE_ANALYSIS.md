# Scraper Data Issue Analysis and Fix

**Date**: October 29, 2025  
**Issue**: Team names in match_scores don't match player team assignments

## Problem Summary

Team names in the `match_scores` table are being incorrectly assigned, causing players to appear on teams they don't belong to. This is causing:
- Incorrect court analysis displays
- Mixed match histories for teams
- Player statistics showing wrong team data

## Root Cause

**The issue is in the scraper, not the import process.**

### How the Scraper Works

1. The scraper extracts team names from HTML like this:
   - HTML text: `"Birchwood - 2 @ Wilmette PD - 2: 4 - 9"`
   - Scraper extracts: `"Wilmette PD"` + series number `"2"`
   - Result: `"Wilmette PD 2"`

2. The database organizes teams differently:
   - One club can have multiple series (e.g., Wilmette PD has Series 2, 26, 30, etc.)
   - The scraper creates separate team names for each series number
   - This creates mismatches between scraped team names and actual player assignments

### Evidence from Analysis

**In JSON file:**
```json
{
  "Home Team": "Wilmette PD 2",
  "Home Player 1 ID": "nndz-WkNPd3hMMzdoZz09",  // This is Mike Wilkins
  ...
}
```

**In database:**
- Player `nndz-WkNPd3hMMzdoZz09` (Mike Wilkins) is assigned to **team_id 59947** ("Wilmette 2")
- But match has **team_id 59385** ("Wilmette PD 26")

This creates a mismatch where the match data says "Wilmette PD 2" but the player actually belongs to a different team.

## Scope of the Problem

### On Staging/Production:

1. **Team Name Mismatches**: ~2,500 records
   - Home/away team names don't match their corresponding team_id's team_name
   - Fixed by syncing name strings with team_id

2. **Player-Team Assignment Issues**: ~4,000 records
   - Players appearing on wrong teams
   - Most are **legitimate substitutes** (same club, different series)
   - ~530 are **misassigned** (both players on different team than assigned)

### Pattern Analysis:

- **Legitimate cases**: Players playing as substitutes for different series within same club
  - Example: Skokie 25 player subbing for Skokie 23
  - These should NOT be "fixed"

- **Data errors**: Both players belong to different team entirely
  - Example: Wilmette PD 26 match has players from Wilmette 2
  - These should be fixed

## Solution

### Post-ETL Fix Script

Created: `data/etl/fix_team_names_from_players.py`

This script identifies and fixes misassigned matches by:
1. Loading player-team mappings from database
2. Finding matches where both players belong to a different team than assigned
3. **Safely skipping same-club cases** (legitimate substitutes)
4. Correcting the team_id and team_name for true misassignments

### Usage

```bash
# Dry run (see what would be fixed)
python data/etl/fix_team_names_from_players.py APTA_CHICAGO --dry-run

# Apply fixes
python data/etl/fix_team_names_from_players.py APTA_CHICAGO
```

### Example Output

```
Found 179 matches with misassigned teams

Sample corrections:
  Match 1803052 (2025-10-22):
    home side: Lifesport-Lshire 1 -> Winnetka 4
    Reason: Both players on Winnetka 4
  Match 1801513 (2025-10-15):
    home side: Midtown - Chicago 10 -> Midtown Chicago 10
    Reason: Both players on Midtown Chicago 10
```

**Note**: The script automatically skips legitimate substitutes (same club, different series)

### Important Notes

- **Temporary fix**: Manual fixes will be overwritten on next ETL run
- **Root cause**: The scraper needs to be fixed to resolve team names correctly
- **Run after ETL**: This script should be run after every ETL import
- **Smart filtering**: Script skips same-club cases (likely legitimate substitutes)
- **Typical results**: Found 179 misassigned matches in APTA_CHICAGO (down from 524 when excluding substitutes)

## Long-Term Solution

The scraper needs to be enhanced to:
1. Resolve team names from player data rather than HTML
2. Use database lookups for team names based on player assignments
3. Handle cross-series substitutions explicitly

This requires refactoring the scraper's team name resolution logic in:
- `data/etl/scrapers/apta_scrape_match_scores.py` (lines 1700-1758)
- Similar logic in other league scrapers

## Testing

- ✅ Tested on local database
- ✅ Tested on staging database  
- ✅ Applied fixes to production database
- ⚠️ **Needs verification** after next ETL run

## Files Modified

1. **Database fixes** (manual):
   - Staging: Fixed 17 misassigned matches for team 59385
   - Production: Fixed 17 misassigned matches for team 59385
   - Local: Fixed 14 misassigned matches total

2. **New files**:
   - `data/etl/fix_team_names_from_players.py` - Post-ETL fix script
   - `md/SCRAPER_DATA_ISSUE_ANALYSIS.md` - This document

## Next Steps

1. ✅ **Immediate**: Run fix script after each ETL import
2. ⚠️ **Short-term**: Monitor for recurring issues after next ETL
3. 🔧 **Medium-term**: Consider scraper refactoring for permanent solution
4. 📝 **Documentation**: Add post-processing step to ETL workflow guide

## Impact

- **Data integrity**: Manual fixes maintain correct team assignments
- **User experience**: Court analysis displays correctly
- **Maintenance**: Script must be run after each ETL import until scraper fixed
- **Risk**: Low - script skips legitimate cases automatically

