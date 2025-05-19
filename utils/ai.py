import os
import traceback
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    organization=os.getenv('OPENAI_ORG_ID')
)

# Get assistant ID from environment variable
assistant_id = os.getenv('OPENAI_ASSISTANT_ID')

def get_or_create_assistant():
    """Get or create the paddle tennis assistant"""
    try:
        # First try to retrieve the existing assistant
        try:
            assistant = client.beta.assistants.retrieve(assistant_id)
            print(f"Successfully retrieved existing assistant with ID: {assistant.id}")
            return assistant
        except Exception as e:
            if "No assistant found" in str(e):
                print(f"Assistant {assistant_id} not found, creating new one...")
            else:
                raise
            print(f"Error retrieving assistant: {str(e)}")
            print("Attempting to create new assistant...")

        # Create new assistant if retrieval failed
        assistant = client.beta.assistants.create(
            name="PaddlePro Assistant",
            instructions="""You are a paddle tennis assistant. Help users with:
            1. Generating optimal lineups based on player statistics
            2. Analyzing match patterns and team performance
            3. Providing strategic advice for upcoming matches
            4. Answering questions about paddle tennis rules and strategy""",
            model="gpt-4-turbo-preview"
        )
        print(f"Successfully created new assistant with ID: {assistant.id}")
        print("\nIMPORTANT: Save this assistant ID in your environment variables:")
        print(f"OPENAI_ASSISTANT_ID={assistant.id}")
        return assistant
    except Exception as e:
        error_msg = str(e)
        print(f"Error with assistant: {error_msg}")
        print("Full error details:", traceback.format_exc())
        
        if "No access to organization" in error_msg:
            print("\nTROUBLESHOOTING STEPS:")
            print("1. Verify your OPENAI_ORG_ID is correct")
            print("2. Ensure your API key has access to the organization")
            print("3. Check if the assistant ID belongs to the correct organization")
        elif "Rate limit" in error_msg:
            print("\nTROUBLESHOOTING STEPS:")
            print("1. Check your API usage and limits")
            print("2. Implement rate limiting or retry logic if needed")
        elif "Invalid authentication" in error_msg:
            print("\nTROUBLESHOOTING STEPS:")
            print("1. Verify your OPENAI_API_KEY is correct and active")
            print("2. Check if your API key has the necessary permissions")
        
        raise Exception("Failed to initialize assistant. Please check the error messages above.") 