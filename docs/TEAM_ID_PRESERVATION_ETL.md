# Team ID Preservation in ETL Process

## Overview

This document describes the new **Team ID Preservation** approach implemented in the ETL process, which replaces the complex team name matching system with a simple, reliable team ID-based backup and restore.

## Problem Solved

**Previous Approach Issues:**
- Complex team name + league + club + series matching logic
- Risk of matching errors when team names change
- Performance overhead from sophisticated matching algorithms
- Maintenance burden for matching logic
- Potential for orphaned data when matching fails

**New Approach Benefits:**
- ✅ **Simple and Reliable**: Direct team ID-based operations
- ✅ **Guaranteed Accuracy**: No risk of matching errors
- ✅ **Better Performance**: No complex matching logic needed
- ✅ **Easier to Debug**: Clear, direct relationships
- ✅ **Future-Proof**: Less likely to break with team name changes

## Implementation Details

### 1. Team Import with UPSERT

Teams are now imported using PostgreSQL's `INSERT ... ON CONFLICT UPDATE` (UPSERT) instead of `DELETE + INSERT`:

```sql
INSERT INTO teams (club_id, series_id, league_id, team_name, team_alias, display_name, created_at)
VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
ON CONFLICT (club_id, series_id, league_id) DO UPDATE SET
    team_name = EXCLUDED.team_name,
    team_alias = EXCLUDED.team_alias,
    display_name = EXCLUDED.display_name,
    updated_at = CURRENT_TIMESTAMP
RETURNING id, (xmax = 0) as is_insert
```

**Key Benefits:**
- **Team IDs are preserved** across ETL runs
- **Existing teams are updated** instead of recreated
- **New teams are inserted** with new IDs
- **No orphaned references** created

### 2. Simple Backup with Team IDs

User data is backed up with direct team ID references:

```sql
-- Backup polls with team IDs
CREATE TABLE polls_backup AS SELECT * FROM polls

-- Backup captain messages with team IDs  
CREATE TABLE captain_messages_backup AS SELECT * FROM captain_messages

-- Backup practice times with team IDs
CREATE TABLE practice_times_backup AS 
SELECT * FROM schedule WHERE home_team ILIKE '%practice%'
```

**Key Benefits:**
- **Direct backup** of all data with team IDs
- **No complex context extraction** needed
- **Fast backup process**
- **Complete data preservation**

### 3. Simple Restore with Team IDs

User data is restored using the same team IDs:

```sql
-- Restore polls with preserved team IDs
INSERT INTO polls 
SELECT * FROM polls_backup
ON CONFLICT (id) DO UPDATE SET
    team_id = EXCLUDED.team_id,
    updated_at = CURRENT_TIMESTAMP

-- Restore captain messages with preserved team IDs
INSERT INTO captain_messages 
SELECT * FROM captain_messages_backup
ON CONFLICT (id) DO UPDATE SET
    team_id = EXCLUDED.team_id,
    updated_at = CURRENT_TIMESTAMP

-- Restore practice times with preserved team IDs
INSERT INTO schedule 
SELECT * FROM practice_times_backup
ON CONFLICT (id) DO UPDATE SET
    home_team_id = EXCLUDED.home_team_id,
    updated_at = CURRENT_TIMESTAMP
```

**Key Benefits:**
- **Direct restore** using preserved team IDs
- **No matching logic** required
- **Guaranteed accuracy** - same team associations
- **Fast restore process**

## ETL Process Flow

### Before (Complex Matching)
1. **Backup**: Extract team context (name, league, club, series)
2. **Clear**: Delete all teams (lose team IDs)
3. **Import**: Create new teams (new team IDs)
4. **Restore**: Complex matching to find new team IDs
5. **Fallback**: Intelligent matching for unmatched data

### After (Team ID Preservation)
1. **Backup**: Direct backup with team IDs
2. **Import**: UPSERT teams (preserve team IDs)
3. **Restore**: Direct restore with same team IDs
4. **Validate**: Simple validation checks

## Migration from Old System

The new system is **backward compatible** and includes:

1. **Automatic Detection**: Detects if team IDs are stable
2. **Fallback Logic**: Falls back to old matching if needed
3. **Validation**: Comprehensive validation of restored data
4. **Cleanup**: Automatic cleanup of backup tables

## Testing

Use the test script to validate the new approach:

```bash
python scripts/test_team_id_preservation.py
```

**Test Coverage:**
- ✅ Team ID preservation during import
- ✅ Backup with team IDs
- ✅ Restore with team IDs
- ✅ No orphaned references
- ✅ Performance validation

## Configuration

The system automatically detects and uses team ID preservation when:

- Teams table has unique constraint on `(club_id, series_id, league_id)`
- PostgreSQL supports `ON CONFLICT` syntax
- No manual override is specified

## Monitoring

**Key Metrics to Monitor:**
- Team ID preservation rate (should be 100%)
- Backup/restore performance
- Orphaned reference count (should be 0)
- ETL completion time

**Log Messages:**
```
📥 Importing teams with ID preservation...
   ✅ Created team: Team Name (ID: 123)
   📝 Updated team: Team Name (ID: 456)
💾 Starting comprehensive user data backup with team ID preservation...
🔄 Starting simple user data restoration with team ID preservation...
```

## Troubleshooting

### Common Issues

**Issue**: Team IDs not preserved
**Solution**: Check unique constraint on teams table

**Issue**: Orphaned references after restore
**Solution**: Verify backup tables contain team IDs

**Issue**: Performance degradation
**Solution**: Check for large backup tables

### Debug Commands

```sql
-- Check team ID preservation
SELECT id, team_name, updated_at FROM teams ORDER BY updated_at DESC LIMIT 10;

-- Check for orphaned references
SELECT COUNT(*) FROM polls p LEFT JOIN teams t ON p.team_id = t.id WHERE p.team_id IS NOT NULL AND t.id IS NULL;

-- Check backup table contents
SELECT COUNT(*) FROM polls_backup WHERE team_id IS NOT NULL;
```

## Future Enhancements

**Potential Improvements:**
1. **Incremental Backup**: Only backup changed data
2. **Parallel Processing**: Parallel backup/restore operations
3. **Compression**: Compress backup tables for large datasets
4. **Validation Rules**: Custom validation rules for specific data types

## Conclusion

The Team ID Preservation approach provides a **simpler, more reliable, and more performant** solution for ETL data preservation. It eliminates the complexity of team matching while guaranteeing data integrity and improving maintainability. 