#!/usr/bin/env python3
"""
User-Agent Manager for Rally Scraping System
Provides config-driven UA management with rotation and metrics tracking
"""

import json
import os
import random
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class UserAgentMetrics:
    """Track metrics for individual User-Agents."""
    user_agent: str
    success_count: int = 0
    failure_count: int = 0
    total_requests: int = 0
    last_used: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    retired: bool = False
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.success_count / self.total_requests) * 100
    
    @property
    def is_healthy(self) -> bool:
        """Check if UA is healthy for use."""
        # If no requests made yet, consider healthy
        if self.total_requests == 0:
            return not self.retired
        
        # Otherwise, check health criteria
        return (not self.retired and 
                self.consecutive_failures < 3 and 
                self.success_rate >= 80)

class UserAgentManager:
    """Manages User-Agent pools with rotation and metrics tracking."""
    
    def __init__(self, config_path: str = None):
        # Auto-detect config path if not provided
        if config_path is None:
            # Try to find the config file relative to this script's location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "user_agents.json")
        
        self.config_path = config_path
        self.windows_apta_pool: List[str] = []
        self.default_pool: List[str] = []
        self.ua_metrics: Dict[str, UserAgentMetrics] = {}
        self.current_apta_ua: Optional[str] = None
        self.current_apta_session_start: Optional[datetime] = None
        self.last_config_update: Optional[datetime] = None
        
        # Load configuration
        self._load_config()
        self._initialize_metrics()
        
        logger.info(f"🔄 User-Agent Manager initialized")
        logger.info(f"   Windows APTA Pool: {len(self.windows_apta_pool)} UAs")
        logger.info(f"   Default Pool: {len(self.default_pool)} UAs")
    
    def _load_config(self):
        """Load User-Agent configuration from JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                
                self.windows_apta_pool = config.get("WINDOWS_APTA_POOL", [])
                self.default_pool = config.get("DEFAULT_POOL", [])
                self.last_config_update = datetime.now()
                
                logger.info(f"✅ Loaded {len(self.windows_apta_pool)} APTA UAs and {len(self.default_pool)} default UAs")
            else:
                # Only show warning if we're not in fallback mode
                if not hasattr(self, '_fallback_loaded'):
                    logger.warning(f"⚠️ Config file not found: {self.config_path}")
                self._load_fallback_config()
                
        except Exception as e:
            logger.error(f"❌ Failed to load UA config: {e}")
            self._load_fallback_config()
    
    def _load_fallback_config(self):
        """Load fallback configuration if JSON file is missing."""
        self._fallback_loaded = True
        self.windows_apta_pool = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ]
        self.default_pool = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        logger.info("✅ Loaded fallback UA configuration")
    
    def _initialize_metrics(self):
        """Initialize metrics tracking for all User-Agents."""
        for ua in self.windows_apta_pool + self.default_pool:
            self.ua_metrics[ua] = UserAgentMetrics(user_agent=ua)
    
    def get_user_agent_for_site(self, site_url: str, force_new: bool = False) -> str:
        """
        Get appropriate User-Agent for a specific site.
        
        Args:
            site_url: URL of the site to scrape
            force_new: Force new UA selection (for retry scenarios)
            
        Returns:
            str: Selected User-Agent string
        """
        # Check if this is APTA
        if "apta.tenniscores.com" in site_url.lower():
            return self._get_apta_user_agent(force_new)
        else:
            return self._get_default_user_agent()
    
    def _get_apta_user_agent(self, force_new: bool = False) -> str:
        """
        Get Windows User-Agent for APTA with session-based rotation.
        
        Args:
            force_new: Force new UA selection (for retry scenarios)
            
        Returns:
            str: Windows User-Agent for APTA
        """
        current_time = datetime.now()
        
        # Check if we need to start a new session
        if (self.current_apta_ua is None or 
            self.current_apta_session_start is None or
            current_time - self.current_apta_session_start > timedelta(minutes=30) or
            force_new):
            
            # Get healthy UAs from APTA pool
            healthy_apta_uas = [
                ua for ua in self.windows_apta_pool
                if self.ua_metrics[ua].is_healthy
            ]
            
            if not healthy_apta_uas:
                # If no healthy UAs, reset all and try again
                logger.warning("⚠️ No healthy APTA UAs, resetting all")
                self._reset_apta_metrics()
                healthy_apta_uas = self.windows_apta_pool
            
            # Select random UA from healthy pool
            self.current_apta_ua = random.choice(healthy_apta_uas)
            self.current_apta_session_start = current_time
            
            logger.info(f"🔄 APTA session started with UA: {self.current_apta_ua[:50]}...")
        
        # Update metrics
        self.ua_metrics[self.current_apta_ua].last_used = current_time
        
        return self.current_apta_ua
    
    def _get_default_user_agent(self) -> str:
        """Get User-Agent for non-APTA sites."""
        # Get healthy UAs from default pool
        healthy_default_uas = [
            ua for ua in self.default_pool
            if self.ua_metrics[ua].is_healthy
        ]
        
        if not healthy_default_uas:
            # If no healthy UAs, reset all and try again
            logger.warning("⚠️ No healthy default UAs, resetting all")
            self._reset_default_metrics()
            healthy_default_uas = self.default_pool
        
        # Select random UA from healthy pool
        selected_ua = random.choice(healthy_default_uas)
        
        # Update metrics
        self.ua_metrics[selected_ua].last_used = datetime.now()
        
        return selected_ua
    
    def report_success(self, user_agent: str, site_url: str = ""):
        """Report successful request for a User-Agent."""
        if user_agent in self.ua_metrics:
            metrics = self.ua_metrics[user_agent]
            metrics.success_count += 1
            metrics.total_requests += 1
            metrics.consecutive_failures = 0
            metrics.last_success = datetime.now()
            
            if "apta" in site_url.lower():
                logger.info(f"✅ APTA UA success: {user_agent[:50]}... (rate: {metrics.success_rate:.1f}%)")
            else:
                logger.debug(f"✅ UA success: {user_agent[:50]}... (rate: {metrics.success_rate:.1f}%)")
    
    def report_failure(self, user_agent: str, site_url: str = ""):
        """Report failed request for a User-Agent."""
        if user_agent in self.ua_metrics:
            metrics = self.ua_metrics[user_agent]
            metrics.failure_count += 1
            metrics.total_requests += 1
            metrics.consecutive_failures += 1
            
            # Retire UA if too many consecutive failures
            if metrics.consecutive_failures >= 3:
                metrics.retired = True
                logger.warning(f"🚫 Retired UA after {metrics.consecutive_failures} consecutive failures: {user_agent[:50]}...")
            
            if "apta" in site_url.lower():
                logger.warning(f"❌ APTA UA failure: {user_agent[:50]}... (consecutive: {metrics.consecutive_failures})")
            else:
                logger.debug(f"❌ UA failure: {user_agent[:50]}... (consecutive: {metrics.consecutive_failures})")
    
    def _reset_apta_metrics(self):
        """Reset metrics for APTA User-Agents."""
        for ua in self.windows_apta_pool:
            if ua in self.ua_metrics:
                self.ua_metrics[ua].retired = False
                self.ua_metrics[ua].consecutive_failures = 0
        logger.info("🔄 Reset APTA UA metrics")
    
    def _reset_default_metrics(self):
        """Reset metrics for default User-Agents."""
        for ua in self.default_pool:
            if ua in self.ua_metrics:
                self.ua_metrics[ua].retired = False
                self.ua_metrics[ua].consecutive_failures = 0
        logger.info("🔄 Reset default UA metrics")
    
    def get_metrics_summary(self) -> Dict:
        """Get comprehensive metrics summary."""
        apta_healthy = len([ua for ua in self.windows_apta_pool if self.ua_metrics[ua].is_healthy])
        default_healthy = len([ua for ua in self.default_pool if self.ua_metrics[ua].is_healthy])
        
        return {
            "apta_pool": {
                "total": len(self.windows_apta_pool),
                "healthy": apta_healthy,
                "retired": len(self.windows_apta_pool) - apta_healthy
            },
            "default_pool": {
                "total": len(self.default_pool),
                "healthy": default_healthy,
                "retired": len(self.default_pool) - default_healthy
            },
            "current_apta_ua": self.current_apta_ua,
            "current_apta_session_start": self.current_apta_session_start.isoformat() if self.current_apta_session_start else None,
            "last_config_update": self.last_config_update.isoformat() if self.last_config_update else None
        }
    
    def refresh_config(self):
        """Refresh User-Agent configuration from file."""
        logger.info("🔄 Refreshing UA configuration...")
        self._load_config()
        self._initialize_metrics()
        logger.info("✅ UA configuration refreshed")

# Global instance
_ua_manager = None

def get_user_agent_manager() -> UserAgentManager:
    """Get the global User-Agent manager instance."""
    global _ua_manager
    if _ua_manager is None:
        _ua_manager = UserAgentManager()
    return _ua_manager

def get_user_agent_for_site(site_url: str, force_new: bool = False) -> str:
    """Convenience function to get User-Agent for a site."""
    manager = get_user_agent_manager()
    return manager.get_user_agent_for_site(site_url, force_new)

def report_ua_success(user_agent: str, site_url: str = ""):
    """Convenience function to report UA success."""
    manager = get_user_agent_manager()
    manager.report_success(user_agent, site_url)

def report_ua_failure(user_agent: str, site_url: str = ""):
    """Convenience function to report UA failure."""
    manager = get_user_agent_manager()
    manager.report_failure(user_agent, site_url) 