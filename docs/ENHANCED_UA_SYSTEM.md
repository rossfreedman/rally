# Enhanced User-Agent Management System

## Overview

The Enhanced User-Agent Management System provides config-driven, sustainable User-Agent rotation for Rally's scraping infrastructure. This system addresses the long-term sustainability of APTA's Windows User-Agent strategy while maintaining compatibility with other tennis sites.

## Key Features

### 1. Config-Driven UA Management
- **Configuration File**: `data/etl/scrapers/user_agents.json`
- **Two UA Pools**: 
  - `WINDOWS_APTA_POOL`: Windows Chrome User-Agents for APTA compatibility
  - `DEFAULT_POOL`: Standard User-Agents for other tennis sites
- **Runtime Loading**: UAs loaded into memory at startup
- **Hot Reload**: Configuration can be updated without code changes

### 2. Intelligent UA Rotation
- **Session-Based**: Same UA used for entire league scrape (30-minute sessions)
- **Force Rotation**: `force_new=True` parameter for retry scenarios
- **Health-Based Selection**: Only healthy UAs (>80% success rate) used
- **Automatic Retirement**: UAs retired after 3 consecutive failures

### 3. Detection-Based Switching
- **Block Detection**: If HTTP request fails, swap UA and retry
- **Granular Retry**: Individual page failures don't trigger full scrape retry
- **Metrics Tracking**: Success/failure rates tracked per UA
- **Adaptive Learning**: System learns which UAs work best for each site

### 4. OS Signal Leak Prevention
- **Windows Platform**: `--platform=Windows` for APTA browser mode
- **JavaScript Overrides**: `navigator.platform`, `navigator.userAgent` overrides
- **Consistent Fingerprinting**: All Windows signals match selected UA
- **No Linux/Mac Leaks**: Prevents cross-platform fingerprinting

### 5. Automatic UA Refresh
- **Monthly Updates**: `scripts/refresh_user_agents.py` for UA updates
- **Validation**: UA format validation before deployment
- **Version Tracking**: Metadata includes last update timestamp
- **Backward Compatibility**: Fallback to hardcoded UAs if config fails

## Architecture

### Core Components

#### 1. User-Agent Manager (`user_agent_manager.py`)
```python
class UserAgentManager:
    """Manages User-Agent pools with rotation and metrics tracking."""
    
    def get_user_agent_for_site(self, site_url: str, force_new: bool = False) -> str:
        """Get appropriate User-Agent for a specific site."""
    
    def report_success(self, user_agent: str, site_url: str = ""):
        """Report successful request for a User-Agent."""
    
    def report_failure(self, user_agent: str, site_url: str = ""):
        """Report failed request for a User-Agent."""
```

#### 2. Configuration File (`user_agents.json`)
```json
{
  "WINDOWS_APTA_POOL": [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    // ... 80+ Windows Chrome UAs
  ],
  "DEFAULT_POOL": [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    // ... mixed platform UAs
  ],
  "metadata": {
    "last_updated": "2025-01-27T10:30:00",
    "version": "1.0",
    "auto_refresh": true
  }
}
```

#### 3. Integration Points
- **Proxy Manager**: `make_proxy_request()` uses site-specific UAs
- **Stealth Browser**: Browser mode uses UA manager for OS consistency
- **Scrapers**: All scrapers automatically use appropriate UAs

## Usage

### Basic Usage

#### 1. Get User-Agent for Site
```python
from data.etl.scrapers.user_agent_manager import get_user_agent_for_site

# APTA gets Windows UA
ua = get_user_agent_for_site("https://apta.tenniscores.com")
# Returns: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."

# NSTF gets default UA
ua = get_user_agent_for_site("https://nstf.tenniscores.com")
# Returns: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36..."
```

#### 2. Report Success/Failure
```python
from data.etl.scrapers.user_agent_manager import report_ua_success, report_ua_failure

# Report success
report_ua_success(user_agent, "https://apta.tenniscores.com")

# Report failure
report_ua_failure(user_agent, "https://apta.tenniscores.com")
```

#### 3. Force New UA (for retries)
```python
# Force new UA for retry scenarios
ua = get_user_agent_for_site("https://apta.tenniscores.com", force_new=True)
```

### Advanced Usage

#### 1. Get Metrics Summary
```python
from data.etl.scrapers.user_agent_manager import get_user_agent_manager

manager = get_user_agent_manager()
metrics = manager.get_metrics_summary()

print(f"APTA Pool: {metrics['apta_pool']['healthy']}/{metrics['apta_pool']['total']} healthy")
print(f"Default Pool: {metrics['default_pool']['healthy']}/{metrics['default_pool']['total']} healthy")
```

