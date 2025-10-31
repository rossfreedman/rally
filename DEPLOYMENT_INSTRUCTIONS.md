# Production Deployment Instructions

## Files Changed
- `data/etl/scrapers/cnswpl_scrape_match_scores.py` - Fixed decimal scores and superscript parsing
- `data/etl/import/import_match_scores.py` - Fixed team name parsing for "H(3)" pattern
- `app/routes/api_routes.py` - Removed JSON fallback

## Deployment Steps

### 1. Commit and Push Changes
```bash
# Review changes
git diff --cached

# Commit with descriptive message
git commit -m "Fix CNSWPL scraper: decimal scores, superscript parsing, and team name parsing for H(3)"

# Push to main branch (triggers production deployment)
git push origin main
```

### 2. After Deployment Completes - Fix Player Assignments

SSH into production and run:
```bash
# Via Railway SSH
railway shell --service 'Rally PRODUCTION App'

# Or run directly
python3 scripts/fix_wilmette_h3_players.py
```

### 3. Re-run CNSWPL Scraper (Production)

After player fix, re-scrape to capture the 10/20 match:
```bash
# Run CNSWPL scraper
python3 data/etl/scrapers/cnswpl_scrape_match_scores.py cnswpl

# Then import matches
python3 data/etl/import/import_match_scores.py CNSWPL
```

## Verification Checklist
- [ ] Verify 10/20 match appears in database
- [ ] Verify Kelly Lyden's match shows correctly
- [ ] Verify Wilmette H(3) player names display correctly
- [ ] Check teams-players page shows players
