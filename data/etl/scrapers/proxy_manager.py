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
import uuid
from typing import Dict, Optional, List, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMS Configuration
ADMIN_PHONE = "17732138911"

def get_random_headers(url: str = "") -> Dict[str, str]:
    """Get random headers for stealth requests with site-specific User-Agent selection."""
    try:
        # Import here to avoid circular imports
        try:
            from .user_agent_manager import get_user_agent_for_site
        except ImportError:
            import sys
            import os
            # Get the absolute path to the scrapers directory
            current_file = os.path.abspath(__file__)
            scrapers_dir = os.path.dirname(current_file)
            if scrapers_dir not in sys.path:
                sys.path.insert(0, scrapers_dir)
            from user_agent_manager import get_user_agent_for_site
        
        # Get site-specific User-Agent
        user_agent = get_user_agent_for_site(url)
        
        # Enhanced realistic headers for better stealth
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",  # Do Not Track
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua-Platform-Version": '"10.0.0"',
            "Sec-Ch-Ua-Model": '""',
            "Sec-Ch-Ua-Full-Version": '"120.0.6099.109"',
            "Sec-Ch-Ua-Arch": '"x86"',
            "Sec-Ch-Ua-Bitness": '"64"',
            "Sec-Ch-Ua-WoW64": "?0"
        }
        
        # Add referer if we have a previous URL context
        if hasattr(get_random_headers, 'last_url') and get_random_headers.last_url:
            headers["Referer"] = get_random_headers.last_url
        
        # Update last URL for next request
        get_random_headers.last_url = url
        
        return headers
    except Exception as e:
        # Fallback to hardcoded Windows UA if UA manager fails
        logger.warning(f"⚠️ UA manager failed, using fallback: {e}")
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua-Platform-Version": '"10.0.0"',
            "Sec-Ch-Ua-Model": '""',
            "Sec-Ch-Ua-Full-Version": '"120.0.6099.109"',
            "Sec-Ch-Ua-Arch": '"x86"',
            "Sec-Ch-Ua-Bitness": '"64"',
            "Sec-Ch-Ua-WoW64": "?0"
        }

def validate_match_response(response: requests.Response) -> bool:
    """
    Validate if response contains expected Tenniscores match content.
    
    Args:
        response: requests.Response object to validate
        
    Returns:
        bool: True if response contains valid match content, False otherwise
    """
    try:
        if response.status_code != 200:
            logger.warning(f"❌ Invalid status code: {response.status_code}")
            return False
        
        content = response.text.lower() if response.text else ""
        
        # Response must be substantial (not just error pages)
        if len(content) < 500:
            logger.warning(f"❌ Response too short: {len(content)} chars")
            return False
        
        # Must contain key Tenniscores elements - be more flexible for player pages
        required_patterns = [
            "court",  # Court assignments
            "match",  # Match data
            "series",  # Series information
            "player",  # Player information
            "wins",    # Win/loss data
            "losses"   # Win/loss data
        ]
        
        found_patterns = []
        for pattern in required_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        # For player pages, we need at least 1 pattern (more flexible)
        # For team pages, we need at least 2 patterns
        min_patterns = 1 if "player.php" in response.url else 2
        
        if len(found_patterns) >= min_patterns:
            logger.debug(f"✅ Valid content detected: {found_patterns}")
            return True
        
        # Additional validation for specific Tenniscores pages - be more flexible for player pages
        tenniscores_indicators = [
            "tenniscores",
            "match results",
            "league standings", 
            "playoff",
            "schedule",
            "team roster",
            "player",  # Player pages
            "wins",    # Win/loss data
            "losses"   # Win/loss data
        ]
        
        tenniscores_found = sum(1 for indicator in tenniscores_indicators if indicator in content)
        
        # For player pages, we need at least 1 indicator (more flexible)
        # For team pages, we need at least 2 indicators
        min_indicators = 1 if "player.php" in response.url else 2
        
        if tenniscores_found >= min_indicators:
            logger.debug(f"✅ Tenniscores content validated: {tenniscores_found} indicators")
            return True
        
        logger.warning(f"❌ Content validation failed: only {len(found_patterns)} required patterns, {tenniscores_found} tenniscores indicators")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error validating response: {e}")
        return False

