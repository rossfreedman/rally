#!/usr/bin/env python3
"""
Simple Decodo Proxy Test
========================

Basic test to verify Decodo proxy connectivity and functionality.
"""

import os
import requests
import json

def test_basic_proxy():
    """Test basic proxy connectivity."""
    print("🧪 Basic Decodo Proxy Test")
    print("=" * 40)
    
    # Set up credentials
    user = "sp2lv5ti3g"
    password = "zU0Pdl~7rcGqgxuM69"
    proxy_url = f"http://{user}:{password}@us.decodo.com:10001"
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    print(f"Proxy URL: {proxy_url}")
    print()
    
    # Test 1: Simple IP check
    print("1. Testing basic IP check...")
    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=30)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 2: IP geolocation
    print("2. Testing IP geolocation...")
    try:
        response = requests.get("https://ipapi.co/json", proxies=proxies, timeout=30)
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   IP: {data.get('ip')}")
        print(f"   Country: {data.get('country_name')} ({data.get('country_code')})")
        print(f"   City: {data.get('city')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # Test 3: Simple website access
    print("3. Testing simple website access...")
    try:
        response = requests.get("https://httpbin.org/get", proxies=proxies, timeout=30)
        print(f"   Status: {response.status_code}")
        print(f"   Success: {response.status_code == 200}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_basic_proxy() 