#### 2. Refresh UA Configuration
```bash
# Run UA refresh script
python3 scripts/refresh_user_agents.py
```

#### 3. Test the System
```bash
# Run comprehensive tests
python3 scripts/test_enhanced_ua_system.py
```

## Configuration

### UA Pool Configuration

#### Windows APTA Pool
- **Purpose**: APTA compatibility (requires Windows Chrome UAs)
- **Format**: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36`
- **Versions**: Chrome 120-200 (80+ UAs)
- **Rotation**: Session-based (30 minutes) or force rotation

#### Default Pool
- **Purpose**: Other tennis sites (NSTF, CITA, etc.)
- **Format**: Mixed platforms (macOS, Linux, Windows)
- **Browsers**: Chrome, Safari, Firefox, Edge, Opera
- **Rotation**: Random selection from healthy pool

### Health Metrics

#### UA Health Criteria
- **Success Rate**: >80% over minimum 10 requests
- **Consecutive Failures**: <3 failures
- **Not Retired**: UA not manually retired
- **Recent Activity**: Used within last 24 hours

#### Automatic Actions
- **Promotion**: UA moved to trusted pool if >90% success rate
- **Demotion**: UA moved to rotating pool if <70% success rate
- **Retirement**: UA retired if 3+ consecutive failures
- **Reset**: All UAs reset if no healthy UAs available

## Integration

### Proxy Manager Integration

The proxy manager automatically uses site-specific UAs:

```python
# In make_proxy_request()
user_agent = get_user_agent_for_site(url, force_new=(attempt > 0))
headers = get_random_headers(url)

response = requests.get(url, proxies=proxies, headers=headers)
```

### Stealth Browser Integration

The stealth browser uses UA manager for OS consistency:

```python
# In _create_driver()
if "apta.tenniscores.com" in self.current_url:
    options.add_argument("--platform=Windows")
    user_agent = get_user_agent_for_site(self.current_url)
else:
    user_agent = UserAgentManager.get_random_user_agent()
```

### Scraper Integration

All scrapers automatically benefit from UA management:

```python
# No changes needed in scrapers
# UA management is transparent
html = browser.get_html("https://apta.tenniscores.com")
```

## Monitoring and Metrics

### Metrics Tracking

#### Per-UA Metrics
- **Success Count**: Number of successful requests
- **Failure Count**: Number of failed requests
- **Total Requests**: Total requests made
- **Success Rate**: Percentage of successful requests
- **Last Used**: Timestamp of last usage
- **Last Success**: Timestamp of last success
- **Consecutive Failures**: Current failure streak

#### Session Metrics
- **Current APTA UA**: UA being used for current APTA session
- **Session Start**: When current session started
- **Pool Health**: Number of healthy UAs in each pool
- **Retirement Count**: Number of retired UAs

### Logging

#### Success Logs
```
✅ APTA UA success: Mozilla/5.0 (Windows NT 10.0; Win64; x64)... (rate: 95.2%)
✅ UA success: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)... (rate: 88.7%)
```

#### Failure Logs
```
❌ APTA UA failure: Mozilla/5.0 (Windows NT 10.0; Win64; x64)... (consecutive: 2)
🚫 Retired UA after 3 consecutive failures: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...
```

#### Session Logs
```
🔄 APTA session started with UA: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...
🔄 Reset APTA UA metrics
```

## Maintenance

### UA Refresh Process

#### Monthly Refresh
1. **Run Refresh Script**: `python3 scripts/refresh_user_agents.py`
2. **Validate UAs**: Script validates UA format
3. **Update Config**: New UAs written to `user_agents.json`
4. **Test System**: Run test suite to verify changes

#### Manual Refresh
```bash
# Force refresh
python3 scripts/refresh_user_agents.py

