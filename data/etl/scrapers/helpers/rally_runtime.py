#!/usr/bin/env python3
"""
Rally Runtime Context Manager
============================

Shared wrapper for all Rally scrapers providing:
- Single driver reuse per series/job
- Consistent User-Agent management  
- Human-like pacing and delays
- Selective debug HTML saving
- Context management for cleanup

Usage:
    # Circular import - ScrapeContext is defined in this file
    
    ctx = ScrapeContext(series_id="cnswpl_players", site_hint="https://cnswpl.tenniscores.com/")
    driver = ctx.start_driver()
    
    for i, url in enumerate(player_urls):
        html = ctx.browser.fetch_player_with_existing_driver(driver, url)
        ok = validate_player_html(html)
        ctx.maybe_save_debug(html, ok, save_html, "player", i)
        process_data(html)
        ctx.pause_between_players(i)
    
    ctx.stop_driver()
"""

import contextlib
import logging
import os
import random
import time
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class ScrapeContext:
    """Context manager for scraper sessions with driver reuse and pacing."""
    
    def __init__(self, series_id: str = "job", site_hint: str = "https://tenniscores.com/"):
        """
        Initialize scrape context.
        
        Args:
            series_id: Identifier for this scraping job/series
            site_hint: URL hint for User-Agent selection
        """
        self.series_id = series_id
        self.site_hint = site_hint
        self.browser: Optional['StealthBrowser'] = None
        self.driver = None
        
        # Import settings
        try:
            try:
                from .settings_stealth import (
                    STEALTH_REUSE_DRIVER, STEALTH_STICKY_UA, STEALTH_SAVE_DEBUG_HTML, 
                    STEALTH_DEBUG_SAMPLE_EVERY, PLAYER_DELAY_RANGE, TEAM_DELAY_RANGE,
                    STRETCH_PAUSE_EVERY, STRETCH_PAUSE_RANGE
                )
            except ImportError:
                from settings_stealth import (
                    STEALTH_REUSE_DRIVER, STEALTH_STICKY_UA, STEALTH_SAVE_DEBUG_HTML, 
                    STEALTH_DEBUG_SAMPLE_EVERY, PLAYER_DELAY_RANGE, TEAM_DELAY_RANGE,
                    STRETCH_PAUSE_EVERY, STRETCH_PAUSE_RANGE
                )
        except ImportError:
            # Fallback defaults if settings not available
            STEALTH_REUSE_DRIVER = True
            STEALTH_STICKY_UA = True
            STEALTH_SAVE_DEBUG_HTML = False
            STEALTH_DEBUG_SAMPLE_EVERY = 25
            PLAYER_DELAY_RANGE = (0.8, 1.8)
            TEAM_DELAY_RANGE = (3.0, 5.0)
            STRETCH_PAUSE_EVERY = 25
            STRETCH_PAUSE_RANGE = (10.0, 15.0)
        
        self.settings = {
            'STEALTH_REUSE_DRIVER': STEALTH_REUSE_DRIVER,
            'STEALTH_STICKY_UA': STEALTH_STICKY_UA,
            'STEALTH_SAVE_DEBUG_HTML': STEALTH_SAVE_DEBUG_HTML,
            'STEALTH_DEBUG_SAMPLE_EVERY': STEALTH_DEBUG_SAMPLE_EVERY,
            'PLAYER_DELAY_RANGE': PLAYER_DELAY_RANGE,
            'TEAM_DELAY_RANGE': TEAM_DELAY_RANGE,
            'STRETCH_PAUSE_EVERY': STRETCH_PAUSE_EVERY,
            'STRETCH_PAUSE_RANGE': STRETCH_PAUSE_RANGE,
        }
        
        # Get User-Agent for this session
        self.ua = self._get_session_ua()
        
        logger.info(f"🚀 ScrapeContext initialized for {series_id}")
        logger.info(f"   Site: {site_hint}")
        logger.info(f"   Driver reuse: {self.settings['STEALTH_REUSE_DRIVER']}")
        logger.info(f"   Sticky UA: {self.settings['STEALTH_STICKY_UA']}")
    
    def _get_session_ua(self) -> str:
        """Get User-Agent for this session."""
        try:
            # Import UA manager
            try:
                from .user_agent_manager import UserAgentManager
            except ImportError:
                from user_agent_manager import UserAgentManager
            
            ua_mgr = UserAgentManager()
            
            if self.settings['STEALTH_STICKY_UA']:
                return ua_mgr.get_sticky_ua()
            else:
                return ua_mgr.get_user_agent_for_site(self.site_hint)
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to get UA, using fallback: {e}")
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def start_driver(self):
        """Start or reuse the driver for this context."""
        if self.driver and self.settings['STEALTH_REUSE_DRIVER']:
            logger.info(f"♻️ Reusing existing driver for {self.series_id}")
            return self.driver
        
        try:
            # Import stealth browser
            try:
                from .stealth_browser import EnhancedStealthBrowser, StealthConfig
            except ImportError:
                from stealth_browser import EnhancedStealthBrowser, StealthConfig
            
            # Create stealth browser with preferred UA
            config = StealthConfig(fast_mode=False, verbose=True, headless=True)
            self.browser = EnhancedStealthBrowser(config)
            self.driver = self.browser._create_driver(preferred_ua=self.ua)
            
            # Warmup request
            try:
                self.driver.get(self.site_hint)
                time.sleep(random.uniform(1.0, 3.0))
            except Exception as e:
                logger.warning(f"⚠️ Warmup request failed: {e}")
            
            logger.info(f"✅ Driver started for {self.series_id}")
            return self.driver
            
        except Exception as e:
            logger.error(f"❌ Failed to start driver: {e}")
            return None
    
    def stop_driver(self):
        """Stop and cleanup the driver."""
        if self.driver:
            with contextlib.suppress(Exception):
                self.driver.quit()
            logger.info(f"🛑 Driver stopped for {self.series_id}")
        
        self.driver = None
        self.browser = None
    
    def pause_between_players(self, index: int):
        """Add human-like pause between player requests."""
        # Base delay between players
        delay = random.uniform(*self.settings['PLAYER_DELAY_RANGE'])
        
        # Longer pause every N players
        if (self.settings['STRETCH_PAUSE_EVERY'] and 
            (index + 1) % self.settings['STRETCH_PAUSE_EVERY'] == 0):
            stretch_delay = random.uniform(*self.settings['STRETCH_PAUSE_RANGE'])
            delay += stretch_delay
            logger.info(f"😴 Stretch pause: {stretch_delay:.1f}s (after {index + 1} players)")
        
        logger.debug(f"⏱️ Player delay: {delay:.1f}s")
        time.sleep(delay)
    
    def pause_between_teams(self):
        """Add human-like pause between team processing."""
        delay = random.uniform(*self.settings['TEAM_DELAY_RANGE'])
        logger.debug(f"⏱️ Team delay: {delay:.1f}s")
        time.sleep(delay)
    
    def maybe_save_debug(self, html: str, success: bool, saver: Callable, name_hint: str, index: int):
        """
        Conditionally save debug HTML based on settings.
        
        Args:
            html: HTML content to potentially save
            success: Whether the request was successful
            saver: Function to call for saving (e.g., save_html)
            name_hint: Hint for filename
            index: Current item index
        """
        if not self.settings['STEALTH_SAVE_DEBUG_HTML']:
            return
        
        should_save = False
        filename_suffix = ""
        
        # Always save failures
        if not success:
            should_save = True
            filename_suffix = "failed"
        
        # Sample successful requests
        elif (self.settings['STEALTH_DEBUG_SAMPLE_EVERY'] and 
              index % self.settings['STEALTH_DEBUG_SAMPLE_EVERY'] == 0):
            should_save = True
            filename_suffix = f"sample_{index}"
        
        if should_save:
            try:
                filename = f"/tmp/{filename_suffix}_{name_hint}_{self.series_id}.html"
                saver(html, filename)
                logger.debug(f"💾 Saved debug HTML: {filename}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save debug HTML: {e}")
    
    def get_html_with_driver(self, url: str) -> str:
        """
        Get HTML content using the current driver.
        
        Args:
            url: URL to fetch
            
        Returns:
            str: HTML content
        """
        if not self.driver:
            logger.error("❌ No driver available - call start_driver() first")
            return ""
        
        try:
            self.driver.get(url)
            
            # Wait for page load
            time.sleep(random.uniform(2.0, 4.0))
            
            return self.driver.page_source
            
        except Exception as e:
            logger.error(f"❌ Failed to get HTML from {url}: {e}")
            return ""
    
    def __enter__(self):
        """Context manager entry."""
        self.start_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_driver()
    
    def get_session_stats(self) -> dict:
        """Get session statistics."""
        stats = {
            "series_id": self.series_id,
            "site_hint": self.site_hint,
            "user_agent": self.ua[:50] + "..." if len(self.ua) > 50 else self.ua,
            "driver_active": self.driver is not None,
            "settings": self.settings
        }
        
        # Add browser stats if available
        if self.browser and hasattr(self.browser, 'session_metrics'):
            browser_stats = self.browser.session_metrics.get_summary()
            stats.update({
                "browser_requests": browser_stats.get("browser_requests", 0),
                "success_rate": browser_stats.get("success_rate", 0),
                "proxy_rotations": browser_stats.get("proxy_rotations", 0)
            })
        
        return stats

