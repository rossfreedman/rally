import logging
import os
import traceback

from openai import OpenAI

# Reduce OpenAI HTTP logging verbosity in production
is_development = os.environ.get("FLASK_ENV") == "development"
if not is_development:
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize OpenAI client with error handling
client = None
try:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        client = OpenAI(
            api_key=openai_api_key, 
            organization=os.getenv("OPENAI_ORG_ID")
        )
        print("✅ OpenAI client initialized successfully")
    else:
        print("⚠️  OPENAI_API_KEY not found - AI features will be disabled")
except Exception as e:
    print(f"⚠️  Failed to initialize OpenAI client: {e}")
    print("AI features will be disabled")

# Get assistant ID from environment variable
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")


def get_or_create_assistant():
    """Get the paddle tennis assistant (do not set or update instructions here)"""
    if not client:
        raise Exception("OpenAI client not available. Please set OPENAI_API_KEY environment variable.")
    
    if not assistant_id:
        raise Exception("OPENAI_ASSISTANT_ID environment variable not set.")
    
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        print(f"Successfully retrieved existing assistant with ID: {assistant.id}")
        return assistant
    except Exception as e:
        print(f"Error retrieving assistant: {str(e)}")
        print("Full error details:", traceback.format_exc())
        raise Exception(
            "Failed to initialize assistant. Please check the error messages above."
        )


def update_assistant_instructions(new_instructions):
    """Update the assistant's instructions"""
    if not client:
        raise Exception("OpenAI client not available. Please set OPENAI_API_KEY environment variable.")
    
    if not assistant_id:
        raise Exception("OPENAI_ASSISTANT_ID environment variable not set.")
    
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        updated_assistant = client.beta.assistants.update(
            assistant_id=assistant.id, instructions=new_instructions
        )
        print(f"Successfully updated assistant instructions")
        return updated_assistant
    except Exception as e:
        print(f"Error updating assistant instructions: {str(e)}")
        print("Full error details:", traceback.format_exc())
        raise Exception(
            "Failed to update assistant instructions. Please check the error messages above."
        )
