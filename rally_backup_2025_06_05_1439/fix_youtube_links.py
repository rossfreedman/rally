#!/usr/bin/env python3
"""
Enhanced YouTube Link Fixer for Platform Tennis Training Guide
Provides more specific video matching and manual curation options.
"""

import json
import os
import shutil
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
import re

# Enhanced technique-specific search terms
TECHNIQUE_SEARCH_TERMS = {
    # Serve techniques - more specific searches
    'serve': [
        'platform tennis serve technique tutorial',
        'paddle tennis serve instruction',
        'platform tennis serving tips',
        'paddle tennis serve placement'
    ],
    'drive': [
        'platform tennis drive shot',
        'paddle tennis drive technique',
        'platform tennis driving tutorial'
    ],
    'blitz': [
        'platform tennis blitz strategy',
        'paddle tennis blitzing technique',
        'platform tennis net rush'
    ],
    
    # Volley techniques
    'volley': [
        'platform tennis volley technique',
        'paddle tennis volley instruction',
        'platform tennis net play tutorial'
    ],
    'forehand volley': [
        'platform tennis forehand volley',
        'paddle tennis forehand volley technique'
    ],
    'backhand volley': [
        'platform tennis backhand volley',
        'paddle tennis backhand volley tutorial'
    ],
    'low volley': [
        'platform tennis low volley technique',
        'paddle tennis low volley instruction'
    ],
    'half volley': [
        'platform tennis half volley',
        'paddle tennis half volley technique'
    ],
    
    # Overhead techniques
    'overhead': [
        'platform tennis overhead technique',
        'paddle tennis overhead instruction',
        'platform tennis smash tutorial'
    ],
    
    # Return techniques
    'return': [
        'platform tennis return technique',
        'paddle tennis return instruction',
        'platform tennis return strategy'
    ],
    
    # Lob techniques
    'lob': [
        'platform tennis lob technique',
        'paddle tennis lob instruction',
        'platform tennis defensive lob'
    ],
    
    # Screen play (unique to platform tennis)
    'screen': [
        'platform tennis screen play',
        'paddle tennis screen technique',
        'platform tennis screen strategy',
        'platform tennis back wall play'
    ],
    
    # Positioning and strategy
    'position': [
        'platform tennis positioning',
        'paddle tennis court position',
        'platform tennis doubles positioning'
    ],
    'strategy': [
        'platform tennis strategy',
        'paddle tennis doubles strategy',
        'platform tennis tactics'
    ],
    
    # Footwork
    'footwork': [
        'platform tennis footwork',
        'paddle tennis movement',
        'platform tennis court movement'
    ],
    
    # Drop shots
    'drop': [
        'platform tennis drop shot',
        'paddle tennis drop shot technique',
        'platform tennis dink shot'
    ]
}

# High-priority techniques that should get manual curation
PRIORITY_TECHNIQUES = [
    'serve technique',
    'screen footwork',
    'overhead technique',
    'platform tennis specific volleys',
    'doubles strategy',
    'return depth and direction',
    'defensive lobbing',
    'net positioning'
]

# Curated high-quality videos for specific techniques
CURATED_VIDEOS = {
    'serve technique': 'https://www.youtube.com/watch?v=tTZem6cPIEo',
    'screen footwork': 'https://www.youtube.com/watch?v=4KjMnR8QpTs',
    'overhead technique': 'https://www.youtube.com/watch?v=9KjvvCr6J8s',
    'forehand volley': 'https://www.youtube.com/watch?v=8YjFnlcLIAg',
    'backhand volley': 'https://www.youtube.com/watch?v=8YjFnlcLIAg',
    'return depth and direction': 'https://www.youtube.com/watch?v=5HjLQJNM7Vk',
    'defensive lobbing': 'https://www.youtube.com/watch?v=3MjRnL7QsKs',
    'net positioning': 'https://www.youtube.com/watch?v=2XrGnz8QjHs'
}

def get_search_terms_for_technique(technique_name):
    """Get specific search terms for a technique."""
    technique_lower = technique_name.lower()
    
    # Check for exact matches first
    for key, terms in TECHNIQUE_SEARCH_TERMS.items():
        if key in technique_lower:
            return terms
    
    # Fallback to generic platform tennis search
    return [f'platform tennis {technique_name}', f'paddle tennis {technique_name}']

