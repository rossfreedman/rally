# Team Videos Feature Documentation

## Overview
Added a new team-specific video section to the My Team page (`/mobile/my-team`) that displays team practice and training videos. The design matches the existing Training Videos page for consistency.

## Database Schema

### Table: `videos`
Created using dbschema migration: `20251012_120000_add_videos_table.sql`

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-incrementing primary key |
| `name` | VARCHAR(255) | Display name for the video (e.g., "Tennaqua 20 Sunday Practice") |
| `url` | TEXT | YouTube or other video platform URL |
| `players` | TEXT | Comma-separated list of player names featured in the video |
| `date` | DATE | Date the video was recorded or associated with |
| `team_id` | INTEGER | Foreign key to teams table (with CASCADE DELETE) |
| `created_at` | TIMESTAMP | Record creation timestamp |
| `updated_at` | TIMESTAMP | Record update timestamp |

**Indexes:**
- `idx_videos_team_id` - Fast lookup by team
- `idx_videos_date` - Date-based queries (DESC order)

## Implementation Details

### Backend Changes

#### 1. Mobile Service (`app/services/mobile_service.py`)
Added new function:
```python
def get_team_videos(team_id):
    """
    Get team-specific training videos from the videos table
    Returns: List of video dictionaries with name, url, players, date
    """
```

Updated `get_mobile_team_data()` to include videos:
- Calls `get_team_videos(team_id)` 
- Returns videos in the result dictionary as `team_videos`

#### 2. Mobile Routes (`app/routes/mobile_routes.py`)
Updated `/mobile/my-team` route:
- Extracts `team_videos` from service result
- Passes `team_videos` to template
- Includes empty list in error handling

### Frontend Changes

#### Template (`templates/mobile/my_team.html`)
Added new "Team Videos" section at the bottom:
- Modern card-based design matching training videos page
- YouTube video thumbnails with play button overlay
- Embedded video player with close button
- Video metadata display (name, players, date)
- Responsive design with hover effects
- Brand colors (#045454 and #bff863)

**JavaScript Functions:**
- `initializeTeamVideos()` - Sets up video player event handlers
- `extractYouTubeVideoId()` - Parses various YouTube URL formats
- Auto-play on click, stop on close

## Usage

### Adding Videos via Script
Use the helper script to add videos:
```bash
python3 scripts/add_sample_team_video.py
```

### Adding Videos Manually
```sql
INSERT INTO videos (name, url, players, date, team_id)
VALUES (
    'Tennaqua 20 Sunday Practice',
    'https://youtu.be/C_fJK5JCGqo',
    'Ross Freedman, Jon Blume, Ryan Jarol, Stephen Statkus',
    '2025-10-12',
    59602
);
```

### Viewing Videos
1. Navigate to `/mobile/my-team`
2. Scroll to bottom to see "Team Videos" section
3. Click play button to watch video
4. Click X to close video player

## Design Features

### Visual Design
- Matches existing Rally color scheme
- Header: #045454 (dark teal)
- Accent: #bff863 (lime green)
- Modern play button with gradient and animations
- YouTube thumbnail auto-loading with fallback
- Smooth transitions and hover effects

### UX Features
- Videos only show for teams with uploaded content
- Sorted by date (most recent first)
- Shows player names and video date
- Embedded YouTube player with controls
- Mobile-responsive design
- Matches training-videos page aesthetics

## Deployment

### Staging
✅ Migration deployed to staging: `20251012_120000_add_videos_table.sql`

### Local
✅ Migration applied to local database
✅ Sample video added for testing

### Production
To deploy to production:
```bash
python3 data/dbschema/dbschema_workflow.py --production
```

## Future Enhancements

Potential improvements:
1. **Video Upload Interface** - Admin UI to add/edit/delete videos
2. **Video Categories** - Filter by practice/match/drill
3. **Player Tagging** - Link to player profiles
4. **Video Analytics** - Track views and engagement
5. **Comments** - Team discussion on videos
6. **Video Processing** - Auto-generate thumbnails
7. **Playlists** - Organize videos by season/theme
8. **Search/Filter** - Find specific videos
9. **Sharing** - Share videos with other teams/leagues

## Testing

### Test Data Added
- Video: "Tennaqua 20 Sunday Practice"
- URL: https://youtu.be/C_fJK5JCGqo
- Players: Ross Freedman, Jon Blume, Ryan Jarol, Stephen Statkus  
- Date: 2025-10-12
- Team: Tennaqua 20 (ID: 59602)

### Test Steps
1. ✅ Database table created
2. ✅ Migration deployed to staging
3. ✅ Backend function implemented
4. ✅ Route updated to pass data
5. ✅ Template section added
6. ✅ JavaScript player functionality working
7. ✅ Sample video added
8. ✅ No linter errors

## Files Changed

### Created
- `data/dbschema/migrations/20251012_120000_add_videos_table.sql`
- `scripts/add_sample_team_video.py`
- `docs/TEAM_VIDEOS_FEATURE.md`

### Modified
- `app/services/mobile_service.py` - Added `get_team_videos()` function
- `app/routes/mobile_routes.py` - Updated route to pass videos
- `templates/mobile/my_team.html` - Added video section

## Notes

- Videos are team-specific (filtered by `team_id`)
- Only YouTube videos supported currently (easily extensible)
- Videos CASCADE DELETE with team deletion
- Empty state: Section hidden when no videos exist
- All functionality follows Rally's existing patterns
- Maintains separation of concerns (service/route/template)

---

**Created:** 2025-10-12  
**Author:** AI Assistant  
**Status:** ✅ Complete and Deployed to Staging

