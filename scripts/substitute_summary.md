# Substitute Player Pattern Analysis

## Investigation Date
October 14, 2025

## Key Findings

### 1. The Problem
**You are 100% correct!** The issue is that the scraper creates **duplicate player records** when someone substitutes on a different team.

### 2. Scope of the Issue

| Metric | Count |
|--------|-------|
| Players with **(S)** suffix | **276** |
| tenniscores_player_ids with duplicates | **20+** |
| Example: Denise Siegel | 2 records (regular + (S)) |

### 3. Denise Siegel's Case (Confirmed)

| Record | Name | Series | Team | Is Her Team? |
|--------|------|--------|------|--------------|
| **Player ID 871012** | Denise Siegel | Series I | Tennaqua I | **✓ YES** (Her actual team) |
| **Player ID 960438** | Denise Siegel(S) | Series 17 | Tennaqua 17 | **✗ NO** (Substitute appearance) |

Both records have the **same tenniscores_player_id**: `cnswpl_WkM2eHhybndqUT09`

### 4. Root Cause

**The scraper** is creating a new player record with **(S)** suffix whenever a player substitutes on a different team, instead of:
- ✅ Using the existing player record
- ✅ Just recording the match with the correct tenniscores_player_id
- ✅ Having a match-level substitute flag

### 5. Impact

1. **Multiple player records** for the same person
2. **Split statistics** across records
3. **Session logic confusion** about which team to show
4. **User association issues** - may link to wrong record
5. **373+ users affected** by NULL tenniscores_player_id issue

### 6. Why the Fix Works

The fix we applied:
1. ✅ Set `users.tenniscores_player_id` (links to both records)
2. ✅ Set `user_contexts.team_id = 59318` (Series I)
3. ✅ Session logic now prioritizes Series I via PRIORITY 2

This works because the session query uses `user_contexts.team_id` as PRIORITY 2, which overrides the "most recent player ID" fallback that would select the (S) record.

### 7. Recommended Long-Term Fixes

#### A. IMMEDIATE (Clean up existing duplicates)
- Identify all (S) player records
- Verify they match a regular player record (same tenniscores_player_id)
- Delete (S) records and migrate their stats/matches to the main record
- Ensure matches still reference correct player via tenniscores_player_id strings

#### B. SHORT-TERM (Fix the scraper)
- Update scraper logic to NOT create new player records for substitutes
- If player has valid tenniscores_player_id, reuse existing player record
- Store substitute info at match level, not player level

#### C. LONG-TERM (Proper substitute tracking)
- Add `is_substitute` flag to match_scores table
- Track which team the player normally plays for
- Display substitute appearances separately in UI
- Maintain single player record per tenniscores_player_id

### 8. Which Scraper Creates (S) Records?

Need to check:
- `data/leagues/CNSWPL/scraper_match_scores.py` - likely culprit
- `data/leagues/NSTF/scraper_match_scores.py` - may have same pattern
- Other league scrapers

Look for code that appends "(S)" to player names when detecting substitute appearances.

## Conclusion

**Yes, you identified the root cause correctly!** Denise Siegel is NOT on two teams - she's on Series I and substituted on Series 17. The scraper incorrectly creates duplicate player records with (S) suffix instead of properly handling substitute appearances.

The immediate fix for Denise works, but there are:
- **276 players with (S) records** that should be cleaned up
- **20+ players with duplicate records** (some with 3-4 records!)
- **Scraper logic** that needs to be updated to prevent future duplicates

This is a systemic data quality issue that's been accumulating over time.

