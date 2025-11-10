# Specific Code Patterns That Need Fixing

This document lists the exact code patterns that need to be fixed to prevent club/team name truncation.

## Pattern 1: Dash Removal Regex in Match Score Scrapers

### Location 1: `data/etl/scrapers/apta_scrape_match_scores.py` (Lines 1718-1719)
**Current Code**:
```python
away_team = re.sub(r'\s*-\s*\d+.*$', '', away_part).strip()
home_team = re.sub(r'\s*-\s*\d+.*$', '', home_part).strip()
```

**Problem**: Removes everything after " - [number]", including legitimate parts like " - 7 SW"

**Fix Needed**: Make regex context-aware - only remove if it's clearly a series identifier, not part of club name

---

### Location 2: `data/etl/scrapers/cnswpl_scrape_match_scores.py` (Lines 2030-2031)
**Current Code**:
```python
away_team = re.sub(r'\s*-\s*\d+.*$', '', away_part).strip()
home_team = re.sub(r'\s*-\s*\d+.*$', '', home_part).strip()
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

## Pattern 2: Dash Splitting in normalize_club_name()

### Location 1: `data/etl/import/import_players.py` (Lines 53-54)
**Current Code**:
```python
if " - " in name:
    name = name.split(" - ")[0].strip()
```

**Problem**: Always removes everything after " - "

**Fix Needed**: Only split if it's clearly a series separator, preserve if it's part of name (e.g., "Salt Creek I - 7 SW")

---

### Location 2: `data/etl/import/import_stats.py` (Lines 53-54)
**Current Code**:
```python
if " - " in name:
    name = name.split(" - ")[0].strip()
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

### Location 3: `data/etl/import/import_match_scores.py` (Lines 60-61)
**Current Code**:
```python
if " - " in text:
    text = text.split(" - ")[0]
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

### Location 4: `data/etl/import/import_schedules.py` (Lines 90-91)
**Current Code**:
```python
if " - " in base:
    base = base.split(" - ")[0].strip()
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

### Location 5: `data/etl/import/start_season.py` (Line 86)
**Current Code**:
```python
s = s.split(' - ')[0].strip()
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

## Pattern 3: Parentheses Removal in normalize_club_name()

### Location 1: `data/etl/import/import_players.py` (Line 57)
**Current Code**:
```python
name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
```

**Problem**: Removes ALL trailing parentheses, including legitimate ones like "C(1)" in "North Shore C(1)"

**Fix Needed**: Distinguish between series markers "(5)" after "SN" vs. name parts "C(1)"

---

### Location 2: `data/etl/import/import_stats.py` (Line 57)
**Current Code**:
```python
name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

### Location 3: `data/etl/import/import_match_scores.py` (Line 64)
**Current Code**:
```python
text = re.sub(r'\s*\([^)]*\)\s*$', '', text)
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

### Location 4: `data/etl/import/import_schedules.py` (Line 94)
**Current Code**:
```python
base = re.sub(r'\s*\([^)]*\)\s*$', '', base).strip()
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

## Pattern 4: Suffix Token Stripping - Roman Numerals

### All Import Scripts: `_strip_trailing_suffix_tokens()` (Lines 90-91)
**Current Code**:
```python
if _ROMAN_RE.fullmatch(t):
    tokens.pop()
    continue
```

**Problem**: Always strips Roman numerals (I, II, III, etc.), even when part of club name like "Wilmette PD II"

**Files Affected**:
- `data/etl/import/import_players.py` (line 90)
- `data/etl/import/import_stats.py` (line 90)
- `data/etl/import/import_match_scores.py` (line 89)
- `data/etl/import/import_schedules.py` (line 54)
- `data/etl/import/start_season.py` (line 49)
- `data/etl/import/helper/load_club_addresses_from_csv.py` (line 42)

**Fix Needed**: Only strip Roman numerals if they're clearly series identifiers (e.g., at end of team name with series context), not when part of club name

---

## Pattern 5: Suffix Token Stripping - Alphanumeric Suffixes

