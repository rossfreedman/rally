#!/usr/bin/env python3
"""
Simple Slow Motion Browser Demo
Shows basic slow motion interactions with the Rally registration form
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

def demo_simple_slow_motion():
    """Simple demo with slow motion interactions"""
    
    print("🎬 Starting Simple Slow Motion Demo")
    print("=" * 50)
    
    with sync_playwright() as p:
        # Launch browser with slow motion
        browser = p.chromium.launch(
            headless=False,  # Show the browser
            slow_mo=1500,    # 1.5 second delay between actions
            args=[
                "--start-maximized",
                "--disable-dev-shm-usage",
            ]
        )
        
        # Create context
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        
        # Create page
        page = context.new_page()
        
        try:
            print("🌐 Navigating to Rally login page...")
            page.goto("http://localhost:8080/login")
            page.wait_for_load_state("networkidle")
            
            print("⏳ Waiting for page to load...")
            time.sleep(2)
            
            # Check what we have
            print("🔍 Checking page elements...")
            page_title = page.title()
            print(f"📄 Page title: {page_title}")
            
            # Look for forms
            forms = page.locator("form").all()
            print(f"📋 Found {len(forms)} forms")
            
            for i, form in enumerate(forms):
                form_id = form.get_attribute("id")
                form_class = form.get_attribute("class")
                print(f"   Form {i}: id='{form_id}', class='{form_class}'")
            
            # Try to show registration form
            print("🔧 Showing registration form...")
            
            # Simple approach - just click to show register form
            page.evaluate("""
                const registerForm = document.getElementById('registerForm');
                const loginForm = document.getElementById('loginForm');
                
                if (registerForm && loginForm) {
                    registerForm.classList.add('active');
                    registerForm.classList.remove('inactive');
                    loginForm.classList.remove('active');
                    loginForm.classList.add('inactive');
                }
            """)
            
            time.sleep(2)
            
            # Now fill the form fields
            print("📝 Filling registration form...")
            
            # Generate unique email
            timestamp = int(time.time())
            test_email = f"demo{timestamp}@example.com"
            
            # Fill email
            print(f"✍️ Filling email: {test_email}")
            email_field = page.locator("#registerEmail")
            if email_field.count() > 0:
                email_field.fill(test_email)
            
            # Fill password
            print("✍️ Filling password...")
            password_field = page.locator("#registerPassword")
            if password_field.count() > 0:
                password_field.fill("DemoPassword123!")
            
            # Fill confirm password
            print("✍️ Filling confirm password...")
            confirm_password_field = page.locator("#confirmPassword")
            if confirm_password_field.count() > 0:
                confirm_password_field.fill("DemoPassword123!")
            
            # Fill first name
            print("✍️ Filling first name...")
            first_name_field = page.locator("#firstName")
            if first_name_field.count() > 0:
                first_name_field.fill("Demo")
            
            # Fill last name
            print("✍️ Filling last name...")
            last_name_field = page.locator("#lastName")
            if last_name_field.count() > 0:
                last_name_field.fill("User")
            
            # Fill phone number
            print("✍️ Filling phone number...")
            phone_field = page.locator("#phoneNumber")
            if phone_field.count() > 0:
                phone_field.fill("555-123-4567")
            
            # Wait for dropdowns to load
            print("⏳ Waiting for dropdowns to load...")
            time.sleep(3)
            
            # Select league
            print("📋 Selecting league...")
            league_select = page.locator("#league")
            if league_select.count() > 0:
                try:
                    league_select.select_option("APTA_CHICAGO")
                except Exception as e:
                    print(f"⚠️ Could not select league: {e}")
            
            # Select club
            print("📋 Selecting club...")
            club_select = page.locator("#club")
            if club_select.count() > 0:
                try:
                    club_select.select_option("Tennaqua")
                except Exception as e:
                    print(f"⚠️ Could not select club: {e}")
            
            # Select series
            print("📋 Selecting series...")
            series_select = page.locator("#series")
            if series_select.count() > 0:
                try:
                    series_select.select_option("Series 7")
                except Exception as e:
                    print(f"⚠️ Could not select series: {e}")
            
            # Select ad/deuce preference
            print("📋 Selecting ad/deuce preference...")
            ad_select = page.locator("#adDeuce")
            if ad_select.count() > 0:
                try:
                    ad_select.select_option("Ad")
                except Exception as e:
                    print(f"⚠️ Could not select ad/deuce: {e}")
            
            # Select dominant hand
            print("📋 Selecting dominant hand...")
            hand_select = page.locator("#dominantHand")
            if hand_select.count() > 0:
                try:
                    hand_select.select_option("Righty")
                except Exception as e:
                    print(f"⚠️ Could not select dominant hand: {e}")
            
            # Check text notifications
            print("📋 Checking text notifications...")
            notification_checkbox = page.locator("#textNotifications")
            if notification_checkbox.count() > 0:
                try:
                    notification_checkbox.check()
                except Exception as e:
                    print(f"⚠️ Could not check notifications: {e}")
            
            # Wait a moment
            time.sleep(2)
            
            # Look for submit button
            print("🔍 Looking for submit button...")
            
            # Try different submit button selectors
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Register")',
                'button:has-text("Sign Up")',
                'button:has-text("Create Account")',
                '.submit-button',
                '#submit',
                '.btn-primary',
                '.btn-success'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                elements = page.locator(selector)
                if elements.count() > 0:
                    for element in elements.all():
                        if element.is_visible() and element.is_enabled():
                            submit_button = element
                            print(f"✅ Found submit button: {selector}")
                            break
                    if submit_button:
                        break
            
            if submit_button:
                print("🚀 Clicking submit button...")
                submit_button.click()
                
                # Wait for response
                print("⏳ Waiting for registration response...")
                time.sleep(5)
                
                # Check result
                current_url = page.url
                print(f"📍 Current URL: {current_url}")
                
                if "welcome" in current_url or "mobile" in current_url:
                    print("🎉 Registration appears successful!")
                else:
                    print("⚠️ Registration may have failed, checking for errors...")
                    
                    # Look for error messages
                    error_elements = page.locator('.error-message, .alert-danger, #error-message, .registration-error')
                    if error_elements.count() > 0:
                        for error in error_elements.all():
                            error_text = error.text_content()
                            print(f"❌ Error: {error_text}")
            else:
                print("❌ Could not find submit button")
                
                # Show all buttons for debugging
                print("🔍 All buttons on page:")
                all_buttons = page.locator("button").all()
                for i, button in enumerate(all_buttons):
                    try:
                        text = button.text_content().strip()
                        is_visible = button.is_visible()
                        is_enabled = button.is_enabled()
                        print(f"   Button {i}: '{text}' (visible: {is_visible}, enabled: {is_enabled})")
                    except:
                        print(f"   Button {i}: [Could not get info]")
            
            print("⏳ Demo complete - keeping browser open for 20 seconds...")
            time.sleep(20)
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print("🔚 Closing browser...")
            browser.close()

if __name__ == "__main__":
    demo_simple_slow_motion() 