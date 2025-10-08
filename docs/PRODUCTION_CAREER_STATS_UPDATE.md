# Production Career Stats Update Instructions

## Overview
This document provides instructions for updating career stats in the production database using SSH.

## Issue Fixed
Career stats were being incorrectly overwritten with current season stats during ETL imports. This update will:
- Fix career stats for 4,913+ players in production
- Use data from `data/leagues/APTA_CHICAGO/players_career_stats.json`
- Update the production database directly

## Prerequisites
1. SSH access to the production server
2. Python 3 and psycopg2 installed on the server
3. The `players_career_stats.json` file must be on the server

## Steps to Update Production via SSH

### Option 1: Run from Local Machine (Recommended)
```bash
# From your local machine, run the script that connects to production
cd /Users/rossfreedman/dev/rally
python3 scripts/update_production_career_stats.py
```

The script will:
1. Ask for confirmation before updating production
2. Show progress during the update
3. Display a summary of changes
4. Show Jeff Day's specific update details

### Option 2: Copy Files to Server and Run via SSH

1. **SSH into the production server:**
```bash
railway ssh
```

2. **Copy the necessary files to the server:**
```bash
# From your local machine in a different terminal
scp data/leagues/APTA_CHICAGO/players_career_stats.json production:/tmp/
scp scripts/update_production_career_stats.py production:/tmp/
```

3. **On the server, run the script:**
```bash
cd /tmp
python3 update_production_career_stats.py
```

### Option 3: Use Railway CLI
```bash
# From local machine
cd /Users/rossfreedman/dev/rally

# Run the script via Railway CLI
railway run python3 scripts/update_production_career_stats.py
```

## What the Script Does

1. **Loads career stats** from `data/leagues/APTA_CHICAGO/players_career_stats.json`
2. **Connects to production database** using the hardcoded connection string
3. **Updates each player's career stats:**
   - `career_wins`
   - `career_losses`
   - `career_matches`
   - `career_win_percentage`
4. **Shows progress** every 500 players
5. **Commits all changes** in a single transaction
6. **Displays summary** with counts and Jeff Day's specific changes

## Expected Results

- **Total records**: 6,446 players in JSON
- **Updated**: ~4,913 players
- **Skipped**: ~1,533 players (no career stats in JSON)

### Jeff Day Specific Update
- **Before**: 1 win, 1 loss, 2 matches (50%)
- **After**: 13 wins, 11 losses, 24 matches (54.2%)

## Safety Features

1. **Confirmation prompt** - Asks "yes/no" before updating production
2. **Transaction-based** - All changes committed together or rolled back on error
3. **Progress tracking** - Shows updates every 500 players
4. **Error handling** - Rolls back all changes if any error occurs
5. **Summary report** - Shows exactly what was updated

## Verification

After running the update, verify Jeff Day's stats:
```sql
SELECT 
    first_name, 
    last_name, 
    career_wins, 
    career_losses, 
    career_matches, 
    career_win_percentage
FROM players 
WHERE tenniscores_player_id = 'nndz-WkMrK3didnhnUT09';
```

Expected result:
- career_wins: 13
- career_losses: 11
- career_matches: 24
- career_win_percentage: 54.20

## Testing

Before running on production, you can test locally:
```bash
# Test on local database first
cd /Users/rossfreedman/dev/rally
python3 scripts/update_production_career_stats.py
# (It will connect to production, so be careful!)
```

## Rollback Plan

If something goes wrong:
1. The script uses transactions and will auto-rollback on errors
2. If you need to manually rollback after the script completes:
   - You'll need a backup of the players table before the update
   - Or re-run the ETL import to restore from the source data

## Related Files

- **Script**: `scripts/update_production_career_stats.py`
- **Data source**: `data/leagues/APTA_CHICAGO/players_career_stats.json`
- **Bug fix documentation**: `docs/CAREER_STATS_BUG_FIX.md`
- **Fixed import scripts**:
  - `data/etl/import/import_players.py`
  - `data/etl/import/start_season.py`

## Notes

- The production database URL is hardcoded in the script for simplicity
- The script requires `psycopg2-binary` to be installed
- All updates happen in a single transaction for safety
- Progress is shown every 500 players to monitor status
- Jeff Day's update is specifically tracked and reported

