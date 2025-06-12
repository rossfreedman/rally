import os
import traceback
import logging
from openai import OpenAI

# Reduce OpenAI HTTP logging verbosity in production
is_development = os.environ.get('FLASK_ENV') == 'development'
if not is_development:
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    organization=os.getenv('OPENAI_ORG_ID')
)

# Get assistant ID from environment variable
assistant_id = os.getenv('OPENAI_ASSISTANT_ID')

def get_or_create_assistant():
    """Get the paddle tennis assistant (do not set or update instructions here)"""
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        print(f"Successfully retrieved existing assistant with ID: {assistant.id}")
        return assistant
    except Exception as e:
        print(f"Error retrieving assistant: {str(e)}")
        print("Full error details:", traceback.format_exc())
        raise Exception("Failed to initialize assistant. Please check the error messages above.")

def update_assistant_instructions(new_instructions):
    """Update the assistant's instructions"""
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        updated_assistant = client.beta.assistants.update(
            assistant_id=assistant.id,
            instructions=new_instructions
        )
        print(f"Successfully updated assistant instructions")
        return updated_assistant
    except Exception as e:
        print(f"Error updating assistant instructions: {str(e)}")
        print("Full error details:", traceback.format_exc())
        raise Exception("Failed to update assistant instructions. Please check the error messages above.") 