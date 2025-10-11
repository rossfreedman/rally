# Import Previous Season Data to Staging

## ✅ COMPLETED:
1. ✅ Database table `match_scores_previous_seasons` created on staging
2. ✅ Code deployed to staging branch
3. ✅ Import script pushed to git

## 🔄 NEXT STEP: Run Import on Staging

You need to run ONE command in an interactive terminal to import the data:

```bash
railway run python scripts/import_previous_season_matches.py
```

### Step-by-Step:

1. **Open a new terminal window**

2. **Navigate to the project:**
   ```bash
   cd /Users/rossfreedman/dev/rally
   ```

3. **Link to staging environment:**
   ```bash
   railway link
   # Select: rossfreedman's Projects → rally → staging
   ```

4. **Run the import:**
   ```bash
   railway run python scripts/import_previous_season_matches.py
   ```

   This will:
   - Connect to staging database automatically
   - Import ~5000+ matches from `data/leagues/APTA_CHICAGO/match_history_2024_2025.json`
   - Take about 2-3 minutes
   - Show progress every 1000 matches

5. **Verify the import:**
   ```bash
   railway run psql -c "SELECT COUNT(*) as total_matches, MIN(match_date) as earliest, MAX(match_date) as latest FROM match_scores_previous_seasons WHERE season = '2024-2025';"
   ```

   Expected output: ~5000+ matches from 2024-2025 season

## 🧪 TEST THE FEATURE:

After import completes, test at:
- https://rally-staging.up.railway.app/mobile/player-detail/nndz-WkNPd3liejlnUT09_team_59976

You should see:
- ✅ "Last Season Stats" card between Current Season and Career Stats
- ✅ Correct stats (matches, win rate, W-L record)
- ✅ "View More Detail" button that navigates to detail page
- ✅ Detail page with Season Summary, Best Partnerships, Court Performance

## 📊 WHAT WAS DEPLOYED:

### Database Changes:
- Created `match_scores_previous_seasons` table (mirrors `match_scores` + season column)
- Added indexes for performance

### Code Changes:
- `app/services/mobile_service.py`: 
  - `get_last_season_stats()` - Fetch and calculate last season statistics
  - `get_last_season_partner_analysis()` - Analyze partnerships with weighted ranking
  - `get_last_season_court_analysis()` - Analyze court performance with substitute detection
  
- `app/routes/mobile_routes.py`:
  - Updated `/mobile/player-detail` route to include last season data
  - Added `/mobile/last-season-stats/<player_id>` route for detail page
  
- `templates/mobile/player_detail.html`:
  - Added "Last Season Stats" card with View More Detail button
  
- `templates/mobile/last_season_stats.html`:
  - New page with Season Summary, Best Partnerships, Court Performance cards
  - Substitute detection and chips
  - Partner match modals

### Import Script:
- `scripts/import_previous_season_matches.py` - Imports JSON data into new table

## ❓ TROUBLESHOOTING:

### If import fails with "connection" error:
- Make sure you're linked to staging: `railway environment`
- Should show "staging" environment

### If import shows duplicate errors:
- Run this to clear and reimport:
  ```bash
  railway run psql -c "TRUNCATE match_scores_previous_seasons;"
  railway run python scripts/import_previous_season_matches.py
  ```

### If "Service not found":
- Relink to Railway:
  ```bash
  railway link
  # Select: rally → staging
  ```

## 🎉 SUCCESS CRITERIA:

Import is successful when:
1. ✅ Script completes without errors
2. ✅ ~5000+ records imported
3. ✅ Verification query shows correct date range (2024-2025 season)
4. ✅ Feature visible and working on staging website

