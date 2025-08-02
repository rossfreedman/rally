# Enhanced Stealth Scraper Architecture Guide

## Overview

The Rally tennis scraper has been completely refactored with comprehensive stealth measures to minimize detection and rate limiting while scraping TennisScores.com. This guide covers all the enhanced features and best practices.

## 🎯 Key Features

### 1. Smart Request Pacing
- **Randomized delays**: `time.sleep(random.uniform(2, 6))` between requests
- **Configurable timing**: Adjustable min/max delays via CLI
- **Fast mode**: `--fast` flag for testing with reduced delays
- **League-level pacing**: Additional delays between league iterations

### 2. IP Rotation Strategy
- **Intelligent rotation**: Every 20-50 requests per session
- **Dead proxy detection**: Automatically blacklists failing proxies
- **Success rate tracking**: Prioritizes healthy proxies
- **Sticky sessions**: 10-minute duration per IP
- **Health monitoring**: Continuous proxy validation

### 3. Retry & Backoff Logic
- **Exponential backoff**: 1s → 3s → 6s up to 3 attempts
- **Smart failure handling**: Rotates proxy on failure
- **Graceful degradation**: Continues scraping even with failures
- **Comprehensive logging**: Tracks all retry attempts

### 4. CAPTCHA / Block Detection
- **Multi-pattern detection**:
  - "Access Denied" pages
  - CAPTCHA screens
  - Blank/short pages (< 1000 chars)
  - HTTP 403/429 status codes
- **Automatic response**: Rotates proxy and retries
- **Detection logging**: Tracks all blocking events

### 5. Session Fingerprinting & Headers
- **Randomized User-Agent**: Rotates between realistic browsers
- **Accept-Language**: Varied language preferences
- **Browser dimensions**: Realistic window sizes
- **Automation hiding**: Removes webdriver indicators
- **Stealth scripts**: Injects anti-detection JavaScript

### 6. Request Budgeting
- **Per-session limits**: 40 requests per proxy (soft threshold)
- **Hard limits**: Automatic blacklisting after repeated failures
- **Budget tracking**: Monitors request volume per IP
- **Intelligent rotation**: Switches before hitting limits

### 7. Comprehensive Logging & Metrics
- **Real-time monitoring**: Live status updates
- **Session summaries**: Complete metrics after each run
- **Detection tracking**: All blocking events logged
- **Performance metrics**: Request counts, success rates, timing

## 🏗️ Architecture Components

### Enhanced Stealth Browser (`stealth_browser.py`)

```python
from data.etl.scrapers.stealth_browser import create_stealth_browser

# Create browser with stealth config
browser = create_stealth_browser(
    fast_mode=False,
    verbose=True,
    environment="production"
)

# Make safe requests
with browser as stealth_browser:
    html = stealth_browser.get_html("https://example.com")
```

**Key Features:**
- Automatic proxy rotation
- CAPTCHA detection
- Retry logic with exponential backoff
- Session metrics tracking
- Stealth script injection

### Enhanced Proxy Manager (`proxy_manager.py`)

```python
from data.etl.scrapers.proxy_manager import get_proxy_rotator

rotator = get_proxy_rotator()
proxy = rotator.get_proxy()  # Gets next healthy proxy
rotator.report_success()     # Reports successful request
rotator.report_failure()     # Reports failed request
```

**Key Features:**
- Dead proxy detection and blacklisting
- Success rate tracking per proxy
- Intelligent rotation based on health
- Automatic testing of all proxies
- Comprehensive status reporting

### Enhanced Match Scraper (`scrape_match_scores.py`)

```python
# Enhanced scraping with stealth measures
matches = scrape_all_matches(
    league_subdomain="nstf",
    fast_mode=False,
    verbose=True,
    delta_mode=True,
    start_date="2025-01-01",
    end_date="2025-01-31"
)
```

**Key Features:**
- Integrated stealth browser
- Delta scraping with date ranges
- Comprehensive error handling
- Detailed metrics tracking
- Configurable stealth behavior

### Enhanced Master Scraper (`master_scraper.py`)

```python
# Run with enhanced stealth features
python3 data/etl/scrapers/master_scraper.py \
    --league "North Shore Tennis Foundation" \
    --fast \
    --verbose \
    --max-retries 3 \
    --min-delay 2.0 \
    --max-delay 6.0
```

