#!/usr/bin/env python3
"""
SendGrid Setup Helper
====================

This script helps you set up and verify your SendGrid API key.
It provides step-by-step instructions and validates your configuration.

Usage:
    python scripts/setup_sendgrid.py
"""

import os
import sys
import getpass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_current_setup():
    """Check current SendGrid setup"""
    print("🔍 Checking Current SendGrid Setup")
    print("=" * 50)
    
    api_key = os.getenv('SENDGRID_API_KEY')
    from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@lovetorally.com')
    admin_email = os.getenv('ADMIN_EMAIL', 'rossfreedman@gmail.com')
    
    if api_key:
        print(f"✅ API Key found: {api_key[:10]}...")
        print(f"✅ From Email: {from_email}")
        print(f"✅ Admin Email: {admin_email}")
        return True
    else:
        print("❌ No SendGrid API key found")
        return False

def get_sendgrid_instructions():
    """Show instructions for getting SendGrid API key"""
    print("\n📋 How to Get a Valid SendGrid API Key")
    print("=" * 50)
    print("1. Go to https://app.sendgrid.com")
    print("2. Log in to your SendGrid account")
    print("3. Navigate to Settings → API Keys")
    print("4. Click 'Create API Key'")
    print("5. Choose 'Full Access' or create restricted key with 'Mail Send' permissions")
    print("6. Copy the generated API key (starts with 'SG.')")
    print("7. IMPORTANT: Save the key immediately - you won't see it again!")
    print("\n📧 Verify Sender Email")
    print("=" * 30)
    print("Before sending emails, you must verify your sender email:")
    print("1. Go to Settings → Sender Authentication")
    print("2. Either verify 'noreply@lovetorally.com' as a single sender")
    print("3. OR authenticate the entire 'lovetorally.com' domain (recommended)")

def update_api_key():
    """Interactive API key update"""
    print("\n🔑 Update SendGrid API Key")
    print("=" * 40)
    
    api_key = getpass.getpass("Enter your SendGrid API key (starts with SG.): ").strip()
    
    if not api_key.startswith('SG.'):
        print("❌ Invalid API key format. SendGrid API keys start with 'SG.'")
        return False
    
    # Update .env file
    env_lines = []
    updated = False
    
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_lines = f.readlines()
    
    # Update or add the API key
    for i, line in enumerate(env_lines):
        if line.startswith('SENDGRID_API_KEY='):
            env_lines[i] = f'SENDGRID_API_KEY={api_key}\n'
            updated = True
            break
    
    if not updated:
        env_lines.append(f'SENDGRID_API_KEY={api_key}\n')
    
    # Write back to .env
    with open('.env', 'w') as f:
        f.writelines(env_lines)
    
    print(f"✅ API key updated in .env file")
    return True

def test_api_key():
    """Test the API key"""
    print("\n🧪 Testing SendGrid API Key")
    print("=" * 40)
    
    try:
        # Reload environment variables
        load_dotenv(override=True)
        
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            print("❌ No API key found")
            return False
        
        # Test with a simple message
        message = Mail(
            from_email='noreply@lovetorally.com',
            to_emails='rossfreedman@gmail.com',
            subject='SendGrid API Test',
            plain_text_content='Testing SendGrid API connection'
        )
        
        sg = SendGridAPIClient(api_key=api_key)
        
        # Try to send (this will fail if sender not verified, but API key will be validated)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            print("✅ API key is valid and email sent successfully!")
            return True
        else:
            print(f"⚠️ API key is valid but email failed: {response.status_code}")
            print("This might be because the sender email is not verified in SendGrid")
            return True
            
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("❌ API key is invalid or expired")
            return False
        elif "403" in error_msg or "Forbidden" in error_msg:
            print("⚠️ API key is valid but sender email not verified")
            print("Please verify 'noreply@lovetorally.com' in SendGrid dashboard")
            return True
        else:
            print(f"❌ Error testing API key: {error_msg}")
            return False

def main():
    print("🚀 SendGrid Setup Helper")
    print("=" * 60)
    
    # Check current setup
    has_key = check_current_setup()
    
    if not has_key:
        get_sendgrid_instructions()
        
        if input("\nDo you have a SendGrid API key ready? (y/n): ").lower().startswith('y'):
            if update_api_key():
                has_key = True
        else:
            print("\n📚 Please follow the instructions above to get your API key first.")
            return False
    
    if has_key:
        print(f"\n🧪 Testing current API key...")
        if test_api_key():
            print("\n🎉 SendGrid is ready to use!")
            print("You can now run: python3 scripts/test_sendgrid_email.py")
            return True
        else:
            print("\n⚠️ API key needs to be updated.")
            if input("Update API key now? (y/n): ").lower().startswith('y'):
                if update_api_key():
                    return test_api_key()
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
