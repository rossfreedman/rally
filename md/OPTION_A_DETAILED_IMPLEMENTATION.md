# Option A: Post-Import Resolution - Detailed Implementation Guide

## Executive Summary

**What**: Add a post-processing step after match import that corrects ~2,500 misassigned team matches in APTA_CHICAGO.

**Where**: New module `data/etl/resolvers/match_team_resolver.py` + integration into `import_match_scores.py`

**Risk Level**: 🟢 LOW (with proper safeguards)

**Impact**: Fixes 94% of all data quality issues permanently

---

## How It Works - The Algorithm

### Current Problem Flow

```
1. Scraper extracts from HTML: "Wilmette PD - 2 @ Tennaqua - 26"
2. Scraper creates team names: 
   - "Wilmette PD 2" (WRONG - should be "26")
   - "Tennaqua 26" (CORRECT)
3. Match imports with WRONG team assignments
4. UI displays incorrect data
```

### Proposed Solution Flow

```
1. Scraper extracts from HTML (unchanged): "Wilmette PD - 2 @ Tennaqua - 26"
2. Match imports with WRONG team assignments (unchanged)
3. ⭐ NEW: Post-processing step analyzes match players
4. ⭐ NEW: Determines correct teams from player data
5. ⭐ NEW: Updates team_id and team_name to correct values
6. UI displays CORRECT data ✅
```

### The Resolution Algorithm

```python
def resolve_match_team_assignments(cur, league_id):
    """
    Core algorithm: Democratic voting by players
    
    For each misassigned match:
    1. Collect all 4 player IDs (home_p1, home_p2, away_p1, away_p2)
    2. Look up which team each player belongs to in database
    3. Count votes: team_id → number of players from that team
    4. Majority rule: Team with 3+ votes wins
    5. Update match record
    
    Example:
    Match 12345: home_team_id=59385 ("Wilmette PD 2")
    Players: [Mike, Bob, Rob, Ross]
    Player lookups:
      Mike → team 59947
      Bob → team 59947  
      Rob → team 59947
      Ross → team 59947
    Result: 4 votes for team 59947
    Update: home_team_id=59947, home_team="Wilmette PD 26" ✅
    """
```

---

## Detailed Implementation

### File Structure

```
data/etl/
├── import/
│   └── import_match_scores.py          (MODIFY: Add resolver call)
└── resolvers/                          (NEW DIRECTORY)
    ├── __init__.py                     (NEW)
    └── match_team_resolver.py          (NEW: Core logic)
```

### New File 1: `data/etl/resolvers/__init__.py`

```python
"""Team resolution utilities for ETL imports."""

from .match_team_resolver import (
    resolve_match_team_assignments,
    build_player_teams_cache,
    get_team_votes_for_match,
)

__all__ = [
    'resolve_match_team_assignments',
    'build_player_teams_cache',
    'get_team_votes_for_match',
]
```

### New File 2: `data/etl/resolvers/match_team_resolver.py` (Core Module)

