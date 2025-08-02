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
            "message": "🏓 Match Reminder: Don't forget about tonight's match! Please arrive 15 minutes early. Let me know if you can't make it."
        },
        "practice_reminder": {
            "title": "Practice Reminder", 
            "description": "Remind team about practice session",
            "message": "🏓 Practice Reminder: Practice tonight at 7:00pm. Please bring your paddle and water. See you there!"
        },
        "availability_update": {
            "title": "Update Availability",
            "description": "Ask team to update their availability",
            "message": "📅 Please update your availability for this week's matches. Go to Rally app and mark your availability. Thanks!"
        },
        "team_poll": {
            "title": "Send a Poll",
            "description": "Create a quick team poll",
            "message": "📊 Quick Poll: What time works best for practice this week? Reply with your preference: 6pm, 7pm, or 8pm."
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