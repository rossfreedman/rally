# Pairing Analysis Feature Implementation

## Overview
Implemented a new "Pairing Analysis" page in the Captain's Corner section that allows team captains to manage player pairing preferences using an interactive grid interface.

## Date
October 24, 2025

## Features Implemented

### 1. Database Model
**File:** `app/models/database_models.py`
- Added `PairingPreference` model to store pairing preferences
- Fields:
  - `team_id`: Reference to team
  - `player1_user_id`: First player in pairing
  - `player2_user_id`: Second player in pairing
  - `is_allowed`: Boolean (True = green/allowed, False = red/not allowed)
  - `created_at`, `updated_at`: Timestamps
- Unique constraint ensures each player pair per team is stored once

### 2. Database Migration
**File:** `data/dbschema/migrations/add_pairing_preferences_table.sql`
- Created `pairing_preferences` table
- Added indexes for fast lookups (team_id, player1_user_id, player2_user_id)
- Added trigger to auto-update `updated_at` timestamp
- Migration successfully applied to local database

### 3. User Interface
**File:** `templates/mobile/pairing_analysis.html`
- Desktop-optimized responsive grid layout
- Player names displayed in both rows and columns
- Color-coded headers based on player positions:
  - **Blue**: Ad side players
  - **Orange**: Deuce side players
  - **Purple**: Players who can play both sides (Either)
- Interactive toggle switches in each cell:
  - **Green cell** (toggle ON): Pairing is allowed
  - **Red cell** (toggle OFF): Pairing is not recommended
- Diagonal cells (same player) are grayed out
- Mobile users see a notice that this is a desktop feature
- Save button to persist preferences

### 4. Routes
**File:** `app/routes/mobile_routes.py`
- Added page route: `/mobile/pairing-analysis`
- Added API endpoint: `/api/pairing-analysis/data` (GET)
  - Returns team players with positions and existing preferences
- Added API endpoint: `/api/pairing-analysis/save` (POST)
  - Saves pairing preferences for the team
  - Uses transaction to delete old preferences and insert new ones

### 5. Navigation
**File:** `templates/mobile/layout.html`
- Added "Pairing Analysis" button to Captain's Corner submenu
- Positioned after "Practice Times" and before "Admin"
- Uses groups/users icon

### 6. Admin Integration
**File:** `app/routes/admin_routes.py`
- Added page name mappings for activity logging:
  - `mobile_pairing_analysis`: "Pairing Analysis"
  - `pairing_analysis`: "Pairing Analysis"

## Technical Implementation Details

### Grid Layout
- Grid is dynamically generated based on team players
- Matrix is symmetric (if A-B pairing is red, B-A is also red)
- Uses consistent pairing keys (smaller user_id first) for database storage
- JavaScript handles bidirectional toggle updates

### Position Detection
- Player positions are pulled from `users.ad_deuce_preference` field
- Defaults to "Either" if not set
- Color coding uses constants:
  - Ad: `#2563eb` (Blue)
  - Deuce: `#ea580c` (Orange)
  - Either: `#9333ea` (Purple)

### Data Flow
1. Page loads → JavaScript calls `/api/pairing-analysis/data`
2. API fetches team players from database (via user_player_associations → players)
3. API fetches existing preferences from `pairing_preferences` table
4. JavaScript renders grid with toggle switches in initial states
5. User toggles switches → Updates local state
6. User clicks "Save" → POSTs preferences to `/api/pairing-analysis/save`
7. API deletes old preferences and inserts new ones for the team
8. Success message displays

### Query Details
- **Get team players**: Joins users → user_player_associations → players, filtered by team_id
- **Get preferences**: Simple SELECT from pairing_preferences by team_id
- **Save preferences**: DELETE all for team, then batch INSERT new preferences

## Security
- All routes require `@login_required` decorator
- User must have a team_id assigned
- Only preferences for user's current team can be saved
- Activity logging for audit trail

## Desktop-First Design
- Grid layout optimized for desktop/laptop screens
- Mobile users see a notice recommending desktop viewing
- Responsive CSS adjusts cell sizes for smaller screens (tablets)
- Feature is still accessible on mobile but with reduced usability

## Usage Instructions

### For Team Captains
1. Navigate to mobile home page
2. Open navigation drawer (hamburger menu)
3. Click "Captain's Corner"
4. Click "Pairing Analysis"
5. View team players grid
6. Toggle cells:
   - **ON (right)** = Green = Pairing allowed
   - **OFF (left)** = Red = Pairing not recommended
7. Click "Save Pairing Preferences" to persist changes
8. Success message confirms save

### Use Cases
- Mark which players should not be paired together (personality conflicts)
- Mark which players should only play on specific sides (Deuce/Ad preferences)
- Quickly visualize all possible pairings for team lineup planning
- Reference during lineup creation to avoid problematic pairings

## Files Modified
1. `app/models/database_models.py` - Added PairingPreference model
2. `templates/mobile/pairing_analysis.html` - New template (830+ lines)
3. `app/routes/mobile_routes.py` - Added route and 2 API endpoints
4. `templates/mobile/layout.html` - Added navigation button
5. `app/routes/admin_routes.py` - Added page name mappings
6. `data/dbschema/migrations/add_pairing_preferences_table.sql` - New migration

## Database Changes
- New table: `pairing_preferences`
- New indexes: `idx_pairing_preferences_team_id`, `idx_pairing_preferences_player1`, `idx_pairing_preferences_player2`
- New trigger: `trigger_update_pairing_preferences_updated_at`
- New function: `update_pairing_preferences_updated_at()`

## Next Steps for Deployment
1. Commit all changes to git
2. Run migration on staging: `python data/dbschema/dbschema_workflow.py --auto`
3. Test on staging environment
4. Run migration on production: `python data/dbschema/dbschema_workflow.py --auto`
5. Deploy to production

## Testing Checklist
- [ ] Load page successfully
- [ ] Grid displays all team players
- [ ] Player positions are color-coded correctly
- [ ] Toggle switches work (both directions)
- [ ] Both cells in pair update when one is toggled
- [ ] Save button persists preferences
- [ ] Reload page shows saved preferences
- [ ] Works for teams of different sizes
- [ ] Mobile notice displays on small screens
- [ ] Activity logging works

## Known Limitations
- Desktop-first design (not optimized for mobile)
- Requires users to have `ad_deuce_preference` set for proper color coding
- Grid gets large for teams with 15+ players (requires scrolling)
- No "Notes" field per pairing (could be added in future)

## Future Enhancements
- Add notes field for each pairing preference
- Color-code cells by pairing quality (green/yellow/red scale)
- Export pairing matrix as PDF
- Suggest optimal lineups based on preferences
- Historical view of preference changes
- Bulk edit features (mark entire row/column)

