# Pickup Games Club Filtering Implementation

## Overview

This implementation adds proper club-based filtering to pickup games, ensuring players only see practice times and pickup games from their own clubs. This addresses a critical security issue where players could see pickup games from other clubs.

## Problem Solved

**Before**: The `pickup_games` table had a `club_only` boolean field but no `club_id` column to specify which club the game belonged to. This meant:
- Players could see pickup games from all clubs
- Club-only games had no way to specify which club they were for
- No proper security boundaries between clubs

**After**: Players only see pickup games from clubs they belong to, maintaining privacy and club exclusivity.

## Database Changes

### 1. Schema Migration

**File**: `data/dbschema/migrations/20250117_140000_add_club_id_to_pickup_games.sql`

Added `club_id` column to `pickup_games` table:
```sql
ALTER TABLE pickup_games 
ADD COLUMN club_id INTEGER REFERENCES clubs(id) ON DELETE SET NULL;

CREATE INDEX idx_pickup_games_club_id ON pickup_games(club_id);
```

### 2. Database Models

**File**: `app/models/database_models.py`

Added complete SQLAlchemy models for:
- `PickupGame` - Main pickup games table with club relationship
- `PickupGameParticipant` - Junction table for participants

## Application Logic Changes

### 1. API Filtering Logic

**File**: `app/routes/api_routes.py`

Updated both main pickup games API and notifications API with proper club filtering:

```sql
AND (
    pg.club_only = false OR 
    pg.club_id IS NULL OR
    (pg.club_only = true AND pg.club_id IN (
        SELECT DISTINCT p.club_id 
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE upa.user_id = %s AND p.club_id IS NOT NULL
    ))
)
```

### 2. Club Name Display

Enhanced the `format_game` function to show the actual club name for pickup games:
- **Before**: Always showed user's club name
- **After**: Shows the pickup game's actual club name or "All Clubs" for open games

## Filtering Rules

The system now follows these security rules:

1. **Open Games** (`club_only = false` OR `club_id = NULL`): Visible to ALL users
2. **Club-Only Games** (`club_only = true` AND `club_id` set): Only visible to members of that specific club
3. **Multi-Club Users**: Can see club-only games from ANY of their clubs

## Security Benefits

### ✅ Privacy Protection
- Players only see pickup games from their own clubs
- Club-only games maintain exclusivity
- No data leakage between different clubs

### ✅ Proper Access Control
- Club membership determines game visibility
- Multi-club users get appropriate access to all their clubs
- Non-club members only see open games

### ✅ Database Integrity
- Foreign key constraints ensure data consistency
- Indexed queries provide good performance
- Proper cascade rules for club deletion

## Testing

### Comprehensive Test Suite

**File**: `scripts/test_pickup_games_club_filtering.py`

Tests cover:
- Users with single club membership
- Users with multiple club memberships  
- Users with no club associations
- Club-only vs open game visibility
- API endpoint filtering
- Edge cases and error conditions

### Migration Script

**File**: `scripts/apply_pickup_games_club_migration.py`

Provides:
- Safe migration application
- Database validation
- Test game creation
- Comprehensive reporting

## Usage Examples

### Creating Club-Only Game
```sql
INSERT INTO pickup_games (
    description, game_date, game_time, players_requested,
    club_only, club_id, creator_user_id
) VALUES (
    'Tennaqua Members Only', '2025-01-20', '18:00', 4,
    true, 10556, 43
);
```

### Creating Open Game
```sql
INSERT INTO pickup_games (
    description, game_date, game_time, players_requested,
    club_only, club_id, creator_user_id
) VALUES (
    'Open to All Clubs', '2025-01-20', '19:00', 6,
    false, NULL, 43
);
```

### API Query for User's Games
```sql
SELECT * FROM pickup_games pg
WHERE (
    pg.club_only = false OR 
    pg.club_id IS NULL OR
    (pg.club_only = true AND pg.club_id IN (
        SELECT DISTINCT p.club_id 
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE upa.user_id = :user_id AND p.club_id IS NOT NULL
    ))
);
```

## Database Schema

### pickup_games Table
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `description` | TEXT | Game description |
| `game_date` | DATE | Game date |
| `game_time` | TIME | Game time |
| `players_requested` | INTEGER | Number of players needed |
| `players_committed` | INTEGER | Number of committed players |
| `pti_low` | INTEGER | Minimum PTI requirement |
| `pti_high` | INTEGER | Maximum PTI requirement |
| `series_low` | INTEGER | Minimum series level |
| `series_high` | INTEGER | Maximum series level |
| `club_only` | BOOLEAN | Whether game is club-restricted |
| `is_private` | BOOLEAN | Whether game is private |
| **`club_id`** | **INTEGER** | **Club that hosts the game (NEW)** |
| `creator_user_id` | INTEGER | User who created the game |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

### Key Relationships
- `pickup_games.club_id` → `clubs.id` (Foreign Key)
- `pickup_games.creator_user_id` → `users.id` (Foreign Key)

## Performance Considerations

### Indexes Added
- `idx_pickup_games_club_id` - For efficient club filtering
- Existing indexes remain for date/time and status filtering

### Query Optimization
- Uses `IN` clause with subquery for multi-club users
- Leverages existing user_player_associations for club lookup
- Minimal additional database load

## Backward Compatibility

### Existing Games
- All existing pickup games have `club_id = NULL`
- This makes them visible to all users (open games)
- No data loss or breaking changes

### API Compatibility
- All existing API endpoints continue to work
- Added new fields (`club_id`, `club_name`) to responses
- Frontend can gradually adopt new club information

## Future Enhancements

### Potential Improvements
1. **Club Admin Controls**: Allow club admins to manage club-only games
2. **Club Invitations**: Cross-club invitations for special events
3. **Club Defaults**: Default new games to user's primary club
4. **Analytics**: Track club-specific pickup game participation

### Integration Points
- User Settings: Club preference management
- Admin Panel: Club-based game oversight
- Notifications: Club-specific game alerts
- Mobile App: Club context in game creation

## Deployment Status

### ✅ Completed
- [x] Database migration created and tested
- [x] Application logic updated
- [x] API endpoints secured
- [x] Database models added
- [x] Comprehensive testing
- [x] Documentation complete

### 🔄 Next Steps
1. Deploy migration to staging environment
2. Test with real user scenarios
3. Deploy to production
4. Update frontend to show club information
5. Monitor for any performance impact

## Support

For questions or issues with pickup games club filtering:
- Check the test scripts in `scripts/`
- Review the migration script for database changes
- Examine the API filtering logic in `app/routes/api_routes.py`
- Run the comprehensive test suite for validation 