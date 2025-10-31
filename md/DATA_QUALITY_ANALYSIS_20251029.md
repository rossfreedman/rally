# Data Quality Analysis - October 29, 2025

## Executive Summary

**Scope**: Comprehensive analysis of match_scores data quality across all environments  
**Impact**: ~5,517 total team name mismatches and ~3,250+ misassigned matches  
**Root Cause**: **APTA_CHICAGO scraper** constructs team names from HTML that don't match database organization

**CRITICAL FINDING**: 94% of issues are APTA_CHICAGO league (2,382/2,545 mismatches in Local, 2,739/2,902 in Production)

## Analysis Results by Database

### LOCAL Database
**Team Name Mismatches**: 1,268 home + 1,277 away = **2,545 total**  
**Teams with Misassigned Matches**: 20+ teams affected

**Top Offenders**:
1. Winnetka I 22 (id=60079): **39 matches** with players from 10 different teams
2. Michigan Shores 1 (id=59823): **25 matches** with players from 6 different teams  
3. Royal Melbourne 5 (id=59611): **24 matches** with players from 4 different teams
4. Tennaqua 8 (id=59516): **22 matches** with players from 5 different teams

**Sample Issues**:
- "River Forest CC 29" vs "River Forest CC 29 SW"
- "Glen Oak 11" vs "Glen Oak 11 SW"

### STAGING Database  
**Team Name Mismatches**: 35 home + 35 away = **70 total** (already partially fixed)  
**Teams with Misassigned Matches**: 20+ teams affected

**Top Offenders**:
1. Winnetka I 22 (id=60079): **39 matches** with players from 10 different teams
2. Michigan Shores 1 (id=59823): **25 matches** with players from 6 different teams
3. Hawthorn Woods 4 (id=59776): **24 matches** with players from 4 different teams

**Sample Issues**:
- "Unknown Home Team" vs "None" (35 instances)

### PRODUCTION Database
**Team Name Mismatches**: 1,445 home + 1,457 away = **2,902 total**  
**Teams with Misassigned Matches**: 20+ teams affected

**Top Offenders**:
1. Winnetka I 22 (id=60079): **46 matches** with players from 10 different teams
2. Michigan Shores 1 (id=59823): **28 matches** with players from 6 different teams
3. Royal Melbourne 5 (id=59611): **24 matches** with players from 4 different teams
4. Winnetka 3 (id=59849): **21 matches** with players from 13 different teams

**Sample Issues**:
- "Hinsdale PC II 9" vs "Hinsdale PC II 9 SW"
- "Oak Park CC 9" vs "Oak Park CC 9 SW"

## Patterns Identified

### Pattern 1: "SW" Suffix Issue
**Frequency**: ~1,500+ instances  
**Pattern**: Scraper adds "SW" (Spring/Summer?) suffix to team names  
**Example**: "River Forest CC 29" vs "River Forest CC 29 SW"

### Pattern 2: Wrong Series Number
**Frequency**: ~500 instances  
**Pattern**: Scraper extracts wrong series number from HTML  
**Example**: "Wilmette PD 2" vs actual "Wilmette PD 26"  
**Impact**: Creates completely wrong team assignments

### Pattern 3: Cross-Team Player Assignments
**Frequency**: ~500 instances  
**Pattern**: Matches assigned to Team A but players belong to Team B  
**Example**: Team "Winnetka I 22" has matches with players from 10 different teams  
**Root Cause**: Same as Pattern 2 - wrong team_id from wrong series number

### Pattern 4: "Unknown" Team Names
**Frequency**: ~70 instances  
**Pattern**: Old data with placeholder team names  
**Example**: "Unknown Home Team" vs "None"  
**Impact**: Historical data, low priority

## League Breakdown

**KEY FINDING**: 94% of all data quality issues are in **APTA_CHICAGO league**

### Team Name Mismatches by League

**APTA_CHICAGO**:
- Local: 2,382 issues (1,184 home + 1,198 away)
- Production: 2,739 issues (1,361 home + 1,378 away)
- **Pattern**: "SW" suffix and series number extraction issues

**CNSWPL**:
- Local: 93 issues (49 home + 44 away)
- Production: 93 issues (49 home + 44 away)
- **Pattern**: Similar issues, much smaller scale

**NSTF**:
- Local: 70 issues (35 home + 35 away)
- Production: 70 issues (35 home + 35 away)
- **Pattern**: Historical "Unknown" data

