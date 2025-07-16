"""
Password Reset Service
=====================

This module handles password reset functionality via SMS using Twilio.
Includes security logging and rate limiting to prevent abuse.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.models.database_models import SessionLocal, User
from app.services.notifications_service import send_sms_notification
from database_utils import execute_query_one, execute_update, execute_query
from utils.logging import log_user_activity

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_ATTEMPTS = 3  # Max attempts per email per time window
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds


def send_password_via_sms(phone: str, email: str = None) -> dict:
    """
    Send user's password via SMS to their registered phone number
    Args:
        phone (str): User's phone number
        email (str, optional): User's email address (for disambiguation when multiple users have same phone)
    Returns:
        Dict: Result with success status and message/error
    """
    try:
        # Normalize phone number
        phone = phone.strip()
        
        # Check rate limiting first
        if not _check_rate_limit(phone):
            logger.warning(f"Rate limit exceeded for password reset: {phone}")
            return {
                "success": False,
                "error": "Too many password reset attempts. Please try again in 5 minutes."
            }
        
        # Find all users with this phone number (using flexible matching)
        # Use the same logic as _find_user_by_phone, but return all matches
        normalized_phone = ''.join(filter(str.isdigit, phone))
        if normalized_phone.startswith('1') and len(normalized_phone) == 11:
            normalized_phone = normalized_phone[1:]
        phone_variations = [
            normalized_phone,
            f"+1{normalized_phone}",
            f"+{normalized_phone}",
            f"1{normalized_phone}",
        ]
        all_matches = []
        for phone_variation in phone_variations:
            query = """
                SELECT id, email, first_name, last_name, phone_number, last_login, created_at
                FROM users
                WHERE phone_number = %s
            """
            users = execute_query(query, [phone_variation])
            if users:
                for user in users:
                    if not any(match['id'] == user['id'] for match in all_matches):
                        all_matches.append(user)
        # Also try partial match if no exact
        if not all_matches:
            partial_query = """
                SELECT id, email, first_name, last_name, phone_number, last_login, created_at
                FROM users
                WHERE REPLACE(REPLACE(REPLACE(phone_number, '+', ''), '-', ''), ' ', '') LIKE %s
            """
            partial_phone = f"%{normalized_phone}%"
            partial_users = execute_query(partial_query, [partial_phone])
            if partial_users:
                for user in partial_users:
                    if not any(match['id'] == user['id'] for match in all_matches):
                        all_matches.append(user)
        
        # No matches
        if not all_matches:
            logger.warning(f"Password reset attempted for non-existent phone: {phone}")
            _log_password_reset_attempt(phone, success=False, reason="user_not_found")
            return {
                "success": False,
                "error": "If this phone number is registered, you will receive a text with your password."
            }
        
        # One match: proceed without requiring email
        if len(all_matches) == 1:
            user = all_matches[0]
        else:
            # Multiple matches: automatically select the most recently active user
            # Sort by last_login (most recent first), then by created_at (most recent first)
            all_matches.sort(key=lambda u: (
                u['last_login'] or datetime.min,  # None values go to the end
                u['created_at'] or datetime.min
            ), reverse=True)
            
            # Select the most recently active user
            user = all_matches[0]
            
            # Log which user was selected for transparency
            logger.info(f"Multiple users found for phone {phone}, selected most recent: {user['email']} (last_login: {user['last_login']})")
            
            # If email was provided, try to match it first
            if email:
                email_match = next((u for u in all_matches if u['email'].lower() == email.strip().lower()), None)
                if email_match:
                    user = email_match
                    logger.info(f"Email match found, using: {user['email']}")
        
        # Get the user's actual password
        # Note: In a production environment, you'd typically send a reset token instead
        # But the user specifically requested sending the actual password
        password = _get_user_password(user["id"])
        if not password:
            logger.error(f"Could not retrieve password for user {phone}")
            _log_password_reset_attempt(phone, success=False, reason="password_error")
            return {
                "success": False,
                "error": "Unable to retrieve password. Please contact support."
            }
        
        # Create SMS message with link back to Rally
        message = f"🔐 Rally Password Reset\n\nForgot your password? No problem!\n\nYour temporary password is: {password}\n\nPlease log in and change your password to something you will remember.\n\nLogin: https://www.lovetorally.com/login\n\n- Rally Team"
        
        # Send SMS using existing notification service
        sms_result = send_sms_notification(
            to_number=user["phone_number"],
            message=message,
            test_mode=False
        )
        
        if sms_result["success"]:
            logger.info(f"Password reset SMS sent successfully to {phone}")
            _log_password_reset_attempt(phone, success=True, reason="sms_sent")
            _record_rate_limit_attempt(phone)
            
            return {
                "success": True,
                "message": f"Password sent to your phone ending in {user['phone_number'][-4:]}!"
            }
        else:
            logger.error(f"Failed to send password reset SMS to {phone}: {sms_result.get('error')}")
            _log_password_reset_attempt(phone, success=False, reason="sms_failed")
            return {
                "success": False,
                "error": "Failed to send text message. Please try again or contact support."
            }
    
    except Exception as e:
        logger.error(f"Error in password reset for {phone}: {str(e)}")
        _log_password_reset_attempt(phone, success=False, reason="system_error")
        return {
            "success": False,
            "error": "An error occurred. Please try again later."
        }


def _find_user_by_phone(phone: str) -> Optional[Dict]:
    """Find user by phone number with flexible matching"""
    try:
        # First check if phone_number column exists
        column_check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'phone_number'
        """
        column_exists = execute_query_one(column_check_query)
        
        if not column_exists:
            logger.error("phone_number column does not exist in users table")
            return None
        
        # Normalize phone number (remove +1, spaces, dashes, etc.)
        normalized_phone = ''.join(filter(str.isdigit, phone))
        if normalized_phone.startswith('1') and len(normalized_phone) == 11:
            normalized_phone = normalized_phone[1:]  # Remove leading 1
        
        logger.info(f"Looking up user by normalized phone: {normalized_phone}")
        
        # Try multiple phone number formats and collect all matches
        phone_variations = [
            normalized_phone,                    # 7732138911
            f"+1{normalized_phone}",            # +17732138911
            f"+{normalized_phone}",             # +7732138911
            f"1{normalized_phone}",             # 17732138911
        ]
        
        all_matches = []
        
        for phone_variation in phone_variations:
            query = """
                SELECT 
                    id,
                    email,
                    first_name,
                    last_name,
                    phone_number
                FROM users 
                WHERE phone_number = %s
            """
            users = execute_query(query, [phone_variation])
            
            if users:
                for user in users:
                    # Avoid duplicates
                    if not any(match['id'] == user['id'] for match in all_matches):
                        all_matches.append(user)
                        logger.info(f"Found user by phone variation '{phone_variation}': {user['email']}")
        
        # If no exact matches, try partial match
        if not all_matches:
            partial_query = """
                SELECT 
                    id,
                    email,
                    first_name,
                    last_name,
                    phone_number
                FROM users 
                WHERE REPLACE(REPLACE(REPLACE(phone_number, '+', ''), '-', ''), ' ', '') LIKE %s
            """
            partial_phone = f"%{normalized_phone}%"
            partial_users = execute_query(partial_query, [partial_phone])
            
            if partial_users:
                for user in partial_users:
                    if not any(match['id'] == user['id'] for match in all_matches):
                        all_matches.append(user)
                        logger.info(f"Found user by partial phone match: {user['email']}")
        
        # Handle multiple matches
        if len(all_matches) == 0:
            logger.warning(f"No user found for phone number: {phone} (normalized: {normalized_phone})")
            return None
        elif len(all_matches) == 1:
            logger.info(f"Single user found: {all_matches[0]['email']}")
            return all_matches[0]
        else:
            # Multiple users found - log all matches and return the first one
            logger.warning(f"Multiple users found for phone {phone}: {[u['email'] for u in all_matches]}")
            logger.info(f"Returning first match: {all_matches[0]['email']}")
            return all_matches[0]
        
    except Exception as e:
        logger.error(f"Error finding user by phone {phone}: {str(e)}")
        return None


