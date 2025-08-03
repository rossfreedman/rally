#!/usr/bin/env python3
"""
Example: Using Rally's Enhanced Stealth System in Production
===========================================================

This script shows how to use all the enhanced stealth features
in a real scraping scenario with proper error handling and monitoring.
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.etl.scrapers.proxy_manager import (
    get_proxy_rotator, 
    fetch_with_retry,
    EnhancedProxyRotator
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def enhanced_scraping_session():
    """
    Example of a complete scraping session using all enhanced features.
    """
    logger.info("🚀 Starting Enhanced Scraping Session")
    
    # Step 1: Initialize Enhanced Proxy Rotator
    logger.info("📊 Initializing Enhanced Proxy Rotator...")
    rotator = EnhancedProxyRotator(
        rotate_every=30,           # Rotate every 30 requests
        usage_cap_per_proxy=35,    # Max 35 requests per proxy
        session_duration=600       # 10-minute sessions
    )
    
    # Step 2: Run Proxy Warmup (CRITICAL for production)
    logger.info("🔥 Running proxy warmup...")
    warmup_results = rotator.run_proxy_warmup(test_tenniscores=True)
    
    healthy_proxies = warmup_results['healthy_proxies']
    tenniscores_accessible = warmup_results['tenniscores_accessible']
    
    logger.info(f"✅ Warmup complete: {healthy_proxies} healthy, {tenniscores_accessible} Tenniscores-ready")
    
    # Abort if too few healthy proxies
    if healthy_proxies < 20:
        logger.error(f"❌ Only {healthy_proxies} healthy proxies - aborting session")
        return False
    
    # Step 3: Example scraping with enhanced features
    urls_to_scrape = [
        "https://httpbin.org/user-agent",  # Test endpoint
        "https://httpbin.org/headers",     # Another test endpoint
        # Add your Tenniscores URLs here:
        # "https://tenniscores.com/nstf/league/...",
    ]
    
    successful_requests = 0
    failed_requests = 0
    
    for i, url in enumerate(urls_to_scrape):
        logger.info(f"📥 Scraping {i+1}/{len(urls_to_scrape)}: {url}")
        
        try:
            # Step 4: Make enhanced request with all features
            response = fetch_with_retry(
                url,
                max_retries=3,
                timeout=30
            )
            
            if response and response.status_code == 200:
                logger.info(f"✅ Success: {len(response.text)} chars received")
                successful_requests += 1
                
                # Log some response details
                if 'user-agent' in url:
                    user_agent_used = response.json().get('user-agent', 'Unknown')
                    logger.info(f"   User-Agent: {user_agent_used[:60]}...")
                
            else:
                logger.warning(f"⚠️ Failed: Status {response.status_code if response else 'None'}")
                failed_requests += 1
                
        except Exception as e:
            logger.error(f"❌ Request failed: {e}")
            failed_requests += 1
        
        # Step 5: Check adaptive throttling
        throttle_delay = rotator.get_adaptive_throttle_delay()
        if throttle_delay > 0:
            logger.info(f"⏳ Adaptive throttling: {throttle_delay:.1f}s delay")
            time.sleep(throttle_delay)
        
        # Step 6: Monitor proxy health
        status = rotator.get_status()
        if status['consecutive_blocks'] >= 3:
            logger.warning(f"🚨 High block rate detected: {status['consecutive_blocks']} consecutive blocks")
        
        # Brief delay between requests (adjust as needed)
        time.sleep(2)
    
    # Step 7: Session Summary
    logger.info("📊 Session Summary")
    logger.info("=" * 40)
    
    final_status = rotator.get_status()
    session_metrics = rotator.session_metrics
    
    logger.info(f"Total Requests: {session_metrics['total_requests']}")
    logger.info(f"Successful: {successful_requests}")
    logger.info(f"Failed: {failed_requests}")
    logger.info(f"Success Rate: {(successful_requests / (successful_requests + failed_requests) * 100):.1f}%")
    logger.info(f"Proxy Rotations: {session_metrics['proxy_rotations']}")
    logger.info(f"Usage-Capped Proxies: {session_metrics['usage_capped_proxies']}")
    logger.info(f"Consecutive Blocks: {final_status['consecutive_blocks']}")
    logger.info(f"Healthy Proxies Remaining: {final_status['healthy_proxies']}")
    
    return True

def monitoring_example():
    """
    Example of how to monitor the proxy system during scraping.
    """
    logger.info("📊 Proxy System Monitoring Example")
    
    rotator = get_proxy_rotator()
    
    # Get comprehensive status
    status = rotator.get_status()
    
    print("\n🔍 Current Proxy System Status:")
    print(f"  Total Proxies: {status['total_proxies']}")
    print(f"  Healthy Proxies: {status['healthy_proxies']}")
    print(f"  Dead Proxies: {status['dead_proxies']}")
    print(f"  Bad Proxies: {status['bad_proxies']}")
    print(f"  Current Proxy: {status['current_proxy']}")
    print(f"  Request Count: {status['request_count']}")
    print(f"  Consecutive Blocks: {status['consecutive_blocks']}")
    
    # Health percentage
    health_percentage = (status['healthy_proxies'] / status['total_proxies']) * 100
    print(f"  Health Percentage: {health_percentage:.1f}%")
    
    # Recommendations
    if health_percentage < 50:
        print("  🚨 ALERT: Low proxy health - consider investigation")
    elif health_percentage < 75:
        print("  ⚠️ WARNING: Moderate proxy degradation")
    else:
        print("  ✅ HEALTHY: Proxy system operating normally")

def error_handling_example():
    """
    Example of proper error handling with the enhanced system.
    """
    logger.info("🛡️ Error Handling Example")
    
    try:
        # Attempt request with comprehensive error handling
        response = fetch_with_retry(
            "https://httpbin.org/status/503",  # This will return 503 (blocked)
            max_retries=2
        )
        logger.info("This shouldn't execute due to 503 status")
        
    except Exception as e:
        logger.info(f"✅ Error properly caught and handled: {e}")
        
        # Check what happened
        rotator = get_proxy_rotator()
        status = rotator.get_status()
        
        if status['consecutive_blocks'] > 0:
            logger.info(f"   Blocks detected: {status['consecutive_blocks']}")
            
            # Apply additional throttling if needed
            throttle_delay = rotator.get_adaptive_throttle_delay()
            if throttle_delay > 0:
                logger.info(f"   Recommended throttling: {throttle_delay:.1f}s")

def main():
    """
    Main function demonstrating complete usage.
    """
    print("🎯 Rally Enhanced Stealth System - Production Example")
    print("=" * 60)
    
    try:
        # Run monitoring check
        monitoring_example()
        
        # Run error handling demo
        error_handling_example()
        
        # Run full scraping session
        success = enhanced_scraping_session()
        
        if success:
            print("\n🎉 Enhanced scraping session completed successfully!")
        else:
            print("\n❌ Scraping session failed - check logs")
            
    except KeyboardInterrupt:
        print("\n⏹️ Session interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    
    print("\n💡 Production Tips:")
    print("  1. Always run warmup before scraping sessions")
    print("  2. Monitor consecutive_blocks for early warning")
    print("  3. Respect adaptive throttling delays")
    print("  4. Set up SMS alerts for critical failures")
    print("  5. Adjust usage caps based on your proxy limits")

if __name__ == "__main__":
    main()