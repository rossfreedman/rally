# Scraper Team Name Resolution Fix Plan

## Executive Summary

**Root Cause**: The APTA scraper constructs team names from HTML strings (e.g., "Wilmette PD - 2" → "Wilmette PD 2") which don't match actual database team names (e.g., "Wilmette PD 26"). This causes ~4,000+ misassigned matches and team name inconsistencies that get overwritten on every ETL run.

**Impact**: Manual database fixes are temporary and will be overwritten on next ETL import.

**Solution**: Update scraper to resolve correct team names from player data instead of HTML text.

## Detailed Problem Analysis

### The Scraper Logic (Current - BROKEN)

**File**: `data/etl/scrapers/apta_scrape_match_scores.py`, lines 1700-1731

```python
def _extract_apta_teams_and_score(self, soup) -> dict:
    # Parse "Exmoor - 20 @ Valley Lo - 20: 4 - 9"
    if ' @ ' in text:
        parts = text.split(' @ ')
        away_part = parts[0].strip()  # "Birchwood - 2"
        home_part = parts[1].strip()  # "Wilmette PD - 2"
        
        # ❌ PROBLEM: Strip numbers, lose context
        away_team = re.sub(r'\s*-\s*\d+.*$', '', away_part).strip()  # "Wilmette PD"
        home_team = re.sub(r'\s*-\s*\d+.*$', '', home_part).strip()  # "Wilmette PD"
        
        # ❌ PROBLEM: Extract series number incorrectly
        series_match = re.search(r'-\s*(\d+)', text)
        if series_match:
            series_num = series_match.group(1)  # "2" from "Wilmette PD - 2"
            home_team = f"{home_team} {series_num}"  # "Wilmette PD 2"
```

**What's Wrong**:
- Takes "Wilmette PD - 2" from HTML
- Creates "Wilmette PD 2" as team name
- In database, players belong to "Wilmette PD 26" (actual team)
- Creates 11 matches with wrong team assignment

### Evidence from Data

**JSON shows**: 
- "Wilmette PD 2": 11 matches with player `nndz-WkNPd3hMMzdoZz09` (Mike Wilkins)
- "Wilmette PD 26": 16 matches with players correctly assigned

**Database shows**:
- Player Mike Wilkins (team_id 59947): on "Wilmette 2", not "Wilmette PD 26"
- Player Mike Wilkins appears in matches labeled "Wilmette PD 2"
- Both "Wilmette PD 2" and "Wilmette PD 26" exist as separate teams in JSON
- Database has teams: "Wilmette PD 26" (id 59385), "Wilmette 2" (id 59947)

### Root Cause Conclusion

The scraper is using HTML strings to construct team names, but:
1. HTML uses series numbers from source website (e.g., "2", "26")
2. Database has different team organization (one club, multiple series)
3. Player assignments don't match scraper-inferred team names
4. Results in: **~4,000+ misassigned matches** across all teams

## Proposed Solution

### Strategy: Resolve Team Names from Player Data

Instead of constructing team names from HTML, resolve them using existing player-team relationships.

### Implementation Options

#### Option A: Post-Import Resolution (Recommended)
**File**: `data/etl/import/import_match_scores.py`

After match insertion, update team assignments based on player data:

```python
def resolve_team_from_players(cur, match_id, league_id):
    """
    Resolve correct team_id for a match based on player assignments.
    Returns team_id that majority of players belong to.
    """
    # Get all players for this match
    players = get_match_players(cur, match_id)
    
    # Count which team each player belongs to
    team_counts = {}
    for player_id in players:
        team_id = get_player_team(cur, player_id, league_id)
        team_counts[team_id] = team_counts.get(team_id, 0) + 1
    
    # Return team with most players
    return max(team_counts.items(), key=lambda x: x[1])[0] if team_counts else None

# Call after INSERT or UPDATE
correct_team_id = resolve_team_from_players(cur, match_id, league_id)
if correct_team_id:
    update_match_team_assignment(cur, match_id, correct_team_id)
```