### All Import Scripts: `_strip_trailing_suffix_tokens()` (Lines 93-94)
**Current Code**:
```python
if _ALNUM_SUFFIX_RE.fullmatch(t):
    tokens.pop()
    continue
```

**Problem**: Always strips numeric/alphanumeric suffixes, even when part of club name like "Lake Shore CC 2"

**Files Affected**: Same as Pattern 4

**Fix Needed**: Only strip if clearly a series number (e.g., standalone number after club name), not when part of club identifier

---

## Pattern 6: Suffix Token Stripping - Letter Patterns with Parentheses

### All Import Scripts: `_strip_trailing_suffix_tokens()` (Lines 96-97)
**Current Code**:
```python
if _LETTER_PAREN_RE.fullmatch(t):
    tokens.pop()
    continue
```

**Problem**: Strips patterns like "C(1)" even when part of club name like "North Shore C(1)"

**Files Affected**: Same as Pattern 4

**Fix Needed**: Only strip if clearly a series marker, not when part of club name structure

---

## Pattern 7: Suffix Token Stripping - Short All-Caps Tokens

### All Import Scripts: `_strip_trailing_suffix_tokens()` (Lines 99-100)
**Current Code**:
```python
if _ALLCAP_SHORT_RE.fullmatch(t):
    tokens.pop()
    continue
```

**Problem**: Strips short all-caps tokens like "SW", "SN", "PD" when they appear at the end, even if part of name

**Files Affected**: Same as Pattern 4

**Fix Needed**: Only strip if clearly a series identifier, preserve if part of club name (e.g., "PD" in "Wilmette PD II")

---

## Pattern 8: Punctuation Removal in normalize_club_name()

### All Import Scripts: normalize_club_name() (Line 65)
**Current Code**:
```python
name = re.sub(r'[^\w\s&]', '', name)
```

**Problem**: Removes all punctuation including parentheses and dashes that might be part of legitimate names

**Files Affected**:
- `data/etl/import/import_players.py` (line 65)
- `data/etl/import/import_stats.py` (line 65)
- `data/etl/import/import_match_scores.py` (line 72)
- `data/etl/import/import_schedules.py` (line 109)

**Fix Needed**: Preserve parentheses and dashes when they're part of the name structure (e.g., "C(1)", " - 7 SW")

---

## Pattern 9: Team Name Parsing - SN with Parentheses Modification

### Location: `data/etl/import/import_players.py` (Lines 213-219)
**Current Code**:
```python
sn_numbered_match = re.search(r'\sSN\s*\((\d+)\)\s*$', team_name)
if sn_numbered_match:
    team_number = sn_numbered_match.group(1)
    base_club_name = team_name[:sn_numbered_match.start()].strip()
    club_name = f"{base_club_name} SN-{team_number}"  # MODIFIES original
    series_name = "Series SN"
    return club_name, series_name, f"SN ({team_number})"
```

**Problem**: Modifies club name from "Prairie Club SN (5)" to "Prairie Club SN-5" instead of preserving original

**Fix Needed**: Preserve original club name, don't modify it

---

## Pattern 10: Team Name Parsing - SW Series Extraction

### Location: `data/etl/import/import_players.py` (Lines 229-234)
**Current Code**:
```python
sw_match = re.search(r'(\d+)\s+SW\s*$', team_name)
if sw_match:
    team_number = sw_match.group(1)
    club_name = team_name[:sw_match.start()].strip()
    series_name = f"Series {team_number} SW"
    return club_name, series_name, f"{team_number} SW"
```

**Problem**: For "Salt Creek I - 7 SW", extracts club as "Salt Creek I -" (incomplete) because dash is still in the name

**Fix Needed**: Handle dash-separated SW patterns correctly, preserve full club name

---

## Pattern 11: Team Name Parsing - Numeric Series Extraction

