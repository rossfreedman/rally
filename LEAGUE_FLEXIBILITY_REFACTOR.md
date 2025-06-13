# League Flexibility Refactor Guide

## Overview
The Rally application currently has hard-coded assumptions for APTA and NSTF leagues throughout the codebase. This document outlines how to make the application truly league-agnostic and easily extensible for new leagues.

## Current Problem

### Hard-coded League Assumptions
The codebase currently contains ~50+ instances of hard-coded league logic:

```python
# ❌ Current hard-coded approach
if user_league_id.startswith('APTA'):
    # APTA-specific logic
else:
    # Non-APTA logic

if league_id == 'NSTF':
    # NSTF-specific format
else:
    # APTA format
```

### Impact
- **Adding new leagues requires code changes in 10+ files**
- **Maintenance burden increases with each new league**
- **Risk of breaking existing leagues when adding new ones**
- **Inconsistent behavior across different parts of the application**

## Solution: League Configuration System

### 1. Database Schema Enhancement

Create a `league_configurations` table to store league-specific settings:

```sql
CREATE TABLE league_configurations (
    id SERIAL PRIMARY KEY,
    league_id VARCHAR(255) REFERENCES leagues(league_id),
    config_key VARCHAR(255) NOT NULL,
    config_value TEXT,
    data_type VARCHAR(50) DEFAULT 'string',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(league_id, config_key)
);

-- Example configurations
INSERT INTO league_configurations (league_id, config_key, config_value, data_type) VALUES
('APTA_CHICAGO', 'courts_per_match', '4', 'integer'),
('APTA_CHICAGO', 'team_name_format', '{club} - {series_number}', 'string'),
('APTA_CHICAGO', 'data_directory', 'apta', 'string'),
('APTA_CHICAGO', 'scoring_system', 'apta_standard', 'string'),

('NSTF', 'courts_per_match', '5', 'integer'),
('NSTF', 'team_name_format', '{club} S{series_code}', 'string'),
('NSTF', 'data_directory', 'NSTF', 'string'),
('NSTF', 'scoring_system', 'nstf_standard', 'string'),

('APTA_NATIONAL', 'courts_per_match', '4', 'integer'),
('APTA_NATIONAL', 'team_name_format', '{club} - {series_number}', 'string'),
('APTA_NATIONAL', 'data_directory', 'apta_national', 'string'),
('APTA_NATIONAL', 'scoring_system', 'apta_standard', 'string');
```

### 2. League Configuration Service

Create `app/services/league_config_service.py`:

```python
from database_utils import execute_query_one, execute_query
from functools import lru_cache

class LeagueConfigService:
    
    @staticmethod
    @lru_cache(maxsize=100)
    def get_config(league_id: str, config_key: str, default_value=None):
        """Get a configuration value for a specific league"""
        try:
            result = execute_query_one(
                "SELECT config_value, data_type FROM league_configurations WHERE league_id = %s AND config_key = %s",
                [league_id, config_key]
            )
            
            if not result:
                return default_value
                
            value = result['config_value']
            data_type = result['data_type']
            
            # Convert to appropriate Python type
            if data_type == 'integer':
                return int(value)
            elif data_type == 'boolean':
                return value.lower() in ('true', '1', 'yes')
            elif data_type == 'json':
                import json
                return json.loads(value)
            else:
                return value
                
        except Exception as e:
            print(f"Error getting league config {league_id}.{config_key}: {e}")
            return default_value
    
    @staticmethod
    @lru_cache(maxsize=50)
    def get_all_configs(league_id: str):
        """Get all configuration values for a league as a dictionary"""
        try:
            results = execute_query(
                "SELECT config_key, config_value, data_type FROM league_configurations WHERE league_id = %s",
                [league_id]
            )
            
            configs = {}
            for result in results:
                key = result['config_key']
                value = result['config_value']
                data_type = result['data_type']
                
                # Convert to appropriate Python type
                if data_type == 'integer':
                    configs[key] = int(value)
                elif data_type == 'boolean':
                    configs[key] = value.lower() in ('true', '1', 'yes')
                elif data_type == 'json':
                    import json
                    configs[key] = json.loads(value)
                else:
                    configs[key] = value
                    
            return configs
            
        except Exception as e:
            print(f"Error getting all league configs for {league_id}: {e}")
            return {}
    
    @staticmethod
    def clear_cache():
        """Clear the configuration cache"""
        LeagueConfigService.get_config.cache_clear()
        LeagueConfigService.get_all_configs.cache_clear()
```

### 3. Team Name Format System

Create `app/utils/team_name_formatter.py`:

