#!/usr/bin/env python3
"""
Quick Proxy Diagnostic
=====================

This script quickly determines if the connection errors are due to:
1. Network connectivity issues
2. Proxy provider infrastructure problems
3. Authentication/credential issues
"""

import requests
import socket
import time
from datetime import datetime

def test_basic_connectivity():
    """Test basic internet connectivity."""
    print("🌐 Testing basic internet connectivity...")
    
    test_urls = [
        "https://httpbin.org/ip",
        "https://api.ipify.org?format=json",
        "https://google.com"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            print(f"   ✅ {url}: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ {url}: {e}")

def test_proxy_server_connectivity():
    """Test if we can reach the proxy server at all."""
    print("\n🔌 Testing proxy server connectivity...")
    
    # Test basic TCP connectivity to proxy server
    proxy_host = "us.decodo.com"
    proxy_ports = [10001, 10002, 10003, 10004, 10005]
    
    for port in proxy_ports:
        try:
            print(f"   Testing {proxy_host}:{port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((proxy_host, port))
            sock.close()
            
            if result == 0:
                print(f"   ✅ {proxy_host}:{port} - Port is open")
            else:
                print(f"   ❌ {proxy_host}:{port} - Port is closed/unreachable")
                
        except Exception as e:
            print(f"   ❌ {proxy_host}:{port} - Error: {e}")

def test_proxy_credentials():
    """Test if proxy credentials are valid."""
    print("\n🔐 Testing proxy credentials...")
    
    # Load a few proxy credentials from ips.txt
    credentials = []
    try:
        with open("ips.txt", "r") as f:
            for i, line in enumerate(f):
                if i >= 3:  # Only test first 3
                    break
                if line.strip() and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 4:
                        host = parts[0]
                        port = parts[1]
                        username = parts[2]
                        password = parts[3]
                        credentials.append({
                            "host": host,
                            "port": port,
                            "username": username,
                            "password": password
                        })
    except Exception as e:
        print(f"   ❌ Error reading ips.txt: {e}")
        return
    
    if not credentials:
        print("   ❌ No credentials found in ips.txt")
        return
    
    print(f"   Found {len(credentials)} credential sets to test")
    
    for i, cred in enumerate(credentials):
        print(f"   Testing credential set {i+1}: {cred['host']}:{cred['port']}")
        
        # Test with a simple request
        proxy_url = f"http://{cred['username']}:{cred['password']}@{cred['host']}:{cred['port']}"
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        try:
            response = requests.get(
                "https://httpbin.org/ip",
                proxies=proxies,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            
            if response.status_code == 200:
                print(f"   ✅ Credential set {i+1} works!")
                try:
                    data = response.json()
                    print(f"      IP: {data.get('origin', 'Unknown')}")
                except:
                    print(f"      Response: {response.text[:100]}...")
            else:
                print(f"   ❌ Credential set {i+1} failed: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Credential set {i+1}: Connection Error (server unreachable)")
        except requests.exceptions.Timeout:
            print(f"   ❌ Credential set {i+1}: Timeout")
        except Exception as e:
            print(f"   ❌ Credential set {i+1}: {e}")

def check_ips_file():
    """Check the format and content of ips.txt."""
    print("\n📄 Checking ips.txt file...")
    
    try:
        with open("ips.txt", "r") as f:
            lines = f.readlines()
        
        print(f"   Total lines: {len(lines)}")
        
        if not lines:
            print("   ❌ ips.txt is empty!")
            return
        
        # Check first few lines
        for i, line in enumerate(lines[:5]):
            line = line.strip()
            if not line:
                continue
                
            if ":" in line:
                parts = line.split(":")
                print(f"   Line {i+1}: {len(parts)} parts")
                if len(parts) >= 4:
                    host, port, username, password = parts[:4]
                    print(f"      Host: {host}")
                    print(f"      Port: {port}")
                    print(f"      Username: {username}")
                    print(f"      Password: {'*' * len(password)}")
                else:
                    print(f"      ❌ Invalid format: {line}")
            else:
                print(f"   ❌ Line {i+1}: No ':' found")
                
    except FileNotFoundError:
        print("   ❌ ips.txt not found!")
    except Exception as e:
        print(f"   ❌ Error reading ips.txt: {e}")

def main():
    """Main diagnostic function."""
    print("🔍 QUICK PROXY DIAGNOSTIC")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test basic connectivity first
    test_basic_connectivity()
    
    # Test proxy server connectivity
    test_proxy_server_connectivity()
    
    # Check ips.txt format
    check_ips_file()
    
    # Test proxy credentials
    test_proxy_credentials()
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSIS SUMMARY:")
    print("=" * 50)
    print("Based on the results above:")
    print("1. If basic connectivity fails → Network issue")
    print("2. If proxy ports are closed → Provider infrastructure down")
    print("3. If credentials fail → Authentication issue")
    print("4. If ips.txt is malformed → Configuration issue")
    print("\n💡 RECOMMENDATIONS:")
    print("- Contact your proxy provider immediately")
    print("- Check your account status and billing")
    print("- Verify proxy credentials are correct")
    print("- Consider switching providers if issues persist")

if __name__ == "__main__":
    main() 