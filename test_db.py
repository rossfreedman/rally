from database import get_db

def test_connection():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Test users table
                cur.execute('SELECT COUNT(*) FROM users')
                user_count = cur.fetchone()[0]
                print(f"Number of users: {user_count}")
                
                # Test user_instructions table
                cur.execute('SELECT COUNT(*) FROM user_instructions')
                instruction_count = cur.fetchone()[0]
                print(f"Number of instructions: {instruction_count}")
                
                # Test player_availability table
                cur.execute('SELECT COUNT(*) FROM player_availability')
                availability_count = cur.fetchone()[0]
                print(f"Number of availability records: {availability_count}")
                
                # Test user_activity_logs table
                cur.execute('SELECT COUNT(*) FROM user_activity_logs')
                log_count = cur.fetchone()[0]
                print(f"Number of activity logs: {log_count}")
                
                print("\nDatabase connection test successful!")
                
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")

if __name__ == '__main__':
    test_connection() 