# Copy Production JSON Files to Local

This guide shows how to copy CNSWPL JSON files from production to local for testing.

## Quick Start

### Method 1: Automated Script (Recommended)

```bash
cd /Users/rossfreedman/dev/rally
python3 scripts/copy_cnswpl_json_from_production.py
```

This script will:
1. ✅ Check Railway CLI is installed and you're logged in
2. 💾 Backup your existing local JSON files
3. 📤 Copy files from production to local
4. ✅ Validate JSON files are valid

### Prerequisites

1. **Install Railway CLI** (if not already installed):
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**:
   ```bash
   railway login
   ```

3. **Link to production environment**:
   ```bash
   railway link
   # Select: rossfreedman's Projects > rally > production
   ```

## Method 2: Manual Copy via SSH

If the automated script doesn't work, you can manually copy files:

### Step 1: SSH into Production

```bash
railway ssh --environment production
```

### Step 2: Check Available Files

```bash
cd /app/data/leagues/CNSWPL
ls -lh *.json
```

You should see files like:
- `series_stats.json`
- `match_history.json`
- `match_scores.json`
- `schedules.json`
- `players.json`

### Step 3: Copy Files to Local

In a **new terminal** (keep the SSH session open), run:

```bash
# From your local machine
cd /Users/rossfreedman/dev/rally

# Backup existing files first
mkdir -p data/leagues/CNSWPL/backup_$(date +%Y%m%d_%H%M%S)
cp data/leagues/CNSWPL/*.json data/leagues/CNSWPL/backup_*/ 2>/dev/null || true

# Copy files using railway CLI (from the SSH session)
railway run --environment production --service rally-production \
  "cat /app/data/leagues/CNSWPL/series_stats.json" > data/leagues/CNSWPL/series_stats.json

railway run --environment production --service rally-production \
  "cat /app/data/leagues/CNSWPL/match_history.json" > data/leagues/CNSWPL/match_history.json

railway run --environment production --service rally-production \
  "cat /app/data/leagues/CNSWPL/match_scores.json" > data/leagues/CNSWPL/match_scores.json

railway run --environment production --service rally-production \
  "cat /app/data/leagues/CNSWPL/schedules.json" > data/leagues/CNSWPL/schedules.json

railway run --environment production --service rally-production \
  "cat /app/data/leagues/CNSWPL/players.json" > data/leagues/CNSWPL/players.json
```

### Step 4: Verify Files

```bash
# Check file sizes
ls -lh data/leagues/CNSWPL/*.json

# Validate JSON
python3 -c "import json; json.load(open('data/leagues/CNSWPL/series_stats.json'))"
```

## Method 3: One-Liner Script

You can also use this one-liner to copy all files:

```bash
cd /Users/rossfreedman/dev/rally
mkdir -p data/leagues/CNSWPL/backup_$(date +%Y%m%d_%H%M%S)
cp data/leagues/CNSWPL/*.json data/leagues/CNSWPL/backup_*/ 2>/dev/null || true

for file in series_stats.json match_history.json match_scores.json schedules.json players.json; do
  echo "Copying $file..."
  railway run --environment production --service rally-production \
    "cat /app/data/leagues/CNSWPL/$file" > "data/leagues/CNSWPL/$file" 2>&1
done
```

## Files Copied

The following files will be copied from production:

1. **series_stats.json** - Team standings and statistics
2. **match_history.json** - Historical match results  
3. **match_scores.json** - Detailed match scores
4. **schedules.json** - Match schedules
5. **players.json** - Player rosters

## After Copying

Once files are copied, you can test the Series H fix locally:

```bash
python3 scripts/fix_cnswpl_series_h_stats.py
```

## Troubleshooting

### Railway CLI Not Found
```bash
npm install -g @railway/cli
```

### Not Logged Into Railway
```bash
railway login
railway link  # Link to production
```

### Files Don't Exist on Production
Some files might not exist yet. Check what's available:
```bash
railway ssh --environment production
ls -lh /app/data/leagues/CNSWPL/*.json
```

### Permission Issues
Make sure you have write access to `data/leagues/CNSWPL/`:
```bash
chmod -R u+w data/leagues/CNSWPL/
```

## Notes

- **Backup**: All scripts automatically backup existing local files before copying
- **Validation**: JSON files are validated after copying
- **Size Check**: File sizes are displayed to verify successful copies
- **Production Path**: Files are located at `/app/data/leagues/CNSWPL/` on production

