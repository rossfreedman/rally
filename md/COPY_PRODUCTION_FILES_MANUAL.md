# Manual Instructions: Copy JSON Files from Production

Since your Railway project has multiple services, we need to specify the service name or use SSH manually.

## Option 1: Using Railway SSH (Recommended)

### Step 1: SSH into Production

```bash
railway ssh
```

### Step 2: Create a tar archive of all JSON files

Once in the SSH session:

```bash
cd /app/data/leagues
tar -czf /tmp/league_json_files.tar.gz \
  CNSWPL/series_stats.json \
  CNSWPL/match_history.json \
  CNSWPL/match_scores.json \
  CNSWPL/schedules.json \
  CNSWPL/players.json \
  APTA_CHICAGO/series_stats.json \
  APTA_CHICAGO/match_history.json \
  APTA_CHICAGO/match_scores.json \
  APTA_CHICAGO/schedules.json \
  APTA_CHICAGO/players.json \
  APTA_CHICAGO/players_career_stats.json \
  APTA_CHICAGO/player_history.json
```

### Step 3: Download the archive

You'll need to download `/tmp/league_json_files.tar.gz` from Railway. 

**Option A: Use Railway CLI** (if available):
```bash
# Exit SSH first
exit

# Download file (you may need to find the correct service name)
railway connect --service <service-name>
# Then use scp or Railway's file transfer
```

**Option B: Use Railway Web Dashboard**
1. Go to Railway dashboard
2. Navigate to your production service
3. Use the file browser/viewer if available
4. Or use the logs/console to view file contents

**Option C: Copy individual files via cat** (simplest for smaller files):

From SSH session, for each file:

```bash
# CNSWPL files
cat /app/data/leagues/CNSWPL/series_stats.json
# Copy the JSON output and paste into local file

cat /app/data/leagues/CNSWPL/match_history.json
cat /app/data/leagues/CNSWPL/match_scores.json
cat /app/data/leagues/CNSWPL/schedules.json
cat /app/data/leagues/CNSWPL/players.json

# APTA_CHICAGO files
cat /app/data/leagues/APTA_CHICAGO/series_stats.json
cat /app/data/leagues/APTA_CHICAGO/match_history.json
cat /app/data/leagues/APTA_CHICAGO/match_scores.json
cat /app/data/leagues/APTA_CHICAGO/schedules.json
cat /app/data/leagues/APTA_CHICAGO/players.json
cat /app/data/leagues/APTA_CHICAGO/players_career_stats.json
cat /app/data/leagues/APTA_CHICAGO/player_history.json
```

## Option 2: Find Service Name and Use Railway Run

### Step 1: Find your service name

```bash
railway status
# Or check Railway dashboard for service names
```

### Step 2: Update the copy script

Edit `scripts/copy_production_json_files.py` and update the service name:

```python
cmd = [
    'railway', 'run',
    '--service', '<YOUR_SERVICE_NAME>',  # Update this
    'cat', filepath
]
```

Then run:
```bash
python3 scripts/copy_production_json_files.py
```

## Quick Reference: File Paths

### Production Paths:
```
/app/data/leagues/CNSWPL/series_stats.json
/app/data/leagues/CNSWPL/match_history.json
/app/data/leagues/CNSWPL/match_scores.json
/app/data/leagues/CNSWPL/schedules.json
/app/data/leagues/CNSWPL/players.json

/app/data/leagues/APTA_CHICAGO/series_stats.json
/app/data/leagues/APTA_CHICAGO/match_history.json
/app/data/leagues/APTA_CHICAGO/match_scores.json
/app/data/leagues/APTA_CHICAGO/schedules.json
/app/data/leagues/APTA_CHICAGO/players.json
/app/data/leagues/APTA_CHICAGO/players_career_stats.json
/app/data/leagues/APTA_CHICAGO/player_history.json
```

### Local Paths (where to save):
```
data/leagues/CNSWPL/series_stats.json
data/leagues/CNSWPL/match_history.json
data/leagues/CNSWPL/match_scores.json
data/leagues/CNSWPL/schedules.json
data/leagues/CNSWPL/players.json

data/leagues/APTA_CHICAGO/series_stats.json
data/leagues/APTA_CHICAGO/match_history.json
data/leagues/APTA_CHICAGO/match_scores.json
data/leagues/APTA_CHICAGO/schedules.json
data/leagues/APTA_CHICAGO/players.json
data/leagues/APTA_CHICAGO/players_career_stats.json
data/leagues/APTA_CHICAGO/player_history.json
```

