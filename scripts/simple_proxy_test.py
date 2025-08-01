#!/usr/bin/env python3

"""
Simple test to check ScraperAPI US proxy functionality
"""

import os
import requests
import time

def test_direct_scraperapi():
    """Test ScraperAPI directly with different configurations"""
    
    api_key = os.getenv("SCRAPERAPI_KEY")
    if not api_key:
        print("❌ SCRAPERAPI_KEY not found")
        return
    
    print("🔍 Testing ScraperAPI US Proxy Configurations")
    print("=" * 50)
    
    # Test different configurations
    test_configs = [
        ("Basic US", f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us"),
        ("US with region", f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&region=us"),
        ("US Premium", f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&premium=true"),
        ("US Session", f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&session_number=1"),
        ("US Keep-alive", f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&keep_alive=true"),
    ]
    
    for config_name, url in test_configs:
        print(f"\n🧪 Testing: {config_name}")
        print(f"🔗 URL: {url[:80]}...")
        
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                ip_data = response.json()
                ip_address = ip_data.get('origin', 'Unknown')
                print(f"✅ IP: {ip_address}")
                
                # Check geolocation
                try:
                    geo_response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10)
                    if geo_response.status_code == 200:
                        geo_data = geo_response.json()
                        country = geo_data.get('country_name', 'Unknown')
                        country_code = geo_data.get('country_code', 'Unknown')
                        print(f"🌍 Location: {country} ({country_code})")
                        
                        if country_code == 'US':
                            print(f"✅ SUCCESS: {config_name} provides US-based IP!")
                            return config_name, url
                        else:
                            print(f"❌ FAILED: {config_name} provides {country_code}-based IP")
                    else:
                        print(f"⚠️ Could not verify location (Status: {geo_response.status_code})")
                except Exception as geo_error:
                    print(f"⚠️ Geolocation check failed: {geo_error}")
            else:
                print(f"❌ HTTP API failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)  # Brief pause between tests
    
    print("\n❌ No US-based proxy configurations found!")
    return None

def check_scraperapi_account():
    """Check ScraperAPI account status"""
    print("\n📊 Checking ScraperAPI Account Status")
    print("=" * 40)
    
    api_key = os.getenv("SCRAPERAPI_KEY")
    if not api_key:
        print("❌ SCRAPERAPI_KEY not found")
        return
    
    try:
        # Test basic connectivity
        test_url = f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ ScraperAPI connectivity: OK")
            ip_data = response.json()
            ip_address = ip_data.get('origin', 'Unknown')
            print(f"📡 Current IP: {ip_address}")
            
            # Check geolocation
            geo_response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10)
            if geo_response.status_code == 200:
                geo_data = geo_response.json()
                country = geo_data.get('country_name', 'Unknown')
                country_code = geo_data.get('country_code', 'Unknown')
                print(f"🌍 Current Location: {country} ({country_code})")
                
                if country_code != 'US':
                    print(f"⚠️ WARNING: Current IP is {country_code}-based, not US-based")
                    print("💡 This suggests ScraperAPI may not have US proxy access")
                else:
                    print("✅ Current IP is US-based")
            else:
                print("⚠️ Could not verify current IP location")
        else:
            print(f"❌ ScraperAPI connectivity failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ ScraperAPI connectivity error: {e}")

if __name__ == "__main__":
    check_scraperapi_account()
    working_config = test_direct_scraperapi()
    
    if working_config:
        config_name, url = working_config
        print(f"\n🎉 SOLUTION FOUND!")
        print(f"Use this configuration: {config_name}")
        print(f"URL pattern: {url}")
    else:
        print(f"\n💡 RECOMMENDATIONS:")
        print("1. Check if your ScraperAPI account has US proxy access")
        print("2. Consider upgrading to a premium plan")
        print("3. Contact ScraperAPI support about US proxy availability")
        print("4. Try using a different proxy service") 