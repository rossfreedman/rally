# Club/Team Name Parsing Pattern Summary

## Understanding the Pattern

The user has clarified the exact parsing rules. Here's what needs to happen:

### Key Principle
**Club names = base identifier (strip all series/team identifiers)**  
**Team names = full identifier (preserve series info, remove dashes)**

---

## Examples and Expected Results

| Input | Club Name | Team Name |
|-------|-----------|-----------|
| `Prairie Club SN (3)` | `Prairie Club` | `Prairie Club SN (3)` |
| `Sunset Ridge 5a` | `Sunset Ridge` | `Sunset Ridge 5a` |
| `Wilmette C(1)` | `Wilmette` | `Wilmette C(1)` |
| `Winnetka SN (2)` | `Winnetka` | `Winnetka SN (2)` |
| `Winnetka SN (3)` | `Winnetka` | `Winnetka SN (3)` |
| `Winnetka SN (4)` | `Winnetka` | `Winnetka SN (4)` |
| `Saddle & Cycle - 2` | `Saddle & Cycle` | `Saddle & Cycle 2` |
| `LaGrange CC - 7 SW` | `LaGrange CC` | `LaGrange CC 7 SW` |
| `Hinsdale PC II - 9 SW` | `Hinsdale PC` | `Hinsdale PC II 9 SW` |

---

## Pattern Recognition Rules

### 1. SN (Sunday Night) with Parentheses
- **Pattern**: `... SN (number)`
- **Club**: Strip `SN (number)`
- **Team**: Keep full name `... SN (number)`
- **Example**: `Prairie Club SN (3)` → Club: `Prairie Club`, Team: `Prairie Club SN (3)`

### 2. Numeric/Alphanumeric Suffix
- **Pattern**: `... number` or `... numberLetter`
- **Club**: Strip suffix
- **Team**: Keep full name
- **Example**: `Sunset Ridge 5a` → Club: `Sunset Ridge`, Team: `Sunset Ridge 5a`

### 3. Letter with Parentheses
- **Pattern**: `... Letter(number)`
- **Club**: Strip `Letter(number)`
- **Team**: Keep full name
- **Example**: `Wilmette C(1)` → Club: `Wilmette`, Team: `Wilmette C(1)`

### 4. Dash with Number
- **Pattern**: `... - number`
- **Club**: Strip ` - number`
- **Team**: Remove dash, keep number → `... number`
- **Example**: `Saddle & Cycle - 2` → Club: `Saddle & Cycle`, Team: `Saddle & Cycle 2`

### 5. Dash with Number and SW
- **Pattern**: `... - number SW`
- **Club**: Strip ` - number SW`
- **Team**: Remove dash, keep `number SW` → `... number SW`
- **Example**: `LaGrange CC - 7 SW` → Club: `LaGrange CC`, Team: `LaGrange CC 7 SW`

### 6. Roman Numeral with Dash and SW
- **Pattern**: `... RomanNumeral - number SW`
- **Club**: Strip `RomanNumeral - number SW` (Roman numeral is NOT part of base club)
- **Team**: Remove dash, keep `RomanNumeral number SW` → `... RomanNumeral number SW`
- **Example**: `Hinsdale PC II - 9 SW` → Club: `Hinsdale PC`, Team: `Hinsdale PC II 9 SW`

---

## Critical Insights

1. **Roman Numerals**: When followed by dash+series, they're NOT part of base club name
   - `Hinsdale PC II - 9 SW` → Club is `Hinsdale PC` (not `Hinsdale PC II`)
   - But team keeps the Roman numeral: `Hinsdale PC II 9 SW`

2. **Dashes**: Always removed from team names, but series info is preserved
   - ` - 2` → `2`
   - ` - 7 SW` → `7 SW`

3. **Parentheses Patterns**:
   - `SN (number)` → Series identifier, strip from club
   - `Letter(number)` → Series identifier, strip from club

4. **Club Type Suffixes**: Always preserved
   - `CC`, `PC`, `GC`, `RC`, `TC`, `AC` stay in club name

---

## Current Code Issues

### Issue 1: SN with Parentheses
**Current**: `parse_team_name("Prairie Club SN (3)")` returns:
- Club: `"Prairie Club SN-3"` ❌ (WRONG - modifies name)
- Should be: Club: `"Prairie Club"` ✅

**Fix**: Don't modify club name, just strip `SN (number)` pattern

### Issue 2: Letter with Parentheses
**Current**: Not handled at all
- `Wilmette C(1)` → Returns `None, None, None` ❌

**Fix**: Add pattern matching for `Letter(number)`

### Issue 3: Dash with Number
**Current**: `normalize_club_name()` strips everything after dash
- `Saddle & Cycle - 2` → Club: `"Saddle & Cycle"` ✅ (correct)
- But team name handling needs dash removal

**Fix**: In team name, remove dash but keep number

### Issue 4: Dash with SW
**Current**: `normalize_club_name()` strips everything after dash
- `LaGrange CC - 7 SW` → Club: `"LaGrange CC"` ✅ (correct)
- But team name needs: `"LaGrange CC 7 SW"` (remove dash)

**Fix**: In team name, remove dash but keep `number SW`

### Issue 5: Roman Numeral with Dash and SW
**Current**: Not handled correctly
- `Hinsdale PC II - 9 SW` → Current code would keep `II` in club name ❌
- Should be: Club: `"Hinsdale PC"`, Team: `"Hinsdale PC II 9 SW"`

**Fix**: When Roman numeral is followed by dash+series, strip it from club name but keep in team name

---

## Implementation Strategy

1. **Update `parse_team_name()`** to:
   - Return full team name (not modified)
   - Return base club name (with series identifiers stripped)
   - Handle all 6 patterns in correct order

2. **Update `normalize_club_name()`** to:
   - Only strip series identifiers, not parts of legitimate names
   - Preserve Roman numerals when NOT followed by dash+series
   - Preserve club type suffixes

3. **Order of Pattern Matching** (most specific first):
   1. `SN (number)` - Most specific
   2. `RomanNumeral - number SW` - Specific pattern
   3. ` - number SW` - SW series with dash
   4. `Letter(number)` - Letter series with parentheses
   5. ` - number` - Generic dash with number
   6. `number SW` - SW without dash
   7. `number` or `numberLetter` - Generic numeric suffix
   8. `Letter` - Single letter series

---

## Testing Checklist

- [ ] `Prairie Club SN (3)` → Club: `Prairie Club`, Team: `Prairie Club SN (3)`
- [ ] `Sunset Ridge 5a` → Club: `Sunset Ridge`, Team: `Sunset Ridge 5a`
- [ ] `Wilmette C(1)` → Club: `Wilmette`, Team: `Wilmette C(1)`
- [ ] `Winnetka SN (2)` → Club: `Winnetka`, Team: `Winnetka SN (2)`
- [ ] `Saddle & Cycle - 2` → Club: `Saddle & Cycle`, Team: `Saddle & Cycle 2`
- [ ] `LaGrange CC - 7 SW` → Club: `LaGrange CC`, Team: `LaGrange CC 7 SW`
- [ ] `Hinsdale PC II - 9 SW` → Club: `Hinsdale PC`, Team: `Hinsdale PC II 9 SW`
- [ ] `Wilmette PD II` (no series) → Club: `Wilmette PD II`, Team: `Wilmette PD II`






