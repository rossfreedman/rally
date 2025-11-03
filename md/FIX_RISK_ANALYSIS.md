# Fix Risk Analysis for APTA Scraper Team Name Resolution

## Overview
Proposed fix adds post-import resolution to correct ~2,500+ misassigned matches in APTA_CHICAGO league where scraper extracts wrong team names from HTML.

## Three Implementation Options

### Option A: Post-Import Resolution (RECOMMENDED)
**Approach**: Keep scraper as-is, add cleanup step after match insertion  
**File**: `data/etl/import/import_match_scores.py`

#### How It Works
```python
# After match inserted/updated
for each match:
    # Collect all player IDs for this match
    players = [home_p1, home_p2, away_p1, away_p2]
    
    # Look up which team each player belongs to in database
    team_votes = {}
    for player_id in players:
        team_id = lookup_player_team(player_id)
        team_votes[team_id] += 1
    
    # Use team with most votes
    correct_team_id = team_with_most_votes(team_votes)
    
    # Update match with correct team assignment
    if correct_team_id != current_team_id:
        UPDATE match_scores SET team_id = correct_team_id WHERE id = match_id
```

#### Risks

**🟢 LOW RISK**:
- ✅ Doesn't change scraper logic (proven stable)
- ✅ Non-destructive (only updates team_id, doesn't delete data)
- ✅ Reversible (can revert single file change)
- ✅ Testable in isolation before integration
- ✅ Works for all leagues (APTA, CNSWPL, NSTF)
- ✅ Players already exist in database when match is imported

**🟡 MEDIUM RISK**:
- ⚠️ **Performance**: Adds ~4 queries per match (4 player lookups)
  - **Mitigation**: Batch lookups, cache player-team mappings
  - **Impact**: ~10,000 extra queries for 2,500 matches = ~1-2 seconds
  
- ⚠️ **Substitute Players**: What if players from different teams?
  - **Current Logic**: Use majority rule (team with 3+ votes wins)
  - **Edge Case**: 2v2 split = both teams have 2 votes → what then?
  - **Risk**: Could assign to wrong team if equal votes
  - **Mitigation**: Fallback to current team_id if tie
  
- ⚠️ **Multi-team Players**: Player on multiple teams in same league
  - **Current Logic**: Uses `LIMIT 1` on player lookup
  - **Risk**: Could pick wrong team if player on Team A and Team B
  - **Mitigation**: Order by most recent activity, or prefer team_id with most matches

**🔴 POTENTIAL CRITICAL RISKS**:

1. **Performance Degradation**
   - **Risk**: If not batched, could add 30+ seconds to import
   - **Mitigation**: Use bulk lookups, CTEs, pre-caching
   - **Test**: Run on full dataset, measure impact

2. **Race Conditions**
   - **Risk**: If players haven't been imported yet when match resolves
   - **Likelihood**: LOW (import order is players → matches)
   - **Mitigation**: Validate player exists before lookup, skip if not found

3. **Historical Data Corruption**
   - **Risk**: Changes correct historical team assignments to wrong ones
   - **Example**: Team that actually switched mid-season
   - **Likelihood**: LOW with majority rule
   - **Mitigation**: Only update if confidence > 50%, log all changes

4. **False Positives**
   - **Risk**: Resolves "Wilmette PD 2" → "Wilmette PD 26" when wrong
   - **Likelihood**: VERY LOW (majority rule is conservative)
   - **Mitigation**: Don't update if confidence threshold not met

### Option B: Enhanced Team Lookup (ALTERNATIVE)
**Approach**: Improve existing `find_team_by_name_unified()` logic  
**File**: `data/etl/import/import_match_scores.py`, lines 144-183

#### How It Works
```python
def find_team_by_name_unified(cur, league_id, team_name):
    # Try 4 strategies in order:
    # 1. Exact match
    # 2. Parse club + series
    # 3. Partial matching
    # 4. NEW: Resolve from player data in match context
```

#### Risks

**🟢 LOW RISK**:
- ✅ Single-step resolution (cleaner)
- ✅ Happens at import time
- ✅ Existing function, just enhancing it

**🟡 MEDIUM RISK**:
- ⚠️ **Match Context Required**: Need match data (players, date) to resolve
  - **Problem**: Function only receives `team_name` string
  - **Solution**: Pass more context or use different approach

**🔴 HIGH RISK**:
- ❌ **Coupling**: Makes team lookup depend on match data
  - **Impact**: Breaks other code that calls this function
  - **Risk**: Team lookup used in schedules, stats, etc. without match context
  - **Mitigation**: Create separate function, keep old one for backward compatibility

**Verdict**: ❌ **NOT RECOMMENDED** - Too risky, breaks existing abstractions

### Option C: Fix Scraper at Source (HIGHEST RISK)
**Approach**: Modify scraper to extract correct team names  
**File**: `data/etl/scrapers/apta_scrape_match_scores.py`, lines 1700-1731

#### How It Works
```python
def _extract_apta_teams_and_score(self, soup):
    # Instead of: HTML "Wilmette PD - 2" → database "Wilmette PD 2"
    # Try: Extract players first, then resolve team from players
    players = extract_players(soup)
    team_name = resolve_team_from_players(players)
```

#### Risks

**🟢 LOW RISK**:
- ✅ Fixes at source
- ✅ Clean data from start
- ✅ No post-processing needed

**🟡 MEDIUM RISK**:
- ⚠️ **Timing**: Players might not be scraped yet
  - **Problem**: Scrape order is matches → players
  - **Workaround**: Two-pass scraping (players first, then matches)
  - **Impact**: Doubles scraping time

**🔴 HIGH RISK**:
- ❌ **Breaking Changes**: Modifies core scraper logic that's proven stable
  - **Impact**: Could break all future scrapes if bug introduced
  - **Risk**: Scraper is complex, hard to test all edge cases
  - **Mitigation**: Extensive testing, but still risky

- ❌ **HTML Dependency**: Assumes player data always available in match HTML
  - **Reality**: Some match pages might not have player lists
  - **Risk**: Fallback logic needed, adds complexity
  
- ❌ **League-Specific**: Works for APTA, might break CNSWPL/NSTF
  - **Risk**: Different leagues have different HTML structures
  - **Mitigation**: Conditional logic per league, more complex

**Verdict**: ❌ **NOT RECOMMENDED** - Too risky, modifies critical scraping logic

## Recommended Solution: Option A with Enhancements

### Enhanced Option A

```python
def resolve_match_team_assignments(cur, league_id=None, confidence_threshold=0.6):
    """
    Resolve team assignments for all matches based on player data.
    
    Args:
        confidence_threshold: Minimum fraction of players that must agree
                              (0.6 = 60%, meaning 3 out of 4 players)
    
    Returns:
        dict: {'updated': count, 'skipped': count, 'errors': count}
    """
    
    # Pre-cache all player-team mappings for performance
    player_teams_cache = build_player_teams_cache(cur, league_id)
    
    # Find matches that need resolution
    matches = find_matches_needing_resolution(cur, league_id)
    
    stats = {'updated': 0, 'skipped': 0, 'errors': 0}
    
    for match in matches:
        try:
            # Get team votes for this match
            team_votes = get_team_votes_for_match(match, player_teams_cache)
            
            if not team_votes:
                stats['skipped'] += 1
                continue
            
            # Calculate confidence
            top_team, top_votes = max(team_votes.items(), key=lambda x: x[1])
            total_votes = sum(team_votes.values())
            confidence = top_votes / total_votes if total_votes > 0 else 0
            
            # Only update if confidence is high enough
            if confidence >= confidence_threshold:
                update_match_team_assignment(cur, match['id'], top_team)
                stats['updated'] += 1
                logging.info(f"Match {match['id']}: Updated to team {top_team} "
                           f"(confidence: {confidence:.1%})")
            else:
                stats['skipped'] += 1
                logging.warning(f"Match {match['id']}: Skipped - low confidence "
                              f"({confidence:.1%} < {confidence_threshold:.1%})")
                
        except Exception as e:
            stats['errors'] += 1
            logging.error(f"Match {match['id']}: Error: {e}")
    
    return stats
```

### Risk Mitigation in Enhanced Option A

1. **Performance** ✅
   - Pre-cache all player-team mappings
   - Batch updates
   - Use CTEs for bulk operations
   - Target: <5 seconds for 10,000 matches

2. **Substitute Handling** ✅
   - Confidence threshold (60% = 3/4 players must agree)
   - Skip ambiguous matches (2v2 split)
   - Log all skips for manual review

3. **Multi-team Players** ✅
   - Use most common team for player
   - Cache by player_id → most_frequent_team_id
   - Fallback: Most recent team assignment

4. **Edge Cases** ✅
   - Missing players: Skip match resolution
   - Empty team_votes: Log and skip
   - All players belong to different teams: Skip (might be error in scraped data)

5. **Testing** ✅
   - Unit tests for vote calculation
   - Integration tests with sample data
   - Dry-run mode (log only, no updates)

## Specific Risks to Watch For

### Scenario 1: Mid-Season Team Change
**Risk**: Player actually switched teams mid-season  
**Current Fix**: Will use most frequent team (may be wrong for early-season matches)  
**Mitigation**: Acceptable - rare case, manual fix if needed

### Scenario 2: Substitute Player  
**Risk**: Player from Team A subs for Team B (legitimate)  
**Current Fix**: If 2 subs, will skip (good). If 1 sub, will change to sub's team (wrong)  
**Impact**: Could corrupt legitimate substitute data  
**Mitigation**: Need substitute detection logic or manual review

### Scenario 3: Players on Multiple Teams  
**Risk**: Player active on Team A and Team B in same league  
**Current Fix**: Uses most frequent team  
**Impact**: May pick wrong team  
**Mitigation**: Prefer team with most matches, or log for review

### Scenario 4: Season Transition
**Risk**: Player moved from Team A last season to Team B this season  
**Current Fix**: Will use most recent assignment  
**Impact**: Could incorrectly update last season's matches  
**Mitigation**: Only run on current season, or exclude old data

## Testing Requirements

### Before Production Deployment

**Must Test**:
1. ✅ Run on local full dataset
2. ✅ Verify no false positives (check sample of updates)
3. ✅ Measure performance impact (<10 seconds for full import)
4. ✅ Test on staging with production data subset
5. ✅ Verify substitute matches not corrupted
6. ✅ Check for multi-team player scenarios
7. ✅ Validate team name consistency

**Must Validate**:
1. ✅ Select 50 random matches before fix
2. ✅ Run fix
3. ✅ Manually verify all 50 are correct
4. ✅ Check 50 random "skipped" matches to ensure they're legitimately ambiguous

## Rollback Plan

**Simple Rollback**:
1. Revert `import_match_scores.py` changes
2. No need to restore data (fix is additive, can't lose existing data)

**Data Rollback** (if needed):
1. Have database backup before running fix
2. Or: Re-import from JSON files

## Recommendation

**Proceed with Enhanced Option A** with these safeguards:
- ✅ Confidence threshold (60%)
- ✅ Comprehensive logging
- ✅ Dry-run mode first
- ✅ Staged deployment (local → staging → production)
- ✅ Performance optimization (caching)
- ✅ Manual validation before production

**Estimated Risk Level**: 🟢 LOW with proper testing and safeguards






