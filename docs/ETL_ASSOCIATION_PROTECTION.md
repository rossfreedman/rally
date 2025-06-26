# ETL Association Protection System

## Overview

The Rally ETL system now includes comprehensive protection against user association and league context issues during database imports. This system ensures that users maintain their proper league/club/series associations and don't see profile alerts after ETL operations.

## Problem Solved

**Before Enhancement**: Database imports would:
- ❌ Clear user associations, causing users to lose access to their teams
- ❌ Reset league contexts to invalid values, triggering profile alerts
- ❌ Require manual re-association of all users after every import

**After Enhancement**: Database imports now:
- ✅ Automatically backup and restore user associations 
- ✅ Preserve and repair league contexts
- ✅ Auto-fix any remaining issues
- ✅ Provide comprehensive health monitoring

## Components

### 1. Enhanced Import Script (`import_all_jsons_to_database.py`)

#### Backup Phase (Before Clearing Tables)
```python
def backup_user_associations(self, conn):
    # Backs up user_player_associations table
    # Backs up user league_context settings with league mappings
    # Returns backup counts for logging
```

#### Restore Phase (After Import)
```python
def restore_user_associations(self, conn):
    # Restores valid user associations (only for players that still exist)
    # Restores league contexts (only for leagues that still exist)
    # Auto-fixes NULL league contexts using most active league logic
    # Returns detailed restoration statistics
```

#### Auto-Fix Logic
```python
def _auto_fix_null_league_contexts(self, conn):
    # Finds users with NULL league_context
    # Sets context to their most active league with team assignment preference
    # Prioritizes leagues where user has team assignments
    # Falls back to most recent match activity
```

### 2. League Context Repair Scripts

#### Main Repair Script (`scripts/fix_broken_league_contexts.py`)
```bash
# Check system health
python scripts/fix_broken_league_contexts.py --dry-run

# Fix specific user
python scripts/fix_broken_league_contexts.py --specific-user user@email.com

# Fix all broken contexts
python scripts/fix_broken_league_contexts.py
```

#### Association Re-discovery (`scripts/re_associate_all_users.py`)
```bash
# Check association system health  
python scripts/re_associate_all_users.py --dry-run

# Fix specific user associations
python scripts/re_associate_all_users.py --specific-user user@email.com

# Fix all user associations
python scripts/re_associate_all_users.py
```

## How It Works

### During ETL Import

1. **Backup Phase**:
   ```
   💾 Backing up user-player associations and league contexts...
   ✅ Backed up 25 user-player associations
   ✅ Backed up 22 user league contexts
   ```

2. **Clear Tables**: Normal ETL clearing process

3. **Import Data**: Normal ETL import process  

4. **Restore Phase**:
   ```
   🔄 Restoring user-player associations and league contexts...
   ✅ Restored 23 valid associations
   ✅ Restored 20 league contexts
   🔧 Auto-fixing any remaining NULL league contexts...
   🔧 John Doe: → APTA Chicago (15 matches)
   ```

5. **Health Check**:
   ```
   🔧 Running final league context health check...
   📊 League context health: 22/22 users have valid contexts  
   ✅ League context health score: 100.0%
   ```

### Association Discovery Integration

The ETL automatically runs association discovery after restoration to find any missing cross-league connections:

```
🔍 Running association discovery for additional connections...
✅ Discovery found 3 additional associations
```

## Protection Features

### 1. **Backup Validation**
- Only backs up valid data (existing users, active players)
- Stores league string IDs for cross-import compatibility
- Handles league ID changes between imports

### 2. **Restore Validation** 
- Only restores associations where target player still exists
- Only restores league contexts where target league still exists
- Logs broken/skipped restorations for transparency

### 3. **Auto-Repair Logic**
- Automatically fixes NULL league contexts
- Uses intelligent prioritization:
  1. Players with team assignments (for polls/availability)
  2. Most active leagues (by match count)
  3. Most recent activity (by last match date)

### 4. **Health Monitoring**
- Real-time health score calculation
- Detailed statistics on association coverage
- Warnings for systems below 95% health

## Example ETL Output

```
🚀 Starting Comprehensive JSON ETL Process
==================================================

💾 Backing up user-player associations and league contexts...
✅ Backed up 25 user-player associations
✅ Backed up 22 user league contexts

🗑️ Clearing existing data from target tables...
✅ Cleared 10,298 records from players
✅ All target tables cleared successfully

📥 Step 6: Importing remaining data...
✅ Imported 10,298 players

🔄 Step 7: Restoring user data...
📊 Associations - Backup: 25, Current: 0
✅ Restored 23 valid associations
⚠️ Skipped 2 associations with missing players
🔄 Restoring league contexts...
✅ Restored 20 league contexts
⚠️ 2 league contexts couldn't be restored (leagues no longer exist)
🔧 Auto-fixing any remaining NULL league contexts...
🔧 John Doe: → APTA Chicago (15 matches)
🔧 Jane Smith: → CNSWPL (8 matches)

🔍 Running association discovery for additional connections...
✅ Discovery found 3 additional associations

🔧 Running final league context health check...
📊 League context health: 22/22 users have valid contexts
✅ League context health score: 100.0%

✅ ETL process completed successfully!
🔗 User associations: 23 restored
🎯 League contexts: 20 restored, 2 auto-fixed
```

## Manual Repair Commands

If issues are detected after ETL:

### Check System Health
```bash
python scripts/fix_broken_league_contexts.py --dry-run
python scripts/re_associate_all_users.py --dry-run
```

### Fix Specific User
```bash
python scripts/fix_broken_league_contexts.py --specific-user user@email.com
python scripts/re_associate_all_users.py --specific-user user@email.com
```

### Fix All Issues
```bash
python scripts/fix_broken_league_contexts.py
python scripts/re_associate_all_users.py
```

## Database Schema Dependencies

The protection system relies on these table relationships:

```sql
-- Core association table
user_player_associations (user_id, tenniscores_player_id)

-- League context in users table  
users.league_context -> leagues.id

-- Player data integrity
players (tenniscores_player_id, league_id, club_id, series_id, team_id)
```

## Health Score Metrics

- **100%**: All users have valid league contexts pointing to leagues they're actually in
- **90-99%**: Excellent - minor issues that don't affect functionality  
- **80-89%**: Good - some users may need manual attention
- **70-79%**: Warning - noticeable issues, repair recommended
- **<70%**: Critical - immediate repair required

## Prevention Best Practices

1. **Always run ETL with latest scripts** (includes all protections)
2. **Monitor health scores** after imports
3. **Run repair scripts if health < 95%** 
4. **Test in staging** before production imports
5. **Keep backup of production data** before major imports

## Troubleshooting

### Profile Alert Still Appears
```bash
# Check user's league context
python scripts/fix_broken_league_contexts.py --specific-user user@email.com

# Check user's associations  
python scripts/re_associate_all_users.py --specific-user user@email.com
```

### Low Health Score After ETL
```bash
# Run comprehensive repair
python scripts/fix_broken_league_contexts.py
python scripts/re_associate_all_users.py

# Check final health
python scripts/fix_broken_league_contexts.py --dry-run
```

### Association Discovery Issues
```bash
# Run manual discovery
python scripts/discover_missing_associations.py --limit 100
```

The system is now **bulletproof** against association issues during database imports! 