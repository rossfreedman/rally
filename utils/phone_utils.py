#!/usr/bin/env python3
"""
Phone Number Utilities
=====================

Centralized phone number validation, normalization, and formatting utilities for Rally.
Ensures consistent phone number handling across registration, settings, and SMS functionality.

Standard Format: +1XXXXXXXXXX (E.164 format for US numbers)
"""

import re
from typing import Tuple, Optional, Dict, Any


def normalize_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Normalize phone number to standard E.164 format (+1XXXXXXXXXX)
    
    Args:
        phone (str): Raw phone number input (any format)
        
    Returns:
        Tuple[bool, str]: (is_valid, normalized_phone_or_error_message)
        
    Examples:
        normalize_phone_number("(773) 213-8911") -> (True, "+17732138911")
        normalize_phone_number("7732138911") -> (True, "+17732138911")
        normalize_phone_number("+1 773 213 8911") -> (True, "+17732138911")
        normalize_phone_number("123") -> (False, "Invalid phone number format")
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Handle different input formats
    if len(digits_only) == 10:
        # 10 digits: assume US number, add country code
        normalized = f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # 11 digits starting with 1: add + prefix
        normalized = f"+{digits_only}"
    elif len(digits_only) == 12 and digits_only.startswith('1'):
        # 12 digits starting with 1: might be +1XXXXXXXXXX without +
        if digits_only[1:].isdigit():
            normalized = f"+{digits_only}"
        else:
            return False, "Invalid phone number format"
    else:
        return False, f"Invalid phone number format. Expected 10 or 11 digits, got {len(digits_only)}"
    
    # Validate the normalized number
    return validate_normalized_phone(normalized)


def validate_normalized_phone(phone: str) -> Tuple[bool, str]:
    """
    Validate a phone number that should already be in E.164 format
    
    Args:
        phone (str): Phone number in E.164 format (+1XXXXXXXXXX)
        
    Returns:
        Tuple[bool, str]: (is_valid, phone_or_error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Must start with +1
    if not phone.startswith('+1'):
        return False, "Only US phone numbers are supported (+1 format)"
    
    # Must be exactly 12 characters (+1 + 10 digits)
    if len(phone) != 12:
        return False, f"Invalid phone number length. Expected 12 characters, got {len(phone)}"
    
    # Must be all digits after +1
    digits = phone[2:]
    if not digits.isdigit():
        return False, "Phone number must contain only digits after country code"
    
    # Validate area code (first 3 digits)
    area_code = digits[:3]
    if area_code.startswith('0') or area_code.startswith('1'):
        return False, "Invalid area code. Area codes cannot start with 0 or 1"
    
    # Validate exchange code (digits 4-6)
    exchange = digits[3:6]
    if exchange.startswith('0') or exchange.startswith('1'):
        return False, "Invalid exchange code. Exchange codes cannot start with 0 or 1"
    
    return True, phone


def format_phone_for_display(phone: str) -> str:
    """
    Format a normalized phone number for display purposes
    
    Args:
        phone (str): Phone number in E.164 format (+1XXXXXXXXXX)
        
    Returns:
        str: Formatted phone number for display (e.g., "(773) 213-8911")
    """
    if not phone or not phone.startswith('+1') or len(phone) != 12:
        return phone  # Return as-is if not in expected format
    
    digits = phone[2:]  # Remove +1
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def format_phone_for_input(phone: str) -> str:
    """
    Format a normalized phone number for input field display
    
    Args:
        phone (str): Phone number in E.164 format (+1XXXXXXXXXX)
        
    Returns:
        str: Formatted phone number for input (e.g., "(773) 213-8911")
    """
    return format_phone_for_display(phone)


def extract_digits_only(phone: str) -> str:
    """
    Extract only digits from a phone number
    
    Args:
        phone (str): Phone number in any format
        
    Returns:
        str: Only the digits (e.g., "7732138911")
    """
    return re.sub(r'\D', '', phone)


def is_phone_number_valid(phone: str) -> bool:
    """
    Quick check if a phone number is valid (without returning error message)
    
    Args:
        phone (str): Phone number to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    is_valid, _ = normalize_phone_number(phone)
    return is_valid


def get_phone_variants_for_matching(phone: str) -> list:
    """
    Get all possible phone number variants for database matching
    
    Args:
        phone (str): Normalized phone number (+1XXXXXXXXXX)
        
    Returns:
        list: List of phone number variants for matching
    """
    if not phone or not phone.startswith('+1') or len(phone) != 12:
        return []
    
    digits = phone[2:]  # Remove +1
    
    variants = [
        phone,                    # +17732138911
        digits,                   # 7732138911
        f"1{digits}",            # 17732138911
        f"({digits[:3]}) {digits[3:6]}-{digits[6:]}",  # (773) 213-8911
        f"{digits[:3]}-{digits[3:6]}-{digits[6:]}",    # 773-213-8911
        f"{digits[:3]}.{digits[3:6]}.{digits[6:]}",    # 773.213.8911
        f"{digits[:3]} {digits[3:6]} {digits[6:]}",    # 773 213 8911
    ]
    
    return variants


def validate_and_normalize_phone_input(phone: str, field_name: str = "phone number") -> Dict[str, Any]:
    """
    Comprehensive phone number validation and normalization for form inputs
    
    Args:
        phone (str): Raw phone number input
        field_name (str): Name of the field for error messages
        
    Returns:
        Dict[str, Any]: {
            'success': bool,
            'normalized_phone': str or None,
            'display_phone': str or None,
            'error': str or None
        }
    """
    result = {
        'success': False,
        'normalized_phone': None,
        'display_phone': None,
        'error': None
    }
    
    if not phone or not phone.strip():
        result['error'] = f"{field_name.title()} is required"
        return result
    
    phone = phone.strip()
    
    # Normalize the phone number
    is_valid, normalized_or_error = normalize_phone_number(phone)
    
    if not is_valid:
        result['error'] = f"Invalid {field_name}: {normalized_or_error}"
        return result
    
    result['success'] = True
    result['normalized_phone'] = normalized_or_error
    result['display_phone'] = format_phone_for_display(normalized_or_error)
    
    return result


# Legacy function for backward compatibility
def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Legacy function for backward compatibility with notifications_service.py
    
    Args:
        phone (str): Phone number to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, formatted_phone_or_error_message)
    """
    return normalize_phone_number(phone)
