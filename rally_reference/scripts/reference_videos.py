import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def search_youtube_video(keywords, api_key):
    """
    Search YouTube for a video using keywords and return the first result URL.
    
    Args:
        keywords (str): Search terms to find relevant video
        api_key (str): YouTube Data API key
        
    Returns:
        str: URL of first matching YouTube video, or None if no results found
    """
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Search for video
        request = youtube.search().list(
            part='id',
            q=keywords,
            type='video',
            maxResults=1
        )
        response = request.execute()

        # Get video ID from response
        if response['items']:
            video_id = response['items'][0]['id']['videoId']
            return f'https://www.youtube.com/watch?v={video_id}'
        
        return None

    except HttpError as e:
        print(f'An HTTP error {e.resp.status} occurred: {e.content}')
        return None

def update_json_with_videos(json_file_path, api_key):
    """
    Update JSON file sections with relevant YouTube video references.
    
    Args:
        json_file_path (str): Path to JSON file
        api_key (str): YouTube Data API key
    """
    try:
        # Read JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        # Iterate through sections
        for section in data:
            # Combine relevant keywords from section
            keywords = f"{section.get('title', '')} {section.get('keywords', '')}"
            
            # Search for video
            video_url = search_youtube_video(keywords.strip(), api_key)
            
            if video_url:
                # Update reference video link
                section['reference_video'] = video_url
            else:
                print(f"No video found for section: {section.get('title', '')}")
        
        # Write updated data back to file
        with open(json_file_path, 'w') as file:
            json.dump(data, file, indent=4)
            
        print("Successfully updated JSON file with video references")
        
    except Exception as e:
        print(f"Error processing JSON file: {str(e)}")

# Example usage:
# api_key = 'YOUR_YOUTUBE_API_KEY'  # Get from Google Cloud Console
# json_file = 'path/to/your/file.json'
# update_json_with_videos(json_file, api_key)
