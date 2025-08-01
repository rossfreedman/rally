#!/usr/bin/env python3
"""
Research script to test different ScraperAPI configurations for forcing US-based IPs.
Based on ScraperAPI documentation and best practices.
"""

import os
import sys
import requests
import json
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_scraperapi_http_api(api_key):
    """Test ScraperAPI HTTP API with different US configurations."""
    print("🔍 Testing ScraperAPI HTTP API Configurations")
    print("=" * 60)
    
    # Test different HTTP API configurations for US IPs
    test_configs = [
        {
            "name": "Basic US",
            "url": f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us",
            "description": "Basic US country code"
        },
        {
            "name": "US with Region",
            "url": f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&region=us",
            "description": "US country code with region specification"
        },
        {
            "name": "US Premium",
            "url": f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&premium=true",
            "description": "US with premium proxies"
        },
        {
            "name": "US Session",
            "url": f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&session_number=1",
            "description": "US with session management"
        },
        {
            "name": "US Keep-alive",
            "url": f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&keep_alive=true",
            "description": "US with keep-alive connections"
        },
        {
            "name": "US Premium + Session",
            "url": f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&premium=true&session_number=1",
            "description": "US premium with session management"
        },
        {
            "name": "US Residential",
            "url": f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&residential=true",
            "description": "US residential proxies"
        },
        {
            "name": "US Datacenter",
            "url": f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip&country_code=us&datacenter=true",
            "description": "US datacenter proxies"
        }
    ]
    
    results = []
    
    for config in test_configs:
        print(f"\n🔍 Testing: {config['name']}")
        print(f"   Description: {config['description']}")
        
        try:
            response = requests.get(config['url'], timeout=30)
            
            if response.status_code == 200:
                try:
                    ip_data = json.loads(response.text)
                    ip_address = ip_data.get('origin', 'Unknown')
                    print(f"   ✅ Success - IP: {ip_address}")
                    
                    # Check if IP is US-based
                    try:
                        geo_response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10)
                        if geo_response.status_code == 200:
                            geo_data = geo_response.json()
                            country = geo_data.get('country_name', 'Unknown')
                            country_code = geo_data.get('country_code', 'Unknown')
                            region = geo_data.get('region', 'Unknown')
                            city = geo_data.get('city', 'Unknown')
                            
                            print(f"   📍 Location: {city}, {region}, {country} ({country_code})")
                            
                            is_us = country_code == 'US'
                            results.append({
                                'config': config['name'],
                                'ip': ip_address,
                                'country': country,
                                'country_code': country_code,
                                'region': region,
                                'city': city,
                                'is_us': is_us,
                                'success': True
                            })
                            
                            if is_us:
                                print(f"   ✅ US-based IP confirmed!")
                            else:
                                print(f"   ⚠️ Non-US IP detected")
                        else:
                            print(f"   ⚠️ Could not verify IP location")
                            results.append({
                                'config': config['name'],
                                'ip': ip_address,
                                'success': True,
                                'is_us': 'Unknown'
                            })
                            
                    except Exception as geo_e:
                        print(f"   ⚠️ IP geolocation check failed: {str(geo_e)}")
                        results.append({
                            'config': config['name'],
                            'ip': ip_address,
                            'success': True,
                            'is_us': 'Unknown'
                        })
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON response: {response.text[:100]}...")
                    results.append({
                        'config': config['name'],
                        'success': False,
                        'error': 'Invalid JSON response'
                    })
            else:
                print(f"   ❌ Failed - Status: {response.status_code}")
                results.append({
                    'config': config['name'],
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                })
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({
                'config': config['name'],
                'success': False,
                'error': str(e)
            })
    
    return results

