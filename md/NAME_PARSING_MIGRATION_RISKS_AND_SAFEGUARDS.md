# Name Parsing Fix: Risks and Safeguards

## Critical Database Constraints

### Clubs Table
- **UNIQUE constraint**: `clubs.name` (unique across all leagues)
- **Impact**: Changing normalization will create NEW clubs with different names
- **Example**: "Wilmette" (existing) vs "Wilmette PD II" (new) → Both will exist

### Teams Table
- **UNIQUE constraint**: `(team_name, league_id)` - team names must be unique per league
- **UNIQUE constraint**: `(club_id, series_id, league_id)` - one team per club/series/league combo
- **Foreign Keys**: `club_id`, `series_id`, `league_id` must exist
- **Impact**: Teams linked to old clubs will become orphaned if clubs are renamed

### Current Data State
- **83 clubs** in database (from schema)
- **931 teams** in database
- **Existing relationships**: Players → Teams → Clubs → Series

---

## Risk Analysis

### Risk 1: Duplicate Clubs Created ⚠️ HIGH

**Scenario**: 
- Existing: Club "Wilmette" (from old normalization)
- New import: "Wilmette PD II" → Normalizes to "Wilmette PD II" (new logic)
- **Result**: Two separate clubs exist

**Impact**:
- Data fragmentation
- Teams split across duplicate clubs
- User confusion
- Reporting/analytics issues

**Likelihood**: **HIGH** - Will happen on first import after change

---

### Risk 2: Orphaned Teams ⚠️ HIGH

**Scenario**:
- Existing team "Wilmette 10" linked to club "Wilmette" (id=2)
- New import creates club "Wilmette PD II" (id=100)
- Team "Wilmette PD II 10" created with club_id=100
- **Result**: Old team still points to old club, new team points to new club

**Impact**:
- Teams split across duplicate clubs
- Players may be on wrong teams
- Match history may be split
- Foreign key integrity maintained, but logical integrity broken

**Likelihood**: **HIGH** - Will happen immediately

---

### Risk 3: Team Name Collisions ⚠️ MEDIUM

**Scenario**:
- Existing: Team "Wilmette 10" (team_name="Wilmette 10")
- New import: "Wilmette PD II 10" → Team name "Wilmette PD II 10"
- **Result**: Different teams, different names (OK)
- BUT: If old team was "Wilmette PD II 10" and new is same, UNIQUE constraint violation

**Impact**:
- Import failures
- Data inconsistency
- Need to handle conflicts

**Likelihood**: **MEDIUM** - Depends on existing data

---

### Risk 4: Series Mismatches ⚠️ MEDIUM

**Scenario**:
- Old: "Wilmette PD II" → Series "II" (incorrectly parsed)
- New: "Wilmette PD II 10" → Series "10" (correctly parsed)
- **Result**: Different series for same logical team

**Impact**:
- Series statistics split
- Standings incorrect
- Team matching failures

**Likelihood**: **MEDIUM** - Depends on parsing changes

---

### Risk 5: Application Code Breakage ⚠️ MEDIUM

**Scenario**:
- Application code expects "Wilmette" as club name
- New normalization returns "Wilmette PD II"
- **Result**: Lookups fail, displays wrong names

**Impact**:
- User-facing errors
- API failures
- Display issues

**Likelihood**: **MEDIUM** - Depends on how app queries clubs

---

### Risk 6: Foreign Key Violations ⚠️ LOW

**Scenario**:
- If we try to rename/delete clubs, foreign keys prevent it
- **Result**: Migration scripts fail

**Impact**:
- Cannot clean up duplicates
- Manual intervention required

**Likelihood**: **LOW** - Foreign keys protect data integrity

---

### Risk 7: Match Score Linking Failures ⚠️ HIGH

**Scenario**:
- Existing matches linked to team "Wilmette 10" (old club)
- New import creates team "Wilmette PD II 10" (new club)
- **Result**: Match history split across teams

**Impact**:
- Historical data fragmentation
- Statistics incorrect
- User confusion

**Likelihood**: **HIGH** - Will happen on first import

---

## Safeguards and Mitigation Strategies

### Safeguard 1: Pre-Migration Analysis ✅

**Action**: Analyze existing database before making changes

**Steps**:
1. Export all club names and counts
2. Identify clubs that will be affected by new normalization
3. Map old names → new names
4. Count teams/players/matches affected
5. Generate impact report

**Script**: `scripts/analyze_club_name_migration_impact.py`

**Output**: 
- List of clubs that will change
- Count of affected teams/players/matches
- Duplicate detection (old vs new names)

---

### Safeguard 2: Dual Normalization Period ✅

**Action**: Support both old and new normalization during transition

**Implementation**:
1. Add `original_name` column to clubs table
2. Store both normalized (new) and original names
3. Use new normalization for new imports
4. Keep old normalization for lookups during transition
5. Gradually migrate existing data

