# Staging Database Migration - October 12, 2025

## Summary

Successfully applied database schema changes to **staging environment** using Alembic migration `20251012_food_videos`.

## Changes Applied

### 1. Food Table Updates ✅
**Enhanced the food table to support separate men's and women's paddle schedules:**

- **Added column:** `mens_food` (TEXT, nullable)
- **Added column:** `womens_food` (TEXT, nullable)  
- **Modified column:** `food_text` now nullable (was NOT NULL)
- **Data migration:** Existing `food_text` values copied to `mens_food` for backward compatibility

### 2. Videos Table Created ✅
**New table for team-specific training videos:**

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing ID |
| `name` | VARCHAR(255) NOT NULL | Video display name |
| `url` | TEXT NOT NULL | YouTube/video platform URL |
| `players` | TEXT | Comma-separated player names |
| `date` | DATE | Video recording date |
| `team_id` | INTEGER NOT NULL | Foreign key to teams (CASCADE DELETE) |
| `created_at` | TIMESTAMP WITH TIME ZONE | Creation timestamp |
| `updated_at` | TIMESTAMP WITH TIME ZONE | Update timestamp |

**Indexes created:**
- `idx_videos_team_id` - Fast lookup by team
- `idx_videos_date` - Date-based queries (DESC order)

## Verification Results

### Staging Database Status ✅
- **Alembic Version:** `20251012_food_videos`
- **Food Table:** 3 columns verified (food_text, mens_food, womens_food)
- **Videos Table:** Created with 8 columns and 2 indexes
- **All columns nullable:** food_text, mens_food, womens_food

## Migration Files Created

1. **Alembic Migration:**
   - `/alembic/versions/20251012_add_food_fields_and_videos_table.py`
   - Revision ID: `20251012_food_videos`
   - Parent: `06076132333a`

2. **Helper Scripts:**
   - `/scripts/apply_migration_to_staging.py` - Alembic-based migration
   - `/scripts/apply_sql_migration_staging.py` - Direct SQL migration (used)
   - `/scripts/verify_staging_migration.py` - Verification script

3. **Original SQL Migration:**
   - `/migrations/add_mens_womens_food_fields.sql`

## Application Changes Required

The following code changes work with these database updates:

### Backend
- `app/routes/api_routes.py` - Food notification formatting with icons
- `app/services/mobile_service.py` - Team videos retrieval
- `app/routes/mobile_routes.py` - Video passing to templates

### Frontend  
- `templates/mobile/my_team.html` - Team videos display section
- `templates/food.html` - Men's/Women's food input
- `templates/food_display.html` - Separate paddle schedule display
- `templates/mobile/index.html` - Notification text wrapping
- `templates/mobile/home_submenu.html` - Notification text wrapping

## Testing Checklist

### Food Feature
- [ ] Test `/food` page - verify men's/women's input fields work
- [ ] Test `/food-display` page - verify separate paddle schedules display
- [ ] Test food notifications - verify bold labels and Rally green icons
- [ ] Test text wrapping in notification cards

### Videos Feature
- [ ] Test `/mobile/my-team` page - verify videos section appears
- [ ] Test video playback functionality
- [ ] Test YouTube video embedding
- [ ] Verify videos are team-specific

## Next Steps

1. **Test on Staging:**
   - Visit staging site and test all food functionality
   - Test team videos feature
   - Verify notification display

2. **Deploy to Production** (when ready):
   ```bash
   # Option 1: Using same SQL script
   python scripts/apply_sql_migration_staging.py
   # (Update connection string to production)
   
   # Option 2: Using Alembic
   DATABASE_URL="<production_url>" alembic upgrade head
   ```

3. **Monitor:**
   - Check for any errors in staging logs
   - Verify data integrity
   - Test with real users

## Database URLs

- **Local:** `postgresql://localhost:5432/rally`
- **Staging:** `postgresql://postgres:***@switchback.proxy.rlwy.net:28473/railway`
- **Production:** (Not yet applied)

## Rollback Instructions

If issues occur, run the downgrade:

```python
# Using Alembic downgrade
alembic downgrade -1

# Or manually:
ALTER TABLE food DROP COLUMN mens_food, DROP COLUMN womens_food;
ALTER TABLE food ALTER COLUMN food_text SET NOT NULL;
DROP TABLE videos CASCADE;
UPDATE alembic_version SET version_num = '06076132333a';
```

---

**Migration Applied:** October 12, 2025  
**Applied By:** AI Assistant  
**Status:** ✅ Completed Successfully on Staging  
**Production Status:** ⏳ Pending