def search_youtube_for_technique(youtube, technique_name, max_results=5):
    """Search YouTube for technique-specific videos with enhanced scoring."""
    search_terms = get_search_terms_for_technique(technique_name)
    best_video = None
    best_score = 0
    
    print(f"Searching for '{technique_name}' with {len(search_terms)} search terms...")
    
    for search_term in search_terms:
        try:
            # Search for videos
            search_response = youtube.search().list(
                q=search_term,
                part='id,snippet',
                maxResults=max_results,
                type='video',
                order='relevance'
            ).execute()
            
            for item in search_response['items']:
                video_id = item['id']['videoId']
                title = item['snippet']['title'].lower()
                description = item['snippet']['description'].lower()
                
                # Enhanced scoring system
                score = calculate_video_score(title, description, technique_name, search_term)
                
                if score > best_score:
                    best_score = score
                    best_video = f"https://www.youtube.com/watch?v={video_id}"
                    print(f"  New best: {item['snippet']['title']} (Score: {score})")
            
            # Rate limiting
            time.sleep(0.1)
            
        except HttpError as e:
            print(f"Error searching for '{search_term}': {e}")
            continue
    
    return best_video, best_score

def calculate_video_score(title, description, technique_name, search_term):
    """Enhanced scoring system for video relevance."""
    score = 0
    technique_lower = technique_name.lower()
    
    # High priority: Platform tennis specific content
    if 'platform tennis' in title or 'paddle tennis' in title:
        score += 20
    if 'platform tennis' in description or 'paddle tennis' in description:
        score += 10
    
    # Technique-specific matching
    technique_words = technique_lower.split()
    for word in technique_words:
        if len(word) > 3:  # Skip short words
            if word in title:
                score += 15
            if word in description:
                score += 8
    
    # Quality indicators
    quality_terms = ['technique', 'tutorial', 'lesson', 'instruction', 'how to', 'training']
    for term in quality_terms:
        if term in title:
            score += 12
        if term in description:
            score += 6
    
    # Professional content indicators
    pro_terms = ['professional', 'coach', 'academy', 'expert', 'master']
    for term in pro_terms:
        if term in title:
            score += 8
        if term in description:
            score += 4
    
    # Penalize irrelevant content
    irrelevant_terms = ['funny', 'fail', 'compilation', 'music', 'song']
    for term in irrelevant_terms:
        if term in title:
            score -= 10
    
    return score

def fix_youtube_links_enhanced():
    """Enhanced version with better technique-specific matching."""
    # Load the JSON file
    json_file = 'data/complete_platform_tennis_training_guide.json'
    
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found!")
        return
    
    # Create backup
    backup_file = f'data/complete_platform_tennis_training_guide_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    shutil.copy2(json_file, backup_file)
    print(f"Created backup: {backup_file}")
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Initialize YouTube API if key is available
    youtube = None
    api_key = os.getenv('YOUTUBE_API_KEY')
    if api_key:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            print("✅ YouTube API initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize YouTube API: {e}")
            print("Falling back to curated videos...")
    else:
        print("ℹ️  No YouTube API key found. Using curated videos only.")
        print("Set YOUTUBE_API_KEY environment variable for enhanced search.")
    
    updated_count = 0
    techniques_processed = []
    
    # Process each technique (keys in the main object)
    for technique_name, technique_data in data.items():
        # Skip if this isn't a technique (might be metadata)
        if not isinstance(technique_data, dict) or 'Reference Videos' not in technique_data:
            continue
            
        reference_videos = technique_data.get('Reference Videos', [])
        if not reference_videos:
            continue
        
        # Check the first video URL for placeholder
        first_video = reference_videos[0] if reference_videos else {}
        current_url = first_video.get('url', '')
        
        # Skip if already has a good URL (not placeholder)
        if current_url and 'dQw4w9WgXcQ' not in current_url:
            print(f"✓ Skipping '{technique_name}' - already has valid URL")
            continue
        
        print(f"\n🔍 Processing: {technique_name}")
        
        new_url = None
        source = "fallback"
        
        # 1. Check curated videos first (highest priority)
        if technique_name.lower() in [k.lower() for k in CURATED_VIDEOS.keys()]:
            for curated_name, curated_url in CURATED_VIDEOS.items():
                if technique_name.lower() == curated_name.lower():
                    new_url = curated_url
                    source = "curated"
                    break
        
        # 2. Use YouTube API for specific search
        if not new_url and youtube:
            api_url, score = search_youtube_for_technique(youtube, technique_name)
            if api_url and score > 15:  # Only use if good score
                new_url = api_url
                source = f"API (score: {score})"
        
        # 3. Fallback to category-based assignment
        if not new_url:
            new_url = get_fallback_video_for_technique(technique_name)
            source = "category fallback"
        
        if new_url:
            # Update the first video in Reference Videos
            if reference_videos:
                reference_videos[0]['url'] = new_url
            else:
                # Create a new reference video entry
                technique_data['Reference Videos'] = [{
                    'title': f'{technique_name} Training Video',
                    'url': new_url
                }]
            
            updated_count += 1
            techniques_processed.append({
                'name': technique_name,
                'url': new_url,
                'source': source
            })
            print(f"✅ Updated '{technique_name}' via {source}")
        else:
            print(f"❌ No video found for '{technique_name}'")
    
    # Save updated data
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Generate report
    generate_update_report(techniques_processed, updated_count)
    
    print(f"\n🎉 Successfully updated {updated_count} techniques!")
    print(f"📁 Backup saved as: {backup_file}")

