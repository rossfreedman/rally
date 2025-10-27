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
# DISABLED: SendGrid email functionality - SMS only now
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail

from config import TwilioConfig, RALLY_TESTING_MODE, ADMIN_PHONE  # SendGridConfig removed - email disabled


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
    from utils.phone_utils import normalize_phone_number
    return normalize_phone_number(phone)


def send_sms_notification(to_number: str, message: str, test_mode: bool = False, max_retries: int = 3) -> Dict:
    """
    Send an SMS using Twilio's Messaging Service API with retry logic for error 21704
    
    TESTING MODE: When RALLY_TESTING_MODE=true, all SMS messages are routed to the admin phone
    to prevent accidental texts to real users during testing.
    
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
    
    # TESTING MODE: Route all messages to admin phone
    original_phone = formatted_phone
    if RALLY_TESTING_MODE:
        logger.info(f"🧪 TESTING MODE: Redirecting SMS from {original_phone} to admin {ADMIN_PHONE}")
        formatted_phone = ADMIN_PHONE
        # Prepend original recipient to message for context
        message = f"[TEST - would send to {original_phone}]\n\n{message}"
    
    # Validate message
    if not message or not message.strip():
        return {
            "success": False,
            "error": "Message content is required",
            "status_code": None,
            "message_sid": None
        }
    
    # Limit to 500 chars for reliable cross-carrier delivery (4-5 SMS segments)
    # Twilio supports up to 1600, but carriers often corrupt messages beyond 500 chars
    if len(message) > 500:
        return {
            "success": False,
            "error": "Message too long (max 500 characters for reliable delivery)",
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
    Send SMS with exponential backoff retry for error 21704, with MMS as fallback
    Tries SMS first (more reliable), then MMS if SMS fails
    
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
    
    # SMS data (no media) - primary method
    sms_data = {
        "To": formatted_phone,
        "From": TwilioConfig.SENDER_PHONE,  # Use direct phone number instead of invalid messaging service
        "Body": message
    }
    
    # MMS data (with media) - fallback method
    mms_data = {
        "To": formatted_phone,
        "From": TwilioConfig.SENDER_PHONE,  # Use direct phone number instead of invalid messaging service
        "Body": message,
        # Use publicly accessible Rally logo for MMS
        "MediaUrl": "https://www.lovetorally.com/static/rallylogo.png"
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
            
            # Try SMS first, then MMS as fallback
            for method, data in [("SMS", sms_data), ("MMS", mms_data)]:
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
                        if method == "MMS":
                            success_msg += " (SMS fallback)"
                        
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
                        
                        # Check if this is error 21704 (provider disruption) - retry if we have attempts left
                        if error_code == 21704 and attempt < max_retries:
                            logger.warning(f"Error 21704 (provider disruption) on attempt {attempt + 1}, will retry...")
                            last_error = f"Twilio error 21704: {error_message}"
                            break  # Break from method loop, continue to next attempt
                        
                        # For SMS errors, try MMS fallback
                        if method == "SMS":
                            logger.warning(f"SMS failed with error {error_code}: {error_message}, trying MMS fallback...")
                            continue
                        
                        # If MMS also failed, return failure
                        logger.error(f"Twilio API error {response.status_code}: {error_message} (Code: {error_code})")
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
                        
                except requests.exceptions.Timeout:
                    logger.error(f"{method} request timed out (attempt {attempt + 1})")
                    if method == "SMS":  # Try MMS fallback
                        continue
                    else:  # MMS also timed out
                        last_error = "Request timed out"
                        break
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error sending {method} (attempt {attempt + 1}): {str(e)}")
                    if method == "SMS":  # Try MMS fallback
                        continue
                    else:  # MMS also failed
                        last_error = f"Network error: {str(e)}"
                        break
                        
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


def send_mms_notification(to_number: str, message: str, test_mode: bool = False, max_retries: int = 3) -> Dict:
    """
    Send an MMS using Twilio's API with retry logic for error 21704
    
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
    
    if len(message) > 1600:  # Twilio's MMS limit
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
            "message": "Test mode - MMS validated successfully",
            "formatted_phone": formatted_phone,
            "message_length": len(message),
            "status_code": 200,
            "message_sid": "test_mms_id"
        }
    
    # Send MMS with retry logic for error 21704
    return _send_mms_with_retry(formatted_phone, message, max_retries)


