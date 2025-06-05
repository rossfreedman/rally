#!/usr/bin/env python3
"""
YouTube Video Replacement Script for Platform Tennis Training Guide
Uses YouTube Data API to find and replace all videos in the JSON file with better, more relevant content.
"""

import json
import os
import shutil
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
import re
import sys

# Enhanced technique-specific search terms for better video matching
TECHNIQUE_SEARCH_TERMS = {
    # Serve techniques
    'serve technique': [
        'platform tennis serve technique tutorial',
        'paddle tennis serve instruction detailed',
        'platform tennis serving fundamentals',
        'how to serve platform tennis'
    ],
    'serve placement': [
        'platform tennis serve placement strategy',
        'paddle tennis serve targeting',
        'platform tennis serve accuracy',
        'serve placement platform tennis'
    ],
    'serve spin': [
        'platform tennis serve spin technique',
        'paddle tennis serve topspin slice',
        'platform tennis serve variations'
    ],
    
    # Return techniques
    'return depth': [
        'platform tennis return technique',
        'paddle tennis return strategy',
        'platform tennis return depth control',
        'return of serve platform tennis'
    ],
    'return direction': [
        'platform tennis return placement',
        'paddle tennis return angles',
        'platform tennis return tactics'
    ],
    
    # Volley techniques
    'forehand volley': [
        'platform tennis forehand volley technique',
        'paddle tennis forehand volley instruction',
        'platform tennis net play forehand'
    ],
    'backhand volley': [
        'platform tennis backhand volley technique',
        'paddle tennis backhand volley instruction',
        'platform tennis net play backhand'
    ],
    'low volley': [
        'platform tennis low volley technique',
        'paddle tennis low volley instruction',
        'platform tennis difficult volleys'
    ],
    'half volley': [
        'platform tennis half volley technique',
        'paddle tennis half volley instruction',
        'platform tennis transition shots'
    ],
    
    # Overhead techniques
    'overhead technique': [
        'platform tennis overhead technique',
        'paddle tennis overhead instruction',
        'platform tennis smash tutorial',
        'overhead shot platform tennis'
    ],
    'overhead placement': [
        'platform tennis overhead placement',
        'paddle tennis overhead strategy',
        'platform tennis overhead angles'
    ],
    'overhead spin': [
        'platform tennis overhead spin',
        'paddle tennis overhead variations',
        'platform tennis cut overhead'
    ],
    'overhead patience': [
        'platform tennis overhead patience',
        'paddle tennis overhead strategy',
        'platform tennis overhead exchanges'
    ],
    
    # Drive techniques
    'drives deck': [
        'platform tennis drive shot',
        'paddle tennis drive technique',
        'platform tennis groundstroke',
        'platform tennis drive instruction'
    ],
    'drives screen': [
        'platform tennis screen drive',
        'paddle tennis off the screen',
        'platform tennis screen shots',
        'platform tennis back wall play'
    ],
    
    # Lob techniques
    'defensive lob': [
        'platform tennis defensive lob',
        'paddle tennis lob technique',
        'platform tennis lob instruction',
        'defensive lob platform tennis'
    ],
    'offensive lob': [
        'platform tennis offensive lob',
        'paddle tennis attacking lob',
        'platform tennis lob strategy'
    ],
    'lob placement': [
        'platform tennis lob placement',
        'paddle tennis lob targeting',
        'platform tennis lob angles'
    ],
    
    # Screen play (unique to platform tennis)
    'screen': [
        'platform tennis screen play',
        'paddle tennis screen technique',
        'platform tennis screen strategy',
        'platform tennis back wall play',
        'platform tennis screen footwork'
    ],
    'side screen': [
        'platform tennis side screen',
        'paddle tennis side wall play',
        'platform tennis screen reads'
    ],
    'back screen': [
        'platform tennis back screen',
        'paddle tennis back wall technique',
        'platform tennis screen timing'
    ],
    'screen footwork': [
        'platform tennis screen footwork',
        'paddle tennis screen movement',
        'platform tennis screen positioning'
    ],
    
    # Net play and tactics
    'blitz': [
        'platform tennis blitz strategy',
        'paddle tennis blitzing technique',
        'platform tennis net rush',
        'platform tennis aggressive net play'
    ],
    'poach': [
        'platform tennis poaching',
        'paddle tennis poach technique',
        'platform tennis net interception'
    ],
    'net pressure': [
        'platform tennis net pressure',
        'paddle tennis aggressive net play',
        'platform tennis net positioning'
    ],
    'drop shot': [
        'platform tennis drop shot',
        'paddle tennis drop shot technique',
        'platform tennis dink shot'
    ],
    
    # Positioning and movement
    'net positioning': [
        'platform tennis net positioning',
        'paddle tennis doubles positioning',
        'platform tennis court position'
    ],
    'court coverage': [
        'platform tennis court coverage',
        'paddle tennis movement',
        'platform tennis positioning strategy'
    ],
    'transition': [
        'platform tennis transition game',
        'paddle tennis baseline to net',
        'platform tennis court movement'
    ],
    'footwork': [
        'platform tennis footwork',
        'paddle tennis movement technique',
        'platform tennis agility training'
    ],
    
    # Strategy and tactics
    'strategy': [
        'platform tennis strategy',
        'paddle tennis doubles strategy',
        'platform tennis tactics',
        'platform tennis game plan'
    ],
    'shot selection': [
        'platform tennis shot selection',
        'paddle tennis decision making',
        'platform tennis tactical choices'
    ],
    'communication': [
        'platform tennis doubles communication',
        'paddle tennis partner communication',
        'platform tennis teamwork'
    ],
    
    # Physical and mental
    'fitness': [
        'platform tennis fitness training',
        'paddle tennis conditioning',
        'platform tennis physical preparation'
    ],
    'mental': [
        'platform tennis mental game',
        'paddle tennis psychology',
        'platform tennis focus techniques'
    ],
    
    # Equipment and conditions
    'equipment': [
        'platform tennis equipment',
        'paddle tennis gear',
        'platform tennis paddle selection'
    ],
    'weather': [
        'platform tennis weather conditions',
        'paddle tennis cold weather play',
        'platform tennis winter play'
    ]
}

