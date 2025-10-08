# Investigation: Player ID nndz-WkM2L3c3bjdnUT09 (Wes Maher)

**Date:** September 30, 2025  
**Investigator:** AI Assistant  
**Issue:** Player appears on more than one team

---

## Summary

Player **Wes Maher** (tenniscores_player_id: `nndz-WkM2L3c3bjdnUT09`) has **2 records** in the database:

1. **Record 1 (DB ID: 872228)** - Tennaqua 20 at **Tennaqua** (Club ID: 8556)
   - Stats: 0-1 season, 28-22 career
   - Created: 2025-09-17
   - **Has actual match history** (1 match found)

2. **Record 2 (DB ID: 909405)** - Winnetka 99 B at **Winnetka** (Club ID: 8564)
   - Stats: 0-0 season, 0-0 career
   - Created: 2025-09-25
   - **No match history** (0 matches found)

**✅ VERDICT: This is VALID!** These are **different clubs**, so Wes Maher legitimately plays at 2 clubs (like Brett Pierson who plays at Valley Lo AND Tennaqua). The Winnetka 99 B appears to be a substitute roster where he's listed but hasn't played.

---

## Root Cause Analysis

### 1. Source Data Issue
The scraper found this player ID on **TWO different team rosters** on the source website:
- **Series 20:** Tennaqua 20 (active roster)
- **Series 99:** Winnetka 99 B (possibly substitute/inactive roster)

This is visible in the JSON data:
```
data/leagues/APTA_CHICAGO/temp/series_20.json - Found Wes on Tennaqua 20
data/leagues/APTA_CHICAGO/temp/series_99.json - Found Wes on Winnetka 99 B
```

### 2. ETL Import Behavior
The import process uses the following UPSERT conflict resolution:
```sql
ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id)
DO UPDATE SET ...
```

**The Key Issue:** The conflict constraint is based on the **combination** of:
- `tenniscores_player_id` (same: nndz-WkM2L3c3bjdnUT09)
- `league_id` (same: 4783 - APTA Chicago)
- `club_id` (DIFFERENT: 8556 Tennaqua vs 8564 Winnetka)
- `series_id` (DIFFERENT: 20364 Series 20 vs 42850 Series B)

Since the `club_id` and `series_id` are **different**, the UPSERT logic treats them as **two separate players** and creates **two records** instead of recognizing them as the same person.

### 3. Why This Happens
Possible reasons Wes appears on both rosters:
1. **Substitute player** - He may have subbed for Winnetka 99 B but never actually played a match
2. **Roster artifact** - The source website may show him on Winnetka's roster even though he's not active
3. **Data entry error** - Someone added him to Winnetka's roster by mistake on the source website

**Evidence:** He has **0 matches** for Winnetka 99 B, confirming he's not actually playing for that team.

---

## Database Details

### Player Records
```
Record 1:
  DB ID: 872228
  Name: Wes Maher
  League ID: 4783 (APTA Chicago)
  Team ID: 59602 (Tennaqua 20)
  Club ID: 8556 (Tennaqua)
  Series ID: 20364 (Series 20)
  Stats: 0-1 season, 28-22 career
  Created: 2025-09-17 02:14:54
  Active: True

Record 2:
  DB ID: 909405
  Name: Wes Maher
  League ID: 4783 (APTA Chicago)
  Team ID: 59984 (Winnetka 99 B)
  Club ID: 8564 (Winnetka)
  Series ID: 42850 (Series B)
  Stats: 0-0 season, 0-0 career
  Created: 2025-09-25 17:21:50
  Active: True
```

### Match History
```
Team ID 59602 (Tennaqua 20): 1 match
Team ID 59984 (Winnetka 99 B): 0 matches
```

---

## Impact Assessment

### Current Issues
1. **User Confusion:** If Wes logs in, he might see options for two different teams
2. **Data Integrity:** Stats are split across two records (28-22 career vs 0-0)
3. **Team Switching:** He might be able to "switch" to a team he doesn't actually play for
4. **Reports/Analytics:** His data might be counted twice in some aggregations

### Systems Affected
- Player login/registration flow
- Team switching functionality
- Player statistics and analytics
- Team rosters and listings

---

## Recommended Solutions

### Option 1: Deactivate the Duplicate (RECOMMENDED)
**Safest short-term fix:**
```sql
UPDATE players 
SET is_active = false 
WHERE id = 909405 AND tenniscores_player_id = 'nndz-WkM2L3c3bjdnUT09';
```

**Pros:**
- Immediate fix
- Preserves data for investigation
- Reversible if needed

**Cons:**
- Doesn't prevent future duplicates
- Requires manual intervention

### Option 2: Delete the Duplicate
**More aggressive approach:**
```sql
DELETE FROM players 
WHERE id = 909405 
  AND tenniscores_player_id = 'nndz-WkM2L3c3bjdnUT09'
  AND team_id = 59984;
```

**Pros:**
- Clean removal
- No residual duplicate data

**Cons:**
- Permanent deletion
- Doesn't prevent recurrence

### Option 3: Fix at Source (LONG-TERM SOLUTION)
**Address the root cause:**

1. **Enhance Scraper Logic:**
   - When a player appears on multiple rosters, only import the roster with actual match history
   - Add a "primary team" detection algorithm based on match participation
   - Flag multi-roster players for manual review

2. **Enhance ETL Logic:**
   - Before import, check if player already exists with same `tenniscores_player_id` + `league_id`
   - If exists, only update if new team has more recent match activity
   - Add duplicate detection and consolidation step