# Verify changes
python3 scripts/test_enhanced_ua_system.py
```

### Health Monitoring

#### Daily Checks
- **Pool Health**: Monitor healthy UA counts
- **Success Rates**: Track UA performance
- **Retirement Alerts**: Monitor UA retirement events

#### Weekly Analysis
- **Performance Review**: Analyze UA success rates
- **Pool Optimization**: Adjust UA pools based on performance
- **Configuration Updates**: Update UA refresh sources

### Troubleshooting

#### Common Issues

1. **No Healthy UAs Available**
   ```
   ⚠️ No healthy APTA UAs, resetting all
   🔄 Reset APTA UA metrics
   ```

2. **Config File Missing**
   ```
   ⚠️ Config file not found: data/etl/scrapers/user_agents.json
   ✅ Loaded fallback UA configuration
   ```

3. **UA Manager Import Error**
   ```
   ⚠️ UA manager failed, using fallback: ModuleNotFoundError
   ```

#### Solutions

1. **Reset UA Metrics**: All UAs will be reset to healthy state
2. **Check Config File**: Ensure `user_agents.json` exists and is valid
3. **Verify Dependencies**: Ensure all imports are working correctly

## Performance

### Expected Performance

#### APTA Compatibility
- **Success Rate**: 90%+ with Windows UAs
- **Response Size**: 36K+ characters
- **Response Time**: 2-3 seconds
- **UA Rotation**: Every 30 minutes or on failure

#### Other Sites
- **Success Rate**: 100% with default UAs
- **Response Size**: 55K-91K characters
- **Response Time**: 2-3 seconds
- **UA Rotation**: Random selection from healthy pool

### Optimization

#### UA Pool Management
- **Trusted Pool**: High-performing UAs used first
- **Rotating Pool**: Backup UAs for fallback
- **Automatic Promotion**: UAs promoted based on performance
- **Automatic Demotion**: UAs demoted based on failures

#### Session Management
- **Sticky Sessions**: Same UA for entire league scrape
- **Consistent Identity**: Maintains consistent fingerprint
- **Reduced Overhead**: Less UA switching
- **Better Success**: Consistent identity improves success rates

## Security

### Privacy Protection

#### UA Fingerprinting
- **Consistent Signals**: All browser signals match selected UA
- **No Cross-Platform Leaks**: Prevents fingerprinting inconsistencies
- **OS-Specific Overrides**: JavaScript overrides for platform consistency

#### Proxy Integration
- **UA + Proxy Matching**: UA selection considers proxy health
- **Failure Correlation**: UA failures correlated with proxy failures
- **Adaptive Selection**: UA selection adapts to proxy performance

### Anti-Detection

#### Detection Avoidance
- **Realistic UAs**: Modern, realistic User-Agent strings
- **Consistent Behavior**: Same UA used throughout session
- **Failure Recovery**: Automatic UA rotation on detection
- **Metrics Learning**: System learns from detection patterns

#### CAPTCHA Bypass
- **Windows UAs**: APTA requires Windows Chrome UAs
- **Session Consistency**: Same UA maintains session identity
- **Failure Retry**: New UA on CAPTCHA detection
- **Success Tracking**: Tracks which UAs bypass CAPTCHA

## Future Enhancements

### Planned Improvements

1. **Machine Learning UA Selection**
   - Predict optimal UAs based on site patterns
   - Learn from historical success/failure data
   - Adaptive UA selection algorithms

2. **Dynamic UA Generation**
   - Generate UAs based on current browser versions
   - Real-time UA freshness checking
   - Automatic UA validation

3. **Enhanced Metrics**
   - Per-site UA performance tracking
   - Geographic UA optimization
   - Time-based UA selection patterns

4. **Advanced Detection Avoidance**
   - Behavioral UA patterns
   - Request timing optimization
   - Advanced fingerprinting prevention

### Extensibility

#### Adding New Sites
```python
# Add site-specific UA logic
def get_user_agent_for_site(url: str, force_new: bool = False) -> str:
    if "new-site.com" in url:
        return get_special_ua_for_new_site()
    elif "apta.tenniscores.com" in url:
        return get_apta_ua(force_new)
    else:
        return get_default_ua()
```

#### Adding New UA Sources
```python
# Add new UA source
def fetch_user_agents_from_source():
    sources = [
        "https://existing-source.com",
        "https://new-source.com",  # Add new source
        "https://another-source.com"
    ]
```

## Conclusion

The Enhanced User-Agent Management System provides a sustainable, config-driven solution for APTA's Windows User-Agent requirements while maintaining compatibility with other tennis sites. The system's intelligent rotation, health monitoring, and OS signal leak prevention ensure long-term reliability and effectiveness.

Key benefits:
- **Sustainability**: Config-driven updates without code changes
- **Intelligence**: Health-based UA selection and automatic retirement
- **Compatibility**: Works with existing proxy and browser systems
- **Monitoring**: Comprehensive metrics and logging
- **Security**: OS signal leak prevention and detection avoidance

The system is production-ready and provides a robust foundation for Rally's scraping infrastructure. 