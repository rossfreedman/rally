#!/usr/bin/env python3
"""
Demo Slow Motion Browser Automation V2
Enhanced version that shows detailed slow motion interactions
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

def demo_slow_motion_v2():
    """Enhanced demo with better UI handling"""
    
    print("🎬 Starting Enhanced Slow Motion Demo")
    print("=" * 50)
    
    with sync_playwright() as p:
        # Launch browser with slower motion for better visibility
        browser = p.chromium.launch(
            headless=False,  # Show the browser
            slow_mo=2000,    # 2 second delay between actions for better visibility
            args=[
                "--start-maximized",
                "--disable-dev-shm-usage",
                "--disable-web-security",
            ]
        )
        
        # Create context with larger viewport
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            ignore_https_errors=True,
        )
        
        # Create page
        page = context.new_page()
        
        try:
            print("🌐 Navigating to Rally login page...")
            page.goto("http://localhost:8080/login")
            page.wait_for_load_state("networkidle")
            
            print("⏳ Waiting for page to load...")
            time.sleep(3)
            
            # Check page content
            print("🔍 Analyzing page structure...")
            page_title = page.title()
            print(f"📄 Page title: {page_title}")
            
            # Take a screenshot to see what we're working with
            page.screenshot(path="ui_tests/screenshots/demo_start.png")
            print("📸 Screenshot saved: ui_tests/screenshots/demo_start.png")
            
            # Look for all buttons and links
            print("🔍 Finding all interactive elements...")
            buttons = page.locator("button").all()
            links = page.locator("a").all()
            
            print(f"📋 Found {len(buttons)} buttons and {len(links)} links")
            
            # Show button texts
            for i, button in enumerate(buttons[:5]):
                try:
                    text = button.text_content().strip()
                    print(f"   Button {i}: '{text}'")
                except:
                    print(f"   Button {i}: [Could not get text]")
            
            # Show link texts
            for i, link in enumerate(links[:5]):
                try:
                    text = link.text_content().strip()
                    href = link.get_attribute("href")
                    print(f"   Link {i}: '{text}' -> {href}")
                except:
                    print(f"   Link {i}: [Could not get text]")
            
            # Try to find registration form
            print("🔍 Looking for registration form...")
            
            # Check for form elements
            forms = page.locator("form").all()
            print(f"📋 Found {len(forms)} forms")
            
            for i, form in enumerate(forms):
                try:
                    form_id = form.get_attribute("id")
                    form_class = form.get_attribute("class")
                    print(f"   Form {i}: id='{form_id}', class='{form_class}'")
                except:
                    print(f"   Form {i}: [Could not get attributes]")
            
            # Try to show registration form using JavaScript
            print("🔧 Attempting to show registration form...")
            
            result = page.evaluate("""
                // Try to find and show registration form
                const forms = document.querySelectorAll('form');
                let foundForm = null;
                
                for (let form of forms) {
                    const formText = form.textContent.toLowerCase();
                    if (formText.includes('register') || formText.includes('sign up')) {
                        foundForm = form;
                        break;
                    }
                }
                
                if (!foundForm) {
                    // Look for any form with registration fields
                    const emailFields = document.querySelectorAll('input[type="email"]');
                    for (let field of emailFields) {
                        const form = field.closest('form');
                        if (form) {
                            foundForm = form;
                            break;
                        }
                    }
                }
                
                if (foundForm) {
                    // Make the form visible
                    foundForm.style.display = 'block';
                    foundForm.style.visibility = 'visible';
                    foundForm.classList.add('show', 'active');
                    foundForm.classList.remove('hide', 'hidden');
                    
                    // Also try to hide other forms
                    for (let form of forms) {
                        if (form !== foundForm) {
                            form.style.display = 'none';
                            form.classList.remove('show', 'active');
                        }
                    }
                    
                    return {
                        success: true,
                        formId: foundForm.id,
                        formClass: foundForm.className
                    };
                }
                
                return { success: false, message: 'No registration form found' };
            """)
            
            print(f"🔧 JavaScript result: {result}")
            
            time.sleep(2)
            
            # Take another screenshot
            page.screenshot(path="ui_tests/screenshots/demo_after_js.png")
            print("📸 Screenshot saved: ui_tests/screenshots/demo_after_js.png")
            
            # Now try to fill the form fields
            print("📝 Starting form filling process...")
            
            # Generate unique email
            timestamp = int(time.time())
            test_email = f"demo{timestamp}@example.com"
            
            # Fill email field with slow motion
            print(f"✍️ Filling email: {test_email}")
            email_field = page.locator("#registerEmail")
            if email_field.count() > 0:
                email_field.fill(test_email)
                time.sleep(1)
            else:
                print("⚠️ Email field not found")
            
            # Fill password field
            print("✍️ Filling password...")
            password_field = page.locator("#registerPassword")
            if password_field.count() > 0:
                password_field.fill("DemoPassword123!")
                time.sleep(1)
            else:
                print("⚠️ Password field not found")
            
            # Fill first name
            print("✍️ Filling first name...")
            first_name_field = page.locator("#firstName")
            if first_name_field.count() > 0:
                first_name_field.fill("Demo")
                time.sleep(1)
            else:
                print("⚠️ First name field not found")
            
            # Fill last name
            print("✍️ Filling last name...")
            last_name_field = page.locator("#lastName")
            if last_name_field.count() > 0:
                last_name_field.fill("User")
                time.sleep(1)
            else:
                print("⚠️ Last name field not found")
            
            # Fill phone number
            print("✍️ Filling phone number...")
            phone_field = page.locator("#phoneNumber")
            if phone_field.count() > 0:
                phone_field.fill("555-123-4567")
                time.sleep(1)
            else:
                print("⚠️ Phone field not found")
            
            # Wait for dropdowns
            print("⏳ Waiting for dropdowns to load...")
            time.sleep(3)
            
            # Select league
            print("📋 Selecting league...")
            league_select = page.locator("#league")
            if league_select.count() > 0:
                try:
                    league_select.select_option("APTA_CHICAGO")
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Could not select league: {e}")
            
            # Select club
            print("📋 Selecting club...")
            club_select = page.locator("#club")
            if club_select.count() > 0:
                try:
                    club_select.select_option("Tennaqua")
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Could not select club: {e}")
            
            # Select series
            print("📋 Selecting series...")
            series_select = page.locator("#series")
            if series_select.count() > 0:
                try:
                    series_select.select_option("Series 7")
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Could not select series: {e}")
            
            # Select preferences
            print("📋 Selecting ad/deuce preference...")
            ad_select = page.locator("#adDeuce")
            if ad_select.count() > 0:
                try:
                    ad_select.select_option("Ad")
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Could not select ad/deuce: {e}")
            
            print("📋 Selecting dominant hand...")
            hand_select = page.locator("#dominantHand")
            if hand_select.count() > 0:
                try:
                    hand_select.select_option("Righty")
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Could not select dominant hand: {e}")
            
            # Check notifications
            print("📋 Checking text notifications...")
            notification_checkbox = page.locator("#textNotifications")
            if notification_checkbox.count() > 0:
                try:
                    notification_checkbox.check()
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Could not check notifications: {e}")
            
            # Take screenshot of filled form
            page.screenshot(path="ui_tests/screenshots/demo_filled_form.png")
            print("📸 Screenshot saved: ui_tests/screenshots/demo_filled_form.png")
            
            # Look for submit button
            print("🔍 Looking for submit button...")
            
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
                
                # Take final screenshot
                page.screenshot(path="ui_tests/screenshots/demo_after_submit.png")
                print("📸 Screenshot saved: ui_tests/screenshots/demo_after_submit.png")
                
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
            
            print("⏳ Demo complete - keeping browser open for 15 seconds...")
            time.sleep(15)
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
            
            # Take error screenshot
            page.screenshot(path="ui_tests/screenshots/demo_error.png")
            print("📸 Error screenshot saved: ui_tests/screenshots/demo_error.png")
        
        finally:
            print("🔚 Closing browser...")
            browser.close()

if __name__ == "__main__":
    demo_slow_motion_v2() 