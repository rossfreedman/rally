# Substitute Player Indicator Implementation

## Overview

This feature adds visual indicators for substitute players in the Court Performance section, showing when a player is competing for a different team/series than their primary assignment.

## Implementation Details

### 1. Substitute Detection Logic

**Function**: `is_substitute_player(player_id, match_team_id, user_league_id=None)`

**Logic**:
- Queries the player's primary team assignment from the `players` table
- Compares the match team ID with the player's primary team ID
- Returns `True` if the player is playing for a different team than their primary team
- Returns `False` if:
  - Player has no primary team assignment
  - Player is playing for their primary team
  - Error occurs during detection

### 2. Court Performance Integration

**Modified Files**:
- `app/services/mobile_service.py`: Added substitute detection to court performance calculation
- `templates/mobile/analyze_me.html`: Added substitute indicator display
- `templates/mobile/teams_players.html`: Added substitute indicator display

**Changes**:
1. **Backend**: Enhanced `calculate_team_analysis_mobile()` to include `isSubstitute` field in player data
2. **Frontend**: Added orange "Sub" badge with exchange icon for substitute players

### 3. Visual Design

**Substitute Indicator**:
- **Color**: Orange (`bg-orange-100 text-orange-700`)
- **Icon**: Exchange icon (`fas fa-exchange-alt`)
- **Text**: "Sub"
- **Style**: Rounded pill with border
- **Position**: Next to player name

**Example**:
```
John Smith 🟠 Sub
```

### 4. Database Requirements

**Required Fields**:
- `players.team_id`: Primary team assignment
- `players.tenniscores_player_id`: Unique player identifier
- `match_scores.home_team_id` / `match_scores.away_team_id`: Team being played for

### 5. Usage

**Pages Affected**:
1. **Analyze Me Page** (`/mobile/analyze-me`): Court Performance section
2. **Teams & Players Page** (`/mobile/teams-players`): Court Analysis section

**When Displayed**:
- Player appears in court performance statistics
- Player is identified as substitute (different team than primary)
- Orange "Sub" badge appears next to player name

### 6. Testing

**Test Cases**:
1. ✅ Player with primary team playing for primary team → No indicator
2. ✅ Player with primary team playing for different team → Shows "Sub" indicator
3. ✅ Player without primary team assignment → No indicator (treated as regular)

**Test Results**:
```
Molly Hughes (Primary Team: 92278)
- Playing for primary team: ✅ Regular
- Playing for different team: ✅ Substitute

Janet Beatty (No team assignment)
- Playing for any team: ✅ Regular
```

## Benefits

1. **Clear Identification**: Users can easily see when players are substitutes
2. **Performance Context**: Helps understand court performance with substitute players
3. **Team Management**: Assists captains in tracking substitute usage
4. **Data Accuracy**: Distinguishes between regular team members and substitutes

## Future Enhancements

1. **Substitute Statistics**: Track substitute performance separately
2. **Substitute History**: Show substitute player history over time
3. **Substitute Notifications**: Alert when substitutes are needed
4. **Substitute Performance Analysis**: Compare substitute vs regular performance 