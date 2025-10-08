#!/usr/bin/env python3
"""
Admin Password Reset Script
==========================

This script allows administrators to:
1. Look up user information by email or phone
2. Reset user passwords and send via SMS
3. Check user registration details

Usage:
    python scripts/admin_password_reset.py --lookup lindafranke17@gmail.com
    python scripts/admin_password_reset.py --reset lindafranke17@gmail.com
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Optional, List

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update
from app.services.notifications_service import send_sms_notification
from werkzeug.security import generate_password_hash
import secrets
import string

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Production database connection
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def lookup_user_by_email(email: str) -> Optional[Dict]:
    """Look up user information by email address"""
    try:
        query = """
            SELECT 
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.phone_number,
                u.is_admin,
                u.has_temporary_password,
                u.temporary_password_set_at,
                u.created_at,
                u.last_login,
                u.league_context,
                l.league_name,
                c.name as club_name,
                s.name as series_name,
                t.team_name
            FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = true
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE LOWER(u.email) = LOWER(%s)
            ORDER BY p.id DESC
            LIMIT 1
        """
        
        result = execute_query_one(query, [email])
        return result
        
    except Exception as e:
        logger.error(f"Error looking up user by email {email}: {str(e)}")
        return None

def lookup_user_by_phone(phone: str) -> Optional[Dict]:
    """Look up user information by phone number"""
    try:
        # Normalize phone number
        normalized_phone = ''.join(filter(str.isdigit, phone))
        if normalized_phone.startswith('1') and len(normalized_phone) == 11:
            normalized_phone = normalized_phone[1:]  # Remove leading 1
        
        # Try multiple phone number formats
        phone_variations = [
            normalized_phone,
            f"+1{normalized_phone}",
            f"+{normalized_phone}",
            f"1{normalized_phone}",
        ]
        
        for phone_variation in phone_variations:
            query = """
                SELECT 
                    u.id,
                    u.email,
                    u.first_name,
                    u.last_name,
                    u.phone_number,
                    u.is_admin,
                    u.has_temporary_password,
                    u.temporary_password_set_at,
                    u.created_at,
                    u.last_login,
                    u.league_context,
                    l.league_name,
                    c.name as club_name,
                    s.name as series_name,
                    t.team_name
                FROM users u
                LEFT JOIN leagues l ON u.league_context = l.id
                LEFT JOIN user_player_associations upa ON u.id = upa.user_id
                LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = true
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE u.phone_number = %s
                ORDER BY p.id DESC
                LIMIT 1
            """
            
            result = execute_query_one(query, [phone_variation])
            if result:
                return result
        
        return None
        
    except Exception as e:
        logger.error(f"Error looking up user by phone {phone}: {str(e)}")
        return None

def generate_temp_password() -> str:
    """Generate a temporary password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))

def reset_user_password(email: str) -> Dict:
    """Reset user password and send via SMS"""
    try:
        # Look up user
        user = lookup_user_by_email(email)
        if not user:
            return {"success": False, "error": f"User not found: {email}"}
        
        if not user['phone_number']:
            return {"success": False, "error": f"No phone number registered for {email}"}
        
        # Generate temporary password
        temp_password = generate_temp_password()
        password_hash = generate_password_hash(temp_password, method='pbkdf2:sha256')
        
        # Update user's password in database
        update_query = """
            UPDATE users 
            SET password_hash = %s, 
                has_temporary_password = TRUE,
                temporary_password_set_at = NOW()
            WHERE id = %s
        """
        
        rows_updated = execute_update(update_query, [password_hash, user['id']])
        
        if rows_updated == 0:
            return {"success": False, "error": "Failed to update password in database"}
        
        # Send SMS with temporary password
        sms_message = f"Rally Password Reset: Your temporary password is {temp_password}. Please change it after logging in."
        
        sms_result = send_sms_notification(
            to_number=user['phone_number'],
            message=sms_message
        )
        
        if sms_result.get('success'):
            return {
                "success": True, 
                "message": f"Password reset successful. Temporary password sent to {user['phone_number']}",
                "temp_password": temp_password,
                "phone": user['phone_number']
            }
        else:
            return {
                "success": False, 
                "error": f"Password updated but SMS failed: {sms_result.get('error', 'Unknown error')}",
                "temp_password": temp_password,
                "phone": user['phone_number']
            }
            
    except Exception as e:
        logger.error(f"Error resetting password for {email}: {str(e)}")
        return {"success": False, "error": f"Password reset failed: {str(e)}"}

def print_user_info(user: Dict):
    """Print user information in a formatted way"""
    if not user:
        print("❌ User not found")
        return
    
    print(f"\n👤 User Information:")
    print(f"   Name: {user.get('first_name', 'N/A')} {user.get('last_name', 'N/A')}")
    print(f"   Email: {user.get('email', 'N/A')}")
    print(f"   Phone: {user.get('phone_number', 'N/A')}")
    print(f"   Admin: {'Yes' if user.get('is_admin') else 'No'}")
    print(f"   Has Temporary Password: {'Yes' if user.get('has_temporary_password') else 'No'}")
    print(f"   Created: {user.get('created_at', 'N/A')}")
    print(f"   Last Login: {user.get('last_login', 'N/A')}")
    print(f"   League Context: {user.get('league_name', 'N/A')}")
    print(f"   Club: {user.get('club_name', 'N/A')}")
    print(f"   Series: {user.get('series_name', 'N/A')}")
    print(f"   Team: {user.get('team_name', 'N/A')}")
    
    if user.get('temporary_password_set_at'):
        print(f"   Temporary Password Set: {user.get('temporary_password_set_at')}")

def main():
    parser = argparse.ArgumentParser(description='Admin Password Reset Tool')
    parser.add_argument('--lookup', help='Look up user by email')
    parser.add_argument('--lookup-phone', help='Look up user by phone number')
    parser.add_argument('--reset', help='Reset password for user by email')
    parser.add_argument('--email', help='Email address for operations')
    parser.add_argument('--phone', help='Phone number for operations')
    
    args = parser.parse_args()
    
    if args.lookup:
        print(f"🔍 Looking up user: {args.lookup}")
        user = lookup_user_by_email(args.lookup)
        print_user_info(user)
        
    elif args.lookup_phone:
        print(f"🔍 Looking up user by phone: {args.lookup_phone}")
        user = lookup_user_by_phone(args.lookup_phone)
        print_user_info(user)
        
    elif args.reset:
        print(f"🔄 Resetting password for: {args.reset}")
        result = reset_user_password(args.reset)
        
        if result['success']:
            print(f"✅ {result['message']}")
            if 'temp_password' in result:
                print(f"   Temporary Password: {result['temp_password']}")
        else:
            print(f"❌ {result['error']}")
            
    else:
        print("Please specify an action: --lookup, --lookup-phone, or --reset")
        print("\nExamples:")
        print("  python scripts/admin_password_reset.py --lookup lindafranke17@gmail.com")
        print("  python scripts/admin_password_reset.py --reset lindafranke17@gmail.com")
        print("  python scripts/admin_password_reset.py --lookup-phone +1234567890")

if __name__ == "__main__":
    main()
