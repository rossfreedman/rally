import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Verify key is loaded
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in .env file")