def _get_user_password(user_id: int) -> Optional[str]:
    """
    Generate and set a temporary password for the user
    Since password hashes cannot be decrypted, we generate a new temporary password
    """
    try:
        import secrets
        import string
        from werkzeug.security import generate_password_hash
        
        # Generate a random temporary password (6 characters, mix of letters and numbers)
        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(6))
        
        # Hash the temporary password using pbkdf2:sha256 method (compatible with most environments)
        password_hash = generate_password_hash(temp_password, method='pbkdf2:sha256')
        
        # Update user's password in database and set temporary password flag
        update_query = """
            UPDATE users 
            SET password_hash = %s, 
                has_temporary_password = TRUE,
                temporary_password_set_at = NOW()
            WHERE id = %s
        """
        
        logger.info(f"Attempting to update password for user {user_id}")
        result = execute_update(update_query, [password_hash, user_id])
        
        if result:
            logger.info(f"Temporary password generated and set for user {user_id} - {result} rows affected")
            return temp_password
        else:
            logger.error(f"Failed to update password for user {user_id} - no rows affected")
            return None
        
    except Exception as e:
        logger.error(f"Error generating temporary password for user {user_id}: {str(e)}")
        return None


def _check_rate_limit(phone: str) -> bool:
    """Check if phone is within rate limit for password reset attempts"""
    try:
        # Check recent attempts in the time window
        since_time = datetime.utcnow() - timedelta(seconds=RATE_LIMIT_WINDOW)
        
        query = """
            SELECT COUNT(*) as attempt_count
            FROM user_activity_logs 
            WHERE user_email = %s 
            AND activity_type = 'password_reset'
            AND timestamp > %s
        """
        result = execute_query_one(query, [phone, since_time])
        
        if result and result["attempt_count"] >= RATE_LIMIT_ATTEMPTS:
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking rate limit for {phone}: {str(e)}")
        # If we can't check rate limit, allow the attempt
        return True


def _record_rate_limit_attempt(phone: str):
    """Record a password reset attempt for rate limiting"""
    try:
        _log_password_reset_attempt(phone, success=True, reason="rate_limit_record")
    except Exception as e:
        logger.error(f"Error recording rate limit attempt for {phone}: {str(e)}")


def _log_password_reset_attempt(phone: str, success: bool, reason: str):
    """Log password reset attempt for security monitoring"""
    try:
        log_user_activity(
            user_email=phone,  # Using phone as identifier since we don't have email
            activity_type="password_reset",
            details={
                "success": success,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": _get_request_ip()
            }
        )
    except Exception as e:
        logger.error(f"Error logging password reset attempt for {phone}: {str(e)}")


def _get_request_ip() -> str:
    """Get client IP address from request"""
    try:
        from flask import request
        # Check for forwarded IP first (for load balancers/proxies)
        forwarded_ip = request.headers.get('X-Forwarded-For')
        if forwarded_ip:
            return forwarded_ip.split(',')[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
        
        # Fallback to remote address
        return request.remote_addr or "unknown"
    except Exception:
        return "unknown" 