def test_scraperapi_proxy_endpoints(api_key):
    """Test ScraperAPI proxy endpoints for US IPs."""
    print("\n🔍 Testing ScraperAPI Proxy Endpoints")
    print("=" * 60)
    
    # Test different proxy endpoint configurations
    proxy_configs = [
        {
            "name": "US Standard",
            "proxy_url": f"http://scraperapi-country-us:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "Standard US proxy"
        },
        {
            "name": "US Premium",
            "proxy_url": f"http://scraperapi-premium-country-us:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "Premium US proxy"
        },
        {
            "name": "US East",
            "proxy_url": f"http://scraperapi-country-us-east:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "US East region proxy"
        },
        {
            "name": "US West",
            "proxy_url": f"http://scraperapi-country-us-west:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "US West region proxy"
        },
        {
            "name": "US Central",
            "proxy_url": f"http://scraperapi-country-us-central:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "US Central region proxy"
        },
        {
            "name": "US Session",
            "proxy_url": f"http://scraperapi-country-us-session:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "US proxy with session management"
        },
        {
            "name": "US Keep-alive",
            "proxy_url": f"http://scraperapi-country-us-keep-alive:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "US proxy with keep-alive"
        },
        {
            "name": "US Residential",
            "proxy_url": f"http://scraperapi-residential-country-us:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "US residential proxy"
        },
        {
            "name": "US Datacenter",
            "proxy_url": f"http://scraperapi-datacenter-country-us:{api_key}@proxy-server.scraperapi.com:8001",
            "description": "US datacenter proxy"
        }
    ]
    
    results = []
    
    for config in proxy_configs:
        print(f"\n🔍 Testing: {config['name']}")
        print(f"   Description: {config['description']}")
        
        try:
            proxies = {
                'http': config['proxy_url'],
                'https': config['proxy_url']
            }
            
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxies,
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    ip_data = response.json()
                    ip_address = ip_data.get('origin', 'Unknown')
                    print(f"   ✅ Success - IP: {ip_address}")
                    
                    # Check if IP is US-based
                    try:
                        geo_response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10)
                        if geo_response.status_code == 200:
                            geo_data = geo_response.json()
                            country = geo_data.get('country_name', 'Unknown')
                            country_code = geo_data.get('country_code', 'Unknown')
                            region = geo_data.get('region', 'Unknown')
                            city = geo_data.get('city', 'Unknown')
                            
                            print(f"   📍 Location: {city}, {region}, {country} ({country_code})")
                            
                            is_us = country_code == 'US'
                            results.append({
                                'config': config['name'],
                                'ip': ip_address,
                                'country': country,
                                'country_code': country_code,
                                'region': region,
                                'city': city,
                                'is_us': is_us,
                                'success': True
                            })
                            
                            if is_us:
                                print(f"   ✅ US-based IP confirmed!")
                            else:
                                print(f"   ⚠️ Non-US IP detected")
                        else:
                            print(f"   ⚠️ Could not verify IP location")
                            results.append({
                                'config': config['name'],
                                'ip': ip_address,
                                'success': True,
                                'is_us': 'Unknown'
                            })
                            
                    except Exception as geo_e:
                        print(f"   ⚠️ IP geolocation check failed: {str(geo_e)}")
                        results.append({
                            'config': config['name'],
                            'ip': ip_address,
                            'success': True,
                            'is_us': 'Unknown'
                        })
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON response: {response.text[:100]}...")
                    results.append({
                        'config': config['name'],
                        'success': False,
                        'error': 'Invalid JSON response'
                    })
            else:
                print(f"   ❌ Failed - Status: {response.status_code}")
                results.append({
                    'config': config['name'],
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                })
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({
                'config': config['name'],
                'success': False,
                'error': str(e)
            })
    
    return results

def test_tennis_site_access(api_key, working_configs):
    """Test access to tennis scores site with working US configurations."""
    print("\n🎾 Testing Tennis Scores Site Access")
    print("=" * 60)
    
    tennis_site = "https://nstf.tenniscores.com"
    results = []
    
    for config in working_configs:
        if not config.get('is_us', False):
            continue
            
        print(f"\n🔍 Testing tennis site with: {config['config']}")
        
        try:
            # Test with HTTP API first
            api_url = f"http://api.scraperapi.com?api_key={api_key}&url={tennis_site}&country_code=us&premium=true"
            response = requests.get(api_url, timeout=30)
            
            if response.status_code == 200:
                print(f"   ✅ HTTP API access successful")
                print(f"   📄 Content length: {len(response.text)} characters")
                
                # Check for tennis-related content
                if any(keyword in response.text.lower() for keyword in ['tennis', 'scores', 'matches', 'players']):
                    print(f"   🎾 Tennis content detected!")
                    results.append({
                        'config': config['config'],
                        'method': 'HTTP API',
                        'success': True,
                        'content_length': len(response.text)
                    })
                else:
                    print(f"   ⚠️ No tennis content detected")
                    results.append({
                        'config': config['config'],
                        'method': 'HTTP API',
                        'success': True,
                        'content_length': len(response.text),
                        'note': 'No tennis content'
                    })
            else:
                print(f"   ❌ HTTP API failed - Status: {response.status_code}")
                results.append({
                    'config': config['config'],
                    'method': 'HTTP API',
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                })
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({
                'config': config['config'],
                'method': 'HTTP API',
                'success': False,
                'error': str(e)
            })
    
    return results