# High-quality curated videos for specific techniques
CURATED_VIDEOS = {
    'serve technique': {
        'title': 'Platform Tennis Serve Fundamentals',
        'url': 'https://www.youtube.com/watch?v=3mfRU8A9oG0'
    },
    'overhead technique': {
        'title': 'Platform Tennis Overhead Technique',
        'url': 'https://www.youtube.com/watch?v=ebjdeMxL4z0'
    },
    'screen play': {
        'title': 'Platform Tennis Screen Mastery',
        'url': 'https://www.youtube.com/watch?v=Jr7ZBdlULCk'
    },
    'return technique': {
        'title': 'Platform Tennis Return Strategy',
        'url': 'https://www.youtube.com/watch?v=jlfhwt1CfRA'
    },
    'volley technique': {
        'title': 'Platform Tennis Volley Fundamentals',
        'url': 'https://www.youtube.com/watch?v=GZgN5rdNm9Y'
    },
    'lob technique': {
        'title': 'Platform Tennis Lob Instruction',
        'url': 'https://www.youtube.com/watch?v=KSvK9Ne7WHY'
    },
    'drive technique': {
        'title': 'Platform Tennis Drive Shot',
        'url': 'https://www.youtube.com/watch?v=DTF86Mu65_0'
    },
    'positioning strategy': {
        'title': 'Platform Tennis Court Positioning',
        'url': 'https://www.youtube.com/watch?v=0j9VIWjCJho'
    }
}

def get_youtube_api_key():
    """Get YouTube API key from environment or user input."""
    api_key = os.getenv('YOUTUBE_API_KEY')
    if api_key:
        print(f"✅ Found API key in environment")
        return api_key
    
    print("❌ No YouTube API key found in environment variable YOUTUBE_API_KEY")
    print("Please set your API key:")
    print("export YOUTUBE_API_KEY='your_api_key_here'")
    
    # Allow manual input for testing
    manual_key = input("Enter API key manually (or press Enter to skip): ").strip()
    return manual_key if manual_key else None

def get_search_terms_for_technique(technique_name):
    """Get specific search terms for a technique."""
    technique_lower = technique_name.lower()
    
    # Check for exact matches first
    for key, terms in TECHNIQUE_SEARCH_TERMS.items():
        if key in technique_lower:
            return terms
    
    # Check for partial matches
    for key, terms in TECHNIQUE_SEARCH_TERMS.items():
        if any(word in technique_lower for word in key.split()):
            return terms
    
    # Fallback to generic platform tennis search
    return [
        f'platform tennis {technique_name}',
        f'paddle tennis {technique_name}',
        f'platform tennis {technique_name} technique',
        f'platform tennis {technique_name} instruction'
    ]

