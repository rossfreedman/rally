#!/usr/bin/env python3
"""
Deep Proxy Diagnostic for Active Accounts
========================================

This script performs deep diagnostics for active accounts to identify
specific authentication or configuration issues.
"""

import requests
import socket
import json
import time
from datetime import datetime

def check_ip_whitelist():
    """Check if current IP is whitelisted."""
    print("🌐 Checking IP whitelist status...")
    
    # Get current IP
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=10)
        current_ip = response.json().get("ip")
        print(f"   Current IP: {current_ip}")
        
        # Check if IP is in common ranges that might be blocked
        ip_parts = current_ip.split(".")
        if ip_parts[0] in ["192", "10", "172"]:
            print("   ⚠️ IP is in private range - this might cause issues")
        elif ip_parts[0] in ["127"]:
            print("   ❌ IP is localhost - this will definitely cause issues")
        else:
            print("   ✅ IP appears to be public")
            
        return current_ip
    except Exception as e:
        print(f"   ❌ Error getting IP: {e}")
        return None

def test_proxy_with_detailed_errors():
    """Test proxy with detailed error analysis."""
    print("\n🔍 Testing proxy with detailed error analysis...")
    
    # Load first credential
    try:
        with open("ips.txt", "r") as f:
            first_line = f.readline().strip()
            if first_line and ":" in first_line:
                parts = first_line.split(":")
                host = parts[0]
                port = parts[1]
                username = parts[2]
                password = parts[3]
                
                print(f"   Testing: {host}:{port}")
                print(f"   Username: {username}")
                print(f"   Password: {'*' * len(password)}")
                
                # Test 1: Basic TCP connection
                print("\n   1. Testing basic TCP connection...")
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    result = sock.connect_ex((host, int(port)))
                    sock.close()
                    
                    if result == 0:
                        print("      ✅ TCP connection successful")
                    else:
                        print(f"      ❌ TCP connection failed (error code: {result})")
                        return False
                except Exception as e:
                    print(f"      ❌ TCP connection error: {e}")
                    return False
                
                # Test 2: HTTP CONNECT method
                print("\n   2. Testing HTTP CONNECT method...")
                try:
                    import urllib3
                    urllib3.disable_warnings()
                    
                    proxy_url = f"http://{username}:{password}@{host}:{port}"
                    proxies = {"http": proxy_url, "https": proxy_url}
                    
                    # Test with a simple endpoint
                    response = requests.get(
                        "http://httpbin.org/ip",
                        proxies=proxies,
                        timeout=15,
                        verify=False,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Connection": "close"
                        }
                    )
                    
                    print(f"      Status: {response.status_code}")
                    if response.status_code == 200:
                        print("      ✅ HTTP CONNECT successful")
                        data = response.json()
                        print(f"      Proxy IP: {data.get('origin', 'Unknown')}")
                        return True
                    else:
                        print(f"      ❌ HTTP CONNECT failed: {response.status_code}")
                        print(f"      Response: {response.text[:200]}")
                        
                except requests.exceptions.ProxyError as e:
                    print(f"      ❌ Proxy Error: {e}")
                    if "407" in str(e):
                        print("      💡 This indicates authentication failure")
                    elif "403" in str(e):
                        print("      💡 This indicates access denied")
                    elif "502" in str(e):
                        print("      💡 This indicates bad gateway")
                    elif "503" in str(e):
                        print("      💡 This indicates service unavailable")
                except requests.exceptions.ConnectionError as e:
                    print(f"      ❌ Connection Error: {e}")
                    if "Connection refused" in str(e):
                        print("      💡 Server actively refusing connections")
                    elif "timeout" in str(e).lower():
                        print("      💡 Connection timeout")
                except Exception as e:
                    print(f"      ❌ Unexpected error: {e}")
                    
    except Exception as e:
        print(f"   ❌ Error reading credentials: {e}")
        return False
    
    return False

