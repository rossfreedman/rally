# Production Availability Fix Guide

## Issue
Users are seeing "No schedule data" on the availability page in production. The error logs show:

```
ERROR: column "user_id" does not exist
LINE 7: WHERE user_id = 43
```

## Root Cause
The production Railway database is missing the `user_id` column in the `player_availability` table. This column was added in a local migration but was never applied to production.

## Solution
Apply the SQL migration to add the missing `user_id` column to the production database.

## How to Apply the Fix

### Step 1: Access Railway Database Console
1. Go to [Railway Dashboard](https://railway.app)
2. Navigate to your Rally project
3. Click on the PostgreSQL service
4. Go to the **Connect** tab
5. Click **Query** to open the database console

### Step 2: Run the Migration
1. Copy the contents of `migrations/production_fix_availability_user_id.sql`
2. Paste it into the Railway database console query editor
3. Click **Run Query**

### Step 3: Verify the Fix
The migration will output verification messages. You should see:
```
✅ Migration completed successfully!
✅ Users should now be able to view availability data properly
```

### Step 4: Test the Application
1. Go to the production application: https://rally.up.railway.app
2. Navigate to the availability page
3. Verify that schedule data loads without errors

## What the Migration Does

1. **Adds user_id column**: Creates the missing `user_id` column with proper foreign key reference
2. **Populates existing data**: Links existing availability records to users through player associations
3. **Creates indexes**: Adds performance indexes for fast lookups
4. **Provides verification**: Reports how many records were successfully updated

## Expected Results
- The "column user_id does not exist" error will be resolved
- Users will be able to view their match schedules and availability data
- The availability page will load properly
- No data will be lost - all existing availability records will be preserved

## Rollback (if needed)
If something goes wrong, you can remove the column:
```sql
ALTER TABLE player_availability DROP COLUMN IF EXISTS user_id;
```

However, this should not be necessary as the migration is designed to be safe and non-destructive.

## Technical Details
The migration uses the same stable reference pattern as user_player_associations:
- Primary storage: `user_id` + `match_date` (stable - never orphaned during ETL)
- Backward compatibility: Maintains `player_id` and `player_name` for legacy support
- Performance: Adds partial unique indexes for fast lookups 