```python
from app.services.league_config_service import LeagueConfigService
import re

class TeamNameFormatter:
    
    @staticmethod
    def format_team_name(league_id: str, club: str, series: str):
        """Format team name according to league-specific rules"""
        
        # Get the format template from league configuration
        format_template = LeagueConfigService.get_config(
            league_id, 
            'team_name_format', 
            '{club} - {series}'  # Default APTA format
        )
        
        # Extract series components
        series_number = None
        series_code = None
        
        # Try to extract number (e.g., "22" from "Chicago 22")
        number_match = re.search(r'\d+', series)
        if number_match:
            series_number = number_match.group()
        
        # Try to extract series code (e.g., "2B" from "Series 2B")
        if series.startswith('Series '):
            series_code = series.replace('Series ', '')
        
        # Format the team name
        try:
            return format_template.format(
                club=club,
                series=series,
                series_number=series_number or '',
                series_code=series_code or ''
            )
        except KeyError as e:
            print(f"Invalid format template for {league_id}: {format_template}, missing key: {e}")
            return f"{club} - {series}"  # Fallback
```

## Refactoring Steps

### Phase 1: Core Infrastructure
1. ✅ **Create league configuration database table**
2. ✅ **Implement LeagueConfigService**
3. ✅ **Create TeamNameFormatter utility**
4. **Add configuration seeding script**

### Phase 2: Court Assignment Logic
1. ✅ **Make court assignment dynamic** (COMPLETED)
2. **Remove hard-coded court counts**
3. **Test with all leagues**

### Phase 3: Replace Hard-coded League Checks

#### Files to Update:

**`app/services/mobile_service.py`** (~15 instances)
```python
# ❌ Before
if user_league_id.startswith('APTA'):
    return match_league_id == 'APTA_CHICAGO' or not match_league_id

# ✅ After  
def is_match_in_user_league(match, user_league_id):
    match_league_id = match.get('league_id')
    if not user_league_id:
        return True  # Show all if no league specified
    return match_league_id == user_league_id
```

**`app/routes/player_routes.py`** (~10 instances)
```python
# ❌ Before
if user_league_id and not user_league_id.startswith('APTA'):
    players_file = os.path.join(project_root, 'data', 'leagues', user_league_id, 'players.json')
else:
    players_file = os.path.join(project_root, 'data', 'leagues', 'apta', 'players.json')

# ✅ After
data_directory = LeagueConfigService.get_config(user_league_id, 'data_directory', 'default')
players_file = os.path.join(project_root, 'data', 'leagues', data_directory, 'players.json')
```

**`app/routes/api_routes.py`** (~5 instances)
```python
# ❌ Before
if user_league_id.startswith('APTA'):
    # APTA-specific team filtering
    
# ✅ After
# Use generic league-based filtering
```

### Phase 4: Team Name Generation
Replace hard-coded team name logic:

```python
# ❌ Before (in mobile_service.py line 2326)
if league_id == 'NSTF':
    # NSTF format: "Tennaqua S2B" from series "Series 2B"
    if series_name.startswith('Series '):
        series_part = series_name.replace('Series ', 'S')
        team_name = f"{club_name} {series_part}"
else:
    # APTA format: "Tennaqua - 22" from series "Chicago 22"
    numbers = re.findall(r'\d+', series_name)
    if numbers:
        series_number = numbers[-1]
        team_name = f"{club_name} - {series_number}"

# ✅ After
team_name = TeamNameFormatter.format_team_name(league_id, club_name, series_name)
```

### Phase 5: File Path Generation
Create `app/utils/league_file_paths.py`:

```python
from app.services.league_config_service import LeagueConfigService
import os

class LeagueFilePaths:
    
    @staticmethod
    def get_data_directory(league_id: str):
        """Get the data directory for a league"""
        return LeagueConfigService.get_config(league_id, 'data_directory', 'default')
    
    @staticmethod
    def get_players_file(league_id: str, project_root: str):
        """Get the players.json file path for a league"""
        data_dir = LeagueFilePaths.get_data_directory(league_id)
        return os.path.join(project_root, 'data', 'leagues', data_dir, 'players.json')
    
    @staticmethod
    def get_team_history_file(league_id: str, project_root: str):
        """Get the team_history.json file path for a league"""
        data_dir = LeagueFilePaths.get_data_directory(league_id)
        return os.path.join(project_root, 'data', 'leagues', data_dir, 'team_history.json')
```

## Testing Strategy

### 1. Unit Tests
Create tests for each league configuration:

```python
# tests/test_league_flexibility.py
def test_apta_court_assignment():
    # Test APTA gets 4 courts
    
def test_nstf_court_assignment():
    # Test NSTF gets 5 courts
    
def test_team_name_formatting():
    # Test each league's team name format
    
def test_file_path_generation():
    # Test league-specific file paths
```

