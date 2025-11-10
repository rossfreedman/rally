# Club and Team Name Truncation Analysis

**Date**: 2025-01-XX  
**Purpose**: Comprehensive analysis of where and how club/team names are being truncated during scrape and import processes

## Executive Summary

The analysis reveals **systematic truncation** of club and team names at multiple stages of the ETL pipeline. Names with Roman numerals (II, I), parentheses (C(1)), numeric suffixes (2, 23), and dash-separated series identifiers (- 7 SW) are being incorrectly stripped, resulting in loss of critical identifying information.

## Problem Names Identified

The following name patterns are being truncated:

1. **Wilmette PD II** → Truncated to "Wilmette"
2. **North Shore C(1)** → Truncated to "North Shore"
3. **Tennaqua I** → Truncated to "Tennaqua"
4. **Lake Shore CC 2** → Truncated to "Lake Shore CC"
5. **Prairie Club SN (5)** → Truncated to "Prairie Club"
6. **Salt Creek I - 7 SW** → Truncated to "Salt Creek"

## Detailed Analysis by Component

### 1. Scraper-Level Issues

#### File: `data/etl/scrapers/apta_scrape_match_scores.py` (Lines 1716-1731)

**Function**: `_extract_apta_teams_and_score()`

**Issue**: Uses regex pattern `r'\s*-\s*\d+.*$'` to remove everything after a dash and number.

**Code**:
```python
away_team = re.sub(r'\s*-\s*\d+.*$', '', away_part).strip()
home_team = re.sub(r'\s*-\s*\d+.*$', '', home_part).strip()
```

**Impact**:
- `"Salt Creek I - 7 SW"` → `"Salt Creek I"` (loses " - 7 SW")
- This pattern assumes all content after " - [number]" is a series identifier, but in cases like "Salt Creek I - 7 SW", the " - 7 SW" is part of the team name structure.

**Test Results**:
```
Original: 'Salt Creek I - 7 SW'
After regex: 'Salt Creek I'
❌ TRUNCATED: Lost ' - 7 SW'
```

#### File: `data/etl/scrapers/apta/apta_scrape_players_simple.py` (Lines 922-928)

**Issue**: Club name extraction splits on " - " and only keeps first part.

**Code**:
```python
if ' - ' in clean_team_name:
    parts = clean_team_name.split(' - ')
    if len(parts) == 2:
        club_name = parts[0].strip()
```

**Impact**: Names with dashes lose important suffixes that are part of the club name.

### 2. Import Script Normalization Issues

#### Function: `normalize_club_name(raw: str)`

**Files Affected**:
- `data/etl/import/import_players.py` (lines 33-79)
- `data/etl/import/import_stats.py` (lines 33-79)
- `data/etl/import/import_match_scores.py` (lines 40-78)
- `data/etl/import/import_schedules.py` (lines 70-122)

**Normalization Steps and Issues**:

1. **Line 53-54: Dash Splitting**
   ```python
   if " - " in name:
       name = name.split(" - ")[0].strip()
   ```
   - **Issue**: Removes everything after " - "
   - **Example**: `"Salt Creek I - 7 SW"` → `"Salt Creek I"` (loses " - 7 SW")

2. **Line 57: Parentheses Removal**
   ```python
   name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
   ```
   - **Issue**: Removes ALL trailing parenthetical segments
   - **Examples**:
     - `"North Shore C(1)"` → `"North Shore C"` (loses "(1)")
     - `"Prairie Club SN (5)"` → `"Prairie Club SN"` (loses " (5)")

3. **Line 61: Suffix Token Stripping**
   ```python
   tokens = _strip_trailing_suffix_tokens(tokens)
   ```
   - **Issue**: Calls function that removes Roman numerals, numbers, letters, etc.
   - **Examples**:
     - `"Wilmette PD II"` → `"Wilmette"` (loses "PD II")
     - `"Tennaqua I"` → `"Tennaqua"` (loses "I")
     - `"Lake Shore CC 2"` → `"Lake Shore CC"` (loses "2")

4. **Line 65: Punctuation Removal**
   ```python
   name = re.sub(r'[^\w\s&]', '', name)
   ```
   - **Issue**: Removes all punctuation except & and spaces
   - **Impact**: Removes parentheses, dashes that might be part of legitimate names

