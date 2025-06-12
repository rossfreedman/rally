# Rally Application - JSON Data Access Documentation

This document provides a comprehensive overview of all JSON data access patterns in the Rally application, including direct file reads, API endpoints, and frontend fetch calls.

## Table of Contents
1. [Data Files Structure](#data-files-structure)
2. [Backend JSON File Access](#backend-json-file-access)
3. [API Endpoints](#api-endpoints)
4. [Frontend JSON Calls](#frontend-json-calls)
5. [Service Layer Access](#service-layer-access)

## Data Files Structure

The application uses JSON files stored in the following structure:
```
data/
├── leagues/
│   └── all/
│       ├── player_history.json
│       ├── match_history.json
│       ├── players.json
│       ├── series_stats.json
│       ├── schedules.json
│       └── improve_data/
│           ├── complete_platform_tennis_training_guide.json
│           └── paddle_tips.json
│       └── club_directories/
│           └── directory_tennaqua.csv
└── players.json (root level)
```

## Backend JSON File Access

### Service Files (`app/services/`)

#### `mobile_service.py`
- **Player Analysis**: `data/leagues/all/player_history.json`, `data/leagues/all/match_history.json`
- **Players Data**: `data/leagues/all/players.json`
- **Team Data**: `data/leagues/all/series_stats.json`, `data/leagues/all/match_history.json`
- **Schedule Data**: `data/leagues/all/schedules.json`
- **Club Data**: `data/leagues/all/series_stats.json`, `data/leagues/all/match_history.json`
- **Search Data**: `data/leagues/all/player_history.json`
- **Improve Data**: `data/leagues/all/improve_data/complete_platform_tennis_training_guide.json`, `data/leagues/all/improve_data/paddle_tips.json`
- **Club Directory**: `data/leagues/all/club_directories/directory_tennaqua.csv`

#### `player_service.py`
- **Player Analysis**: `data/leagues/all/players.json`, `data/leagues/all/player_history.json`

#### `api_service.py`
- **Stats Data**: `data/leagues/all/series_stats.json`, `data/leagues/all/match_history.json`
- **Players Data**: `data/leagues/all/players.json`, `data/leagues/all/match_history.json`
- **Training Data**: `data/leagues/all/improve_data/complete_platform_tennis_training_guide.json`
- **Schedule Data**: `data/leagues/all/schedules.json`

### Route Files (`routes/`)

#### `routes/act/schedule.py`
- **Schedule Data**: `data/leagues/apta/schedules.json` (⚠️ **NEEDS UPDATE**)
- **Match History**: `data/leagues/apta/match_history.json` (⚠️ **NEEDS UPDATE**)

#### `routes/act/find_people_to_play.py`
- **Players Data**: `data/players.json` (root level file)

#### `routes/act/rally_ai.py`
- **Player History**: `data/player_history.json` (root level file)
- **Training Guide**: `data/improve_data/complete_platform_tennis_training_guide.json` (root level file)

### API Files (`api/`)

#### `api/training_data.py`
- **Training Guide**: `data/leagues/apta/improve_data/complete_platform_tennis_training_guide.json` (⚠️ **NEEDS UPDATE**)

### Scripts (`scripts/`)

#### Data Processing Scripts
- `scripts/remove_practices.py`: `data/leagues/all/schedules.json`
- `scripts/search_missing_players.py`: `data/leagues/all/players.json`
- `scripts/analyze_matches.py`: `data/leagues/all/match_history.json`
- `scripts/add_real_data.py`: `data/leagues/all/series_stats.json`
- `scripts/execute_youtube_replacement.py`: `data/leagues/all/improve_data/complete_platform_tennis_training_guide.json`
- `scripts/fix_youtube_links.py`: `data/leagues/all/improve_data/complete_platform_tennis_training_guide.json`

#### Helper Scripts
- `Helper Scripts/test_replacement_setup.py`: `data/leagues/all/improve_data/complete_platform_tennis_training_guide.json`
- `Helper Scripts/troubleshoot_youtube_urls.py`: `data/leagues/all/improve_data/complete_platform_tennis_training_guide.json`
- `Helper Scripts/test_youtube_urls.py`: `data/leagues/all/improve_data/complete_platform_tennis_training_guide.json`

## API Endpoints

### Authentication (`app/routes/auth_routes.py`)
- `POST /api/register` - User registration
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/check-auth` - Check authentication status

### Player Data (`app/routes/player_routes.py`)
- `GET /api/players` - Get players list (with filtering)
- `GET /api/team-players/<team_id>` - Get players for specific team
- `GET /api/player-court-stats/<player_name>` - Get court statistics for player
- `GET /api/player-streaks` - Get player win/loss streaks
- `GET /api/player-history` - Get player history data
- `GET /api/player-history/<player_name>` - Get specific player history

### Team/Club Data
- `GET /api/research-team` - Team research data (`routes/analyze/competition.py`)
- `GET /api/research-my-team` - User's team data (`routes/analyze/my_team.py`)
- `GET /api/team-matches` - Team match data (`routes/act/schedule.py`)
- `GET /api/win-streaks` - Club win streaks (`routes/analyze/my_club.py`)

### Series Data
- `GET /api/series-stats` - Series statistics (`routes/analyze/my_series.py`)
- `GET /api/get-series` - Available series list (`routes/act/settings.py`)

### Admin Data (`routes/admin.py`)
- `GET /api/admin/users` - Get all users
- `GET /api/admin/user-activity/<email>` - Get user activity
- `POST /api/admin/update-user` - Update user data
- `GET /api/admin/clubs` - Get all clubs
- `POST /api/admin/save-club` - Save club data
- `DELETE /api/admin/delete-club/<club_id>` - Delete club
- `GET /api/admin/series` - Get all series
- `POST /api/admin/save-series` - Save series data
- `DELETE /api/admin/delete-series/<series_id>` - Delete series

### Settings (`routes/act/settings.py`)
- `GET /api/get-user-settings` - Get user settings
- `POST /api/update-settings` - Update user settings
- `POST /api/set-series` - Set user series
- `GET /api/get-clubs` - Get available clubs
- `GET /api/get-leagues` - Get available leagues

### Availability (`routes/act/availability.py`)
- `GET /api/availability` - Get availability data
- `POST /api/availability` - Update availability

### AI/Chat (`routes/act/rally_ai.py`)
- `POST /api/chat` - AI chat interface
- `GET /api/chat/debug/<thread_id>` - Debug chat thread
- `POST /api/chat/clear/<thread_id>` - Clear chat thread
- `POST /api/chat/optimize/<thread_id>` - Optimize chat thread
- `POST /api/chat/clear-cache` - Clear chat cache
- `POST /api/assistant/update` - Update assistant
- `GET /api/ai/stats` - Get AI statistics
- `POST /api/ai/reset-stats` - Reset AI statistics

### Training Data (`api/training_data.py`)
- `POST /api/get-training-data-by-topic` - Get training data by topic
- `GET /api/training-topics` - Get available training topics
- `GET /api/training-data-health` - Health check for training data

### Miscellaneous
- `GET /api/schedule` - Schedule data (`routes/act/schedule.py`)
- `GET /api/player-contact` - Player contact info (`routes/act/find_sub.py`)
- `GET /api/club-players` - Club players data (`routes/act/find_people_to_play.py`)
- `POST /api/generate-lineup` - Generate team lineup (`routes/act/lineup.py`)
- `POST /api/reserve-court` - Reserve court (`routes/act/court.py`)

## Frontend JSON Calls

### Direct JSON File Access
These are direct fetch calls to JSON files served as static assets:

#### Analysis Templates
- `templates/analysis/pti_vs_opponents_analysis.html`:
  - `/data/leagues/all/player_history.json`
  - `/data/leagues/all/match_history.json`
  - `/data/leagues/all/players.json`

#### Static JavaScript Files
- `static/js/research-me.js`:
  - `/data/leagues/all/match_history.json`
  - `/api/player-history`
  - `/api/player-court-stats/<player_name>`

- `static/js/fixed-research-me.js`:
  - `/data/leagues/all/match_history.json`
  - `/data/leagues/all/player_history.json`
  - `/api/player-history`

- `static/js/research-team.js`:
  - `/data/leagues/all/match_history.json`
  - `/data/leagues/all/series_stats.json`
  - `/api/team-matches`
  - `/api/research-team`

- `static/js/research-my-team.js`:
  - `/data/leagues/all/match_history.json`
  - `/data/leagues/all/series_stats.json`
  - `/api/research-my-team`
  - `/api/team-matches`
  - `/api/team-players/<team>`

### Mobile Templates
All mobile templates use API endpoints rather than direct file access:

#### `templates/mobile/analyze_me.html`
- `/api/player-history`

#### `templates/mobile/player_detail.html`
- `/api/player-history/<player_name>`

#### `templates/mobile/my_series.html`
- `/api/series-stats`

#### `templates/mobile/matches.html`
- `/api/team-matches`

#### `templates/mobile/rankings.html`
- `/api/players`

#### `templates/mobile/lineup.html`
- `/api/players`
- `/api/lineup-instructions`
- `/api/generate-lineup`

#### `templates/mobile/admin.html`
- `/api/admin/users`
- `/api/admin/delete-user`
- `/api/admin/clubs`
- `/api/admin/series`
- `/api/admin/user-activity/<email>`
- `/api/admin/update-user`

#### `templates/mobile/find_people_to_play.html`
- `/api/club-players`

#### `templates/mobile/contact_sub.html`
- `/api/player-contact`

#### `templates/mobile/find_subs.html`
- `/api/get-series`
- `/api/players`

#### `templates/mobile/ask_ai.html`
- `/api/find-training-video`
- `/api/chat`

#### `templates/mobile/improve.html`
- `/api/chat`
- `/api/find-training-video`

#### `templates/mobile/user_settings.html`
- `/api/get-leagues`
- `/api/get-clubs`
- `/api/get-series`
- `/api/get-user-settings`
- `/api/update-settings`

#### `templates/mobile/practice_times.html`
- `/api/add-practice-times`
- `/api/remove-practice-times`

#### `templates/mobile/availability.html` & `availability-calendar.html`
- `/api/availability`

#### `templates/mobile/team_schedule.html`
- `/api/team-schedule-data`

### Login Template
- `templates/login.html`:
  - `/api/get-clubs`
  - `/api/get-series`
  - `/api/login`
  - `/api/register`

## Service Layer Access

### Data Access Patterns

1. **Direct File Access**: Services read JSON files directly using Python's `open()` function
2. **API Endpoints**: Frontend components call REST API endpoints that return JSON data
3. **Hybrid Approach**: Some pages use both direct file access and API calls

### Key Service Functions

#### Mobile Service (`app/services/mobile_service.py`)
- `get_player_analysis()` - Player analysis data
- `get_mobile_team_data()` - Team data for mobile
- `get_mobile_series_data()` - Series data for mobile
- `get_teams_players_data()` - Teams and players data
- `get_player_search_data()` - Player search functionality
- `get_mobile_availability_data()` - Availability data
- `get_mobile_club_data()` - Club data
- `get_mobile_player_stats()` - Player statistics
- `get_club_players_data()` - Club players data
- `get_mobile_improve_data()` - Training/improvement data

#### Player Service (`app/services/player_service.py`)
- `get_player_analysis()` - Player analysis
- `get_player_analysis_by_name()` - Player analysis by name

#### API Service (`app/services/api_service.py`)
- Various functions for handling API data requests

## Notes and Recommendations

### ⚠️ Files That Need Path Updates
The following files still reference the old `data/leagues/apta` path and need to be updated:

1. `routes/act/schedule.py` - Lines 11, 95, 108
2. `api/training_data.py` - Line 38

### Data Flow Summary

1. **Mobile Pages**: Use API endpoints exclusively → Service layer → JSON files
2. **Desktop Analysis Pages**: Mix of direct JSON file access and API calls
3. **Static JavaScript**: Mostly direct JSON file access with some API calls
4. **Admin Functions**: API endpoints exclusively
5. **Scripts**: Direct file access for data processing

### Security Considerations

- Direct JSON file access exposes file structure to frontend
- API endpoints provide better abstraction and security
- Consider migrating all direct file access to API endpoints for consistency

### Performance Considerations

- Direct file access can be faster but less flexible
- API endpoints allow for data processing and filtering
- Consider caching strategies for frequently accessed data

---

*Last updated: December 2024*
*This documentation should be updated whenever new JSON access patterns are added to the application.* 