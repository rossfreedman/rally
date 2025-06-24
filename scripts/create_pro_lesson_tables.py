#!/usr/bin/env python3

"""
Script to create pro lesson tables for the Rally application.
This script creates the necessary tables for the Schedule Lesson with Pro feature.
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_update, execute_query_one

def create_pros_table():
    """Create the pros table to store professional instructor information"""
    create_pros_sql = """
    CREATE TABLE IF NOT EXISTS pros (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        bio TEXT,
        specialties TEXT,
        hourly_rate DECIMAL(6,2),
        image_url VARCHAR(500),
        phone VARCHAR(20),
        email VARCHAR(255),
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    print("Creating pros table...")
    try:
        execute_update(create_pros_sql)
        print("✅ Pros table created successfully")
    except Exception as e:
        print(f"❌ Error creating pros table: {e}")
        return False
    
    return True

def create_pro_lessons_table():
    """Create the pro_lessons table to store lesson bookings"""
    create_lessons_sql = """
    CREATE TABLE IF NOT EXISTS pro_lessons (
        id SERIAL PRIMARY KEY,
        user_email VARCHAR(255) NOT NULL,
        pro_id INTEGER REFERENCES pros(id),
        lesson_date DATE NOT NULL,
        lesson_time TIME NOT NULL,
        focus_areas TEXT NOT NULL,
        notes TEXT,
        status VARCHAR(50) DEFAULT 'requested',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    print("Creating pro_lessons table...")
    try:
        execute_update(create_lessons_sql)
        print("✅ Pro lessons table created successfully")
    except Exception as e:
        print(f"❌ Error creating pro_lessons table: {e}")
        return False
    
    return True

def insert_sample_pros():
    """Insert sample pro data"""
    sample_pros = [
        {
            'name': 'Olga Martinsone',
            'bio': 'Director of Racquets, Tennaqua Swim & Racquet Club, Deerfield, IL. I am a USPTA certified Tennis/Paddle Elite Professional. I began playing tennis when I was ten years old in my home country of Latvia where I played for the Latvian National Tennis Team. Additionally, I played in several International Tennis Federation (ITF) tournaments throughout Europe and the Middle East.',
            'specialties': 'Overheads, Volleys, Court Positioning',
            'hourly_rate': 80.00,
            'phone': '555-0101',
            'email': 'olga.martinsone@tennaqua.com'
        },
        {
            'name': 'Billy Friedman, Tennis Pro',
            'bio': 'The NJCAA Region 4 Player-of-the-Year award tops off a season where Billy was also the Illinois Skyway Collegiate Conference Player-of-the-Year. Billy was the Region 4 champion at number two singles and number one doubles the past two years. Billy\'s undefeated record at number one singles led the CLC Men\'s Tennis Team to the NJCAA Men\'s Tennis National Tournament, a second place finish in both the region and conference, and a 8-2 team record.',
            'specialties': 'Serves, Backhands, Mental Game',
            'hourly_rate': 75.00,
            'phone': '555-0102', 
            'email': 'billy.friedman@rallytennis.com'
        },
        {
            'name': 'Mike Simms, Tennis Pro',
            'bio': 'Experienced tennis professional with over 10 years of coaching experience. Specializes in developing players of all skill levels, from beginners learning the fundamentals to advanced players refining their technique. Known for his patient teaching style and ability to break down complex techniques into manageable steps.',
            'specialties': 'Forehands, Footwork, Strategy',
            'hourly_rate': 70.00,
            'phone': '555-0103',
            'email': 'mike.simms@rallytennis.com'
        }
    ]
    
    print("Inserting sample pros...")
    
    # Check if pros already exist
    existing_pros = execute_query_one("SELECT COUNT(*) as count FROM pros")
    if existing_pros and existing_pros['count'] > 0:
        print("🔄 Pros already exist, skipping sample data insertion")
        return True
    
    insert_sql = """
    INSERT INTO pros (name, bio, specialties, hourly_rate, phone, email, is_active)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        for pro in sample_pros:
            execute_update(insert_sql, [
                pro['name'],
                pro['bio'], 
                pro['specialties'],
                pro['hourly_rate'],
                pro['phone'],
                pro['email'],
                True
            ])
        print(f"✅ Inserted {len(sample_pros)} sample pros")
    except Exception as e:
        print(f"❌ Error inserting sample pros: {e}")
        return False
    
    return True

def create_indexes():
    """Create indexes for better performance"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_pro_lessons_user_email ON pro_lessons(user_email);",
        "CREATE INDEX IF NOT EXISTS idx_pro_lessons_lesson_date ON pro_lessons(lesson_date);",
        "CREATE INDEX IF NOT EXISTS idx_pro_lessons_status ON pro_lessons(status);",
        "CREATE INDEX IF NOT EXISTS idx_pros_active ON pros(is_active);"
    ]
    
    print("Creating indexes...")
    try:
        for index_sql in indexes:
            execute_update(index_sql)
        print("✅ Indexes created successfully")
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False
    
    return True

def main():
    """Main function to run the migration"""
    print("=== Creating Pro Lesson Tables ===")
    
    success = True
    
    # Create tables
    if not create_pros_table():
        success = False
    
    if not create_pro_lessons_table():
        success = False
    
    if not create_indexes():
        success = False
    
    if not insert_sample_pros():
        success = False
    
    if success:
        print("🎉 Pro lesson tables setup completed successfully!")
        print("\nNext steps:")
        print("- The Schedule Lesson with Pro feature is now ready to use")
        print("- Users can schedule lessons with the sample pros")
        print("- Admin can manage pros through the database")
        return True
    else:
        print("❌ Some operations failed. Check the errors above.")
        return False

if __name__ == "__main__":
    main() 