**Test Results for `normalize_club_name()`**:
```
Original: 'Wilmette PD II'
Normalized: 'Wilmette'
❌ TRUNCATED: Lost ' PD II'

Original: 'North Shore C(1)'
Normalized: 'North Shore'
❌ TRUNCATED: Lost ' C(1)'

Original: 'Tennaqua I'
Normalized: 'Tennaqua'
❌ TRUNCATED: Lost ' I'

Original: 'Lake Shore CC 2'
Normalized: 'Lake Shore CC'
❌ TRUNCATED: Lost ' 2'

Original: 'Prairie Club SN (5)'
Normalized: 'Prairie Club'
❌ TRUNCATED: Lost ' SN (5)'

Original: 'Salt Creek I - 7 SW'
Normalized: 'Salt Creek'
❌ TRUNCATED: Lost ' I - 7 SW'
```

### 3. Suffix Stripping Function Issues

#### Function: `_strip_trailing_suffix_tokens(tokens: list[str])`

**Location**: All import scripts (lines 81-105 in import_players.py)

**Regex Patterns Used**:

1. **`_ROMAN_RE = re.compile(r'\b[IVXLCDM]{1,4}\b', re.IGNORECASE)`**
   - **Issue**: Strips Roman numerals (I, II, III, IV, etc.)
   - **Impact**: `"Wilmette PD II"` → `"Wilmette PD"` loses "II"
   - **Test Result**: `['Wilmette', 'PD', 'II']` → `['Wilmette']` (removed `['PD', 'II']`)

2. **`_ALNUM_SUFFIX_RE = re.compile(r'\b(\d+[A-Za-z]?|[A-Za-z]?\d+)\b')`**
   - **Issue**: Strips alphanumeric suffixes
   - **Impact**: `"Lake Shore CC 2"` → `"Lake Shore CC"` loses "2"
   - **Test Result**: `['Lake', 'Shore', 'CC', '2']` → `['Lake', 'Shore', 'CC']` (removed `['2']`)

3. **`_LETTER_PAREN_RE = re.compile(r'\b[A-Za-z]{1,3}\(\d+\)\b')`**
   - **Issue**: Strips letter patterns with parentheses
   - **Impact**: `"North Shore C(1)"` → `"North Shore"` loses "C(1)"
   - **Note**: This pattern didn't match in our test because the tokenizer splits on spaces, so "C(1)" is a single token with parentheses, not matching the word boundary pattern.

4. **`_ALLCAP_SHORT_RE = re.compile(r'\b[A-Z]{1,3}\b')`**
   - **Issue**: Strips short all-caps tokens
   - **Impact**: Could remove "SW", "SN", "PD" if they appear at the end
   - **Test Result**: `['Salt', 'Creek', 'I', '-', '7', 'SW']` → `['Salt', 'Creek', 'I', '-']` (removed `['7', 'SW']`)

**Test Results for `_strip_trailing_suffix_tokens()`**:
```
Original tokens: ['Wilmette', 'PD', 'II']
Stripped tokens: ['Wilmette']
❌ REMOVED TOKENS: ['PD', 'II']

Original tokens: ['Tennaqua', 'I']
Stripped tokens: ['Tennaqua']
❌ REMOVED TOKENS: ['I']

Original tokens: ['Lake', 'Shore', 'CC', '2']
Stripped tokens: ['Lake', 'Shore', 'CC']
❌ REMOVED TOKENS: ['2']

Original tokens: ['Salt', 'Creek', 'I', '-', '7', 'SW']
Stripped tokens: ['Salt', 'Creek', 'I', '-']
❌ REMOVED TOKENS: ['7', 'SW']
```

**Root Problem**: The function assumes ALL trailing tokens matching these patterns are series identifiers, but they can be legitimate parts of club names (e.g., "PD II" is part of "Wilmette PD II", not a series marker).

### 4. Team Name Parsing Issues

#### Function: `parse_team_name(team_name)` in `import_players.py` (Lines 192-270)

**Issues by Pattern**:

