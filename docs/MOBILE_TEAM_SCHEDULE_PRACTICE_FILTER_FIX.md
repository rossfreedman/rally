# Mobile Team Schedule Practice Filter Fix

**Date**: January 15, 2025  
**Issue**: Practice times showing for wrong teams on mobile team schedule page  
**Status**: ✅ RESOLVED  

## Problem Summary

Users on the mobile team schedule page (https://www.lovetorally.com/mobile/team-schedule) were seeing practice times from other teams in their club, not just their own team's practices. This caused confusion and incorrect date filter population.

### Specific Case
- **User**: Jessica Freedman (Player ID: `cnswpl_WkMrK3dMMzdndz09`)
- **Team**: Tennaqua Series 17 (Team ID: 59151) 
- **Expected**: 0 practice times (Series 17 has none)
- **Actual**: Showing practice times from Series D and F teams

## Root Cause Analysis

The issue was in the `get_matches_for_user_club()` function in `routes/act/schedule.py` at **line 50**:

```python
# BUGGY CODE (line 50)
practice_pattern = f"{user_club} Practice%"  # Too broad!
practice_search = f"%{practice_pattern}%"    # Matches ALL club practices
```

### Why This Was Wrong

1. **Intended Pattern**: `"Tennaqua Practice - Series 17"` (specific to user's series)
2. **Actual Pattern**: `"Tennaqua Practice%"` (matches ALL Tennaqua practices)
3. **Result**: Series 17 users saw practices from Series D and F

### Pattern Matching Results

| Pattern | Series 17 User Should See | Actually Matched |
|---------|---------------------------|------------------|
| `%Tennaqua Practice - Series 17%` | 0 practices ✅ | N/A (not used) |
| `%Tennaqua Practice%%` | 0 practices ❌ | 43 practices from D/F |

## The Fix

**File**: `routes/act/schedule.py`  
**Lines**: 50-56  

### Before (Buggy)
```python
# Practice pattern for ILIKE search (fallback for practices not using team_id)
practice_pattern = f"{user_club} Practice%"
practice_search = f"%{practice_pattern}%"
```

### After (Fixed)
```python
# Practice pattern for ILIKE search (fallback for practices not using team_id)
# FIXED: Use specific series pattern instead of broad club pattern
if "Division" in user_series:
    division_num = user_series.replace("Division ", "")
    practice_pattern = f"{user_club} Practice - Series {division_num}"
else:
    practice_pattern = f"{user_club} Practice - {user_series}"
practice_search = f"%{practice_pattern}%"
```

## Verification

### Test Results

| Test Case | Pattern | Expected | Actual | Status |
|-----------|---------|----------|---------|---------|
| Series 17 | `%Tennaqua Practice - Series 17%` | 0 matches | 0 matches | ✅ Fixed |
| Series D | `%Tennaqua Practice - Series D%` | 28 matches | 28 matches | ✅ Works |
| Series F | `%Tennaqua Practice - Series F%` | 15 matches | 15 matches | ✅ Works |

### Before Fix (Buggy Behavior)
```
Pattern: "%Tennaqua Practice%%"
Found 5 matches (WRONG - should be 0):
  2025-09-06 - Tennaqua Practice - Series D
  2025-09-07 - Tennaqua Practice - Series F
  ...
```

### After Fix (Correct Behavior)
```
Pattern: "%Tennaqua Practice - Series 17%"
No matches found (CORRECT - Series 17 has no practices)
```

## Impact

### Pages Affected
- **Primary**: `/mobile/team-schedule` (mobile team schedule page)
- **Secondary**: Any page using `get_matches_for_user_club()` function

### User Experience Before Fix
- ❌ Users saw practice times from other teams in their club
- ❌ Date filter populated with wrong dates
- ❌ Confusion about which practices belonged to their team
- ❌ Inability to remove "non-existent" practices (they belonged to other teams)

### User Experience After Fix
- ✅ Users only see their own team's practice times
- ✅ Date filter correctly shows only relevant dates
- ✅ Practice removal works correctly (when practices exist)
- ✅ Clear distinction between teams within the same club

## Prevention

### Code Review Guidelines
1. **Be Specific with Patterns**: Always use specific search patterns instead of broad wildcards
2. **Test Cross-Team Scenarios**: Verify functionality works correctly for users on different teams within the same club
3. **Validate Team Isolation**: Ensure team-specific data doesn't leak between teams

### Monitoring
- Monitor for reports of users seeing "phantom" practice times
- Verify practice removal functionality works as expected
- Check that date filters populate correctly for all team configurations

## Related Issues

This fix resolves the original user report:
> "Investigate why these practice times are not being removed when I remove all practice times from CNSWPL Series 17"

**Root Cause**: The practice times being shown weren't actually for Series 17 - they were for Series D and F, which is why they couldn't be removed by a Series 17 user.

## Files Modified

- `routes/act/schedule.py` - Fixed practice pattern matching logic
- `scripts/diagnose_practice_times_issue.py` - Created diagnostic tool for future issues

## Testing

Created comprehensive diagnostic script for future troubleshooting:
```bash
# Test specific player
DATABASE_URL='production_url' python3 scripts/diagnose_practice_times_issue.py --player-id cnswpl_WkMrK3dMMzdndz09

# Test specific team  
DATABASE_URL='production_url' python3 scripts/diagnose_practice_times_issue.py --team-id 59151
```

## Deployment

**Commit**: `87cbfb8` - "fix | Fix mobile team schedule showing wrong practice times"  
**Status**: Ready for deployment to staging and production  
**Risk Level**: Low (only affects practice time filtering, no data loss risk)
