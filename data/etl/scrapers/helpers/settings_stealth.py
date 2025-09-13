#!/usr/bin/env python3
"""
Stealth & Efficiency Configuration for Rally Scrapers
=====================================================

Central configuration for all stealth and efficiency settings across Rally's scrapers.
This file controls driver reuse, User-Agent management, debug output, proxy behavior,
and human-like pacing patterns.

Usage:
    # Circular import - these are defined in this file
    
Key Features:
- Driver reuse for efficiency
- Sticky User-Agent management
- Selective debug HTML saving  
- Smart proxy management
- Human-like delay patterns
- Consistent viewport and language settings
"""

# ==============================================================================
# DRIVER MANAGEMENT
# ==============================================================================

# Reuse single driver per series/job instead of creating new driver per player
STEALTH_REUSE_DRIVER = True

# Use sticky Windows-Chrome User-Agent across HTTP + Selenium for *.tenniscores.com
STEALTH_STICKY_UA = True

# ==============================================================================
# DEBUG & LOGGING
# ==============================================================================

# Save debug HTML files (set to False to disable completely)
STEALTH_SAVE_DEBUG_HTML = False

# When debug saving is enabled, save sample every N requests (reduces storage)
STEALTH_DEBUG_SAMPLE_EVERY = 25

# ==============================================================================
# BROWSER SETTINGS
# ==============================================================================

# Standard viewport size for consistency (Windows-like)
STEALTH_VIEWPORT = (1366, 768)

# Timezone for consistent fingerprinting
STEALTH_TIMEZONE = "America/Chicago"

# Language settings
STEALTH_LANG = "en-US"
HTTP_ACCEPT_LANGUAGE = "en-US,en;q=0.9"

# ==============================================================================
# PROXY MANAGEMENT
# ==============================================================================

# Test proxy against target homepage before use
PROXY_TEST_TARGET = False

# Use sticky proxy sessions per series for better performance
PROXY_STICKY_BY_SERIES = True

# Only retire proxies on hard blocks (captcha, access denied), not soft fails
PROXY_RETIRE_ON_HARD_BLOCKS_ONLY = True

# ==============================================================================
# HUMAN-LIKE PACING
# ==============================================================================

# Delays between individual player requests (seconds)
PLAYER_DELAY_RANGE = (0.8, 1.8)

# Delays between team processing (seconds)
TEAM_DELAY_RANGE = (3.0, 5.0)

# Take a longer pause every N players to mimic human breaks
STRETCH_PAUSE_EVERY = 25
STRETCH_PAUSE_RANGE = (10.0, 15.0)

# ==============================================================================
# HARD BLOCK DETECTION PATTERNS
# ==============================================================================

# Patterns that indicate hard blocks requiring proxy retirement
HARD_BLOCK_PATTERNS = [
    "captcha",
    "access denied", 
    "forbidden",
    "cloudflare",
    "just a moment",
    "bot detection",
    "blocked",
    "ray id",
    "challenge",
    "checking your browser"
]

# ==============================================================================
# TENNISCORES SITE DETECTION
# ==============================================================================

# All *.tenniscores.com sites should use Windows-Chrome UA
TENNISCORES_DOMAINS = [
    "aptachicago.tenniscores.com",
    "cnswpl.tenniscores.com", 
    "nstf.tenniscores.com",
    "cita.tenniscores.com",
    "tenniscores.com"
]

# ==============================================================================
# EFFICIENCY SETTINGS  
# ==============================================================================

# Maximum number of requests per driver before rotation
MAX_REQUESTS_PER_DRIVER = 200  # Increased from 100 (2x more efficient)

# Maximum driver session duration (seconds)
MAX_DRIVER_SESSION_DURATION = 3600  # 60 minutes (2x longer sessions)

# Batch size for processing multiple items
DEFAULT_BATCH_SIZE = 50

# ==============================================================================
# COST OPTIMIZATION SETTINGS
# ==============================================================================

# Proxy rotation settings for cost optimization
PROXY_REQUESTS_PER_ROTATION = 100  # Rotate every 100 requests (vs 15)
PROXY_SESSION_DURATION = 1800  # 30 minutes per proxy session
PROXY_USAGE_CAP = 200  # Max requests per proxy per session

