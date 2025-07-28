#!/usr/bin/env python3

"""
Direct import script to bypass interactive prompts
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from modernized_import_filterable import ModernizedETLImporter

def main():
    print("🚀 Direct Import: All Match Scores to Main Database")
    print("=" * 60)
    
    # Create importer instance
    importer = ModernizedETLImporter()
    
    # Set configuration directly (bypass interactive prompts)
    importer.config = {
        'league': 'all',
        'series': 'all', 
        'data_types': ['match_scores']
    }
    
    print(f"📋 Configuration:")
    print(f"   League: {importer.config['league']}")
    print(f"   Series: {importer.config['series']}")
    print(f"   Data Types: {importer.config['data_types']}")
    print()
    
    # Connect to database
    if not importer.connect_db():
        print("❌ Database connection failed")
        return False
    
    # Process match scores directly
    try:
        print("🔄 Processing match_scores...")
        success = importer._process_match_scores()
        
        if success:
            print("✅ Match scores import completed successfully!")
        else:
            print("❌ Match scores import failed")
            
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    finally:
        importer.close_db()
    
    return True

if __name__ == "__main__":
    main() 