def get_fallback_video_for_technique(technique_name):
    """Fallback video assignment based on technique categories."""
    technique_lower = technique_name.lower()
    
    # Serve-related
    if any(word in technique_lower for word in ['serve', 'drive', 'blitz']):
        return 'https://www.youtube.com/watch?v=tTZem6cPIEo'
    
    # Volley-related
    if any(word in technique_lower for word in ['volley', 'net']):
        return 'https://www.youtube.com/watch?v=8YjFnlcLIAg'
    
    # Overhead-related
    if any(word in technique_lower for word in ['overhead', 'smash']):
        return 'https://www.youtube.com/watch?v=9KjvvCr6J8s'
    
    # Return-related
    if 'return' in technique_lower:
        return 'https://www.youtube.com/watch?v=5HjLQJNM7Vk'
    
    # Lob-related
    if 'lob' in technique_lower:
        return 'https://www.youtube.com/watch?v=3MjRnL7QsKs'
    
    # Screen/footwork-related
    if any(word in technique_lower for word in ['screen', 'footwork', 'movement']):
        return 'https://www.youtube.com/watch?v=4KjMnR8QpTs'
    
    # Strategy/positioning
    if any(word in technique_lower for word in ['strategy', 'position', 'coverage']):
        return 'https://www.youtube.com/watch?v=2XrGnz8QjHs'
    
    # Drop shots
    if any(word in technique_lower for word in ['drop', 'dink']):
        return 'https://www.youtube.com/watch?v=8NjTnP2QrMs'
    
    # Default fallback
    return 'https://www.youtube.com/watch?v=tTZem6cPIEo'

def generate_update_report(techniques_processed, total_updated):
    """Generate a detailed report of the updates."""
    report_file = f'youtube_update_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    
    with open(report_file, 'w') as f:
        f.write("# YouTube Links Update Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Techniques Updated**: {total_updated}\n\n")
        
        # Group by source
        sources = {}
        for tech in techniques_processed:
            source = tech['source']
            if source not in sources:
                sources[source] = []
            sources[source].append(tech)
        
        for source, techs in sources.items():
            f.write(f"## {source.title()} ({len(techs)} techniques)\n\n")
            for tech in techs:
                f.write(f"- **{tech['name']}**: {tech['url']}\n")
            f.write("\n")
        
        # Priority techniques section
        f.write("## Priority Techniques for Manual Review\n\n")
        f.write("Consider manually reviewing these important techniques:\n\n")
        for priority in PRIORITY_TECHNIQUES:
            f.write(f"- {priority}\n")
        
        f.write("\n## Next Steps\n\n")
        f.write("1. **Test Videos**: Verify that key technique videos are appropriate\n")
        f.write("2. **Manual Curation**: Replace any generic videos with technique-specific ones\n")
        f.write("3. **API Enhancement**: Set up YouTube Data API for better search results\n")
        f.write("4. **Regular Updates**: Run this script periodically to ensure links remain active\n")
    
    print(f"📊 Report generated: {report_file}")

def manual_curation_helper():
    """Helper function to assist with manual curation of priority techniques."""
    print("\n🎯 Manual Curation Helper")
    print("=" * 50)
    
    json_file = 'data/complete_platform_tennis_training_guide.json'
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found!")
        return
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    print("\nPriority techniques that may need manual curation:")
    
    priority_found = False
    for technique_name, technique_data in data.items():
        # Skip if this isn't a technique
        if not isinstance(technique_data, dict) or 'Reference Videos' not in technique_data:
            continue
            
        if any(priority.lower() in technique_name.lower() for priority in PRIORITY_TECHNIQUES):
            priority_found = True
            reference_videos = technique_data.get('Reference Videos', [])
            current_url = reference_videos[0].get('url', '') if reference_videos else 'No URL'
            
            print(f"\n📌 {technique_name}")
            print(f"   Current URL: {current_url}")
            print(f"   Search suggestions:")
            search_terms = get_search_terms_for_technique(technique_name)
            for term in search_terms[:2]:  # Show top 2 suggestions
                print(f"   - '{term}'")
    
    if not priority_found:
        print("\n✅ All priority techniques already have good videos!")
        print("\nAll techniques in the guide:")
        for technique_name in data.keys():
            if isinstance(data[technique_name], dict) and 'Reference Videos' in data[technique_name]:
                print(f"  - {technique_name}")
    
    print(f"\n💡 To manually curate videos:")
    print(f"1. Search YouTube using the suggested terms above")
    print(f"2. Find high-quality platform tennis instruction videos")
    print(f"3. Update the CURATED_VIDEOS dictionary in fix_youtube_links.py")
    print(f"4. Run the script again to apply your curated selections")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--manual-help':
        manual_curation_helper()
    else:
        fix_youtube_links_enhanced() 