3. **Change Conflict Resolution:**
   Consider changing from:
   ```sql
   ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id)
   ```
   
   To:
   ```sql
   ON CONFLICT (tenniscores_player_id, league_id)
   ```
   
   **But this has implications:**
   - Would prevent players from legitimately switching teams mid-season
   - Might overwrite valid team changes
   - Needs careful thought about team movement scenarios

---

## Detection Query

To find **all players** with similar duplicate issues:

```sql
SELECT 
    tenniscores_player_id,
    first_name,
    last_name,
    COUNT(*) as record_count,
    STRING_AGG(DISTINCT team_name || ' (' || club_name || ')', ', ') as teams
FROM players p
JOIN teams t ON p.team_id = t.id
JOIN clubs c ON t.club_id = c.id
WHERE p.is_active = true
  AND p.league_id = 4783  -- APTA Chicago
GROUP BY tenniscores_player_id, first_name, last_name
HAVING COUNT(*) > 1
ORDER BY record_count DESC;
```

This will show **all players** in APTA Chicago who have multiple active records.

---

## ⚠️  CRITICAL UPDATE: SYSTEMIC ISSUE DISCOVERED

### Investigation Results

Initial analysis showed 1,460 players with multiple records. However, after understanding the business rule that **players CAN legitimately play for multiple teams at DIFFERENT clubs**, the breakdown is:

| Category | Players | Total Records | Status |
|----------|---------|---------------|---------|
| **INVALID - Same Club** | **705** | **1,420** | ❌ **Must fix** |
| **MIXED - Some Same Club** | **85** | **265** | ⚠️ **Partial fix** |
| **VALID - Different Clubs** | **421** | **878** | ✅ **Keep as-is** |

### The Real Problem: Same-Club Duplicates

**705 players have multiple records at the SAME club** - these are definitively invalid. A player cannot play for multiple teams at the same club simultaneously.

### Common INVALID Duplicate Patterns

1. **Team I/II Splits** - Players on "Team I" and "Team II" at same club (e.g., `Hinsdale PC I 11 SW` vs `Hinsdale PC II 11 SW`)
2. **Multiple Series at Same Club** - Same player in different series at same club (e.g., `Skokie 19` vs `Skokie 25` vs `Skokie 27`)
3. **Series 99/B/C at Same Club** - Substitute/overflow rosters creating ghost records with no match history
4. **Club Name Variations** - Same physical club, different spelling creating duplicate club_ids (e.g., `Midt Bannockburn` vs `Midt-Bannockburn`)

### Valid Multi-Club Players (Examples)

These are LEGITIMATE and should be kept:
- **Brett Pierson:** Valley Lo 4 + Tennaqua 6 (different clubs)
- **Wes Maher:** Tennaqua 20 + Winnetka 99 B (different clubs)

## Next Steps

### Immediate Actions (Staging Environment)

1. **✅ COMPLETED:** Identified same-club duplicate player records
   - 705 players with 1,420 total records at same club
   - 808 records to remove, 797 to keep

2. **✅ COMPLETED:** Created cleanup script
   - Script: `scripts/cleanup_same_club_duplicates.py`
   - Strategy: Keep record with most match history, then season matches, then career matches, then most recent
   - Supports both deactivation and deletion

3. **NEXT:** Test cleanup on staging environment
   ```bash
   # Preview changes (dry run)
   python3 scripts/cleanup_same_club_duplicates.py --dry-run
   
   # Execute cleanup (deactivate duplicates)
   python3 scripts/cleanup_same_club_duplicates.py --execute --deactivate
   ```

4. **AFTER STAGING:** Deploy to production if successful

### Long-Term Prevention (ETL Redesign)

**Note:** The current UPSERT conflict resolution `(tenniscores_player_id, league_id, club_id, series_id)` is actually CORRECT for the business rule that allows players at different clubs. The issue is same-club duplicates from the source data.

**Recommended ETL Enhancements:**

1. **Add same-club duplicate detection** as post-import validation step
   - After import, check for players with multiple records at same club_id
   - Keep record with most match history, deactivate others
   - Log all deduplication actions for review

2. **Improve team roster scraping**
   - Detect "Series 99/B/C/D" substitute pools and flag as secondary rosters
   - Only import substitute roster if player has actual matches for that team
   - Add metadata field: `is_substitute_roster` boolean

3. **Add data quality checks**
   - Validate that scraped team assignments match actual match participation
   - Flag discrepancies for manual review
   - Alert when player appears on >3 teams in same league

4. **Club name normalization**
   - Standardize club names before creating club records (e.g., "Midt Bannockburn" vs "Midt-Bannockburn")
   - Use fuzzy matching to detect club name variations
   - Consolidate duplicate clubs with different spellings

---

## Questions for User

1. **✅ ANSWERED:** Do players ever play for multiple teams simultaneously?
   - YES - Players can play for teams at DIFFERENT clubs (e.g., Brett Pierson at Valley Lo + Tennaqua)
   - NO - Players CANNOT play for multiple teams at the SAME club

2. **Should we execute the cleanup on staging?**
   - Ready to deactivate 808 duplicate records
   - Affects 705 players with same-club duplicates
   - Keeps the record with most match history

3. **Deactivate vs Delete?**
   - **Deactivate (Recommended):** Sets `is_active = false`, preserves data for audit
   - **Delete:** Permanently removes records

4. **Should we add ETL post-import validation?**
   - Automatically detect and fix same-club duplicates after each import
   - Prevent recurrence without manual intervention

---

## Files Involved

- **Source Data:** `data/leagues/APTA_CHICAGO/players.json`
- **Scraped Data:** `data/leagues/APTA_CHICAGO/temp/series_20.json`, `data/leagues/APTA_CHICAGO/temp/series_99.json`
- **ETL Script:** `data/etl/import/import_players.py` (lines 612-630)
- **Database:** `players` table, records 872228 and 909405
