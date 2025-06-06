import os
import json
from datetime import datetime
from database import get_db
import logging
from flask import request

logger = logging.getLogger(__name__)

def log_user_activity(user_email, activity_type, **kwargs):
    """Log user activity to the database"""
    try:
        # Extract common fields from kwargs
        page = kwargs.pop('page', None)
        action = kwargs.pop('action', None)
        details = kwargs.pop('details', None)
        
        # Get IP address from request or kwargs
        ip_address = kwargs.pop('ip_address', None)
        if not ip_address and request:
            # Try to get IP from X-Forwarded-For header first (for proxy setups)
            ip_address = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            if not ip_address:
                # Fallback to remote_addr if no X-Forwarded-For
                ip_address = request.remote_addr
        
        # Convert details to JSON string if it's a dictionary
        if isinstance(details, dict):
            details = json.dumps(details)
        
        # Connect to database
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Insert activity log
            cursor.execute('''
                INSERT INTO user_activity_logs 
                (user_email, activity_type, page, action, details, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (user_email, activity_type, page, action, details, ip_address))
            
            conn.commit()
            
        return True
    except Exception as e:
        logger.error(f"Error logging user activity: {str(e)}")
        return False

def get_user_activity(user_email):
    """Get user activity history"""
    try:
        # Connect to database
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get activity logs
            cursor.execute('''
                SELECT activity_type, page, action, details, ip_address, timestamp
                FROM user_activity_logs
                WHERE user_email = %s
                ORDER BY timestamp DESC
                LIMIT 100
            ''', (user_email,))
            
            activities = []
            for row in cursor.fetchall():
                activity_type, page, action, details, ip_address, timestamp = row
                activities.append({
                    'type': activity_type,
                    'page': page,
                    'action': action,
                    'details': details,
                    'ip_address': ip_address,
                    'timestamp': timestamp.isoformat() if timestamp else None
                })
            
            return activities
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        return [] 