def _send_mms_with_retry(formatted_phone: str, message: str, max_retries: int) -> Dict:
    """
    Send MMS with exponential backoff retry for error 21704
    
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
    
    # MMS data (with media)
    mms_data = {
        "To": formatted_phone,
        "From": TwilioConfig.SENDER_PHONE,
        "Body": message,
        # Use publicly accessible Rally logo for MMS
        "MediaUrl": "https://www.lovetorally.com/static/rallylogo.png"
    }
    
    last_error = None
    last_response_data = None
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            if attempt > 0:
                # Calculate exponential backoff delay
                delay = min(2 ** attempt, 60)  # Max 60 seconds
                logger.info(f"MMS retry {attempt}/{max_retries} in {delay}s")
                time.sleep(delay)
            
            logger.info(f"Sending MMS to {formatted_phone} via Twilio (attempt {attempt + 1}/{max_retries + 1})")
            
            response = requests.post(
                url,
                data=mms_data,
                auth=auth,
                timeout=30
            )
            
            response_data = response.json()
            last_response_data = response_data
            
            if response.status_code == 201:  # Twilio success status
                success_msg = "MMS sent successfully"
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
                    "sending_method": "mms"
                }
            else:
                error_message = response_data.get("message", "Unknown Twilio error")
                error_code = response_data.get("code")
                
                # Check if this is error 21704 (provider disruption) - retry if we have attempts left
                if error_code == 21704 and attempt < max_retries:
                    logger.warning(f"Error 21704 (provider disruption) on attempt {attempt + 1}, will retry...")
                    last_error = f"Twilio error 21704: {error_message}"
                    continue
                
                # If not 21704, don't retry
                logger.error(f"Twilio API error {response.status_code}: {error_message} (Code: {error_code})")
                return {
                    "success": False,
                    "error": f"Twilio error: {error_message}",
                    "error_code": error_code,
                    "status_code": response.status_code,
                    "message_sid": None,
                    "raw_response": response_data,
                    "final_attempt": attempt + 1,
                    "max_retries": max_retries,
                    "sending_method": "mms"
                }
                    
        except requests.exceptions.Timeout:
            logger.error(f"MMS request timed out (attempt {attempt + 1})")
            last_error = "Request timed out"
            if attempt < max_retries:
                continue
            else:
                break
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending MMS (attempt {attempt + 1}): {str(e)}")
            last_error = f"Network error: {str(e)}"
            if attempt < max_retries:
                continue
            else:
                break
                
        except Exception as e:
            error_msg = f"Unexpected error (attempt {attempt + 1}): {str(e)}"
            logger.error(error_msg)
            last_error = f"Unexpected error: {str(e)}"
            # Don't retry unexpected errors
            break
    
    # All retries exhausted
    final_error = last_error or "All retry attempts failed"
    logger.error(f"MMS sending failed after {max_retries + 1} attempts: {final_error}")
    
    return {
        "success": False,
        "error": f"Failed after {max_retries + 1} attempts: {final_error}",
        "status_code": None,
        "message_sid": None,
        "final_attempt": attempt + 1,
        "max_retries": max_retries,
        "last_response": last_response_data,
        "sending_method": "mms"
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


def get_team_notification_templates() -> Dict[str, Dict[str, str]]:
    """
    Get predefined team notification templates for captains
    
    Returns:
        Dict[str, Dict[str, str]]: Dictionary of template objects with title, description, and message
    """
    return {
        "match_reminder": {
            "title": "Match Reminder",
            "description": "Remind team about upcoming match",
            "message": "Match Reminder: Just a quick reminder that we have a match this week. Let's go!"
        },
        "practice_reminder": {
            "title": "Practice Reminder", 
            "description": "Remind team about practice session",
            "message": "🏓 Practice Reminder: Practice tonight at 7:00pm. Please bring your paddle and water. See you there!"
        },
        "availability_update": {
            "title": "Update Availability",
            "description": "Ask team to update their availability",
            "message": "Hi Team! Please update your availability in Rally for this week's practice and match if you haven't done so already. Just go to: https://www.lovetorally.com/mobile/availability-calendar"
        },
        "team_poll": {
            "title": "Send a Poll",
            "description": "Go to polls page to create a team poll",
            "message": ""
        },
        "court_assignments": {
            "title": "Court Assignments",
            "description": "Share court assignments with team",
            "message": "🎾 Court Assignments: Check the Rally app for your court assignments for tonight's match. Good luck everyone!"
        }
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


# Simple wrapper for master import script
def send_sms(to_number: str, message: str) -> Dict:
    """Simple wrapper for send_sms_notification - used by master import script"""
    return send_sms_notification(to_number, message)


def send_pickup_game_join_notifications(game_id: int, joining_user_id: int, joining_user_name: str) -> Dict:
    """
    Send SMS notifications when a user joins a pickup game
    
    Args:
        game_id (int): ID of the pickup game
        joining_user_id (int): ID of the user who joined
        joining_user_name (str): Name of the user who joined
        
    Returns:
        Dict: Results of notification sending
    """
    try:
        from database_utils import execute_query_one, execute_query
        
        # Get pickup game details
        game_query = """
            SELECT pg.*, c.name as club_name
            FROM pickup_games pg
            LEFT JOIN clubs c ON pg.club_id = c.id
            WHERE pg.id = %s
        """
        game = execute_query_one(game_query, [game_id])
        
        if not game:
            return {
                "success": False,
                "error": f"Pickup game {game_id} not found"
            }
        
        # Get all participants (excluding the joining user)
        participants_query = """
            SELECT u.id, u.first_name, u.last_name, u.phone_number, u.email
            FROM pickup_game_participants pgp
            JOIN users u ON pgp.user_id = u.id
            WHERE pgp.pickup_game_id = %s AND u.id != %s
        """
        participants = execute_query(participants_query, [game_id, joining_user_id])
        
        # Format game details
        game_date = game["game_date"].strftime("%m/%d/%Y") if game["game_date"] else "TBD"
        game_time = game["game_time"].strftime("%I:%M %p") if game["game_time"] else "TBD"
        club_name = game["club_name"] or "TBD"
        
        # Create message for other participants
        game_url = f"https://www.lovetorally.com/mobile/pickup-games"
        message = f"🎾 Rally Pickup Game Update:\n\n{joining_user_name} just joined this pickup game:\n\n\"{game['description']}\" on {game_date} at {game_time}.\n\nCurrent players: {game['players_committed']}/{game['players_requested']}\n\nClick here to view the game: {game_url}"
        
        # Send notifications to all other participants
        results = {
            "success": True,
            "message": f"Sent notifications to {len(participants)} participants",
            "participants_notified": 0,
            "participants_failed": 0,
            "details": []
        }
        
        for participant in participants:
            if not participant["phone_number"]:
                results["details"].append({
                    "user": f"{participant['first_name']} {participant['last_name']}",
                    "status": "skipped",
                    "reason": "No phone number"
                })
                continue
            
            # Send SMS notification
            sms_result = send_sms_notification(
                to_number=participant["phone_number"],
                message=message,
                test_mode=False
            )
            
            if sms_result["success"]:
                results["participants_notified"] += 1
                results["details"].append({
                    "user": f"{participant['first_name']} {participant['last_name']}",
                    "phone": participant["phone_number"],
                    "status": "sent",
                    "message_sid": sms_result.get("message_sid")
                })
            else:
                results["participants_failed"] += 1
                results["details"].append({
                    "user": f"{participant['first_name']} {participant['last_name']}",
                    "phone": participant["phone_number"],
                    "status": "failed",
                    "error": sms_result.get("error")
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Error sending pickup game join notifications: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to send notifications: {str(e)}"
        }


def send_pickup_game_leave_notifications(game_id: int, leaving_user_id: int, leaving_user_name: str) -> Dict:
    """
    Send SMS notifications when a user leaves a pickup game
    
    Args:
        game_id (int): ID of the pickup game
        leaving_user_id (int): ID of the user who left
        leaving_user_name (str): Name of the user who left
        
    Returns:
        Dict: Results of notification sending
    """
    try:
        from database_utils import execute_query_one, execute_query
        
        # Get pickup game details
        game_query = """
            SELECT pg.*, c.name as club_name
            FROM pickup_games pg
            LEFT JOIN clubs c ON pg.club_id = c.id
            WHERE pg.id = %s
        """
        game = execute_query_one(game_query, [game_id])
        
        if not game:
            return {
                "success": False,
                "error": f"Pickup game {game_id} not found"
            }
        
        # Get all remaining participants
        participants_query = """
            SELECT u.id, u.first_name, u.last_name, u.phone_number, u.email
            FROM pickup_game_participants pgp
            JOIN users u ON pgp.user_id = u.id
            WHERE pgp.pickup_game_id = %s
        """
        participants = execute_query(participants_query, [game_id])
        
        # Format game details
        game_date = game["game_date"].strftime("%m/%d/%Y") if game["game_date"] else "TBD"
        game_time = game["game_time"].strftime("%I:%M %p") if game["game_time"] else "TBD"
        club_name = game["club_name"] or "TBD"
        
        # Create message for remaining participants
        game_url = f"https://www.lovetorally.com/mobile/pickup-games"
        message = f"🎾 Rally Pickup Game Update:\n\n{leaving_user_name} just left this pickup game:\n\n\"{game['description']}\" on {game_date} at {game_time}.\n\nCurrent players: {game['players_committed']}/{game['players_requested']}\n\nClick here to view the game: {game_url}"
        
        # Send notifications to all remaining participants
        results = {
            "success": True,
            "message": f"Sent notifications to {len(participants)} participants",
            "participants_notified": 0,
            "participants_failed": 0,
            "details": []
        }
        
        for participant in participants:
            if not participant["phone_number"]:
                results["details"].append({
                    "user": f"{participant['first_name']} {participant['last_name']}",
                    "status": "skipped",
                    "reason": "No phone number"
                })
                continue
            
            # Send SMS notification
            sms_result = send_sms_notification(
                to_number=participant["phone_number"],
                message=message,
                test_mode=False
            )
            
            if sms_result["success"]:
                results["participants_notified"] += 1
                results["details"].append({
                    "user": f"{participant['first_name']} {participant['last_name']}",
                    "phone": participant["phone_number"],
                    "status": "sent",
                    "message_sid": sms_result.get("message_sid")
                })
            else:
                results["participants_failed"] += 1
                results["details"].append({
                    "user": f"{participant['first_name']} {participant['last_name']}",
                    "phone": participant["phone_number"],
                    "status": "failed",
                    "error": sms_result.get("error")
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Error sending pickup game leave notifications: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to send notifications: {str(e)}"
        }


def send_pickup_game_join_confirmation(user_id: int, game_id: int) -> Dict:
    """
    Send confirmation SMS to the user who just joined a pickup game
    
    Args:
        user_id (int): ID of the user who joined
        game_id (int): ID of the pickup game
        
    Returns:
        Dict: Result of confirmation SMS
    """
    try:
        from database_utils import execute_query_one
        
        # Get user details
        user_query = """
            SELECT u.first_name, u.last_name, u.phone_number, u.email
            FROM users u
            WHERE u.id = %s
        """
        user = execute_query_one(user_query, [user_id])
        
        if not user or not user["phone_number"]:
            return {
                "success": False,
                "error": "User not found or no phone number"
            }
        
        # Get pickup game details
        game_query = """
            SELECT pg.*, c.name as club_name
            FROM pickup_games pg
            LEFT JOIN clubs c ON pg.club_id = c.id
            WHERE pg.id = %s
        """
        game = execute_query_one(game_query, [game_id])
        
        if not game:
            return {
                "success": False,
                "error": f"Pickup game {game_id} not found"
            }
        
        # Format game details
        game_date = game["game_date"].strftime("%m/%d/%Y") if game["game_date"] else "TBD"
        game_time = game["game_time"].strftime("%I:%M %p") if game["game_time"] else "TBD"
        club_name = game["club_name"] or "TBD"
        
        # Create confirmation message
        game_url = f"https://www.lovetorally.com/mobile/pickup-games"
        message = f"🎾 Rally Pickup Game Confirmation:\n\nYou've successfully joined this pickup game:\n\n\"{game['description']}\" on {game_date} at {game_time}.\n\nCurrent players: {game['players_committed']}/{game['players_requested']}\n\nClick here to view the game: {game_url}\n\nYou'll be notified when other players join or leave."
        
        # Send confirmation SMS
        sms_result = send_sms_notification(
            to_number=user["phone_number"],
            message=message,
            test_mode=False
        )
        
        if sms_result["success"]:
            return {
                "success": True,
                "message": "Confirmation SMS sent successfully",
                "message_sid": sms_result.get("message_sid")
            }
        else:
            return {
                "success": False,
                "error": f"Failed to send confirmation SMS: {sms_result.get('error')}"
            }
        
    except Exception as e:
        logger.error(f"Error sending pickup game join confirmation: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to send confirmation: {str(e)}"
        }


def send_pickup_game_leave_confirmation(user_id: int, game_id: int) -> Dict:
    """
    Send confirmation SMS to the user who just left a pickup game
    
    Args:
        user_id (int): ID of the user who left
        game_id (int): ID of the pickup game
        
    Returns:
        Dict: Result of confirmation SMS
    """
    try:
        from database_utils import execute_query_one
        
        # Get user details
        user_query = """
            SELECT u.first_name, u.last_name, u.phone_number, u.email
            FROM users u
            WHERE u.id = %s
        """
        user = execute_query_one(user_query, [user_id])
        
        if not user or not user["phone_number"]:
            return {
                "success": False,
                "error": "User not found or no phone number"
            }
        
        # Get pickup game details
        game_query = """
            SELECT pg.*, c.name as club_name
            FROM pickup_games pg
            LEFT JOIN clubs c ON pg.club_id = c.id
            WHERE pg.id = %s
        """
        game = execute_query_one(game_query, [game_id])
        
        if not game:
            return {
                "success": False,
                "error": f"Pickup game {game_id} not found"
            }
        
        # Format game details
        game_date = game["game_date"].strftime("%m/%d/%Y") if game["game_date"] else "TBD"
        game_time = game["game_time"].strftime("%I:%M %p") if game["game_time"] else "TBD"
        club_name = game["club_name"] or "TBD"
        
        # Create confirmation message
        game_url = f"https://www.lovetorally.com/mobile/pickup-games"
        message = f"🎾 Rally Pickup Game Confirmation:\n\nYou've successfully left this pickup game:\n\n\"{game['description']}\" on {game_date} at {game_time}.\n\nCurrent players: {game['players_committed']}/{game['players_requested']}\n\nClick here to view the game: {game_url}"
        
        # Send confirmation SMS
        sms_result = send_sms_notification(
            to_number=user["phone_number"],
            message=message,
            test_mode=False
        )
        
        if sms_result["success"]:
            return {
                "success": True,
                "message": "Confirmation SMS sent successfully",
                "message_sid": sms_result.get("message_sid")
            }
        else:
            return {
                "success": False,
                "error": f"Failed to send confirmation SMS: {sms_result.get('error')}"
            }
        
    except Exception as e:
        logger.error(f"Error sending pickup game leave confirmation: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to send confirmation: {str(e)}"
        }


def validate_email_address(email: str) -> Tuple[bool, str]:
    """
    Validate email address format
    
    Args:
        email (str): Email address to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, formatted_email_or_error_message)
    """
    if not email:
        return False, "Email address is required"
    
    # Basic email validation regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(email_pattern, email.strip()):
        return True, email.strip().lower()
    else:
        return False, "Invalid email address format"


def send_email_notification(to_email: str, subject: str, content: str, html_content: str = None, test_mode: bool = False) -> Dict:
    """
    DISABLED: Email notifications have been turned off - Rally uses SMS only now
    
    This function is kept for backwards compatibility but always returns disabled status.
    
    Args:
        to_email (str): Recipient email address (unused)
        subject (str): Email subject line (unused)
        content (str): Plain text email content (unused)
        html_content (str): Optional HTML email content (unused)
        test_mode (bool): If True, validates but doesn't actually send (unused)
        
    Returns:
        Dict: Result indicating email functionality is disabled
    """
    logger.info(f"Email notification skipped (emails disabled) - would have sent to: {to_email}")
    return {
        "success": False,
        "error": "Email notifications disabled - Rally uses SMS only",
        "status_code": None,
        "message_id": None,
        "disabled": True
    }
    
    # ORIGINAL CODE COMMENTED OUT - SendGrid functionality disabled
    # # Validate configuration
    # config_status = SendGridConfig.validate_config()
    # if not config_status["is_valid"]:
    #     return {
    #         "success": False,
    #         "error": f"SendGrid not configured. Missing: {', '.join(config_status['missing_vars'])}",
    #         "status_code": None,
    #         "message_id": None
    #     }
    # 
    # # Validate email address
    # is_valid_email, email_result = validate_email_address(to_email)
    # if not is_valid_email:
    #     return {
    #         "success": False,
    #         "error": email_result,
    #         "status_code": None,
    #         "message_id": None
    #     }
    # 
    # formatted_email = email_result
    # 
    # # Validate content
    # if not subject or not subject.strip():
    #     return {
    #         "success": False,
    #         "error": "Email subject is required",
    #         "status_code": None,
    #         "message_id": None
    #     }
    # 
    # if not content or not content.strip():
    #     return {
    #         "success": False,
    #         "error": "Email content is required",
    #         "status_code": None,
    #         "message_id": None
    #     }
    # 
    # # Test mode - validate but don't send
    # if test_mode:
    #     return {
    #         "success": True,
    #         "message": "Test mode - email validated successfully",
    #         "formatted_email": formatted_email,
    #         "subject": subject,
    #         "content_length": len(content),
    #         "status_code": 200,
    #         "message_id": "test_email_id"
    #     }
    # 
    # # Send email with SendGrid
    # return _send_email_with_sendgrid(formatted_email, subject, content, html_content)


def _send_email_with_sendgrid(to_email: str, subject: str, content: str, html_content: str = None) -> Dict:
    """
    DISABLED: SendGrid email functionality has been turned off
    
    This function is kept for backwards compatibility but always returns disabled status.
    
    Args:
        to_email (str): Validated email address (unused)
        subject (str): Email subject (unused)
        content (str): Plain text content (unused)
        html_content (str): Optional HTML content (unused)
        
    Returns:
        Dict: Result indicating email functionality is disabled
    """
    logger.info(f"SendGrid email skipped (emails disabled) - would have sent to: {to_email}")
    return {
        "success": False,
        "error": "Email notifications disabled - Rally uses SMS only",
        "status_code": None,
        "message_id": None,
        "disabled": True
    }
    
    # ORIGINAL CODE COMMENTED OUT - SendGrid functionality disabled
    # try:
    #     # Create the email message
    #     message = Mail(
    #         from_email=(SendGridConfig.FROM_EMAIL, SendGridConfig.FROM_NAME),
    #         to_emails=to_email,
    #         subject=subject,
    #         plain_text_content=content,
    #         html_content=html_content or f"<p>{content.replace(chr(10), '<br>')}</p>"
    #     )
    #     
    #     # Initialize SendGrid client
    #     sg = SendGridAPIClient(api_key=SendGridConfig.API_KEY)
    #     
    #     # Set EU data residency if enabled
    #     if SendGridConfig.EU_DATA_RESIDENCY:
    #         sg.set_sendgrid_data_residency("eu")
    #         logger.info("EU data residency enabled for SendGrid")
    #     
    #     # Send email
    #     response = sg.send(message)
    #     
    #     # Check response status
    #     if response.status_code in [200, 201, 202]:
    #         logger.info(f"Email sent successfully to {to_email}")
    #         return {
    #             "success": True,
    #             "status_code": response.status_code,
    #             "message_id": response.headers.get('X-Message-Id', 'unknown'),
    #             "message": "Email sent successfully"
    #         }
    #     else:
    #         logger.error(f"SendGrid returned status {response.status_code}: {response.body}")
    #         return {
    #             "success": False,
    #             "error": f"SendGrid error: Status {response.status_code}",
    #             "status_code": response.status_code,
    #             "message_id": None
    #         }
    #         
    # except Exception as e:
    #     logger.error(f"SendGrid email sending failed: {str(e)}")
    #     return {
    #         "success": False,
    #         "error": f"Email sending failed: {str(e)}",
    #         "status_code": None,
    #         "message_id": None
    #     }


def send_admin_activity_notification(user_email: str, activity_type: str, page: str = None, action: str = None, details: str = None, is_impersonating: bool = False, first_name: str = None, last_name: str = None) -> Dict:
    """
    DISABLED: Email notifications have been turned off - Rally uses SMS only now
    
    This function is kept for backwards compatibility but always returns disabled status.
    
    Args:
        user_email (str): Email of user performing activity (unused)
        activity_type (str): Type of activity (unused)
        page (str): Page where activity occurred (unused)
        action (str): Specific action taken (unused)
        details (str): Additional details about the activity (unused)
        is_impersonating (bool): Whether activity was performed while impersonating (unused)
        first_name (str): User's first name (unused)
        last_name (str): User's last name (unused)
        
    Returns:
        Dict: Result indicating email functionality is disabled
    """
    logger.info(f"Admin activity email skipped (emails disabled) - activity: {activity_type} for {user_email}")
    return {
        "success": False,
        "error": "Email notifications disabled - Rally uses SMS only",
        "status_code": None,
        "message_id": None,
        "disabled": True
    }
    
    # ORIGINAL CODE COMMENTED OUT - Email functionality disabled
    # """
    # Send email notification to admin about user activity
    # 
    # Args:
    #     user_email (str): Email of user performing activity
    #     activity_type (str): Type of activity
    #     page (str): Page where activity occurred
    #     action (str): Specific action taken
    #     details (str): Additional details about the activity
    #     is_impersonating (bool): Whether activity was performed while impersonating
    #     first_name (str): User's first name
    #     last_name (str): User's last name
    #     
    # Returns:
    #     Dict: Result of email sending
    # """
    
    # ORIGINAL CODE COMMENTED OUT - Email functionality disabled
    # # Helper function to convert technical page names to human-readable format
    # def humanize_page_name(page_name):
    #     if not page_name:
    #         return "Unknown Page"
    #     
    #     # Remove common prefixes
    #     page_name = page_name.replace("mobile_", "").replace("admin_", "").replace("api_", "")
    #     
    #     # Handle specific cases
    #     page_mappings = {
    #         "my_series": "My Series",
    #         "analyze_me": "Analyze Me", 
    #         "player_detail": "Player Detail",
    #         "home_submenu": "Home Page",
    #         "home_alt1": "Home Page",
    #         "home_classic": "Home Page",
    #         "my_team": "My Team",
    #         "my_club": "My Club",
    #         "user_activity": "User Activity",
    #         "player_search": "Player Search",
    #         "player_stats": "Player Stats",
    #         "schedule_lesson": "Schedule Lesson",
    #         "email_team": "Email Team",
    #         "practice_times": "Practice Times",
    #         "availability": "Availability",
    #         "team_schedule": "Team Schedule",
    #         "find_people_to_play": "Find People to Play",
    #         "pickup_games": "Pickup Games",
    #         "private_groups": "Private Groups",
    #         "create_pickup_game": "Create Pickup Game",
    #         "reserve_court": "Reserve Court",
    #         "share_rally": "Share Rally",
    #         "create_team": "Create Team",
    #         "matchup_simulator": "Matchup Simulator",
    #         "polls": "Polls"
    #     }
    #     
    #     # Check for exact matches first
    #     if page_name in page_mappings:
    #         return page_mappings[page_name]
    #     
    #     # Generic conversion: replace underscores with spaces and title case
    #     return page_name.replace("_", " ").title()
    # 
    # # Create email subject using requested format 
    # user_name = f"{first_name} {last_name}" if first_name and last_name else user_email
    # 
    # # Special formatting for login and registration activities
    # if activity_type == "login":
    #     subject = f"{user_name} - Login: Successful"
    #     content_parts = [
    #         f"Rally Activity:",
    #         f"{user_name} logged in successfully",
    #         f"Activity: {activity_type}",
    #     ]
    # elif activity_type == "login_failed":
    #     subject = f"{user_name} - Login: Unsuccessful"
    #     content_parts = [
    #         f"Rally Activity:",
    #         f"{user_name} login failed",
    #         f"Activity: {activity_type}",
    #     ]
    # elif activity_type in ["registration_successful", "registration_failed"]:
    #     status = "Successful" if "successful" in activity_type else "Unsuccessful"
    #     subject = f"{user_name} - Registration: {status}"
    #     content_parts = [
    #         f"Rally Activity:",
    #         f"{user_name} registration {status.lower()}",
    #         f"Activity: {activity_type}",
    #     ]
    # else:
    #     # Regular page visit formatting
    #     page_display = humanize_page_name(page)
    #     subject = f"{user_name} - {page_display}"
    #     content_parts = [
    #         f"Rally Activity:",
    #         f"{user_name} visited {page_display}",
    #         f"Activity: {activity_type}",
    #     ]
    # 
    # if is_impersonating:
    #     subject = f"Admin Impersonation: {subject}"
    # 
    # # Keep it simple - only add impersonation note if needed
    # if is_impersonating:
    #     content_parts.append("⚠️ Note: This activity was performed while impersonating another user")
    # 
    # content = "\n".join(content_parts)
    # 
    # # Create HTML version
    # html_content = f"""
    # <html>
    # <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    #     <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
    #         <h2 style="color: #2c3e50; margin-bottom: 20px;">
    #             {'👥 Rally Admin Impersonation Activity' if is_impersonating else '🔔 Rally Activity Alert'}
    #         </h2>
    #         
    #         <div style="background-color: white; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db;">
    #             <table style="width: 100%; border-collapse: collapse;">
    #                 <tr><td style="font-weight: bold; padding: 5px 0;">User:</td><td style="padding: 5px 0;">{user_name} ({user_email})</td></tr>
    #                 <tr><td style="font-weight: bold; padding: 5px 0;">Activity:</td><td style="padding: 5px 0;">{activity_type}</td></tr>
    #                 {f'<tr><td style="font-weight: bold; padding: 5px 0;">Page:</td><td style="padding: 5px 0;">{page}</td></tr>' if page else ''}
    #                 {f'<tr><td style="font-weight: bold; padding: 5px 0;">Action:</td><td style="padding: 5px 0;">{action}</td></tr>' if action else ''}
    #                 {f'<tr><td style="font-weight: bold; padding: 5px 0;">Details:</td><td style="padding: 5px 0;">{details}</td></tr>' if details else ''}
    #                 <tr><td style="font-weight: bold; padding: 5px 0;">Timestamp:</td><td style="padding: 5px 0;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
    #             </table>
    #             
    #             {f'<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin-top: 15px;"><strong>⚠️ Note:</strong> This activity was performed while impersonating another user</div>' if is_impersonating else ''}
    #         </div>
    #         
    #         <div style="margin-top: 20px; text-align: center;">
    #             <a href="https://www.lovetorally.com/admin" style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
    #                 Visit Rally Admin Panel
    #             </a>
    #         </div>
    #     </div>
    # </body>
    # </html>
    # """
    # 
    # # Send email to admin
    # return send_email_notification(
    #     to_email=SendGridConfig.ADMIN_EMAIL,
    #     subject=subject,
    #     content=content,
    #     html_content=html_content
    # )