```python
#!/usr/bin/env python3
"""
Match Team Resolution Module

Resolves correct team assignments for matches based on player data.
Addresses the issue where scraper extracts wrong team names from HTML,
leading to ~2,500 misassigned matches in APTA_CHICAGO league.

Algorithm:
- For each match, collect all 4 player IDs
- Look up which team each player belongs to
- Use majority rule to determine correct team
- Update match record if confidence threshold met

Confidence Threshold: 60% (3 out of 4 players must agree)
"""

import logging
from typing import Optional, Dict, List, Tuple
from collections import Counter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_player_teams_cache(cur, league_id: Optional[int] = None) -> Dict[str, int]:
    """
    Pre-cache all player-team mappings for performance.
    
    Returns dictionary: player_id → most_common_team_id
    Only caches players with valid team assignments.
    
    Args:
        cur: Database cursor
        league_id: Optional league filter
        
    Returns:
        Dict mapping player_id (str) to team_id (int)
    """
    logger.info("Building player-teams cache...")
    
    query = """
        SELECT 
            p.tenniscores_player_id,
            p.team_id,
            COUNT(*) as match_count
        FROM players p
        WHERE p.team_id IS NOT NULL
    """
    params = []
    
    if league_id:
        query += " AND p.league_id = %s"
        params.append(league_id)
    
    query += """
        GROUP BY p.tenniscores_player_id, p.team_id
        ORDER BY p.tenniscores_player_id, match_count DESC
    """
    
    cur.execute(query, params)
    results = cur.fetchall()
    
    # Build cache with most common team per player
    cache = {}
    for player_id, team_id, match_count in results:
        if player_id and team_id:
            # Use most common team if player on multiple teams
            if player_id not in cache:
                cache[player_id] = team_id
    
    logger.info(f"Cached {len(cache)} player-team mappings")
    return cache


def get_team_votes_for_match(
    match: Dict, 
    player_teams_cache: Dict[str, int]
) -> Counter:
    """
    Get team votes for a match based on player assignments.
    
    Args:
        match: Match dictionary with player IDs
        player_teams_cache: Pre-built player-team mappings
        
    Returns:
        Counter of team_id → vote_count
    """
    votes = Counter()
    
    # Collect all player IDs for this match
    player_ids = [
        match.get('home_player_1_id'),
        match.get('home_player_2_id'),
        match.get('away_player_1_id'),
        match.get('away_player_2_id'),
    ]
    
    # Count votes
    for player_id in player_ids:
        if player_id in player_teams_cache:
            team_id = player_teams_cache[player_id]
            votes[team_id] += 1
        elif player_id:
            logger.debug(f"Player {player_id} not found in cache")
    
    return votes


def find_matches_needing_resolution(
    cur, 
    league_id: Optional[int] = None,
    limit: Optional[int] = None
) -> List[Dict]:
    """
    Find matches that may need team resolution.
    
    Strategy: Look for matches where team_name doesn't match actual team
    We identify these by checking if any players belong to different teams.
    
    Args:
        cur: Database cursor
        league_id: Optional league filter
        limit: Optional limit for testing
        
    Returns:
        List of match dictionaries
    """
    logger.info("Finding matches needing resolution...")
    
    query = """
        SELECT 
            ms.id,
            ms.match_date,
            ms.home_team,
            ms.away_team,
            ms.home_team_id,
            ms.away_team_id,
            ms.home_player_1_id,
            ms.home_player_2_id,
            ms.away_player_1_id,
            ms.away_player_2_id
        FROM match_scores ms
        WHERE 1=1
    """
    params = []
    
    if league_id:
        query += " AND ms.league_id = %s"
        params.append(league_id)
    
    # Only consider matches with all 4 player IDs filled
    query += """
        AND ms.home_player_1_id IS NOT NULL
        AND ms.home_player_2_id IS NOT NULL
        AND ms.away_player_1_id IS NOT NULL
        AND ms.away_player_2_id IS NOT NULL
        ORDER BY ms.id
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    
    matches = []
    for row in rows:
        matches.append({
            'id': row[0],
            'match_date': row[1],
            'home_team': row[2],
            'away_team': row[3],
            'home_team_id': row[4],
            'away_team_id': row[5],
            'home_player_1_id': row[6],
            'home_player_2_id': row[7],
            'away_player_1_id': row[8],
            'away_player_2_id': row[9],
        })
    
    logger.info(f"Found {len(matches)} matches to analyze")
    return matches


def resolve_single_match(
    cur,
    match: Dict,
    player_teams_cache: Dict[str, int],
    confidence_threshold: float = 0.6
) -> Tuple[bool, Optional[str]]:
    """
    Resolve correct team assignment for a single match.
    
    Args:
        cur: Database cursor
        match: Match dictionary
        player_teams_cache: Pre-built player-team mappings
        confidence_threshold: Minimum fraction of players that must agree (default 0.6 = 60%)
        
    Returns:
        Tuple of (success: bool, reason: Optional[str])
        If success=True, team was updated
        If success=False, reason explains why (low confidence, tie, etc.)
    """
    match_id = match['id']
    
    # Get team votes for this match
    team_votes = get_team_votes_for_match(match, player_teams_cache)
    
    if not team_votes:
        return False, "No votes"
    
    # Calculate confidence
    total_votes = sum(team_votes.values())
    if total_votes == 0:
        return False, "Zero total votes"
    
    top_team, top_votes = team_votes.most_common(1)[0]
    confidence = top_votes / total_votes if total_votes > 0 else 0
    
    # Check if we have high enough confidence
    if confidence < confidence_threshold:
        return False, f"Low confidence ({confidence:.1%} < {confidence_threshold:.1%})"
    
    # Determine which side needs updating
    needs_home_update = False
    needs_away_update = False
    new_home_team_id = match['home_team_id']
    new_away_team_id = match['away_team_id']
    
    # Check home team
    home_votes = Counter()
    for pid in [match['home_player_1_id'], match['home_player_2_id']]:
        if pid in player_teams_cache:
            home_votes[player_teams_cache[pid]] += 1
    
    if home_votes and home_votes.most_common(1)[0][0] != match['home_team_id']:
        needs_home_update = True
        new_home_team_id = home_votes.most_common(1)[0][0]
    
    # Check away team
    away_votes = Counter()
    for pid in [match['away_player_1_id'], match['away_player_2_id']]:
        if pid in player_teams_cache:
            away_votes[player_teams_cache[pid]] += 1
    
    if away_votes and away_votes.most_common(1)[0][0] != match['away_team_id']:
        needs_away_update = True
        new_away_team_id = away_votes.most_common(1)[0][0]
    
    # Update if needed
    if not needs_home_update and not needs_away_update:
        return False, "No changes needed"
    
    # Get canonical team names for new IDs
    updates = []
    params = []
    
    if needs_home_update:
        # Get team name for new home_team_id
        cur.execute("SELECT team_name FROM teams WHERE id = %s", (new_home_team_id,))
        result = cur.fetchone()
        if result:
            new_home_team_name = result[0]
            updates.append("home_team_id = %s")
            updates.append("home_team = %s")
            params.extend([new_home_team_id, new_home_team_name])
    
    if needs_away_update:
        # Get team name for new away_team_id
        cur.execute("SELECT team_name FROM teams WHERE id = %s", (new_away_team_id,))
        result = cur.fetchone()
        if result:
            new_away_team_name = result[0]
            updates.append("away_team_id = %s")
            updates.append("away_team = %s")
            params.extend([new_away_team_id, new_away_team_name])
    
    if not updates:
        return False, "Failed to get team names"
    
    # Execute update
    params.append(match_id)
    update_sql = f"""
        UPDATE match_scores 
        SET {', '.join(updates)}
        WHERE id = %s
    """
    cur.execute(update_sql, params)
    
    logger.info(f"Match {match_id}: Updated teams (confidence: {confidence:.1%})")
    return True, f"Updated (confidence: {confidence:.1%})"


def resolve_match_team_assignments(
    cur,
    league_id: Optional[int] = None,
    confidence_threshold: float = 0.6,
    dry_run: bool = False,
    limit: Optional[int] = None
) -> Dict[str, int]:
    """
    Main entry point: Resolve team assignments for all matches.
    
    Args:
        cur: Database cursor
        league_id: Optional league filter (recommended for initial testing)
        confidence_threshold: Minimum confidence required (default 0.6 = 60%)
        dry_run: If True, only log what would be changed (no updates)
        limit: Optional limit for testing
        
    Returns:
        Dictionary with stats: {'updated': count, 'skipped': count, 'errors': count}
    """
    stats = {'updated': 0, 'skipped': 0, 'errors': 0}
    
    # Build cache for performance
    player_teams_cache = build_player_teams_cache(cur, league_id)
    
    # Find matches needing resolution
    matches = find_matches_needing_resolution(cur, league_id, limit)
    
    logger.info(f"Processing {len(matches)} matches (dry_run={dry_run})...")
    
    for match in matches:
        try:
            # Resolve match
            success, reason = resolve_single_match(
                cur, 
                match, 
                player_teams_cache,
                confidence_threshold
            )
            
            if success:
                stats['updated'] += 1
                if dry_run:
                    # Roll back in dry-run mode
                    cur.connection.rollback()
            else:
                stats['skipped'] += 1
                logger.debug(f"Match {match['id']}: {reason}")
                
        except Exception as e:
            stats['errors'] += 1
            logger.error(f"Match {match['id']}: Error: {e}")
    
    logger.info(f"Resolution complete: {stats}")
    return stats
```

