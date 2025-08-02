#!/usr/bin/env python3
"""
Enhanced Proxy Manager for Rally Tennis Scraper
===============================================

Uses Decodo residential proxies with intelligent rotation, robust failure detection,
and comprehensive metrics tracking.

NEW FEATURES:
✅ Robust proxy block detection (is_blocked function)
✅ Enhanced retry logic with automatic proxy rotation (fetch_with_retry)
✅ Proxy health tracking with bad_proxies set
✅ URGENT SMS alerts for multiple proxy failures
✅ Comprehensive blocking pattern detection

USAGE:
    # Basic usage with automatic retry and block detection
    from data.etl.scrapers.proxy_manager import fetch_with_retry
    
    try:
        response = fetch_with_retry('https://example.com')
        print(f'Success: {response.status_code}')
    except Exception as e:
        print(f'All proxies failed: {e}')

SMS ALERTS:
    Set these environment variables for SMS notifications:
    - TWILIO_ACCOUNT_SID
    - TWILIO_AUTH_TOKEN
    - TWILIO_SENDER_PHONE
    
    Alerts are sent when:
    - 3+ consecutive proxy blocks across different IPs
    - >50% of proxies are unhealthy
    - >70% of proxies are marked as bad

BLOCKING DETECTION:
    Automatically detects:
    - Status codes: 403, 429, 503
    - Short responses (< 100 chars)
    - Blocking text patterns (captcha, access denied, etc.)
    - Redirects to blocking pages
"""

import os
import random
import time
import logging
import requests
from typing import Dict, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMS Configuration
ADMIN_PHONE = "17732138911"

def send_urgent_sms(message: str) -> bool:
    """Send urgent SMS alert using Twilio."""
    try:
        import requests
        from urllib.parse import urlencode
        
        # Get Twilio credentials from environment
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_SENDER_PHONE")
        to_number = ADMIN_PHONE
        
        if not all([account_sid, auth_token, from_number]):
            logger.warning("⚠️ Twilio credentials not configured - cannot send SMS alert")
            return False
        
        # Send via Twilio API
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        auth = (account_sid, auth_token)
        data = {
            "To": to_number,
            "From": from_number,
            "Body": message
        }
        
        response = requests.post(url, auth=auth, data=data, timeout=30)
        
        if response.status_code == 201:
            logger.info(f"🚨 URGENT SMS sent: {message[:50]}...")
            return True
        else:
            logger.error(f"❌ Failed to send SMS: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending SMS: {e}")
        return False

def is_blocked(response: requests.Response) -> bool:
    """
    Detect if response indicates proxy blocking or bot detection.
    
    Args:
        response: requests.Response object to analyze
        
    Returns:
        bool: True if response indicates blocking/detection
    """
    try:
        # Check status codes
        if response.status_code in [403, 429, 503]:
            logger.warning(f"🚫 Blocked status code: {response.status_code}")
            return True
        
        # Check response body length (suspiciously short responses)
        content = response.text.lower() if response.text else ""
        if len(content) < 100:
            logger.warning(f"🚫 Suspiciously short response: {len(content)} chars")
            return True
        
        # Check for known blocking text patterns
        blocking_patterns = [
            "access denied",
            "verify you are human", 
            "bot detected",
            "please complete the security check",
            "cloudflare",
            "attention required",
            "checking your browser",
            "ddos protection",
            "security challenge",
            "suspicious activity",
            "blocked for security",
            "captcha",
            "recaptcha"
        ]
        
        for pattern in blocking_patterns:
            if pattern in content:
                logger.warning(f"🚫 Blocking pattern detected: '{pattern}'")
                return True
        
        # Check for redirect to blocking page
        if response.history and len(response.history) > 0:
            final_url = response.url.lower()
            if any(keyword in final_url for keyword in ["block", "deny", "captcha", "security"]):
                logger.warning(f"🚫 Redirected to blocking page: {response.url}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking if blocked: {e}")
        return False  # Assume not blocked if we can't determine