# Convenience functions for backwards compatibility
def create_scrape_context(series_id: str, site_hint: str = "https://tenniscores.com/") -> ScrapeContext:
    """Create a new scrape context."""
    return ScrapeContext(series_id=series_id, site_hint=site_hint)

def with_driver_context(series_id: str, site_hint: str = "https://tenniscores.com/"):
    """Decorator for automatic driver context management."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with ScrapeContext(series_id=series_id, site_hint=site_hint) as ctx:
                return func(ctx, *args, **kwargs)
        return wrapper
    return decorator

# Example usage for backwards compatibility
if __name__ == "__main__":
    # Example of how to use the context manager
    with ScrapeContext("test_job", "https://aptachicago.tenniscores.com/") as ctx:
        # Simulate scraping some players
        test_urls = [
            "https://aptachicago.tenniscores.com/player.php?id=123",
            "https://aptachicago.tenniscores.com/player.php?id=456",
            "https://aptachicago.tenniscores.com/player.php?id=789"
        ]
        
        for i, url in enumerate(test_urls):
            html = ctx.get_html_with_driver(url)
            success = len(html) > 1000  # Simple success check
            
            # Mock save function
            def mock_save(content, filename):
                print(f"Would save {len(content)} chars to {filename}")
            
            ctx.maybe_save_debug(html, success, mock_save, "player", i)
            ctx.pause_between_players(i)
            
        print("Session stats:", ctx.get_session_stats())
