#!/usr/bin/env python3
"""
Date verification utilities for ensuring proper timezone handling
Used for debugging and validating date operations after TIMESTAMPTZ migration
"""

from datetime import datetime, timezone
import logging
from .date_utils import date_to_db_timestamp, normalize_date_string

logger = logging.getLogger(__name__)

def verify_and_fix_date_for_storage(date_input):
    """
    Verify and fix a date for proper database storage
    
    Args:
        date_input: Date in various formats
        
    Returns:
        datetime: UTC timezone-aware datetime for storage
    """
    try:
        utc_datetime = date_to_db_timestamp(date_input)
        log_date_operation(f"Date converted for storage: {date_input} -> {utc_datetime}")
        return utc_datetime
    except Exception as e:
        logger.error(f"Failed to convert date for storage: {date_input}, error: {e}")
        raise

def verify_date_from_database(db_result):
    """
    Verify a date retrieved from the database
    
    Args:
        db_result: Result from database query
        
    Returns:
        bool: True if date is properly formatted
    """
    if not db_result:
        return False
    
    try:
        # Check if it's a timezone-aware datetime
        if isinstance(db_result, datetime):
            if db_result.tzinfo is None:
                logger.warning(f"Database returned timezone-naive datetime: {db_result}")
                return False
            
            # Check if it's at midnight UTC
            if (db_result.hour == 0 and db_result.minute == 0 and 
                db_result.tzinfo == timezone.utc):
                log_date_operation(f"Valid UTC midnight datetime from DB: {db_result}")
                return True
            else:
                logger.warning(f"Database datetime not at midnight UTC: {db_result}")
                return False
        
        logger.warning(f"Database result is not a datetime: {type(db_result)}")
        return False
        
    except Exception as e:
        logger.error(f"Error verifying database date: {e}")
        return False

def log_date_operation(message):
    """
    Log date operations for debugging
    
    Args:
        message (str): Message to log
    """
    logger.info(f"[DATE_VERIFICATION] {message}")

def validate_date_consistency(original_date, stored_date, retrieved_date):
    """
    Validate that a date remains consistent through storage and retrieval
    
    Args:
        original_date: Original date input
        stored_date: Date as stored in database
        retrieved_date: Date as retrieved from database
        
    Returns:
        bool: True if dates are consistent
    """
    try:
        # Convert original to expected storage format
        expected_stored = date_to_db_timestamp(original_date)
        
        # Check storage consistency
        if stored_date != expected_stored:
            logger.error(f"Storage inconsistency: expected {expected_stored}, got {stored_date}")
            return False
        
        # Check retrieval consistency
        if retrieved_date != stored_date:
            logger.error(f"Retrieval inconsistency: stored {stored_date}, retrieved {retrieved_date}")
            return False
        
        log_date_operation(f"Date consistency verified: {original_date} -> {stored_date} -> {retrieved_date}")
        return True
        
    except Exception as e:
        logger.error(f"Error validating date consistency: {e}")
        return False 