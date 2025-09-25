# Rally Cron Jobs

This directory contains cron job scripts for automated data processing and scraping.

## APTA Chicago Scraper Sequence

### Overview

The `apta_chicago_scraper_sequence.py` script runs three APTA Chicago scrapers in sequence:

1. **Players Scraper** (`apta_scrape_players_simple.py`)
   - Scrapes current season player data from APTA Chicago series
   - Outputs: `data/leagues/APTA_CHICAGO/players.json`

2. **Match Scores Scraper** (`scrape_match_scores.py`)
   - Scrapes match scores and results
   - Outputs: `data/leagues/APTA_CHICAGO/match_scores.json`

3. **Stats Scraper** (`scrape_stats.py`)
   - Scrapes team statistics and standings
   - Outputs: `data/leagues/APTA_CHICAGO/series_stats.json`

### Features

- **Sequential Execution**: Runs scrapers one after another with validation
- **SMS Notifications**: Sends status updates to admin after each scraper
- **Error Handling**: Continues with remaining scrapers if one fails
- **Validation**: Checks output files exist and have content
- **Comprehensive Logging**: Detailed logs with timestamps
- **Final Summary**: Complete status report via SMS

### Usage

#### Manual Execution
```bash
# Run the complete sequence
python cron/apta_chicago_scraper_sequence.py

# Test the sequence (dry run)
python cron/test_apta_sequence.py
```

#### Railway Cron Configuration
```toml
[deploy.cronJobs.apta_chicago_sequence]
schedule = "0 3 * * *"  # Daily at 3 AM
command = "python cron/apta_chicago_scraper_sequence.py"
```

### SMS Notifications

The script sends SMS notifications to the admin phone number (`17732138911`) at key points:

1. **Start Notification**: When the sequence begins
2. **Individual Scraper Notifications**: After each scraper completes (success/failure)
3. **Final Summary**: Complete status report with all results

### Output Validation

Each scraper's output is validated by checking:
- Expected output files exist
- Files contain data (not empty)
- Files are in the correct location

### Error Handling

- **Individual Scraper Failures**: Script continues with remaining scrapers
- **Timeout Protection**: 30-minute timeout per scraper
- **Comprehensive Logging**: All errors logged with details
- **SMS Alerts**: Immediate notification of failures

### Configuration

#### Environment Variables
- `TEST_MODE`: Set to `true` for testing (prevents actual SMS sending)
- `CRON_JOB_MODE`: Set by Railway for cron execution

#### Admin Phone Number
- Hardcoded: `17732138911` (Ross's phone)
- Can be modified in the script if needed

### Testing

Use the test script to verify everything works:

```bash
python cron/test_apta_sequence.py
```

The test script checks:
- SMS notification functionality
- Scraper script availability
- Data directory structure
- Sequence script syntax
- Dry run execution

### Logs

The script provides detailed logging:
- Timestamped messages
- Success/failure status for each step
- Error details and stack traces
- Performance metrics (duration, etc.)

### Dependencies

- Python 3.7+
- Rally project dependencies
- SMS notification service (Twilio)
- All three scraper scripts must be available

### Troubleshooting

#### Common Issues

1. **SMS Notifications Not Working**
   - Check Twilio configuration in `app/services/notifications_service.py`
   - Verify phone number format

2. **Scraper Scripts Not Found**
   - Ensure all scraper scripts exist in their expected locations
   - Check file permissions

3. **Data Directory Issues**
   - Verify `data/leagues/APTA_CHICAGO/` directory exists
   - Check write permissions

4. **Timeout Issues**
   - Increase timeout in script if needed
   - Check network connectivity
   - Verify scraper performance

#### Debug Mode

To run in debug mode with more verbose output:
```bash
# Set debug environment variable
export DEBUG_MODE=true
python cron/apta_chicago_scraper_sequence.py
```

### Monitoring

The script provides comprehensive monitoring through:
- SMS notifications for all status changes
- Detailed console logging
- File validation checks
- Performance timing

Monitor the Railway logs for detailed execution information.

### Maintenance

#### Regular Tasks
- Monitor SMS notification delivery
- Check scraper output file sizes
- Review error logs for patterns
- Update phone numbers if needed

#### Updates
- Modify scraper arguments in the script as needed
- Update validation patterns if output formats change
- Adjust timeouts based on performance
- Add new scrapers to the sequence if needed
