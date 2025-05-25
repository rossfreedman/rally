#!/usr/bin/env python3
"""
YouTube URL Troubleshooting Script
Validates URLs without using YouTube API to avoid quota issues
"""

import json
import re
import requests
from urllib.parse import urlparse, parse_qs
import time

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

def validate_url_format(url):
    """Validate if URL is a proper YouTube URL format"""
    youtube_patterns = [
        r'https?://(www\.)?youtube\.com/watch\?.*v=[\w-]+',
        r'https?://(www\.)?youtu\.be/[\w-]+',
        r'https?://(www\.)?youtube\.com/embed/[\w-]+'
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False

def check_url_accessibility(url, timeout=10):
    """Check if URL is accessible without using YouTube API"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

def analyze_json_urls():
    """Analyze all YouTube URLs in the JSON file"""
    print("🔍 YOUTUBE URL TROUBLESHOOTING")
    print("=" * 50)
    
    # Load JSON file
    try:
        with open('data/complete_platform_tennis_training_guide.json', 'r') as f:
            data = json.load(f)
        print(f"✅ JSON file loaded successfully")
        print(f"📊 Found {len(data)} techniques")
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return
    
    # Analyze URLs
    total_videos = 0
    valid_format = 0
    accessible_urls = 0
    invalid_urls = []
    duplicate_urls = {}
    
    print(f"\n🔍 ANALYZING URLS...")
    print("-" * 30)
    
    for technique_name, technique_data in data.items():
        videos = technique_data.get('Reference Videos', [])
        
        if not videos:
            print(f"⚠️  {technique_name}: No videos found")
            continue
            
        print(f"\n📋 {technique_name} ({len(videos)} videos)")
        
        for i, video in enumerate(videos, 1):
            total_videos += 1
            url = video.get('url', '')
            title = video.get('title', 'Unknown')
            
            print(f"   {i}. {title}")
            print(f"      URL: {url}")
            
            # Check URL format
            if not url:
                print(f"      ❌ Empty URL")
                invalid_urls.append((technique_name, title, url, "Empty URL"))
                continue
                
            if not validate_url_format(url):
                print(f"      ❌ Invalid YouTube URL format")
                invalid_urls.append((technique_name, title, url, "Invalid format"))
                continue
            
            valid_format += 1
            print(f"      ✅ Valid YouTube URL format")
            
            # Extract video ID
            video_id = extract_video_id(url)
            if video_id:
                print(f"      📹 Video ID: {video_id}")
                
                # Check for duplicates
                if video_id in duplicate_urls:
                    duplicate_urls[video_id].append((technique_name, title))
                    print(f"      ⚠️  Duplicate video ID found")
                else:
                    duplicate_urls[video_id] = [(technique_name, title)]
            
            # Check accessibility (with rate limiting)
            print(f"      🌐 Checking accessibility...")
            if check_url_accessibility(url):
                accessible_urls += 1
                print(f"      ✅ URL is accessible")
            else:
                print(f"      ❌ URL not accessible")
                invalid_urls.append((technique_name, title, url, "Not accessible"))
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
    
    # Summary Report
    print(f"\n📈 SUMMARY REPORT")
    print("=" * 30)
    print(f"Total videos found: {total_videos}")
    print(f"Valid URL format: {valid_format}")
    print(f"Accessible URLs: {accessible_urls}")
    print(f"Invalid/Inaccessible: {len(invalid_urls)}")
    print(f"Success rate: {(accessible_urls/total_videos)*100:.1f}%" if total_videos > 0 else "No videos found")
    
    # Duplicate analysis
    duplicates = {vid_id: techniques for vid_id, techniques in duplicate_urls.items() if len(techniques) > 1}
    if duplicates:
        print(f"\n🔄 DUPLICATE VIDEOS FOUND: {len(duplicates)}")
        print("-" * 30)
        for video_id, techniques in duplicates.items():
            print(f"Video ID: {video_id}")
            for technique, title in techniques:
                print(f"  - {technique}: {title}")
            print()
    
    # Invalid URLs
    if invalid_urls:
        print(f"\n❌ INVALID/INACCESSIBLE URLS: {len(invalid_urls)}")
        print("-" * 30)
        for technique, title, url, reason in invalid_urls:
            print(f"Technique: {technique}")
            print(f"Title: {title}")
            print(f"URL: {url}")
            print(f"Issue: {reason}")
            print()
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("=" * 30)
    
    if len(invalid_urls) > 0:
        print("1. 🔧 Fix invalid/inaccessible URLs:")
        print("   - Check if videos still exist on YouTube")
        print("   - Update URLs for moved/renamed videos")
        print("   - Remove or replace unavailable content")
    
    if len(duplicates) > 0:
        print("2. 🔄 Handle duplicate videos:")
        print("   - Consider if same video should be used for multiple techniques")
        print("   - Find technique-specific alternatives where appropriate")
    
    print("3. 🚫 YouTube API Quota Issue:")
    print("   - Your API key has exceeded daily quota limits")
    print("   - YouTube Data API v3 has strict quotas (10,000 units/day default)")
    print("   - Each video lookup costs ~1-3 quota units")
    print("   - Wait 24 hours for quota reset, or request quota increase")
    
    print("4. 🔄 Alternative Approaches:")
    print("   - Use this script for URL validation (no API needed)")
    print("   - Manually curate videos instead of automated replacement")
    print("   - Batch process videos during low-usage periods")
    
    return {
        'total_videos': total_videos,
        'valid_format': valid_format,
        'accessible_urls': accessible_urls,
        'invalid_urls': invalid_urls,
        'duplicates': duplicates
    }

if __name__ == "__main__":
    results = analyze_json_urls() 