"""
Notifications Service
====================

This module handles SMS notifications using Twilio's A2P messaging service.
Supports sending test messages and managing notification preferences.

Enhanced with retry logic for error 21704 (provider disruptions).
"""

import logging
import re
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth

from config import TwilioConfig


# Configure logging
logger = logging.getLogger(__name__)


def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Validate and format phone number for SMS
    
    Args:
        phone (str): Phone number to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, formatted_phone_or_error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid US number
    if len(digits_only) == 10:
        # Add US country code
        formatted = f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # Already has US country code
        formatted = f"+{digits_only}"
    else:
        return False, "Invalid phone number format. Please use a valid US phone number (10 or 11 digits)"
    
    # Additional validation for US numbers
    if not formatted.startswith('+1'):
        return False, "Only US phone numbers are supported"
    
    # Check for valid area code (not starting with 0 or 1)
    area_code = formatted[2:5]
    if area_code.startswith('0') or area_code.startswith('1'):
        return False, "Invalid area code"
    
    return True, formatted


def send_sms_notification(to_number: str, message: str, test_mode: bool = False, max_retries: int = 3) -> Dict:
    """
    Send an SMS using Twilio's Messaging Service API with retry logic for error 21704
    
    Args:
        to_number (str): Recipient phone number
        message (str): Message content
        test_mode (bool): If True, validates but doesn't actually send
        max_retries (int): Maximum number of retry attempts for error 21704
        
    Returns:
        Dict: Result with status, message_sid, and any errors
    """
    
    # Validate configuration
    config_status = TwilioConfig.validate_config()
    if not config_status["is_valid"]:
        return {
            "success": False,
            "error": f"Twilio not configured. Missing: {', '.join(config_status['missing_vars'])}",
            "status_code": None,
            "message_sid": None
        }
    
    # Validate phone number
    is_valid_phone, phone_result = validate_phone_number(to_number)
    if not is_valid_phone:
        return {
            "success": False,
            "error": phone_result,
            "status_code": None,
            "message_sid": None
        }
    
    formatted_phone = phone_result
    
    # Validate message
    if not message or not message.strip():
        return {
            "success": False,
            "error": "Message content is required",
            "status_code": None,
            "message_sid": None
        }
    
    if len(message) > 1600:  # Twilio's SMS limit
        return {
            "success": False,
            "error": "Message too long (max 1600 characters)",
            "status_code": None,
            "message_sid": None
        }
    
    # Test mode - validate but don't send
    if test_mode:
        return {
            "success": True,
            "message": "Test mode - message validated successfully",
            "formatted_phone": formatted_phone,
            "message_length": len(message),
            "status_code": 200,
            "message_sid": "test_message_id"
        }
    
    # Send SMS with retry logic for error 21704
    return _send_sms_with_retry(formatted_phone, message, max_retries)


