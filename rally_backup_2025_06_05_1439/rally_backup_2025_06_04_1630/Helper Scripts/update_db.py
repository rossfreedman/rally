import sqlite3
import os

def update_db():
    """Update the database structure to fix foreign key constraint issues"""
    # Get the database path
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
    print(f"Updating database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Rename the old table
        print("Renaming user_activity_logs table to user_activity_logs_old...")
        cursor.execute('''
        ALTER TABLE user_activity_logs RENAME TO user_activity_logs_old
        ''')
        
        # Create new table without the foreign key constraint
        print("Creating new user_activity_logs table without foreign key constraint...")
        cursor.execute('''
        CREATE TABLE user_activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            page TEXT,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Copy data from old table to new table
        print("Copying data from old table to new table...")
        cursor.execute('''
        INSERT INTO user_activity_logs 
        (user_email, activity_type, page, action, details, ip_address, timestamp)
        SELECT user_email, activity_type, page, action, details, ip_address, timestamp
        FROM user_activity_logs_old
        ''')
        
        # Create index on user_email and timestamp
        print("Creating index on user_email and timestamp...")
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_activity_logs_user_email 
        ON user_activity_logs(user_email, timestamp)
        ''')
        
        # Drop the old table
        print("Dropping old table...")
        cursor.execute('''
        DROP TABLE user_activity_logs_old
        ''')
        
        # Commit the transaction
        conn.commit()
        print("Database update completed successfully!")
        
    except Exception as e:
        # Roll back in case of error
        conn.rollback()
        print(f"Error updating database: {str(e)}")
        raise
    finally:
        # Close connection
        conn.close()

if __name__ == "__main__":
    update_db() 