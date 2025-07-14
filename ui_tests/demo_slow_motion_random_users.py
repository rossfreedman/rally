#!/usr/bin/env python3
"""
Slow Motion Browser Demo with Random Users
Tests registration flow with 5 random users in slow motion
"""

import time
import sys
import os
import random
import string
import requests

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

def check_server_running(port=8080):
    """Check if the Flask server is running"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def generate_random_user():
    """Generate random user data for testing"""
    
    # Random first names
    first_names = [
        "Alex", "Jordan", "Casey", "Taylor", "Morgan", "Riley", "Quinn", "Avery",
        "Blake", "Cameron", "Drew", "Emery", "Finley", "Gray", "Harper", "Indigo",
        "Jamie", "Kendall", "Logan", "Mason", "Noah", "Oakley", "Parker", "Quincy"
    ]
    
    # Random last names
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
        "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
    ]
    
    # Random clubs
    clubs = ["Tennaqua", "Glenbrook RC", "LifeSport", "North Shore", "Evanston"]
    
    # Random series
    series_options = ["Series 1", "Series 2", "Series 3", "Series 4", "Series 5", "Series 6"]
    
    # Generate random email
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    email = f"{random.choice(first_names).lower()}.{random.choice(last_names).lower()}.{random_suffix}@example.com"
    
    return {
        "first_name": random.choice(first_names),
        "last_name": random.choice(last_names),
        "email": email,
        "password": "TestPassword123!",
        "club": random.choice(clubs),
        "series": random.choice(series_options),
        "preferences": random.choice(["Available", "Unavailable", "Not Sure"])
    }

def demo_random_users_slow_motion():
    """Demo registration process with 5 random users in slow motion"""
    
    print("🎬 Starting Slow Motion Demo with 5 Random Users")
    print("=" * 60)
    
    # Check if server is running
    port = 8080
    if not check_server_running(port):
        print(f"❌ Server not running on port {port}")
        print("Please start the server first with: python server.py")
        print("Or run: FLASK_ENV=development python server.py")
        return
    
    print(f"✅ Server is running on port {port}")
    
    # Generate 5 random users
    users = [generate_random_user() for _ in range(5)]
    
    print(f"Generated {len(users)} random users:")
    for i, user in enumerate(users, 1):
        print(f"  {i}. {user['first_name']} {user['last_name']} ({user['email']})")
    print()
    
    with sync_playwright() as p:
        # Launch browser with slow motion
        browser = p.chromium.launch(
            headless=False,  # Show the browser
            slow_mo=1000,    # 1 second delay between actions
            args=[
                "--start-maximized",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ]
        )
        
        # Create new context
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        # Navigate to the application
        print("🌐 Navigating to application...")
        page.goto(f"http://localhost:{port}")
        time.sleep(1.5)
        
        for i, user in enumerate(users, 1):
            print(f"\n👤 Testing User {i}: {user['first_name']} {user['last_name']}")
            print("-" * 40)
            
            try:
                # Navigate to login page
                print("  📝 Going to registration form...")
                page.goto(f"http://localhost:{port}/login")
                time.sleep(1)
                
                # Switch to registration tab
                print("  🔄 Switching to registration tab...")
                register_tab = page.locator("text=Register")
                if register_tab.is_visible():
                    register_tab.click()
                    time.sleep(1)
                
                # Fill out registration form
                print("  ✏️  Filling out registration form...")
                
                # First Name
                print(f"    - First Name: {user['first_name']}")
                first_name_input = page.locator("#firstName")
                first_name_input.fill(user['first_name'])
                time.sleep(0.5)
                
                # Last Name
                print(f"    - Last Name: {user['last_name']}")
                last_name_input = page.locator("#lastName")
                last_name_input.fill(user['last_name'])
                time.sleep(0.5)
                
                # Email
                print(f"    - Email: {user['email']}")
                email_input = page.locator("#registerEmail")
                email_input.fill(user['email'])
                time.sleep(0.5)
                
                # Phone Number
                print(f"    - Phone: (555) 123-4567")
                phone_input = page.locator("#phoneNumber")
                phone_input.fill("(555) 123-4567")
                time.sleep(0.5)
                
                # Password
                print(f"    - Password: {user['password']}")
                password_input = page.locator("#registerPassword")
                password_input.fill(user['password'])
                time.sleep(0.5)
                
                # Confirm Password
                print(f"    - Confirm Password: {user['password']}")
                confirm_password_input = page.locator("#confirmPassword")
                confirm_password_input.fill(user['password'])
                time.sleep(0.5)
                
                # League (APTA Chicago)
                print("    - League: APTA Chicago")
                league_select = page.locator("#league")
                league_select.select_option("APTA_CHICAGO")
                time.sleep(0.5)
                
                # Club
                print(f"    - Club: {user['club']}")
                club_select = page.locator("#club")
                club_select.select_option(user['club'])
                time.sleep(0.5)
                
                # Series
                print(f"    - Series: {user['series']}")
                series_select = page.locator("#series")
                try:
                    series_select.select_option(user['series'])
                    time.sleep(0.5)
                except Exception as e:
                    print(f"      ⚠️  Series {user['series']} not available, trying Series 1")
                    try:
                        series_select.select_option("Series 1")
                        time.sleep(0.5)
                    except:
                        print(f"      ⚠️  Could not select series, continuing...")
                
                # Ad/Deuce Preference
                print("    - Ad/Deuce: Either")
                ad_deuce_select = page.locator("#adDeuce")
                ad_deuce_select.select_option("Either")
                time.sleep(0.5)
                
                # Dominant Hand
                print("    - Hand: Righty")
                hand_select = page.locator("#dominantHand")
                hand_select.select_option("Righty")
                time.sleep(0.5)
                
                # Text Notifications
                print("    - Text Notifications: Yes")
                text_checkbox = page.locator("#textNotifications")
                text_checkbox.check()
                time.sleep(0.5)
                
                # Submit the form
                print("  🚀 Submitting registration form...")
                # Use a more specific selector for the register form submit button
                submit_button = page.locator("#registerForm button[type='submit']")
                if submit_button.is_visible():
                    submit_button.click()
                    time.sleep(2.5)
                    
                    # Check for success or error
                    if page.url != f"http://localhost:{port}/login":
                        print("  ✅ Registration successful!")
                    else:
                        print("  ⚠️  Registration may have failed - still on login page")
                else:
                    print("  ❌ Submit button not found")
                
                # Wait a bit before next user
                print("  ⏳ Waiting before next user...")
                time.sleep(1.5)
                
            except Exception as e:
                print(f"  ❌ Error with user {i}: {str(e)}")
                continue
        
        # Keep browser open for final review
        print(f"\n🎬 Demo complete! Browser will stay open for 30 seconds for review...")
        time.sleep(15)
        
        browser.close()

if __name__ == "__main__":
    demo_random_users_slow_motion() 