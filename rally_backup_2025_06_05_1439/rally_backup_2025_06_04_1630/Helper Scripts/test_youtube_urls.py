#!/usr/bin/env python3
"""
Test script to validate YouTube URLs in the JSON file
"""

import json
import os
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def test_youtube_api():
    """Test YouTube API connection and validate some URLs"""
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ YOUTUBE_API_KEY not found in environment")
        return False
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        print("✅ YouTube API connection successful")
        
        # Load JSON file
        with open('data/complete_platform_tennis_training_guide.json', 'r') as f:
            data = json.load(f)
        
        print(f"\n📊 Found {len(data)} techniques in JSON")
        
        # Test first few videos
        test_count = 0
        valid_count = 0
        invalid_urls = []
        
        for technique_name, technique_data in list(data.items())[:5]:  # Test first 5 techniques
            videos = technique_data.get('Reference Videos', [])
            print(f"\n🔍 Testing technique: {technique_name}")
            print(f"   Videos found: {len(videos)}")
            
            for video in videos:
                test_count += 1
                url = video.get('url', '')
                title = video.get('title', 'Unknown')
                
                print(f"   Testing: {title}")
                print(f"   URL: {url}")
                
                # Extract video ID
                video_id = extract_video_id(url)
                if not video_id:
                    print(f"   ❌ Could not extract video ID from URL")
                    invalid_urls.append((technique_name, title, url, "Invalid URL format"))
                    continue
                
                print(f"   Video ID: {video_id}")
                
                # Test with YouTube API
                try:
                    response = youtube.videos().list(
                        part='snippet,status',
                        id=video_id
                    ).execute()
                    
                    if response['items']:
                        video_info = response['items'][0]
                        snippet = video_info['snippet']
                        status = video_info['status']
                        
                        print(f"   ✅ Video found: {snippet['title']}")
                        print(f"   📅 Published: {snippet['publishedAt'][:10]}")
                        print(f"   👤 Channel: {snippet['channelTitle']}")
                        print(f"   🔒 Privacy: {status['privacyStatus']}")
                        
                        if status['privacyStatus'] == 'public':
                            valid_count += 1
                        else:
                            invalid_urls.append((technique_name, title, url, f"Not public: {status['privacyStatus']}"))
                    else:
                        print(f"   ❌ Video not found or unavailable")
                        invalid_urls.append((technique_name, title, url, "Video not found"))
                        
                except HttpError as e:
                    print(f"   ❌ API Error: {e}")
                    invalid_urls.append((technique_name, title, url, f"API Error: {e}"))
                
                print()  # Empty line for readability
        
        # Summary
        print(f"\n📈 SUMMARY")
        print(f"=" * 30)
        print(f"Total videos tested: {test_count}")
        print(f"Valid videos: {valid_count}")
        print(f"Invalid videos: {len(invalid_urls)}")
        print(f"Success rate: {(valid_count/test_count)*100:.1f}%" if test_count > 0 else "No videos tested")
        
        if invalid_urls:
            print(f"\n❌ INVALID VIDEOS:")
            for technique, title, url, reason in invalid_urls:
                print(f"   {technique}: {title}")
                print(f"      URL: {url}")
                print(f"      Issue: {reason}")
                print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_youtube_api() 