# Add Player Admin Guide

## Overview

The Add Player admin interface allows administrators to search for and add individual players to the Rally system by providing their basic information. The system automatically finds the player's ID by searching the league website. This is particularly useful for:

- Players who joined after the last scrape
- Players with unusual names that weren't captured
- Players from specific teams that need immediate access
- Testing and development purposes

## Access

Navigate to **Admin → Add Player** in the admin interface. This page is only accessible to users with admin privileges.

## How It Works

### 1. Player Search
The system searches the league website for a player matching your input by:

- **Team Discovery**: Finding the team page for the specified club and series
- **Player Search**: Locating the player by name on that team page
- **ID Extraction**: Extracting the player ID from the player link
- **Profile Scraping**: Scraping the player's full profile page

### 2. Data Extraction
Once the player is found, the system extracts:

- **Player Information**: First name, last name, player ID
- **Team Context**: Club, series, team name
- **Statistics**: PTI rating, wins, losses, win percentage
- **Status**: Captain/co-captain designation

### 2. Data Storage
- **JSON File**: Player data is saved to `data/leagues/{league}/players.json`
- **Database**: Player record is created/updated in the `players` table
- **Relationships**: Club, series, and team records are created if they don't exist

### 3. User Registration
Once a player is added, users can register with Rally and the system will automatically associate them with the correct player record using the existing association logic.

## Usage

### Step 1: Select League
Choose the league where the player competes:
- **APTA Chicago**: `aptachicago`
- **NSTF**: `nstf`
- **CNSWPL**: `cnswpl`
- **CITA**: `cita`

### Step 2: Enter Player Information
Provide the player's details:
- **First Name**: Player's first name as it appears on the website
- **Last Name**: Player's last name as it appears on the website
- **Club**: The facility where they play (e.g., "Glenbrook RC")
- **Series**: Their division level (e.g., "Series 8", "Division 1a")

### Step 3: Submit
Click "Search & Add Player" to:
1. Search the league website for the player
2. Extract the player ID automatically
3. Scrape the player's full profile data
4. Save to JSON file
5. Import to database
6. Display confirmation with all found information

## Search Process

### How the System Finds Players
1. **Team Discovery**: The system searches the league's teams page to find a team matching your club and series
2. **Player Search**: Once the team is found, it searches for a player with the specified name
3. **ID Extraction**: When the player is found, it automatically extracts their player ID from the link
4. **Profile Scraping**: Finally, it scrapes the player's full profile page to get complete information

### Search Strategy
- **League-Specific**: Different leagues use different search approaches
- **Fallback Methods**: If the primary search fails, the system tries alternative methods
- **Error Handling**: Clear feedback if the player cannot be found

## Technical Details

### Search Strategy
1. **Team Page Discovery**: Searches the league's teams page for matching club/series combinations
2. **Player Name Matching**: Looks for player names that match the input (case-insensitive)
3. **ID Extraction**: Uses regex patterns to extract player IDs from various link formats
4. **Profile Scraping**: Once ID is found, scrapes the full player profile page

### Scraping Strategy
1. **HTTP Request First**: Attempts direct HTTP request for speed
2. **Chrome WebDriver Fallback**: Uses Selenium if HTTP fails
3. **Multiple Parsing Methods**: Tries various selectors and patterns
4. **Fallback Logic**: Provides reasonable defaults for missing data

### Data Validation
- **Required Fields**: Player ID, first name, last name
- **Optional Fields**: PTI, wins, losses, captain status
- **Auto-creation**: Clubs, series, and teams are created if missing
- **Duplicate Prevention**: Updates existing players instead of creating duplicates

### Error Handling
- **Network Issues**: Automatic fallback between HTTP and WebDriver
- **Missing Data**: Graceful degradation with default values
- **Validation Errors**: Clear error messages and suggestions
- **Database Errors**: Transaction rollback on failure

## Troubleshooting

### Common Issues

#### Player Not Found
- **Cause**: Player doesn't exist on the team, or club/series combination is incorrect
- **Solution**: Verify the club name, series, and player name match exactly what appears on the league website

#### Scraping Failed
- **Cause**: League website is down or blocking requests
- **Solution**: Try again later or check website status

#### Database Import Failed
- **Cause**: Missing league, club, or series records
- **Solution**: Ensure the league is properly configured in the database

#### Invalid Data
- **Cause**: Website structure changed or parsing failed
- **Solution**: Check the scraped data and adjust parsing logic if needed

### Debug Information
The system provides detailed logging including:
- Scraping attempts and results
- Data extraction details
- Database operation results
- Error messages and stack traces

## Integration Points

### Existing Systems
- **Player Import Pipeline**: Compatible with bulk import scripts
- **User Registration**: Automatic player association
- **Team Management**: Player-team relationships maintained
- **Statistics**: Win/loss records integrated

### Data Flow
```
League Website → Player Scraper → JSON File → Database → User Registration
```

## Security Considerations

### Access Control
- **Admin Only**: Requires admin privileges
- **Session Validation**: Checks user authentication
- **Input Validation**: Sanitizes player IDs and league names

### Rate Limiting
- **Request Throttling**: Built-in delays between requests
- **Browser Management**: Proper cleanup of WebDriver instances
- **Error Handling**: Graceful failure without system impact

## Performance

### Optimization Features
- **HTTP First**: Fastest method for successful requests
- **WebDriver Fallback**: Only when needed
- **Batch Processing**: Efficient database operations
- **Resource Cleanup**: Automatic browser cleanup

### Expected Performance
- **Team Search**: 2-5 seconds to find the team page
- **Player Search**: 2-5 seconds to locate the player
- **Profile Scraping**: 2-5 seconds to scrape player data
- **Database Import**: 1-2 seconds to add to database
- **Total Time**: 7-17 seconds depending on search complexity

## Future Enhancements

### Planned Features
1. **Bulk Import**: Add multiple players at once
2. **Scheduled Scraping**: Automatic discovery of new players
3. **Data Validation**: Enhanced parsing and validation
4. **Notification System**: Alerts for failed imports
5. **Audit Trail**: Track all admin actions

### Integration Opportunities
1. **Match Scraper**: Trigger player scraping from match data
2. **Team Discovery**: Automatic player discovery from team pages
3. **Performance Monitoring**: Track scraping success rates
4. **Data Quality**: Validate scraped data against existing records

## Support

### Getting Help
1. **Check Logs**: Review server logs for detailed error information
2. **Test Script**: Use `test_add_player.py` to verify functionality
3. **Database Check**: Verify league, club, and series records exist
4. **Website Status**: Check if the league website is accessible

### Common Solutions
- **Player Not Found**: Verify club name, series, and player name match exactly what appears on the website
- **Team Not Found**: Check that the club and series combination exists in the league
- **Scraping Failures**: Check website accessibility and structure
- **Database Errors**: Ensure proper database setup and permissions
- **Performance Issues**: Monitor system resources and network connectivity

---

**Last Updated**: January 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
