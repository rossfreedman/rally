#!/usr/bin/env python3
"""
Date verification utilities for ensuring correct dates in database operations
Includes Railway PostgreSQL timezone correction logic
"""

from datetime import datetime, date, timedelta
import logging
from .date_utils import date_to_db_timestamp, normalize_date_string

# Set up logging for date operations
logger = logging.getLogger(__name__)

def verify_and_fix_date_for_storage(input_date, intended_display_date=None):
    """
    Verify and potentially fix a date before storing in database.
    
    This function addresses the Railway PostgreSQL timezone issue by ensuring
    the stored date matches the user's intended date.
    
    Args:
        input_date: The date to be stored (string, date, or datetime)
        intended_display_date: What the user sees on screen (for verification)
    
    Returns:
        tuple: (corrected_date_string, verification_info)
    """
    verification_info = {
        'original_input': str(input_date),
        'intended_display': str(intended_display_date) if intended_display_date else None,
        'correction_applied': False,
        'final_date': None,
        'warning': None
    }
    
    try:
        # Normalize input date to YYYY-MM-DD format
        if isinstance(input_date, str):
            normalized_date = normalize_date_string(input_date)
        elif isinstance(input_date, (date, datetime)):
            normalized_date = input_date.strftime('%Y-%m-%d')
        else:
            raise ValueError(f"Invalid date type: {type(input_date)}")
        
        verification_info['final_date'] = normalized_date
        
        # If we have an intended display date, verify consistency
        if intended_display_date:
            intended_normalized = normalize_date_string(str(intended_display_date))
            
            if normalized_date != intended_normalized:
                # Dates don't match - this indicates a timezone issue
                logger.warning(f"Date mismatch detected: input={normalized_date}, intended={intended_normalized}")
                
                # Apply correction based on the intended display date
                verification_info['final_date'] = intended_normalized
                verification_info['correction_applied'] = True
                verification_info['warning'] = f"Corrected {normalized_date} to {intended_normalized}"
                
                logger.info(f"Applied date correction: {normalized_date} -> {intended_normalized}")
        
        logger.info(f"Date verification complete: {verification_info}")
        return verification_info['final_date'], verification_info
        
    except Exception as e:
        logger.error(f"Error in date verification: {e}")
        verification_info['warning'] = f"Error: {str(e)}"
        return str(input_date), verification_info

def verify_date_from_database(stored_date, expected_display_format=None):
    """
    Verify a date retrieved from database and ensure it displays correctly.
    
    Args:
        stored_date: Date from database
        expected_display_format: Expected format like "Monday 5/26/25"
    
    Returns:
        tuple: (display_date_string, verification_info)
    """
    verification_info = {
        'stored_value': str(stored_date),
        'correction_applied': False,
        'display_date': None,
        'warning': None
    }
    
    try:
        # Convert stored date to display format
        if isinstance(stored_date, str):
            date_obj = datetime.strptime(stored_date, '%Y-%m-%d').date()
        elif isinstance(stored_date, (date, datetime)):
            date_obj = stored_date if isinstance(stored_date, date) else stored_date.date()
        else:
            raise ValueError(f"Invalid stored date type: {type(stored_date)}")
        
        # Check if we need to apply Railway correction
        corrected_date = check_railway_date_correction(date_obj)
        if corrected_date != date_obj:
            verification_info['correction_applied'] = True
            verification_info['warning'] = f"Applied Railway correction: {date_obj} -> {corrected_date}"
            date_obj = corrected_date
            logger.info(f"Applied Railway date correction: {stored_date} -> {corrected_date}")
        
        # Format for display
        display_date = format_date_for_display(date_obj)
        verification_info['display_date'] = display_date
        
        logger.info(f"Date retrieval verification: {verification_info}")
        return display_date, verification_info
        
    except Exception as e:
        logger.error(f"Error in date retrieval verification: {e}")
        verification_info['warning'] = f"Error: {str(e)}"
        return str(stored_date), verification_info

def check_railway_date_correction(date_obj):
    """
    Check if a date needs Railway timezone correction.
    
    This addresses the known issue where Railway PostgreSQL stores dates
    incorrectly due to timezone handling, even when PGTZ/TZ variables are set.
    
    Args:
        date_obj: date object to check
    
    Returns:
        date: Corrected date if needed, original date otherwise
    """
    import os
    
    # Check if timezone environment variables are set
    tz_env = os.getenv('TZ')
    pgtz_env = os.getenv('PGTZ')
    
    # If timezone environment variables are properly set, no correction needed
    # This means Railway timezone issues are handled at the infrastructure level
    if (tz_env and 'America/Chicago' in tz_env) or (pgtz_env and 'America/Chicago' in pgtz_env):
        logger.info(f"Timezone environment variables detected (TZ={tz_env}, PGTZ={pgtz_env}), skipping Railway correction")
        return date_obj
    
    # Check for Railway environment variables
    railway_env_vars = [
        'RAILWAY_ENVIRONMENT', 'DATABASE_URL', 'POSTGRES_DB', 'PGDATABASE'
    ]
    
    is_railway = any(os.getenv(var) for var in railway_env_vars)
    
    if not is_railway:
        logger.info("Not running on Railway, no correction needed")
        return date_obj
    
    # Only apply Railway correction if:
    # 1. We're on Railway
    # 2. No timezone environment variables are set
    logger.info("Railway environment detected without timezone variables, applying +1 day correction")
    corrected_date = date_obj + timedelta(days=1)
    logger.info(f"Railway correction applied: {date_obj} -> {corrected_date}")
    return corrected_date

def format_date_for_display(date_obj):
    """
    Format a date for display with day of week.
    """
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
    
    day_of_week = date_obj.strftime('%A')
    date_str = date_obj.strftime('%-m/%-d/%y')  # Remove leading zeros
    return f"{day_of_week} {date_str}"

def log_date_operation(operation, input_data, output_data, verification_info):
    """
    Log date operations for debugging and monitoring.
    """
    logger.info(f"""
=== DATE OPERATION LOG ===
Operation: {operation}
Input: {input_data}
Output: {output_data}
Verification: {verification_info}
==========================""") 