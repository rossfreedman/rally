#!/usr/bin/env python3
"""
Date utility functions for timezone-aware date handling
After TIMESTAMPTZ migration, all dates are stored at midnight UTC
"""

from datetime import datetime, timezone, date
import pytz

# Application timezone - all dates should be interpreted in this timezone
APP_TIMEZONE = pytz.timezone('America/Chicago')

def normalize_date_string(date_str):
    """
    Normalize various date string formats to YYYY-MM-DD format
    
    Supports:
    - MM/DD/YYYY (e.g., "05/26/2025")
    - MM/DD/YY (e.g., "05/26/25") 
    - YYYY-MM-DD (e.g., "2025-05-26")
    - DD-MMM-YY (e.g., "26-May-25")
    
    Args:
        date_str (str): Date string in various formats
        
    Returns:
        str: Date string in YYYY-MM-DD format
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # If already in YYYY-MM-DD format, return as is
    if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str
    
    # Handle MM/DD/YYYY format
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            month, day, year = parts
            # Handle 2-digit years
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # Handle DD-MMM-YY format
    if '-' in date_str and len(date_str.split('-')) == 3:
        parts = date_str.split('-')
        if len(parts[1]) == 3:  # Month abbreviation
            day, month_abbr, year = parts
            month_map = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }
            month = month_map.get(month_abbr, '01')
            # Handle 2-digit years
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            return f"{year}-{month}-{day.zfill(2)}"
    
    # If we can't parse it, try to parse with datetime and convert
    try:
        # Try common formats
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d-%b-%y', '%m/%d/%y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except Exception:
        pass
    
    # If all else fails, return the original string
    return date_str

def date_to_db_timestamp(date_obj):
    """
    Convert a date object to a timezone-aware timestamp for database storage.
    After TIMESTAMPTZ migration, stores at midnight UTC for consistency.
    
    Args:
        date_obj: datetime.date, datetime.datetime, or string in various formats (YYYY-MM-DD, MM/DD/YYYY, etc.)
    
    Returns:
        datetime: Timezone-aware datetime at midnight UTC
    """
    if isinstance(date_obj, str):
        # First normalize the date string to YYYY-MM-DD format
        normalized_date_str = normalize_date_string(date_obj)
        if normalized_date_str:
            date_obj = datetime.strptime(normalized_date_str, '%Y-%m-%d').date()
        else:
            raise ValueError(f"Could not parse date string: {date_obj}")
    elif isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    elif not isinstance(date_obj, date):
        raise ValueError(f"Invalid date type: {type(date_obj)}")
    
    # Create midnight timestamp in UTC
    midnight_dt = datetime.combine(date_obj, datetime.min.time())
    return midnight_dt.replace(tzinfo=timezone.utc)

def db_timestamp_to_date(timestamp_obj):
    """
    Convert a database timestamp back to a date object.
    
    Args:
        timestamp_obj: timezone-aware datetime from database
    
    Returns:
        date: Date object in application timezone
    """
    if timestamp_obj is None:
        return None
    
    # Convert to application timezone and extract date
    local_dt = timestamp_obj.astimezone(APP_TIMEZONE)
    return local_dt.date()

def parse_date_flexible(date_str):
    """
    Parse a date string flexibly, handling multiple formats
    
    Args:
        date_str (str): Date string in various formats
        
    Returns:
        datetime.date or None: Parsed date object or None if parsing fails
    """
    if not date_str:
        return None
    
    try:
        normalized = normalize_date_string(date_str)
        if normalized:
            return datetime.strptime(normalized, '%Y-%m-%d').date()
    except Exception:
        pass
    
    return None

def format_date_for_display(date_obj, include_day=True):
    """
    Format a date for display in the UI
    
    Args:
        date_obj: datetime.date, datetime.datetime, or string
        include_day (bool): Whether to include day of week
        
    Returns:
        str: Formatted date string (e.g., "Monday 5/26/25" or "5/26/25")
    """
    if isinstance(date_obj, str):
        date_obj = parse_date_flexible(date_obj)
    
    if not date_obj:
        return ""
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    # Format as M/D/YY
    date_str = f"{date_obj.month}/{date_obj.day}/{str(date_obj.year)[2:]}"
    
    if include_day:
        day_name = date_obj.strftime('%A')
        return f"{day_name} {date_str}"
    
    return date_str

def is_same_date(date1, date2):
    """
    Compare two dates for equality, handling various input types.
    
    Args:
        date1, date2: date objects, datetime objects, or YYYY-MM-DD strings
    
    Returns:
        bool: True if dates represent the same day
    """
    def normalize_to_date(d):
        if isinstance(d, str):
            return datetime.strptime(normalize_date_string(d), '%Y-%m-%d').date()
        elif isinstance(d, datetime):
            return d.date()
        return d
    
    return normalize_to_date(date1) == normalize_to_date(date2)

# Database query helpers
def build_date_query(table_alias="", date_column="match_date"):
    """
    Build SQL for date comparison with TIMESTAMPTZ columns.
    
    After migration to TIMESTAMPTZ with midnight UTC storage, we can use simple DATE() extraction.
    
    Returns:
        str: SQL fragment like "DATE(match_date)"
    """
    prefix = f"{table_alias}." if table_alias else ""
    return f"DATE({prefix}{date_column})"

def build_date_params(date_value):
    """
    Build parameters for date queries with TIMESTAMPTZ columns.
    
    Args:
        date_value: date, datetime, or string
    
    Returns:
        datetime: Timezone-aware datetime at midnight UTC for database queries
    """
    return date_to_db_timestamp(date_value) 