### 2. Integration Tests
- Test mobile my-team page with each league
- Test court assignments with real data
- Test team name resolution

### 3. Migration Testing
- Ensure existing functionality works unchanged
- Test with mixed league data

## Implementation Checklist

### Database Changes
- [ ] Create `league_configurations` table
- [ ] Seed initial configurations for APTA_CHICAGO, NSTF, APTA_NATIONAL
- [ ] Add migration script

### New Services
- [ ] Implement `LeagueConfigService`
- [ ] Implement `TeamNameFormatter`
- [ ] Implement `LeagueFilePaths`
- [ ] Add proper error handling and fallbacks

### Code Refactoring
- [ ] Update `app/services/mobile_service.py` (15 locations)
- [ ] Update `app/routes/player_routes.py` (10 locations)
- [ ] Update `app/routes/api_routes.py` (5 locations)
- [ ] Remove all `league_id.startswith('APTA')` checks
- [ ] Remove all hard-coded league ID comparisons

### Court Assignment (✅ COMPLETED)
- [x] Make court assignment dynamic
- [x] Remove hard-coded 4-court assumption
- [x] Test with APTA (4 courts) and NSTF (5 courts)

### Testing
- [ ] Write unit tests for new services
- [ ] Test each league independently
- [ ] Test mixed league scenarios
- [ ] Performance testing with configuration caching

## Configuration Examples

### Adding a New League
To add a new league, only database configuration is needed:

```sql
-- Add league to leagues table
INSERT INTO leagues (league_id, league_name, league_url) 
VALUES ('USTA_TEXAS', 'USTA Texas', 'https://texas.usta.com/');

-- Configure league settings
INSERT INTO league_configurations (league_id, config_key, config_value, data_type) VALUES
('USTA_TEXAS', 'courts_per_match', '3', 'integer'),
('USTA_TEXAS', 'team_name_format', '{club} {series_code}', 'string'),
('USTA_TEXAS', 'data_directory', 'usta_texas', 'string'),
('USTA_TEXAS', 'scoring_system', 'usta_standard', 'string');
```

No code changes required!

### Configuration Options
Available configuration keys:

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| `courts_per_match` | integer | Number of courts per team match | `4` |
| `team_name_format` | string | Template for team names | `{club} - {series_number}` |
| `data_directory` | string | Directory name in `data/leagues/` | `apta` |
| `scoring_system` | string | Scoring system identifier | `apta_standard` |
| `match_duration_minutes` | integer | Expected match duration | `120` |
| `season_start_month` | integer | Month when season starts | `9` |
| `season_end_month` | integer | Month when season ends | `4` |

### Template Variables
Available in `team_name_format`:

| Variable | Description | Example |
|----------|-------------|---------|
| `{club}` | Club name | `Tennaqua` |
| `{series}` | Full series name | `Chicago 22` |
| `{series_number}` | Extracted number | `22` |
| `{series_code}` | Extracted code | `2B` |

## Benefits After Refactoring

### For Developers
- **Single source of truth** for league configurations
- **Easy to add new leagues** without code changes
- **Consistent behavior** across the application
- **Better testability** with isolated league logic

### For Users
- **Reliable court assignments** regardless of league
- **Consistent UI behavior** across all leagues
- **Faster feature rollouts** to new leagues

### For Maintenance
- **Reduced code duplication**
- **Centralized configuration management**
- **Easier debugging** of league-specific issues
- **Clear separation of concerns**

## Migration Plan

### Week 1: Infrastructure
- Set up database schema
- Implement core services
- Create unit tests

### Week 2: Mobile Services Refactor
- Update `mobile_service.py`
- Test court assignment logic
- Verify team name formatting

### Week 3: Routes Refactor
- Update `player_routes.py`
- Update `api_routes.py`
- Test file path generation

### Week 4: Testing & Validation
- Comprehensive testing with all leagues
- Performance validation
- Production deployment

## Success Metrics

### Code Quality
- [ ] Zero hard-coded league checks remaining
- [ ] All leagues use the same code paths
- [ ] Configuration cache hit rate > 95%

### Functionality
- [ ] All existing features work unchanged
- [ ] Court assignments correct for all leagues
- [ ] Team names formatted correctly
- [ ] File paths resolve correctly

### Extensibility
- [ ] New league can be added in < 5 minutes
- [ ] No code changes needed for new leagues
- [ ] Configuration changes take effect immediately

---

**Next Steps:**
1. Implement the database schema changes
2. Create the LeagueConfigService
3. Start refactoring mobile_service.py with the new approach
4. Test thoroughly with existing APTA and NSTF data

This refactor will make Rally truly league-agnostic and easily extensible for future growth! 