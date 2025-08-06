#!/usr/bin/env python3
"""
Configure SMS alerts for proxy monitoring
"""

import os
import sys

def check_twilio_config():
    """Check if Twilio is configured."""
    required_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN", 
        "TWILIO_SENDER_PHONE"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars

def setup_sms_config():
    """Set up SMS configuration."""
    print("📱 SMS Alert Configuration")
    print("=" * 30)
    
    # Check current configuration
    missing_vars = check_twilio_config()
    
    if not missing_vars:
        print("✅ Twilio is already configured!")
        return True
    
    print(f"❌ Missing Twilio configuration: {', '.join(missing_vars)}")
    print("\nTo configure SMS alerts, you need to:")
    print("1. Sign up for a Twilio account at https://www.twilio.com")
    print("2. Get your Account SID and Auth Token from the Twilio Console")
    print("3. Get a phone number for sending SMS")
    print("4. Set the following environment variables:")
    
    print("\n📋 Required Environment Variables:")
    print("export TWILIO_ACCOUNT_SID='your_account_sid'")
    print("export TWILIO_AUTH_TOKEN='your_auth_token'")
    print("export TWILIO_SENDER_PHONE='+1234567890'")
    
    print("\n🔧 Alternative: Add to your .env file:")
    print("TWILIO_ACCOUNT_SID=your_account_sid")
    print("TWILIO_AUTH_TOKEN=your_auth_token")
    print("TWILIO_SENDER_PHONE=+1234567890")
    
    # Test if we can create a .env file
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"\n⚠️ {env_file} already exists. Add these lines to it:")
    else:
        print(f"\n📝 Creating {env_file} file...")
        with open(env_file, "w") as f:
            f.write("# Twilio SMS Configuration\n")
            f.write("TWILIO_ACCOUNT_SID=your_account_sid\n")
            f.write("TWILIO_AUTH_TOKEN=your_auth_token\n")
            f.write("TWILIO_SENDER_PHONE=+1234567890\n")
        print(f"✅ Created {env_file} file")
    
    return False

def test_sms_functionality():
    """Test SMS functionality if configured."""
    missing_vars = check_twilio_config()
    
    if missing_vars:
        print("❌ Cannot test SMS - Twilio not configured")
        return False
    
    try:
        from data.etl.scrapers.proxy_manager import send_urgent_sms
        
        # Test SMS
        test_message = "🧪 Rally Proxy Test: SMS alerts are working!"
        result = send_urgent_sms(test_message)
        
        if result:
            print("✅ SMS test successful!")
            return True
        else:
            print("❌ SMS test failed")
            return False
            
    except Exception as e:
        print(f"❌ SMS test failed: {e}")
        return False

def create_sms_monitoring_script():
    """Create a script to monitor proxy health with SMS alerts."""
    monitoring_script = '''#!/usr/bin/env python3
"""
Proxy Health Monitoring with SMS Alerts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.etl.scrapers.proxy_manager import get_proxy_rotator, send_urgent_sms
import time

def monitor_proxy_health():
    """Monitor proxy health and send SMS alerts."""
    print("📊 Proxy Health Monitor")
    print("=" * 30)
    
    rotator = get_proxy_rotator()
    
    while True:
        try:
            # Get current status
            status = rotator.get_status()
            
            # Check for critical issues
            healthy_proxies = status['healthy_proxies']
            total_proxies = status['total_proxies']
            dead_proxies = status['dead_proxies']
            
            # Calculate health percentage
            health_percentage = (healthy_proxies / total_proxies) * 100
            
            print(f"📊 Health: {health_percentage:.1f}% ({healthy_proxies}/{total_proxies})")
            
            # Send alerts for critical issues
            if health_percentage < 50:
                message = f"🚨 CRITICAL: Proxy health at {health_percentage:.1f}% ({healthy_proxies}/{total_proxies} healthy)"
                send_urgent_sms(message)
                print(f"📱 Sent SMS alert: {message}")
            
            elif dead_proxies > 10:
                message = f"⚠️ WARNING: {dead_proxies} dead proxies detected"
                send_urgent_sms(message)
                print(f"📱 Sent SMS alert: {message}")
            
            # Wait 5 minutes before next check
            time.sleep(300)
            
        except Exception as e:
            error_message = f"❌ Proxy monitor error: {e}"
            send_urgent_sms(error_message)
            print(error_message)
            time.sleep(60)

if __name__ == "__main__":
    monitor_proxy_health()
'''
    
    with open("scripts/monitor_proxy_health.py", "w") as f:
        f.write(monitoring_script)
    
    print("✅ Created proxy health monitoring script: scripts/monitor_proxy_health.py")
    print("   Run with: python3 scripts/monitor_proxy_health.py")

def main():
    """Main function."""
    print("📱 SMS Alert Configuration Tool")
    print("=" * 40)
    
    # Step 1: Check current configuration
    print("\n1. Checking current SMS configuration...")
    if setup_sms_config():
        print("✅ SMS is configured!")
        
        # Step 2: Test SMS functionality
        print("\n2. Testing SMS functionality...")
        if test_sms_functionality():
            print("✅ SMS alerts are working!")
        else:
            print("❌ SMS test failed")
    
    # Step 3: Create monitoring script
    print("\n3. Creating proxy health monitoring script...")
    create_sms_monitoring_script()
    
    print("\n📋 Next Steps:")
    print("1. Configure Twilio credentials (see above)")
    print("2. Test SMS functionality: python3 scripts/configure_sms_alerts.py")
    print("3. Start monitoring: python3 scripts/monitor_proxy_health.py")
    print("4. SMS alerts will be sent automatically for critical proxy issues")

if __name__ == "__main__":
    main() 