**Pros**:
- Minimal changes to scraper
- Works for all leagues
- Backward compatible

**Cons**:
- Two-step process (insert then update)
- Requires players to exist first

#### Option B: Use Existing Team Lookup with Better Logic
**File**: `data/etl/import/import_match_scores.py`, lines 144-183

Enhance `find_team_by_name_unified()` to handle these cases:

```python
def find_team_by_name_unified(cur, league_id: int, team_name: str) -> Optional[int]:
    # Strategy 1: Exact match
    # Strategy 2: Parse and match by club + series
    # Strategy 3: Partial matching
    # ✅ NEW Strategy 4: Resolve from player data
    resolved_team = resolve_team_from_match_players(cur, league_id, team_name)
    if resolved_team:
        return resolved_team
```

**Pros**:
- Single-step resolution
- More robust matching

**Cons**:
- Requires match context
- More complex logic

#### Option C: Fix Scraper to Extract Correct Data
**File**: `data/etl/scrapers/apta_scrape_match_scores.py`

Instead of stripping series numbers, extract full team context from HTML:

```python
def _extract_apta_teams_and_score(self, soup) -> dict:
    # Instead of: "Wilmette PD - 2" → "Wilmette PD 2"
    # Extract: "Wilmette PD - 2" → resolve via player lookup
    
    # Get players first
    players = extract_players(soup)
    
    # Resolve team from players
    team_name = resolve_team_from_players_in_match(players)
    if not team_name:
        # Fallback to HTML extraction
        team_name = extract_team_name_from_html(soup)
```

**Pros**:
- Fixes at source
- Clean data from start

**Cons**:
- Requires player data to be available
- May need additional HTML parsing

## Recommended Approach

**Hybrid: Option A (Post-Import Resolution)**

1. **Keep scraper as-is** (minimal disruption)
2. **Add resolution step** in `import_match_scores.py` after INSERT/UPDATE
3. **Create helper function** `resolve_match_team_assignments(cur)` that:
   - Finds all matches with misassigned teams
   - Resolves correct team_id from player data
   - Updates match_scores with correct team_id and team_name

**Implementation Steps**:

1. Create `resolvers/match_team_resolver.py` module
2. Add `resolve_match_team_assignments()` function
3. Integrate into `import_match_scores.py` post-import
4. Test on local database
5. Deploy to staging
6. Verify results
7. Deploy to production

## Files to Modify

### New Files
- `data/etl/resolvers/__init__.py`
- `data/etl/resolvers/match_team_resolver.py`

### Modified Files
- `data/etl/import/import_match_scores.py`
- Add call to resolver after batch import

## Testing Strategy

1. **Local Testing**:
   - Run import on local database
   - Verify match assignments correct
   - Check team name consistency

2. **Staging Validation**:
   - Import sample data
   - Compare before/after assignments
   - Verify player-team relationships

3. **Production Rollout**:
   - Backup production database
   - Run import with new logic
   - Validate results
   - Monitor for issues

## Expected Outcomes

✅ No more "Wilmette PD 2" vs "Wilmette PD 26" conflicts  
✅ Matches correctly assigned to teams based on player data  
✅ Team name strings match actual database team names  
✅ ~4,000 misassigned matches auto-corrected on next import  
✅ Future imports maintain data consistency  

## Rollback Plan

If issues arise:
1. Revert `import_match_scores.py` changes
2. Run existing ETL to restore previous state
3. Re-export JSON files if needed

## Timeline Estimate

- **Development**: 4-6 hours
- **Testing**: 2-3 hours  
- **Deployment**: 1 hour
- **Total**: 7-10 hours

## Questions to Resolve

1. Should we fix historical data or only new imports?
   - **Recommendation**: Fix historical data by running resolution on existing database

2. How to handle multi-team players (substitutes)?
   - **Recommendation**: Use majority rule (team with most appearances in match)

3. What about matches with no players assigned?
   - **Recommendation**: Leave team assignment as-is from HTML

4. Should this run on every import or only when needed?
   - **Recommendation**: Always run during import for consistency






