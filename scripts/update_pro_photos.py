#!/usr/bin/env python3

"""
Script to update pro photos in the Rally application.
This script updates the pros table with the actual photo URLs.
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_update

def update_pro_photos():
    """Update the pros table with the actual photo URLs"""
    
    # Photo mapping - based on the order and descriptions
    photo_updates = [
        {
            'name': 'Olga Martinsone',
            'image_url': '/static/images/olga_martinsone.jpg'
        },
        {
            'name': 'Billy Friedman, Tennis Pro', 
            'image_url': '/static/images/billy_friedman.jpg'
        },
        {
            'name': 'Mike Simms, Tennis Pro',
            'image_url': '/static/images/mike_simms.jpg'
        }
    ]
    
    print("Updating pro photos...")
    
    update_sql = """
    UPDATE pros 
    SET image_url = %s, updated_at = CURRENT_TIMESTAMP 
    WHERE name = %s
    """
    
    try:
        for pro in photo_updates:
            rows_affected = execute_update(update_sql, [pro['image_url'], pro['name']])
            if rows_affected > 0:
                print(f"✅ Updated photo for {pro['name']}: {pro['image_url']}")
            else:
                print(f"❌ No rows updated for {pro['name']} - check if pro exists")
                
        print("🎉 Pro photo updates completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating pro photos: {e}")
        return False

def verify_updates():
    """Verify the photo updates were successful"""
    from database_utils import execute_query
    
    print("\nVerifying photo updates...")
    
    query = "SELECT name, image_url FROM pros ORDER BY name DESC"
    
    try:
        pros = execute_query(query)
        print("\nCurrent pro photos:")
        for pro in pros:
            photo_status = "✅ Has photo" if pro['image_url'] else "❌ No photo"
            print(f"  {pro['name']}: {pro.get('image_url', 'None')} {photo_status}")
            
    except Exception as e:
        print(f"❌ Error verifying updates: {e}")

def main():
    """Main function to run the photo updates"""
    print("=== Updating Pro Photos ===")
    
    success = update_pro_photos()
    
    if success:
        verify_updates()
        print("\n🎉 All done! The Schedule Lesson page should now show actual photos instead of placeholders.")
        print("\nNext steps:")
        print("1. Make sure the photo files are saved in the static/images directory:")
        print("   - static/images/olga_martinsone.jpg")
        print("   - static/images/billy_friedman.jpg") 
        print("   - static/images/mike_simms.jpg")
        print("2. Visit /mobile/schedule-lesson to see the updated photos")
    else:
        print("❌ Photo update failed. Check the errors above.")

if __name__ == "__main__":
    main() 