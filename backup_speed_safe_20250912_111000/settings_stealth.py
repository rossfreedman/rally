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
MAX_REQUESTS_PER_DRIVER = 100

# Maximum driver session duration (seconds)
MAX_DRIVER_SESSION_DURATION = 1800  # 30 minutes

# Batch size for processing multiple items
DEFAULT_BATCH_SIZE = 50

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
