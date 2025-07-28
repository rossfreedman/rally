# Multi-Series Match Scraper Guide

## Overview

The match scraper has been enhanced to support scraping multiple series simultaneously by specifying comma-separated series numbers. This allows for more efficient data collection when you need matches from specific series rather than scraping all series.

## New Functionality

### Multiple Series Support

You can now specify multiple series to scrape in a single command:

- **Single series**: `22` (scrapes Chicago 22)
- **Multiple series**: `19,22,24SW` (scrapes Chicago 19, 22, and 24SW)
- **All series**: `all` (scrapes all available series)

### Input Format

The series filter accepts the following formats:

```
22              # Single series
19,22           # Two series
19,22,24SW      # Three series with mixed formats
22,24SW,26      # Multiple series with different naming patterns
all             # All series (existing functionality)
```

## Usage Examples

### Command Line Usage

```bash
# Scrape specific series
python data/etl/scrapers/scraper_match_scores.py aptachicago
# Then enter: 19,22,24SW

# Or use the test script
python scripts/test_match_scraper_multi_series.py
```

### Programmatic Usage

```python
from data.etl.scrapers.scraper_match_scores import scrape_all_matches

# Scrape multiple series
results = scrape_all_matches("aptachicago", "19,22,24SW")

# Scrape single series
results = scrape_all_matches("aptachicago", "22")

# Scrape all series
results = scrape_all_matches("aptachicago", "all")
```

## How It Works

### Series Discovery

1. The scraper discovers all available series from the league's main page
2. It presents the list of discovered series to the user
3. The user can specify which series to scrape using the new multi-series format

### Filtering Logic

The new filtering logic:

1. **Splits comma-separated input**: `"19,22,24SW"` becomes `["19", "22", "24SW"]`
2. **Matches any filter**: Series that match ANY of the specified filters are included
3. **Case-insensitive matching**: `"22"` matches `"Chicago 22"`, `"Series 22"`, etc.
4. **Partial matching**: `"24SW"` matches `"Chicago 24SW"`, `"Series 24SW"`, etc.

### Example Matching

For input `"19,22,24SW"`:

- ✅ `"Chicago 19"` (matches "19")
- ✅ `"Chicago 22"` (matches "22") 
- ✅ `"Chicago 24SW"` (matches "24SW")
- ❌ `"Chicago 23"` (no match)
- ❌ `"Chicago 25"` (no match)

## Benefits

### Efficiency

- **Faster scraping**: Only scrape the series you need
- **Reduced bandwidth**: Avoid unnecessary data collection
- **Targeted testing**: Test specific series without full league scraping

### Flexibility

- **Selective updates**: Update only specific series that have new data
- **Incremental scraping**: Add new series to existing data
- **Custom combinations**: Mix and match series based on your needs

### Error Recovery

- **Partial failures**: If one series fails, others can still succeed
- **Retry logic**: Each series has independent retry attempts
- **Progress tracking**: See which series completed successfully

## Testing

Use the test script to verify the functionality:

```bash
python scripts/test_match_scraper_multi_series.py
```

The test script provides several test cases:

1. **Two series test**: `22,24` (Chicago 22 and 24)
2. **Three series test**: `19,22,24SW` (Chicago 19, 22, and 24SW)
3. **All series test**: `all` (for comparison)
4. **Custom test**: User-defined league and series filter

## Error Handling

### Input Validation

- **Empty input**: Treated as "all"
- **Invalid characters**: Stripped and cleaned
- **Duplicate filters**: Automatically deduplicated
- **No matches**: Clear error message with available series

### Scraping Errors

- **Individual series failures**: Logged but don't stop other series
- **Network timeouts**: Retry logic per series
- **Missing data**: Graceful handling with warnings

## Migration from Single Series

The new functionality is **backward compatible**:

- **Existing single series input**: Still works exactly as before
- **"all" option**: Unchanged behavior
- **Command line arguments**: No changes needed
- **API calls**: Same function signature

## Best Practices

### Series Selection

- **Start small**: Test with 2-3 series before large batches
- **Logical grouping**: Group related series (e.g., `22,23,24` for consecutive series)
- **Mixed formats**: Include different naming patterns (e.g., `22,24SW,26`)

### Performance

- **Batch size**: Limit to 5-10 series per run for optimal performance
- **Stealth delays**: Built-in delays prevent rate limiting
- **Progress monitoring**: Watch the progress output for each series

### Data Quality

- **Verification**: Check the output for each series
- **Deduplication**: Automatic deduplication handles overlaps
- **Validation**: Match data is validated before saving

## Troubleshooting

### Common Issues

1. **No series found**: Check available series names in the output
2. **Partial matches**: Verify series naming patterns
3. **Network errors**: Check internet connection and retry
4. **Browser issues**: Ensure Chrome/Chromium is available

### Debug Information

The scraper provides detailed output:

```
🔍 Multiple series filters detected: ['19', '22', '24SW']
🔍 Filtered to 3 series matching any of: ['19', '22', '24SW']
📋 Filtered series:
   1. Chicago 19
   2. Chicago 22  
   3. Chicago 24SW
```

## Future Enhancements

Potential improvements:

- **Regex patterns**: Support for more complex matching patterns
- **Series ranges**: Support for ranges like `"22-26"` or `"22,24-26"`
- **Exclusion patterns**: Support for excluding specific series
- **Batch processing**: Process multiple leagues with different series filters 