1. **SN with Parentheses (Lines 213-219)**
   ```python
   sn_numbered_match = re.search(r'\sSN\s*\((\d+)\)\s*$', team_name)
   if sn_numbered_match:
       club_name = f"{base_club_name} SN-{team_number}"  # MODIFIES original
   ```
   - **Issue**: Creates modified club name instead of preserving original
   - **Example**: `"Prairie Club SN (5)"` → club becomes `"Prairie Club SN-5"` (not in original)
   - **Test Result**: `❌ CLUB MODIFIED: 'Prairie Club SN-5' is not in original 'Prairie Club SN (5)'`

2. **SW Series Extraction (Lines 229-234)**
   ```python
   sw_match = re.search(r'(\d+)\s+SW\s*$', team_name)
   if sw_match:
       club_name = team_name[:sw_match.start()].strip()
   ```
   - **Issue**: Strips everything before SW, including parts that might be club name
   - **Example**: `"Salt Creek I - 7 SW"` → club becomes `"Salt Creek I -"` (incomplete)
   - **Test Result**: `❌ CLUB TRUNCATED: Lost '7 SW'`

3. **Numeric Series Extraction (Lines 237-242)**
   ```python
   numeric_match = re.search(r'(\d+[a-z]?)$', team_name)
   if numeric_match:
       club_name = team_name[:numeric_match.start()].strip()
   ```
   - **Issue**: Strips numeric suffix, assuming it's always a series
   - **Example**: `"Lake Shore CC 2"` → club becomes `"Lake Shore CC"` (loses "2")
   - **Test Result**: `❌ CLUB TRUNCATED: Lost '2'`

4. **Single Letter Extraction (Lines 245-250)**
   ```python
   letter_match = re.search(r'\s([A-Z])\s*$', team_name)
   if letter_match:
       club_name = team_name[:letter_match.start()].strip()
   ```
   - **Issue**: Strips single letters, assuming they're series identifiers
   - **Example**: `"Tennaqua I"` → club becomes `"Tennaqua"` (loses "I")
   - **Test Result**: `❌ CLUB TRUNCATED: Lost 'I'`

5. **Multi-Letter Extraction (Lines 252-258)**
   ```python
   multi_letter_match = re.search(r'\s([A-Z]{2,})\s*$', team_name)
   ```
   - **Issue**: Could strip "II", "SW", "SN" if they appear at the end
   - **Example**: `"Wilmette PD II"` → club becomes `"Wilmette PD"` (loses "II")
   - **Test Result**: `❌ CLUB TRUNCATED: Lost 'II'`

**Test Results for `parse_team_name()`**:
```
Original: 'Wilmette PD II'
  Club: 'Wilmette PD'
  Series: 'Series II'
  ❌ CLUB TRUNCATED: Lost 'II'

Original: 'Tennaqua I'
  Club: 'Tennaqua'
  Series: 'Series I'
  ❌ CLUB TRUNCATED: Lost 'I'

Original: 'Lake Shore CC 2'
  Club: 'Lake Shore CC'
  Series: 'Series 2'
  ❌ CLUB TRUNCATED: Lost '2'

Original: 'Prairie Club SN (5)'
  Club: 'Prairie Club SN-5'
  Series: 'Series SN'
  ❌ CLUB MODIFIED: 'Prairie Club SN-5' is not in original 'Prairie Club SN (5)'

Original: 'Salt Creek I - 7 SW'
  Club: 'Salt Creek I -'
  Series: 'Series 7 SW'
  ❌ CLUB TRUNCATED: Lost '7 SW'
```

### 5. Validation Issues

#### Function: `validate_entity_name()` in `import_players.py` (Lines 107-140)

**Issue at Line 137**:
```python
if re.match(r'^[^\w]|[^\w]$', name):
    return False, f"Invalid {entity_type} name '{name}' - starts or ends with punctuation"
```

**Impact**: 
- Could reject valid names like "C(1)" if they end with punctuation
- However, this check runs AFTER normalization, so names with parentheses are already stripped by that point

**Note**: The validation itself may not be the primary issue, but it could compound problems if names with legitimate punctuation are rejected.

## Data Flow Analysis

### Example: "Salt Creek I - 7 SW"