**Key Features:**
- Intelligent strategy selection (DELTA vs FULL)
- Comprehensive stealth integration
- Detailed logging and metrics
- Configurable behavior via CLI
- Automatic proxy management

## 🚀 Usage Examples

### Basic Stealth Scraping

```bash
# Standard stealth mode
python3 data/etl/scrapers/master_scraper.py --league "NSTF"

# Fast mode for testing
python3 data/etl/scrapers/master_scraper.py --league "NSTF" --fast

# Verbose mode for debugging
python3 data/etl/scrapers/master_scraper.py --league "NSTF" --verbose
```

### Advanced Configuration

```bash
# Custom stealth settings
python3 data/etl/scrapers/master_scraper.py \
    --league "NSTF" \
    --max-retries 5 \
    --min-delay 3.0 \
    --max-delay 8.0 \
    --requests-per-proxy 25 \
    --session-duration 900 \
    --timeout 45 \
    --verbose
```

### Delta Scraping

```bash
# Force incremental scraping
python3 data/etl/scrapers/master_scraper.py \
    --league "NSTF" \
    --force-incremental

# Full scraping
python3 data/etl/scrapers/master_scraper.py \
    --league "NSTF" \
    --force-full
```

### Direct Match Scraper Usage

```bash
# Scrape with date range
python3 data/etl/scrapers/scrape_match_scores.py \
    nstf \
    --start-date 2025-01-01 \
    --end-date 2025-01-31 \
    --delta-mode \
    --fast \
    --verbose
```

## 📊 Monitoring & Metrics

### Session Metrics

Each scraping session tracks comprehensive metrics:

```python
{
    "session_id": "session_1234567890",
    "duration": 45.2,
    "total_requests": 150,
    "successful_requests": 142,
    "failed_requests": 8,
    "success_rate": 94.7,
    "proxy_rotations": 5,
    "detections": {
        "captcha": 2,
        "access_denied": 1,
        "rate_limit": 0
    },
    "leagues_scraped": ["NSTF", "APTA_CHICAGO"]
}
```

### Proxy Health Monitoring

```python
{
    "total_proxies": 100,
    "healthy_proxies": 87,
    "dead_proxies": 13,
    "current_proxy": 10045,
    "request_count": 25,
    "total_rotations": 3,
    "session_duration": 300.5,
    "proxy_health": {
        "10001": {
            "status": "active",
            "success_rate": 95.2,
            "total_requests": 42,
            "consecutive_failures": 0
        }
    }
}
```

## 🛡️ Anti-Detection Features

### 1. Browser Fingerprinting Protection

- **User-Agent Rotation**: 5 realistic desktop browsers
- **Window Dimensions**: Realistic screen sizes
- **Language Headers**: Varied Accept-Language
- **Automation Hiding**: Removes webdriver indicators

### 2. Request Pattern Randomization

- **Random Delays**: 2-6 seconds between requests
- **Variable Timing**: Non-uniform request patterns
- **Session Limits**: Prevents overuse of single IP
- **Natural Browsing**: Mimics human behavior

### 3. Proxy Intelligence

- **Health Monitoring**: Continuous proxy validation
- **Failure Tracking**: Automatic blacklisting
- **Success Prioritization**: Uses best-performing proxies
- **Geographic Distribution**: US-based residential IPs

### 4. Detection Response

- **Immediate Rotation**: Switches proxy on detection
- **Retry Logic**: Exponential backoff with new IP
- **Graceful Degradation**: Continues despite failures
- **Comprehensive Logging**: Tracks all events

## 🔧 Configuration Options

### Stealth Configuration

```python
@dataclass
class StealthConfig:
    fast_mode: bool = False          # Reduced delays for testing
    verbose: bool = False            # Detailed logging
    environment: str = "production"  # Environment mode
    max_retries: int = 3            # Maximum retry attempts
    min_delay: float = 2.0          # Minimum delay between requests
    max_delay: float = 6.0          # Maximum delay between requests
    timeout: int = 30               # Request timeout
    requests_per_proxy: int = 30    # Requests per proxy before rotation
    session_duration: int = 600     # Session duration in seconds
```

### CLI Arguments