class ProxyStatus(Enum):
    """Proxy status enumeration."""
    ACTIVE = "active"
    DEAD = "dead"
    BANNED = "banned"
    TESTING = "testing"

@dataclass
class ProxyInfo:
    """Information about a single proxy."""
    port: int
    host: str = "us.decodo.com"
    status: ProxyStatus = ProxyStatus.ACTIVE
    last_used: Optional[datetime] = None
    last_tested: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    total_requests: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.success_count / self.total_requests) * 100
    
    @property
    def is_healthy(self) -> bool:
        """Check if proxy is healthy."""
        return (self.status == ProxyStatus.ACTIVE and 
                self.consecutive_failures < 3 and 
                self.success_rate > 50)

class EnhancedProxyRotator:
    """
    Enhanced proxy rotator with dead proxy detection and intelligent rotation.
    
    Features:
    - Dead proxy detection and blacklisting
    - Success rate tracking
    - Intelligent rotation based on health
    - Automatic testing of proxies
    - Comprehensive metrics
    """
    
    def __init__(self, 
                 ports: List[int] = None,
                 rotate_every: int = 30,
                 session_duration: int = 600,
                 test_url: str = "https://httpbin.org/ip"):
        """
        Initialize enhanced proxy rotator.
        
        Args:
            ports: List of available ports
            rotate_every: Rotate IP after this many requests
            session_duration: Session duration in seconds
            test_url: URL to test proxy health
        """
        self.ports = ports or self._load_default_ports()
        self.rotate_every = rotate_every
        self.session_duration = session_duration
        self.test_url = test_url
        
        # Initialize proxy info
        self.proxies: Dict[int, ProxyInfo] = {}
        for port in self.ports:
            self.proxies[port] = ProxyInfo(port=port)
        
        # Session tracking
        self.request_count = 0
        self.current_port = random.choice(self.ports)
        self.session_start_time = time.time()
        self.total_rotations = 0
        self.total_requests = 0
        self.dead_proxies: Set[int] = set()
        
        # Enhanced proxy health tracking
        self.bad_proxies: Set[int] = set()
        self.proxy_health: Dict[int, Dict[str, int]] = {}
        self.consecutive_blocks = 0
        self.last_sms_alert = None
        self.session_blocked_proxies = 0
        
        # Metrics
        self.session_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "proxy_rotations": 0,
            "dead_proxies_detected": 0
        }
        
        logger.info(f"🔄 Enhanced Proxy Rotator initialized")
        logger.info(f"📊 Total proxies: {len(self.ports)}")
        logger.info(f"🔄 Rotation: Every {rotate_every} requests")
        logger.info(f"⏱️ Session duration: {session_duration} seconds")
        
        # Test all proxies initially
        self._test_all_proxies()
    
    def _load_default_ports(self) -> List[int]:
        """Load default ports from ips.txt or use fallback."""
        try:
            if os.path.exists("ips.txt"):
                with open("ips.txt", "r") as f:
                    lines = f.readlines()
                
                ports = []
                for line in lines:
                    line = line.strip()
                    if line and ":" in line:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            port = int(parts[1])
                            ports.append(port)
                
                if ports:
                    logger.info(f"📊 Loaded {len(ports)} ports from ips.txt")
                    return ports
        except Exception as e:
            logger.error(f"❌ Error loading ips.txt: {e}")
        
        # Fallback to default range
        return list(range(10001, 10101))  # 100 ports
    
    def _test_proxy(self, proxy_info: ProxyInfo) -> bool:
        """Test if a proxy is working."""
        try:
            proxy_url = f"http://{proxy_info.host}:{proxy_info.port}"
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            response = requests.get(
                self.test_url,
                proxies=proxies,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            
            if response.status_code == 200:
                proxy_info.status = ProxyStatus.ACTIVE
                proxy_info.success_count += 1
                proxy_info.consecutive_failures = 0
                return True
            else:
                proxy_info.failure_count += 1
                proxy_info.consecutive_failures += 1
                return False
                
        except Exception as e:
            proxy_info.failure_count += 1
            proxy_info.consecutive_failures += 1
            logger.debug(f"❌ Proxy {proxy_info.port} failed: {e}")
            return False
        finally:
            proxy_info.last_tested = datetime.now()
            proxy_info.total_requests += 1
    
    def _test_all_proxies(self):
        """Test all proxies to determine health."""
        logger.info("🧪 Testing all proxies...")
        
        healthy_count = 0
        for port, proxy_info in self.proxies.items():
            if self._test_proxy(proxy_info):
                healthy_count += 1
            else:
                if proxy_info.consecutive_failures >= 3:
                    proxy_info.status = ProxyStatus.DEAD
                    self.dead_proxies.add(port)
        
        logger.info(f"✅ Proxy testing complete: {healthy_count}/{len(self.proxies)} healthy")
    
    def _get_healthy_proxies(self) -> List[int]:
        """Get list of healthy proxy ports."""
        return [port for port, info in self.proxies.items() 
                if info.is_healthy and port not in self.dead_proxies]
    
    def _should_rotate(self) -> bool:
        """Determine if we should rotate to a new proxy."""
        # Rotate based on request count
        if self.request_count % self.rotate_every == 0:
            return True
        
        # Rotate if current proxy is unhealthy
        current_info = self.proxies.get(self.current_port)
        if current_info and not current_info.is_healthy:
            return True
        
        # Rotate if session is too old
        if time.time() - self.session_start_time > self.session_duration:
            return True
        
        return False
    
    def _rotate_proxy(self):
        """Rotate to a new healthy proxy."""
        old_port = self.current_port
        
        # Get healthy proxies
        healthy_proxies = self._get_healthy_proxies()
        
        if not healthy_proxies:
            logger.warning("⚠️ No healthy proxies available, testing all proxies...")
            self._test_all_proxies()
            healthy_proxies = self._get_healthy_proxies()
        
        if healthy_proxies:
            # Choose proxy with best success rate
            best_proxy = max(healthy_proxies, 
                           key=lambda p: self.proxies[p].success_rate)
            self.current_port = best_proxy
        else:
            # Fallback to random proxy
            self.current_port = random.choice(self.ports)
        
        # Update session
        self.session_start_time = time.time()
        self.total_rotations += 1
        self.session_metrics["proxy_rotations"] += 1
        
        # Update proxy info
        if self.current_port in self.proxies:
            self.proxies[self.current_port].last_used = datetime.now()
        
        logger.info(f"🔄 Rotating proxy: {old_port} → {self.current_port}")
    
    def get_proxy(self) -> str:
        """Get current proxy URL."""
        if self._should_rotate():
            self._rotate_proxy()
        
        # Update request count
        self.request_count += 1
        self.total_requests += 1
        self.session_metrics["total_requests"] += 1
        
        # Update current proxy info
        if self.current_port in self.proxies:
            self.proxies[self.current_port].last_used = datetime.now()
        
        return f"http://us.decodo.com:{self.current_port}"
    
    def report_success(self, port: int = None):
        """Report successful request for proxy."""
        port = port or self.current_port
        if port in self.proxies:
            self.proxies[port].success_count += 1
            self.proxies[port].consecutive_failures = 0
            self.session_metrics["successful_requests"] += 1
            
            # Update proxy health tracking
            if port not in self.proxy_health:
                self.proxy_health[port] = {"success": 0, "blocked": 0, "failures": 0}
            
            self.proxy_health[port]["success"] += 1
            
            # Reset consecutive blocks on successful request
            self.reset_consecutive_blocks()
    
    def report_failure(self, port: int = None):
        """Report failed request for proxy."""
        port = port or self.current_port
        if port in self.proxies:
            self.proxies[port].failure_count += 1
            self.proxies[port].consecutive_failures += 1
            
            # Mark as dead if too many consecutive failures
            if self.proxies[port].consecutive_failures >= 3:
                self.proxies[port].status = ProxyStatus.DEAD
                self.dead_proxies.add(port)
                self.session_metrics["dead_proxies_detected"] += 1
                logger.warning(f"💀 Marking proxy {port} as dead")
            
            self.session_metrics["failed_requests"] += 1
    
    def report_blocked(self, port: int = None):
        """Report blocked response for proxy."""
        port = port or self.current_port
        if port in self.proxies:
            # Update proxy-specific tracking
            if port not in self.proxy_health:
                self.proxy_health[port] = {"success": 0, "blocked": 0, "failures": 0}
            
            self.proxy_health[port]["blocked"] += 1
            self.proxies[port].failure_count += 1
            self.proxies[port].consecutive_failures += 1
            
            # Track consecutive blocks across all proxies
            self.consecutive_blocks += 1
            self.session_blocked_proxies += 1
            
            # Retire proxy if blocked too many times
            if self.proxy_health[port]["blocked"] >= 3:
                self.bad_proxies.add(port)
                self.proxies[port].status = ProxyStatus.BANNED
                logger.warning(f"🚫 Retiring proxy {port} - blocked {self.proxy_health[port]['blocked']} times")
            
            # Check if we need to send SMS alert
            self._check_sms_alert()
            
            logger.warning(f"🚫 Proxy {port} blocked (consecutive blocks: {self.consecutive_blocks})")
    
    def _check_sms_alert(self):
        """Check if we need to send urgent SMS alert."""
        now = datetime.now()
        
        # Don't spam SMS - limit to once per hour
        if self.last_sms_alert and (now - self.last_sms_alert).seconds < 3600:
            return
        
        # Alert conditions:
        # 1. 3 or more consecutive blocks across different proxies
        # 2. More than 50% of proxies are blocked/banned in this session
        healthy_proxies = len(self._get_healthy_proxies())
        total_proxies = len(self.proxies)
        healthy_percentage = (healthy_proxies / total_proxies) * 100 if total_proxies > 0 else 0
        
        should_alert = (
            self.consecutive_blocks >= 3 or 
            healthy_percentage < 50 or
            len(self.bad_proxies) >= total_proxies * 0.7  # 70% of proxies are bad
        )
        
        if should_alert:
            message = (
                f"URGENT: Rally scraper hit proxy blocks. "
                f"Consecutive blocks: {self.consecutive_blocks}, "
                f"Healthy proxies: {healthy_proxies}/{total_proxies} ({healthy_percentage:.1f}%), "
                f"Bad proxies: {len(self.bad_proxies)}. "
                f"Investigation required."
            )
            
            if send_urgent_sms(message):
                self.last_sms_alert = now
                logger.warning(f"🚨 SMS alert sent: {message}")
            else:
                logger.error("❌ Failed to send SMS alert")
    
    def reset_consecutive_blocks(self):
        """Reset consecutive block counter on successful request."""
        if self.consecutive_blocks > 0:
            logger.info(f"✅ Resetting consecutive blocks counter (was {self.consecutive_blocks})")
            self.consecutive_blocks = 0
    
    def get_status(self) -> Dict:
        """Get comprehensive status information."""
        healthy_proxies = self._get_healthy_proxies()
        
        return {
            "total_proxies": len(self.proxies),
            "healthy_proxies": len(healthy_proxies),
            "dead_proxies": len(self.dead_proxies),
            "bad_proxies": len(self.bad_proxies),
            "current_proxy": self.current_port,
            "request_count": self.request_count,
            "total_rotations": self.total_rotations,
            "session_duration": time.time() - self.session_start_time,
            "consecutive_blocks": self.consecutive_blocks,
            "session_blocked_proxies": self.session_blocked_proxies,
            "last_sms_alert": self.last_sms_alert.isoformat() if self.last_sms_alert else None,
            "session_metrics": self.session_metrics,
            "proxy_health": {
                port: {
                    "status": info.status.value,
                    "success_rate": info.success_rate,
                    "total_requests": info.total_requests,
                    "consecutive_failures": info.consecutive_failures,
                    "health_stats": self.proxy_health.get(port, {"success": 0, "blocked": 0, "failures": 0})
                }
                for port, info in self.proxies.items()
            }
        }
    
    def get_proxies_dict(self) -> Dict[str, str]:
        """Get proxy dictionary for requests library."""
        proxy_url = self.get_proxy()
        return {
            "http": proxy_url,
            "https": proxy_url
        }

# Global instance
_proxy_rotator = None

def get_proxy_rotator() -> EnhancedProxyRotator:
    """Get the global proxy rotator instance."""
    global _proxy_rotator
    if _proxy_rotator is None:
        _proxy_rotator = EnhancedProxyRotator()
    return _proxy_rotator

def make_proxy_request(url: str, timeout: int = 30, max_retries: int = 3) -> Optional[requests.Response]:
    """Make a request using the proxy rotator."""
    rotator = get_proxy_rotator()
    
    for attempt in range(max_retries):
        try:
            proxy_url = rotator.get_proxy()
            proxies = {"http": proxy_url, "https": proxy_url}
            
            response = requests.get(
                url,
                proxies=proxies,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            
            # Report success
            rotator.report_success()
            return response
            
        except Exception as e:
            logger.warning(f"⚠️ Proxy request failed (attempt {attempt + 1}): {e}")
            rotator.report_failure()
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
    
    return None

def fetch_with_retry(url: str, max_retries: int = 3, timeout: int = 30, **kwargs) -> requests.Response:
    """
    Enhanced fetch function with robust proxy failure detection and retry logic.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of proxy attempts (default: 3)
        timeout: Request timeout in seconds
        **kwargs: Additional arguments for requests.get()
        
    Returns:
        requests.Response: Successful response
        
    Raises:
        Exception: If all proxies fail or are blocked
    """
    rotator = get_proxy_rotator()
    skipped_proxies = set()
    
    for attempt in range(max_retries):
        current_proxy_port = rotator.current_port
        
        # Skip if we've already tried this proxy and it was blocked
        if current_proxy_port in skipped_proxies:
            logger.info(f"🔄 Skipping previously blocked proxy {current_proxy_port}")
            rotator._rotate_proxy()
            current_proxy_port = rotator.current_port
        
        try:
            # Get proxy configuration
            proxy_url = rotator.get_proxy()
            proxies = {"http": proxy_url, "https": proxy_url}
            
            # Set default headers if not provided
            headers = kwargs.get('headers', {})
            if 'User-Agent' not in headers:
                headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            kwargs['headers'] = headers
            
            logger.debug(f"🌐 Attempting request to {url} via proxy {current_proxy_port}")
            
            # Make the request
            response = requests.get(
                url,
                proxies=proxies,
                timeout=timeout,
                **kwargs
            )
            
            # Check if response indicates blocking
            if is_blocked(response):
                logger.warning(f"🚫 Proxy {current_proxy_port} blocked for {url}")
                rotator.report_blocked(current_proxy_port)
                skipped_proxies.add(current_proxy_port)
                
                # Force rotation to try a different proxy
                rotator._rotate_proxy()
                
                if attempt < max_retries - 1:
                    backoff_delay = min(2 ** attempt, 10)  # Cap at 10 seconds
                    logger.info(f"⏳ Waiting {backoff_delay}s before retry...")
                    time.sleep(backoff_delay)
                    continue
                else:
                    raise Exception(f"All {max_retries} proxy attempts blocked for {url}")
            
            # Success!
            rotator.report_success(current_proxy_port)
            logger.debug(f"✅ Successful request to {url} via proxy {current_proxy_port}")
            return response
            
        except requests.exceptions.RequestException as e:
            # Network-related errors (timeout, connection, etc.)
            logger.warning(f"🌐 Network error with proxy {current_proxy_port}: {e}")
            rotator.report_failure(current_proxy_port)
            skipped_proxies.add(current_proxy_port)
            
            # Force rotation on network errors
            rotator._rotate_proxy()
            
            if attempt < max_retries - 1:
                backoff_delay = min(2 ** attempt, 10)
                logger.info(f"⏳ Network error - waiting {backoff_delay}s before retry...")
                time.sleep(backoff_delay)
                continue
            else:
                raise Exception(f"All {max_retries} attempts failed due to network errors for {url}")
                
        except Exception as e:
            # Other unexpected errors
            logger.error(f"❌ Unexpected error with proxy {current_proxy_port}: {e}")
            rotator.report_failure(current_proxy_port)
            
            if attempt < max_retries - 1:
                rotator._rotate_proxy()
                time.sleep(1)
                continue
            else:
                raise Exception(f"Unexpected error after {max_retries} attempts: {e}")
    
    # This should never be reached due to the raise statements above
    raise Exception(f"Failed to fetch {url} after {max_retries} attempts")

if __name__ == "__main__":
    # Test the enhanced proxy rotator with blocking detection
    print("🧪 Testing Enhanced Proxy Rotator with Blocking Detection")
    print("=" * 60)
    
    # Example usage
    print("\n📋 USAGE EXAMPLES:")
    print("=" * 30)
    
    print("\n1. Basic usage with fetch_with_retry:")
    print("   try:")
    print("       response = fetch_with_retry('https://example.com')")
    print("       print(f'Success: {response.status_code}')")
    print("   except Exception as e:")
    print("       print(f'All proxies failed: {e}')")
    
    print("\n2. Check if response is blocked:")
    print("   if is_blocked(response):")
    print("       print('Response indicates blocking!')")
    
    print("\n3. Manual proxy health management:")
    print("   rotator = get_proxy_rotator()")
    print("   rotator.report_blocked()  # Report current proxy as blocked")
    print("   rotator.report_success()  # Report successful request")
    
    print("\n4. Get comprehensive status:")
    print("   status = rotator.get_status()")
    print("   print(f'Healthy proxies: {status[\"healthy_proxies\"]}')")
    print("   print(f'Consecutive blocks: {status[\"consecutive_blocks\"]}')")
    
    # Quick functional test
    print("\n🔧 FUNCTIONAL TEST:")
    print("=" * 30)
    
    try:
        rotator = EnhancedProxyRotator(rotate_every=2)  # Test with faster rotation
        
        # Test basic functionality
        print("✅ Proxy rotator initialized successfully")
        
        # Test status reporting
        status = rotator.get_status()
        print(f"✅ Status check: {status['total_proxies']} total proxies")
        print(f"✅ Healthy proxies: {status['healthy_proxies']}")
        print(f"✅ Bad proxies: {status['bad_proxies']}")
        print(f"✅ Consecutive blocks: {status['consecutive_blocks']}")
        
        # Test proxy cycling
        for i in range(3):
            proxy = rotator.get_proxy()
            print(f"✅ Proxy {i+1}: Port {rotator.current_port}")
            time.sleep(0.5)
        
        print("\n🎉 Enhanced proxy rotator test completed!")
        print("\n💡 TIP: Set environment variables for SMS alerts:")
        print("   - TWILIO_ACCOUNT_SID")
        print("   - TWILIO_AUTH_TOKEN") 
        print("   - TWILIO_SENDER_PHONE")
        
    except Exception as e:
        print(f"❌ Test failed: {e}") 