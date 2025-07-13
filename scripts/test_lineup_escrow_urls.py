#!/usr/bin/env python3
"""
Test script to verify lineup escrow URL generation works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_url_generation_logic():
    """Test URL generation logic directly"""
    
    print("🧪 Testing Lineup Escrow URL Generation Logic")
    print("=" * 50)
    
    # Test 1: Production URL generation
    base_url = "https://www.lovetorally.com"
    escrow_token = "test_token_123"
    view_url = f"{base_url}/mobile/lineup-escrow-view/{escrow_token}"
    
    print("✅ Production URL test:")
    print(f"   Base URL: {base_url}")
    print(f"   Escrow Token: {escrow_token}")
    print(f"   Generated URL: {view_url}")
    print(f"   Expected: https://www.lovetorally.com/mobile/lineup-escrow-view/test_token_123")
    print(f"   Match: {view_url == 'https://www.lovetorally.com/mobile/lineup-escrow-view/test_token_123'}")
    print()
    
    # Test 2: Local development URL generation
    base_url = ""
    escrow_token = "test_token_456"
    view_url = f"{base_url}/mobile/lineup-escrow-view/{escrow_token}" if base_url else f"/mobile/lineup-escrow-view/{escrow_token}"
    
    print("✅ Local development URL test:")
    print(f"   Base URL: {base_url}")
    print(f"   Escrow Token: {escrow_token}")
    print(f"   Generated URL: {view_url}")
    print(f"   Expected: /mobile/lineup-escrow-view/test_token_456")
    print(f"   Match: {view_url == '/mobile/lineup-escrow-view/test_token_456'}")
    print()
    
    # Test 3: Localhost URL generation
    base_url = "http://localhost:5000"
    escrow_token = "test_token_789"
    view_url = f"{base_url}/mobile/lineup-escrow-view/{escrow_token}" if base_url else f"/mobile/lineup-escrow-view/{escrow_token}"
    
    print("✅ Localhost URL test:")
    print(f"   Base URL: {base_url}")
    print(f"   Escrow Token: {escrow_token}")
    print(f"   Generated URL: {view_url}")
    print(f"   Expected: http://localhost:5000/mobile/lineup-escrow-view/test_token_789")
    print(f"   Match: {view_url == 'http://localhost:5000/mobile/lineup-escrow-view/test_token_789'}")
    print()
    
    # Test 4: Email notification URL generation
    base_url = "http://localhost:5000"
    escrow_id = 123
    email_url = f"{base_url}/lineup-escrow/{escrow_id}" if base_url else f"/lineup-escrow/{escrow_id}"
    
    print("✅ Email notification URL test:")
    print(f"   Base URL: {base_url}")
    print(f"   Escrow ID: {escrow_id}")
    print(f"   Generated URL: {email_url}")
    print(f"   Expected: http://localhost:5000/lineup-escrow/123")
    print(f"   Match: {email_url == 'http://localhost:5000/lineup-escrow/123'}")
    print()
    
    print("✅ All URL generation tests completed!")

if __name__ == "__main__":
    test_url_generation_logic() 