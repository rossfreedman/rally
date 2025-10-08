# APTA Directory Scraper

A stealth scraper for extracting player information from the APTA Chicago directory page.

## Features

- **Stealth Technology**: Uses undetected Chrome browser with anti-detection measures
- **Proxy Rotation**: Automatically rotates through residential proxies to avoid IP blocking
- **Smart Extraction**: Extracts player names, emails, and phone numbers using multiple patterns
- **CSV Export**: Saves data in CSV format with columns: First Name, Last Name, Email, Phone
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Error Handling**: Robust retry logic and graceful failure handling

## Usage

### Basic Usage
```bash
python scripts/scrape_apta_directory.py
```

### With Custom Output File
```bash
python scripts/scrape_apta_directory.py --output my_players.csv
```

### Fast Mode (for testing)
```bash
python scripts/scrape_apta_directory.py --fast
```

### Command Line Options
- `--output, -o`: Specify output CSV file path
- `--fast`: Use fast mode with reduced delays (for testing)

## Output Format

The scraper generates a CSV file with the following columns:
- **First Name**: Player's first name
- **Last Name**: Player's last name  
- **Email**: Player's email address
- **Phone**: Player's phone number

## Requirements

The scraper requires the following components from the Rally project:
- `data/etl/scrapers/helpers/stealth_browser.py`
- `data/etl/scrapers/helpers/proxy_manager.py`
- `data/etl/scrapers/helpers/user_agent_manager.py`

## Testing

Run the test script to verify everything is working:
```bash
python scripts/test_apta_scraper.py
```

## How It Works

1. **Initialization**: Sets up stealth browser with proxy rotation
2. **Page Access**: Uses stealth browser to access the APTA directory page
3. **Data Extraction**: Searches for player information using multiple patterns:
   - Email address patterns
   - Phone number patterns
   - Name patterns (First Last format)
   - HTML element analysis
4. **Data Matching**: Attempts to match names with emails and phones
5. **Deduplication**: Removes duplicate entries
6. **CSV Export**: Saves results to CSV file

## Stealth Features

- **User Agent Rotation**: Uses realistic browser user agents
- **Request Pacing**: Random delays between requests
- **Proxy Rotation**: Switches IP addresses to avoid detection
- **Anti-Detection**: Removes automation indicators
- **CAPTCHA Handling**: Automatically detects and handles blocks

## Logging

The scraper creates detailed logs in the format:
`apta_directory_scraper_YYYYMMDD_HHMMSS.log`

Logs include:
- Scraping progress
- Data extraction results
- Error messages
- Performance metrics

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root directory
2. **No Data Found**: The page structure may have changed; check the logs
3. **Proxy Issues**: The scraper will automatically retry with different proxies
4. **Blocking**: If you get blocked, wait a few minutes and try again

### Debug Mode

For detailed debugging, check the log file or run with verbose output:
```bash
python scripts/scrape_apta_directory.py --fast 2>&1 | tee debug.log
```

## Notes

- The scraper is designed to be respectful of the target website
- It uses appropriate delays and stealth measures
- Results may vary depending on the current page structure
- Some player information may not be publicly available on the directory page

## Support

If you encounter issues:
1. Check the log file for error messages
2. Run the test script to verify setup
3. Ensure all dependencies are properly installed
4. Verify proxy configuration is working
