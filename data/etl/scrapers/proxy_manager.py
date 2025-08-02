#!/usr/bin/env python3
"""
Enhanced Proxy Manager for Rally Tennis Scraper
Uses Decodo residential proxies with intelligent rotation, dead proxy detection,
and comprehensive metrics tracking.
"""

import os
import random
import time
import logging
import requests
from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    def get_status(self) -> Dict:
        """Get comprehensive status information."""
        healthy_proxies = self._get_healthy_proxies()
        
        return {
            "total_proxies": len(self.proxies),
            "healthy_proxies": len(healthy_proxies),
            "dead_proxies": len(self.dead_proxies),
            "current_proxy": self.current_port,
            "request_count": self.request_count,
            "total_rotations": self.total_rotations,
            "session_duration": time.time() - self.session_start_time,
            "session_metrics": self.session_metrics,
            "proxy_health": {
                port: {
                    "status": info.status.value,
                    "success_rate": info.success_rate,
                    "total_requests": info.total_requests,
                    "consecutive_failures": info.consecutive_failures
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

if __name__ == "__main__":
    # Test the proxy rotator
    print("🧪 Testing Enhanced Proxy Rotator")
    print("=" * 50)
    
    rotator = EnhancedProxyRotator(rotate_every=5)  # Test with faster rotation
    
    for i in range(10):
        print(f"\n🔄 Test {i+1}/10:")
        
        # Get proxy
        proxy = rotator.get_proxy()
        print(f"   Proxy: {proxy}")
        
        # Validate IP (this part is not directly applicable to the new structure,
        # but we can add a placeholder for now)
        # For now, we'll just show the current proxy and its status
        status = rotator.get_status()
        print(f"   Current Proxy: {status['current_proxy']}")
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