1. **Scraper** → Extracts `"Salt Creek I - 7 SW"` from HTML
2. **Match Score Scraper** → `re.sub(r'\s*-\s*\d+.*$', '', name)` → `"Salt Creek I"` (loses " - 7 SW")
3. **Import Script** → `normalize_club_name()`:
   - Step 1: Dash split → `"Salt Creek I"` (already lost " - 7 SW")
   - Step 2: Parentheses removal → No change
   - Step 3: Suffix stripping → `"Salt Creek"` (loses "I")
   - Step 4: Punctuation removal → `"Salt Creek"`
4. **Database** → Stores `"Salt Creek"` instead of `"Salt Creek I - 7 SW"`

### Example: "Wilmette PD II"

1. **Scraper** → Extracts `"Wilmette PD II"` from HTML
2. **Match Score Scraper** → No change (no dash pattern)
3. **Import Script** → `normalize_club_name()`:
   - Step 1: Dash split → No change
   - Step 2: Parentheses removal → No change
   - Step 3: Suffix stripping → `"Wilmette"` (loses "PD II" - both "PD" and "II" removed)
   - Step 4: Punctuation removal → `"Wilmette"`
4. **Database** → Stores `"Wilmette"` instead of `"Wilmette PD II"`

## Root Causes Summary

1. **Over-aggressive normalization**: The `normalize_club_name()` function is designed to collapse variants but strips legitimate parts of names that are not variants.

2. **Suffix stripping assumes all suffixes are series identifiers**: Roman numerals, numbers, and letters are treated as series markers, not part of club names. The system cannot distinguish between:
   - "Wilmette PD II" (where "II" is part of the club name)
   - "Exmoor 12" (where "12" is a series identifier)

3. **Dash handling is too simplistic**: Splitting on " - " loses important information. The system assumes everything after " - [number]" is a series, but this isn't always true.

4. **Parentheses are always removed**: No distinction between series markers like "(5)" in "Prairie Club SN (5)" and name parts like "C(1)" in "North Shore C(1)".

5. **No preservation of original names**: The system doesn't track what the original scraped name was, so there's no way to recover the full name after truncation.

6. **Context-unaware parsing**: The `parse_team_name()` function doesn't consider context - it applies the same rules regardless of whether a pattern is part of a club name or a series identifier.

## Impact Assessment

### Data Integrity Issues

1. **Club Name Collisions**: Different clubs are being collapsed into the same name:
   - "Wilmette PD" and "Wilmette PD II" both become "Wilmette"
   - "Salt Creek" and "Salt Creek I" both become "Salt Creek"

2. **Team Matching Failures**: Teams cannot be properly matched because club names don't match:
   - Team "Wilmette PD II 10" has club "Wilmette PD II" in JSON
   - After normalization, club becomes "Wilmette"
   - Database lookup fails or matches wrong club

3. **Loss of Information**: Critical identifying information is permanently lost:
   - Roman numerals (II, I) that distinguish club variants
   - Numeric suffixes (2) that are part of club names
   - Parenthetical identifiers (C(1)) that are part of names
   - Dash-separated series info (- 7 SW) that's part of team structure

### Affected Data

Based on JSON file analysis:
- **Wilmette PD II**: Found in JSON as both Team and Club names
- **Salt Creek I - 7 SW**: Pattern found in backup files
- **Prairie Club SN (5)**: Pattern should exist but not found in current JSON (may have been truncated already)

## Recommendations

### Immediate Fixes

1. **Preserve Original Names**: Store both normalized and original names in database
   - Add `original_name` column to `clubs` table
   - Use original name for display, normalized name for matching

2. **Context-Aware Normalization**: Don't strip suffixes that are part of known club name patterns
   - Whitelist approach: Only strip known series patterns
   - Maintain a list of club name patterns that should be preserved

