#!/usr/bin/env python3
"""
SendGrid Example - Basic Email Sending
=====================================

This script demonstrates basic SendGrid email sending as shown in the SendGrid documentation.
It includes EU data residency support for GDPR compliance.

Usage:
    python scripts/sendgrid_example.py
    python scripts/sendgrid_example.py --eu-residency  # Enable EU data residency
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_basic_email(eu_residency=False):
    """Send basic email using SendGrid API"""
    
    message = Mail(
        from_email='noreply@lovetorally.com',
        to_emails='rossfreedman@gmail.com',
        subject='Sending with Twilio SendGrid is Fun',
        html_content='<strong>and easy to do anywhere, even with Python</strong>'
    )
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        
        # Set EU data residency if requested
        if eu_residency:
            sg.set_sendgrid_data_residency("eu")
            print("🇪🇺 EU data residency enabled")
        
        response = sg.send(message)
        
        print(f"✅ Email sent successfully!")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.body.decode() if response.body else 'None'}")
        print(f"Response Headers: {dict(response.headers)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        if hasattr(e, 'message'):
            print(f"Error message: {e.message}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Send basic email with SendGrid")
    parser.add_argument("--eu-residency", action="store_true", 
                       help="Enable EU data residency for GDPR compliance")
    
    args = parser.parse_args()
    
    print("📧 SendGrid Basic Email Example")
    print("=" * 40)
    print(f"EU Data Residency: {args.eu_residency}")
    print(f"API Key: {os.environ.get('SENDGRID_API_KEY', 'Not set')[:10]}...")
    print()
    
    if not os.environ.get('SENDGRID_API_KEY'):
        print("❌ SENDGRID_API_KEY environment variable not set")
        print("Please add it to your .env file:")
        print("SENDGRID_API_KEY=your_api_key_here")
        return False
    
    success = send_basic_email(eu_residency=args.eu_residency)
    
    if success:
        print("\n🎉 Email sent successfully! Check your inbox.")
    else:
        print("\n❌ Failed to send email. Check the error messages above.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
