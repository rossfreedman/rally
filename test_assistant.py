#!/usr/bin/env python3

from utils.ai import get_or_create_assistant
import traceback

def test_assistant_connection():
    """Test the OpenAI assistant connection"""
    try:
        print("🔍 Testing OpenAI assistant connection...")
        assistant = get_or_create_assistant()
        print('✅ Assistant connection successful!')
        print(f'Assistant ID: {assistant.id}')
        print(f'Assistant Name: {assistant.name}')
        print(f'Assistant Model: {assistant.model}')
        return True
    except Exception as e:
        print(f'❌ Assistant connection failed: {str(e)}')
        print("\n🔍 Full error traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_assistant_connection() 