def test_alternative_proxy_formats():
    """Test alternative proxy authentication formats."""
    print("\n🔧 Testing alternative proxy formats...")
    
    try:
        with open("ips.txt", "r") as f:
            first_line = f.readline().strip()
            if first_line and ":" in first_line:
                parts = first_line.split(":")
                host = parts[0]
                port = parts[1]
                username = parts[2]
                password = parts[3]
                
                # Test different authentication formats
                formats = [
                    # Standard format
                    f"http://{username}:{password}@{host}:{port}",
                    # Without protocol
                    f"{username}:{password}@{host}:{port}",
                    # With different username formats
                    f"http://{username}@decodo.com:{password}@{host}:{port}",
                    f"http://{username}@us.decodo.com:{password}@{host}:{port}",
                    # URL encoded
                    f"http://{username}:{password.replace('~', '%7E')}@{host}:{port}",
                    # Different port format
                    f"http://{username}:{password}@{host}:{port}/",
                ]
                
                for i, proxy_url in enumerate(formats, 1):
                    print(f"   Testing format {i}: {proxy_url.split('@')[0]}@***")
                    
                    proxies = {"http": proxy_url, "https": proxy_url}
                    
                    try:
                        response = requests.get(
                            "http://httpbin.org/ip",
                            proxies=proxies,
                            timeout=10,
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                        )
                        
                        if response.status_code == 200:
                            print(f"      ✅ Format {i} works!")
                            data = response.json()
                            print(f"      IP: {data.get('origin', 'Unknown')}")
                            return proxy_url
                        else:
                            print(f"      ❌ Format {i}: HTTP {response.status_code}")
                            
                    except requests.exceptions.ProxyError as e:
                        print(f"      ❌ Format {i}: Proxy Error")
                    except requests.exceptions.ConnectionError as e:
                        print(f"      ❌ Format {i}: Connection Error")
                    except Exception as e:
                        print(f"      ❌ Format {i}: {e}")
                        
    except Exception as e:
        print(f"   ❌ Error testing formats: {e}")
    
    return None

def check_decodo_service_status():
    """Check Decodo service status."""
    print("\n📊 Checking Decodo service status...")
    
    # Test various Decodo endpoints
    endpoints = [
        "https://decodo.com",
        "https://us.decodo.com", 
        "https://api.decodo.com",
        "https://status.decodo.com",
        "https://decodo.com/status"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            print(f"   {endpoint}: HTTP {response.status_code}")
            if response.status_code == 200:
                print(f"      Content length: {len(response.text)}")
        except Exception as e:
            print(f"   {endpoint}: {e}")

def create_working_proxy_test():
    """Create a simple test to verify if any proxies work."""
    print("\n🧪 Creating working proxy test...")
    
    test_script = """#!/usr/bin/env python3
\"\"\"
Simple Proxy Test
================

This script tests if any proxies are working with minimal overhead.
\"\"\"

import requests
import time

def test_single_proxy(host, port, username, password):
    \"\"\"Test a single proxy with minimal overhead.\"\"\"
    proxy_url = f"http://{username}:{password}@{host}:{port}"
    proxies = {"http": proxy_url, "https": proxy_url}
    
    try:
        response = requests.get(
            "http://httpbin.org/ip",
            proxies=proxies,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Proxy {host}:{port} works! IP: {data.get('origin')}")
            return True
        else:
            print(f"❌ Proxy {host}:{port} failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Proxy {host}:{port} error: {e}")
        return False

# Load and test first 5 proxies
with open("ips.txt", "r") as f:
    for i, line in enumerate(f):
        if i >= 5:
            break
            
        if line.strip() and ":" in line:
            parts = line.split(":")
            if len(parts) >= 4:
                host, port, username, password = parts[:4]
                test_single_proxy(host, port, username, password)
                time.sleep(1)  # Brief delay between tests
"""
    
    with open("scripts/simple_proxy_test.py", "w") as f:
        f.write(test_script)
    
    print("   📄 Created scripts/simple_proxy_test.py")

def main():
    """Main diagnostic function."""
    print("🔍 DEEP PROXY DIAGNOSTIC FOR ACTIVE ACCOUNTS")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check IP whitelist
    current_ip = check_ip_whitelist()
    
    # Test proxy with detailed errors
    proxy_works = test_proxy_with_detailed_errors()
    
    if proxy_works:
        print("\n✅ Proxy authentication is working!")
        print("   The issue might be with specific endpoints or rate limiting.")
    else:
        print("\n❌ Proxy authentication is failing.")
        
        # Test alternative formats
        working_format = test_alternative_proxy_formats()
        
        if working_format:
            print(f"\n✅ Found working format: {working_format}")
            print("   Update your proxy configuration to use this format.")
        else:
            print("\n❌ No alternative formats work.")
            
            # Check service status
            check_decodo_service_status()
            
            # Create simple test
            create_working_proxy_test()
            
            print("\n🚨 SPECIFIC RECOMMENDATIONS:")
            print("1. Contact Decodo support with these details:")
            print(f"   - Your IP: {current_ip}")
            print("   - All authentication methods tested and failed")
            print("   - TCP connections work but HTTP auth fails")
            print("2. Ask them to:")
            print("   - Check if your IP is whitelisted")
            print("   - Verify your account configuration")
            print("   - Check for any service maintenance")
            print("3. Run the simple test: python3 scripts/simple_proxy_test.py")
    
    print(f"\n✅ Deep diagnostic complete at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 