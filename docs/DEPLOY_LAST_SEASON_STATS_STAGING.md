# Deploy Last Season Stats Feature to Staging

## Overview
This guide walks through deploying the "Last Season Stats" feature to staging, which requires:
1. Creating the `match_scores_previous_seasons` table
2. Importing historical match data from `data/leagues/APTA_CHICAGO/match_history_2024_2025.json`
3. Deploying code changes

## Prerequisites
- Access to Railway staging environment
- Railway CLI installed and configured, OR access to Railway web console
- Local changes committed to git

---

## Step 1: Create Database Table

### Option A: Using Railway CLI
```bash
# Connect to staging database
railway shell --service rally-staging

# Run psql
psql $DATABASE_URL

# Paste the SQL from scripts/create_match_scores_previous_seasons_table.sql
```

### Option B: Using Railway Web Console
1. Go to Railway dashboard → rally-staging → PostgreSQL
2. Click "Query" tab
3. Paste contents from `scripts/create_match_scores_previous_seasons_table.sql`
4. Execute

### Option C: Using local psql with DATABASE_URL
```bash
# Get DATABASE_URL from Railway dashboard
# Then run:
psql "postgresql://..." -f scripts/create_match_scores_previous_seasons_table.sql
```

**✅ Verify:** Table exists
```sql
SELECT COUNT(*) FROM match_scores_previous_seasons;
-- Should return 0 (empty table)
```

---

## Step 2: Import Historical Data

### Prepare files for staging
The import script and data need to be on the staging server.

### Option A: Using Railway CLI
```bash
# Copy files to staging (if Railway supports file upload)
railway shell --service rally-staging

# From the staging shell:
cd /app
python scripts/import_previous_season_matches.py
```

### Option B: Run import locally against staging database
```bash
# Get DATABASE_URL from Railway
export DATABASE_URL="postgresql://..."

# Temporarily modify database_config.py to use DATABASE_URL
# OR create a staging-specific import script

python scripts/import_previous_season_matches.py
```

### Option C: Manual SQL import (if Python import fails)
If the import script doesn't work on staging, you can:
1. Run the import locally to generate SQL INSERT statements
2. Export to SQL file
3. Execute on staging database

**✅ Verify:** Data imported
```sql
SELECT 
    COUNT(*) as total_matches,
    MIN(match_date) as earliest,
    MAX(match_date) as latest,
    COUNT(DISTINCT season) as seasons
FROM match_scores_previous_seasons;
-- Should show ~5000+ matches for 2024-2025 season
```

---

## Step 3: Deploy Code Changes

### Check what needs to be committed
```bash
git status
```

### Commit and push to staging
```bash
# Add all changes
git add .

# Commit with descriptive message
git commit -m "feat | Add Last Season Stats feature

- Created match_scores_previous_seasons table
- Added get_last_season_stats, get_last_season_partner_analysis, get_last_season_court_analysis functions
- Added /mobile/last-season-stats/<player_id> route
- Created last_season_stats.html template with Season Summary, Best Partnerships, and Court Performance cards
- Updated player_detail.html to show Last Season Stats card
- Import script for historical match data"

# Push to staging branch
git push origin staging
```

**✅ Verify:** Railway automatically deploys from staging branch

---

## Step 4: Test on Staging

### Test URLs
1. **Player Detail Page** (should show "Last Season Stats" card):
   - https://rally-staging.up.railway.app/mobile/player-detail/{player_id}_team_{team_id}
   - Example: https://rally-staging.up.railway.app/mobile/player-detail/nndz-WkNPd3liejlnUT09_team_59976

2. **Last Season Stats Detail Page**:
   - Click "View More Detail" button on player detail page
   - Should show: Season Summary, Best Partnerships, Court Performance

### What to verify
- ✅ "Last Season Stats" card appears between Current Season and Career Stats
- ✅ Stats show correct data (matches, win rate, W-L record)
- ✅ "View More Detail" button works and navigates correctly
- ✅ Last Season Stats detail page loads
- ✅ Best Partnerships shows partners sorted by weighted score
- ✅ Court Performance shows correct court assignments
- ✅ Substitute chips appear for partners from different series
- ✅ Partner match modals work correctly

---

## Troubleshooting

### Table creation fails
- Check if table already exists: `\dt match_scores_previous_seasons`
- Drop and recreate if needed: `DROP TABLE match_scores_previous_seasons CASCADE;`

### Import fails with "connection closed"
- Use `with get_db() as conn:` pattern (already implemented)
- Check DATABASE_URL is correct
- Verify network connectivity to staging database

### No data showing on frontend
- Verify data imported: `SELECT COUNT(*) FROM match_scores_previous_seasons WHERE season = '2024-2025';`
- Check player_id exists in data: `SELECT COUNT(*) FROM match_scores_previous_seasons WHERE home_player_1_id = 'nndz-XXX' OR home_player_2_id = 'nndz-XXX';`
- Check server logs for errors

### Code not deploying
- Verify push succeeded: `git log origin/staging`
- Check Railway deployment logs
- Ensure Railway is watching the staging branch

---

## Rollback Plan

If something goes wrong:

### Rollback database
```sql
-- Remove all previous season data
TRUNCATE TABLE match_scores_previous_seasons;

-- Or drop table entirely
DROP TABLE match_scores_previous_seasons CASCADE;
```

### Rollback code
```bash
# Revert to previous commit
git revert HEAD
git push origin staging
```

---

## Files Modified/Created

### New Files
- `app/models/database_models.py` - Added `MatchScorePreviousSeason` model
- `templates/mobile/last_season_stats.html` - New page template
- `scripts/import_previous_season_matches.py` - Data import script
- `scripts/create_match_scores_previous_seasons_table.sql` - Table creation SQL

### Modified Files
- `app/services/mobile_service.py` - Added 3 new functions for last season analysis
- `app/routes/mobile_routes.py` - Added route and updated player detail route
- `templates/mobile/player_detail.html` - Added "Last Season Stats" card

---

## Success Criteria

Deployment is successful when:
1. ✅ Table exists with correct structure
2. ✅ Historical data imported (~5000+ matches)
3. ✅ Code deployed and Railway shows healthy status
4. ✅ "Last Season Stats" card visible on player detail pages
5. ✅ Last Season Stats detail page loads and shows correct data
6. ✅ All features work: partnerships, court analysis, substitute detection

---

## Post-Deployment

After successful deployment:
1. Monitor staging for any errors
2. Test with multiple player IDs
3. Verify performance (page load times)
4. Get user feedback before deploying to production
5. Document any issues discovered

---

## Production Deployment

Once verified on staging, repeat similar steps for production:
1. Merge staging → main branch
2. Create table on production database
3. Import data on production
4. Deploy via git push to main
5. Monitor and verify

