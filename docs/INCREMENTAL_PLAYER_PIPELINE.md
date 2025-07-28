# 🎾 Incremental Player Pipeline

This document describes the modern, incremental player data pipeline for the Rally application. The pipeline is designed to be efficient, idempotent, and only scrape players who appeared in newly scraped matches.

## 📋 Overview

The incremental player pipeline consists of two main components:

1. **`scrape_players.py`** - Scrapes player data for specific `tenniscores_player_id`s only
2. **`import_players.py`** - Imports player data using upsert logic (ON CONFLICT DO UPDATE)

## 🚀 Key Features

- **🎯 Match-Based Targeting**: Only scrapes players who appeared in recently scraped matches
- **⚡ Automatic Player ID Extraction**: Extracts player IDs directly from match_history.json
- **🔄 Idempotent**: Can be run multiple times safely without creating duplicates
- **📊 Upsert Logic**: Uses `ON CONFLICT DO UPDATE` for reliable data updates
- **🔍 Comprehensive Logging**: Detailed progress tracking and error reporting

## 📁 File Structure

```
data/etl/
├── scrapers/
│   └── scrape_players.py          # Incremental player scraper
├── database_import/
│   └── import_players.py          # Player import with upsert logic
└── all/
    └── players_incremental_*.json # Scraped player data
```

## 🔧 Usage

### Step 1: Run Match Scraping First

The player scraper requires match data to identify which players to scrape:

```bash
# First, run match scraping to generate match_history.json
python3 data/etl/scrapers/scraper_match_scores.py aptachicago
```

### Step 2: Scrape Player Data

The player scraper automatically extracts player IDs from match history:

```bash
# Scrape players who appeared in matches
python3 data/etl/scrapers/scrape_players.py aptachicago
```

### Step 3: Import Player Data

```bash
# Import using the most recent players file
python3 data/etl/database_import/import_players.py

# Or specify a specific file
python3 data/etl/database_import/import_players.py data/leagues/all/players_incremental_20250115_143022.json
```

## 📊 Data Flow

### 1. Match Data Requirement

The player scraper requires `match_history.json` to identify which players to scrape:

```bash
# Step 1: Generate match data
python3 data/etl/scrapers/scraper_match_scores.py aptachicago

# Step 2: Extract player IDs from matches
python3 data/etl/scrapers/scrape_players.py aptachicago
```

### 2. Player ID Extraction

The system automatically extracts unique `tenniscores_player_id`s from the match history:

```python
# From match_history.json
{
  "Home Player 1 ID": "nndz-WkMrK3didjlnUT09",
  "Home Player 2 ID": "nndz-WlNhd3hMYi9nQT09",
  "Away Player 1 ID": "nndz-WkNHeHdiZjVoUT09",
  "Away Player 2 ID": "nndz-WkM2eHhidi9qUT09"
}
```

### 2. Player Scraping

For each player ID, the scraper:

1. Builds the URL: `https://{subdomain}.tenniscores.com/player/view?id={player_id}`
2. Scrapes the player profile page
3. Extracts:
   - `Player ID` (tenniscores_player_id)
   - `First Name` and `Last Name`
   - `Series` and `Series Mapping ID`
   - `Club` and `Location ID`
   - `League`
   - `PTI` (Performance Tracking Index)
   - `Wins`, `Losses`, `Win %`
   - `Captain` status

### 3. Data Import

The import script uses upsert logic to handle both new players and updates:

```sql
INSERT INTO players (
    tenniscores_player_id, first_name, last_name, team_id,
    league_id, club_id, series_id, pti, is_active, created_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, CURRENT_TIMESTAMP)
ON CONFLICT (tenniscores_player_id) DO UPDATE SET
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    team_id = EXCLUDED.team_id,
    league_id = EXCLUDED.league_id,
    club_id = EXCLUDED.club_id,
    series_id = EXCLUDED.series_id,
    pti = EXCLUDED.pti,
    updated_at = CURRENT_TIMESTAMP
```

**Note**: The import script maps the JSON fields to database columns:
- `Player ID` → `tenniscores_player_id`
- `First Name` → `first_name`
- `Last Name` → `last_name`
- `Series Mapping ID` → `team_id` (looked up)
- `Club` → `club_id` (looked up)
- `Series` → `series_id` (looked up)
- `PTI` → `pti`

## 🧪 Testing

### Complete Pipeline Test

Run the complete pipeline test to verify all components:

```bash
python3 scripts/test_player_pipeline.py
```

This test:
1. Extracts player IDs from match history
2. Scrapes player data for a sample of IDs
3. Imports the data using upsert logic
4. Tests the upsert functionality by modifying and re-importing