def calculate_video_score(title, description, technique_name, search_term):
    """Enhanced scoring system for video relevance."""
    score = 0
    technique_lower = technique_name.lower()
    title_lower = title.lower()
    description_lower = description.lower()
    
    # High priority: Platform tennis specific content
    if 'platform tennis' in title_lower:
        score += 25
    elif 'paddle tennis' in title_lower:
        score += 20
    
    if 'platform tennis' in description_lower:
        score += 15
    elif 'paddle tennis' in description_lower:
        score += 10
    
    # Technique-specific scoring
    technique_words = technique_lower.split()
    for word in technique_words:
        if word in title_lower:
            score += 15
        if word in description_lower:
            score += 8
    
    # Quality indicators
    quality_indicators = [
        'instruction', 'tutorial', 'technique', 'fundamentals',
        'lesson', 'coaching', 'tips', 'strategy', 'how to'
    ]
    for indicator in quality_indicators:
        if indicator in title_lower:
            score += 5
        if indicator in description_lower:
            score += 3
    
    # Professional content indicators
    pro_indicators = ['uspta', 'ppa', 'professional', 'coach', 'instructor']
    for indicator in pro_indicators:
        if indicator in title_lower or indicator in description_lower:
            score += 10
    
    # Penalize non-relevant content
    negative_indicators = ['funny', 'fail', 'compilation', 'music', 'highlights only']
    for indicator in negative_indicators:
        if indicator in title_lower or indicator in description_lower:
            score -= 10
    
    return max(0, score)

def search_youtube_for_technique(youtube, technique_name, max_results=8):
    """Search YouTube for technique-specific videos with enhanced scoring."""
    search_terms = get_search_terms_for_technique(technique_name)
    best_videos = []
    
    print(f"🔍 Searching for '{technique_name}' with {len(search_terms)} search terms...")
    
    for search_term in search_terms:
        try:
            # Search for videos
            search_response = youtube.search().list(
                q=search_term,
                part='id,snippet',
                maxResults=max_results,
                type='video',
                order='relevance',
                videoDuration='medium'  # Prefer medium-length videos
            ).execute()
            
            for item in search_response['items']:
                video_id = item['id']['videoId']
                title = item['snippet']['title']
                description = item['snippet']['description']
                
                # Calculate relevance score
                score = calculate_video_score(title, description, technique_name, search_term)
                
                if score > 10:  # Only consider videos with decent relevance
                    video_data = {
                        'title': title,
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'score': score,
                        'search_term': search_term
                    }
                    best_videos.append(video_data)
            
            # Rate limiting to respect API quotas
            time.sleep(0.2)
            
        except HttpError as e:
            print(f"⚠️  Error searching for '{search_term}': {e}")
            continue
        except Exception as e:
            print(f"⚠️  Unexpected error: {e}")
            continue
    
    # Sort by score and return top videos
    best_videos.sort(key=lambda x: x['score'], reverse=True)
    return best_videos[:3]  # Return top 3 videos

def get_curated_video_for_technique(technique_name):
    """Get curated video for a technique if available."""
    technique_lower = technique_name.lower()
    
    for key, video_data in CURATED_VIDEOS.items():
        if key in technique_lower or any(word in technique_lower for word in key.split()):
            return video_data
    
    return None

