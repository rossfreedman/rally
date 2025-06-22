#!/usr/bin/env python3
"""
League Utilities
================

Centralized utilities for league ID normalization and standardization.
This ensures consistent league IDs across all data sources and systems.
"""

import re
from typing import Dict, Optional, Set

# Master league ID mappings - all variations should map to these canonical values
CANONICAL_LEAGUE_IDS = {
    "APTA_CHICAGO": "APTA_CHICAGO",
    "NSTF": "NSTF",
    "CITA": "CITA",
    "CNSWPL": "CNSWPL",
    "APTA_NATIONAL": "APTA_NATIONAL",
}

# Mapping of all known variations to canonical league IDs
LEAGUE_ID_MAPPINGS = {
    # APTA Chicago variations
    "apta_chicago": "APTA_CHICAGO",
    "aptachicago": "APTA_CHICAGO",
    "apta-chicago": "APTA_CHICAGO",
    "chicago": "APTA_CHICAGO",
    # NSTF variations
    "nstf": "NSTF",
    "nsft": "NSTF",  # This is the problematic one from series_stats
    "north_shore": "NSTF",
    "northshore": "NSTF",
    "north-shore": "NSTF",
    # CITA variations
    "cita": "CITA",
    # CNSWPL variations
    "cnswpl": "CNSWPL",
    "cns": "CNSWPL",
    "chicago_north_shore": "CNSWPL",
    # APTA National variations
    "apta_national": "APTA_NATIONAL",
    "aptanational": "APTA_NATIONAL",
    "apta-national": "APTA_NATIONAL",
    "national": "APTA_NATIONAL",
}


def normalize_league_id(league_id: Optional[str]) -> Optional[str]:
    """
    Normalize a league ID to the canonical format.

    Args:
        league_id: Raw league ID string (can be in any case/format)

    Returns:
        Canonical league ID or None if input is None/empty

    Examples:
        >>> normalize_league_id('nsft')
        'NSTF'
        >>> normalize_league_id('apta_chicago')
        'APTA_CHICAGO'
        >>> normalize_league_id('NSTF')
        'NSTF'
    """
    if not league_id:
        return None

    # Clean the input - remove extra whitespace, convert to lowercase
    cleaned = str(league_id).strip().lower()

    if not cleaned:
        return None

    # Check direct mapping first
    if cleaned in LEAGUE_ID_MAPPINGS:
        return LEAGUE_ID_MAPPINGS[cleaned]

    # Check if it's already a canonical value (case-insensitive)
    upper_cleaned = cleaned.upper()
    if upper_cleaned in CANONICAL_LEAGUE_IDS:
        return upper_cleaned

    # If no mapping found, return the uppercase version and log warning
    print(
        f"[WARNING] Unknown league ID '{league_id}' - using fallback: {upper_cleaned}"
    )
    return upper_cleaned


def validate_league_id(league_id: str) -> bool:
    """
    Check if a league ID is valid (maps to a known canonical league).

    Args:
        league_id: League ID to validate

    Returns:
        True if the league ID is valid, False otherwise
    """
    normalized = normalize_league_id(league_id)
    return normalized in CANONICAL_LEAGUE_IDS


def get_all_known_league_ids() -> Set[str]:
    """
    Get all known league ID variations.

    Returns:
        Set of all known league ID strings (variations + canonical)
    """
    all_ids = set(LEAGUE_ID_MAPPINGS.keys())
    all_ids.update(CANONICAL_LEAGUE_IDS.keys())
    return all_ids


def get_canonical_league_ids() -> Set[str]:
    """
    Get the set of canonical league IDs.

    Returns:
        Set of canonical league ID strings
    """
    return set(CANONICAL_LEAGUE_IDS.keys())


def get_league_display_name(league_id: str) -> str:
    """
    Get the human-readable display name for a league.

    Args:
        league_id: League ID (will be normalized first)

    Returns:
        Human-readable league name
    """
    normalized = normalize_league_id(league_id)

    display_names = {
        "NSTF": "North Shore Tennis Foundation",
        "APTA_CHICAGO": "APTA Chicago",
        "APTA_NATIONAL": "APTA National",
        "CITA": "CITA",
        "CNSWPL": "Chicago North Shore Women's Platform Tennis League",
    }

    return display_names.get(normalized, normalized or "Unknown League")


def get_league_url(league_id: str) -> str:
    """
    Get the official URL for a league.

    Args:
        league_id: League ID (will be normalized first)

    Returns:
        League URL or empty string if unknown
    """
    normalized = normalize_league_id(league_id)

    urls = {
        "NSTF": "https://nstf.org/",
        "APTA_CHICAGO": "https://aptachicago.tenniscores.com/",
        "APTA_NATIONAL": "https://apta.tenniscores.com/",
        "CITA": "",
        "CNSWPL": "https://cnswpl.tenniscores.com/",
    }

    return urls.get(normalized, "")


# Legacy compatibility functions for existing scrapers
def standardize_league_id(subdomain: str) -> str:
    """
    Legacy compatibility function for scrapers.
    Maps subdomain to standardized league ID.

    Args:
        subdomain: The subdomain (e.g., 'aptachicago', 'nstf')

    Returns:
        Standardized league ID (e.g., 'APTA_CHICAGO', 'NSTF')
    """
    return normalize_league_id(subdomain) or subdomain.upper()