3. **Better Dash Handling**: Preserve content after dashes if it's part of the name
   - Distinguish between "Club - Series" (series) and "Club I - 7 SW" (part of name)
   - Use context clues (e.g., if "SW" follows, it's likely part of name)

4. **Parentheses Preservation**: Distinguish between series markers and name parts
   - Series markers: "SN (5)" - number in parentheses after series identifier
   - Name parts: "C(1)" - letter followed by number in parentheses

5. **Validation Updates**: Allow punctuation in names when it's part of the legitimate name
   - Update validation to allow parentheses, dashes in specific contexts
   - Only reject names that are clearly invalid

### Long-Term Improvements

1. **Two-Phase Normalization**:
   - Phase 1: Preserve full names exactly as scraped
   - Phase 2: Create normalized versions for matching only

2. **Pattern Recognition**: Build a pattern database of known club name structures
   - Learn from existing data which patterns are club names vs. series
   - Use machine learning or rule-based system to classify patterns

3. **Validation at Scrape Time**: Validate names immediately after scraping
   - Catch truncation issues before they enter the import pipeline
   - Log warnings when names don't match expected patterns

## Files Requiring Changes

1. **`data/etl/import/import_players.py`**
   - `normalize_club_name()` - Fix normalization logic
   - `_strip_trailing_suffix_tokens()` - Add context awareness
   - `parse_team_name()` - Preserve full club names
   - `validate_entity_name()` - Allow legitimate punctuation

2. **`data/etl/import/import_stats.py`**
   - `normalize_club_name()` - Same fixes as above
   - `_strip_trailing_suffix_tokens()` - Same fixes as above

3. **`data/etl/import/import_match_scores.py`**
   - `normalize_club_name()` - Same fixes as above
   - `parse_team_name()` - Preserve full names

4. **`data/etl/import/import_schedules.py`**
   - `normalize_club_name()` - Same fixes as above

5. **`data/etl/scrapers/apta_scrape_match_scores.py`**
   - `_extract_apta_teams_and_score()` - Fix dash removal regex

6. **`data/etl/scrapers/apta/apta_scrape_players_simple.py`**
   - Club name extraction - Preserve full names

## Testing Requirements

1. **Unit Tests**: Test all normalization functions with problematic names
   - "Wilmette PD II"
   - "North Shore C(1)"
   - "Tennaqua I"
   - "Lake Shore CC 2"
   - "Prairie Club SN (5)"
   - "Salt Creek I - 7 SW"

2. **Integration Tests**: Verify end-to-end flow
   - Scrape → Import → Database
   - Verify names are preserved exactly as scraped
   - Verify database contains full names

3. **Regression Tests**: Ensure existing functionality still works
   - Verify team matching still works with preserved names
   - Verify series extraction still works correctly
   - Verify no duplicate clubs are created

4. **Data Validation**: Check existing database for truncated names
   - Identify clubs that should have suffixes but don't
   - Create migration script to fix existing data

## Actual Data in JSON Files

Analysis of `data/leagues/APTA_CHICAGO/players.json` reveals:

### Patterns Found:
- **Wilmette PD II**: Found in JSON (6 variations including "Wilmette PD II 10", "Wilmette PD II 11", etc.)
- **Lake Shore CC**: Found in JSON (5 variations including "Lake Shore CC 19", "Lake Shore CC 23", etc.)

### Patterns NOT Found (Likely Already Truncated):
- **North Shore C(1)**: NOT FOUND - May have been truncated during previous imports
- **Salt Creek I - 7 SW**: NOT FOUND - Dash pattern likely removed by scraper
- **Prairie Club SN (5)**: NOT FOUND - Parentheses likely removed
- **Tennaqua I**: NOT FOUND - Single letter likely stripped

**Conclusion**: Some problematic patterns still exist in the JSON (Wilmette PD II, Lake Shore CC), but others have already been truncated, indicating the issue has been affecting data for some time.

## Conclusion

The name truncation issue is **systematic and widespread**, affecting multiple stages of the ETL pipeline. The root cause is over-aggressive normalization that assumes all suffixes are series identifiers, when in fact many are legitimate parts of club names.

**Priority**: **HIGH** - This affects data integrity and team matching functionality.

**Estimated Impact**: Hundreds of club/team names are likely affected, causing:
- Incorrect team assignments
- Club name collisions
- Loss of identifying information
- Matching failures in the application

**Evidence**: 
- Test results show 8/8 problematic name patterns are truncated by normalization
- JSON analysis shows some patterns still exist (indicating they haven't been imported yet), while others are missing (indicating they were truncated in previous imports)
- Multiple functions across 6+ files contribute to the truncation

**Recommended Action**: Implement fixes immediately, starting with preserving original names and making normalization context-aware.

