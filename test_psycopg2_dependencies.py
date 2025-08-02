#!/usr/bin/env python3
"""
PostgreSQL Dependency Test Script
==================================

Tests psycopg2-binary installation and system dependencies to diagnose
Railway deployment issues.

Usage:
    python test_psycopg2_dependencies.py

This script should be run in the Railway environment to verify:
1. System libraries are available
2. psycopg2-binary imports successfully
3. PostgreSQL connections work
"""

import os
import sys
import subprocess

def test_system_libraries():
    """Test that required system libraries are available"""
    print("🔍 Testing System Libraries")
    print("=" * 50)
    
    # Test for zlib
    try:
        import zlib
        print("✅ zlib library: Available")
    except ImportError as e:
        print(f"❌ zlib library: Missing - {e}")
        return False
    
    # Test for SSL libraries
    try:
        import ssl
        print("✅ SSL library: Available")
    except ImportError as e:
        print(f"❌ SSL library: Missing - {e}")
        return False
    
    return True

def test_psycopg2_import():
    """Test psycopg2 import with detailed error reporting"""
    print("\n🔍 Testing psycopg2-binary Import")
    print("=" * 50)
    
    try:
        import psycopg2
        print("✅ psycopg2 import: SUCCESS")
        print(f"   Version: {psycopg2.__version__}")
        
        # Test specific imports that might fail
        from psycopg2.extras import RealDictCursor
        print("✅ psycopg2.extras: SUCCESS")
        
        return True
        
    except ImportError as e:
        print(f"❌ psycopg2 import: FAILED")
        print(f"   Error: {e}")
        
        # Check if it's the libz.so.1 issue
        if "libz.so.1" in str(e):
            print("🔧 DIAGNOSIS: Missing zlib system library")
            print("   Solution: Add zlib to nixpacks.toml")
        elif "libpq" in str(e):
            print("🔧 DIAGNOSIS: Missing PostgreSQL client library")
            print("   Solution: Add postgresql_15 and libpq to nixpacks.toml")
        else:
            print("🔧 DIAGNOSIS: Unknown import error")
            
        return False

def test_environment_setup():
    """Test Railway environment setup"""
    print("\n🔍 Testing Environment Setup")
    print("=" * 50)
    
    # Check nixpacks environment
    nix_store_exists = os.path.exists("/nix/store")
    print(f"{'✅' if nix_store_exists else '❌'} Nix store: {'Available' if nix_store_exists else 'Missing'}")
    
    # Check for PostgreSQL environment variables
    db_vars = ["DATABASE_URL", "DB_HOST", "DB_NAME", "DB_USER"]
    for var in db_vars:
        value = os.environ.get(var, "Not set")
        masked_value = "***" if "password" in var.lower() and value != "Not set" else value
        print(f"   {var}: {masked_value}")
    
    # Check Python version
    print(f"✅ Python version: {sys.version}")
    
    return True

def test_database_connection():
    """Test actual database connection"""
    print("\n🔍 Testing Database Connection")
    print("=" * 50)
    
    try:
        import psycopg2
        
        # Try to get database config
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found in environment")
            return False
            
        # Test connection
        try:
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Database connection: SUCCESS")
            print(f"   PostgreSQL version: {version}")
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Database connection: FAILED")
            print(f"   Error: {e}")
            return False
            
    except ImportError:
        print("❌ Cannot test database connection - psycopg2 import failed")
        return False

def main():
    """Run all diagnostic tests"""
    print("🔬 Railway PostgreSQL Dependency Diagnostics")
    print("=" * 60)
    print(f"🌍 Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
    print(f"📁 Working Directory: {os.getcwd()}")
    print("=" * 60)
    
    tests = [
        ("System Libraries", test_system_libraries),
        ("psycopg2 Import", test_psycopg2_import),
        ("Environment Setup", test_environment_setup),
        ("Database Connection", test_database_connection),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name}: CRASHED - {e}")
            results[test_name] = False
    
    # Summary
    print("\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Railway psycopg2 setup is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check nixpacks.toml system dependencies.")
        return 1

if __name__ == "__main__":
    sys.exit(main())