### Location: `data/etl/import/import_players.py` (Lines 237-242)
**Current Code**:
```python
numeric_match = re.search(r'(\d+[a-z]?)$', team_name)
if numeric_match:
    team_number = numeric_match.group(1)
    club_name = team_name[:numeric_match.start()].strip()
    series_name = f"Series {team_number}"
    return club_name, series_name, team_number
```

**Problem**: Strips numeric suffix from "Lake Shore CC 2", assuming "2" is always a series, but it's part of club name

**Fix Needed**: Only extract as series if it's clearly a series identifier, not part of club name

---

## Pattern 12: Team Name Parsing - Single Letter Extraction

### Location: `data/etl/import/import_players.py` (Lines 245-250)
**Current Code**:
```python
letter_match = re.search(r'\s([A-Z])\s*$', team_name)
if letter_match:
    team_letter = letter_match.group(1)
    club_name = team_name[:letter_match.start()].strip()
    series_name = f"Series {team_letter}"
    return club_name, series_name, team_letter
```

**Problem**: Strips single letter from "Tennaqua I", assuming "I" is always a series, but it's part of club name

**Fix Needed**: Only extract as series if it's clearly a series identifier, not part of club name

---

## Pattern 13: Team Name Parsing - Multi-Letter Extraction

### Location: `data/etl/import/import_players.py` (Lines 252-258)
**Current Code**:
```python
multi_letter_match = re.search(r'\s([A-Z]{2,})\s*$', team_name)
if multi_letter_match:
    team_letters = multi_letter_match.group(1)
    club_name = team_name[:multi_letter_match.start()].strip()
    series_name = f"Series {team_letters}"
    return club_name, series_name, team_letters
```

**Problem**: Could strip "II" from "Wilmette PD II", assuming it's a series, but it's part of club name

**Fix Needed**: Only extract as series if it's clearly a series identifier, not part of club name

---

## Pattern 14: Dash Splitting in Scrapers

### Location 1: `data/etl/scrapers/apta/apta_scrape_players_simple.py` (Lines 803, 890)
**Current Code**:
```python
parts = team_name.split(' - ')
```

**Problem**: Splits on dash and may lose important information

**Fix Needed**: Preserve full team name, don't split unnecessarily

---

### Location 2: `data/etl/scrapers/apta/apta_scrape_players_detailed.py` (Line 925)
**Current Code**:
```python
parts = clean_team_name.split(' - ')
```

**Problem**: Same as above

**Fix Needed**: Same fix as Location 1

---

## Summary of Files Requiring Changes

### High Priority (Core Import Functions):
1. `data/etl/import/import_players.py` - 4 patterns (normalize, strip, parse, dash split)
2. `data/etl/import/import_stats.py` - 3 patterns (normalize, strip, dash split)
3. `data/etl/import/import_match_scores.py` - 4 patterns (normalize, strip, parse, dash split)
4. `data/etl/import/import_schedules.py` - 3 patterns (normalize, strip, dash split)

### Medium Priority (Scrapers):
5. `data/etl/scrapers/apta_scrape_match_scores.py` - 1 pattern (dash regex)
6. `data/etl/scrapers/cnswpl_scrape_match_scores.py` - 1 pattern (dash regex)
7. `data/etl/scrapers/apta/apta_scrape_players_simple.py` - 1 pattern (dash split)
8. `data/etl/scrapers/apta/apta_scrape_players_detailed.py` - 1 pattern (dash split)

### Lower Priority (Helper/Season):
9. `data/etl/import/start_season.py` - 2 patterns (normalize, strip)
10. `data/etl/import/helper/load_club_addresses_from_csv.py` - 2 patterns (normalize, strip)

## Total Patterns to Fix: 14 unique patterns across 10 files

## Key Principles for Fixes

1. **Preserve Original Names**: Store both original and normalized versions
2. **Context-Aware Parsing**: Distinguish between series identifiers and name parts
3. **Whitelist Approach**: Only strip known series patterns, not all matching patterns
4. **Pattern Recognition**: Use context clues (e.g., "SW" after dash is likely part of name)
5. **Validation Updates**: Allow legitimate punctuation in names






