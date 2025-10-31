# CNSWPL Match Parsing Fixes

## Issue Summary

The 10/20 match between "Tennaqua H @ Wilmette H(3): 10.5 - 3" was not being scraped correctly due to two parsing issues:

### Issue 1: Decimal Scores Not Supported
- **Problem**: The regex pattern in `_extract_cnswpl_teams_and_score()` only matched integer scores (`\d+`), but the actual match header shows "10.5 - 3" (decimal score)
- **Fix**: Updated regex from `(\d+)` to `([\d.]+)` to handle both integer and decimal scores
- **Location**: `data/etl/scrapers/cnswpl_scrape_match_scores.py` lines 419, 445

### Issue 2: Tie-Break Scores with Superscript Not Parsed
- **Problem**: Score extraction used `get_text()` which strips HTML formatting, losing superscript tie-break information (e.g., `6<sup>4</sup>`, `7<sup>7</sup>`)
- **Fix**: Added logic to extract raw HTML from score cells, detect `<sup>` tags, and parse tie-break scores before extracting text
- **Location**: `data/etl/scrapers/cnswpl_scrape_match_scores.py` lines 517-537, 548-566

## Changes Made

### 1. Team/Score Header Parsing (`_extract_cnswpl_teams_and_score`)
- Updated regex pattern to handle decimal scores: `r'([^@\n]+)\s*@\s*([^:\n]+):\s*([\d.]+)\s*-\s*([\d.]+)'`
- Added float parsing with fallback to integer conversion when whole number
- Handles scores like "10.5", "12", "0", etc.

### 2. Individual Set Score Extraction (`_extract_cnswpl_lines`)
- Added HTML cell extraction (`str(cell)`) before text extraction
- Added regex pattern to detect superscript: `r'(\d+)<sup>(\d+)</sup>'`
- Extracts main score and tie-break points separately
- Preserves main score value while handling tie-break formatting

## Testing

The fixes should now correctly parse:
- ✅ Team names with parentheses: "Wilmette H(3)"
- ✅ Decimal match scores: "10.5 - 3"
- ✅ Tie-break scores with superscript: `6<sup>4</sup>` → "6", `7<sup>7</sup>` → "7"

## Next Steps

1. Re-run CNSWPL scraper in production to capture the 10/20 match
2. Verify the match appears in `match_scores.json` and database
3. Confirm Kelly Lyden's match shows up on her stats page