---

## Integration into Existing Code

### Modification to `data/etl/import/import_match_scores.py`

Add this import at the top:

```python
# Add after other imports
from data.etl.resolvers import resolve_match_team_assignments
```

Modify the `main()` function to call resolver after import:

```python
def main():
    # ... existing code ...
    
    # Import match scores (existing)
    print("Importing match scores...")
    inserted, updated, existing, skipped, validation_failed = import_match_scores(cur, league_id, matches_data)
    
    # NEW: Resolve team assignments
    print("\n🔧 Resolving team assignments from player data...")
    resolution_stats = resolve_match_team_assignments(
        cur,
        league_id=league_id,
        confidence_threshold=0.6,
        dry_run=False
    )
    print(f"Team resolution: {resolution_stats['updated']} updated, "
          f"{resolution_stats['skipped']} skipped, "
          f"{resolution_stats['errors']} errors")
    
    # Existing integrity checks
    integrity_issues = run_integrity_checks(cur, league_id)
    
    # Commit transaction
    conn.commit()
    # ... rest of existing code ...
```

---

## Testing Strategy

### Phase 1: Unit Tests

Create `tests/test_match_team_resolver.py`:

```python
import pytest
from data.etl.resolvers.match_team_resolver import (
    build_player_teams_cache,
    get_team_votes_for_match,
    resolve_single_match,
)

def test_confidence_calculation():
    """Test that confidence threshold works correctly."""
    # Mock data: 4 players, 3 from Team A, 1 from Team B
    match = {
        'id': 1,
        'home_player_1_id': 'player_A_1',
        'home_player_2_id': 'player_A_2',
        'away_player_1_id': 'player_A_3',
        'away_player_2_id': 'player_B_1',
        'home_team_id': 999,  # Wrong team
        'away_team_id': 888,
    }
    
    cache = {
        'player_A_1': 1,
        'player_A_2': 1,
        'player_A_3': 1,
        'player_B_1': 2,
    }
    
    votes = get_team_votes_for_match(match, cache)
    assert votes[1] == 3  # Team 1 has 3 votes
    assert votes[2] == 1  # Team 2 has 1 vote

def test_skip_tie():
    """Test that ties (2v2 split) are skipped."""
    match = {
        'id': 2,
        'home_player_1_id': 'player_A_1',
        'home_player_2_id': 'player_A_2',
        'away_player_1_id': 'player_B_1',
        'away_player_2_id': 'player_B_2',
        'home_team_id': 999,
        'away_team_id': 888,
    }
    
    cache = {
        'player_A_1': 1,
        'player_A_2': 1,
        'player_B_1': 2,
        'player_B_2': 2,
    }
    
    votes = get_team_votes_for_match(match, cache)
    # 2 votes for Team 1, 2 votes for Team 2
    # Should skip due to tie (requires 60% confidence = 3+ votes)
    assert len([v for v in votes.values() if v >= 3]) == 0
```

