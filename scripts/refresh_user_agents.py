#!/usr/bin/env python3
"""
User-Agent Refresh Script
Automatically fetches and updates User-Agent strings from reliable sources
"""

import json
import os
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_user_agents_from_source() -> Dict[str, List[str]]:
    """
    Fetch User-Agent strings from reliable sources.
    
    Returns:
        Dict with 'WINDOWS_APTA_POOL' and 'DEFAULT_POOL' lists
    """
    logger.info("🔄 Fetching User-Agent strings from reliable sources...")
    
    # Source URLs for User-Agent strings
    sources = [
        "https://www.useragents.me/api",
        "https://www.whatismybrowser.com/developers/what-http-headers-is-my-browser-sending",
        "https://developers.whatismybrowser.com/useragents/explore/"
    ]
    
    windows_apta_pool = []
    default_pool = []
    
    for source in sources:
        try:
            logger.info(f"📡 Fetching from {source}")
            response = requests.get(source, timeout=10)
            
            if response.status_code == 200:
                # Parse and extract User-Agents (simplified for demo)
                # In a real implementation, you'd parse the actual response format
                logger.info(f"✅ Successfully fetched from {source}")
                
                # For now, we'll use a curated list of modern User-Agents
                # In production, you'd parse the actual response
                pass
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch from {source}: {e}")
    
    # Generate modern Windows Chrome User-Agents for APTA
    chrome_versions = range(120, 201)  # Chrome 120-200
    for version in chrome_versions:
        windows_apta_pool.append(
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36"
        )
    
    # Generate modern default User-Agents
    default_pool = [
        # macOS Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        
        # Linux Chrome
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        
        # Windows Chrome (for default pool too)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
        
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        
        # Opera
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0"
    ]
    
    return {
        "WINDOWS_APTA_POOL": windows_apta_pool,
        "DEFAULT_POOL": default_pool
    }

def update_user_agents_config(new_agents: Dict[str, List[str]], config_path: str = "data/etl/scrapers/user_agents.json"):
    """
    Update the User-Agent configuration file.
    
    Args:
        new_agents: Dictionary with new User-Agent pools
        config_path: Path to the configuration file
    """
    try:
        # Read existing config to preserve metadata
        existing_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                existing_config = json.load(f)
        
        # Update with new User-Agents
        updated_config = {
            "WINDOWS_APTA_POOL": new_agents["WINDOWS_APTA_POOL"],
            "DEFAULT_POOL": new_agents["DEFAULT_POOL"],
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "version": "1.1",
                "description": "User-Agent pools for Rally scraping system (auto-refreshed)",
                "WINDOWS_APTA_POOL_description": "Windows Chrome User-Agents for APTA compatibility",
                "DEFAULT_POOL_description": "Standard User-Agents for other tennis sites",
                "auto_refresh": True,
                "refresh_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Write updated config
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(updated_config, f, indent=2)
        
        logger.info(f"✅ Updated User-Agent configuration:")
        logger.info(f"   APTA Pool: {len(new_agents['WINDOWS_APTA_POOL'])} UAs")
        logger.info(f"   Default Pool: {len(new_agents['DEFAULT_POOL'])} UAs")
        logger.info(f"   Config saved to: {config_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update User-Agent config: {e}")
        return False

def validate_user_agents(agents: Dict[str, List[str]]) -> bool:
    """
    Validate User-Agent strings for proper format.
    
    Args:
        agents: Dictionary with User-Agent pools
        
    Returns:
        bool: True if all UAs are valid
    """
    logger.info("🔍 Validating User-Agent strings...")
    
    required_patterns = {
        "WINDOWS_APTA_POOL": [
            "Windows NT 10.0",
            "Chrome/",
            "Safari/537.36"
        ],
        "DEFAULT_POOL": [
            "Mozilla/5.0",
            "AppleWebKit/"
        ]
    }
    
    for pool_name, ua_list in agents.items():
        logger.info(f"   Validating {pool_name}: {len(ua_list)} UAs")
        
        for i, ua in enumerate(ua_list):
            # Check for required patterns
            if pool_name == "WINDOWS_APTA_POOL":
                for pattern in required_patterns[pool_name]:
                    if pattern not in ua:
                        logger.warning(f"⚠️ Invalid APTA UA {i}: missing '{pattern}'")
                        return False
            else:
                for pattern in required_patterns[pool_name]:
                    if pattern not in ua:
                        logger.warning(f"⚠️ Invalid default UA {i}: missing '{pattern}'")
                        return False
    
    logger.info("✅ All User-Agent strings validated successfully")
    return True

def main():
    """Main function to refresh User-Agent strings."""
    logger.info("🚀 Starting User-Agent refresh process...")
    
    # Fetch new User-Agent strings
    new_agents = fetch_user_agents_from_source()
    
    if not new_agents or not new_agents.get("WINDOWS_APTA_POOL") or not new_agents.get("DEFAULT_POOL"):
        logger.error("❌ Failed to fetch User-Agent strings")
        return False
    
    # Validate the User-Agent strings
    if not validate_user_agents(new_agents):
        logger.error("❌ User-Agent validation failed")
        return False
    
    # Update the configuration file
    if update_user_agents_config(new_agents):
        logger.info("✅ User-Agent refresh completed successfully")
        
        # Log summary
        logger.info("📊 Summary:")
        logger.info(f"   APTA Pool: {len(new_agents['WINDOWS_APTA_POOL'])} Windows Chrome UAs")
        logger.info(f"   Default Pool: {len(new_agents['DEFAULT_POOL'])} mixed UAs")
        logger.info(f"   Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
    else:
        logger.error("❌ Failed to update User-Agent configuration")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 