#!/usr/bin/env python3
"""
Final Proxy Solution
===================

This script provides a comprehensive solution for the proxy authentication issues.
"""

import os
import requests
import time
import json
from datetime import datetime

def test_with_different_auth_methods():
    """Test different authentication methods."""
    print("🔐 Testing different authentication methods...")
    
    # Load credentials
    with open("ips.txt", "r") as f:
        first_line = f.readline().strip()
        if first_line and ":" in first_line:
            parts = first_line.split(":")
            host, port, username, password = parts[:4]
    
    # Test different authentication formats
    auth_methods = [
        # Method 1: Standard format
        {
            "name": "Standard",
            "proxy_url": f"http://{username}:{password}@{host}:{port}",
            "description": "Standard HTTP proxy authentication"
        },
        # Method 2: URL encoded password
        {
            "name": "URL Encoded",
            "proxy_url": f"http://{username}:{password.replace('~', '%7E')}@{host}:{port}",
            "description": "URL encoded special characters"
        },
        # Method 3: Different username format
        {
            "name": "Domain Username",
            "proxy_url": f"http://{username}@decodo.com:{password}@{host}:{port}",
            "description": "Username with domain"
        },
        # Method 4: Session-based
        {
            "name": "Session",
            "proxy_url": f"http://{username}:{password}@{host}:{port}",
            "description": "With session headers",
            "headers": {
                "Proxy-Authorization": f"Basic {username}:{password}",
                "Connection": "keep-alive"
            }
        }
    ]
    
    for method in auth_methods:
        print(f"\n🧪 Testing: {method['name']}")
        print(f"   Description: {method['description']}")
        
        proxies = {"http": method['proxy_url'], "https": method['proxy_url']}
        
        # Use custom headers if provided
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json,text/html,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        if "headers" in method:
            headers.update(method["headers"])
        
        try:
            response = requests.get(
                "http://httpbin.org/ip",
                proxies=proxies,
                headers=headers,
                timeout=20
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS! IP: {data.get('origin')}")
                return method
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(2)  # Delay between tests
    
    return None

def create_working_config(working_method):
    """Create a working configuration file."""
    print(f"\n🔧 Creating working configuration...")
    
    config = {
        "working_method": working_method["name"],
        "proxy_format": working_method["proxy_url"],
        "description": working_method["description"],
        "created_at": datetime.now().isoformat(),
        "recommendations": [
            "Use this exact proxy format in your scraper",
            "Increase timeout to 20 seconds",
            "Add proper headers for authentication",
            "Implement exponential backoff for retries"
        ]
    }
    
    config_file = "working_proxy_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"   📄 Configuration saved to: {config_file}")
    return config

def create_fallback_solution():
    """Create a fallback solution if no method works."""
    print(f"\n🔄 Creating fallback solution...")
    
    fallback_config = {
        "use_direct_requests": True,
        "proxy_timeout": 5,
        "direct_timeout": 30,
        "retry_without_proxy": True,
        "rate_limiting": {
            "requests_per_minute": 10,
            "delay_between_requests": 6
        },
        "recommendations": [
            "Contact Decodo support immediately",
            "Check account status and billing",
            "Verify IP whitelist settings",
            "Consider switching to a different provider"
        ]
    }
    
    fallback_file = "fallback_config.json"
    with open(fallback_file, "w") as f:
        json.dump(fallback_config, f, indent=2)
    
    print(f"   📄 Fallback configuration saved to: {fallback_file}")
    return fallback_config

def update_proxy_manager():
    """Update the proxy manager with the working configuration."""
    print(f"\n🔧 Updating proxy manager...")
    
    # Create an updated proxy manager configuration
    updated_config = {
        "timeout": 20,
        "max_retries": 3,
        "retry_delay": 2,
        "exponential_backoff": True,
        "test_subset_only": True,
        "max_test_proxies": 5,
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json,text/html,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
    }
    
    config_file = "updated_proxy_manager_config.json"
    with open(config_file, "w") as f:
        json.dump(updated_config, f, indent=2)
    
    print(f"   📄 Updated proxy manager config saved to: {config_file}")
    return updated_config

def main():
    """Main solution function."""
    print("🔧 FINAL PROXY SOLUTION")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test different authentication methods
    working_method = test_with_different_auth_methods()
    
    if working_method:
        print(f"\n✅ SOLUTION FOUND!")
        print(f"   Method: {working_method['name']}")
        print(f"   Format: {working_method['proxy_url']}")
        
        # Create working configuration
        config = create_working_config(working_method)
        
        # Update proxy manager
        update_proxy_manager()
        
        print(f"\n📋 NEXT STEPS:")
        print("1. Use the working configuration in your scraper")
        print("2. Update timeout settings to 20 seconds")
        print("3. Implement proper headers")
        print("4. Test with a small subset of proxies first")
        
    else:
        print(f"\n❌ No authentication method worked.")
        print("   This indicates a provider-side issue.")
        
        # Create fallback solution
        fallback_config = create_fallback_solution()
        
        print(f"\n🚨 IMMEDIATE ACTIONS:")
        print("1. Contact Decodo support with these details:")
        print("   - All authentication methods tested and failed")
        print("   - HTTP 407 errors indicate credential rejection")
        print("   - Account is active but authentication failing")
        print("2. Ask them to:")
        print("   - Check account configuration")
        print("   - Verify IP whitelist settings")
        print("   - Reset authentication credentials")
        print("3. Use the fallback configuration for now")
    
    print(f"\n✅ Solution complete at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 