def get_sendgrid_status() -> Dict:
    """
    DISABLED: Get SendGrid configuration status
    
    This function is kept for backwards compatibility but always returns disabled status.
    """
    return {
        "configured": False,
        "api_key": None,
        "from_email": None,
        "from_name": None,
        "admin_email": None,
        "eu_data_residency": False,
        "missing_vars": [],
        "status_message": "📧 Email notifications disabled - Rally uses SMS only",
        "status_color": "gray",
        "disabled": True
    }
    
    # ORIGINAL CODE COMMENTED OUT - Email functionality disabled
    # """Get SendGrid configuration status"""
    # config = SendGridConfig.validate_config()
    # 
    # status = {
    #     "configured": config["is_valid"],
    #     "api_key": config["api_key"],
    #     "from_email": config["from_email"],
    #     "from_name": config["from_name"],
    #     "admin_email": config["admin_email"],
    #     "eu_data_residency": config["eu_data_residency"],
    #     "missing_vars": config["missing_vars"]
    # }
    # 
    # if config["is_valid"]:
    #     status["status_message"] = "✅ SendGrid is properly configured"
    #     status["status_color"] = "green"
    # else:
    #     status["status_message"] = f"❌ Missing: {', '.join(config['missing_vars'])}"
    #     status["status_color"] = "red"
    # 
    # return status 