def _send_sms_with_retry(formatted_phone: str, message: str, max_retries: int) -> Dict:
    """
    Send SMS with exponential backoff retry for error 21704
    Enhanced to try MMS first with publicly accessible media URL, then fallback to SMS
    
    Args:
        formatted_phone (str): Validated phone number
        message (str): Message content
        max_retries (int): Maximum retry attempts
        
    Returns:
        Dict: Result with status, message_sid, and any errors
    """
    
    # Prepare API request
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messages.json"
    auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
    
    # Try MMS first with publicly accessible media URL
    mms_data = {
        "To": formatted_phone,
        "From": TwilioConfig.SENDER_PHONE,  # Use direct phone number instead of invalid messaging service
        "Body": message,
        # Use publicly accessible Rally logo for MMS
        "MediaUrl": "https://www.lovetorally.com/static/images/rallylogo.png"
    }
    
    # SMS fallback data (no media)
    sms_data = {
        "To": formatted_phone,
        "From": TwilioConfig.SENDER_PHONE,  # Use direct phone number instead of invalid messaging service
        "Body": message
    }
    
    last_error = None
    last_response_data = None
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            if attempt > 0:
                # Calculate exponential backoff delay
                delay = min(2 ** attempt, 60)  # Max 60 seconds
                logger.info(f"Retry {attempt}/{max_retries} in {delay}s")
                time.sleep(delay)
            
            # Try MMS first, then fallback to SMS
            for method, data in [("MMS", mms_data), ("SMS", sms_data)]:
                try:
                    logger.info(f"Sending {method} to {formatted_phone} via Twilio (attempt {attempt + 1}/{max_retries + 1})")
                    
                    response = requests.post(
                        url,
                        data=data,
                        auth=auth,
                        timeout=30
                    )
                    
                    response_data = response.json()
                    last_response_data = response_data
                    
                    if response.status_code == 201:  # Twilio success status
                        success_msg = f"{method} sent successfully"
                        if attempt > 0:
                            success_msg += f" (succeeded on retry {attempt})"
                        
                        logger.info(f"{success_msg}. Message SID: {response_data.get('sid')}")
                        return {
                            "success": True,
                            "message": success_msg,
                            "status_code": response.status_code,
                            "message_sid": response_data.get("sid"),
                            "formatted_phone": formatted_phone,
                            "message_length": len(message),
                            "twilio_status": response_data.get("status"),
                            "price": response_data.get("price"),
                            "date_sent": response_data.get("date_sent"),
                            "retry_attempt": attempt,
                            "sending_method": method.lower()
                        }
                    else:
                        error_message = response_data.get("message", "Unknown Twilio error")
                        error_code = response_data.get("code")
                        
                        # If MMS failed with media URL error, continue to SMS fallback
                        if method == "MMS" and error_code == 21620:
                            logger.warning(f"MMS failed with error 21620 (invalid media URL), trying SMS fallback...")
                            continue
                        
                        # Check if this is error 21704 (provider disruption) - retry if we have attempts left
                        if error_code == 21704 and attempt < max_retries:
                            logger.warning(f"Error 21704 (provider disruption) on attempt {attempt + 1}, will retry...")
                            last_error = f"Twilio error 21704: {error_message}"
                            break  # Break from method loop, continue to next attempt
                        
                        # For other errors, try next method or fail
                        logger.error(f"Twilio API error {response.status_code}: {error_message} (Code: {error_code})")
                        
                        # If this was SMS (last fallback), return failure
                        if method == "SMS":
                            return {
                                "success": False,
                                "error": f"Twilio error: {error_message}",
                                "error_code": error_code,
                                "status_code": response.status_code,
                                "message_sid": None,
                                "raw_response": response_data,
                                "final_attempt": attempt + 1,
                                "max_retries": max_retries,
                                "sending_method": method.lower()
                            }
                        
                        # If MMS failed with non-media error, continue to SMS
                        continue
                        
                except requests.exceptions.Timeout:
                    logger.error(f"{method} request timed out (attempt {attempt + 1})")
                    if method == "SMS":  # Last fallback
                        last_error = "Request timed out"
                        break
                    continue
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error sending {method} (attempt {attempt + 1}): {str(e)}")
                    if method == "SMS":  # Last fallback
                        last_error = f"Network error: {str(e)}"
                        break
                    continue
                    
            # If we get here, all methods failed for this attempt
            if attempt < max_retries and last_error:
                logger.info("Retrying after failures...")
                continue
            
        except Exception as e:
            error_msg = f"Unexpected error (attempt {attempt + 1}): {str(e)}"
            logger.error(error_msg)
            last_error = f"Unexpected error: {str(e)}"
            # Don't retry unexpected errors
            break
    
    # All retries exhausted
    final_error = last_error or "All retry attempts failed"
    logger.error(f"Message sending failed after {max_retries + 1} attempts: {final_error}")
    
    return {
        "success": False,
        "error": f"Failed after {max_retries + 1} attempts: {final_error}",
        "status_code": None,
        "message_sid": None,
        "final_attempt": attempt + 1,
        "max_retries": max_retries,
        "last_response": last_response_data,
        "sending_method": "failed"
    }


def get_predefined_messages() -> Dict[str, str]:
    """
    Get predefined test messages for the admin interface
    
    Returns:
        Dict[str, str]: Dictionary of message templates
    """
    return {
        "poll_vote": "Can you make it to Sunday's practice? Tap to vote: https://rally.link/poll123",
        "sub_needed": "We need a sub for Thursday night's match. Are you available?",
        "match_confirmation": "You still good for the 6:30pm match at Tennaqua? Reply YES or NO.",
        "practice_reminder": "Don't forget - practice tonight at 7:00pm at the club. See you there!",
        "league_update": "League standings have been updated! Check your team's position: https://rally.link/standings",
        "weather_alert": "Weather alert: Tonight's outdoor matches may be delayed due to rain. Stay tuned for updates.",
        "tournament_announcement": "Tournament registration is now open! Sign up before spots fill: https://rally.link/tournament"
    }


def get_twilio_status() -> Dict:
    """
    Get current Twilio configuration status for admin display
    
    Returns:
        Dict: Configuration status and details
    """
    config = TwilioConfig.validate_config()
    
    status = {
        "configured": config["is_valid"],
        "account_sid": config["account_sid"][:8] + "..." if config["account_sid"] else None,
        "messaging_service_sid": config["messaging_service_sid"][:8] + "..." if config["messaging_service_sid"] else None,
        "sender_phone": config["sender_phone"],
        "missing_vars": config["missing_vars"]
    }
    
    if config["is_valid"]:
        status["status_message"] = "✅ Twilio is properly configured"
        status["status_color"] = "green"
    else:
        status["status_message"] = f"❌ Missing: {', '.join(config['missing_vars'])}"
        status["status_color"] = "red"
    
    return status


# Legacy function name for backwards compatibility
def send_text_notification(to_number: str, message: str) -> Dict:
    """Legacy function name - calls send_sms_notification"""
    return send_sms_notification(to_number, message) 