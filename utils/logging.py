from flask import request
from datetime import datetime
from .db import execute_update
import sqlite3
import json
import traceback

def ensure_activity_logs_table():
    """Ensure the user activity logs table exists"""
    try:
        conn = sqlite3.connect('data/paddlepro.db')
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                page TEXT,
                action TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error creating activity logs table: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")

def log_user_activity(user_email, activity_type, page=None, action=None, details=None):
    """Log user activity to the database"""
    try:
        # Ensure table exists
        ensure_activity_logs_table()
        
        # Connect to database
        conn = sqlite3.connect('data/paddlepro.db')
        cursor = conn.cursor()
        
        # Convert details to string if it's a dictionary
        if isinstance(details, dict):
            details = json.dumps(details)
        elif details is None:
            details = ''
            
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Insert activity log
        cursor.execute('''
            INSERT INTO user_activity_logs (
                user_email, 
                activity_type,
                page,
                action,
                details, 
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_email, activity_type, page, action, details, timestamp))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error executing update: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        print("WARNING: Failed to log user activity")
        return False
                    
    except Exception as e:
        print(f"Error logging user activity: {str(e)}")
        return False 