```bash
# Core arguments
--league LEAGUE              # Specific league to scrape
--force-full                # Force full scraping
--force-incremental         # Force incremental scraping
--environment {local,staging,production}  # Environment mode

# Stealth configuration
--fast                      # Enable fast mode (reduced delays)
--verbose                   # Enable verbose logging
--max-retries INT           # Maximum retry attempts
--min-delay FLOAT           # Minimum delay between requests
--max-delay FLOAT           # Maximum delay between requests
--requests-per-proxy INT    # Requests per proxy before rotation
--session-duration INT      # Session duration in seconds
--timeout INT               # Request timeout in seconds
```

## 🧪 Testing

### Run Test Suite

```bash
# Test all stealth features
python3 scripts/test_enhanced_stealth.py
```

### Individual Component Tests

```python
# Test proxy rotation
from data.etl.scrapers.proxy_manager import get_proxy_rotator
rotator = get_proxy_rotator()
proxy = rotator.get_proxy()
status = rotator.get_status()

# Test stealth browser
from data.etl.scrapers.stealth_browser import create_stealth_browser
with create_stealth_browser(fast_mode=True) as browser:
    html = browser.get_html("https://httpbin.org/ip")
```

## 📈 Performance Optimization

### 1. Request Efficiency

- **Delta Scraping**: Only scrape missing data
- **Intelligent Strategy**: Choose DELTA vs FULL based on volume
- **Parallel Processing**: Multiple leagues simultaneously
- **Caching**: Reuse successful proxy sessions

### 2. Resource Management

- **Proxy Pool**: 100+ US residential IPs
- **Session Recycling**: 10-minute sessions per IP
- **Failure Isolation**: Individual proxy blacklisting
- **Health Monitoring**: Continuous proxy validation

### 3. Error Handling

- **Graceful Degradation**: Continue despite failures
- **Automatic Recovery**: Retry with new proxies
- **Comprehensive Logging**: Track all issues
- **Alert System**: Notify on critical failures

## 🔒 Security Best Practices

### 1. Proxy Management

- **Geographic Distribution**: US-based residential IPs only
- **Session Limits**: Prevent overuse of single IP
- **Health Monitoring**: Continuous validation
- **Failure Isolation**: Individual proxy blacklisting

### 2. Request Patterns

- **Natural Timing**: Random delays between requests
- **Human-like Behavior**: Realistic browsing patterns
- **Session Limits**: Prevent excessive requests
- **Geographic Consistency**: US-based requests only

### 3. Detection Avoidance

- **Stealth Headers**: Realistic browser headers
- **Automation Hiding**: Remove detection indicators
- **Pattern Randomization**: Non-uniform request timing
- **Session Management**: Proper session lifecycle

## 🚨 Troubleshooting

### Common Issues

1. **Proxy Failures**
   ```bash
   # Check proxy health
   python3 -c "from data.etl.scrapers.proxy_manager import get_proxy_rotator; print(get_proxy_rotator().get_status())"
   ```

2. **Detection Events**
   ```bash
   # Run with verbose logging
   python3 data/etl/scrapers/master_scraper.py --league "NSTF" --verbose
   ```

3. **Performance Issues**
   ```bash
   # Use fast mode for testing
   python3 data/etl/scrapers/master_scraper.py --league "NSTF" --fast
   ```

### Debug Mode

```bash
# Enable comprehensive debugging
python3 data/etl/scrapers/master_scraper.py \
    --league "NSTF" \
    --verbose \
    --fast \
    --max-retries 1
```

## 📋 Checklist for Production Deployment

- [ ] Test all stealth features with `test_enhanced_stealth.py`
- [ ] Verify proxy health and rotation
- [ ] Confirm detection avoidance measures
- [ ] Test delta scraping functionality
- [ ] Validate metrics and logging
- [ ] Review performance under load
- [ ] Monitor for detection events
- [ ] Verify graceful error handling

## 🎯 Summary

The enhanced stealth scraper provides:

1. **Comprehensive Anti-Detection**: Multi-layered protection against blocking
2. **Intelligent Resource Management**: Efficient proxy and session handling
3. **Robust Error Handling**: Graceful degradation and recovery
4. **Detailed Monitoring**: Complete metrics and logging
5. **Flexible Configuration**: Extensive customization options
6. **Production Ready**: Tested and optimized for reliability

This architecture ensures reliable, stealthy scraping while maintaining high performance and avoiding detection. 