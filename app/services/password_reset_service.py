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
from database_utils import execute_query_one, execute_update
from utils.logging import log_user_activity

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_ATTEMPTS = 3  # Max attempts per email per time window
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds


def send_password_via_sms(email: str) -> Dict[str, any]:
    """
    Send user's password via SMS to their registered phone number
    
    Args:
        email (str): User's email address
        
    Returns:
        Dict: Result with success status and message/error
    """
    try:
        # Normalize email
        email = email.strip().lower()
        
        # Check rate limiting first
        if not _check_rate_limit(email):
            logger.warning(f"Rate limit exceeded for password reset: {email}")
            return {
                "success": False,
                "error": "Too many password reset attempts. Please try again in 5 minutes."
            }
        
        # Find user by email
        user = _find_user_by_email(email)
        if not user:
            # Log the attempt but don't reveal if email exists
            logger.warning(f"Password reset attempted for non-existent email: {email}")
            _log_password_reset_attempt(email, success=False, reason="user_not_found")
            
            # Return generic message for security
            return {
                "success": False,
                "error": "If this email is registered, you will receive a text with your password."
            }
        
        # Check if user has a phone number
        if not user.get("phone_number"):
            logger.warning(f"Password reset attempted for user without phone: {email}")
            _log_password_reset_attempt(email, success=False, reason="no_phone")
            return {
                "success": False,
                "error": "No phone number on file. Please contact support to update your profile."
            }
        
        # Get the user's actual password
        # Note: In a production environment, you'd typically send a reset token instead
        # But the user specifically requested sending the actual password
        password = _get_user_password(user["id"])
        if not password:
            logger.error(f"Could not retrieve password for user {email}")
            _log_password_reset_attempt(email, success=False, reason="password_error")
            return {
                "success": False,
                "error": "Unable to retrieve password. Please contact support."
            }
        
        # Create SMS message
        message = f"🔐 Rally Password Reset\n\nYour temporary password is: {password}\n\nPlease log in and change this password immediately for security.\n\nAfter you login, you can change your password in your profile (bottom right corner in the app).\n\n- Rally Team"
        
        # Send SMS using existing notification service
        sms_result = send_sms_notification(
            to_number=user["phone_number"],
            message=message,
            test_mode=False
        )
        
        if sms_result["success"]:
            logger.info(f"Password reset SMS sent successfully to {email}")
            _log_password_reset_attempt(email, success=True, reason="sms_sent")
            _record_rate_limit_attempt(email)
            
            return {
                "success": True,
                "message": f"Password sent to your phone ending in {user['phone_number'][-4:]}!"
            }
        else:
            logger.error(f"Failed to send password reset SMS to {email}: {sms_result.get('error')}")
            _log_password_reset_attempt(email, success=False, reason="sms_failed")
            return {
                "success": False,
                "error": "Failed to send text message. Please try again or contact support."
            }
    
    except Exception as e:
        logger.error(f"Error in password reset for {email}: {str(e)}")
        _log_password_reset_attempt(email, success=False, reason="system_error")
        return {
            "success": False,
            "error": "An error occurred. Please try again later."
        }


def _find_user_by_email(email: str) -> Optional[Dict]:
    """Find user by email address"""
    try:
        query = """
            SELECT 
                id,
                email,
                first_name,
                last_name,
                phone_number
            FROM users 
            WHERE email = %s
        """
        return execute_query_one(query, [email])
    except Exception as e:
        logger.error(f"Error finding user by email {email}: {str(e)}")
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
        
        # Generate a random temporary password (8 characters, mix of letters and numbers)
        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        # Hash the temporary password using pbkdf2:sha256 method (compatible with most environments)
        password_hash = generate_password_hash(temp_password, method='pbkdf2:sha256')
        
        # Update user's password in database
        update_query = """
            UPDATE users 
            SET password_hash = %s 
            WHERE id = %s
        """
        
        result = execute_update(update_query, [password_hash, user_id])
        
        if result:
            logger.info(f"Temporary password generated and set for user {user_id}")
            return temp_password
        else:
            logger.error(f"Failed to update password for user {user_id}")
            return None
        
    except Exception as e:
        logger.error(f"Error generating temporary password for user {user_id}: {str(e)}")
        return None


def _check_rate_limit(email: str) -> bool:
    """Check if email is within rate limit for password reset attempts"""
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
        result = execute_query_one(query, [email, since_time])
        
        if result and result["attempt_count"] >= RATE_LIMIT_ATTEMPTS:
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking rate limit for {email}: {str(e)}")
        # If we can't check rate limit, allow the attempt
        return True


def _record_rate_limit_attempt(email: str):
    """Record a password reset attempt for rate limiting"""
    try:
        _log_password_reset_attempt(email, success=True, reason="rate_limit_record")
    except Exception as e:
        logger.error(f"Error recording rate limit attempt for {email}: {str(e)}")


def _log_password_reset_attempt(email: str, success: bool, reason: str):
    """Log password reset attempt for security monitoring"""
    try:
        log_user_activity(
            user_email=email,
            activity_type="password_reset",
            details={
                "success": success,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": _get_request_ip()
            }
        )
    except Exception as e:
        logger.error(f"Error logging password reset attempt for {email}: {str(e)}")


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