# Cost tracking
TRACK_PROXY_COSTS = True
MAX_COST_PER_HOUR = 50.0  # Alert if exceeding $50/hour
COST_PER_REQUEST = 0.001  # Estimated cost per request

# ==============================================================================
# SPEED OPTIMIZATION SETTINGS
# ==============================================================================

# Aggressive delay reduction for speed
TEAM_DELAY_MIN = 0.3  # Reduced from 3.0
TEAM_DELAY_MAX = 1.2  # Reduced from 5.0
SERIES_DELAY_MIN = 1.0  # Reduced from 5.0
SERIES_DELAY_MAX = 2.5  # Reduced from 9.0

# Adaptive delay thresholds
HIGH_SUCCESS_THRESHOLD = 0.98  # 98%+ success = very fast
GOOD_SUCCESS_THRESHOLD = 0.95  # 95%+ success = fast
MODERATE_SUCCESS_THRESHOLD = 0.90  # 90%+ success = moderate

# Speed multipliers
VERY_FAST_MULTIPLIER = 0.3  # 30% of base delay
FAST_MULTIPLIER = 0.6  # 60% of base delay
MODERATE_MULTIPLIER = 0.8  # 80% of base delay
CONSERVATIVE_MULTIPLIER = 1.2  # 120% of base delay

# ==============================================================================
# PARALLEL PROCESSING SETTINGS
# ==============================================================================

# Enable parallel team processing
ENABLE_PARALLEL_PROCESSING = True

# Number of parallel workers for team processing
PARALLEL_WORKERS = 4  # Process 4 teams simultaneously

# Batch size for parallel processing
PARALLEL_BATCH_SIZE = 5  # Process teams in batches of 5

# Delay between parallel batches (instead of between individual teams)
PARALLEL_BATCH_DELAY = 0.5  # 0.5 seconds between batches

# Maximum retries for parallel requests
PARALLEL_MAX_RETRIES = 2

# Timeout for parallel requests
PARALLEL_TIMEOUT = 30  # 30 seconds per team request

# ==============================================================================
# FALLBACK SETTINGS
# ==============================================================================

# Fallback settings if stealth features fail
FALLBACK_TO_BASIC_MODE = True
FALLBACK_DELAY_RANGE = (2.0, 4.0)
FALLBACK_VIEWPORT = (1920, 1080)

# ==============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# ==============================================================================

import os

# Allow environment-specific overrides
if os.getenv("RALLY_FAST_MODE"):
    PLAYER_DELAY_RANGE = (0.3, 0.8)
    TEAM_DELAY_RANGE = (1.0, 2.0)
    STRETCH_PAUSE_EVERY = 50

if os.getenv("RALLY_DEBUG_MODE"):
    STEALTH_SAVE_DEBUG_HTML = True
    STEALTH_DEBUG_SAMPLE_EVERY = 5

# Production safety overrides
if os.getenv("RAILWAY_ENVIRONMENT") == "production":
    # More conservative settings in production
    PLAYER_DELAY_RANGE = (1.2, 2.5)
    TEAM_DELAY_RANGE = (4.0, 7.0)
    STRETCH_PAUSE_EVERY = 20
    MAX_REQUESTS_PER_DRIVER = 75

# ==============================================================================
# SPEED OPTIMIZATIONS (SAFE TO TOGGLE)
# ==============================================================================

# Master switch for eager page loads, CDP blocking, and stop-early features
ENABLE_SPEED_OPTIMIZATIONS = True

# Selector that indicates page is ready for scraping (adjust per page type)
# Conservative default - only used if optimizations enabled
READY_SELECTOR = "table.roster"  # Common selector for roster pages

# Selector method: 'css' or 'xpath'
READY_SELECTOR_BY = "css"

# Timeout for waiting for ready selector (seconds)
READY_SELECTOR_TIMEOUT = 12

# Alternative selectors for different page types
READY_SELECTORS_BY_PAGE = {
    "roster": "table.roster",
    "player": ".player-info, .career-stats",
    "team": ".team-info, .team-stats",
    "schedule": ".schedule-table, table[class*='schedule']"
}
