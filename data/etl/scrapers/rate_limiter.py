#!/usr/bin/env python3
"""
Per-Domain Rate Limiter for Rally Scrapers
==========================================

Implements token bucket rate limiting per domain to prevent 429 responses
and maintain stealth during long-running scrapes.

Usage:
    from rate_limiter import PerDomainRateLimiter
    
    limiter = PerDomainRateLimiter(requests_per_minute=30)
    if limiter.can_make_request('tenniscores.com'):
        # Make request
        limiter.record_request('tenniscores.com')
    else:
        # Wait or skip
"""

import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float = 0
    last_refill: float = field(default_factory=time.time)
    refill_rate: float = 0  # tokens per second
    
    def __post_init__(self):
        self.tokens = self.capacity
        self.refill_rate = self.capacity / 60.0  # Convert per-minute to per-second
    
    def can_consume(self, tokens: int = 1) -> bool:
        """Check if we can consume tokens."""
        self._refill()
        return self.tokens >= tokens
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens if available."""
        if self.can_consume(tokens):
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        time_passed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
        self.last_refill = now

class PerDomainRateLimiter:
    """Rate limiter that maintains separate token buckets per domain."""
    
    def __init__(self, requests_per_minute: int = 30, burst_capacity: int = None):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute per domain
            burst_capacity: Maximum burst capacity (defaults to requests_per_minute)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_capacity = burst_capacity or requests_per_minute
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = threading.Lock()
        
        # Domain-specific overrides for different sites
        self.domain_limits = {
            'tenniscores.com': 25,  # More conservative for tenniscores
            'aptachicago.tenniscores.com': 20,
            'cnswpl.tenniscores.com': 20,
            'nstf.tenniscores.com': 20,
            'cita.tenniscores.com': 20,
        }
    
    def _get_bucket(self, domain: str) -> TokenBucket:
        """Get or create token bucket for domain."""
        with self.lock:
            if domain not in self.buckets:
                # Use domain-specific limit if available
                limit = self.domain_limits.get(domain, self.requests_per_minute)
                self.buckets[domain] = TokenBucket(capacity=limit)
            return self.buckets[domain]
    
    def can_make_request(self, domain: str) -> bool:
        """
        Check if we can make a request to the domain.
        
        Args:
            domain: Domain name (e.g., 'tenniscores.com')
            
        Returns:
            bool: True if request is allowed
        """
        bucket = self._get_bucket(domain)
        return bucket.can_consume()
    
    def record_request(self, domain: str) -> bool:
        """
        Record a request to the domain.
        
        Args:
            domain: Domain name
            
        Returns:
            bool: True if request was recorded successfully
        """
        bucket = self._get_bucket(domain)
        return bucket.consume()
    
    def get_wait_time(self, domain: str) -> float:
        """
        Get the time to wait before next request is allowed.
        
        Args:
            domain: Domain name
            
        Returns:
            float: Seconds to wait (0 if no wait needed)
        """
        bucket = self._get_bucket(domain)
        bucket._refill()
        
        if bucket.tokens >= 1:
            return 0.0
        
        # Calculate time needed to get 1 token
        tokens_needed = 1 - bucket.tokens
        return tokens_needed / bucket.refill_rate
    
    def get_status(self, domain: str) -> Dict[str, float]:
        """
        Get current status of domain's rate limiter.
        
        Args:
            domain: Domain name
            
        Returns:
            dict: Status information
        """
        bucket = self._get_bucket(domain)
        bucket._refill()
        
        return {
            'tokens_available': bucket.tokens,
            'capacity': bucket.capacity,
            'refill_rate': bucket.refill_rate,
            'utilization': (bucket.capacity - bucket.tokens) / bucket.capacity * 100
        }
    
    def reset_domain(self, domain: str):
        """Reset rate limiter for a specific domain."""
        with self.lock:
            if domain in self.buckets:
                del self.buckets[domain]
    
    def reset_all(self):
        """Reset all rate limiters."""
        with self.lock:
            self.buckets.clear()

# Global instance for easy access
_global_limiter: Optional[PerDomainRateLimiter] = None

def get_rate_limiter() -> PerDomainRateLimiter:
    """Get global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = PerDomainRateLimiter()
    return _global_limiter

def can_make_request(domain: str) -> bool:
    """Convenience function to check if request is allowed."""
    return get_rate_limiter().can_make_request(domain)

def record_request(domain: str) -> bool:
    """Convenience function to record a request."""
    return get_rate_limiter().record_request(domain)
