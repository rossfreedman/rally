# Nate Hewitt Schedule Issue - Investigation Report

## Problem
Nate Hewitt's schedule is not showing up on the home page for APTA Chicago Series 5 @ Lifesportlshire.

## Root Cause
The schedule entries have incorrect `team_id` values assigned. All schedule entries for "Lifesport-Lshire 5" have `team_id = 59376`, but Nate's actual team is `team_id = 59974`.

### Details:
- **Nate's Team**: 
  - Team ID: `59974`
  - Team Name: `"Lifesport-Lshire 5"`
  - Club: `"Lifesportlshire"` (Club ID: 14202)
  - Series: `Series 5`
  
- **Wrong Team in Schedule**:
  - Team ID: `59376` 
  - Team Name: `"LifeSport-Lshire 8"` (Series 8, not Series 5!)
  - Club: `"Lifesport Lshire"` (Club ID: 8711 - different club variation!)
  
- **Affected Schedule Entries**: 18 entries have "Lifesport-Lshire 5" in the text but `team_id = 59376` instead of `59974`

## Contributing Factors
1. **Multiple Club Name Variations**: There are 6 different Lifesport club name variations in the database:
   - `LifeSport` (ID: 8521)
   - `LifeSport-Lshire` (ID: 8663)
   - `Lifesport` (ID: 8746)
   - `Lifesport Lshire` (ID: 8711) - used by team 59376
   - `Lifesport-Lshire` (ID: 8522)
   - `Lifesportlshire` (ID: 14202) - used by Nate's team 59974

2. **Schedule Import Process**: The schedule import likely matched teams by name/string pattern, and due to the multiple club variations, it assigned the wrong team_id during import.

## Solution
Update all schedule entries that reference "Lifesport-Lshire 5" in the text to use the correct `team_id = 59974` instead of `59376`.

## Impact
- **User Impact**: Nate Hewitt cannot see his schedule on the home page
- **Data Integrity**: Schedule entries have incorrect foreign key relationships
- **Scope**: 18 schedule entries need to be corrected

## Next Steps
1. Create a fix script to update the schedule entries
2. Test the fix on staging
3. Verify the schedule shows up correctly for Nate
4. Consider improving the schedule import process to prevent similar issues

