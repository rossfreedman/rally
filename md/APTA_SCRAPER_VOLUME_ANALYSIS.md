# APTA Scraper Runner - Volume and Environment Variable Analysis

## Question
Will `data/cron/apta_scraper_runner_all.py` work without a volume and environment variable?

## Analysis

### Current Implementation

1. **APTA Scraper Runner** (`apta_scraper_runner_all.py`):
   - Runs scraper: `apta_scrape_match_scores.py aptachicago --weeks 2`
   - Runs import: `import_match_scores.py APTA_CHICAGO`
   - Both run in the same session sequentially

2. **Path Resolution**:
   - Both scraper and import use `LeagueDirectoryManager.get_league_file_path()`
   - `LeagueDirectoryManager` checks for `CNSWPL_CRON_VARIABLE` environment variable
   - **Important**: Only checks `CNSWPL_CRON_VARIABLE` (not APTA-specific)
   - If not set, defaults to `data/leagues` (relative path)

3. **Import Script Fix**:
   - Import scripts now use `os.path.abspath()` to ensure absolute paths
   - This ensures reliable file access regardless of working directory

## Answer: **YES, but with limitations**

### ✅ Will Work:
- **Within the same container session**: The scraper and import run sequentially in the same session, so files will exist between steps
- **Path consistency**: Both scraper and import use the same path resolution logic
- **Code fix ensures compatibility**: `os.path.abspath()` ensures paths work correctly

### ❌ Limitations:
- **Files won't persist**: Without a volume, files are on ephemeral filesystem
- **Lost on restart**: If container restarts between scraper and import, files will be lost
- **No persistence**: Files won't survive container restarts or deployments

## How It Works

### Scenario 1: No Volume, No Environment Variable

1. **Scraper saves to**: `data/leagues/APTA_CHICAGO/match_scores.json` (relative)
   - Resolves to: `/app/data/leagues/APTA_CHICAGO/match_scores.json` (from `/app` working directory)
   - File is on ephemeral filesystem

2. **Import looks for**: Same path (via `get_league_file_path()` + `os.path.abspath()`)
   - Resolves to: `/app/data/leagues/APTA_CHICAGO/match_scores.json`
   - ✅ **Will find the file** (same session)

3. **After container restart**: File is lost ❌

### Scenario 2: Volume Mounted, CNSWPL_CRON_VARIABLE Set

If `CNSWPL_CRON_VARIABLE=/app/data/leagues` is set:

1. **Scraper saves to**: `/app/data/leagues/APTA_CHICAGO/match_scores.json` (volume)
2. **Import looks for**: Same path (volume)
3. **Files persist** ✅ across container restarts

### Scenario 3: Volume Mounted, No Environment Variable

1. **Scraper saves to**: `data/leagues/APTA_CHICAGO/match_scores.json` (relative)
   - Resolves to: `/app/data/leagues/APTA_CHICAGO/match_scores.json`
   - If volume is mounted at `/app/data`, files will be on volume ✅
   - But path resolution depends on working directory

## Recommendations

### Option 1: Set CNSWPL_CRON_VARIABLE (Recommended)
**Works for both APTA and CNSWPL**

- Set `CNSWPL_CRON_VARIABLE=/app/data/leagues` on APTA service
- Mount volume at `/app/data`
- Both leagues will use the volume
- Files persist across restarts

### Option 2: Make Environment Variable Generic
**Better long-term solution**

Consider renaming or creating a generic variable:
- `LEAGUE_DATA_DIR=/app/data/leagues` (applies to all leagues)
- Or keep `CNSWPL_CRON_VARIABLE` but document it applies to all leagues

### Option 3: No Volume (Current State)
**Works but not ideal**

- APTA will work in the same session
- Files won't persist
- If scraper and import run in same session, no problem
- If they run separately or container restarts, files will be lost

## Comparison: APTA vs CNSWPL

| Aspect | CNSWPL | APTA |
|--------|--------|------|
| **Environment Variable** | `CNSWPL_CRON_VARIABLE` | Uses same variable (if set) |
| **Default Path** | `data/leagues` | `data/leagues` |
| **Volume Needed?** | ✅ Recommended | ✅ Recommended |
| **Works Without Volume?** | ✅ Yes (same session) | ✅ Yes (same session) |
| **Persists Without Volume?** | ❌ No | ❌ No |

## Conclusion

**APTA scraper runner WILL work without a volume and environment variable**, but:

1. ✅ **Within same session**: Scraper → Import will work fine
2. ❌ **No persistence**: Files lost on container restart
3. ✅ **Code fix helps**: `os.path.abspath()` ensures path consistency
4. ⚠️ **Best practice**: Use volume + `CNSWPL_CRON_VARIABLE` for persistence

## Action Items

1. **Current state**: APTA will work but files won't persist
2. **Recommended**: Set `CNSWPL_CRON_VARIABLE=/app/data/leagues` on APTA service too
3. **Future improvement**: Consider making environment variable league-agnostic


