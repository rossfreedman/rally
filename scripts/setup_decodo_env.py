#!/usr/bin/env python3
"""
Setup Decodo Environment Variables
=================================

Sets up the Decodo proxy environment variables for the Rally scraper system.
This script helps configure the environment for both local development and Railway deployment.

Usage:
    python scripts/setup_decodo_env.py
"""

import os
import sys

def setup_decodo_environment():
    """Set up Decodo environment variables."""
    print("🔧 Setting up Decodo Environment Variables")
    print("=" * 50)
    
    # Decodo credentials
    decodo_user = "sp2lv5ti3g"
    decodo_pass = "zU0Pdl~7rcGqgxuM69"
    
    # Set environment variables
    os.environ["DECODO_USER"] = decodo_user
    os.environ["DECODO_PASS"] = decodo_pass
    
    print(f"✅ DECODO_USER set to: {decodo_user}")
    print(f"✅ DECODO_PASS set to: {'*' * len(decodo_pass)} (hidden)")
    
    # Verify the variables are set
    print("\n🔍 Verifying environment variables:")
    user = os.getenv("DECODO_USER")
    password = os.getenv("DECODO_PASS")
    
    if user and password:
        print("   ✅ Environment variables are set correctly")
    else:
        print("   ❌ Environment variables are not set correctly")
        return False
    
    return True

def generate_railway_env():
    """Generate Railway environment variable configuration."""
    print("\n🚂 Railway Environment Configuration")
    print("=" * 50)
    
    print("Add these environment variables to your Railway project:")
    print()
    print("DECODO_USER=sp2lv5ti3g")
    print("DECODO_PASS=zU0Pdl~7rcGqgxuM69")
    print()
    print("✅ CONFIRMED WORKING: us.decodo.com:10001 endpoint")
    print()
    print("To add them via Railway CLI:")
    print("railway variables set DECODO_USER=sp2lv5ti3g")
    print("railway variables set DECODO_PASS=zU0Pdl~7rcGqgxuM69")
    print()
    print("Or add them to your .env file:")
    print("DECODO_USER=sp2lv5ti3g")
    print("DECODO_PASS=zU0Pdl~7rcGqgxuM69")

def generate_docker_env():
    """Generate Docker environment variable configuration."""
    print("\n🐳 Docker Environment Configuration")
    print("=" * 50)
    
    print("Add these environment variables to your Dockerfile or docker-compose.yml:")
    print()
    print("ENV DECODO_USER=sp2lv5ti3g")
    print("ENV DECODO_PASS=zU0Pdl~7rcGqgxuM69")
    print()
    print("Or for docker-compose.yml:")
    print("environment:")
    print("  - DECODO_USER=sp2lv5ti3g")
    print("  - DECODO_PASS=zU0Pdl~7rcGqgxuM69")

def main():
    """Main setup function."""
    print("🚀 Decodo Environment Setup")
    print("=" * 50)
    
    # Set up local environment
    if setup_decodo_environment():
        print("\n✅ Local environment setup completed successfully!")
    else:
        print("\n❌ Local environment setup failed!")
        return 1
    
    # Generate configuration for different environments
    generate_railway_env()
    generate_docker_env()
    
    print("\n" + "=" * 50)
    print("🎉 Setup Complete!")
    print("=" * 50)
    print("Next steps:")
    print("1. Test the proxy: python3 scripts/test_decodo_proxy.py")
    print("2. Test scraper logic: python3 scripts/test_decodo_scraper.py")
    print("3. Update Railway environment variables")
    print("4. Test a scraper: python3 data/etl/scrapers/scrape_match_scores.py aptachicago")
    
    return 0

if __name__ == "__main__":
    exit(main()) 