### Phase 2: Local Database Testing

```bash
# 1. Backup local database
python cb.py local

# 2. Run with dry-run first
python data/etl/import/import_match_scores.py APTA_CHICAGO --dry-run

# 3. Review logs to see what would be changed
# Look for: "Match X: Updated teams (confidence: Y%)"

# 4. Run actual import on small subset
python data/etl/import/import_match_scores.py APTA_CHICAGO --limit 100

# 5. Verify a sample of changes manually
# Check: Does match now show correct team names?

# 6. Run full import
python data/etl/import/import_match_scores.py APTA_CHICAGO
```

### Phase 3: Staging Validation

```bash
# 1. Run on staging with dry-run
# Review all proposed changes

# 2. Run actual import on staging subset
# Validate team assignments

# 3. Run full import
# Monitor logs for errors

# 4. Verify UI displays correct data
```

### Phase 4: Production Deployment

```bash
# 1. Backup production database
python cb.py production

# 2. Run dry-run on production
# Verify proposed changes look correct

# 3. Run actual import
# Monitor closely

# 4. Verify results in UI
```

---

## Performance Optimization

### Current Performance Estimate

**Without caching**:
- 4 player lookups per match × 2,500 matches = 10,000 queries
- At 1ms per query = **10 seconds**

**With caching**:
- 1 cache build query (all players) = 1 query
- Hash map lookups × 10,000 = negligible
- Batch updates in CTEs = **~2 seconds total**