def generate_recommendations(http_results, proxy_results, tennis_results):
    """Generate recommendations based on test results."""
    print("\n📊 ANALYSIS AND RECOMMENDATIONS")
    print("=" * 60)
    
    # Find working US configurations
    working_us_configs = []
    
    for result in http_results + proxy_results:
        if result.get('success') and result.get('is_us'):
            working_us_configs.append(result)
    
    print(f"✅ Found {len(working_us_configs)} working US-based configurations:")
    for config in working_us_configs:
        print(f"   - {config['config']}: {config['ip']} ({config['city']}, {config['region']})")
    
    # Find tennis site access
    tennis_access = [r for r in tennis_results if r.get('success')]
    print(f"\n🎾 Tennis site access: {len(tennis_access)} successful configurations")
    
    # Generate recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    if working_us_configs:
        best_config = working_us_configs[0]  # First working config
        print(f"   1. Use configuration: {best_config['config']}")
        print(f"      IP: {best_config['ip']}")
        print(f"      Location: {best_config['city']}, {best_config['region']}")
        
        if tennis_access:
            print(f"   2. Tennis site access confirmed with US IP")
            print(f"   3. Ready to run scraper with US-based proxy")
        else:
            print(f"   2. Tennis site access needs verification")
            print(f"   3. Test scraper with US proxy configuration")
    else:
        print("   ❌ No working US-based configurations found")
        print("   🔧 Check ScraperAPI account and plan")
        print("   📞 Contact ScraperAPI support if needed")
    
    # Create configuration file
    if working_us_configs:
        create_optimal_config(working_us_configs[0])

def create_optimal_config(best_config):
    """Create optimal configuration file based on best working config."""
    print(f"\n🔧 Creating optimal configuration...")
    
    config_content = f"""# Optimal ScraperAPI Configuration
# Based on testing results: {best_config['config']}
# IP: {best_config['ip']} ({best_config['city']}, {best_config['region']})

# ScraperAPI Configuration
SCRAPERAPI_KEY=${{SCRAPERAPI_KEY}}
SCRAPERAPI_REGION=us-premium
REQUIRE_PROXY=true

# Optimal Settings
SCRAPERAPI_USE_PREMIUM=true
SCRAPERAPI_USE_SESSION=true
SCRAPERAPI_USE_KEEP_ALIVE=false

# Scraper Configuration
HEADLESS_MODE=true
MAX_RETRIES=3
REQUEST_TIMEOUT=60

# Chrome Configuration
CHROMEDRIVER_PATH=

# Usage Instructions:
# 1. Set your API key: export SCRAPERAPI_KEY=your_key_here
# 2. Run scraper: python3 data/etl/scrapers/master_scraper.py
"""
    
    config_file = project_root / "scripts" / "optimal_scraperapi_config.sh"
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Created optimal configuration: {config_file}")

def main():
    """Main research function."""
    print("🔬 SCRAPERAPI US IP RESEARCH")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("SCRAPERAPI_KEY")
    if not api_key:
        print("❌ SCRAPERAPI_KEY environment variable not set")
        print("\n💡 To run this research:")
        print("   export SCRAPERAPI_KEY=your_api_key_here")
        print("   python3 scripts/research_scraperapi_us_ip.py")
        return
    
    print(f"✅ Using ScraperAPI key: {api_key[:8]}...")
    
    # Test HTTP API configurations
    http_results = test_scraperapi_http_api(api_key)
    
    # Test proxy endpoints
    proxy_results = test_scraperapi_proxy_endpoints(api_key)
    
    # Find working US configurations
    working_us_configs = []
    for result in http_results + proxy_results:
        if result.get('success') and result.get('is_us'):
            working_us_configs.append(result)
    
    # Test tennis site access
    if working_us_configs:
        tennis_results = test_tennis_site_access(api_key, working_us_configs)
    else:
        tennis_results = []
        print("\n⚠️ No working US configurations found - skipping tennis site test")
    
    # Generate recommendations
    generate_recommendations(http_results, proxy_results, tennis_results)
    
    print(f"\n🎯 RESEARCH COMPLETE")
    print(f"   HTTP API tests: {len(http_results)}")
    print(f"   Proxy endpoint tests: {len(proxy_results)}")
    print(f"   Working US configs: {len(working_us_configs)}")
    print(f"   Tennis site access: {len(tennis_results)}")

if __name__ == "__main__":
    main() 