# CNSWPL Fixes - Production Deployment Summary

## Changes to Deploy

### 1. CNSWPL Scraper Fixes (`data/etl/scrapers/cnswpl_scrape_match_scores.py`)
- **Fixed decimal score parsing**: Now handles "10.5 - 3" scores correctly
- **Fixed superscript tie-break parsing**: Correctly extracts `6<sup>4</sup>`, `7<sup>7</sup>` scores
- **Impact**: The 10/20 match with decimal scores will now be scraped correctly

### 2. Team Name Parsing Fix (`data/etl/import/import_match_scores.py`)
- **Fixed `parse_team_name()` function**: Now correctly parses "Wilmette H(3)" as series "H(3)" instead of "H"
- **Impact**: Future player imports will correctly assign players to Wilmette H(3) team

### 3. API Routes Fix (`app/routes/api_routes.py`)
- **Removed JSON fallback**: Cleaned up temporary fallback code
- **Impact**: No functional change, code cleanup

## Post-Deployment Steps Required

### 1. Run Player Reassignment Script (Production)
```bash
# SSH into production and run:
python3 scripts/fix_wilmette_h3_players.py
```

This will:
- Create missing player records for Wilmette H(3) 
- Reassign players who are on wrong teams to correct team_id (60050)

### 2. Re-run CNSWPL Scraper (Production)
After deployment, re-run the CNSWPL scraper to capture the 10/20 match with the fixes:
```bash
# Run via Railway CLI or SSH
python3 data/etl/scrapers/cnswpl_scrape_match_scores.py cnswpl
```

### 3. Import Match Scores (Production)
After scraping, import the updated match scores:
```bash
python3 data/etl/import/import_match_scores.py CNSWPL
```

## Testing Checklist

After deployment:
- [ ] Verify 10/20 match appears in match_scores
- [ ] Verify Kelly Lyden's 10/20 match shows correctly
- [ ] Verify Wilmette H(3) players show names correctly (not truncated IDs)
- [ ] Check teams-players page for Wilmette H(3) shows players
- [ ] Verify player names resolve correctly in match displays

