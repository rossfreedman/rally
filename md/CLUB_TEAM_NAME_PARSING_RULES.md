# Club and Team Name Parsing Rules

## Core Principle

**Club names should be the base identifier, stripped of series/team identifiers. Team names should preserve the full identifier including series information.**

## Pattern Rules

### Rule 1: SN (Sunday Night) with Parentheses
**Pattern**: `ClubName SN (number)`

**Examples**:
- `Prairie Club SN (3)` → Club: `Prairie Club`, Team: `Prairie Club SN (3)`
- `Winnetka SN (2)` → Club: `Winnetka`, Team: `Winnetka SN (2)`
- `Winnetka SN (3)` → Club: `Winnetka`, Team: `Winnetka SN (3)`
- `Winnetka SN (4)` → Club: `Winnetka`, Team: `Winnetka SN (4)`

**Logic**: 
- "SN" is a series identifier
- The number in parentheses is part of the team identifier
- Strip "SN (number)" from club name, keep full string for team name

---

### Rule 2: Numeric/Alphanumeric Series Suffix
**Pattern**: `ClubName number` or `ClubName numberLetter`

**Examples**:
- `Sunset Ridge 5a` → Club: `Sunset Ridge`, Team: `Sunset Ridge 5a`
- `Lake Shore CC 2` → Club: `Lake Shore CC`, Team: `Lake Shore CC 2`

**Logic**:
- Numeric or alphanumeric suffix (like "5a", "2", "23") is a series identifier
- Strip from club name, keep in team name

---

### Rule 3: Letter with Parentheses
**Pattern**: `ClubName Letter(number)`

**Examples**:
- `Wilmette C(1)` → Club: `Wilmette`, Team: `Wilmette C(1)`
- `North Shore C(1)` → Club: `North Shore`, Team: `North Shore C(1)`

**Logic**:
- Single letter followed by parentheses with number is a series identifier
- Strip from club name, keep in team name

---

### Rule 4: Dash with Number (Series Separator)
**Pattern**: `ClubName - number`

**Examples**:
- `Saddle & Cycle - 2` → Club: `Saddle & Cycle`, Team: `Saddle & Cycle 2`
- Note: Remove dash, keep number as part of team name

**Logic**:
- Dash followed by number is a series separator
- Remove dash from team name, keep number
- Strip from club name entirely

---

### Rule 5: Dash with Number and SW (Summer/Winter Series)
**Pattern**: `ClubName - number SW` or `ClubName - number SW`

**Examples**:
- `LaGrange CC - 7 SW` → Club: `LaGrange CC`, Team: `LaGrange CC 7 SW`
- `Salt Creek I - 7 SW` → Club: `Salt Creek I`, Team: `Salt Creek I 7 SW`

**Logic**:
- Dash followed by number and "SW" is a series identifier
- Remove dash from team name, keep "number SW"
- Strip from club name entirely

---

### Rule 6: Roman Numerals with Dash and SW
**Pattern**: `ClubName RomanNumeral - number SW`

**Examples**:
- `Hinsdale PC II - 9 SW` → Club: `Hinsdale PC`, Team: `Hinsdale PC II 9 SW`
- Note: Roman numeral is stripped from club name but kept in team name

**Logic**:
- When Roman numeral is followed by dash and series, it's NOT part of base club name
- Strip Roman numeral AND " - number SW" from club name
- For team name: remove dash, keep "RomanNumeral number SW"

---

### Rule 7: Roman Numerals (Standalone)
**Pattern**: `ClubName RomanNumeral` (without dash/series)

**Examples**:
- `Wilmette PD II` → Club: `Wilmette PD II`, Team: `Wilmette PD II` (if no series)
- `Hinsdale PC II` → Club: `Hinsdale PC II`, Team: `Hinsdale PC II` (if no series)

**Logic**:
- Roman numerals are part of club name when NOT followed by dash/series
- Keep in both club and team names

---

## Key Distinctions

### What to Strip from Club Names:
1. ✅ Series identifiers: `SN (number)`, `SW`, `number SW`
2. ✅ Series numbers: `2`, `5a`, `23`, etc.
3. ✅ Letter series with parentheses: `C(1)`, `H(3)`, etc.
4. ✅ Dash-separated series: ` - 2`, ` - 7 SW`

### What to Keep in Club Names:
1. ✅ Roman numerals when part of name: `PD II`, `PC II` (when not followed by dash/series)
2. ✅ Club type suffixes: `CC`, `PC`, `GC`, `RC`, `TC`, `AC`
3. ✅ All base club name words

### What to Keep in Team Names:
1. ✅ Full original name with series identifiers
2. ✅ Remove dashes but keep series info: `- 2` → `2`, `- 7 SW` → `7 SW`

---

## Parsing Algorithm

```
1. Check for SN (number) pattern
   - If found: Club = name before "SN (number)", Team = full name

2. Check for dash with number SW pattern
   - If found: Club = name before " - number SW", Team = name with dash removed

3. Check for dash with number pattern
   - If found: Club = name before " - number", Team = name with dash removed

4. Check for letter(number) pattern
   - If found: Club = name before "Letter(number)", Team = full name

5. Check for numeric/alphanumeric suffix
   - If found: Club = name before suffix, Team = full name

6. Check for Roman numeral at end
   - If followed by dash/series: Part of club name, strip series
   - If standalone: Keep in club name
```

---

## Edge Cases to Handle

1. **Multiple dashes**: `Club Name - Series - Extra` → Only remove first dash pattern
2. **Spaces in parentheses**: `SN ( 3 )` → Normalize to `SN (3)`
3. **Case sensitivity**: `sn (3)` vs `SN (3)` → Normalize to uppercase
4. **Club type preservation**: `Lake Shore CC` → Keep "CC" in club name
5. **Ampersand preservation**: `Saddle & Cycle` → Keep "&" in club name

---

## Implementation Notes

1. **Preserve original team name**: Always store the full team name as scraped
2. **Normalize club name**: Strip series identifiers but preserve base name
3. **Context matters**: Roman numerals are part of name unless followed by dash/series
4. **Dash removal**: Remove dash from team name but keep series identifier
5. **Validation**: Ensure club names don't end with series identifiers after normalization

