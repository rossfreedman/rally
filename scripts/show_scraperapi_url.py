#!/usr/bin/env python3
"""
Show the exact ScraperAPI URL being generated for support ticket.
"""

import os
import sys

# Add the scrapers directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data', 'etl', 'scrapers'))

def show_scraperapi_url():
    """Show the ScraperAPI URL being generated."""
    
    print("🔗 ScraperAPI URL for Support Ticket")
    print("=" * 50)
    
    # Check if SCRAPERAPI_KEY is set
    api_key = os.getenv("SCRAPERAPI_KEY")
    if not api_key:
        print("❌ SCRAPERAPI_KEY environment variable not set")
        return
    
    print(f"✅ SCRAPERAPI_KEY found: {api_key[:10]}...")
    
    # Generate the URL exactly as the scraper does
    test_url = "https://httpbin.org/ip"
    base_params = f"api_key={api_key}&url={test_url}&country_code=us&region=us&premium=true&session_number=1&retry=3&timeout=60"
    scraperapi_url = f"http://api.scraperapi.com?{base_params}"
    
    print(f"\n📋 EXACT URL BEING SENT TO SCRAPERAPI:")
    print("-" * 50)
    print(scraperapi_url)
    print("-" * 50)
    
    # Break down the parameters
    print(f"\n📊 URL PARAMETERS:")
    print(f"• api_key: {api_key[:10]}...")
    print(f"• url: {test_url}")
    print(f"• country_code: us")
    print(f"• region: us") 
    print(f"• premium: true")
    print(f"• session_number: 1")
    print(f"• retry: 3")
    print(f"• timeout: 60")
    
    print(f"\n🎯 EXPECTED BEHAVIOR:")
    print(f"• Should return a US-based IP address")
    print(f"• Should respond within 60 seconds")
    print(f"• Should use premium US proxies")
    
    print(f"\n❌ CURRENT ISSUE:")
    print(f"• Getting timeout errors or 500 status codes")
    print(f"• Sometimes getting non-US IPs (e.g., Bulgaria)")
    
    print(f"\n" + "=" * 50)
    print("📝 COPY THE URL ABOVE FOR YOUR SUPPORT TICKET")

if __name__ == "__main__":
    show_scraperapi_url() 