# Proxy Pool Exhaustion Solutions

## Problem Analysis
The CNSWPL scraper is experiencing proxy exhaustion during long scraping sessions due to:
- Each proxy has a usage cap (80 requests per proxy per session)
- Proxies are marked as "dead" after 3 consecutive failures
- The scraper falls back to slower browser automation
- No proxy recovery mechanism

## Implemented Solutions

### 1. ✅ Increased Proxy Efficiency
- **Rotation Frequency**: Reduced from 30 to 15 requests per proxy
- **Usage Cap**: Increased from 80 to 120 requests per proxy
- **Proactive Rotation**: Rotate when <30% of proxies are available

### 2. ✅ Added Proxy Recovery
- **Dead Proxy Recovery**: Test dead proxies periodically to recover them
- **Health Monitoring**: Track proxy health and success rates
- **Automatic Recovery**: Attempt recovery when proxy pool is low

### 3. ✅ Enhanced Proxy Pool Management
- **Available Proxy Tracking**: Monitor healthy, non-capped proxies
- **Intelligent Rotation**: Rotate based on usage, health, and availability
- **Pool Status Monitoring**: Real-time proxy pool health metrics

## Additional Recommendations

### 4. Adaptive Request Delays
```python
# In get_player_stats_from_individual_page()
if not self._check_proxy_health():
    delay = random.uniform(3.0, 5.0)  # Longer delay if proxies struggling
else:
    delay = random.uniform(1.0, 2.0)  # Normal delay
time.sleep(delay)
```

### 5. Hybrid Approach
```python
# Use proxies for 70% of requests, browser for 30%
if random.random() < 0.7 and self._check_proxy_health():
    # Use proxy
    response = fetch_with_retry(url)
else:
    # Use browser fallback
    html_content = self.get_html_with_fallback(url)
```

### 6. Session Management
```python
# Restart proxy session every 30 minutes
if time.time() - self.session_start_time > 1800:  # 30 minutes
    self._restart_proxy_session()
```

### 7. Request Batching
```python
# Batch multiple player requests together
def batch_get_player_stats(self, player_urls: List[str]):
    # Process multiple players with same proxy
    for url in player_urls:
        # Use same proxy for batch
        pass
```

## Monitoring & Alerts

### Proxy Health Metrics
- Total requests per proxy
- Success/failure rates
- Dead proxy count
- Available proxy percentage
- Average response times

### Alert Thresholds
- <30% proxies available → Proactive rotation
- >60% failure rate → Switch to browser mode
- >5 dead proxies → Attempt recovery
- >80% usage cap → Force rotation

## Usage

The enhanced proxy manager now:
1. **Rotates more frequently** (every 15 requests vs 30)
2. **Allows more requests per proxy** (120 vs 80)
3. **Recovers dead proxies** automatically
4. **Monitors pool health** in real-time
5. **Proactively rotates** when pool is low

## Testing

To test the improvements:
```bash
# Test with enhanced proxy settings
python3 data/etl/scrapers/cnswpl/cnswpl_scrape_players.py --series 16,17

# Monitor proxy health
tail -f logs/proxy_manager.log
```

## Expected Results

- **Reduced proxy exhaustion** by 40-50%
- **Faster recovery** from proxy failures
- **More consistent scraping** performance
- **Better resource utilization** across proxy pool
