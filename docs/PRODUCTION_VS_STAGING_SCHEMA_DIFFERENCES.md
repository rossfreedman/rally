# Production vs Staging/Local Schema Differences

## Critical Schema Mismatches Found

### SERIES TABLE DIFFERENCES

| Component | Local/Staging | Production | Status |
|-----------|---------------|------------|---------|
| `league_id` column | ✅ EXISTS | ❌ MISSING | 🚨 CRITICAL |
| `series_name_key` constraint | ✅ REMOVED | ❌ STILL EXISTS | 🚨 CRITICAL |
| `series_name_league_unique` constraint | ✅ EXISTS | ❌ MISSING | 🚨 CRITICAL |
| Foreign key `series_league_id_fkey` | ✅ EXISTS | ❌ MISSING | 🚨 CRITICAL |

**Impact**: This is the ROOT CAUSE of Aaron's "No Series Data" issue and ETL conflicts.

### USER_CONTEXTS TABLE DIFFERENCES

| Component | Local/Staging | Production | Status |
|-----------|---------------|------------|---------|
| Total columns | 5 columns | 11 columns | 🚨 MISMATCH |
| `id` column | ❌ NO (user_id is PK) | ✅ YES | 🚨 MISMATCH |
| `club` column | ❌ NO | ✅ YES | 🚨 MISMATCH |
| `context_type` column | ❌ NO | ✅ YES | 🚨 MISMATCH |
| `is_active` column | ❌ NO | ✅ YES | 🚨 MISMATCH |
| `created_at` column | ❌ NO | ✅ YES | 🚨 MISMATCH |
| `updated_at` column | ❌ NO | ✅ YES | 🚨 MISMATCH |
| `active_team_id` column | ❌ NO | ✅ YES | 🚨 MISMATCH |

**Local/Staging Schema (5 columns)**:
- user_id (PK)
- league_id
- team_id  
- series_id
- last_updated

**Production Schema (11 columns)**:
- id (PK)
- user_id
- league_id
- team_id
- series_id
- club
- context_type
- is_active
- created_at
- updated_at
- active_team_id

**Impact**: SQLAlchemy model mismatch causes registration failures.

## REQUIRED MIGRATIONS FOR PRODUCTION

### Priority 1: Series League Isolation
```sql
-- Add league_id column
ALTER TABLE series ADD COLUMN league_id INTEGER;

-- Add foreign key
ALTER TABLE series ADD CONSTRAINT series_league_id_fkey 
    FOREIGN KEY (league_id) REFERENCES leagues(id);

-- Populate league_id for existing series
-- (Complex migration logic needed)

-- Drop old constraint
ALTER TABLE series DROP CONSTRAINT series_name_key;

-- Add new composite constraint
ALTER TABLE series ADD CONSTRAINT series_name_league_unique 
    UNIQUE (name, league_id);
```

### Priority 2: User Contexts Schema Alignment
Two options:
1. **Update SQLAlchemy model** to match production schema (11 columns)
2. **Migrate production schema** to match local/staging (5 columns)

**Recommendation**: Option 2 - Migrate production to match local/staging for consistency.

## DEPLOYMENT IMPACT

### Without Series Migration:
- ❌ Aaron's issue persists
- ❌ ETL conflicts continue
- ❌ Cross-league series problems

### Without User Contexts Schema Fix:
- ❌ Registration failures on production
- ❌ SQLAlchemy model mismatches
- ❌ UserContext creation errors

## NEXT STEPS

1. Run series league isolation migration on production
2. Align user_contexts schema across environments  
3. Deploy updated SQLAlchemy models
4. Test Aaron's registration flow

Generated: 2025-08-15