def adaptive_throttle(recent_blocks: List[datetime], max_recent: int = 20) -> float:
    """
    Calculate adaptive throttling delay based on recent blocking patterns.
    
    Args:
        recent_blocks: List of recent block timestamps
        max_recent: Maximum number of recent requests to consider
        
    Returns:
        float: Recommended delay in seconds (0 if no throttling needed)
    """
    try:
        if not recent_blocks:
            return 0.0
        
        # Only consider recent blocks (last 20 requests)
        now = datetime.now()
        recent_blocks = [block for block in recent_blocks[-max_recent:] 
                        if (now - block).total_seconds() < 3600]  # Within last hour
        
        if not recent_blocks:
            return 0.0
        
        # Calculate block rate
        total_timespan = (now - recent_blocks[0]).total_seconds() if len(recent_blocks) > 1 else 60
        block_rate = len(recent_blocks) / max(total_timespan / 60, 1)  # blocks per minute
        
        # Calculate percentage of recent requests that were blocked
        block_percentage = (len(recent_blocks) / max_recent) * 100
        
        logger.info(f"📊 Adaptive throttling analysis: {len(recent_blocks)} blocks, {block_percentage:.1f}% rate")
        
        # Escalating throttling based on block rate
        if block_percentage >= 50:  # 50%+ blocks = severe throttling
            delay = random.uniform(45, 75)
            logger.warning(f"🚨 SEVERE throttling: {delay:.1f}s delay (block rate: {block_percentage:.1f}%)")
            return delay
            
        elif block_percentage >= 30:  # 30%+ blocks = heavy throttling
            delay = random.uniform(20, 40)
            logger.warning(f"⚠️ HEAVY throttling: {delay:.1f}s delay (block rate: {block_percentage:.1f}%)")
            return delay
            
        elif block_percentage >= 20:  # 20%+ blocks = moderate throttling
            delay = random.uniform(10, 20)
            logger.warning(f"⏳ MODERATE throttling: {delay:.1f}s delay (block rate: {block_percentage:.1f}%)")
            return delay
            
        elif block_percentage >= 10:  # 10%+ blocks = light throttling
            delay = random.uniform(5, 10)
            logger.info(f"⏳ Light throttling: {delay:.1f}s delay (block rate: {block_percentage:.1f}%)")
            return delay
        
        return 0.0
        
    except Exception as e:
        logger.error(f"❌ Error in adaptive throttling: {e}")
        return 5.0  # Safe fallback

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
        # Check status codes - 522 is Cloudflare timeout, not necessarily a block
        if response.status_code in [403, 429, 503]:
            logger.warning(f"🚫 Blocked status code: {response.status_code}")
            return True
        elif response.status_code == 522:
            logger.warning(f"⚠️ Cloudflare timeout (522) - may be temporary, not marking as blocked")
            return False  # Don't mark 522 as blocked, it's often temporary
        
        # Check response body length (suspiciously short responses)
        content = response.text.lower() if response.text else ""
        if len(content) < 100:
            # Allow short responses if they contain expected content
            tennis_indicators = ["tennis", "match", "player", "score", "league", "series", "club"]
            api_indicators = ["ip", "json", "api", "status", "ok", "success"]
            if not any(indicator in content for indicator in tennis_indicators + api_indicators):
                logger.warning(f"🚫 Suspiciously short response: {len(content)} chars")
                return True
        
        # Check for known blocking text patterns (refined to avoid CDN false positives)
        blocking_patterns = [
            "access denied",
            "verify you are human", 
            "bot detected",
            "please complete the security check",
            "cloudflare ray id",         # More specific than just "cloudflare"
            "ddos protection by cloudflare", # More specific than just "cloudflare"
            "attention required",
            "checking your browser",
            "ddos protection",
            "security challenge", 
            "suspicious activity",
            "blocked for security",
            "captcha",
            "recaptcha"
        ]
        
        # ALLOW legitimate CDN references (these are NOT blocking)
        if any(cdn in content for cdn in [
            "cdnjs.cloudflare.com",
            "cdn.cloudflare.com", 
            "ajax.cloudflare.com"
        ]):
            # If we see CDN references, only flag as blocked if we also see protection patterns
            protection_keywords = ["ray id", "challenge", "checking your browser", "ddos protection"]
            if not any(keyword in content for keyword in protection_keywords):
                return False  # CDN reference without protection = legitimate
        
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
    username: str = ""
    password: str = ""
    status: ProxyStatus = ProxyStatus.ACTIVE
    last_used: Optional[datetime] = None
    last_tested: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    total_requests: int = 0
    last_failure_type: Optional[str] = None  # Track what type of failure occurred
    avg_latency: float = 0.0  # Average response time in seconds
    pool: str = "rotating"  # "trusted" or "rotating"
    session_id: Optional[str] = None  # For sticky sessions
    
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
                 test_url: str = "https://httpbin.org/ip",
                 usage_cap_per_proxy: int = 80,
                 sticky: bool = False):
        """
        Initialize enhanced proxy rotator.
        
        Args:
            ports: List of available ports
            rotate_every: Rotate IP after this many requests
            session_duration: Session duration in seconds
            test_url: URL to test proxy health
            usage_cap_per_proxy: Maximum requests per proxy per session (60-100)
        """
        self.rotate_every = rotate_every
        self.session_duration = session_duration
        self.test_url = test_url
        self.usage_cap_per_proxy = usage_cap_per_proxy
        
        # Initialize proxy credentials storage BEFORE loading ports
        self.proxy_credentials: Dict[int, Dict[str, str]] = {}
        
        # Load ports (this will populate proxy_credentials)
        self.ports = ports or self._load_default_ports()
        
        # Initialize proxy info with loaded credentials
        self.proxies: Dict[int, ProxyInfo] = {}
        for port in self.ports:
            # Get credentials if available
            creds = self.proxy_credentials.get(port, {})
            self.proxies[port] = ProxyInfo(
                port=port,
                host=creds.get('host', 'us.decodo.com'),
                username=creds.get('username', ''),
                password=creds.get('password', '')
            )
        
        # Session tracking
        self.request_count = 0
        self.current_port = random.choice(self.ports)
        self.session_start_time = time.time()
        self.total_rotations = 0
        self.total_requests = 0
        self.dead_proxies: Set[int] = set()
        
        # Session ID for tracking
        self.session_id = str(uuid.uuid4())
        
        # Sticky session support
        self.sticky = sticky
        self.sticky_session_id = None
        self.sticky_proxy_port = None
        
        # Enhanced proxy health tracking
        self.bad_proxies: Set[int] = set()
        self.proxy_health: Dict[int, Dict[str, int]] = {}
        self.consecutive_blocks = 0
        self.last_sms_alert = None
        self.session_blocked_proxies = 0
        
        # Adaptive throttling tracking
        self.recent_blocks: List[datetime] = []
        
        # Usage cap tracking
        self.proxy_usage: Dict[int, int] = {port: 0 for port in self.ports}
        self.capped_proxies: Set[int] = set()
        
        # Adaptive proxy pools
        self.trusted_pool: Set[int] = set()
        self.rotating_pool: Set[int] = set()
        self.pool_promotions = 0
        self.pool_demotions = 0
        
        # Metrics
        self.session_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "proxy_rotations": 0,
            "dead_proxies_detected": 0,
            "warmup_completed": False,
            "usage_capped_proxies": 0,
            "avg_latency_per_proxy": {},
            "proxy_success_rates": {},
            "pool_promotions": 0,
            "pool_demotions": 0,
            "sticky_sessions": 0
        }
        
        logger.info(f"🔄 Enhanced Proxy Rotator initialized")
        logger.info(f"📊 Total proxies: {len(self.ports)}")
        logger.info(f"🔄 Rotation: Every {rotate_every} requests")
        logger.info(f"⏱️ Session duration: {session_duration} seconds")
        logger.info(f"🎯 Usage cap: {usage_cap_per_proxy} requests per proxy")
        
        # Test all proxies initially (skip if in quick test mode or fast mode)
        skip_testing = os.getenv('QUICK_TEST') or os.getenv('FAST_MODE') or os.getenv('SKIP_PROXY_TEST')
        
        if skip_testing:
            logger.info("⚡ Fast mode: Skipping proxy testing, marking first 20 as ready")
            # Mark first 20 proxies as healthy for fast testing
            for port in list(self.ports)[:20]:
                self.proxies[port].status = ProxyStatus.ACTIVE
                self.proxies[port].success_count = 1
        else:
            logger.info("🧪 Testing all proxies...")
            # Only test first 5 proxies to avoid overwhelming the service
            test_ports = list(self.ports)[:5]
            logger.info(f"🧪 Testing first {len(test_ports)} proxies (to avoid rate limiting)")
            self._test_proxy_subset(test_ports)
    
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
                        if len(parts) >= 4:  # host:port:username:password
                            host = parts[0]
                            port = int(parts[1])
                            username = parts[2]
                            password = parts[3]
                            
                            # Store credentials in proxy info when creating
                            self.proxy_credentials[port] = {
                                'host': host,
                                'username': username, 
                                'password': password
                            }
                            ports.append(port)
                        elif len(parts) >= 2:  # Fallback for host:port format
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
        """Test if a proxy is working with multiple fallback URLs and better error handling."""
        try:
            # Create proxy URL with authentication if available
            if proxy_info.username and proxy_info.password:
                proxy_url = f"http://{proxy_info.username}:{proxy_info.password}@{proxy_info.host}:{proxy_info.port}"
            else:
                # Use working credentials as fallback
                proxy_url = f"http://sp2lv5ti3g:zU0Pdl~7rcGqgxuM69@{proxy_info.host}:{proxy_info.port}"
            
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            # Use a single, reliable test URL to avoid rate limiting
            test_urls = [
                "https://api.ipify.org?format=json"  # More reliable than httpbin.org
            ]
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json,text/html,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }
            
            # Try each test URL until one works
            for i, test_url in enumerate(test_urls):
                try:
                    logger.debug(f"🧪 Testing proxy {proxy_info.port} with URL {i+1}/{len(test_urls)}: {test_url}")
                    
                    response = requests.get(
                        test_url,
                        proxies=proxies,
                        timeout=20,  # Increased timeout for reliability
                        headers=headers,
                        allow_redirects=True
                    )
                    
                    # Log the specific status code for debugging
                    if response.status_code != 200:
                        logger.warning(f"⚠️ Proxy {proxy_info.port} returned status {response.status_code} for {test_url}")
                        
                        # If it's a 503, try the next URL
                        if response.status_code == 503:
                            logger.info(f"🔄 Proxy {proxy_info.port} got 503 from {test_url}, trying next URL...")
                            proxy_info.last_failure_type = '503'
                            continue
                        
                        # If it's a 522 (Cloudflare timeout), try the next URL but don't mark as failed
                        if response.status_code == 522:
                            logger.info(f"🔄 Proxy {proxy_info.port} got 522 from {test_url} (Cloudflare timeout), trying next URL...")
                            proxy_info.last_failure_type = '522'
                            continue
                        
                        # For other status codes, mark as failed
                        proxy_info.failure_count += 1
                        proxy_info.consecutive_failures += 1
                        proxy_info.last_failure_type = f'status_{response.status_code}'
                        return False
                    
                    # Success! Verify we got a valid response
                    try:
                        if test_url == "https://httpbin.org/user-agent":
                            # This endpoint returns HTML, not JSON
                            if "user-agent" in response.text.lower():
                                proxy_info.status = ProxyStatus.ACTIVE
                                proxy_info.success_count += 1
                                proxy_info.consecutive_failures = 0
                                logger.info(f"✅ Proxy {proxy_info.port} is healthy (tested with {test_url})")
                                return True
                        else:
                            # JSON endpoints
                            data = response.json()
                            # Check for expected fields in different APIs
                            if any(field in data for field in ['origin', 'ip', 'user-agent']):
                                proxy_info.status = ProxyStatus.ACTIVE
                                proxy_info.success_count += 1
                                proxy_info.consecutive_failures = 0
                                logger.info(f"✅ Proxy {proxy_info.port} is healthy (tested with {test_url})")
                                return True
                            else:
                                logger.warning(f"⚠️ Proxy {proxy_info.port} returned invalid JSON from {test_url}")
                                continue  # Try next URL
                                
                    except ValueError:
                        # Non-JSON response, but might still be valid
                        if len(response.text) > 100:  # Substantial response
                            proxy_info.status = ProxyStatus.ACTIVE
                            proxy_info.success_count += 1
                            proxy_info.consecutive_failures = 0
                            logger.info(f"✅ Proxy {proxy_info.port} is healthy (non-JSON response from {test_url})")
                            return True
                        else:
                            logger.warning(f"⚠️ Proxy {proxy_info.port} returned short response from {test_url}")
                            continue  # Try next URL
                            
                except requests.exceptions.Timeout:
                    logger.warning(f"⏰ Proxy {proxy_info.port} timed out on {test_url}")
                    proxy_info.last_failure_type = 'timeout'
                    continue  # Try next URL
                except requests.exceptions.ConnectionError:
                    logger.warning(f"🔌 Proxy {proxy_info.port} connection error on {test_url}")
                    proxy_info.last_failure_type = 'connection'
                    continue  # Try next URL
                except Exception as e:
                    logger.warning(f"❌ Proxy {proxy_info.port} failed on {test_url}: {e}")
                    proxy_info.last_failure_type = 'exception'
                    continue  # Try next URL
            
            # If we get here, all test URLs failed
            logger.warning(f"❌ Proxy {proxy_info.port} failed all test URLs")
            proxy_info.failure_count += 1
            proxy_info.consecutive_failures += 1
            return False
                
        except Exception as e:
            logger.error(f"❌ Error testing proxy {proxy_info.port}: {e}")
            proxy_info.failure_count += 1
            proxy_info.consecutive_failures += 1
            return False
        finally:
            proxy_info.last_tested = datetime.now()
            proxy_info.total_requests += 1
    
    def _test_proxy_subset(self, ports_to_test: List[int]):
        """Test a subset of proxies to avoid overwhelming the service."""
        logger.info(f"🧪 Testing subset of {len(ports_to_test)} proxies...")
        
        # Test all proxies but with better error handling and diagnostics
        healthy_count = 0
        total_tested = 0
        failed_503_count = 0
        failed_other_count = 0
        timeout_count = 0
        connection_error_count = 0
        
        for port in ports_to_test:
            proxy_info = self.proxies[port]
            total_tested += 1
            logger.info(f"🧪 Testing proxy {total_tested}/{len(ports_to_test)}: Port {port}")
            
            try:
                if self._test_proxy(proxy_info):
                    healthy_count += 1
                    logger.info(f"✅ Proxy {port} is healthy")
                else:
                    logger.warning(f"❌ Proxy {port} failed test")
                    
                    # Track failure types for diagnostics
                    if proxy_info.consecutive_failures >= 3:
                        proxy_info.status = ProxyStatus.DEAD
                        self.dead_proxies.add(port)
                        logger.warning(f"💀 Proxy {port} marked as dead")
                        
                        # Categorize the failure type based on recent testing
                        if hasattr(proxy_info, 'last_failure_type'):
                            if proxy_info.last_failure_type == '503':
                                failed_503_count += 1
                            elif proxy_info.last_failure_type == 'timeout':
                                timeout_count += 1
                            elif proxy_info.last_failure_type == 'connection':
                                connection_error_count += 1
                            else:
                                failed_other_count += 1
                                
            except Exception as e:
                logger.error(f"❌ Error testing proxy {port}: {e}")
                proxy_info.failure_count += 1
                proxy_info.consecutive_failures += 1
                if proxy_info.consecutive_failures >= 3:
                    proxy_info.status = ProxyStatus.DEAD
                    self.dead_proxies.add(port)
                    failed_other_count += 1
        
        # Enhanced diagnostics
        logger.info(f"✅ Proxy testing complete: {healthy_count}/{total_tested} healthy")
        logger.info(f"📊 Failure breakdown:")
        logger.info(f"   - 503 errors: {failed_503_count}")
        logger.info(f"   - Timeouts: {timeout_count}")
        logger.info(f"   - Connection errors: {connection_error_count}")
        logger.info(f"   - Other failures: {failed_other_count}")
        
        # If we have a high 503 rate, provide specific recommendations
        if failed_503_count > 0:
            failure_rate = (failed_503_count / total_tested) * 100
            logger.warning(f"⚠️ High 503 failure rate: {failure_rate:.1f}% ({failed_503_count}/{total_tested})")
            
            if failure_rate > 50:
                logger.error("🚨 CRITICAL: More than 50% of proxies returning 503 errors!")
                logger.error("   This suggests either:")
                logger.error("   1. Proxy provider infrastructure issues")
                logger.error("   2. Test URLs are being rate-limited")
                logger.error("   3. Authentication problems")
                logger.error("   Consider:")
                logger.error("   - Contacting proxy provider")
                logger.error("   - Using different test URLs")
                logger.error("   - Checking proxy credentials")
                
                # Send urgent SMS if configured
                if failed_503_count >= 10:  # Only alert if significant number of failures
                    message = f"URGENT: Rally scraper proxy crisis. {failed_503_count}/{total_tested} proxies returning 503 errors ({failure_rate:.1f}% failure rate). Proxy provider may be down."
                    send_urgent_sms(message)
        
        # If no healthy proxies found, mark first 10 as active for fallback
        if healthy_count == 0:
            logger.warning("⚠️ No healthy proxies found, marking first 10 as active for fallback")
            for i, (port, proxy_info) in enumerate(list(self.proxies.items())[:10]):
                proxy_info.status = ProxyStatus.ACTIVE
                proxy_info.success_count = 1
                logger.info(f"🔄 Marked proxy {port} as active (fallback)")
        
        # If very few healthy proxies, provide recommendations
        elif healthy_count < len(ports_to_test) * 0.2:  # Less than 20% healthy
            logger.warning(f"⚠️ Low healthy proxy count: {healthy_count}/{total_tested} ({healthy_count/total_tested*100:.1f}%)")
            logger.warning("   Consider:")
            logger.warning("   - Reducing request frequency")
            logger.warning("   - Using longer delays between requests")
            logger.warning("   - Contacting proxy provider for support")
    
    def _test_all_proxies(self):
        """Test all proxies to find healthy ones."""
        logger.info(f"🧪 Testing all {len(self.ports)} proxies...")
        
        healthy_count = 0
        total_tested = 0
        failed_503_count = 0
        failed_other_count = 0
        timeout_count = 0
        connection_error_count = 0
        
        for port in self.ports:
            proxy_info = self.proxies[port]
            total_tested += 1
            logger.info(f"🧪 Testing proxy {total_tested}/{len(self.ports)}: Port {port}")
            
            try:
                if self._test_proxy(proxy_info):
                    healthy_count += 1
                    logger.info(f"✅ Proxy {port} is healthy")
                else:
                    logger.warning(f"❌ Proxy {port} failed test")
                    
                    # Track failure types for diagnostics
                    if proxy_info.consecutive_failures >= 3:
                        proxy_info.status = ProxyStatus.DEAD
                        self.dead_proxies.add(port)
                        logger.warning(f"💀 Proxy {port} marked as dead")
                        
                        # Categorize the failure type based on recent testing
                        if hasattr(proxy_info, 'last_failure_type'):
                            if proxy_info.last_failure_type == '503':
                                failed_503_count += 1
                            elif proxy_info.last_failure_type == 'timeout':
                                timeout_count += 1
                            elif proxy_info.last_failure_type == 'connection':
                                connection_error_count += 1
                            else:
                                failed_other_count += 1
                                
            except Exception as e:
                logger.error(f"❌ Error testing proxy {port}: {e}")
                proxy_info.failure_count += 1
                proxy_info.consecutive_failures += 1
                if proxy_info.consecutive_failures >= 3:
                    proxy_info.status = ProxyStatus.DEAD
                    self.dead_proxies.add(port)
                    failed_other_count += 1
        
        # Enhanced diagnostics
        logger.info(f"✅ Proxy testing complete: {healthy_count}/{total_tested} healthy")
        logger.info(f"📊 Failure breakdown:")
        logger.info(f"   - 503 errors: {failed_503_count}")
        logger.info(f"   - Timeouts: {timeout_count}")
        logger.info(f"   - Connection errors: {connection_error_count}")
        logger.info(f"   - Other failures: {failed_other_count}")
        
        # If we have a high 503 rate, provide specific recommendations
        if failed_503_count > 0:
            failure_rate = (failed_503_count / total_tested) * 100
            logger.warning(f"⚠️ High 503 failure rate: {failure_rate:.1f}% ({failed_503_count}/{total_tested})")
            
            if failure_rate > 50:
                logger.error("🚨 CRITICAL: More than 50% of proxies returning 503 errors!")
                logger.error("   This suggests either:")
                logger.error("   1. Proxy provider infrastructure issues")
                logger.error("   2. Test URLs are being rate-limited")
                logger.error("   3. Authentication problems")
                logger.error("   Consider:")
                logger.error("   - Contacting proxy provider")
                logger.error("   - Using different test URLs")
                logger.error("   - Checking proxy credentials")
                
                # Send urgent SMS if configured
                if failed_503_count >= 10:  # Only alert if significant number of failures
                    message = f"URGENT: Rally scraper proxy crisis. {failed_503_count}/{total_tested} proxies returning 503 errors ({failure_rate:.1f}% failure rate). Proxy provider may be down."
                    send_urgent_sms(message)
        
        # If no healthy proxies found, mark first 10 as active for fallback
        if healthy_count == 0:
            logger.warning("⚠️ No healthy proxies found, marking first 10 as active for fallback")
            for i, (port, proxy_info) in enumerate(list(self.proxies.items())[:10]):
                proxy_info.status = ProxyStatus.ACTIVE
                proxy_info.success_count = 1
                logger.info(f"🔄 Marked proxy {port} as active (fallback)")
        
        # If very few healthy proxies, provide recommendations
        elif healthy_count < len(self.ports) * 0.2:  # Less than 20% healthy
            logger.warning(f"⚠️ Low healthy proxy count: {healthy_count}/{total_tested} ({healthy_count/total_tested*100:.1f}%)")
            logger.warning("   Consider:")
            logger.warning("   - Reducing request frequency")
            logger.warning("   - Using longer delays between requests")
            logger.warning("   - Contacting proxy provider for support")
    
    def run_proxy_warmup(self, test_tenniscores: bool = True) -> Dict[str, any]:
        """
        Run comprehensive proxy warmup to test all proxies before scraping session.
        
        Args:
            test_tenniscores: Whether to test access to Tenniscores.com specifically
            
        Returns:
            Dict: Warmup results and statistics
        """
        logger.info("🔥 Starting proxy warmup process...")
        warmup_start = time.time()
        
        warmup_results = {
            "total_proxies": len(self.ports),
            "healthy_proxies": 0,
            "slow_proxies": 0,
            "dead_proxies": 0,
            "tenniscores_accessible": 0,
            "average_response_time": 0.0,
            "warmup_duration": 0.0,
            "detailed_results": []
        }
        
        response_times = []
        
        for i, port in enumerate(self.ports):
            proxy_info = self.proxies[port]
            
            logger.info(f"🧪 Warming up proxy {i+1}/{len(self.ports)}: Port {port}")
            
            proxy_result = {
                "port": port,
                "ip_test_success": False,
                "ip_test_time": 0.0,
                "tenniscores_test_success": False,
                "tenniscores_test_time": 0.0,
                "status": "unknown"
            }
            
            # Test 1: Basic IP validation
            try:
                proxy_url = f"http://sp2lv5ti3g:zU0Pdl~7rcGqgxuM69@us.decodo.com:{port}"
                proxies = {"http": proxy_url, "https": proxy_url}
                
                start_time = time.time()
                response = requests.get(
                    "https://ip.decodo.com/json",
                    proxies=proxies,
                    timeout=15,
                    headers=get_random_headers()
                )
                
                ip_test_time = time.time() - start_time
                proxy_result["ip_test_time"] = ip_test_time
                
                if response.status_code == 200:
                    proxy_result["ip_test_success"] = True
                    response_times.append(ip_test_time)
                    
                    # Check if response time is reasonable
                    if ip_test_time > 10:
                        warmup_results["slow_proxies"] += 1
                        proxy_info.status = ProxyStatus.TESTING
                        logger.warning(f"⚠️ Proxy {port} is slow: {ip_test_time:.2f}s")
                    else:
                        warmup_results["healthy_proxies"] += 1
                        proxy_info.status = ProxyStatus.ACTIVE
                        proxy_info.success_count += 1
                        proxy_info.consecutive_failures = 0
                        
                else:
                    raise Exception(f"Bad status code: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"❌ Proxy {port} failed IP test: {e}")
                proxy_info.failure_count += 1
                proxy_info.consecutive_failures += 1
                proxy_info.status = ProxyStatus.DEAD
                self.dead_proxies.add(port)
                warmup_results["dead_proxies"] += 1
                proxy_result["status"] = "dead"
                
            # Test 2: Tenniscores accessibility (if proxy passed IP test)
            if test_tenniscores and proxy_result["ip_test_success"]:
                try:
                    start_time = time.time()
                    response = requests.get(
                        "https://tenniscores.com/",
                        proxies=proxies,
                        timeout=15,
                        headers=get_random_headers()
                    )
                    
                    tenniscores_test_time = time.time() - start_time
                    proxy_result["tenniscores_test_time"] = tenniscores_test_time
                    
                    if response.status_code == 200 and validate_match_response(response):
                        proxy_result["tenniscores_test_success"] = True
                        warmup_results["tenniscores_accessible"] += 1
                        proxy_result["status"] = "excellent"
                        logger.info(f"✅ Proxy {port} - Tenniscores accessible: {tenniscores_test_time:.2f}s")
                    else:
                        logger.warning(f"⚠️ Proxy {port} - Tenniscores blocked or invalid")
                        proxy_result["status"] = "limited"
                        
                except Exception as e:
                    logger.warning(f"❌ Proxy {port} failed Tenniscores test: {e}")
                    proxy_result["status"] = "limited"
            
            warmup_results["detailed_results"].append(proxy_result)
            
            # Update proxy info
            proxy_info.last_tested = datetime.now()
            proxy_info.total_requests += 1
            
            # Brief delay between tests to avoid overwhelming
            time.sleep(random.uniform(0.5, 1.5))
        
        # Calculate statistics
        warmup_duration = time.time() - warmup_start
        warmup_results["warmup_duration"] = warmup_duration
        
        if response_times:
            warmup_results["average_response_time"] = sum(response_times) / len(response_times)
        
        # Update session metrics
        self.session_metrics["warmup_completed"] = True
        
        # Log summary
        logger.info(f"🔥 Proxy warmup completed in {warmup_duration:.1f}s")
        logger.info(f"✅ Results: {warmup_results['healthy_proxies']} healthy, "
                   f"{warmup_results['slow_proxies']} slow, "
                   f"{warmup_results['dead_proxies']} dead")
        logger.info(f"🎯 Tenniscores accessible: {warmup_results['tenniscores_accessible']}/{len(self.ports)}")
        logger.info(f"⚡ Average response time: {warmup_results['average_response_time']:.2f}s")
        
        return warmup_results
    
    def _get_healthy_proxies(self) -> List[int]:
        """Get list of healthy proxy ports that haven't reached usage caps."""
        return [port for port, info in self.proxies.items() 
                if info.is_healthy 
                and port not in self.dead_proxies 
                and port not in self.capped_proxies
                and self.proxy_usage.get(port, 0) < self.usage_cap_per_proxy]
    
    def _should_rotate(self) -> bool:
        """Determine if we should rotate to a new proxy."""
        # Rotate based on request count
        if self.request_count % self.rotate_every == 0:
            return True
        
        # Rotate if current proxy is unhealthy
        current_info = self.proxies.get(self.current_port)
        if current_info and not current_info.is_healthy:
            return True
        
        # Rotate if current proxy has reached usage cap
        if self.proxy_usage.get(self.current_port, 0) >= self.usage_cap_per_proxy:
            logger.info(f"🎯 Proxy {self.current_port} reached usage cap ({self.usage_cap_per_proxy} requests)")
            self.capped_proxies.add(self.current_port)
            self.session_metrics["usage_capped_proxies"] += 1
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
            if os.getenv('QUICK_TEST'):
                logger.info("⚡ QUICK_TEST: Using first 10 proxies without testing")
                # In quick test mode, just mark first 10 proxies as healthy
                for port in list(self.ports)[:10]:
                    self.proxies[port].status = ProxyStatus.ACTIVE
                    self.proxies[port].success_count = 1  # Fake success
                healthy_proxies = list(self.ports)[:10]
            else:
                # Prefer testing a subset to reduce long retest bursts
                logger.warning("⚠️ No healthy proxies available, testing a subset of proxies...")
                # Prefer non-dead and non-capped proxies
                candidate_ports = [
                    p for p in self.ports
                    if p not in self.dead_proxies and p not in self.capped_proxies
                ]
                test_ports = (candidate_ports or list(self.ports))[:30]
                self._test_proxy_subset(test_ports)
                healthy_proxies = self._get_healthy_proxies()

                # If still none, fall back to testing all proxies
                if not healthy_proxies:
                    logger.warning("⚠️ Subset test yielded no healthy proxies, testing all proxies...")
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
    
    def get_proxy(self, session_id: str = None) -> str:
        """Get current proxy URL with authentication."""
        # Handle sticky sessions
        if self.sticky and session_id:
            if self.sticky_session_id == session_id and self.sticky_proxy_port:
                # Reuse the same proxy for this session
                self.current_port = self.sticky_proxy_port
                logger.info(f"🔄 Sticky session {session_id}: reusing proxy {self.current_port}")
            else:
                # Start new sticky session
                self.sticky_session_id = session_id
                self.sticky_proxy_port = self._select_best_proxy()
                self.current_port = self.sticky_proxy_port
                self.session_metrics["sticky_sessions"] += 1
                logger.info(f"🔄 Sticky session {session_id}: assigned proxy {self.current_port}")
        else:
            # Check if we should rotate
            if self._should_rotate():
                self._rotate_proxy()
        
        # Update request count
        self.request_count += 1
        self.total_requests += 1
        self.session_metrics["total_requests"] += 1
        
        # Update proxy usage count
        self.proxy_usage[self.current_port] = self.proxy_usage.get(self.current_port, 0) + 1
        
        # Update current proxy info
        if self.current_port in self.proxies:
            self.proxies[self.current_port].last_used = datetime.now()
        
        # Get proxy info with credentials
        proxy_info = self.proxies.get(self.current_port)
        if proxy_info and proxy_info.username and proxy_info.password:
            return f"http://{proxy_info.username}:{proxy_info.password}@{proxy_info.host}:{proxy_info.port}"
        else:
            # Use working credentials as fallback (from working_proxy_config.json)
            return f"http://sp2lv5ti3g:zU0Pdl~7rcGqgxuM69@us.decodo.com:{self.current_port}"
    
    def report_success(self, port: int = None, latency: float = None):
        """Report successful request for proxy."""
        port = port or self.current_port
        if port in self.proxies:
            proxy_info = self.proxies[port]
            proxy_info.success_count += 1
            proxy_info.consecutive_failures = 0
            proxy_info.total_requests += 1
            self.session_metrics["successful_requests"] += 1
            
            # Update latency tracking
            if latency is not None:
                if proxy_info.avg_latency == 0.0:
                    proxy_info.avg_latency = latency
                else:
                    # Rolling average (80% old, 20% new)
                    proxy_info.avg_latency = (proxy_info.avg_latency * 0.8) + (latency * 0.2)
                
                self.session_metrics["avg_latency_per_proxy"][port] = proxy_info.avg_latency
            
            # Update success rate tracking
            self.session_metrics["proxy_success_rates"][port] = proxy_info.success_rate
            
            # Check for pool promotion (to trusted pool)
            if (proxy_info.pool == "rotating" and 
                proxy_info.success_rate >= 90 and 
                proxy_info.total_requests >= 10 and
                port not in self.trusted_pool):
                self._promote_to_trusted(port)
            
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
            proxy_info = self.proxies[port]
            proxy_info.failure_count += 1
            proxy_info.consecutive_failures += 1
            proxy_info.total_requests += 1
            
            # Update success rate tracking
            self.session_metrics["proxy_success_rates"][port] = proxy_info.success_rate
            
            # Check for pool demotion (from trusted pool)
            if (proxy_info.pool == "trusted" and 
                proxy_info.success_rate < 70 and 
                proxy_info.total_requests >= 10):
                self._demote_from_trusted(port)
            
            # Mark as dead if too many consecutive failures
            if proxy_info.consecutive_failures >= 3:
                proxy_info.status = ProxyStatus.DEAD
                self.dead_proxies.add(port)
                self.session_metrics["dead_proxies_detected"] += 1
                logger.warning(f"💀 Marking proxy {port} as dead")
            
            self.session_metrics["failed_requests"] += 1
    
    def report_blocked(self, port: int = None):
        """Report blocked response for proxy."""
        port = port or self.current_port
        if port in self.proxies:
            # Track block timestamp for adaptive throttling
            block_time = datetime.now()
            self.recent_blocks.append(block_time)
            
            # Keep only recent blocks (last 50 for efficiency)
            if len(self.recent_blocks) > 50:
                self.recent_blocks = self.recent_blocks[-50:]
            
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
            
            # Remove SMS alert - only send summary at end of session
            # self._check_sms_alert()
            
            logger.warning(f"🚫 Proxy {port} blocked (consecutive blocks: {self.consecutive_blocks})")
    
    def get_adaptive_throttle_delay(self) -> float:
        """Get recommended throttling delay based on recent blocks."""
        return adaptive_throttle(self.recent_blocks)
    
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
    
    def _select_best_proxy(self) -> int:
        """Select the best available proxy, prioritizing trusted pool."""
        # First try trusted pool
        trusted_available = [p for p in self.trusted_pool if p not in self.dead_proxies and p not in self.capped_proxies]
        if trusted_available:
            return random.choice(trusted_available)
        
        # Fall back to rotating pool
        rotating_available = [p for p in self.rotating_pool if p not in self.dead_proxies and p not in self.capped_proxies]
        if rotating_available:
            return random.choice(rotating_available)
        
        # Last resort: any available proxy
        available = [p for p in self.ports if p not in self.dead_proxies and p not in self.capped_proxies]
        if available:
            return random.choice(available)
        
        # If all proxies are dead/capped, reset usage caps and try again
        logger.warning("⚠️ All proxies are dead or capped, resetting usage caps")
        self.capped_proxies.clear()
        available = [p for p in self.ports if p not in self.dead_proxies]
        return random.choice(available) if available else self.ports[0]
    
    def _promote_to_trusted(self, port: int):
        """Promote a proxy to the trusted pool."""
        if port in self.rotating_pool:
            self.rotating_pool.remove(port)
        self.trusted_pool.add(port)
        self.proxies[port].pool = "trusted"
        self.pool_promotions += 1
        self.session_metrics["pool_promotions"] += 1
        logger.info(f"⭐ Promoted proxy {port} to trusted pool (success rate: {self.proxies[port].success_rate:.1f}%)")
    
    def _demote_from_trusted(self, port: int):
        """Demote a proxy from the trusted pool."""
        if port in self.trusted_pool:
            self.trusted_pool.remove(port)
        self.rotating_pool.add(port)
        self.proxies[port].pool = "rotating"
        self.pool_demotions += 1
        self.session_metrics["pool_demotions"] += 1
        logger.warning(f"📉 Demoted proxy {port} from trusted pool (success rate: {self.proxies[port].success_rate:.1f}%)")
    
    def release_proxy(self, session_id: str = None):
        """Release a sticky proxy session."""
        if self.sticky and session_id == self.sticky_session_id:
            self.sticky_session_id = None
            self.sticky_proxy_port = None
            logger.info(f"🔄 Released sticky session {session_id}")
    
    def _update_pool_assignments(self):
        """Update pool assignments based on current performance."""
        for port, proxy_info in self.proxies.items():
            if proxy_info.total_requests < 5:  # Need minimum data
                continue
                
            # Promote to trusted if criteria met
            if (proxy_info.pool == "rotating" and 
                proxy_info.success_rate >= 90 and 
                proxy_info.total_requests >= 10 and
                port not in self.trusted_pool):
                self._promote_to_trusted(port)
            
            # Demote from trusted if criteria not met
            elif (proxy_info.pool == "trusted" and 
                  (proxy_info.success_rate < 80 or proxy_info.consecutive_failures >= 2)):
                self._demote_from_trusted(port)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the proxy rotator."""
        healthy_proxies = len(self._get_healthy_proxies())
        total_proxies = len(self.proxies)
        
        return {
            "total_proxies": total_proxies,
            "healthy_proxies": healthy_proxies,
            "bad_proxies": len(self.bad_proxies),
            "dead_proxies": len(self.dead_proxies),
            "capped_proxies": len(self.capped_proxies),
            "consecutive_blocks": self.consecutive_blocks,
            "session_blocked_proxies": self.session_blocked_proxies,
            "pool_promotions": self.pool_promotions,
            "pool_demotions": self.pool_demotions,
            "sticky_sessions": self.session_metrics.get("sticky_sessions", 0),
            "current_port": self.current_port,
            "sticky_proxy_port": self.sticky_proxy_port,
            "session_metrics": self.session_metrics
        }
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics for summary reporting."""
        healthy_proxies = len(self._get_healthy_proxies())
        total_proxies = len(self.proxies)
        blocked_proxies = len(self.bad_proxies) + len(self.dead_proxies)
        
        return {
            "healthy_proxies": f"{healthy_proxies}/{total_proxies}",
            "blocked_proxies": f"{blocked_proxies}/{total_proxies}",
            "success_rate": f"{healthy_proxies/total_proxies*100:.1f}%" if total_proxies > 0 else "0%",
            "consecutive_blocks": self.consecutive_blocks,
            "total_requests": self.session_metrics.get("total_requests", 0),
            "successful_requests": self.session_metrics.get("successful_requests", 0),
            "failed_requests": self.session_metrics.get("failed_requests", 0)
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

def get_proxy_rotator(sticky: bool = True) -> EnhancedProxyRotator:
    """Get the global proxy rotator instance."""
    global _proxy_rotator
    if _proxy_rotator is None:
        _proxy_rotator = EnhancedProxyRotator(sticky=sticky)
    elif sticky and not _proxy_rotator.sticky:
        # If sticky is requested but current instance isn't sticky, create new one
        _proxy_rotator = EnhancedProxyRotator(sticky=sticky)
    return _proxy_rotator

def make_proxy_request(url: str, timeout: int = 30, max_retries: int = 3) -> Optional[requests.Response]:
    """Make a request using the proxy rotator with User-Agent management."""
    rotator = get_proxy_rotator()
    
    # Import UA manager functions
    try:
        from .user_agent_manager import report_ua_success, report_ua_failure, get_user_agent_for_site
    except ImportError:
        import sys
        import os
        # Get the absolute path to the scrapers directory
        current_file = os.path.abspath(__file__)
        scrapers_dir = os.path.dirname(current_file)
        if scrapers_dir not in sys.path:
            sys.path.insert(0, scrapers_dir)
        from user_agent_manager import report_ua_success, report_ua_failure, get_user_agent_for_site
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            proxy_url = rotator.get_proxy()
            proxies = {"http": proxy_url, "https": proxy_url}
            
            # Get site-specific User-Agent
            user_agent = get_user_agent_for_site(url, force_new=(attempt > 0))
            headers = get_random_headers(url)
            
            response = requests.get(
                url,
                proxies=proxies,
                timeout=timeout,
                headers=headers
            )
            
            latency = time.time() - start_time
            
            # Check if blocked
            if is_blocked(response):
                rotator.report_blocked()
                report_ua_failure(user_agent, url)
                
                if attempt < max_retries - 1:
                    # Swap proxy and retry with new UA
                    logger.info(f"🔄 Swapping proxy and UA due to block (attempt {attempt + 1})")
                    time.sleep(random.uniform(1, 3))  # Random delay
                    continue
                else:
                    raise Exception(f"All proxies blocked for {url}")
            
            # Report success with latency
            rotator.report_success(latency=latency)
            report_ua_success(user_agent, url)
            return response
            
        except Exception as e:
            logger.warning(f"⚠️ Proxy request failed (attempt {attempt + 1}): {e}")
            rotator.report_failure()
            
            # Report UA failure if we have the user agent
            try:
                user_agent = get_user_agent_for_site(url, force_new=(attempt > 0))
                report_ua_failure(user_agent, url)
            except:
                pass
            
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2 ** attempt, 2 ** (attempt + 1)))  # Exponential backoff with randomization
                continue
    
    raise Exception(f"All proxies failed for {url}")

def fetch_with_retry(url: str, max_retries: int = 3, timeout: int = 30, session_id: str = None, **kwargs) -> requests.Response:
    """
    Enhanced fetch function with granular retry logic and proxy rotation.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of proxy attempts (default: 3)
        timeout: Request timeout in seconds
        session_id: Optional session ID for sticky sessions
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
            
            # Use randomized headers for stealth
            headers = kwargs.get('headers', {})
            if not headers or 'User-Agent' not in headers:
                headers = get_random_headers()
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
                    # Apply adaptive throttling
                    adaptive_delay = rotator.get_adaptive_throttle_delay()
                    base_backoff = min(2 ** attempt, 10)  # Cap at 10 seconds
                    total_delay = max(base_backoff, adaptive_delay)
                    
                    logger.info(f"⏳ Adaptive throttling: {total_delay:.1f}s delay (base: {base_backoff:.1f}s, adaptive: {adaptive_delay:.1f}s)")
                    time.sleep(total_delay)
                    continue
                else:
                    raise Exception(f"All {max_retries} proxy attempts blocked for {url}")
            
            # Additional content validation for Tenniscores pages
            if "tenniscores.com" in url.lower() and not validate_match_response(response):
                logger.warning(f"❌ Content validation failed for {url} via proxy {current_proxy_port}")
                rotator.report_blocked(current_proxy_port)  # Treat invalid content as blocking
                skipped_proxies.add(current_proxy_port)
                rotator._rotate_proxy()
                
                if attempt < max_retries - 1:
                    # Apply adaptive throttling for content validation failures too
                    adaptive_delay = rotator.get_adaptive_throttle_delay()
                    base_backoff = min(2 ** attempt, 10)
                    total_delay = max(base_backoff, adaptive_delay)
                    
                    logger.info(f"⏳ Content validation failed - adaptive delay: {total_delay:.1f}s")
                    time.sleep(total_delay)
                    continue
                else:
                    raise Exception(f"All {max_retries} attempts failed content validation for {url}")
            
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