# Migration to tenniscores_player_id Schema Implementation Guide

This guide walks through implementing the `tenniscores_player_id` approach to make user-player associations ETL-resilient.

## Overview

**Problem**: ETL process clears and reimports players with new auto-incremented IDs, breaking `user_player_associations` foreign key relationships.

**Solution**: Change `user_player_associations` to use stable `tenniscores_player_id + league_id` instead of database-generated `player_id`.

## Benefits

✅ **ETL-Resilient**: Associations never break during data imports  
✅ **Clean Data Model**: No database bloat from inactive players  
✅ **External System Friendly**: Uses stable identifiers  
✅ **Logical Consistency**: Associates users with tennis players, not database records  

## Implementation Steps

### Step 1: Backup Current Data

```bash
# Create backup of current associations
python -c "
from database_config import get_db
import json
from datetime import datetime

with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.email, p.tenniscores_player_id, l.league_id, upa.is_primary, upa.created_at
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        JOIN players p ON upa.player_id = p.id
        JOIN leagues l ON p.league_id = l.id
    ''')
    
    backup = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
    
    with open(f'user_associations_backup_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.json', 'w') as f:
        json.dump(backup, f, indent=2, default=str)
        
print('Backup created successfully')
"
```

### Step 2: Run Database Migration

```bash
# Run the migration script
psql -d your_database_name -f migrations/use_tenniscores_player_id.sql
```

**Expected Output:**
```
NOTICE:  Safety Check 1 PASSED: All players have tenniscores_player_id
NOTICE:  Safety Check 2 PASSED: All players have league_id  
NOTICE:  Safety Check 3 PASSED: No duplicate tenniscores_player_id + league_id combinations
NOTICE:  Step 1 COMPLETED: Created backup table
...
NOTICE:  Step 9 COMPLETED: Removed old player_id column
SELECT 1
    status     | total_associations | unique_users | unique_player_league_combinations 
AFTER MIGRATION |                5 |            3 |                                 4
```

### Step 3: Update Application Code

```bash
# Update application queries to use new schema
python scripts/update_application_queries.py
```

**Manual Code Review Required:**

1. **Review Updated Files:**
   - `app/routes/api_routes.py` 
   - `app/services/auth_service_refactored.py`
   - `app/models/database_models.py` (already updated)

2. **Import Helper Functions** (where needed):
   ```python
   from app.utils.association_helpers import (
       find_user_player_association,
       create_user_player_association,
       get_user_associated_players
   )
   ```

3. **Update Any Direct SQL Queries** in templates or other files:
   ```sql
   -- OLD
   JOIN user_player_associations upa ON upa.player_id = p.id
   
   -- NEW  
   JOIN user_player_associations upa ON upa.tenniscores_player_id = p.tenniscores_player_id 
                                    AND upa.league_id = p.league_id
   ```

### Step 4: Test the Changes

```bash
# Test user authentication and player associations
python -c "
from app.models.database_models import SessionLocal, User, UserPlayerAssociation
from database_config import get_db

with SessionLocal() as session:
    # Test getting user associations
    user = session.query(User).first()
    if user:
        players = user.get_players(session)
        print(f'User {user.email} has {len(players)} associated players')
        
        for player in players:
            print(f'  - {player.full_name} ({player.tenniscores_player_id}) in {player.league.league_id}')
    
    # Test association queries
    associations = session.query(UserPlayerAssociation).all()
    print(f'Total associations: {len(associations)}')
    
    for assoc in associations:
        player = assoc.get_player(session)
        print(f'  - User {assoc.user_id} -> Player {assoc.tenniscores_player_id} in league {assoc.league_id}')
"
```

### Step 5: Test ETL Resilience

```bash
# Run ETL to verify associations are preserved
python etl/json_import.py

# Verify associations are still intact
python -c "
from app.models.database_models import SessionLocal, UserPlayerAssociation

with SessionLocal() as session:
    associations = session.query(UserPlayerAssociation).all()
    print(f'Associations after ETL: {len(associations)}')
    
    for assoc in associations:
        player = assoc.get_player(session)
        if player:
            print(f'  ✅ Valid: User {assoc.user_id} -> Player {player.full_name}')
        else:
            print(f'  ❌ Broken: User {assoc.user_id} -> Player {assoc.tenniscores_player_id} (not found)')
"
```

## New Schema Reference

### Updated Table Structure

```sql
-- NEW: user_player_associations table
CREATE TABLE user_player_associations (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenniscores_player_id VARCHAR(255) NOT NULL,
    league_id INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, tenniscores_player_id, league_id)
);
```

### Query Pattern Changes

```python
# OLD: Direct foreign key join
association = session.query(UserPlayerAssociation).filter(
    UserPlayerAssociation.user_id == user_id,
    UserPlayerAssociation.player_id == player_id
).first()

# NEW: Use stable identifiers
association = session.query(UserPlayerAssociation).filter(
    UserPlayerAssociation.user_id == user_id,
    UserPlayerAssociation.tenniscores_player_id == player.tenniscores_player_id,
    UserPlayerAssociation.league_id == player.league_id
).first()
```

### Helper Methods

```python
# Get player from association
player = association.get_player(session)

# Get all user's players  
players = user.get_players(session)

# Get user's primary player
primary_player = user.get_primary_player(session)

# Get all users associated with a player
users = player.get_associated_users(session)
```

## Rollback Plan

If issues occur, you can rollback:

```sql
-- EMERGENCY ROLLBACK (loses associations created after migration)
BEGIN;
DROP TABLE IF EXISTS user_player_associations;
ALTER TABLE user_player_associations_backup RENAME TO user_player_associations;
COMMIT;
```

## Verification Queries

```sql
-- Check association counts
SELECT 
    COUNT(*) as total_associations,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT (tenniscores_player_id, league_id)) as unique_players
FROM user_player_associations;

-- Verify no orphaned associations
SELECT COUNT(*) as orphaned_count
FROM user_player_associations upa
LEFT JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id 
                   AND p.league_id = upa.league_id
WHERE p.id IS NULL;

-- Sample associations with player names
SELECT 
    u.email,
    upa.tenniscores_player_id,
    p.first_name || ' ' || p.last_name as player_name,
    l.league_id,
    upa.is_primary
FROM user_player_associations upa
JOIN users u ON upa.user_id = u.id
JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id 
               AND p.league_id = upa.league_id
JOIN leagues l ON l.id = upa.league_id
ORDER BY u.email, upa.is_primary DESC;
```

## Expected Results

After successful implementation:

1. **ETL Process**: No longer breaks user-player associations
2. **Application**: Works seamlessly with new schema
3. **Performance**: Minimal impact (string joins vs integer joins)
4. **Data Integrity**: Cleaner, more logical associations

**Success Criteria:**
- ✅ All existing associations preserved after migration
- ✅ ETL runs without breaking associations  
- ✅ User authentication and player lookup works
- ✅ All application features function normally
- ✅ No orphaned association records 