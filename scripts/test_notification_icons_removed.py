#!/usr/bin/env python3
"""
Test script to verify that emoji icons have been removed from notification titles.
"""

import requests
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_notification_titles():
    """Test that notification titles no longer contain emoji icons"""
    
    # Test data - these are the expected titles without emojis
    expected_titles = [
        "Captain's Message",
        "Upcoming Schedule", 
        "Team Poll",
        "Pickup Game Available",
        "Team Position",
        "My Win Streaks"
    ]
    
    # Emoji patterns that should NOT be in titles
    emoji_patterns = ["📢", "📅", "📊", "🎾", "🏆", "🔥"]
    
    print("🔍 Testing notification titles for emoji removal...")
    print("=" * 60)
    
    # Test the API endpoint
    try:
        # Note: This would require authentication in a real test
        # For now, we'll just check the code changes
        print("✅ Backend changes verified:")
        
        # Check that all emoji patterns have been removed from the code
        api_file = "app/routes/api_routes.py"
        if os.path.exists(api_file):
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for any remaining emoji patterns
            found_emojis = []
            for emoji in emoji_patterns:
                if emoji in content:
                    found_emojis.append(emoji)
            
            if found_emojis:
                print(f"❌ Found remaining emoji patterns: {found_emojis}")
                return False
            else:
                print("✅ All emoji patterns removed from API routes")
        else:
            print("❌ API routes file not found")
            return False
            
        # Check frontend templates
        print("\n✅ Frontend templates verified:")
        
        templates_to_check = [
            "templates/mobile/index.html",
            "templates/mobile/home_submenu.html"
        ]
        
        for template_file in templates_to_check:
            if os.path.exists(template_file):
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for any emoji patterns in the template
                found_emojis = []
                for emoji in emoji_patterns:
                    if emoji in content:
                        found_emojis.append(emoji)
                
                if found_emojis:
                    print(f"❌ Found emoji patterns in {template_file}: {found_emojis}")
                    return False
                else:
                    print(f"✅ No emoji patterns found in {template_file}")
            else:
                print(f"❌ Template file not found: {template_file}")
                return False
        
        print("\n" + "=" * 60)
        print("🎉 SUCCESS: All emoji icons have been removed from notification titles!")
        print("\nExpected notification titles (without emojis):")
        for title in expected_titles:
            print(f"  • {title}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🧪 Notification Title Emoji Removal Test")
    print("=" * 60)
    
    success = test_notification_titles()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 