from database import get_db

def add_club_automation_column():
    """Add club_automation_password column to users table"""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                # Check if the column exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'club_automation_password'
                """)
                column_exists = cursor.fetchone() is not None
                
                if not column_exists:
                    print("Adding club_automation_password column to users table...")
                    cursor.execute('''
                        ALTER TABLE users
                        ADD COLUMN club_automation_password TEXT
                    ''')
                    conn.commit()
                    print("Column added successfully!")
                else:
                    print("club_automation_password column already exists.")
                    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    add_club_automation_column() 