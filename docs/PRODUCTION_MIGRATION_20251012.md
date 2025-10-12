# Production Database Migration - October 12, 2025

## Summary

Successfully applied database schema changes to **PRODUCTION environment** using the same migration as staging: `20251012_food_videos`.

## Changes Applied

### 1. Food Table Updates ✅
**Enhanced the food table to support separate men's and women's paddle schedules:**

- **Added column:** `mens_food` (TEXT, nullable)
- **Added column:** `womens_food` (TEXT, nullable)  
- **Modified column:** `food_text` now nullable (was NOT NULL)
- **Data migration:** All 6 existing `food_text` values copied to `mens_food` for backward compatibility

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
- `videos_pkey` - Primary key index

## Verification Results

### Production Database Status ✅
- **Alembic Version:** `20251012_food_videos`
- **Food Table:** 3 columns verified (food_text, mens_food, womens_food)
- **Videos Table:** Created with 8 columns and 3 indexes
- **Existing Data:** 6 food records successfully migrated

### Data Migration Status
```
Total food records: 6
- Records with mens_food: 6 (100% migrated)
- Records with womens_food: 0 (ready for new data)
- Records with food_text: 6 (preserved for backward compatibility)
```

## Deployment Timeline

| Environment | Status | Date | Alembic Version |
|------------|--------|------|-----------------|
| Local | ✅ Complete | 2025-10-12 | 20251012_food_videos |
| Staging | ✅ Complete | 2025-10-12 | 20251012_food_videos |
| Production | ✅ Complete | 2025-10-12 | 20251012_food_videos |

## Migration Method

Used **Direct SQL Migration** approach for both staging and production:
- Script: `/scripts/apply_sql_migration_production.py`
- Connection: Direct PostgreSQL connection with transaction safety
- Verification: Automated checks post-migration

## Features Now Live in Production

### 1. Enhanced Food Notifications 🍽️
- Bold labels for "Men's (T/W/Th):" and "Women's (S/M/F):"
- Rally green person icons (fa-person and fa-person-dress)
- Proper text wrapping in notification cards
- Separate paddle schedule support

### 2. Team Videos Feature 🎥
- Team-specific video library on `/mobile/my-team`
- YouTube video embedding with play controls
- Player names and recording dates
- Modern card-based UI with thumbnails

### 3. UI Improvements ✨
- Text wrapping fixes in notification cards
- Break-words CSS class for long text strings
- Consistent Rally brand colors (#045454)

## Code Changes in Production

The following frontend/backend changes work with the new schema:

### Backend Files
- ✅ `app/routes/api_routes.py` - Food notification formatting
- ✅ `app/services/mobile_service.py` - Team videos retrieval
- ✅ `app/routes/mobile_routes.py` - Video data passing

### Frontend Files
- ✅ `templates/mobile/my_team.html` - Team videos section
- ✅ `templates/food.html` - Men's/Women's food inputs
- ✅ `templates/food_display.html` - Separate schedules
- ✅ `templates/mobile/index.html` - Text wrapping
- ✅ `templates/mobile/home_submenu.html` - Text wrapping

## Testing Results

### Production Verification ✅
- [x] Database schema matches staging
- [x] All 6 existing food records migrated successfully
- [x] Videos table created with proper indexes
- [x] Alembic version updated correctly
- [x] No data loss or corruption

### Live Testing Checklist
- [ ] Test food notifications on live site
- [ ] Verify bold labels and Rally green icons appear
- [ ] Test text wrapping with long food descriptions
- [ ] Test team videos feature (if videos added)
- [ ] Monitor error logs for issues

## Database Connections

- **Local:** `postgresql://localhost:5432/rally`
- **Staging:** `postgresql://postgres:***@switchback.proxy.rlwy.net:28473/railway`
- **Production:** `postgresql://postgres:***@ballast.proxy.rlwy.net:40911/railway`

## Rollback Instructions

If critical issues occur in production:

```python
# Connect to production
import psycopg2
conn = psycopg2.connect('postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway')
cur = conn.cursor()

# Rollback changes
cur.execute("ALTER TABLE food DROP COLUMN mens_food, DROP COLUMN womens_food;")
cur.execute("ALTER TABLE food ALTER COLUMN food_text SET NOT NULL;")
cur.execute("DROP TABLE videos CASCADE;")
cur.execute("UPDATE alembic_version SET version_num = '06076132333a';")

conn.commit()
cur.close()
conn.close()
```

## Post-Deployment Monitoring

### Metrics to Watch
1. **Food Notifications:** Check if users see new format
2. **Error Rates:** Monitor for database-related errors
3. **Performance:** Verify no slowdown in food/video queries
4. **User Feedback:** Watch for reports about food display

### Log Locations
- Production logs: Railway dashboard
- Database logs: PostgreSQL logs on Railway
- Application errors: Flask error logs

## Next Steps

1. **Immediate:**
   - ✅ Migration complete on all environments
   - ✅ Verification successful
   
2. **Short-term:**
   - Test food notifications with real users
   - Add sample team videos for testing
   - Monitor for any issues

3. **Future Enhancements:**
   - Admin UI for managing food menus
   - Video upload interface
   - Video analytics and tracking

## Files Created

### Migration Files
- `/alembic/versions/20251012_add_food_fields_and_videos_table.py`
- `/scripts/apply_sql_migration_staging.py`
- `/scripts/apply_sql_migration_production.py`
- `/scripts/verify_staging_migration.py`
- `/scripts/verify_production_migration.py`

### Documentation
- `/docs/STAGING_MIGRATION_20251012.md`
- `/docs/PRODUCTION_MIGRATION_20251012.md` (this file)
- `/docs/FOOD_FIELDS_MIGRATION.md`
- `/docs/TEAM_VIDEOS_FEATURE.md`

---

**Migration Applied:** October 12, 2025  
**Applied By:** AI Assistant  
**Status:** ✅ Completed Successfully  
**Verified:** ✅ All checks passed  
**Production Status:** 🟢 LIVE

