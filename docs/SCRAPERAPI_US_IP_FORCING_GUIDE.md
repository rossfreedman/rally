# ScraperAPI US IP Forcing Guide

## Overview
This guide covers how to force US-based IP addresses using ScraperAPI for accessing tennis scores sites that require US-based IPs.

## ScraperAPI US IP Methods

### 1. HTTP API Method (Recommended)

The HTTP API method is the most reliable way to force US-based IPs:

```bash
# Basic US IP
http://api.scraperapi.com?api_key=YOUR_API_KEY&url=TARGET_URL&country_code=us

# US with premium proxies
http://api.scraperapi.com?api_key=YOUR_API_KEY&url=TARGET_URL&country_code=us&premium=true

# US with session management
http://api.scraperapi.com?api_key=YOUR_API_KEY&url=TARGET_URL&country_code=us&session_number=1

# US with keep-alive
http://api.scraperapi.com?api_key=YOUR_API_KEY&url=TARGET_URL&country_code=us&keep_alive=true
```

### 2. Proxy Endpoint Method

For Selenium/Chrome automation, use proxy endpoints:

```bash
# Standard US proxy
http://scraperapi-country-us:YOUR_API_KEY@proxy-server.scraperapi.com:8001

# Premium US proxy
http://scraperapi-premium-country-us:YOUR_API_KEY@proxy-server.scraperapi.com:8001

# US East region
http://scraperapi-country-us-east:YOUR_API_KEY@proxy-server.scraperapi.com:8001

# US West region
http://scraperapi-country-us-west:YOUR_API_KEY@proxy-server.scraperapi.com:8001

# US Central region
http://scraperapi-country-us-central:YOUR_API_KEY@proxy-server.scraperapi.com:8001
```

## Key Parameters for US IP Forcing

### HTTP API Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `country_code` | `us` | Forces US-based IP |
| `region` | `us` | Specifies US region |
| `premium` | `true` | Uses premium US proxies |
| `session_number` | `1-10` | Maintains session for consistency |
| `keep_alive` | `true` | Keeps connection alive |
| `residential` | `true` | Uses residential US proxies |
| `datacenter` | `true` | Uses datacenter US proxies |

### Proxy Endpoint Options

| Endpoint | Description | Reliability |
|----------|-------------|-------------|
| `scraperapi-country-us` | Standard US proxy | Good |
| `scraperapi-premium-country-us` | Premium US proxy | Excellent |
| `scraperapi-country-us-east` | US East region | Good |
| `scraperapi-country-us-west` | US West region | Good |
| `scraperapi-country-us-central` | US Central region | Good |
| `scraperapi-country-us-session` | US with session | Excellent |
| `scraperapi-country-us-keep-alive` | US with keep-alive | Excellent |

## Implementation Examples

### Python Requests Example

```python
import requests

api_key = "your_api_key_here"
target_url = "https://nstf.tenniscores.com"

# Method 1: HTTP API
api_url = f"http://api.scraperapi.com?api_key={api_key}&url={target_url}&country_code=us&premium=true"
response = requests.get(api_url)

# Method 2: Proxy
proxy_url = f"http://scraperapi-premium-country-us:{api_key}@proxy-server.scraperapi.com:8001"
proxies = {'http': proxy_url, 'https': proxy_url}
response = requests.get(target_url, proxies=proxies)
```

### Selenium Example

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Configure proxy
proxy_url = f"http://scraperapi-premium-country-us:{api_key}@proxy-server.scraperapi.com:8001"

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')

# Create driver with proxy
driver = webdriver.Chrome(options=options)
driver.get("https://nstf.tenniscores.com")
```

## Testing US IP Configuration

### 1. IP Verification

```python
import requests
import json

def verify_us_ip(api_key):
    # Test IP with ScraperAPI
    test_url = f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&premium=true"
    response = requests.get(test_url)
    
    if response.status_code == 200:
        ip_data = json.loads(response.text)
        ip_address = ip_data.get('origin')
        
        # Verify IP location
        geo_response = requests.get(f"https://ipapi.co/{ip_address}/json/")
        geo_data = geo_response.json()
        
        is_us = geo_data.get('country_code') == 'US'
        print(f"IP: {ip_address}")
        print(f"Location: {geo_data.get('city')}, {geo_data.get('region')}, {geo_data.get('country_name')}")
        print(f"US-based: {is_us}")
        
        return is_us
    return False
```

### 2. Tennis Site Access Test

```python
def test_tennis_access(api_key):
    tennis_url = "https://nstf.tenniscores.com"
    
    # Test with HTTP API
    api_url = f"http://api.scraperapi.com?api_key={api_key}&url={tennis_url}&country_code=us&premium=true"
    response = requests.get(api_url)
    
    if response.status_code == 200:
        content = response.text.lower()
        has_tennis_content = any(keyword in content for keyword in ['tennis', 'scores', 'matches'])
        print(f"Access successful: {has_tennis_content}")
        return has_tennis_content
    return False
```

## Best Practices

### 1. Use Premium Proxies
Premium proxies provide better reliability and US IP consistency:
```bash
# Always use premium for US IPs
&premium=true
```

### 2. Session Management
Use session management for consistent IPs:
```bash
# Maintain session for consistency
&session_number=1
```

### 3. Keep-Alive Connections
Use keep-alive for persistent connections:
```bash
# Keep connection alive
&keep_alive=true
```

### 4. Retry Logic
Implement retry logic for failed requests:
```bash
# Add retry parameters
&retry=3&timeout=60
```

## Troubleshooting

### Issue: Non-US IP Detected
**Solutions:**
1. Use premium proxies: `&premium=true`
2. Add session management: `&session_number=1`
3. Try different regions: `&region=us`
4. Contact ScraperAPI support

### Issue: Tennis Site Still Blocked
**Solutions:**
1. Verify US IP is working
2. Try residential proxies: `&residential=true`
3. Use session management for consistency
4. Check site's specific blocking rules

### Issue: Proxy Connection Failed
**Solutions:**
1. Check API key validity
2. Verify account has US proxy access
3. Try different proxy endpoints
4. Check network connectivity

## Configuration Files

### Environment Variables
```bash
export SCRAPERAPI_KEY=your_api_key_here
export SCRAPERAPI_REGION=us-premium
export REQUIRE_PROXY=true
export SCRAPERAPI_USE_PREMIUM=true
export SCRAPERAPI_USE_SESSION=true
```

### Python Configuration
```python
import os

# ScraperAPI Configuration
os.environ["SCRAPERAPI_KEY"] = "your_api_key_here"
os.environ["SCRAPERAPI_REGION"] = "us-premium"
os.environ["REQUIRE_PROXY"] = "true"
os.environ["SCRAPERAPI_USE_PREMIUM"] = "true"
os.environ["SCRAPERAPI_USE_SESSION"] = "true"
```

## Research Script

Use the research script to test all configurations:
```bash
export SCRAPERAPI_KEY=your_api_key_here
python3 scripts/research_scraperapi_us_ip.py
```

This script will:
- Test all HTTP API configurations
- Test all proxy endpoints
- Verify US IP geolocation
- Test tennis site access
- Generate optimal configuration

## Success Indicators

When working correctly, you should see:
- ✅ IP geolocation shows US location
- ✅ Tennis site access successful
- ✅ Content contains tennis-related keywords
- ✅ Consistent US IP across requests

## Next Steps

1. **Get ScraperAPI account** with US proxy access
2. **Set API key** as environment variable
3. **Run research script** to find optimal configuration
4. **Test tennis site access** with US IP
5. **Implement in scraper** with optimal settings 