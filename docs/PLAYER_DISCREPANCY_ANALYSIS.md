# Player Discrepancy Analysis: nndz-WkNDd3liZitndz09

## Issue Summary
Player ID `nndz-WkNDd3liZitndz09` (Brett Pierson) shows different team contexts between local and production environments:

- **Local**: 2 team contexts (Tennaqua Series 7 + Valley Lo Series 8)
- **Production**: 1 team context (Tennaqua Series 7 only)

## Root Cause Analysis

### 1. Database Schema Differences
**Local Database:**
- Allows multiple player records with same name in same league
- No `unique_name_per_league` constraint
- Brett Pierson can exist in both Tennaqua Series 7 and Valley Lo Series 8

**Production Database:**
- Has `unique_name_per_league` constraint on `(first_name, last_name, league_id)`
- Prevents duplicate player names within the same league
- Brett Pierson can only exist once in APTA Chicago league

### 2. Business Logic Differences
**Local Behavior:**
- Supports players being on multiple teams within the same league
- Each team/series combination gets its own player record
- Allows for complex multi-team scenarios

**Production Behavior:**
- Enforces one player per league rule
- Prevents data duplication and confusion
- More restrictive but cleaner data model

### 3. Data Integrity Impact
The production constraint prevents:
- Duplicate player records within the same league
- Data inconsistency issues
- Confusion about which record represents the "real" player

## Current State

### Local Environment
```
Player Records:
1. ID: 1386832 - Brett Pierson, Tennaqua Series 7, APTA Chicago
2. ID: 1408294 - Brett Pierson, Valley Lo Series 8, APTA Chicago

User Association:
- User ID: 904 (bpierson@gmail.com) associated with tenniscores_player_id: nndz-WkNDd3liZitndz09
```

### Production Environment
```
Player Records:
1. ID: 755915 - Brett Pierson, Tennaqua Series 7, APTA Chicago

User Association:
- User ID: 965 (brett.a.pierson@gmail.com) associated with tenniscores_player_id: nndz-WkNDd3liZitndz09
```

## Recommended Solution

### Option 1: Align Production with Local (Recommended)
1. **Remove the `unique_name_per_league` constraint** from production
2. **Add the missing Valley Lo Series 8 record** to production
3. **Ensure both environments have identical data structures**

**Pros:**
- Maintains data consistency between environments
- Supports the business requirement of players on multiple teams
- Preserves existing local functionality

**Cons:**
- Requires database schema change in production
- May introduce data integrity risks if not managed properly

### Option 2: Align Local with Production
1. **Add the `unique_name_per_league` constraint** to local
2. **Remove the duplicate Valley Lo Series 8 record** from local
3. **Implement alternative multi-team support** (e.g., through team assignments)

**Pros:**
- Enforces stricter data integrity
- Prevents duplicate player records
- More scalable long-term solution

**Cons:**
- Breaks existing local functionality
- Requires significant application logic changes
- May not support current business requirements

## Implementation Plan for Option 1

### Phase 1: Schema Alignment
1. Create migration script to remove `unique_name_per_league` constraint
2. Test migration in staging environment
3. Deploy to production during maintenance window

### Phase 2: Data Synchronization
1. Insert missing Valley Lo Series 8 player record
2. Verify data consistency between environments
3. Update any related application logic

### Phase 3: Validation
1. Confirm both environments show identical player records
2. Test user association functionality
3. Verify team switching works correctly

## Risk Assessment

### High Risk
- **Database schema changes** in production
- **Data integrity** during constraint removal
- **Application compatibility** with new data structure

### Medium Risk
- **User experience** changes
- **Team switching** functionality
- **Data synchronization** between environments

### Low Risk
- **Performance impact** (minimal)
- **Backup and recovery** (standard procedures)

## Conclusion

The discrepancy is caused by different database constraints between environments. Production enforces a stricter "one player per league" rule, while local allows multiple team contexts per player.

**Recommendation**: Align production with local by removing the restrictive constraint and adding the missing player record. This maintains business functionality while ensuring environment consistency.

**Next Steps**: 
1. Create and test migration script
2. Schedule production deployment
3. Synchronize missing data
4. Validate functionality across environments