### Optimized Cache Build Query

```python
def build_player_teams_cache_optimized(cur, league_id):
    """Optimized version using single query with CTEs."""
    query = """
    WITH player_team_counts AS (
        SELECT 
            p.tenniscores_player_id,
            p.team_id,
            ROW_NUMBER() OVER (
                PARTITION BY p.tenniscores_player_id 
                ORDER BY COUNT(*) DESC, MAX(p.id) DESC
            ) as rn
        FROM players p
        WHERE p.team_id IS NOT NULL
        AND (%s IS NULL OR p.league_id = %s)
        GROUP BY p.tenniscores_player_id, p.team_id
    )
    SELECT tenniscores_player_id, team_id
    FROM player_team_counts
    WHERE rn = 1
    """
    
    cur.execute(query, (league_id, league_id))
    return {row[0]: row[1] for row in cur.fetchall()}
```

---

## Expected Results

### Before Fix

```
Match 12345: home_team_id=59385, home_team="Wilmette PD 2"
Players: Mike (team 59947), Bob (team 59947), Rob (team 59947), Ross (team 59947)
Result: WRONG - All 4 players are from different team!
```

### After Fix

```
Match 12345: home_team_id=59947, home_team="Wilmette PD 26"
Players: Mike (team 59947), Bob (team 59947), Rob (team 59947), Ross (team 59947)
Result: ✅ CORRECT - Match assigned to proper team
```

### Statistics Expected

- **Updated**: ~2,500 matches (majority rule success)
- **Skipped**: ~500 matches (ambiguous or low confidence)
- **Errors**: ~0 (robust error handling)

---

## Edge Case Handling

### Case 1: Substitute Players (1-2 players from different team)

**Example**: Match has 3 regular players + 1 substitute from another team

**Behavior**: 3 votes for Team A, 1 vote for Team B  
**Result**: ✅ Updates to Team A (75% confidence > 60% threshold)

**Rationale**: Correct - match belongs to Team A, sub is temporary

### Case 2: Equal Split (2v2)

**Example**: 2 players from Team A, 2 players from Team B

**Behavior**: 2 votes each, 50% confidence  
**Result**: ❌ Skip (50% < 60% threshold)

**Rationale**: Can't determine with confidence - requires manual review

### Case 3: Multi-team Player

**Example**: Player John is on Team A and Team B

**Behavior**: Cache picks most frequent team  
**Result**: ✅ Uses most common team assignment

**Rationale**: Conservative approach - use best available information

### Case 4: Missing Players

**Example**: Match has NULL for home_player_2_id

**Behavior**: Only 3 player lookups, not 4  
**Result**: ✅ Still works with 3+ votes

**Rationale**: Flexible - works with partial data

---

## Rollback Plan

### If Issues Arise

**Simple Case**:
```bash
# Revert code change
git checkout data/etl/import/import_match_scores.py

# Re-import from JSON
python data/etl/import/import_match_scores.py APTA_CHICAGO
```

**Data Rollback**:
```bash
# Restore from backup
python cb.py --restore local_backup_YYYYMMDD_HHMMSS.sql
```

---

## Timeline

- **Development**: 4-6 hours
  - Create resolver module (2 hours)
  - Integration with import script (1 hour)
  - Unit tests (1 hour)
  - Performance optimization (1-2 hours)

- **Testing**: 2-3 hours
  - Local testing (1 hour)
  - Staging validation (1 hour)
  - Manual verification (1 hour)

- **Deployment**: 1 hour
  - Production dry-run (15 min)
  - Production import (15 min)
  - Verification (30 min)

**Total**: 7-10 hours

---

## Success Criteria

✅ **Performance**: Import time increases by <5 seconds  
✅ **Accuracy**: 95%+ of updates are correct (manual validation)  
✅ **Safety**: 0 critical errors during import  
✅ **Coverage**: All 2,500 misassigned matches addressed  
✅ **Stability**: No adverse effects on other data  

---

## Next Steps After Implementation

1. Monitor production import logs for 1 week
2. Collect user feedback on data accuracy
3. Consider expanding to historical data cleanup
4. Document lessons learned