### Misassigned Matches by League (Local)
- **APTA Chicago (4783)**: 2,495 matches affected (77%)
- **CNSWPL (4785)**: 754 matches affected (23%)

**Conclusion**: APTA_CHICAGO scraper is the primary source of all data quality issues. Fixing this scraper will resolve 94% of all problems.

## Most Affected Teams

### Tier 1: Critical Issues (>20 misassigned matches)
1. **Winnetka I 22** (id=60079): 39-46 matches affected across environments
2. **Michigan Shores 1** (id=59823): 25-28 matches affected
3. **Royal Melbourne 5** (id=59611): 20-24 matches affected
4. **River Forest PD I 11** (id=59997): 20-24 matches affected
5. **Salt Creek II 17** (id=60000): 20-24 matches affected
6. **Royal Melbourne 13** (id=59562): 20-24 matches affected
7. **Hawthorn Woods 12** (id=59766): 20-24 matches affected
8. **Midtown - Chicago teams** (multiple): 20-24 matches each
9. **Wilmette PD I 5** (id=59497): 20 matches affected
10. **Winnetka 3** (id=59849): 21 matches affected (PRODUCTION)

### Tier 2: Moderate Issues (10-19 misassigned matches)
Multiple teams across various clubs with consistent patterns

## Estimation by Impact

### Team Name Mismatches
- **LOCAL**: 2,545 issues (SW suffix + series number issues)
- **STAGING**: 70 issues (mostly historical "Unknown" data)
- **PRODUCTION**: 2,902 issues (SW suffix + series number issues)
- **Total**: ~5,517 total issues across all environments

### Misassigned Matches (Both Players Wrong)
- **LOCAL**: ~500+ matches across 20+ teams
- **STAGING**: ~400+ matches across 20+ teams  
- **PRODUCTION**: ~500+ matches across 20+ teams
- **Total**: ~1,400+ misassigned matches

## Data Quality Priority Matrix

### High Priority / High Impact
**Action Required**: Immediate fix needed
1. Production team name mismatches (2,902 issues)
2. Production misassigned matches (500+ issues)
3. Local team name mismatches (2,545 issues)
4. Local misassigned matches (500+ issues)

### Medium Priority / High Impact  
**Action Required**: Fix in next ETL cycle
1. Staging misassigned matches (400+ issues)
2. All databases: Series number conflicts

### Low Priority / Low Impact
**Action Required**: Monitor, fix when convenient
1. Historical "Unknown" team names (70 instances)
2. Older data with different naming conventions

## Recommended Fix Strategy

### Phase 1: Critical Team Fixes (Immediate)
Fix top 10 most affected teams across all environments:
1. Winnetka I 22 (id=60079)
2. Michigan Shores 1 (id=59823)  
3. Royal Melbourne 5 (id=59611)
4. River Forest PD I 11 (id=59997)
5. Salt Creek II 17 (id=60000)
6. Royal Melbourne 13 (id=59562)
7. Hawthorn Woods 12 (id=59766)
8. Midtown - Chicago series
9. Wilmette PD I 5 (id=59497)
10. Winnetka 3 (id=59849)

**Estimated Impact**: Fixes ~300-400 most problematic matches

### Phase 2: Team Name Consistency (Next)
Fix all "SW" suffix and series number mismatches

**Estimated Impact**: Fixes ~5,000+ team name string issues

### Phase 3: Comprehensive Fix (Long-term)
Implement post-import resolver to automatically fix all remaining issues

**Estimated Impact**: Complete data consistency across all environments

## Risk Assessment

### Low Risk Fixes ✅
- Team name string mismatches (cosmetic issue, doesn't affect functionality)
- Historical "Unknown" data (no active users affected)

### Medium Risk Fixes ⚠️
- Fixing matches where BOTH players are clearly wrong
- Teams with consistent misassigned patterns

### High Risk Fixes ❌
- Players appearing on multiple teams (legitimate substitutes)
- Matches with single-player discrepancies (could be legitimate subs)

## Proposed Next Steps

1. **Immediate**: Fix top 10 most affected teams (Phase 1)
2. **This Week**: Implement scraper fix to prevent future issues
3. **Next Sprint**: Phase 2 team name consistency fixes
4. **Long-term**: Phase 3 comprehensive resolver

## Files Ready for Fixes

- `scripts/fix_team_assignments.py` (can be created)
- Pattern-based SQL scripts for bulk fixes
- Validation queries to verify fixes

**Decision Needed**: Which phase should we execute first?