def replace_videos_in_json(json_file_path, youtube_api_key=None):
    """Replace all videos in the JSON file with better alternatives."""
    
    # Create backup
    backup_path = f"{json_file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(json_file_path, backup_path)
    print(f"📋 Created backup: {backup_path}")
    
    # Load JSON data
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Initialize YouTube API if key provided
    youtube = None
    if youtube_api_key:
        try:
            youtube = build('youtube', 'v3', developerKey=youtube_api_key)
            print("✅ YouTube API initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize YouTube API: {e}")
            print("Will use curated videos only")
    
    # Statistics
    total_techniques = len(data)
    techniques_updated = 0
    videos_added = 0
    videos_replaced = 0
    
    print(f"\n🎾 Processing {total_techniques} techniques...")
    
    for technique_name, technique_data in data.items():
        print(f"\n📝 Processing: {technique_name}")
        
        # Get current videos
        current_videos = technique_data.get('Reference Videos', [])
        current_count = len(current_videos)
        
        new_videos = []
        
        # First, try to get curated video
        curated_video = get_curated_video_for_technique(technique_name)
        if curated_video:
            new_videos.append(curated_video)
            print(f"  ✅ Added curated video: {curated_video['title']}")
        
        # Then, search for additional videos using API
        if youtube and len(new_videos) < 3:
            try:
                search_results = search_youtube_for_technique(youtube, technique_name)
                
                for video in search_results:
                    if len(new_videos) >= 3:  # Limit to 3 videos per technique
                        break
                    
                    # Avoid duplicates
                    if not any(existing['url'] == video['url'] for existing in new_videos):
                        new_videos.append({
                            'title': video['title'],
                            'url': video['url']
                        })
                        print(f"  ✅ Added API video: {video['title']} (Score: {video['score']})")
                
            except Exception as e:
                print(f"  ⚠️  API search failed: {e}")
        
        # If we still don't have enough videos, keep some original ones
        if len(new_videos) < 2 and current_videos:
            for video in current_videos:
                if len(new_videos) >= 3:
                    break
                if not any(existing['url'] == video['url'] for existing in new_videos):
                    new_videos.append(video)
                    print(f"  ♻️  Kept original: {video['title']}")
        
        # Update the technique data
        if new_videos:
            technique_data['Reference Videos'] = new_videos
            techniques_updated += 1
            videos_added += len(new_videos) - current_count if len(new_videos) > current_count else 0
            videos_replaced += min(current_count, len(new_videos))
            print(f"  📊 Updated: {current_count} → {len(new_videos)} videos")
        else:
            print(f"  ⚠️  No suitable videos found, keeping original")
    
    # Save updated JSON
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Generate report
    print(f"\n📊 REPLACEMENT SUMMARY")
    print(f"=" * 50)
    print(f"Total techniques processed: {total_techniques}")
    print(f"Techniques updated: {techniques_updated}")
    print(f"Videos added: {videos_added}")
    print(f"Videos replaced: {videos_replaced}")
    print(f"Backup created: {backup_path}")
    print(f"Updated file: {json_file_path}")
    
    # Create detailed report
    report_path = f"youtube_replacement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, 'w') as f:
        f.write(f"# YouTube Video Replacement Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total techniques processed: {total_techniques}\n")
        f.write(f"- Techniques updated: {techniques_updated}\n")
        f.write(f"- Videos added: {videos_added}\n")
        f.write(f"- Videos replaced: {videos_replaced}\n")
        f.write(f"- Backup file: {backup_path}\n")
        f.write(f"- Updated file: {json_file_path}\n\n")
        f.write(f"## Process Details\n\n")
        f.write(f"The replacement process used:\n")
        f.write(f"1. Curated high-quality videos for key techniques\n")
        f.write(f"2. YouTube Data API search with enhanced relevance scoring\n")
        f.write(f"3. Fallback to original videos when no better alternatives found\n")
        f.write(f"4. Maximum of 3 videos per technique\n\n")
        f.write(f"## API Usage\n\n")
        if youtube_api_key:
            f.write(f"- YouTube Data API: ✅ Used\n")
        else:
            f.write(f"- YouTube Data API: ❌ Not available (used curated videos only)\n")
    
    print(f"📄 Detailed report saved: {report_path}")
    
    return {
        'total_techniques': total_techniques,
        'techniques_updated': techniques_updated,
        'videos_added': videos_added,
        'videos_replaced': videos_replaced,
        'backup_path': backup_path,
        'report_path': report_path
    }

def main():
    """Main execution function."""
    print("🎾 Platform Tennis YouTube Video Replacement Tool")
    print("=" * 60)
    
    # Check if JSON file exists
    json_file = 'data/complete_platform_tennis_training_guide.json'
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        print("Please ensure you're in the correct directory.")
        return
    
    # Get API key
    api_key = get_youtube_api_key()
    if not api_key:
        print("⚠️  No API key available. Will use curated videos only.")
        proceed = input("Continue with curated videos only? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Exiting...")
            return
    
    # Confirm operation
    print(f"\n📋 About to replace videos in: {json_file}")
    print("This will:")
    print("- Create a backup of the original file")
    print("- Search for better platform tennis videos")
    print("- Replace existing videos with more relevant content")
    print("- Generate a detailed report")
    
    confirm = input("\nProceed with video replacement? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    # Execute replacement
    try:
        result = replace_videos_in_json(json_file, api_key)
        print(f"\n🎉 Video replacement completed successfully!")
        print(f"Check the report for details: {result['report_path']}")
        
    except Exception as e:
        print(f"\n❌ Error during replacement: {e}")
        print("Check the backup file if needed.")
        return

if __name__ == "__main__":
    main() 