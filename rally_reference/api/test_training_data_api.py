"""
Test script for the Training Data API module.

This script tests the training data API endpoints to ensure they work correctly
before integrating with the OpenAI Assistant.
"""

import requests
import json
import sys
import os

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_api_endpoint(base_url="http://localhost:8080"):
    """
    Test the training data API endpoints.
    
    Args:
        base_url (str): The base URL of the Flask application
    """
    print("🧪 Testing Training Data API")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/api/training-data-health")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['message']}")
            print(f"   Total topics available: {data.get('total_topics', 'Unknown')}")
        else:
            print(f"❌ Health check failed: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False
    
    # Test 2: Get all topics
    print("\n2. Testing topics list endpoint...")
    try:
        response = requests.get(f"{base_url}/api/training-topics")
        if response.status_code == 200:
            data = response.json()
            topics = data['topics']
            print(f"✅ Retrieved {data['total_count']} topics")
            print(f"   First 5 topics: {topics[:5]}")
        else:
            print(f"❌ Failed to get topics: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    # Test 3: Get specific topic data
    print("\n3. Testing specific topic retrieval...")
    test_topics = [
        "Serve technique and consistency",
        "Forehand volleys", 
        "serve",  # Partial match test
        "NonExistentTopic"  # Error case test
    ]
    
    for topic in test_topics:
        print(f"\n   Testing topic: '{topic}'")
        try:
            response = requests.post(
                f"{base_url}/api/get-training-data-by-topic",
                json={"topic": topic},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Found topic: '{data['topic']}'")
                
                # Check if Reference Videos exist and have URLs
                ref_videos = data['data'].get('Reference Videos', [])
                if ref_videos:
                    print(f"   📹 Found {len(ref_videos)} reference videos:")
                    for i, video in enumerate(ref_videos[:2]):  # Show first 2
                        title = video.get('title', 'No title')
                        url = video.get('url', 'No URL')
                        print(f"      {i+1}. {title}")
                        print(f"         URL: {url}")
                else:
                    print("   ⚠️  No reference videos found")
                    
            elif response.status_code == 404:
                data = response.json()
                print(f"   ❌ Topic not found: {data['error']}")
                if 'available_topics_sample' in data:
                    print(f"   💡 Suggestion: {data.get('suggestion', 'Try different keywords')}")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Connection error: {e}")
    
    # Test 4: Invalid request format
    print("\n4. Testing error handling...")
    try:
        # Test empty request
        response = requests.post(
            f"{base_url}/api/get-training-data-by-topic",
            json={},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 400:
            print("   ✅ Empty request properly rejected")
        else:
            print(f"   ❌ Expected 400, got {response.status_code}")
            
        # Test missing topic
        response = requests.post(
            f"{base_url}/api/get-training-data-by-topic",
            json={"topic": ""},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 400:
            print("   ✅ Empty topic properly rejected")
        else:
            print(f"   ❌ Expected 400, got {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 API testing completed!")

def test_local_module():
    """
    Test the training data module directly (without Flask server).
    """
    print("🧪 Testing Training Data Module Directly")
    print("=" * 50)
    
    try:
        from api.training_data import load_training_data, find_topic_data
        
        # Test loading data
        print("\n1. Testing data loading...")
        training_data = load_training_data()
        print(f"✅ Loaded {len(training_data)} topics from JSON file")
        
        # Test topic finding
        print("\n2. Testing topic finding...")
        test_topics = ["Serve technique and consistency", "serve", "volley"]
        
        for topic in test_topics:
            topic_key, topic_data = find_topic_data(training_data, topic)
            if topic_data:
                print(f"✅ Found '{topic}' -> '{topic_key}'")
                ref_videos = topic_data.get('Reference Videos', [])
                print(f"   📹 {len(ref_videos)} reference videos")
            else:
                print(f"❌ Topic '{topic}' not found")
        
        print("\n✅ Module testing completed successfully!")
        
    except Exception as e:
        print(f"❌ Module test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Training Data API Test Suite")
    print("=" * 60)
    
    # Test the module directly first
    test_local_module()
    
    print("\n" + "=" * 60)
    
    # Test the API endpoints (requires server to be running)
    print("Note: The following tests require the Flask server to be running.")
    print("Start the server with: python server.py")
    
    user_input = input("\nIs the server running? (y/n): ").lower().strip()
    if user_input == 'y':
        test_api_endpoint()
    else:
        print("Skipping API endpoint tests. Start the server and run this script again.") 