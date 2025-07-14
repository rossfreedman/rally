#!/usr/bin/env python3
"""
Demo Slow Motion Browser Automation
Shows the registration process with slow motion for visual debugging
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

def demo_registration_slow_motion():
    """Demo registration process with slow motion"""
    
    print("🎬 Starting Slow Motion Registration Demo")
    print("=" * 50)
    
    with sync_playwright() as p:
        # Launch browser in non-headless mode with slow motion
        browser = p.chromium.launch(
            headless=False,  # Show the browser
            slow_mo=1000,    # 1 second delay between actions
            args=[
                "--start-maximized",  # Start with maximized window
                "--disable-dev-shm-usage",
            ]
        )
        
        # Create context with larger viewport
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
            
            # Check if we're on the login page
            print("🔍 Checking page content...")
            page_title = page.title()
            print(f"📄 Page title: {page_title}")
            
            # Look for registration elements
            print("🔍 Looking for registration form...")
            
            # Try to find and click register tab/button
            register_selectors = [
                'button:has-text("Register")',
                'a:has-text("Register")',
                '[data-tab="register"]',
                '.tab:has-text("Register")',
                "#register-tab",
                'li:has-text("Register")',
                '.nav-link:has-text("Register")',
                '[href="#register"]',
                '[data-toggle="tab"]:has-text("Register")',
            ]
            
            register_clicked = False
            for selector in register_selectors:
                elements = page.locator(selector)
                count = elements.count()
                print(f"🔍 Selector '{selector}': found {count} elements")
                
                if count > 0:
                    try:
                        if elements.first.is_visible():
                            print(f"✅ Clicking visible element: {selector}")
                            elements.first.click()
                            register_clicked = True
                            time.sleep(1)
                            break
                    except Exception as e:
                        print(f"❌ Error with selector {selector}: {e}")
                        continue
            
            if not register_clicked:
                print("⚠️ Could not find register tab, trying to show register form directly...")
                
                # Try to show register form using JavaScript
                page.evaluate("""
                    // Try multiple approaches to show register form
                    const registerForm = document.querySelector('#register, .register-form, [id*="register"]');
                    if (registerForm) {
                        registerForm.style.display = 'block';
                        registerForm.style.visibility = 'visible';
                        registerForm.classList.add('show', 'active');
                        registerForm.classList.remove('hide', 'hidden');
                        console.log('Made register form visible');
                    }
                    
                    // Also try to hide login form
                    const loginForm = document.querySelector('#login, .login-form, [id*="login"]');
                    if (loginForm && loginForm !== registerForm) {
                        loginForm.style.display = 'none';
                        loginForm.classList.remove('show', 'active');
                        loginForm.classList.add('hide', 'hidden');
                    }
                """)
                time.sleep(1)
            
            # Now try to fill the registration form
            print("📝 Filling registration form...")
            
            # Generate unique email
            timestamp = int(time.time())
            test_email = f"demo{timestamp}@example.com"
            
            # Fill email field
            email_selectors = ["#registerEmail", "#email", 'input[type="email"]']
            email_filled = False
            for selector in email_selectors:
                if page.locator(selector).count() > 0:
                    print(f"✍️ Filling email: {selector}")
                    page.fill(selector, test_email)
                    email_filled = True
                    break
            
            if not email_filled:
                print("❌ Could not find email field")
                return
            
            # Fill password field
            password_selectors = ["#registerPassword", "#password", 'input[type="password"]']
            password_filled = False
            for selector in password_selectors:
                if page.locator(selector).count() > 0:
                    print(f"✍️ Filling password: {selector}")
                    page.fill(selector, "DemoPassword123!")
                    password_filled = True
                    break
            
            if not password_filled:
                print("❌ Could not find password field")
                return
            
            # Fill name fields
            first_name_selectors = ["#firstName", "#first_name", 'input[name="firstName"]']
            for selector in first_name_selectors:
                if page.locator(selector).count() > 0:
                    print(f"✍️ Filling first name: {selector}")
                    page.fill(selector, "Demo")
                    break
            
            last_name_selectors = ["#lastName", "#last_name", 'input[name="lastName"]']
            for selector in last_name_selectors:
                if page.locator(selector).count() > 0:
                    print(f"✍️ Filling last name: {selector}")
                    page.fill(selector, "User")
                    break
            
            # Try to fill phone number
            phone_selectors = ["#phoneNumber", "#phone", 'input[name="phoneNumber"]']
            for selector in phone_selectors:
                if page.locator(selector).count() > 0:
                    print(f"✍️ Filling phone: {selector}")
                    page.fill(selector, "555-123-4567")
                    break
            
            # Wait for dropdowns to load
            print("⏳ Waiting for dropdowns to load...")
            time.sleep(2)
            
            # Try to select league
            league_selectors = ["#league", 'select[name="league"]']
            for selector in league_selectors:
                if page.locator(selector).count() > 0:
                    print(f"📋 Selecting league: {selector}")
                    try:
                        page.select_option(selector, "APTA_CHICAGO")
                        break
                    except Exception as e:
                        print(f"⚠️ Could not select league: {e}")
            
            time.sleep(1)
            
            # Try to select club
            club_selectors = ["#club", 'select[name="club"]']
            for selector in club_selectors:
                if page.locator(selector).count() > 0:
                    print(f"📋 Selecting club: {selector}")
                    try:
                        page.select_option(selector, "Tennaqua")
                        break
                    except Exception as e:
                        print(f"⚠️ Could not select club: {e}")
            
            time.sleep(1)
            
            # Try to select series
            series_selectors = ["#series", 'select[name="series"]']
            for selector in series_selectors:
                if page.locator(selector).count() > 0:
                    print(f"📋 Selecting series: {selector}")
                    try:
                        page.select_option(selector, "Series 7")
                        break
                    except Exception as e:
                        print(f"⚠️ Could not select series: {e}")
            
            # Try to select preferences
            ad_selectors = ["#adDeuce", 'select[name="adDeuce"]']
            for selector in ad_selectors:
                if page.locator(selector).count() > 0:
                    print(f"📋 Selecting ad/deuce preference: {selector}")
                    try:
                        page.select_option(selector, "Ad")
                        break
                    except Exception as e:
                        print(f"⚠️ Could not select ad/deuce: {e}")
            
            hand_selectors = ["#dominantHand", 'select[name="dominantHand"]']
            for selector in hand_selectors:
                if page.locator(selector).count() > 0:
                    print(f"📋 Selecting dominant hand: {selector}")
                    try:
                        page.select_option(selector, "Righty")
                        break
                    except Exception as e:
                        print(f"⚠️ Could not select dominant hand: {e}")
            
            # Try to check notifications
            notification_selectors = ["#textNotifications", 'input[name="textNotifications"]']
            for selector in notification_selectors:
                if page.locator(selector).count() > 0:
                    print(f"📋 Checking text notifications: {selector}")
                    try:
                        page.check(selector)
                        break
                    except Exception as e:
                        print(f"⚠️ Could not check notifications: {e}")
            
            print("⏳ Waiting for form to be ready...")
            time.sleep(2)
            
            # Try to submit the form
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Register")',
                'button:has-text("Sign Up")',
                '.submit-button',
                '#submit'
            ]
            
            form_submitted = False
            for selector in submit_selectors:
                if page.locator(selector).count() > 0:
                    submit_button = page.locator(selector).first
                    if submit_button.is_visible() and submit_button.is_enabled():
                        print(f"🚀 Submitting form with: {selector}")
                        submit_button.click()
                        form_submitted = True
                        break
            
            if not form_submitted:
                print("❌ Could not find submit button")
                return
            
            print("⏳ Waiting for registration to complete...")
            time.sleep(5)
            
            # Check if registration was successful
            current_url = page.url
            print(f"📍 Current URL: {current_url}")
            
            if "welcome" in current_url or "mobile" in current_url:
                print("🎉 Registration appears successful!")
            else:
                print("⚠️ Registration may have failed, checking for errors...")
                
                # Look for error messages
                error_selectors = [
                    '.error-message',
                    '.alert-danger',
                    '#error-message',
                    '.registration-error'
                ]
                
                for selector in error_selectors:
                    if page.locator(selector).count() > 0:
                        error_text = page.locator(selector).first.text_content()
                        print(f"❌ Error message: {error_text}")
                        break
            
            print("⏳ Demo complete - keeping browser open for 10 seconds...")
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print("🔚 Closing browser...")
            browser.close()

if __name__ == "__main__":
    demo_registration_slow_motion() 