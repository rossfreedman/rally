# Master Tennis Scraper

The Master Tennis Scraper is a comprehensive automation script that runs all individual scrapers in sequence for complete data collection from any TennisScores league website.

## Features

- **Complete Automation**: Run all 5 scrapers with a single command
- **Single Prompt**: Only asks for league subdomain once
- **Progress Tracking**: Real-time progress updates with timing information
- **Error Handling**: Continues scraping even if individual scrapers fail
- **Comprehensive Reporting**: Detailed success/failure reports and timing statistics
- **Data Organization**: All data saved to organized league-specific directories

## Usage

### Basic Usage

```bash
python scrapers/master_scraper.py
```

### What It Does

The master scraper runs these 5 individual scrapers in sequence:

1. **Player Data Scraper** - Collects all player information with detailed stats
2. **Match History Scraper** - Scrapes all match results and scores
3. **Schedule Scraper** - Collects upcoming match schedules
4. **Team Statistics Scraper** - Gathers team standings and performance data
5. **Player History Scraper** - Collects detailed player match history

### Supported Leagues

Any TennisScores league subdomain, including:
- `aptachicago` (APTA Chicago)
- `nstf` (NSTF)
- `aptanational` (APTA National)
- And any other TennisScores league

### Example Session

```
🎾 TennisScores Master Scraper - Complete Data Collection Suite
======================================================================
🔍 This script will run ALL scrapers in sequence for comprehensive data collection
📊 Includes: Players, Matches, Schedules, Statistics, and Player History
⚡ Fully automated - no additional prompts after league selection

Enter league subdomain (e.g., 'aptachicago', 'nstf'): aptachicago

🌐 Target URL: https://aptachicago.tenniscores.com

📋 SCRAPING PLAN:
  🌐 League: APTACHICAGO
  📊 Scrapers: 5 (Players, Matches, Schedules, Stats, Player History)
  ⏱️  Estimated time: 10-30 minutes (depends on league size)
  🔄 Mode: Fully automated (no additional prompts)

🚀 Ready to start complete data collection? (y/N): y
```

### Data Output

All scraped data is saved to:
```
data/leagues/[LEAGUE_ID]/
├── players.json              # Player data from scraper_players.py
├── match_history.json        # Match results from scraper_match_scores.py
├── schedules.json           # Schedules from scraper_schedule.py
├── series_stats.json        # Team statistics from scraper_stats.py
└── player_history.json      # Player history from scraper_players_history.py
```

### Performance

- **Typical runtime**: 10-30 minutes depending on league size
- **Memory usage**: Moderate (Chrome browser instances)
- **Network usage**: Respectful rate limiting with delays between requests

### Error Handling

- Individual scraper failures don't stop the entire process
- Comprehensive error logging and reporting
- Partial data is saved even if some scrapers fail
- Full stack traces available for debugging

### Benefits Over Individual Scrapers

1. **Convenience**: One command instead of running 5 separate scripts
2. **Efficiency**: Optimal scraping order and shared setup
3. **Reliability**: Centralized error handling and recovery
4. **Reporting**: Comprehensive success/failure tracking
5. **Automation**: No need to manually run each scraper

## Individual Scrapers

The individual scrapers can still be run standalone if needed:

- `python scrapers/scraper_players.py`
- `python scrapers/scraper_match_scores.py`
- `python scrapers/scraper_schedule.py`
- `python scrapers/scraper_stats.py`
- `python scrapers/scraper_players_history.py`

Each individual scraper will prompt for the league subdomain when run standalone.

## Requirements

- Python 3.6+
- Chrome browser (for Selenium-based scrapers)
- Required Python packages (see main requirements.txt)

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all scraper files are in the same directory
2. **Chrome Driver Issues**: Make sure Chrome browser is installed
3. **Network Timeouts**: Some leagues may have slower response times
4. **Memory Issues**: Close other applications if running into memory problems

### Getting Help

If a scraper fails:
1. Check the detailed error output in the console
2. Try running the individual scraper standalone for more detailed debugging
3. Ensure the league subdomain is correct and the website is accessible

## Technical Notes

- Uses Python's `importlib` to dynamically import scraper modules
- Implements comprehensive error handling with try/catch blocks
- Provides detailed timing and performance metrics
- Respects server resources with appropriate delays between requests
- Maintains backward compatibility with existing individual scrapers 