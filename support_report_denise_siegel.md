# Support Ticket Resolution: Denise Siegel Team Visibility Issue

**Date:** October 14, 2025  
**Player ID:** cnswpl_WkM2eHhybndqUT09  
**User ID:** 1092  
**Email:** siegeldenise@yahoo.com  
**Expected Team:** Series I, Tennaqua (CNSWPL)

---

## Issue Summary

Denise Siegel reported that she was not seeing her correct team (Series I) when logging into Rally. The system was showing incorrect team information instead.

---

## Root Cause Analysis

### Database Investigation Revealed:

1. **Corrupted User Record:**
   - The `users` table had NULL values for critical fields:
     - `tenniscores_player_id`: NULL (should be `cnswpl_WkM2eHhybndqUT09`)
     - `league_id`: NULL (should be `4785` for CNSWPL)

2. **Multiple Player Records:**
   - Two player records exist in the database with the same `tenniscores_player_id`:
     - **Player DB ID 871012**: Denise Siegel - Series I, Team ID 59318 (Tennaqua I) ✓ CORRECT
     - **Player DB ID 960438**: Denise Siegel(S) - Series 17, Team ID 59151 (Tennaqua 17)

3. **Session Logic Failure:**
   - Without the `tenniscores_player_id` set in the `users` table, the session initialization logic couldn't properly determine which team to show
   - The user had valid associations to both teams, but no "primary" association was marked
   - This caused the system to potentially show the wrong team context

### Why This Happened:

This issue occurred because the user registration or association discovery process failed to properly populate the `tenniscores_player_id` and `league_id` fields in the `users` table. This is a known pattern we've seen before [[memory:535722]] where association discovery completes but doesn't fully update the user record.

---

## Resolution Applied

### Database Updates:

1. **Updated `users` table (User ID 1092):**
   ```sql
   UPDATE users
   SET tenniscores_player_id = 'cnswpl_WkM2eHhybndqUT09',
       league_id = 4785
   WHERE id = 1092;
   ```

2. **Updated `user_player_associations` table:**
   - Marked the association as `is_primary = true`
   - This ensures the system prioritizes the correct team context

### Verification:

**Before Fix:**
```
tenniscores_player_id: NULL
league_id: NULL
is_primary: False
```

**After Fix:**
```
tenniscores_player_id: cnswpl_WkM2eHhybndqUT09
league_id: 4785 (Chicago North Shore Women's Platform Tennis League)
is_primary: True
```

---

## Current Status

✅ **RESOLVED - APPLIED TO PRODUCTION**

The production database has been corrected. Denise Siegel's account now has:
- Proper `tenniscores_player_id` linking to her player records (`cnswpl_WkM2eHhybndqUT09`)
- Correct `league_id` for CNSWPL (`4785`)
- Primary association marked for proper team context
- User context set to Series I team (Tennaqua I, Team ID: `59318`)

**Production Fix Applied:** October 14, 2025

---

## User Instructions

**Please ask Denise to:**

1. **Log out completely** from Rally
2. **Log back in** with her credentials (siegeldenise@yahoo.com)
3. She should now see her **Series I** team (Tennaqua I) by default
4. If she plays in both Series I and Series 17, she can use the **team switcher** to toggle between them

---

## Technical Details

### Player Records:
- **Correct Team:** Tennaqua I (Series I)
  - Team ID: 59318
  - Players on this team: 10 others in Series I division
  
- **Alternate Team:** Tennaqua 17 (Series 17)
  - Team ID: 59151
  - Also accessible via team switcher if needed

### Database Tables Affected:
- `users` (1 record updated)
- `user_player_associations` (1 record updated)

### Scripts Created:
- `/scripts/diagnose_denise_siegel.py` - Diagnostic tool
- `/scripts/fix_denise_siegel.py` - Resolution script

---

## Prevention

This issue highlights a known gap in the registration/association discovery process. To prevent similar issues:

1. **Immediate:** Monitor for other users with NULL `tenniscores_player_id` in the `users` table
2. **Short-term:** Add validation during registration to ensure these fields are never NULL after successful player matching
3. **Long-term:** Enhance the association discovery system to always populate user table fields [[memory:535722]]

### Suggested Query to Find Similar Issues:
```sql
SELECT u.id, u.email, u.first_name, u.last_name, u.tenniscores_player_id, u.league_id
FROM users u
WHERE u.tenniscores_player_id IS NULL 
  AND u.id IN (SELECT DISTINCT user_id FROM user_player_associations);
```

This will identify other users who have associations but are missing the critical `tenniscores_player_id` field.

---

## Resolution Time

- **Issue Reported:** October 14, 2025
- **Investigation Started:** October 14, 2025
- **Fix Applied:** October 14, 2025
- **Status:** Resolved - Awaiting user confirmation

---

**Resolution By:** AI Assistant  
**Database:** Production (Railway - ballast.proxy.rlwy.net)  
**Environment:** Production  
**Scripts Used:** 
- `/scripts/production_diagnose_denise.py` - Diagnostic
- `/scripts/production_fix_denise.py` - Fix implementation

