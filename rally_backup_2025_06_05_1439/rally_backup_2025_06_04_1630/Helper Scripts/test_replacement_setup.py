#!/usr/bin/env python3
"""
Test script to verify the YouTube replacement setup is working correctly.
"""

import json
import os
import sys

def test_json_file():
    """Test if the JSON file can be loaded and has the expected structure."""
    print("🧪 Testing JSON file...")
    
    json_file = 'data/complete_platform_tennis_training_guide.json'
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        return False
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ JSON file loaded successfully")
        print(f"📊 Found {len(data)} techniques")
        
        # Check structure
        sample_technique = next(iter(data.values()))
        if 'Reference Videos' in sample_technique:
            print("✅ Reference Videos structure found")
        else:
            print("❌ Reference Videos structure missing")
            return False
        
        # Count current videos
        total_videos = 0
        techniques_with_videos = 0
        for technique_name, technique_data in data.items():
            videos = technique_data.get('Reference Videos', [])
            if videos:
                techniques_with_videos += 1
                total_videos += len(videos)
        
        print(f"📹 Current state: {total_videos} videos across {techniques_with_videos} techniques")
        return True
        
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return False

def test_dependencies():
    """Test if required dependencies are available."""
    print("\n🧪 Testing dependencies...")
    
    try:
        import googleapiclient
        print("✅ googleapiclient available")
    except ImportError:
        print("❌ googleapiclient missing - run: pip install google-api-python-client")
        return False
    
    try:
        import google.auth
        print("✅ google.auth available")
    except ImportError:
        print("❌ google.auth missing - run: pip install google-auth")
        return False
    
    return True

def test_api_key():
    """Test if API key is configured."""
    print("\n🧪 Testing API key configuration...")
    
    api_key = os.getenv('YOUTUBE_API_KEY')
    if api_key:
        print(f"✅ API key found: {api_key[:10]}...")
        return True
    else:
        print("⚠️  No API key found in YOUTUBE_API_KEY environment variable")
        print("This is optional - you can still use curated videos")
        return True

def test_scripts_exist():
    """Test if the replacement scripts exist."""
    print("\n🧪 Testing script files...")
    
    scripts = [
        'replace_youtube_videos.py',
        'setup_youtube_replacement.py'
    ]
    
    all_exist = True
    for script in scripts:
        if os.path.exists(script):
            print(f"✅ {script} exists")
        else:
            print(f"❌ {script} missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests."""
    print("🎾 YouTube Replacement Setup Test")
    print("=" * 40)
    
    tests = [
        ("JSON File", test_json_file),
        ("Dependencies", test_dependencies),
        ("API Key", test_api_key),
        ("Script Files", test_scripts_exist)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        try:
            result = test_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name} test failed: {e}")
            all_passed = False
    
    print(f"\n{'='*40}")
    if all_passed:
        print("🎉 All tests passed! Ready to run YouTube replacement.")
        print("\nNext steps:")
        print("1. Set up your YouTube API key (if not already done)")
        print("2. Run: python setup_youtube_replacement.py")
        print("   OR")
        print("   Run: python replace_youtube_videos.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 