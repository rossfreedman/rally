# ScraperAPI Setup Guide for US-Based IPs

## Problem
The tennis scores sites (nstf.tenniscores.com, etc.) require a US-based IP address to access their content. Currently, the scraper is getting a Bulgarian IP (216.128.6.125), which is being blocked.

## Solution
Use ScraperAPI to get US-based IP addresses for scraping.

## Step 1: Get ScraperAPI Account

1. **Sign up for ScraperAPI**:
   - Go to https://www.scraperapi.com/
   - Click "Start Free Trial"
   - Create an account (free tier available)

2. **Get your API key**:
   - Log into your ScraperAPI dashboard
   - Copy your API key from the dashboard
   - The key looks like: `abc123def456ghi789...`

## Step 2: Set Environment Variable

Set your ScraperAPI key as an environment variable:

```bash
export SCRAPERAPI_KEY=your_api_key_here
```

To make it permanent, add to your shell profile:
```bash
echo 'export SCRAPERAPI_KEY=your_api_key_here' >> ~/.zshrc
source ~/.zshrc
```

## Step 3: Test US-Based IP

Run the setup script to test and configure ScraperAPI:

```bash
python3 scripts/setup_scraperapi.py
```

This script will:
- ✅ Check if your API key is set
- 🌐 Test different US proxy endpoints
- 📍 Verify IP geolocation is US-based
- 🎾 Test access to tennis scores sites
- 🔧 Create configuration files

## Step 4: Test Selenium with Proxy

After successful setup, test Selenium with the US proxy:

```bash
python3 scripts/test_selenium_with_proxy.py
```

## Step 5: Run the Scraper

Once everything is working, run the scraper:

```bash
python3 data/etl/scrapers/master_scraper.py
```

## Troubleshooting

### Issue: "SCRAPERAPI_KEY not set"
**Solution**: Set your API key as shown in Step 2.

### Issue: "Non-US IP detected"
**Solution**: 
- Check your ScraperAPI plan - you need access to US-based proxies
- Try different US proxy endpoints (the script tests multiple)
- Contact ScraperAPI support if you have a paid plan

### Issue: "Tennis scores site not accessible"
**Solution**:
- The site might be temporarily down
- Try again later
- Check if the site has additional blocking measures

### Issue: "OpenSSL errors"
**Solution**: 
- The selenium-wire dependency has OpenSSL conflicts
- Use the direct Selenium approach with ScraperAPI proxy
- The setup script creates a working configuration

## Configuration Files

The setup script creates these files:

### `.env` file:
```env
# ScraperAPI Configuration
SCRAPERAPI_KEY=your_api_key_here
SCRAPERAPI_REGION=us-premium
REQUIRE_PROXY=true

# Scraper Configuration
HEADLESS_MODE=true
MAX_RETRIES=3
REQUEST_TIMEOUT=60
```

### Test scripts:
- `scripts/test_selenium_with_proxy.py` - Tests Selenium with US proxy
- `scripts/setup_scraperapi.py` - Setup and configuration script

## ScraperAPI Plans

### Free Tier:
- 1,000 requests/month
- Basic US proxies
- Good for testing

### Paid Plans:
- More requests
- Premium US proxies
- Better reliability
- Session management

## Alternative Solutions

If ScraperAPI doesn't work:

1. **VPN with US server**: Use a VPN service with US servers
2. **Other proxy services**: Try Bright Data, SmartProxy, etc.
3. **Cloud hosting**: Deploy scraper on US-based cloud server (AWS, GCP, etc.)

## Success Indicators

When working correctly, you should see:
- ✅ US-based IP confirmed
- ✅ Tennis scores site accessible
- ✅ Selenium navigation successful
- ✅ Page content loaded successfully

## Next Steps

After successful setup:
1. Test with a small scrape first
2. Monitor request usage in ScraperAPI dashboard
3. Set up monitoring for IP changes
4. Consider upgrading plan if needed for production use 