from database import get_db

def set_club_automation_password():
    """Set Club Automation password for Ross Freedman"""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                # Update the password for Ross Freedman
                cursor.execute('''
                    UPDATE users 
                    SET club_automation_password = %s 
                    WHERE email = %s
                ''', ('PjapNA8MLniWQjFTFTxZ', 'rossfreedman@gmail.com'))
                
                if cursor.rowcount == 0:
                    print("No user found with email rossfreedman@gmail.com")
                else:
                    conn.commit()
                    print("Successfully set Club Automation password for Ross Freedman")
                    
    except Exception as e:
        print(f"Error setting password: {str(e)}")

if __name__ == '__main__':
    set_club_automation_password() 