**Code Pattern**:
```python
def normalize_club_name_v2(raw: str) -> str:
    """New normalization logic"""
    # ... new rules ...

def normalize_club_name_legacy(raw: str) -> str:
    """Old normalization logic (for backward compatibility)"""
    # ... old rules ...

def normalize_club_name(raw: str, use_legacy: bool = False) -> str:
    """Unified function with flag"""
    if use_legacy:
        return normalize_club_name_legacy(raw)
    return normalize_club_name_v2(raw)
```

**Benefit**: Allows gradual migration without breaking existing data

---

### Safeguard 3: Club Name Mapping Table ✅

**Action**: Create mapping table to link old and new club names

**Schema**:
```sql
CREATE TABLE club_name_mappings (
    id SERIAL PRIMARY KEY,
    old_name VARCHAR(255) NOT NULL,
    new_name VARCHAR(255) NOT NULL,
    migration_status VARCHAR(50), -- 'pending', 'migrated', 'merged'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Usage**:
- Map "Wilmette" → "Wilmette PD II"
- Use mapping during lookups
- Gradually migrate teams to new clubs
- Merge duplicates when safe

---

### Safeguard 4: Dry-Run Mode ✅

**Action**: Test changes without modifying database

**Implementation**:
1. Add `--dry-run` flag to all import scripts
2. In dry-run mode:
   - Parse names using new logic
   - Show what WOULD be created/changed
   - Don't write to database
   - Generate report of changes

**Usage**:
```bash
python3 data/etl/import/import_players.py APTA_CHICAGO --dry-run
```

**Output**: Report showing:
- New clubs that would be created
- Teams that would be affected
- Conflicts that would occur

---

### Safeguard 5: Staged Rollout ✅

**Action**: Deploy changes in stages

**Stage 1: Analysis** (No code changes)
- Run analysis scripts
- Generate impact reports
- Create club name mappings

**Stage 2: Database Preparation** (Schema changes only)
- Add `original_name` column to clubs
- Create `club_name_mappings` table
- Add indexes for performance

**Stage 3: Dual Support** (Code changes, both modes)
- Implement new normalization
- Keep old normalization available
- Use feature flag to switch

**Stage 4: Testing** (New mode on test data)
- Test on staging database
- Verify no data loss
- Check application compatibility

**Stage 5: Production Migration** (Gradual)
- Enable new normalization for NEW imports only
- Migrate existing data gradually
- Monitor for issues

**Stage 6: Cleanup** (Final)
- Remove old normalization code
- Clean up duplicate clubs
- Update application code

---

### Safeguard 6: Data Backup ✅

**Action**: Full backup before any changes

**Steps**:
1. Backup production database
2. Backup staging database
3. Verify backups are restorable
4. Document backup locations

**Command**:
```bash
python3 cb.py backup production
python3 cb.py backup staging
```

**Timing**: Before Stage 2 (database changes)

---

### Safeguard 7: Validation Scripts ✅

**Action**: Create validation scripts to check data integrity

**Scripts Needed**:

1. **`scripts/validate_club_names.py`**
   - Check for duplicate clubs (old vs new names)
   - Verify team-club relationships
   - Check for orphaned teams

2. **`scripts/validate_team_names.py`**
   - Verify team names match expected patterns
   - Check for duplicate team names
   - Validate series assignments

3. **`scripts/validate_foreign_keys.py`**
   - Verify all foreign keys are valid
   - Check for orphaned records
   - Validate constraint compliance

**Run After**: Each stage of migration

---

### Safeguard 8: Rollback Plan ✅

**Action**: Ability to revert changes if issues occur

**Rollback Steps**:

1. **Code Rollback**
   - Revert to previous git commit
   - Redeploy application
   - Use old normalization logic

2. **Database Rollback** (if needed)
   - Restore from backup
   - Revert schema changes
   - Restore club names

3. **Data Rollback** (selective)
   - Use club_name_mappings to revert specific clubs
   - Update team club_id references
   - Re-run imports with old logic

**Test**: Practice rollback on staging before production

---

### Safeguard 9: Monitoring and Alerts ✅

**Action**: Monitor for issues during and after migration

**Metrics to Track**:
- Number of new clubs created per import
- Number of duplicate clubs
- Team matching success rate
- Import error rates
- Application error rates

**Alerts**:
- Alert if duplicate clubs exceed threshold
- Alert if team matching fails > 5%
- Alert if import errors spike

**Tools**:
- Database query monitoring
- Application error logging
- Import script logging

---

### Safeguard 10: Club Consolidation Script ✅

**Action**: Script to merge duplicate clubs after migration

**Functionality**:
1. Identify duplicate clubs (old vs new names)
2. Map teams from old club to new club
3. Update all foreign key references
4. Delete old club (after verification)
5. Log all changes

**Script**: `scripts/consolidate_duplicate_clubs.py`

**Usage**:
```bash
python3 scripts/consolidate_duplicate_clubs.py --dry-run
python3 scripts/consolidate_duplicate_clubs.py --live
```

**Safety**:
- Dry-run mode by default
- Requires explicit `--live` flag
- Creates backup before changes
- Validates all foreign keys after changes

---

## Migration Checklist

### Pre-Migration
- [ ] Full database backup (production + staging)
- [ ] Run impact analysis script
- [ ] Review impact report
- [ ] Create club name mappings
- [ ] Test on staging database
- [ ] Get approval for changes

### Stage 1: Schema Changes
- [ ] Add `original_name` column to clubs
- [ ] Create `club_name_mappings` table
- [ ] Add indexes
- [ ] Verify schema changes
- [ ] Test rollback of schema changes

### Stage 2: Code Changes
- [ ] Implement new normalization functions
- [ ] Add dual-mode support (old + new)
- [ ] Add `--dry-run` flags
- [ ] Update all import scripts
- [ ] Add feature flag for new normalization
- [ ] Test on staging

### Stage 3: Testing
- [ ] Run dry-run on production data (read-only)
- [ ] Verify new normalization produces expected results
- [ ] Check for conflicts
- [ ] Test application compatibility
- [ ] Validate data integrity

### Stage 4: Staged Rollout
- [ ] Enable new normalization on staging
- [ ] Run full import on staging
- [ ] Validate results
- [ ] Enable new normalization on production (new imports only)
- [ ] Monitor for issues
- [ ] Gradually migrate existing data

### Stage 5: Cleanup
- [ ] Consolidate duplicate clubs
- [ ] Remove old normalization code
- [ ] Update application code
- [ ] Remove temporary tables/columns
- [ ] Final validation

### Post-Migration
- [ ] Run validation scripts
- [ ] Verify no data loss
- [ ] Check application functionality
- [ ] Monitor for issues
- [ ] Document changes

---

## Testing Strategy

### Unit Tests
- Test new normalization functions with all patterns
- Test edge cases
- Test backward compatibility

### Integration Tests
- Test full import pipeline
- Test team matching
- Test club creation
- Test duplicate handling

### Staging Tests
- Full import on staging database
- Compare results with production
- Verify data integrity
- Test application compatibility

### Production Tests
- Dry-run on production data
- Small test import
- Monitor closely
- Rollback if issues

---

## Success Criteria

1. ✅ No data loss
2. ✅ No duplicate clubs (after consolidation)
3. ✅ All teams properly linked to clubs
4. ✅ All matches properly linked to teams
5. ✅ Application works correctly
6. ✅ Import process works correctly
7. ✅ Performance not degraded
8. ✅ All validation scripts pass

---

## Timeline Estimate

- **Pre-Migration Analysis**: 1-2 days
- **Schema Changes**: 1 day
- **Code Implementation**: 2-3 days
- **Testing**: 2-3 days
- **Staged Rollout**: 1-2 weeks (gradual)
- **Cleanup**: 1-2 days

**Total**: 2-3 weeks for safe migration

---

## Recommended Approach

1. **Start with Analysis**: Don't change anything until we understand impact
2. **Use Dual Mode**: Support both old and new during transition
3. **Staged Rollout**: Don't change everything at once
4. **Monitor Closely**: Watch for issues at each stage
5. **Have Rollback Ready**: Be prepared to revert if needed
6. **Test Thoroughly**: Test on staging before production

**Key Principle**: **Gradual migration is safer than big bang change**

---

## Quick Reference: Top 5 Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Duplicate Clubs** | HIGH | Use club_name_mappings table + consolidation script |
| **Orphaned Teams** | HIGH | Gradual migration + validation scripts |
| **Match History Split** | HIGH | Consolidate clubs after migration |
| **Application Breakage** | MEDIUM | Dual-mode support + feature flags |
| **Import Failures** | MEDIUM | Dry-run mode + validation |

## Quick Reference: Top 5 Safeguards

1. **Pre-Migration Analysis** - Understand impact before changing anything
2. **Dual Normalization** - Support both old and new during transition
3. **Dry-Run Mode** - Test changes without modifying database
4. **Club Consolidation Script** - Merge duplicates after migration (already exists: `post_etl_club_cleanup.py`)
5. **Staged Rollout** - Change gradually, not all at once

## Existing Tools We Can Leverage

1. **`post_etl_club_cleanup.py`** - Already exists for consolidating duplicate clubs
   - Can be extended to handle new normalization duplicates
   - Has dry-run mode
   - Supports staging/production

2. **`cb.py`** - Database backup utility
   - Use before any changes
   - Verify backups are restorable

3. **Database constraints** - Protect data integrity
   - UNIQUE constraints prevent some issues
   - Foreign keys maintain relationships
   - Use constraints to validate changes

