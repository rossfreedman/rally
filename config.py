import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key (only validate when actually used, not on import)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class TwilioConfig:
    """Configuration for Twilio SMS notifications"""
    ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "AC3061535ed8ad3468101940a6ab20b281")
    AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "MGa5958eb19c37c4d26b111098d4ffb809")
    SENDER_PHONE = os.getenv("TWILIO_SENDER_PHONE", "+13128001632")
    # Removed invalid CAMPAIGN_SID to prevent A2P 10DLC enforcement issues
    # CAMPAIGN_SID = os.getenv("TWILIO_CAMPAIGN_SID", "CM09eba13d94c2053c6bf9a2bb78410d58")
    
    @classmethod
    def is_configured(cls):
        """Check if Twilio is properly configured"""
        return bool(cls.ACCOUNT_SID and cls.AUTH_TOKEN and cls.MESSAGING_SERVICE_SID)
    
    @classmethod
    def validate_config(cls):
        """Validate Twilio configuration and return status"""
        missing = []
        if not cls.ACCOUNT_SID:
            missing.append("TWILIO_ACCOUNT_SID")
        if not cls.AUTH_TOKEN:
            missing.append("TWILIO_AUTH_TOKEN")  
        if not cls.MESSAGING_SERVICE_SID:
            missing.append("TWILIO_MESSAGING_SERVICE_SID")
            
        return {
            "is_valid": len(missing) == 0,
            "missing_vars": missing,
            "account_sid": cls.ACCOUNT_SID,
            "messaging_service_sid": cls.MESSAGING_SERVICE_SID,
            "sender_phone": cls.SENDER_PHONE
        }


def get_openai_api_key():
    """Get OpenAI API key with validation"""
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key not found in .env file")
    return OPENAI_API_KEY