### Individual Component Tests

#### Test Player Scraper

```bash
# Ensure match_history.json exists first
python3 data/etl/scrapers/scraper_match_scores.py aptachicago

# Run player scraper (automatically extracts IDs from matches)
python3 data/etl/scrapers/scrape_players.py aptachicago
```

#### Test Player Import

```bash
# Import with test database
RALLY_DATABASE=test python3 data/etl/database_import/import_players.py
```

## 📈 Performance Benefits

### Before (Full Scraping)
- **Time**: 2-3 hours for all players
- **Requests**: 10,000+ HTTP requests
- **Data**: Scrapes all players regardless of changes

### After (Incremental)
- **Time**: 5-10 minutes for new players only
- **Requests**: 50-100 HTTP requests (only new players)
- **Data**: Only scrapes players who appeared in new matches

## 🔍 Monitoring and Logging

### Scraper Logs

```
🎾 Incremental Player Scraper for aptachicago
📊 League ID: APTA_CHICAGO
🌐 Base URL: https://aptachicago.tenniscores.com
✅ Browser setup complete

📊 Progress: 1/5 (20.0%)
🔍 Scraping player: nndz-WkMrK3didjlnUT09
✅ Successfully scraped: Becky Smith

📊 Progress: 2/5 (40.0%)
🔍 Scraping player: nndz-WlNhd3hMYi9nQT09
✅ Successfully scraped: John Doe
```

### Import Logs

```
🔧 Players ETL initialized
📁 Data directory: /path/to/data/leagues/all
📄 Players file: players_incremental_20250115_143022.json
📖 Loading players data from players_incremental_20250115_143022.json
✅ Loaded 5 player records

🔧 Pre-caching lookup data...
✅ Cached 4 leagues, 150 teams, 25 clubs, 20 series

🚀 Starting players import...
📊 Imported 5 player records so far...

📊 PLAYERS IMPORT SUMMARY
============================================================
📄 Total records processed: 5
✅ Successfully imported: 5
❌ Errors: 0
⏭️ Skipped: 0
🎉 100% success rate!
```

## 🛠️ Configuration

### Environment Variables

- `RALLY_DATABASE`: Database to use (`main`, `test`, `staging`)
- `CHROME_HEADLESS`: Set to `true` for headless browser mode

### League Configuration

The scraper automatically detects league configuration:

```python
# Supported leagues
platform_tennis_leagues = {"aptachicago", "aptanational", "nstf"}
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Player Not Found

```
⚠️ No data found for player: nndz-invalid-id
```

**Solution**: Verify the player ID exists in the match history and is valid.

#### 2. Browser Setup Failed

```
❌ Browser setup failed: ChromeDriver not found
```

**Solution**: Install Chrome and ChromeDriver, or use headless mode.

#### 3. Import Errors

```
❌ League not found: INVALID_LEAGUE
```

**Solution**: Check that the league ID is properly normalized and exists in the database.

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📋 Data Schema

### Input JSON Format

```json
[
  {
    "League": "APTA_CHICAGO",
    "Series": "Chicago 2",
    "Series Mapping ID": "Birchwood - 2",
    "Club": "Birchwood",
    "Location ID": "BIRCHWOOD",
    "Player ID": "nndz-WkNDNnhyYjVoZz09",
    "First Name": "Brett",
    "Last Name": "Stein",
    "PTI": "20.4",
    "Wins": "8",
    "Losses": "7",
    "Win %": "53.3%",
    "Captain": "",
    "source_league": "APTA_CHICAGO"
  }
]
```

### Database Schema

The import creates/updates records in the `players` table:

```sql
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    tenniscores_player_id TEXT UNIQUE NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    league_id INTEGER REFERENCES leagues(id) NOT NULL,
    club_id INTEGER REFERENCES clubs(id),
    series_id INTEGER REFERENCES series(id),
    pti NUMERIC(10,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 🚀 Future Enhancements

### Planned Features

1. **Batch Processing**: Process multiple leagues simultaneously
2. **Caching**: Cache player data to avoid re-scraping unchanged data
3. **Incremental Updates**: Only update fields that have changed
4. **Web Interface**: Admin interface for monitoring and manual runs
5. **Scheduling**: Automated runs based on match scraping schedule

### Integration Points

- **Match Scraping**: Automatically trigger player scraping after match imports
- **User Registration**: Link new users to scraped player data
- **Analytics**: Track player performance changes over time

## 📞 Support

For issues or questions about the incremental player pipeline:

1. Check the troubleshooting section above
2. Review the logs for specific error messages
3. Run the test script to verify functionality
4. Check the database schema and constraints

---

**Last Updated**: January 15, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅ 