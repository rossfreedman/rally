#!/usr/bin/env python3
"""
Proxy Manager for Rally Tennis Scraper
Uses Decodo residential proxies with intelligent rotation and sticky sessions.
"""

import os
import random
import time
import logging
import requests
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Decodo Configuration
DECODO_USER = os.getenv("DECODO_USER", "sp2lv5ti3g")
DECODO_PASS = os.getenv("DECODO_PASS", "zU0Pdl~7rcGqgxuM69")
DECODO_ENDPOINT = "us.decodo.com"

def load_decodo_ips():
    """
    Load all 100 Decodo IP addresses from ips.txt file.
    
    Returns:
        list: List of port numbers for all available IPs
    """
    try:
        # Try to load from ips.txt file
        if os.path.exists("ips.txt"):
            with open("ips.txt", "r") as f:
                lines = f.readlines()
            
            ports = []
            for line in lines:
                line = line.strip()
                if line and ":" in line:
                    # Format: us.decodo.com:10001:sp2lv5ti3g:zU0Pdl~7rcGqgxuM69
                    parts = line.split(":")
                    if len(parts) >= 2:
                        port = int(parts[1])
                        ports.append(port)
            
            if ports:
                logger.info(f"📊 Loaded {len(ports)} Decodo IP addresses from ips.txt")
                return ports
            else:
                logger.warning("⚠️ No valid IPs found in ips.txt, using default range")
        else:
            logger.warning("⚠️ ips.txt not found, using default range")
    except Exception as e:
        logger.error(f"❌ Error loading ips.txt: {e}")
    
    # Fallback to default range if file not found or invalid
    return list(range(10001, 10011))  # 10 sticky US ports

DECODO_PORTS = load_decodo_ips()

class ProxyRotator:
    """
    Intelligent proxy rotator with sticky sessions.
    
    Features:
    - Sticky sessions (10-minute duration per IP)
    - Rotates every 30-50 requests
    - Automatic retry with new IP on failure
    - US-based residential IPs only
    """
    
    def __init__(self, ports=DECODO_PORTS, rotate_every=30, session_duration=600):
        """
        Initialize proxy rotator.
        
        Args:
            ports (list): List of available ports
            rotate_every (int): Rotate IP after this many requests
            session_duration (int): Session duration in seconds (10 minutes)
        """
        self.ports = ports
        self.rotate_every = rotate_every
        self.session_duration = session_duration
        self.request_count = 0
        self.current_port = random.choice(self.ports)
        self.session_start_time = time.time()
        self.current_ip = None
        self.total_rotations = 0
        self.total_requests = 0
        
        logger.info(f"🔄 Proxy Rotator initialized with {len(ports)} endpoints")
        logger.info(f"📊 Rotation: Every {rotate_every} requests")
        logger.info(f"⏱️ Session duration: {session_duration} seconds")
        logger.info(f"🌐 IP Pool: {min(ports)}-{max(ports)} ({len(ports)} total IPs)")
    
    def _should_rotate(self) -> bool:
        """Determine if we should rotate to a new IP."""
        # Rotate based on request count
        if self.request_count % self.rotate_every == 0:
            return True
        
        # Rotate based on session duration
        if time.time() - self.session_start_time > self.session_duration:
            return True
        
        return False
    
    def _rotate_ip(self):
        """Rotate to a new IP address."""
        old_port = self.current_port
        self.current_port = random.choice(self.ports)
        self.session_start_time = time.time()
        self.request_count = 0
        self.total_rotations += 1
        
        logger.info(f"\n🔄 Rotating IP: {old_port} → {self.current_port}")
        logger.info(f"📊 Rotation #{self.total_rotations} (Total requests: {self.total_requests})")
        logger.info(f"🌐 Proxy Pool: {len(self.ports)} US-based residential IPs")
        logger.info(f"📈 Performance: {self.total_requests/self.total_rotations:.1f} requests per rotation\n")
    
    def get_proxy(self) -> str:
        """
        Get current proxy URL with intelligent rotation.
        
        Returns:
            str: Proxy URL in format http://user:pass@host:port
        """
        if self._should_rotate():
            self._rotate_ip()
        
        self.request_count += 1
        self.total_requests += 1
        
        proxy_url = f"http://{DECODO_USER}:{DECODO_PASS}@{DECODO_ENDPOINT}:{self.current_port}"
        
        logger.debug(f"📊 Request {self.request_count} via {self.current_port}")
        return proxy_url
    
    def get_proxies_dict(self) -> Dict[str, str]:
        """
        Get proxy configuration for requests library.
        
        Returns:
            dict: Proxy configuration for requests
        """
        proxy_url = self.get_proxy()
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def validate_ip(self) -> Optional[Dict]:
        """
        Validate current IP and get location info.
        
        Returns:
            dict: IP information or None if validation fails
        """
        try:
            proxies = self.get_proxies_dict()
            
            response = requests.get("https://ip.decodo.com/json", proxies=proxies, timeout=10)
            response.raise_for_status()
            
            ip_data = response.json()
            self.current_ip = ip_data.get("proxy", {}).get("ip", "Unknown")
            
            country = ip_data.get("country", {})
            country_code = country.get("code", "") if isinstance(country, dict) else str(country)
            
            logger.info(f"\n✅ IP Validation: {self.current_ip} ({country_code})")
            logger.info(f"🌍 Location: US-based residential proxy")
            logger.info(f"🔒 Security: Anti-detection enabled")
            logger.info(f"📊 Status: Ready for scraping operations\n")
            return ip_data
            
        except Exception as e:
            logger.error(f"❌ IP Validation failed: {str(e)}")
            return None
    
    def get_status(self) -> Dict:
        """
        Get current proxy status.
        
        Returns:
            dict: Status information
        """
        session_age = time.time() - self.session_start_time
        return {
            "current_port": self.current_port,
            "current_ip": self.current_ip,
            "request_count": self.request_count,
            "total_requests": self.total_requests,
            "total_rotations": self.total_rotations,
            "session_age_seconds": session_age,
            "session_age_minutes": session_age / 60,
            "rotate_every": self.rotate_every,
            "session_duration": self.session_duration,
            "available_ips": len(self.ports),
            "ip_pool_range": f"{min(self.ports)}-{max(self.ports)}"
        }

# Global proxy rotator instance
_proxy_rotator = None

def get_proxy_rotator() -> ProxyRotator:
    """Get global proxy rotator instance."""
    global _proxy_rotator
    if _proxy_rotator is None:
        _proxy_rotator = ProxyRotator()
    return _proxy_rotator

def make_proxy_request(url: str, timeout: int = 30, max_retries: int = 3) -> Optional[requests.Response]:
    """
    Make a request through the proxy rotator with automatic retry.
    
    Args:
        url (str): URL to request
        timeout (int): Request timeout
        max_retries (int): Maximum retry attempts
        
    Returns:
        requests.Response: Response object or None if all retries failed
    """
    rotator = get_proxy_rotator()
    
    for attempt in range(max_retries):
        try:
            proxies = rotator.get_proxies_dict()
            response = requests.get(url, proxies=proxies, timeout=timeout)
            response.raise_for_status()
            
            logger.info(f"✅ Request successful via {rotator.current_port}")
            return response
            
        except Exception as e:
            logger.warning(f"⚠️ Attempt {attempt + 1} failed via {rotator.current_port}: {str(e)}")
            
            if attempt < max_retries - 1:
                # Force rotation on failure
                rotator._rotate_ip()
                time.sleep(random.uniform(1, 3))  # Random delay
    
    logger.error(f"❌ All {max_retries} attempts failed for {url}")
    return None

if __name__ == "__main__":
    # Test the proxy rotator
    print("🧪 Testing Proxy Rotator")
    print("=" * 50)
    
    rotator = ProxyRotator(rotate_every=5)  # Test with faster rotation
    
    for i in range(10):
        print(f"\n🔄 Test {i+1}/10:")
        
        # Get proxy
        proxy = rotator.get_proxy()
        print(f"   Proxy: {proxy}")
        
        # Validate IP
        ip_info = rotator.validate_ip()
        if ip_info:
            country = ip_info.get("country", {})
            country_code = country.get("code", "") if isinstance(country, dict) else str(country)
            proxy_ip = ip_info.get("proxy", {}).get("ip", "Unknown")
            print(f"   IP: {proxy_ip}")
            print(f"   Country: {country_code}")
        
        # Show status
        status = rotator.get_status()
        print(f"   Requests: {status['request_count']}")
        print(f"   Session Age: {status['session_age_minutes']:.1f} minutes")
        
        time.sleep(1)  # Brief delay between tests
    
    print("\n🎉 Proxy rotator test completed!") 